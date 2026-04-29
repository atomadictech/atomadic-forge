"""Tier a1 — pure agent_plan/v1 emitter.

Consumes one or more Forge reports and emits an ordered
``AgentPlan``. Codex's prescription:

  > 'observe → propose cards → agent chooses/edits → apply bounded
  >  change → certify → next card'

This module owns the 'propose cards' step. The agent owns 'choose
/ edit / apply'. Forge provides the bounded-change verbs (auto,
enforce, certify, etc.) the cards point at.

Ranking: same deterministic order as ``agent_summary``:
  1. operational + applyable + low risk  (cheapest wins first)
  2. architectural + auto_fixable        (forge enforce path)
  3. release-blocking certify axes
  4. high-confidence synthesis (synergy adapters)
  5. composition opportunities (emergent chains)
  6. medium-risk architectural (review_manually)
"""
from __future__ import annotations

import datetime as _dt
from typing import Any

from ..a0_qk_constants.agent_plan_schema import (
    REQUIRED_PLAN_FIELDS,
    SCHEMA_VERSION_AGENT_ACTION_V1,
    SCHEMA_VERSION_AGENT_PLAN_V1,
    AgentActionCard,
    AgentPlan,
)
from ..a0_qk_constants.error_codes import (
    fcode_for_certify_axis,
    fcode_for_tier_violation,
    get_fcode,
)


_KIND_RANK = {
    "operational":  0,
    "architectural": 1,
    "release":      2,
    "synthesis":    3,
    "composition":  4,
}
_RISK_RANK = {"low": 0, "medium": 1, "high": 2}


def _now_utc_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(*parts: str) -> str:
    """Build a stable card id from its parts. Lowercased; non-alnum
    collapsed to '-'."""
    raw = "-".join(p for p in parts if p)
    out: list[str] = []
    prev_dash = False
    for ch in raw.lower():
        if ch.isalnum() or ch == ".":
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    return "".join(out).strip("-")[:80] or "action"


def _operational_cards(certify_report: dict | None,
                       *, package: str | None) -> list[AgentActionCard]:
    cards: list[AgentActionCard] = []
    if not certify_report:
        return cards
    pkg_label = package or "your_pkg"

    if not certify_report.get("documentation_complete", True):
        cards.append(AgentActionCard(
            schema_version=SCHEMA_VERSION_AGENT_ACTION_V1,
            id=_slug("docs", pkg_label),
            kind="operational",
            title="Add a README so the documentation axis passes",
            why="forge certify documentation_complete=False blocks any "
                 "score above 75/100; a one-paragraph README is worth +25.",
            risk="low",
            applyable=False,
            write_scope=["README.md"],
            commands=[f"forge certify . --package {pkg_label}"],
            related_fcodes=[fcode_for_certify_axis("documentation_complete")],
            next_command=f"echo '# {pkg_label}' > README.md",
            sample_path=None,
            score_delta_estimate=25,
        ))
    if not certify_report.get("tests_present", True):
        cards.append(AgentActionCard(
            schema_version=SCHEMA_VERSION_AGENT_ACTION_V1,
            id=_slug("tests", pkg_label),
            kind="operational",
            title="Add a tests/ directory so the tests axis passes",
            why="forge certify tests_present=False; even one smoke test "
                 "(import-only) clears the axis and unlocks +25.",
            risk="low",
            applyable=False,
            write_scope=["tests/test_smoke.py", "tests/__init__.py"],
            commands=[f"forge certify . --package {pkg_label}",
                      "python -m pytest"],
            related_fcodes=[fcode_for_certify_axis("tests_present")],
            next_command=(
                f"mkdir -p tests && printf 'import {pkg_label}\\n' > "
                "tests/test_smoke.py"
            ),
            sample_path=None,
            score_delta_estimate=25,
        ))
    return cards


def _architectural_cards(wire_report: dict | None,
                         *, package_root: str | None) -> list[AgentActionCard]:
    cards: list[AgentActionCard] = []
    if not wire_report:
        return cards
    violations = wire_report.get("violations") or []
    if not violations:
        return cards
    by_fcode_file: dict[tuple[str, str], list[dict]] = {}
    for v in violations:
        code = v.get("f_code") or fcode_for_tier_violation(
            v.get("from_tier", ""), v.get("to_tier", ""))
        key = (code, v.get("file", ""))
        by_fcode_file.setdefault(key, []).append(v)
    for (code, file_path), group in by_fcode_file.items():
        entry = get_fcode(code)
        applyable = bool(entry and entry.get("auto_fixable"))
        if applyable:
            risk = "low"
            cmd = (f"forge enforce {package_root or 'src/your_pkg'} "
                   "--apply  # rolls back if violations rise")
            why = (
                f"{file_path} carries {len(group)} {code} violation(s). "
                "auto_fixable=True; forge enforce can move the file up "
                "to the higher tier and atomically roll back if the "
                "move increases violations."
            )
        else:
            risk = "medium"
            cmd = (f"# review {file_path}: invert the import direction "
                   "or extract the symbol down to a lower tier.")
            why = (
                f"{file_path} carries {len(group)} {code} violation(s). "
                "Mechanical fix is unsafe (a0 special-case or "
                "non-canonical tier shape); requires agent judgement."
            )
        cards.append(AgentActionCard(
            schema_version=SCHEMA_VERSION_AGENT_ACTION_V1,
            id=_slug("fix", code, file_path),
            kind="architectural",
            title=(entry["title"] if entry else f"{code} on {file_path}"),
            why=why,
            risk=risk,
            applyable=applyable,
            write_scope=[file_path],
            commands=[
                f"forge wire {package_root or 'src/your_pkg'} "
                "--suggest-repairs",
                "python -m pytest",
            ],
            related_fcodes=[code],
            next_command=cmd,
            sample_path=file_path,
            score_delta_estimate=10 if applyable else 5,
        ))
    return cards


