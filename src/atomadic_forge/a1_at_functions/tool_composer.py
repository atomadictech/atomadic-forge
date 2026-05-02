"""Tier a1 — compose_tools: tool-use planner (Codex #9).

Codex's prescription:

  > Forge has synergy/emergent. Make that agent-native: compose_tools(
  > {goal}). Returns a sequence like:
  >   1. recon
  >   2. summary
  >   3. preflight_change
  >   4. score_patch
  >   5. select_tests
  >   6. certify
  > This makes Forge not just a toolbox, but a planner for tool use.

Pure: maps a goal-keyword to a sequence of MCP tool names with
short rationale per step. Heuristic; the agent picks one or runs
the whole sequence.
"""
from __future__ import annotations

from typing import TypedDict

SCHEMA_VERSION_COMPOSE_V1 = "atomadic-forge.tool_compose/v1"


class ComposedToolStep(TypedDict, total=False):
    step: int
    tool: str
    why: str
    inputs_hint: dict[str, str]


class ComposedToolPlan(TypedDict, total=False):
    schema_version: str
    goal: str
    matched_recipe: str
    steps: list[ComposedToolStep]
    notes: list[str]


# Recipe library — keyword → ordered tool sequence.
_RECIPES: dict[str, dict] = {
    "orient": {
        "match": ("orient", "what is this", "explain", "first time",
                   "context", "onboard", "new repo"),
        "steps": [
            {"tool": "context_pack", "why": "first-call orientation"},
            {"tool": "recon", "why": "tier inventory + symbol counts"},
            {"tool": "audit_list", "why": "what has Forge written before?"},
        ],
    },
    "release_check": {
        "match": ("release", "ship", "publish", "merge", "ready to ship"),
        "steps": [
            {"tool": "wire", "why": "upward-import gate"},
            {"tool": "certify", "why": "score against the 4 axes"},
            {"tool": "score_patch", "why": "review the unified diff"},
            {"tool": "select_tests", "why": "minimum + full test sets"},
        ],
    },
    "fix_violation": {
        "match": ("fix wire", "fix violation", "fix import", "f0042",
                   "f0041", "f0046", "upward import"),
        "steps": [
            {"tool": "wire", "why": "scan with --suggest-repairs"},
            {"tool": "auto_plan",
              "why": "generate ranked action cards"},
            {"tool": "auto_apply",
              "why": "execute applyable cards (rollback-safe)"},
            {"tool": "certify", "why": "verify score recovered"},
        ],
    },
    "before_edit": {
        "match": ("before edit", "before write", "preflight", "guardrail",
                   "i'm about to"),
        "steps": [
            {"tool": "context_pack", "why": "ground the agent first"},
            {"tool": "preflight_change",
              "why": "tier check + forbidden imports + likely tests"},
            {"tool": "select_tests",
              "why": "what to run after the edit"},
        ],
    },
    "verify_patch": {
        "match": ("verify patch", "score diff", "review patch", "is this safe",
                   "review my change", "verify_patch"),
        "steps": [
            {"tool": "score_patch",
              "why": "architecture / api / release / test risk"},
            {"tool": "select_tests",
              "why": "minimum tests for the changed files"},
            {"tool": "wire", "why": "confirm no upward imports introduced"},
            {"tool": "certify", "why": "final repo confidence gate"},
        ],
    },
}


def compose_tools(*, goal: str) -> ComposedToolPlan:
    """Match ``goal`` against the recipe library and return an ordered
    tool-use plan. Falls back to the 'orient' recipe when no keyword
    matches."""
    goal_l = (goal or "").lower()
    normalized_goal = goal_l.replace("_", " ").replace("-", " ")
    matched: str = ""
    chosen: list[dict] | None = None
    for name, recipe in _RECIPES.items():
        normalized_name = name.replace("_", " ").replace("-", " ")
        if normalized_goal.strip() in {name, normalized_name} or any(
            kw in normalized_goal for kw in recipe["match"]
        ):
            matched = name
            chosen = recipe["steps"]
            break
    if chosen is None:
        matched = "orient"
        chosen = _RECIPES["orient"]["steps"]
    steps: list[ComposedToolStep] = []
    for i, s in enumerate(chosen, 1):
        steps.append(ComposedToolStep(
            step=i,
            tool=s["tool"],
            why=s["why"],
            inputs_hint={},
        ))
    notes: list[str] = []
    if not goal:
        notes.append("no goal supplied — defaulted to 'orient' recipe.")
    return ComposedToolPlan(
        schema_version=SCHEMA_VERSION_COMPOSE_V1,
        goal=goal,
        matched_recipe=matched,
        steps=steps,
        notes=notes,
    )
