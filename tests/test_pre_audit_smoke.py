"""Tier verification — pre-audit ground-truth smoke tests.

These tests pin the structural claims made by the post-audit lane plan so
that subsequent Lane A/C/D/E/G refactors don't silently drift the
codebase out from under the plan.

Each test is intentionally narrow: it should fail loudly the moment a
named claim becomes false (file moved, symbol renamed, line count out of
band, etc.), prompting an explicit decision to update both the code AND
this fixture.

Run as part of the regular pytest suite. Keep fast — these are static
file inspections, no imports of the runtime forge package required.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


_ROOT = Path(__file__).resolve().parents[1]
_PKG = _ROOT / "src" / "atomadic_forge"


def _read(relpath: str) -> str:
    return (_PKG / relpath).read_text(encoding="utf-8")


# --- Lane A1: deprecated datetime.utcnow() must stay swept ---------------

def test_no_datetime_utcnow_in_source() -> None:
    """Lane A1 invariant: no datetime.utcnow() call sites remain.

    `datetime.utcnow()` is deprecated in Python 3.12+ and slated for
    removal in 3.14+. The 4 historical sites (emergent_feature.py:69,
    commandsmith_feature.py:99 + 264, synergy_feature.py:41) must all
    use timezone-aware datetime.now(timezone.utc) instead.
    """
    offenders: list[str] = []
    for py in _PKG.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        text = py.read_text(encoding="utf-8")
        if "utcnow()" in text:
            offenders.append(str(py.relative_to(_PKG)))
    assert not offenders, (
        f"datetime.utcnow() reintroduced in: {offenders}. "
        "Use datetime.now(timezone.utc) — see Lane A1 of audit."
    )


# --- Lane A2: StubLLMClient is stateful and must move to a2 (eventually) -

def test_stub_llm_client_still_in_a1_for_now() -> None:
    """Sentinel: StubLLMClient currently lives in a1 but is mutable
    state (`_calls`, `_canned`). Lane A2 will relocate it to
    a2_mo_composites/. This test pins the *current* location so the
    relocation is an explicit, reviewed move rather than a silent drift.
    """
    src = _read("a1_at_functions/llm_client.py")
    assert "class StubLLMClient" in src
    assert "self._calls" in src and "self._canned" in src, (
        "StubLLMClient state shape changed — re-evaluate Lane A2 plan."
    )


def test_stub_llm_client_not_in_a2_yet() -> None:
    """Companion to the above: when Lane A2 lands, this test gets
    inverted (assert presence in a2_mo_composites/, absence from a1)."""
    a2 = _PKG / "a2_mo_composites"
    if not a2.exists():
        pytest.skip("a2_mo_composites missing")
    for py in a2.glob("*.py"):
        if "class StubLLMClient" in py.read_text(encoding="utf-8"):
            pytest.fail(
                f"StubLLMClient already in a2 ({py.name}) — "
                "Lane A2 landed; flip this test."
            )


# --- Lane A3: signature extraction is duplicated across modules ----------

_SIG_DUP_FILES = (
    "a1_at_functions/body_extractor.py",
    "a1_at_functions/commandsmith_discover.py",
    "a1_at_functions/doc_synthesizer.py",
    "a1_at_functions/emergent_signature_extract.py",
    "a1_at_functions/generation_quality.py",
    "a1_at_functions/scout_walk.py",
    "a1_at_functions/stub_detector.py",
    "a1_at_functions/synergy_surface_extract.py",
)


def test_signature_extraction_duplication_still_present() -> None:
    """Sentinel for Lane A3 — until `signature_shared.py` lands and the
    callers are migrated, every module in _SIG_DUP_FILES walks
    ast.FunctionDef on its own. When Lane A3 lands, we expect:
        - `a1_at_functions/signature_shared.py` to exist
        - the count of independent ast.FunctionDef walkers to drop
    This test fails loudly if either condition flips so the audit plan
    stays in sync with reality.
    """
    walkers = 0
    for rel in _SIG_DUP_FILES:
        p = _PKG / rel
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        if re.search(r"ast\.FunctionDef", text):
            walkers += 1
    shared = _PKG / "a1_at_functions" / "signature_shared.py"
    assert (walkers >= 6 and not shared.exists()) or (
        walkers <= 3 and shared.exists()
    ), (
        f"Signature-extraction duplication state inconsistent: "
        f"walkers={walkers}, shared_exists={shared.exists()}. "
        "Either Lane A3 landed (consolidate this test) or it half-landed."
    )


# --- Lane D2: wire_check.auto_fixable is now a real counter --------------
# (Originally a sentinel that auto_fixable was hardcoded to 0; flipped
# in Lane D2 — the assertion now confirms repair-suggestion plumbing
# is wired and that scan_violations exposes a suggest_repairs kwarg.)

def test_wire_check_suggest_repairs_is_wired() -> None:
    """Lane D2 landed: scan_violations(... suggest_repairs=True) returns
    a non-zero auto_fixable count on a synthesized illegal a1->a2 import.
    """
    from atomadic_forge.a1_at_functions.wire_check import scan_violations

    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as tmp:
        pkg = pathlib.Path(tmp) / "pkg"
        a1 = pkg / "a1_at_functions"
        a2 = pkg / "a2_mo_composites"
        a1.mkdir(parents=True)
        a2.mkdir(parents=True)
        (a2 / "store.py").write_text(
            '"""a2 store."""\nclass Store:\n    pass\n', encoding="utf-8")
        (a1 / "helper.py").write_text(
            '"""a1 with illegal upward import."""\n'
            "from ..a2_mo_composites.store import Store\n",
            encoding="utf-8",
        )
        soft = scan_violations(pkg)
        hard = scan_violations(pkg, suggest_repairs=True)
        assert soft["violation_count"] >= 1
        assert soft["auto_fixable"] == 0
        assert "repair_suggestions" not in soft
        assert hard["auto_fixable"] >= 1
        assert "repair_suggestions" in hard
        assert any(
            v.get("proposed_destination") == "a2_mo_composites"
            for v in hard["violations"]
        )


# --- Lane A6/A7: chained `*_then_*` commands are auto-synthesized --------

_CHAINED = (
    "commands/emergent_then_synergy.py",
    "commands/synergy_then_emergent.py",
    "commands/evolve_then_iterate.py",
    "commands/feature_then_emergent.py",
)


def test_chained_then_commands_count_is_pinned() -> None:
    """The audit observed 4 `*_then_*` chained commands totaling 321 LOC.

    Lane A6 will delete them in favor of a `--follow=<verb>` flag on
    base commands. This test fails when (a) more chained verbs appear
    (synergy emitter regressed — Lane A7 not done) or (b) they are
    deleted (Lane A6 landed — flip this test).
    """
    present = [r for r in _CHAINED if (_PKG / r).exists()]
    assert len(present) in (0, 4), (
        f"Unexpected chained-then command count: {len(present)} "
        f"({present}). Audit pinned 4; expect 0 after Lane A6."
    )


# --- Lane A5: per-provider retry loops in llm_client ---------------------

def test_llm_client_provider_count() -> None:
    """7 client classes documented by the audit. Lane A5 doesn't change
    the count, only consolidates retry/backoff. This test catches a
    silent provider addition or deletion that would invalidate the
    Lane A5/C plan.
    """
    src = _read("a1_at_functions/llm_client.py")
    classes = re.findall(r"^class\s+(\w+Client)\b", src, re.MULTILINE)
    expected = {
        "StubLLMClient",
        "AnthropicClient",
        "OpenAIClient",
        "GeminiClient",
        "AAAANexusClient",
        "OllamaClient",
        "OpenRouterClient",
    }
    actual = set(classes)
    missing = expected - actual
    extra = actual - expected
    assert not missing, f"LLM provider classes missing: {missing}"
    if extra:
        pytest.skip(
            f"New LLM provider class(es) detected: {extra} — "
            "update audit and the Lane A5 plan to cover them."
        )


# --- Lane A8: iterate vs evolve overlap ----------------------------------

def test_iterate_and_evolve_modules_still_separate() -> None:
    """Lane A8 collapses these into one `run_loop(depth=N)` module.

    Until then, both must exist. After A8, expect either
    `forge_evolve.py` to be removed or to be a thin alias.
    """
    loop = _PKG / "a3_og_features" / "forge_loop.py"
    evolve = _PKG / "a3_og_features" / "forge_evolve.py"
    assert loop.exists(), "forge_loop.py vanished — Lane A8 may have landed."
    if not evolve.exists():
        pytest.skip("forge_evolve.py removed — Lane A8 landed; flip this test.")
    # Both still present — pin the size band so a silent rewrite trips us.
    evolve_loc = sum(1 for _ in evolve.read_text(encoding="utf-8").splitlines())
    assert 100 <= evolve_loc <= 350, (
        f"forge_evolve.py LOC {evolve_loc} outside expected band — "
        "Lane A8 may have started; reconcile with the audit plan."
    )
