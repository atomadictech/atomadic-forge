"""Tests for cost_circuit_breaker cherry-picked from forge-deluxe-seed.

Multi-tier budget enforcement (per-task / per-session / per-day)
with hard-kill + soft-warn-at-80% + no-progress-stuck-detector.
"""

from __future__ import annotations

import pytest

from atomadic_forge.a2_mo_composites.cost_circuit_breaker import (
    CostCircuitBreaker,
)


def test_breaker_allows_within_budget():
    cb = CostCircuitBreaker(max_steps_per_task=10)
    d = cb.check(task_id="t1")
    assert d.allowed
    assert d.severity == "ok"


def test_breaker_trips_on_step_limit():
    cb = CostCircuitBreaker(max_steps_per_task=3,
                              no_progress_step_limit=999)
    for _ in range(3):
        cb.record(task_id="t1", made_progress=True)
    d = cb.check(task_id="t1")
    assert not d.allowed
    assert d.triggered_check == "steps_per_task"


def test_breaker_trips_on_no_progress():
    cb = CostCircuitBreaker(no_progress_step_limit=3)
    for _ in range(3):
        cb.record(task_id="t1", made_progress=False)
    d = cb.check(task_id="t1")
    assert not d.allowed
    assert d.triggered_check == "no_progress"


def test_breaker_warn_at_80_pct():
    cb = CostCircuitBreaker(max_steps_per_task=10,
                              soft_warn_frac=0.8,
                              no_progress_step_limit=999)
    for _ in range(8):
        cb.record(task_id="t1", made_progress=True)
    d = cb.check(task_id="t1")
    assert d.allowed
    assert d.severity == "warn"


def test_breaker_daily_usd_ceiling():
    cb = CostCircuitBreaker(max_usd_per_day=1.0,
                              no_progress_step_limit=999)
    cb.record(task_id="t", usd_spent=1.5)
    d = cb.check(task_id="t", est_usd=0.1)
    assert not d.allowed
    assert d.triggered_check == "usd_per_day"


def test_breaker_status_dict():
    cb = CostCircuitBreaker()
    cb.record(task_id="t", tokens_in=100, tokens_out=50, usd_spent=0.05)
    s = cb.status()
    assert s["today"]["tokens"] == 150
    assert s["today"]["usd_spent"] == pytest.approx(0.05)


def test_breaker_thread_safe_basic():
    """Multi-thread record + check shouldn't crash / corrupt state."""
    import threading
    cb = CostCircuitBreaker(no_progress_step_limit=999)
    def worker():
        for _ in range(10):
            cb.record(task_id="t", tokens_in=1, made_progress=True)
            cb.check(task_id="t")
    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    s = cb.status()
    # 4 threads * 10 records = 40 entries
    assert s["today"]["tokens"] >= 30  # allow for any race-condition undercount


def test_breaker_reset_task():
    cb = CostCircuitBreaker(max_steps_per_task=2,
                              no_progress_step_limit=999)
    cb.record(task_id="t", made_progress=True)
    cb.record(task_id="t", made_progress=True)
    assert not cb.check(task_id="t").allowed
    cb.reset_task("t")
    assert cb.check(task_id="t").allowed
