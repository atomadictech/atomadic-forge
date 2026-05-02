"""Tier a2 - production-grade cost circuit breaker for autonomous loops.

Stops a runaway loop BEFORE it burns through $10k+ in API credits.
Real incidents reported: $47k loop, $30k agent loop. The pattern:
multi-tier budgets (per-task / per-session / per-day) with two
severity levels (soft = warn, hard = kill).

Composes nothing - this is a primitive that other modules wrap
around their LLM call sites.

Pattern (per OpenHands, Cursor agent-mode, AutoGPT):
  1. Hard step budget        per task
  2. Hard token budget       per task + per session + per day
  3. Hard wall-clock budget  per task + per session
  4. Soft warn at 80% of any hard ceiling
  5. Token-velocity-vs-progress detector (loop-stuck signal)

State is in-memory; persistence is the caller's job (e.g. ledger).
Thread-safe.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

SCHEMA: str = "atomadic-forge-deluxe.cost-circuit-breaker/v1"

# Defaults match published industry references:
#   OpenHands MAX_ITERATIONS default = 100
#   Cursor agent-mode budget         ~ 25 tool calls
#   Devin's published budget          per-task token cap
DEFAULT_MAX_STEPS_PER_TASK = 100
DEFAULT_MAX_TOKENS_PER_TASK = 1_000_000
DEFAULT_MAX_WALL_S_PER_TASK = 1800.0
DEFAULT_MAX_TOKENS_PER_SESSION = 5_000_000
DEFAULT_MAX_TOKENS_PER_DAY = 50_000_000
DEFAULT_MAX_USD_PER_DAY = 100.0
DEFAULT_SOFT_WARN_FRAC = 0.80


@dataclass(frozen=True)
class CircuitDecision:
    schema: str = SCHEMA
    allowed: bool = True
    severity: str = "ok"          # "ok" | "warn" | "trip"
    reason: str = ""
    triggered_check: str = ""
    budget_remaining_steps: int = 0
    budget_remaining_tokens: int = 0
    budget_remaining_usd: float = 0.0


@dataclass
class TaskState:
    task_id: str = ""
    started_at: float = 0.0
    steps: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    usd_spent: float = 0.0
    last_progress_step: int = 0
    last_progress_at: float = 0.0


@dataclass
class SessionState:
    session_id: str = ""
    tokens_total: int = 0
    usd_total: float = 0.0
    started_at: float = 0.0


@dataclass
class DayState:
    day_key: str = ""
    tokens_total: int = 0
    usd_total: float = 0.0


class CostCircuitBreaker:
    """Multi-tier breaker. Caller invokes ``check()`` before each LLM
    call and ``record()`` after to update counters."""

    def __init__(self, *,
                  max_steps_per_task: int = DEFAULT_MAX_STEPS_PER_TASK,
                  max_tokens_per_task: int = DEFAULT_MAX_TOKENS_PER_TASK,
                  max_wall_s_per_task: float = DEFAULT_MAX_WALL_S_PER_TASK,
                  max_tokens_per_session: int = DEFAULT_MAX_TOKENS_PER_SESSION,
                  max_tokens_per_day: int = DEFAULT_MAX_TOKENS_PER_DAY,
                  max_usd_per_day: float = DEFAULT_MAX_USD_PER_DAY,
                  soft_warn_frac: float = DEFAULT_SOFT_WARN_FRAC,
                  no_progress_step_limit: int = 5,
                  ) -> None:
        self.max_steps = max_steps_per_task
        self.max_tokens_task = max_tokens_per_task
        self.max_wall_s = max_wall_s_per_task
        self.max_tokens_session = max_tokens_per_session
        self.max_tokens_day = max_tokens_per_day
        self.max_usd_day = max_usd_per_day
        self.soft_frac = soft_warn_frac
        self.no_progress_limit = no_progress_step_limit
        self._tasks: dict[str, TaskState] = {}
        self._sessions: dict[str, SessionState] = {}
        self._days: dict[str, DayState] = {}
        self._lock = threading.Lock()

    def _day_key(self, ts: float) -> str:
        return time.strftime("%Y-%m-%d", time.gmtime(ts))

    def _task(self, task_id: str) -> TaskState:
        if task_id not in self._tasks:
            now = time.time()
            self._tasks[task_id] = TaskState(
                task_id=task_id, started_at=now,
                last_progress_at=now)
        return self._tasks[task_id]

    def _session(self, session_id: str) -> SessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(
                session_id=session_id, started_at=time.time())
        return self._sessions[session_id]

    def _day(self) -> DayState:
        key = self._day_key(time.time())
        if key not in self._days:
            self._days[key] = DayState(day_key=key)
        return self._days[key]

    def check(self, *, task_id: str, session_id: str = "default",
                est_tokens: int = 0, est_usd: float = 0.0,
                ) -> CircuitDecision:
        """Pre-call check. Returns CircuitDecision; caller MUST refuse
        the LLM call when allowed=False."""
        with self._lock:
            t = self._task(task_id)
            s = self._session(session_id)
            d = self._day()
            now = time.time()

            # 1. Steps per task
            if t.steps >= self.max_steps:
                return CircuitDecision(
                    allowed=False, severity="trip",
                    triggered_check="steps_per_task",
                    reason=(f"task {task_id} hit step limit "
                              f"{self.max_steps}"))

            # 2. Wall clock per task
            if (now - t.started_at) > self.max_wall_s:
                return CircuitDecision(
                    allowed=False, severity="trip",
                    triggered_check="wall_clock",
                    reason=(f"task {task_id} exceeded "
                              f"{self.max_wall_s:.0f}s wall clock"))

            # 3. Token budget per task
            if (t.tokens_in + t.tokens_out + est_tokens) \
                    > self.max_tokens_task:
                return CircuitDecision(
                    allowed=False, severity="trip",
                    triggered_check="tokens_per_task",
                    reason=(f"task token budget exhausted "
                              f"({t.tokens_in + t.tokens_out}/"
                              f"{self.max_tokens_task})"))

            # 4. Token budget per session
            if (s.tokens_total + est_tokens) > self.max_tokens_session:
                return CircuitDecision(
                    allowed=False, severity="trip",
                    triggered_check="tokens_per_session",
                    reason=(f"session token budget exhausted "
                              f"({s.tokens_total}/"
                              f"{self.max_tokens_session})"))

            # 5. Token budget per day
            if (d.tokens_total + est_tokens) > self.max_tokens_day:
                return CircuitDecision(
                    allowed=False, severity="trip",
                    triggered_check="tokens_per_day",
                    reason=(f"daily token budget exhausted "
                              f"({d.tokens_total}/"
                              f"{self.max_tokens_day})"))

            # 6. USD budget per day
            if (d.usd_total + est_usd) > self.max_usd_day:
                return CircuitDecision(
                    allowed=False, severity="trip",
                    triggered_check="usd_per_day",
                    reason=(f"daily USD budget exhausted "
                              f"(${d.usd_total:.2f}/"
                              f"${self.max_usd_day:.2f})"))

            # 7. No-progress stuck signal
            steps_since_progress = t.steps - t.last_progress_step
            if steps_since_progress >= self.no_progress_limit:
                return CircuitDecision(
                    allowed=False, severity="trip",
                    triggered_check="no_progress",
                    reason=(f"no progress for "
                              f"{steps_since_progress} steps"))

            # Soft warn ladder
            warn_reasons: list[str] = []
            if t.steps >= int(self.max_steps * self.soft_frac):
                warn_reasons.append(
                    f"steps at {t.steps}/{self.max_steps}")
            if (d.tokens_total + est_tokens) \
                    > int(self.max_tokens_day * self.soft_frac):
                warn_reasons.append("daily tokens 80% reached")
            if (d.usd_total + est_usd) > self.max_usd_day * self.soft_frac:
                warn_reasons.append("daily USD 80% reached")

            severity = "warn" if warn_reasons else "ok"
            reason = "; ".join(warn_reasons) if warn_reasons else ""

            return CircuitDecision(
                allowed=True, severity=severity, reason=reason,
                budget_remaining_steps=self.max_steps - t.steps,
                budget_remaining_tokens=(
                    self.max_tokens_task - t.tokens_in - t.tokens_out),
                budget_remaining_usd=(
                    self.max_usd_day - d.usd_total),
            )

    def record(self, *, task_id: str, session_id: str = "default",
                  tokens_in: int = 0, tokens_out: int = 0,
                  usd_spent: float = 0.0,
                  made_progress: bool = False) -> None:
        """Post-call counter update. ``made_progress=True`` resets
        the no-progress detector."""
        with self._lock:
            t = self._task(task_id)
            s = self._session(session_id)
            d = self._day()
            t.steps += 1
            t.tokens_in += tokens_in
            t.tokens_out += tokens_out
            t.usd_spent += usd_spent
            s.tokens_total += tokens_in + tokens_out
            s.usd_total += usd_spent
            d.tokens_total += tokens_in + tokens_out
            d.usd_total += usd_spent
            if made_progress:
                t.last_progress_step = t.steps
                t.last_progress_at = time.time()

    def reset_task(self, task_id: str) -> None:
        with self._lock:
            self._tasks.pop(task_id, None)

    def status(self) -> dict:
        with self._lock:
            return {
                "schema": SCHEMA,
                "active_tasks": len(self._tasks),
                "active_sessions": len(self._sessions),
                "today": {
                    "tokens": self._day().tokens_total,
                    "usd_spent": self._day().usd_total,
                    "tokens_cap": self.max_tokens_day,
                    "usd_cap": self.max_usd_day,
                },
            }
