"""Tier a1 — pure synergy detector.

Given a list of :class:`FeatureSurfaceCard`, produce ranked
:class:`SynergyCandidateCard`s.

Five signals (each contributes to the score):

* ``json_artifact``      — A emits ``--json-out``, B accepts a path/file arg.
* ``in_memory_pipe``     — vocabulary from A's outputs overlaps B's inputs.
* ``shared_schema``      — both reference the same ``atomadic-forge.<x>/v<n>`` schema.
* ``shared_vocabulary``  — Jaccard(vocab_A, vocab_B) ≥ threshold.
* ``phase_omission``     — A.phase_hint == "emit" and B.phase_hint == "ingest"
                            (or analogous predecessor → successor).

The detector ALWAYS proposes pairs (A, B) with A ≠ B and returns them
sorted by descending score.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from ..a0_qk_constants.synergy_types import (
    FeatureSurfaceCard,
    SynergyCandidateCard,
    SynergyKind,
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
    shared_schemas = sorted(set(a["schemas"]) & set(b["schemas"]))
    if shared_schemas:
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


def detect_synergies(features: Iterable[FeatureSurfaceCard]) -> list[SynergyCandidateCard]:
    feats = list(features)
    out: list[SynergyCandidateCard] = []
    seen: set[tuple[str, str, SynergyKind]] = set()
    for i, a in enumerate(feats):
        for b in feats[i + 1:] + feats[:i]:
            for cand in _detect_pair(a, b):
                key = (cand["producer"], cand["consumer"], cand["kind"])
                if key in seen:
                    continue
                seen.add(key)
                out.append(cand)
    out.sort(key=lambda c: c["score"], reverse=True)
    return out
