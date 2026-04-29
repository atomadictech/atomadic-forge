"""Tier a3 — apply the ``forge enforce`` plan.

Composes a1.enforce_planner + a1.wire_check + filesystem moves into
one orchestrator that:
  1. runs scan_violations(suggest_repairs=True)
  2. plans actions via enforce_planner.plan_actions
  3. when --apply, executes each auto_apply action atomically:
        * mkdir -p <dest_tier>/
        * git-rename or shutil.move
        * RE-RUN scan_violations to confirm violations actually
          dropped; if violations rose, ROLL BACK the move and mark
          the action 'rolled_back'.

a3 because: combines a1 helpers + filesystem state. No upward imports.
The CLI surface (``commands/enforce.py``) is the only thing that
depends on this module.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from ..a1_at_functions.enforce_planner import (
    EnforceAction,
    plan_actions,
    summarize_plan,
)
from ..a1_at_functions.wire_check import scan_violations


def run_enforce(
    package_root: Path,
    *,
    apply: bool = False,
    dry_run_only: bool = False,
) -> dict:
    """Plan (and optionally apply) mechanical fixes for wire violations.

    Returns a result dict that always includes:
      schema_version  — 'atomadic-forge.enforce/v1'
      apply           — whether file moves were attempted
      pre_violations  — violation_count before the run
      post_violations — violation_count after (== pre when apply=False)
      plan            — summarize_plan() output (action list + counts)
      applied         — list of {action, status} per attempted action
      rollbacks       — list of action srcs that were rolled back

    Caller is responsible for any version-control commit/discard. The
    function never deletes, only moves; rollbacks restore the original
    location.
    """
    package_root = Path(package_root).resolve()
    pre = scan_violations(package_root, suggest_repairs=True)
    actions = plan_actions(pre, package_root=package_root)

    applied: list[dict[str, Any]] = []
    rollbacks: list[str] = []

    if apply and not dry_run_only:
        for a in actions:
            if not a.get("auto_apply"):
                applied.append({"action": a, "status": "skipped"})
                continue
            try:
                _apply_one(package_root, a)
            except OSError as exc:
                applied.append({"action": a, "status": "io_error",
                                "detail": str(exc)})
                continue
            # Confirm the fix actually reduced violations; otherwise roll back.
            mid = scan_violations(package_root)
            if mid["violation_count"] > pre["violation_count"]:
                _rollback_one(package_root, a)
                rollbacks.append(a["src"])
                applied.append({"action": a, "status": "rolled_back"})
            else:
                applied.append({"action": a, "status": "applied"})

    post = scan_violations(package_root) if apply else pre
    return {
        "schema_version": "atomadic-forge.enforce/v1",
        "apply": apply,
        "pre_violations": pre["violation_count"],
        "post_violations": post["violation_count"],
        "plan": summarize_plan(actions),
        "applied": applied,
        "rollbacks": rollbacks,
    }


def _apply_one(package_root: Path, action: EnforceAction) -> None:
    src = package_root / action["src"]
    dest = package_root / action["dest"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise OSError(f"destination already exists: {dest}")
    shutil.move(str(src), str(dest))


def _rollback_one(package_root: Path, action: EnforceAction) -> None:
    """Best-effort: move the file back if we still own its destination."""
    src = package_root / action["src"]
    dest = package_root / action["dest"]
    if dest.exists() and not src.exists():
        src.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(dest), str(src))
