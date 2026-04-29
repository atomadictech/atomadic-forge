"""Tier a0 — F-code registry: stable, citeable error codes.

Golden Path Lane A W5 deliverable. Every error Forge surfaces (wire
violations, certify failures, scout misclassifications, …) carries an
``F-code`` of the form ``F0042``: a 4-digit, zero-padded, fixed
integer that is **never reused or renumbered**. Once an F-code is
assigned to a class of error, that mapping is part of the schema
contract — the same way ``schema_version`` is.

Why F-codes:
  * Linker-style citeability — a CI report can say "F0042 occurred 3
    times" without leaking the underlying message string, which
    reviewers and tooling can grep / pivot / dashboards on.
  * Machine-applicable ``--fix`` — Lane A W6's ``forge enforce``
    routes by F-code: F0042 has a known mechanical fix (move the
    importing file up to the higher tier), F0050 (no README) has
    another, etc.
  * Forward-compat — adding an F-code is additive. Removing or
    renumbering an F-code is a major schema bump.
  * Internationalization-ready — the message string can change per
    locale; the F-code stays.

Registry convention:
  F0001..F0009  — scout / classification (info)
  F0010..F0019  — cherry-pick (warn)
  F0040..F0049  — wire / upward-import violations  ← W5 seeds these
  F0050..F0059  — certify axis failures            ← W5 seeds these
  F0060..F0069  — stub detection
  F0070..F0079  — import-repair
  F0080..F0089  — assimilate conflicts
  F0090..F0099  — receipt / signing

Pure data: this module imports only ``__future__`` and ``typing``.
The lookup helpers are pure.
"""
from __future__ import annotations

from typing import Literal, TypedDict


FCodeSeverity = Literal["info", "warn", "error"]


class FCode(TypedDict):
    """One entry in the F-code registry.

    Fields:
      code              — 'F' + 4 zero-padded digits (e.g. 'F0042')
      name              — short kebab-case slug (stable; never renamed)
      severity          — info | warn | error
      title             — one-line human label (may be localized)
      hint_key          — name of an a1.error_hints template; '' for none
      auto_fixable      — when True, Lane A W6 'forge enforce' has a
                          mechanical fix path
      doc_anchor        — section anchor in docs/F_CODES.md (forthcoming)
    """
    code: str
    name: str
    severity: FCodeSeverity
    title: str
    hint_key: str
    auto_fixable: bool
    doc_anchor: str


F_CODE_REGISTRY: dict[str, FCode] = {
    # ---- Wire / upward-import violations (F0040-F0049) ----
    "F0040": FCode(
        code="F0040",
        name="a0-cannot-import-anything",
        severity="error",
        title="a0_qk_constants must not import any other tier (a0 holds zero logic).",
        hint_key="wire_fail_with_violations",
        auto_fixable=False,
        doc_anchor="f0040-a0-cannot-import-anything",
    ),
    "F0041": FCode(
        code="F0041",
        name="a1-imports-a2",
        severity="error",
        title="a1_at_functions imports from a2_mo_composites (upward).",
        hint_key="wire_fail_with_violations",
        auto_fixable=True,
        doc_anchor="f0041-a1-imports-a2",
    ),
    "F0042": FCode(
        code="F0042",
        name="a1-imports-a3",
        severity="error",
        title="a1_at_functions imports from a3_og_features (upward).",
        hint_key="wire_fail_with_violations",
        auto_fixable=True,
        doc_anchor="f0042-a1-imports-a3",
    ),
    "F0043": FCode(
        code="F0043",
        name="a1-imports-a4",
        severity="error",
        title="a1_at_functions imports from a4_sy_orchestration (upward).",
        hint_key="wire_fail_with_violations",
        auto_fixable=True,
        doc_anchor="f0043-a1-imports-a4",
    ),
    "F0044": FCode(
        code="F0044",
        name="a2-imports-a3",
        severity="error",
        title="a2_mo_composites imports from a3_og_features (upward).",
        hint_key="wire_fail_with_violations",
        auto_fixable=True,
        doc_anchor="f0044-a2-imports-a3",
    ),
    "F0045": FCode(
        code="F0045",
        name="a2-imports-a4",
        severity="error",
        title="a2_mo_composites imports from a4_sy_orchestration (upward).",
        hint_key="wire_fail_with_violations",
        auto_fixable=True,
        doc_anchor="f0045-a2-imports-a4",
    ),
    "F0046": FCode(
        code="F0046",
        name="a3-imports-a4",
        severity="error",
        title="a3_og_features imports from a4_sy_orchestration (upward).",
        hint_key="wire_fail_with_violations",
        auto_fixable=True,
        doc_anchor="f0046-a3-imports-a4",
    ),
    "F0049": FCode(
        code="F0049",
        name="unknown-tier-violation",
        severity="error",
        title="Upward import detected but tier shape is non-canonical; review manually.",
        hint_key="wire_fail_with_violations",
        auto_fixable=False,
        doc_anchor="f0049-unknown-tier-violation",
    ),
    # ---- Certify axis failures (F0050-F0059) ----
    "F0050": FCode(
        code="F0050",
        name="documentation-missing",
        severity="error",
        title="Documentation axis FAIL: no README.md and < 2 docs/*.md files.",
        hint_key="certify_below_threshold",
        auto_fixable=True,
        doc_anchor="f0050-documentation-missing",
    ),
    "F0051": FCode(
        code="F0051",
        name="tests-missing",
        severity="error",
        title="Tests axis FAIL: no tests/test_*.py or tests/*_test.py present.",
        hint_key="certify_below_threshold",
        auto_fixable=False,
        doc_anchor="f0051-tests-missing",
    ),
    "F0052": FCode(
        code="F0052",
        name="tier-layout-incomplete",
        severity="error",
        title="Tier-layout axis FAIL: fewer than 3 tier directories present.",
        hint_key="no_tier_dirs",
        auto_fixable=False,
        doc_anchor="f0052-tier-layout-incomplete",
    ),
    "F0053": FCode(
        code="F0053",
        name="upward-imports-present",
        severity="error",
        title="Import-discipline axis FAIL: at least one wire violation present.",
        hint_key="wire_fail_with_violations",
        auto_fixable=True,
        doc_anchor="f0053-upward-imports-present",
    ),
    # ---- Sidecar drift (F0100-F0109; Lane D W8/W11) ----
    "F0100": FCode(
        code="F0100",
        name="sidecar-source-unparseable",
        severity="error",
        title="Sidecar present but the source file did not parse.",
        hint_key="",
        auto_fixable=False,
        doc_anchor="f0100-sidecar-source-unparseable",
    ),
    "F0101": FCode(
        code="F0101",
        name="sidecar-declares-missing-symbol",
        severity="error",
        title="Sidecar declares a symbol the source file doesn't have.",
        hint_key="",
        auto_fixable=False,
        doc_anchor="f0101-sidecar-declares-missing-symbol",
    ),
    "F0102": FCode(
        code="F0102",
        name="sidecar-coverage-incomplete",
        severity="warn",
        title="Source has a public symbol the sidecar didn't declare (advisory).",
        hint_key="",
        auto_fixable=False,
        doc_anchor="f0102-sidecar-coverage-incomplete",
    ),
    "F0103": FCode(
        code="F0103",
        name="sidecar-pure-violates-purity",
        severity="error",
        title="Sidecar declares Pure but source uses I/O / network / non-deterministic input.",
        hint_key="",
        auto_fixable=False,
        doc_anchor="f0103-sidecar-pure-violates-purity",
    ),
    "F0106": FCode(
        code="F0106",
        name="sidecar-tier-mismatch",
        severity="warn",
        title="Sidecar declares a tier different from the source file's actual path tier.",
        hint_key="",
        auto_fixable=False,
        doc_anchor="f0106-sidecar-tier-mismatch",
    ),
}


