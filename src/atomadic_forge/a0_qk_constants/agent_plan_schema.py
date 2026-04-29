"""Tier a0 — agent-plan/v1 wire-format schema.

Direct response to Codex's follow-up directive after using earlier
Forge releases:

  > 'Make Forge output \"next best action cards.\" The active agent
  >  then does what agents are good at: inspect files, edit
  >  carefully, run tests, decide whether the suggestion was
  >  actually good. Forge stays the architectural conscience and
  >  candidate generator.'

Where ``agent_summary/v1`` (prior commit) was a compact dashboard,
``agent_plan/v1`` is the operational manifest the agent actually
executes against. Each ``AgentActionCard`` is a bounded, named,
applyable proposal: id, why, write_scope, validation commands,
risk, and whether Forge itself can apply it via existing verbs.

a0 invariant: this file holds only TypedDicts + constant strings.
No logic. Imports limited to ``__future__`` and ``typing``.
"""
from __future__ import annotations

from typing import Literal, TypedDict


SCHEMA_VERSION_AGENT_PLAN_V1 = "atomadic-forge.agent_plan/v1"
SCHEMA_VERSION_AGENT_ACTION_V1 = "atomadic-forge.agent_action/v1"


# Card kinds — pinned for downstream filtering. Adding a new kind is
# additive; renaming or removing one is a major schema bump.
ACTION_KINDS: tuple[str, ...] = (
    "operational",      # CI / changelog / README / tests-present gaps
    "architectural",    # wire violations, F-coded
    "composition",      # emergent — symbol chains
    "synthesis",        # synergy — feature-pair adapters
    "release",          # final-mile (sign Receipt, gate certify ≥ N)
)

# Plan modes — the agent declares what it wants to do.
PLAN_MODES: tuple[str, ...] = (
    "improve",   # operate on the existing repo in-place
    "absorb",    # take a flat repo and emit a new tier-organized package
)

# Risk levels — drives the agent's confirmation policy.
RISK_LEVELS: tuple[str, ...] = ("low", "medium", "high")


class AgentActionCard(TypedDict, total=False):
    """One bounded proposal for the agent to inspect, edit, apply.

    Required fields:
      schema_version  — atomadic-forge.agent_action/v1
      id              — stable slug (e.g. 'fix-wire-F0042-helper-py');
                        the agent uses this in `auto step <id>`
      kind            — one of ACTION_KINDS
      title           — one-line human label
      why             — 1-3 sentence justification (concrete, no fluff)
      risk            — one of RISK_LEVELS
      applyable       — true when Forge has a verb that can execute this
                        unattended; false means hand to the agent

    Optional but strongly encouraged:
      write_scope     — list of file globs the action will touch
      commands        — list of validation commands the agent should
                        run AFTER applying (pytest, forge wire, etc.)
      related_fcodes  — F-codes this action resolves
      next_command    — the single shell command to execute the action
      sample_path     — representative file (when applicable)
      score_delta_estimate — expected certify score increase (heuristic)
    """
    schema_version: str
    id: str
    kind: str
    title: str
    why: str
    risk: str
    applyable: bool
    write_scope: list[str]
    commands: list[str]
    related_fcodes: list[str]
    next_command: str
    sample_path: str | None
    score_delta_estimate: int


class AgentPlan(TypedDict, total=False):
    """The plan envelope: ordered top-N actions + meta.

    Required:
      schema_version, generated_at_utc, verdict, goal, mode,
      top_actions, project_root.
    """
    schema_version: str
    generated_at_utc: str
    verdict: Literal["PASS", "FAIL", "REFINE", "QUARANTINE"]
    goal: str
    mode: str                    # one of PLAN_MODES
    project_root: str
    top_actions: list[AgentActionCard]
    action_count: int            # full count regardless of top_n cap
    applyable_count: int
    next_command: str
    # Codex feedback: surface the certify score on the plan envelope
    # so MCP _summary digests don't have to guess. None when no
    # certify_report fed the plan.
    score: float | None
    # Provenance — what scans fed into this plan.
    sources: dict[str, str]      # {source_name: schema_version}


REQUIRED_PLAN_FIELDS: tuple[str, ...] = (
    "schema_version",
    "generated_at_utc",
    "verdict",
    "goal",
    "mode",
    "project_root",
    "top_actions",
)
