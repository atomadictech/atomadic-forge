"""Test synergy surface extractor + detector + per-kind renderer."""
from __future__ import annotations

import ast

from atomadic_forge.a0_qk_constants.synergy_types import (
    FeatureSurfaceCard,
    SynergyCandidateCard,
)
from atomadic_forge.a1_at_functions.synergy_detect import detect_synergies
from atomadic_forge.a1_at_functions.synergy_render import render_synergy_adapter


def _card(**overrides) -> FeatureSurfaceCard:
    base: FeatureSurfaceCard = FeatureSurfaceCard(
        name=overrides.get("name", "x"),
        module=overrides.get("module", "pkg.x"),
        help_text=overrides.get("help_text", ""),
        inputs=overrides.get("inputs", []),
        input_files=overrides.get("input_files", []),
        outputs=overrides.get("outputs", []),
        output_files=overrides.get("output_files", []),
        schemas=overrides.get("schemas", []),
        vocabulary=overrides.get("vocabulary", []),
        phase_hint=overrides.get("phase_hint", "misc"),
    )
    return base


def test_json_artifact_synergy_detected():
    producer = _card(name="scout",
                     outputs=["json-out", "save"],
                     output_files=["scout.json"],
                     phase_hint="recon")
    consumer = _card(name="emergent",
                     inputs=["report-path"],
                     input_files=["report.json"],
                     phase_hint="ingest")
    cands = detect_synergies([producer, consumer])
    kinds = {c["kind"] for c in cands}
    assert "json_artifact" in kinds


def test_shared_schema_synergy():
    producer = _card(name="cherry", schemas=["atomadic-forge.cherry/v1"])
    consumer = _card(name="register", schemas=["atomadic-forge.cherry/v1"])
    cands = detect_synergies([producer, consumer])
    assert any(c["kind"] == "shared_schema" for c in cands)


def test_phase_omission_synergy():
    producer = _card(name="ingest", phase_hint="ingest", vocabulary=["foo"])
    consumer = _card(name="plan", phase_hint="plan", vocabulary=["bar"])
    cands = detect_synergies([producer, consumer])
    assert any(c["kind"] == "phase_omission" for c in cands)


def test_each_renderer_emits_valid_python():
    """Per-kind templates must produce parseable Python."""
    base = SynergyCandidateCard(
        candidate_id="syn-test", producer="alpha", consumer="beta",
        kind="json_artifact", why=["test"],
        score=80.0, score_breakdown={"x": 80},
        proposed_adapter_name="alpha-then-beta",
        proposed_summary="run alpha then beta",
    )
    for kind in ("json_artifact", "in_memory_pipe", "phase_omission",
                 "shared_schema", "shared_vocabulary"):
        card = dict(base)
        card["kind"] = kind  # type: ignore[typeddict-item]
        src = render_synergy_adapter(card)  # type: ignore[arg-type]
        ast.parse(src)  # raises SyntaxError on regression — caught the v1 unclosed-bracket bug