def _synthesis_cards(synergy_report: dict | None,
                     *, top_n: int = 3) -> list[AgentActionCard]:
    cards: list[AgentActionCard] = []
    if not synergy_report:
        return cards
    candidates = synergy_report.get("candidates") or []
    for c in candidates[:top_n]:
        cid = c.get("id") or _slug("syn",
                                     c.get("producer", ""),
                                     c.get("consumer", ""))
        cards.append(AgentActionCard(
            schema_version=SCHEMA_VERSION_AGENT_ACTION_V1,
            id=_slug("synergy", cid),
            kind="synthesis",
            title=f"Synergy adapter: {c.get('producer', '?')} → "
                   f"{c.get('consumer', '?')}",
            why=(c.get("reason")
                 or "forge synergy detected a high-confidence "
                    "feature-pair compose-by-law match."),
            risk="medium",
            applyable=True,
            write_scope=[],
            commands=[f"forge synergy implement {cid}",
                      "python -m pytest"],
            related_fcodes=[],
            next_command=f"forge synergy implement {cid}",
            sample_path=None,
            score_delta_estimate=0,
        ))
    return cards


def _composition_cards(emergent_report: dict | None,
                       *, top_n: int = 3) -> list[AgentActionCard]:
    cards: list[AgentActionCard] = []
    if not emergent_report:
        return cards
    candidates = emergent_report.get("candidates") or []
    for c in candidates[:top_n]:
        cid = c.get("id") or _slug("emg", *(s for s in c.get("chain", [])))
        chain = c.get("chain") or []
        cards.append(AgentActionCard(
            schema_version=SCHEMA_VERSION_AGENT_ACTION_V1,
            id=_slug("emergent", cid),
            kind="composition",
            title=f"Compose: {' → '.join(chain) if chain else cid}",
            why=(c.get("reason")
                 or "forge emergent surfaced a hidden composition chain."),
            risk="medium",
            applyable=True,
            write_scope=[],
            commands=[f"forge emergent synthesize {cid}",
                      "python -m pytest"],
            related_fcodes=[],
            next_command=f"forge emergent synthesize {cid}",
            sample_path=None,
            score_delta_estimate=0,
        ))
    return cards


def _rank(card: AgentActionCard) -> tuple[int, int, int, str]:
    """Stable card rank — see module docstring."""
    return (
        0 if card.get("applyable") else 1,
        _KIND_RANK.get(card.get("kind", "operational"), 99),
        _RISK_RANK.get(card.get("risk", "high"), 99),
        card.get("id", ""),
    )


def emit_agent_plan(
    *,
    project_root: str,
    goal: str,
    mode: str = "improve",
    wire_report: dict | None = None,
    certify_report: dict | None = None,
    emergent_report: dict | None = None,
    synergy_report: dict | None = None,
    package: str | None = None,
    top_n: int = 7,
) -> AgentPlan:
    """Build an agent_plan/v1 from any combination of Forge reports.

    Caller is responsible for running the source scans (cheap to do
    in parallel; a3 ``run_auto_plan`` wraps the orchestration).
    """
    if top_n < 1:
        raise ValueError("top_n must be >= 1")
    if mode not in ("improve", "absorb"):
        raise ValueError(f"mode must be 'improve' | 'absorb', got {mode!r}")

    cards: list[AgentActionCard] = []
    cards.extend(_operational_cards(certify_report, package=package))
    cards.extend(_architectural_cards(wire_report,
                                        package_root=package or project_root))
    cards.extend(_synthesis_cards(synergy_report))
    cards.extend(_composition_cards(emergent_report))
    cards.sort(key=_rank)

    applyable = sum(1 for c in cards if c.get("applyable"))
    score = float((certify_report or {}).get("score", 0.0))
    if wire_report and wire_report.get("verdict") == "PASS" and score >= 100:
        verdict = "PASS"
    elif not cards:
        verdict = "PASS"
    else:
        verdict = "FAIL"

    next_command = (cards[0]["next_command"] if cards
                    else "# already PASSing — no next action.")

    sources: dict[str, str] = {}
    if wire_report:
        sources["wire"] = wire_report.get("schema_version", "")
    if certify_report:
        sources["certify"] = certify_report.get("schema_version", "")
    if emergent_report:
        sources["emergent"] = emergent_report.get("schema_version", "")
    if synergy_report:
        sources["synergy"] = synergy_report.get("schema_version", "")

    plan: AgentPlan = AgentPlan(
        schema_version=SCHEMA_VERSION_AGENT_PLAN_V1,
        generated_at_utc=_now_utc_iso(),
        verdict=verdict,  # type: ignore[typeddict-item]
        goal=goal,
        mode=mode,
        project_root=str(project_root),
        top_actions=list(cards[:top_n]),
        action_count=len(cards),
        applyable_count=applyable,
        next_command=next_command,
        sources=sources,
    )
    # Defensive — TypedDict isn't enforced at runtime.
    for f in REQUIRED_PLAN_FIELDS:
        if f not in plan:
            raise RuntimeError(
                f"agent_plan emitter built a plan missing required "
                f"field {f!r} — schema/emitter drift"
            )
    return plan
