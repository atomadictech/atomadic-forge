"""Tier a3 — apply ONE card / ALL applyable cards from an agent_plan.

Codex's prescription: 'agent picks one card, runs its next_command'.
This module is the bounded-execution helper Forge supplies so the
agent doesn't have to reimplement card-routing.

Routing strategy:
  * architectural cards with auto_fixable F-codes → forge enforce
    --apply against the card's write_scope; Forge enforce already
    rolls back if violations rise.
  * operational F0050 (docs missing) → write a minimal README.md
    using the card's write_scope[0].
  * operational F0051 (tests missing) → not yet implemented; the
    apply call records 'skipped' with a 'manual_required' reason.
  * synthesis / composition cards → not yet implemented; require
    forge synergy implement / forge emergent synthesize integration.

Every apply attempt records a per-card event in the plan store
(applied / skipped / rolled_back / failed) so the agent (and Lane F
W26 audit trail) can reason about what was done.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..a0_qk_constants.agent_plan_schema import AgentActionCard
from ..a2_mo_composites.plan_store import PlanStore
from .forge_enforce import run_enforce

_ARCHITECTURAL_AUTO_FIX_FCODES: frozenset[str] = frozenset({
    "F0041", "F0042", "F0043", "F0044", "F0045", "F0046",
})


def _find_card(plan: dict, card_id: str) -> AgentActionCard | None:
    for card in plan.get("top_actions", []) or []:
        if card.get("id") == card_id:
            return card
    return None


def _apply_architectural_card(
    project_root: Path,
    card: AgentActionCard,
    *,
    apply: bool,
) -> dict[str, Any]:
    """Route an F0041..F0046 card through forge enforce.

    The card's write_scope identifies the file under threat; we run
    enforce against its package root so the rollback-safe orchestrator
    handles it. apply=False -> dry-run; apply=True -> actually move.
    """
    write_scope = card.get("write_scope") or []
    if not write_scope:
        return {"status": "failed",
                "detail": {"reason": "card has empty write_scope"}}
    rel = write_scope[0]
    # Walk up from the file to the nearest tier-organized package.
    file_path = (project_root / rel).resolve()
    candidate = file_path.parent
    pkg_root: Path | None = None
    while candidate != candidate.parent:
        # A package root contains tier directories.
        if any((candidate / t).is_dir() for t in (
                "a0_qk_constants", "a1_at_functions", "a2_mo_composites",
                "a3_og_features", "a4_sy_orchestration",
        )):
            pkg_root = candidate
            break
        candidate = candidate.parent
    if pkg_root is None:
        return {"status": "failed",
                "detail": {"reason": "no tier-organized package root above "
                                       f"{rel}"}}
    report = run_enforce(pkg_root, apply=apply)
    pre, post = report["pre_violations"], report["post_violations"]
    if not apply:
        return {"status": "dry_run",
                "detail": {"pre_violations": pre, "post_violations": post,
                            "plan": report["plan"]}}
    if post < pre:
        return {"status": "applied",
                "detail": {"pre_violations": pre, "post_violations": post,
                            "applied": report["applied"]}}
    if post > pre:
        return {"status": "rolled_back",
                "detail": {"pre_violations": pre, "post_violations": post,
                            "rollbacks": report["rollbacks"]}}
    return {"status": "noop",
            "detail": {"pre_violations": pre, "post_violations": post}}


def _apply_docs_card(
    project_root: Path,
    card: AgentActionCard,
    *,
    apply: bool,
) -> dict[str, Any]:
    """F0050 minimal-README writer.

    The card's write_scope[0] tells us where the README belongs.
    apply=True writes a one-line H1 + paragraph; apply=False is a
    no-op dry-run.
    """
    rel = (card.get("write_scope") or ["README.md"])[0]
    target = (project_root / rel).resolve()
    if target.exists():
        return {"status": "skipped",
                "detail": {"reason": f"{rel} already exists"}}
    if not apply:
        return {"status": "dry_run",
                "detail": {"would_write": str(target.relative_to(project_root))}}
    pkg = card.get("sample_path") or project_root.name
    body = (
        f"# {pkg}\n\n"
        f"_Stub README written by `forge plan-apply` "
        f"({card.get('id')})._\n\n"
        f"Replace this with a real overview before shipping.\n"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return {"status": "applied",
            "detail": {"written": str(target.relative_to(project_root))}}


def _route_card(
    project_root: Path,
    card: AgentActionCard,
    *,
    apply: bool,
) -> dict[str, Any]:
    if not card.get("applyable"):
        return {"status": "skipped",
                "detail": {"reason": "card.applyable=False (review_manually)"}}
    related = set(card.get("related_fcodes") or [])
    if related & _ARCHITECTURAL_AUTO_FIX_FCODES:
        return _apply_architectural_card(project_root, card, apply=apply)
    if "F0050" in related:
        return _apply_docs_card(project_root, card, apply=apply)
    # F0051 / synthesis / composition: not yet implementable.
    return {
        "status": "skipped",
        "detail": {
            "reason": "card kind not yet implementable in plan-apply v1",
            "kind": card.get("kind"),
            "related_fcodes": list(related),
        },
    }


def apply_card(
    project_root: Path,
    plan: dict,
    card_id: str,
    *,
    apply: bool = False,
) -> dict[str, Any]:
    """Apply a single card from a plan.

    Returns a result dict with shape:
      {schema_version, plan_id, card_id, apply, status, detail}

    Always records the event to the plan store regardless of apply
    flag (dry runs included) so the audit trail is complete.
    """
    project_root = Path(project_root).resolve()
    plan_id = plan.get("id") or "<unsaved>"
    card = _find_card(plan, card_id)
    if card is None:
        return {
            "schema_version": "atomadic-forge.plan_apply/v1",
            "plan_id": plan_id, "card_id": card_id, "apply": apply,
            "status": "failed",
            "detail": {"reason": f"card_id {card_id!r} not in plan"},
        }
    outcome = _route_card(project_root, card, apply=apply)
    PlanStore(project_root).record_card_event(
        plan_id, card_id=card_id,
        status=outcome["status"],
        detail={"apply": apply, **outcome.get("detail", {})},
    )
    return {
        "schema_version": "atomadic-forge.plan_apply/v1",
        "plan_id": plan_id, "card_id": card_id, "apply": apply,
        **outcome,
    }


def apply_all_applyable(
    project_root: Path,
    plan: dict,
    *,
    apply: bool = False,
) -> dict[str, Any]:
    """Iterate applyable cards in plan order; collect results.

    Stops on the first ``rolled_back`` or ``failed`` outcome — the
    agent should inspect that result before proceeding rather than
    cascading further mutations against a now-suspect repo.
    """
    project_root = Path(project_root).resolve()
    plan_id = plan.get("id") or "<unsaved>"
    results: list[dict] = []
    halted = None
    for card in plan.get("top_actions", []) or []:
        if not card.get("applyable"):
            continue
        outcome = apply_card(project_root, plan, card["id"], apply=apply)
        results.append(outcome)
        if outcome["status"] in {"rolled_back", "failed"}:
            halted = outcome["status"]
            break
    return {
        "schema_version": "atomadic-forge.plan_apply_all/v1",
        "plan_id": plan_id, "apply": apply,
        "results": results,
        "halted_on": halted,
        "applied_count": sum(1 for r in results if r["status"] == "applied"),
        "skipped_count": sum(1 for r in results if r["status"] == "skipped"),
    }
