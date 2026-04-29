"""Tier a2 — append-only persistence for agent_plan/v1 documents.

Codex's follow-up: 'forge auto step <card-id>' / 'forge auto apply
<plan-id>' need plans to be addressable. This store gives every plan
a stable id (SHA-256 prefix of the plan's structural content) and
persists it under ``.atomadic-forge/plans/<id>.json``. Per-card
state (applied / rejected / skipped) lives in a sibling
``.atomadic-forge/plans/<id>.state.json`` so the plan doc itself
stays append-only and re-emit-safe.

Pure-ish: file I/O scoped under one project_root; no network. The
pure id-derivation lives in a1 (``a1.lineage_chain.canonical_receipt_hash``-style)
but for plans the canonical fields are different — declared inline
here to keep the dependency surface tight.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
from pathlib import Path
from typing import Any


_DIRNAME = ".atomadic-forge"
_PLANS_SUBDIR = "plans"


# Fields that participate in the plan id hash. Mutable / volatile
# fields are excluded so re-emitting the same plan yields the same id.
_PLAN_HASH_INCLUDE: tuple[str, ...] = (
    "schema_version",
    "goal",
    "mode",
    "project_root",
    "top_actions",
)


def compute_plan_id(plan: dict) -> str:
    """SHA-256 hex prefix derived from the plan's structural content."""
    canonical = {k: plan.get(k) for k in _PLAN_HASH_INCLUDE}
    blob = json.dumps(canonical, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def _now_utc_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class PlanStore:
    """Append-only plan + per-card-state persistence."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root).resolve()
        self.dir = self.project_root / _DIRNAME / _PLANS_SUBDIR

    # ---- write paths ---------------------------------------------------

    def save_plan(self, plan: dict) -> str:
        """Persist a plan dict and return its id (idempotent)."""
        plan_id = plan.get("id") or compute_plan_id(plan)
        self.dir.mkdir(parents=True, exist_ok=True)
        # Persist the plan with its id baked in so repeat saves are safe.
        out = dict(plan)
        out.setdefault("id", plan_id)
        out.setdefault("saved_at_utc", _now_utc_iso())
        target = self.dir / f"{plan_id}.json"
        target.write_text(
            json.dumps(out, indent=2, default=str), encoding="utf-8")
        # Initialize state file if missing.
        state_path = self._state_path(plan_id)
        if not state_path.exists():
            state_path.write_text(
                json.dumps({
                    "schema_version": "atomadic-forge.plan_state/v1",
                    "plan_id": plan_id,
                    "events": [],
                }, indent=2),
                encoding="utf-8",
            )
        return plan_id

    def record_card_event(
        self,
        plan_id: str,
        *,
        card_id: str,
        status: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        """Append a per-card outcome (applied / rejected / skipped /
        rolled_back). Pure append; never rewrites prior events."""
        state = self.load_state(plan_id) or {
            "schema_version": "atomadic-forge.plan_state/v1",
            "plan_id": plan_id, "events": [],
        }
        state["events"].append({
            "ts_utc": _now_utc_iso(),
            "card_id": card_id,
            "status": status,
            "detail": detail or {},
        })
        self._state_path(plan_id).write_text(
            json.dumps(state, indent=2, default=str), encoding="utf-8")

    # ---- read paths ----------------------------------------------------

    def load_plan(self, plan_id: str) -> dict | None:
        target = self.dir / f"{plan_id}.json"
        if not target.exists():
            return None
        try:
            return json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def load_state(self, plan_id: str) -> dict | None:
        target = self._state_path(plan_id)
        if not target.exists():
            return None
        try:
            return json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def list_plans(self) -> list[dict]:
        """Return summaries newest-first by saved_at_utc."""
        if not self.dir.exists():
            return []
        out: list[dict] = []
        for f in self.dir.glob("*.json"):
            if f.name.endswith(".state.json"):
                continue
            try:
                doc = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            out.append({
                "plan_id": doc.get("id", f.stem),
                "verdict": doc.get("verdict", "?"),
                "goal": doc.get("goal", ""),
                "mode": doc.get("mode", ""),
                "action_count": doc.get("action_count", 0),
                "applyable_count": doc.get("applyable_count", 0),
                "saved_at_utc": doc.get("saved_at_utc", ""),
            })
        out.sort(key=lambda d: d["saved_at_utc"], reverse=True)
        return out

    def card_status(self, plan_id: str, card_id: str) -> str:
        """Return the latest status for ``card_id`` in plan, or
        'unapplied' when no event has been recorded."""
        state = self.load_state(plan_id)
        if not state:
            return "unapplied"
        for ev in reversed(state.get("events", [])):
            if ev.get("card_id") == card_id:
                return ev.get("status", "unapplied")
        return "unapplied"

    # ---- helpers -------------------------------------------------------

    def _state_path(self, plan_id: str) -> Path:
        return self.dir / f"{plan_id}.state.json"
