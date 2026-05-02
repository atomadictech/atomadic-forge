"""Tier verification — Golden Path Lane A W3: Compiler Feedback Loop.

Splits cleanly into two layers:

  Pure (compiler_feedback.py):
    * pack_compile_feedback formats the prompt deterministically
    * should_fix_round honours importable + missing-trace shortcuts

  Integration (forge_loop._run_fix_rounds):
    * a stub LLM that emits a broken file then a corrected file is
      driven by run_iterate(max_fix_rounds=2); the broken-then-fixed
      sequence registers as exactly one fix-round
    * max_fix_rounds=0 (default) disables the path entirely — the
      existing iterate behaviour is preserved
"""
from __future__ import annotations

import json

import pytest

from atomadic_forge.a1_at_functions.compiler_feedback import (
    pack_compile_feedback,
    should_fix_round,
)
from atomadic_forge.a1_at_functions.llm_client import StubLLMClient
from atomadic_forge.a3_og_features.forge_loop import run_iterate

# ---- pure compiler_feedback ---------------------------------------------

_BROKEN_SMOKE = {
    "schema_version": "atomadic-forge.import_smoke/v1",
    "package": "demo",
    "src_root": "/tmp",
    "importable": False,
    "duration_ms": 12,
    "error_kind": "SyntaxError",
    "error_message": "invalid syntax (helper.py, line 4)",
    "traceback_excerpt": (
        'File "/tmp/demo/a1_at_functions/helper.py", line 4\n'
        "    def foo(x:\n"
        "             ^\n"
        "SyntaxError: invalid syntax"
    ),
}

_OK_SMOKE = {
    "schema_version": "atomadic-forge.import_smoke/v1",
    "package": "demo", "src_root": "/tmp",
    "importable": True, "duration_ms": 8,
    "error_kind": "", "error_message": "", "traceback_excerpt": "",
}


def test_pack_includes_package_and_attempt_index():
    out = pack_compile_feedback(_BROKEN_SMOKE, package="demo",
                                 fix_round_index=1, max_fix_rounds=3)
    assert "FIX ROUND" in out
    assert "package:" in out and "demo" in out
    assert "fix-round attempt: 1 of 3" in out
    assert "SyntaxError" in out
    assert "invalid syntax" in out


def test_pack_traceback_truncated():
    huge = {**_BROKEN_SMOKE, "traceback_excerpt": "x" * 5000}
    out = pack_compile_feedback(huge, package="demo",
                                 fix_round_index=1, max_fix_rounds=1)
    # Traceback section should not exceed 1200 chars + the fence framing.
    fence_start = out.index("```")
    fence_end = out.rindex("```")
    assert fence_end - fence_start < 1500


def test_pack_invalid_indices_raise():
    with pytest.raises(ValueError):
        pack_compile_feedback(_BROKEN_SMOKE, package="x",
                               fix_round_index=0, max_fix_rounds=1)
    with pytest.raises(ValueError):
        pack_compile_feedback(_BROKEN_SMOKE, package="x",
                               fix_round_index=1, max_fix_rounds=0)


def test_should_fix_round_skips_when_importable():
    assert should_fix_round(_OK_SMOKE) is False


def test_should_fix_round_fires_on_real_error():
    assert should_fix_round(_BROKEN_SMOKE) is True


def test_should_fix_round_skips_when_no_useful_trace():
    nothing = {"importable": False, "error_kind": "", "error_message": ""}
    assert should_fix_round(nothing) is False


# ---- run_iterate integration via stub LLM ------------------------------

_GOOD_FILE_BODY = (
    '"""a1 helper."""\n'
    "def add(a, b):\n"
    "    return a + b\n"
)

_BROKEN_FILE_BODY = (
    '"""a1 helper."""\n'
    "def add(a, b\n"   # missing close paren — SyntaxError
    "    return a + b\n"
)


_BROKEN_INIT = (
    '"""demo package."""\n'
    "raise RuntimeError('boom at import time — needs a fix round')\n"
)

_FIXED_INIT = '"""demo package."""\n'


def _broken_then_fixed_responder(_prompt: str, _system: str) -> str:
    """Stateful closure across calls — turn 0 emits a broken __init__
    that crashes at import; the fix-round emits a clean __init__.

    The package __init__ is what import_smoke actually loads, so the
    failure is detectable end-to-end (unlike a broken sibling file
    that the empty tier-init re-export skips).
    """
    state = _broken_then_fixed_responder
    state.calls = getattr(state, "calls", 0) + 1
    if state.calls == 1:
        files = [{"path": "src/demo/__init__.py", "content": _BROKEN_INIT}]
        return json.dumps(files)
    if state.calls == 2:
        files = [{"path": "src/demo/__init__.py", "content": _FIXED_INIT}]
        return json.dumps(files)
    return "[]"


def _always_clean_responder(_prompt: str, _system: str) -> str:
    """Single call: emits a clean helper, then [] forever."""
    state = _always_clean_responder
    state.calls = getattr(state, "calls", 0) + 1
    if state.calls == 1:
        files = [{"path": "src/demo/a1_at_functions/helper.py",
                  "content": _GOOD_FILE_BODY}]
        return json.dumps(files)
    return "[]"


def test_max_fix_rounds_zero_keeps_existing_behaviour(tmp_path):
    """Default --max-fix-rounds=0 → no fix-rounds fire; the iterate
    report includes an empty fix_rounds list."""
    _always_clean_responder.calls = 0  # reset
    llm = StubLLMClient(responder=_always_clean_responder)
    rep = run_iterate(
        "build a tiny adder",
        output=tmp_path,
        package="demo",
        llm=llm,
        max_iterations=1,
        max_fix_rounds=0,
        target_score=0.0,
    )
    assert rep["fix_rounds"] == []
    assert rep["fix_round_count"] == 0
    assert rep["max_fix_rounds"] == 0


def test_fix_round_recovers_from_broken_emit(tmp_path):
    """The broken-then-fixed responder produces exactly 1 fix-round
    that flips the import_smoke from FAIL → PASS."""
    _broken_then_fixed_responder.calls = 0  # reset
    llm = StubLLMClient(responder=_broken_then_fixed_responder)
    rep = run_iterate(
        "build a tiny adder",
        output=tmp_path,
        package="demo",
        llm=llm,
        max_iterations=1,
        max_fix_rounds=2,
        target_score=0.0,
    )
    # Exactly one fix-round registered (the second call from the
    # responder); the third call (subsequent iterate turn) emits [].
    fr = rep["fix_rounds"]
    assert len(fr) == 1
    entry = fr[0]
    assert entry["turn"] == 0
    assert entry["fix_round"] == 1
    assert entry["smoke_error_kind"] in {"RuntimeError", "Other",
                                          "ImportError", "ModuleNotFoundError"}
    assert entry["files_written"], "fix round should have written at least 1 file"
    # The fixed __init__ is on disk and imports cleanly.
    fixed = tmp_path / "src" / "demo" / "__init__.py"
    assert fixed.exists()
    assert "raise RuntimeError" not in fixed.read_text(encoding="utf-8")
    # Manifest carries the fix-round trace.
    iterate_manifest = json.loads(
        (tmp_path / ".atomadic-forge" / "iterate.json").read_text(
            encoding="utf-8")
    )
    assert iterate_manifest["fix_round_count"] == 1
    assert iterate_manifest["max_fix_rounds"] == 2
