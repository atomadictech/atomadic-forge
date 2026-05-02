"""Tier a1 — pure synergy detector.

Given a list of :class:`FeatureSurfaceCard`, produce ranked
:class:`SynergyCandidateCard`s.

Eight signals (each contributes to the score):

* ``json_artifact``      — A emits ``--json-out``, B accepts a path/file arg.
* ``in_memory_pipe``     — vocabulary from A's outputs overlaps B's inputs.
* ``shared_schema``      — both reference the same ``atomadic-forge.<x>/v<n>`` schema.
* ``shared_vocabulary``  — Jaccard(vocab_A, vocab_B) ≥ threshold.
* ``phase_omission``     — A.phase_hint is the natural predecessor of B.phase_hint
                            and neither mentions the other (un-wired phase chain).
* ``feedback_loop``      — A produces (materialize) what B certifies; they naturally
                            form an iterate cycle: produce → certify → refine → repeat.
* ``type_pipeline``      — A's ``output_types`` includes a specific named type that
                            appears in B's ``input_types``; zero-cost in-memory pipe.
* ``data_flow_gap``      — A and B both reference the same specific named type in
                            their surfaces but no adapter bridges them yet.

The detector ALWAYS proposes pairs (A, B) with A ≠ B and returns them
sorted by descending score.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from ..a0_qk_constants.synergy_types import (
    FeatureSurfaceCard,
    SynergyCandidateCard,
)

_PHASE_FLOW = [
    "recon", "ingest", "plan", "materialize", "certify", "emit", "register",
]
_PHASE_NEXT = {p: _PHASE_FLOW[i + 1] for i, p in enumerate(_PHASE_FLOW[:-1])}


def _candidate_id(producer: str, consumer: str, kind: str) -> str:
    h = hashlib.sha256(f"{producer}->{consumer}|{kind}".encode()).hexdigest()
    return f"syn-{h[:8]}"


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def _detect_pair(a: FeatureSurfaceCard,
                 b: FeatureSurfaceCard) -> list[SynergyCandidateCard]:
    out: list[SynergyCandidateCard] = []

    # 1. JSON-artifact handoff: producer outputs a JSON, consumer takes a file.
    json_out_signals = [o for o in a["outputs"] if "json" in o or "out" in o]
    file_in_signals = [f for f in b["input_files"] if f]
    if json_out_signals and file_in_signals:
        score_breakdown = {
            "json_handoff": 35,
            "phase_step": 15 if _PHASE_NEXT.get(a["phase_hint"]) == b["phase_hint"] else 0,
            "vocab_overlap": min(20, int(20 * _jaccard(set(a["vocabulary"]),
                                                      set(b["vocabulary"])))),
        }
        score = sum(score_breakdown.values())
        if score >= 30:
            out.append(SynergyCandidateCard(
                candidate_id=_candidate_id(a["name"], b["name"], "json_artifact"),
                producer=a["name"],
                consumer=b["name"],
                kind="json_artifact",
                why=[
                    f"{a['name']} emits {json_out_signals[0]}",
                    f"{b['name']} accepts {file_in_signals[0]}",
                ],
                score=float(score),
                score_breakdown=score_breakdown,
                proposed_adapter_name=f"{a['name']}-then-{b['name']}",
                proposed_summary=(
                    f"Run {a['name']} to emit a JSON artifact, then feed it to "
                    f"{b['name']} for the next phase."
                ),
            ))

    # 2. Shared schema reference — both source files mention the same
    #    atomadic-forge.<x>/v<n> schema string.  Strong signal regardless of phase.
    #    Skip same-module pairs (e.g., two classes in the same file sharing the
    #    same schema constant — that's colocation, not a synergy gap).
    shared_schemas = sorted(set(a["schemas"]) & set(b["schemas"]))
    _same_module = a["module"] == b["module"]
    if shared_schemas and not _same_module:
        score_breakdown = {"schema_match": 50, "schemas_count": min(10, 5 * len(shared_schemas))}
        score = sum(score_breakdown.values())
        out.append(SynergyCandidateCard(
            candidate_id=_candidate_id(a["name"], b["name"], "shared_schema"),
            producer=a["name"],
            consumer=b["name"],
            kind="shared_schema",
            why=[f"both reference schema(s) {', '.join(shared_schemas)}"],
            score=float(score),
            score_breakdown=score_breakdown,
            proposed_adapter_name=f"{a['name']}-feeds-{b['name']}",
            proposed_summary=(
                f"{a['name']} and {b['name']} share schema {shared_schemas[0]} — "
                "wire them as a pipeline rather than running each by hand."
            ),
        ))

    # 3. Phase-omission: producer is at step N, consumer at step N+1, but
    #    neither lists the other in its vocabulary (i.e. no existing mention
    #    of the partner).
    if (_PHASE_NEXT.get(a["phase_hint"]) == b["phase_hint"]
            and a["name"].lower() not in set(b["vocabulary"])
            and b["name"].lower() not in set(a["vocabulary"])):
        score_breakdown = {"phase_step": 30, "missing_mention": 20}
        score = sum(score_breakdown.values())
        out.append(SynergyCandidateCard(
            candidate_id=_candidate_id(a["name"], b["name"], "phase_omission"),
            producer=a["name"],
            consumer=b["name"],
            kind="phase_omission",
            why=[
                f"{a['name']} is at phase '{a['phase_hint']}', "
                f"{b['name']} at '{b['phase_hint']}' — natural successor",
                "neither references the other in help/docstring",
            ],
            score=float(score),
            score_breakdown=score_breakdown,
            proposed_adapter_name=f"{a['name']}-into-{b['name']}",
            proposed_summary=(
                f"{a['name']} produces {a['phase_hint']}-phase output that "
                f"{b['name']} could consume — currently un-piped."
            ),
        ))

    # 4. High-overlap vocabulary (subject-matter pairs working in same area).
    overlap = _jaccard(set(a["vocabulary"]), set(b["vocabulary"]))
    if overlap >= 0.4:
        score_breakdown = {"vocab_overlap": int(40 * overlap)}
        score = sum(score_breakdown.values())
        if score >= 25:
            shared = sorted(set(a["vocabulary"]) & set(b["vocabulary"]))[:6]
            out.append(SynergyCandidateCard(
                candidate_id=_candidate_id(a["name"], b["name"], "shared_vocabulary"),
                producer=a["name"],
                consumer=b["name"],
                kind="shared_vocabulary",
                why=[f"shared vocabulary: {', '.join(shared)}"],
                score=float(score),
                score_breakdown=score_breakdown,
                proposed_adapter_name=f"{a['name']}-with-{b['name']}",
                proposed_summary=(
                    f"{a['name']} and {b['name']} talk about the same domain "
                    f"({', '.join(shared[:3])}) but aren't wired together."
                ),
            ))
    return out


# ── Multi-level detectors (require enriched cards from harvest_multilevel_surfaces) ──

_PRIMITIVE_TYPES = frozenset({
    "str", "int", "float", "bool", "bytes", "None", "NoneType",
    "Any", "Path", "dict", "list", "tuple", "set",
})


def _is_specific_type(t: str) -> bool:
    """Return True for specific named types (not scalar primitives or Any)."""
    base = t.split("[")[0].split("|")[0].strip()
    return base not in _PRIMITIVE_TYPES and len(base) > 3


def _specific_types(type_list: list[str]) -> set[str]:
    return {t for t in type_list if _is_specific_type(t)}


def _detect_feedback_loop(
    a: FeatureSurfaceCard, b: FeatureSurfaceCard
) -> list[SynergyCandidateCard]:
    """Detect certify→materialize feedback loops (the REFINE cycle).

    When A certifies/validates what B produces, they form a natural iterate
    loop: B produces → A certifies → result feeds back to B for refinement.
    Vocabulary overlap confirms they operate on the same artifact.
    """
    _CERTIFY = {"certify", "verify", "audit", "lint"}
    _MAKE    = {"materialize", "plan", "generate", "render", "synthesize"}

    if a["phase_hint"] not in _CERTIFY or b["phase_hint"] not in _MAKE:
        return []

    overlap = _jaccard(set(a["vocabulary"]), set(b["vocabulary"]))
    if overlap < 0.15:
        return []

    shared = sorted(set(a["vocabulary"]) & set(b["vocabulary"]))[:6]
    score_breakdown = {
        "phase_feedback": 35,
        "vocab_overlap": min(15, int(30 * overlap)),
    }
    return [SynergyCandidateCard(
        candidate_id=_candidate_id(b["name"], a["name"], "feedback_loop"),
        producer=b["name"],   # the producer (being certified)
        consumer=a["name"],   # the certifier (drives the loop)
        kind="feedback_loop",
        why=[
            f"{b['name']} produces at phase '{b['phase_hint']}'; "
            f"{a['name']} certifies at phase '{a['phase_hint']}'",
            f"shared vocabulary: {', '.join(shared)}",
            "natural iterate loop: produce → certify → refine → repeat",
        ],
        score=float(sum(score_breakdown.values())),
        score_breakdown=score_breakdown,
        proposed_adapter_name=f"{b['name']}-certify-loop",
        proposed_summary=(
            f"Iterate: run {b['name']} to produce, then {a['name']} to certify; "
            "loop until certify passes or max iterations reached."
        ),
    )]


def _detect_type_pipeline(
    a: FeatureSurfaceCard, b: FeatureSurfaceCard
) -> list[SynergyCandidateCard]:
    """Detect when A's specific output types exactly match B's input types.

    Unlike ``json_artifact`` (file-based handoff) this is an in-memory typed
    pipe — no serialisation needed.  Both cards must have been enriched by
    ``harvest_multilevel_surfaces``.
    """
    a_out = _specific_types(a.get("output_types") or [])  # type: ignore[arg-type]
    b_in  = _specific_types(b.get("input_types")  or [])  # type: ignore[arg-type]
    matched = sorted(a_out & b_in)
    if not matched:
        return []

    tier_a = a.get("tier", "")
    tier_b = b.get("tier", "")
    score_breakdown: dict[str, float] = {
        "type_match": min(60, 20 * len(matched)),
        "tier_cross": 15 if tier_a and tier_b and tier_a != tier_b else 0,
        "specificity": 10 if all(_is_specific_type(t) for t in matched) else 0,
    }
    score = sum(score_breakdown.values())
    if score <= 20:
        return []

    return [SynergyCandidateCard(
        candidate_id=_candidate_id(a["name"], b["name"], "type_pipeline"),
        producer=a["name"],
        consumer=b["name"],
        kind="type_pipeline",
        why=[
            f"producer outputs: {', '.join(matched[:3])}",
            f"consumer accepts: {', '.join(matched[:3])}",
            "specific named-type alignment — in-memory pipe, no JSON overhead",
            *(
                [f"crosses tiers ({tier_a} → {tier_b})"]
                if tier_a and tier_b and tier_a != tier_b else []
            ),
        ],
        score=float(score),
        score_breakdown=score_breakdown,
        proposed_adapter_name=f"{a['name']}-typed-pipe-{b['name']}",
        proposed_summary=(
            f"Typed in-memory pipeline: {a['name']} produces "
            f"{matched[0]} that {b['name']} consumes directly — no file I/O."
        ),
    )]


def _detect_data_flow_gap(
    a: FeatureSurfaceCard, b: FeatureSurfaceCard
) -> list[SynergyCandidateCard]:
    """Detect two features that share a specific named type but have no adapter.

    Both features reference the same concrete type (via ``input_types`` /
    ``output_types`` from enriched harvest) but no ``commands/`` adapter
    bridges them yet.  Only fires for pairs from different tiers (same-tier
    is already covered by type_pipeline or phase_omission).
    """
    tier_a = a.get("tier", "commands")
    tier_b = b.get("tier", "commands")
    if tier_a == tier_b:
        return []

    # Collect all specific type names from both cards
    a_all_types = _specific_types(
        (a.get("input_types") or []) + (a.get("output_types") or [])  # type: ignore[operator]
    )
    b_all_types = _specific_types(
        (b.get("input_types") or []) + (b.get("output_types") or [])  # type: ignore[operator]
    )
    shared_types = sorted(a_all_types & b_all_types)
    if not shared_types:
        return []

    score_breakdown: dict[str, float] = {
        "shared_typed_surface": min(45, 15 * len(shared_types)),
        "tier_gap": 20 if tier_a != tier_b else 0,
    }
    score = sum(score_breakdown.values())
    if score < 35:
        return []

    return [SynergyCandidateCard(
        candidate_id=_candidate_id(a["name"], b["name"], "data_flow_gap"),
        producer=a["name"],
        consumer=b["name"],
        kind="data_flow_gap",
        why=[
            f"shared specific type(s): {', '.join(shared_types[:4])}",
            f"crosses tiers ({tier_a} → {tier_b})",
            "no existing adapter bridges these two typed surfaces",
        ],
        score=float(score),
        score_breakdown=score_breakdown,
        proposed_adapter_name=f"{a['name']}-gap-bridge-{b['name']}",
        proposed_summary=(
            f"{a['name']} and {b['name']} both work with "
            f"{shared_types[0]} but nothing pipes one into the other yet."
        ),
    )]


def detect_synergies(features: Iterable[FeatureSurfaceCard]) -> list[SynergyCandidateCard]:
    feats = list(features)
    out: list[SynergyCandidateCard] = []
    seen: set[tuple[str, str, str]] = set()

    def _add(cand: SynergyCandidateCard) -> None:
        key = (cand["producer"], cand["consumer"], cand["kind"])
        if key not in seen:
            seen.add(key)
            out.append(cand)

    for i, a in enumerate(feats):
        for b in feats[i + 1:] + feats[:i]:
            for cand in _detect_pair(a, b):
                _add(cand)
            # Multi-level detectors: call both orderings so phase checks work.
            for cand in _detect_feedback_loop(a, b):
                _add(cand)
            for cand in _detect_type_pipeline(a, b):
                _add(cand)
            for cand in _detect_data_flow_gap(a, b):
                _add(cand)

    out.sort(key=lambda c: c["score"], reverse=True)
    return out
