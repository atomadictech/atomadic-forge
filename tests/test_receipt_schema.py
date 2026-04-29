"""Tier verification — Golden Path Lane A W0: Receipt v1 schema.

The schema lives in a0 as TypedDict declarations (Python's structural
type checker doesn't enforce TypedDict at runtime). These tests pin
the wire-format contract structurally so that:

  * the required-fields list is treated as a published commitment
  * the verdict enum stays synchronized with UEP v20's four values
  * the documented version constants point at the regex routing key
  * the example in docs/RECEIPT.md remains a valid v1 instance

Lane A W1 will follow with receipt_emitter.py (the producer) and
card_renderer.py (the renderer); those modules will gain their own
test files. This file pins the *contract* the producers must respect.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from atomadic_forge.a0_qk_constants.receipt_schema import (
    REQUIRED_RECEIPT_V1_FIELDS,
    SCHEMA_VERSION_V1,
    SCHEMA_VERSION_V1_1,
    SCHEMA_VERSION_V1_2,
    SCHEMA_VERSION_V2,
    VALID_VERDICTS,
    ForgeReceiptV1,
)

_SCHEMA_REGEX = re.compile(r"^atomadic-forge\.receipt/v\d+(?:\.\d+)?$")


# ---- schema version constants -------------------------------------------

def test_schema_version_constants_match_routing_regex() -> None:
    """The dispatcher regex documented in RECEIPT.md must accept every
    declared version constant. Future v1.3 / v3.0 / etc. additions
    must update this regex if and only if the format changes."""
    for v in (SCHEMA_VERSION_V1, SCHEMA_VERSION_V1_1,
              SCHEMA_VERSION_V1_2, SCHEMA_VERSION_V2):
        assert _SCHEMA_REGEX.match(v), f"{v!r} does not match dispatcher regex"


def test_v1_constant_is_unmodified() -> None:
    """Pin the v1 wire string — once published, it cannot change without
    a major-version bump. Tests guarding 'atomadic-forge.receipt/v1'."""
    assert SCHEMA_VERSION_V1 == "atomadic-forge.receipt/v1"


# ---- required fields contract ------------------------------------------

def test_required_v1_fields_pinned() -> None:
    """The v1 required-fields tuple is part of the schema contract.
    Adding to it is a major version bump. Removing from it is also a
    major bump (consumer breakage). This test fails loudly on any drift.
    """
    assert REQUIRED_RECEIPT_V1_FIELDS == (
        "schema_version",
        "generated_at_utc",
        "forge_version",
        "verdict",
        "project",
        "certify",
        "wire",
        "scout",
    )


def test_required_fields_subset_of_typeddict_keys() -> None:
    """Every required field name must appear in the TypedDict declaration.
    Catches typos: a required field nobody can populate is structurally
    invalid."""
    declared = set(ForgeReceiptV1.__annotations__.keys())
    for f in REQUIRED_RECEIPT_V1_FIELDS:
        assert f in declared, (
            f"Required field {f!r} is not declared in ForgeReceiptV1"
        )


# ---- verdict enum -------------------------------------------------------

def test_valid_verdicts_match_uep_v20_set() -> None:
    """UEP v20 names exactly four verdicts. The Receipt enum must equal
    that set — any drift is a governance gap."""
    assert set(VALID_VERDICTS) == {"PASS", "FAIL", "REFINE", "QUARANTINE"}
    assert len(VALID_VERDICTS) == 4


# ---- TypedDict shape sanity --------------------------------------------

def test_top_level_optional_fields_documented() -> None:
    """The Receipt v1.0 spec lists these optional fields. If a future
    edit removes one, RECEIPT.md and any consumer must be updated in
    the same PR. This test fails if a field silently disappears.
    """
    declared = set(ForgeReceiptV1.__annotations__.keys())
    expected_optional = {
        "assimilate_digest",
        "artifacts",
        "signatures",
        "lean4_attestation",
        "lineage",
        "compliance_mappings",
        "notes",
        "extra",
    }
    missing = expected_optional - declared
    assert not missing, (
        f"v1.0-documented optional fields missing from TypedDict: {missing}"
    )


# ---- example in docs/RECEIPT.md is valid -------------------------------

def _extract_first_full_receipt_block(md_text: str) -> str:
    """Pull the first complete fenced JSON block that parses cleanly
    AND contains schema_version + verdict. Robust against the smaller
    `{ ... }` shape blocks earlier in the doc which intentionally use
    JSON-with-placeholders for readability."""
    in_block = False
    buf: list[str] = []
    for line in md_text.splitlines():
        if line.strip().startswith("```json"):
            in_block = True
            buf = []
            continue
        if in_block and line.strip() == "```":
            text = "\n".join(buf)
            if '"schema_version"' in text and '"verdict"' in text:
                try:
                    json.loads(text)
                except json.JSONDecodeError:
                    in_block = False
                    continue
                return text
            in_block = False
            continue
        if in_block:
            buf.append(line)
    raise AssertionError(
        "no parseable receipt JSON block found in RECEIPT.md"
    )


def test_docs_receipt_example_is_valid_v1() -> None:
    """The full worked example in docs/RECEIPT.md must be valid JSON,
    declare schema_version v1, name a valid verdict, and populate
    every required field. Drift between the doc and the schema is a
    documentation bug we want to catch in CI, not in the field.
    """
    md = Path(__file__).resolve().parents[1] / "docs" / "RECEIPT.md"
    text = md.read_text(encoding="utf-8")
    block = _extract_first_full_receipt_block(text)
    data = json.loads(block)
    assert data["schema_version"] == SCHEMA_VERSION_V1
    assert data["verdict"] in VALID_VERDICTS
    for field in REQUIRED_RECEIPT_V1_FIELDS:
        assert field in data, f"docs example missing required field {field!r}"
    # Required sub-shapes
    assert isinstance(data["project"], dict)
    assert isinstance(data["certify"]["axes"], dict)
    assert set(data["certify"]["axes"].keys()) == {
        "documentation_complete",
        "tests_present",
        "tier_layout_present",
        "no_upward_imports",
    }
    assert data["wire"]["verdict"] in {"PASS", "FAIL"}
    assert isinstance(data["scout"]["tier_distribution"], dict)


def test_docs_receipt_example_lean4_corpus_totals_consistent() -> None:
    """Cross-check: total_theorems must equal the sum of corpus
    theorem counts in the doc example. Catches typos in the doc."""
    md = Path(__file__).resolve().parents[1] / "docs" / "RECEIPT.md"
    block = _extract_first_full_receipt_block(md.read_text(encoding="utf-8"))
    data = json.loads(block)
    att = data.get("lean4_attestation", {})
    if not att:
        return  # optional field; nothing to check
    summed = sum(c["theorem_count"] for c in att["corpora"])
    assert summed == att["total_theorems"], (
        f"lean4_attestation.total_theorems ({att['total_theorems']}) "
        f"does not match summed corpora ({summed}) in docs/RECEIPT.md."
    )


# ---- a0 tier discipline -------------------------------------------------

def test_receipt_schema_module_imports_only_typing() -> None:
    """a0 modules must not import from a1+, must not perform I/O at
    import time, must hold no logic. Pin: receipt_schema.py imports
    only from `__future__` and `typing`."""
    src = (
        Path(__file__).resolve().parents[1]
        / "src" / "atomadic_forge" / "a0_qk_constants" / "receipt_schema.py"
    ).read_text(encoding="utf-8")
    # Find every top-level import line.
    imports = [ln.strip() for ln in src.splitlines()
               if ln.startswith(("import ", "from "))]
    for ln in imports:
        assert ln.startswith(("from __future__", "from typing")), (
            f"a0/receipt_schema.py imports outside __future__ / typing: {ln!r}"
        )