# Sidecar S-code → F-code mapping. Exposed so the validator (a1) can
# promote local drift labels into the global F-code namespace
# without re-importing this whole registry.
SIDECAR_S_TO_F: dict[str, str] = {
    "S0000": "F0100",
    "S0001": "F0101",
    "S0002": "F0102",
    "S0003": "F0103",
    "S0006": "F0106",
}
"""Canonical F-code registry. Adding a new code is additive; renaming
or renumbering is a major schema bump (and requires updating every
test and consumer). See the H1 pre-audit smoke for the drift sentinel.
"""


_TIER_PAIR_TO_FCODE: dict[tuple[str, str], str] = {
    # (from_tier, to_tier) → F-code. a0 is special-cased below.
    ("a1_at_functions", "a2_mo_composites"):    "F0041",
    ("a1_at_functions", "a3_og_features"):      "F0042",
    ("a1_at_functions", "a4_sy_orchestration"): "F0043",
    ("a2_mo_composites", "a3_og_features"):     "F0044",
    ("a2_mo_composites", "a4_sy_orchestration"): "F0045",
    ("a3_og_features", "a4_sy_orchestration"):   "F0046",
}


def fcode_for_tier_violation(from_tier: str, to_tier: str) -> str:
    """Map a (from, to) tier pair to its registered F-code.

    Returns:
      'F0040' when from_tier is a0 (a0 may not import anything)
      one of F0041..F0046 for the canonical upward-import pairs
      'F0049' for any other shape (non-canonical tier, mixed-language)

    Pure: O(1) lookup.
    """
    if from_tier == "a0_qk_constants":
        return "F0040"
    return _TIER_PAIR_TO_FCODE.get((from_tier, to_tier), "F0049")


def fcode_for_certify_axis(axis: str) -> str:
    """Map a certify axis name to its F-code.

    Recognised axis names match the CertifyResult booleans:
      'documentation_complete'  → F0050
      'tests_present'           → F0051
      'tier_layout_present'     → F0052
      'no_upward_imports'       → F0053
    Unknown axes return '' (no F-code assigned).
    """
    return {
        "documentation_complete": "F0050",
        "tests_present":          "F0051",
        "tier_layout_present":    "F0052",
        "no_upward_imports":      "F0053",
    }.get(axis, "")


def get_fcode(code: str) -> FCode | None:
    """Return the registry entry for ``code`` or None if unregistered."""
    return F_CODE_REGISTRY.get(code)


def all_auto_fixable_fcodes() -> tuple[str, ...]:
    """Return the codes Lane A W6 'forge enforce' has a path for.

    Sorted ascending so consumers get a stable iteration order.
    """
    return tuple(sorted(c for c, e in F_CODE_REGISTRY.items()
                         if e["auto_fixable"]))
