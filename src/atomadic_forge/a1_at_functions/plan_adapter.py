"""Tier a1 — adapt_plan: capability-aware card filtering (Codex #8).

Codex's prescription:

  > Different agents have different strengths: some can edit, some
  > can only review, some can run commands, some cannot access
  > network. adapt_plan({agent_capabilities}) tailors action cards:
  > 'agent can apply', 'agent should ask human', 'agent should
  > delegate', 'agent should only report'.

Pure: takes an existing AgentPlan + capability set, returns a new
plan with each card's recommended_handling field populated.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


SCHEMA_VERSION_ADAPTED_PLAN_V1 = "atomadic-forge.agent_plan_adapted/v1"


# Known agent capability slugs.
_KNOWN_CAPABILITIES: frozenset[str] = frozenset({
    "edit_files",       # can write to disk
    "run_commands",     # can shell out
    "network",          # can reach external HTTP
    "review",           # can analyse but not modify
    "delegate",         # can spawn other agents
})


def _handling_for(card: dict, *, capabilities: set[str]) -> str:
    """Map a card to one of:
      apply           — agent has every capability the card needs
      delegate        — agent should spawn / invoke another tool
      ask_human       — card needs out-of-band judgement
      report_only     — agent should surface, not act
    """
    applyable = bool(card.get("applyable"))
    if not applyable:
        return "ask_human"
    kind = card.get("kind", "")
    risk = card.get("risk", "high")
    if kind == "synthesis" and "delegate" in capabilities:
        return "delegate"
    if kind in ("operational", "architectural"):
        if "edit_files" in capabilities and "run_commands" in capabilities:
            return "apply"
        if "edit_files" in capabilities:
            return "apply"
        return "report_only"
    if risk == "high":
        return "ask_human"
    return "report_only" if "edit_files" not in capabilities else "apply"


def adapt_plan(plan: dict, *, agent_capabilities: list[str]) -> dict:
    """Return a new plan with per-card 'recommended_handling' set.

    Pure: input is not mutated.
    """
    caps = {c for c in agent_capabilities or [] if c in _KNOWN_CAPABILITIES}
    out = deepcopy(plan)
    for card in out.get("top_actions", []):
        card["recommended_handling"] = _handling_for(card, capabilities=caps)
    out["schema_version"] = SCHEMA_VERSION_ADAPTED_PLAN_V1
    out["agent_capabilities"] = sorted(caps)
    out["unknown_capabilities"] = sorted(
        c for c in (agent_capabilities or []) if c not in _KNOWN_CAPABILITIES
    )
    counts: dict[str, int] = {}
    for card in out.get("top_actions", []):
        h = card["recommended_handling"]
        counts[h] = counts.get(h, 0) + 1
    out["handling_counts"] = counts
    return out
