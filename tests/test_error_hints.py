"""Tier verification — Lane B4: error recovery hints.

Covers the named-template hint module and a few CLI end paths that
were rewired to use it. Future hints added to ``error_hints.py`` should
gain a smoke case here so their format strings are exercised in CI.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import typer.testing

from atomadic_forge.a1_at_functions.error_hints import (
    HINT_TEMPLATES,
    format_hint,
    hint_lines,
)
from atomadic_forge.a4_sy_orchestration.cli import app

runner = typer.testing.CliRunner()


# ---- pure-function tests ------------------------------------------------

def test_hint_templates_all_format_cleanly():
    """Every template must accept the canonical kwargs without KeyError.

    Pinning this prevents a stray ``{some_field}`` that nobody supplies.
    """
    canonical_kwargs: dict[str, dict[str, object]] = {
        "provider_missing_key": {"provider": "gemini", "env_var": "GEMINI_API_KEY"},
        "no_tier_dirs": {"path": "/tmp/out"},
        "wire_fail_with_violations": {"count": 5, "path": "/tmp/out/src/pkg"},
        "certify_below_threshold": {"score": 60, "threshold": 75, "path": "/tmp/out"},
        "fail_under_out_of_range": {"value": 150},
        "not_a_forge_manifest": {"path": "/tmp/foo.json"},
    }
    # Confirm every defined template has a covering kwargs entry — and
    # vice versa — so nobody can silently add an unformatted template.
    assert set(HINT_TEMPLATES.keys()) == set(canonical_kwargs.keys()), (
        "HINT_TEMPLATES keys drifted vs the test's canonical kwargs map. "
        "Add a covering kwargs entry for each new template."
    )
    for name, kwargs in canonical_kwargs.items():
        rendered = format_hint(name, **kwargs)
        assert rendered, f"empty render for {name}"


def test_format_hint_unknown_name_raises():
    with pytest.raises(KeyError):
        format_hint("does_not_exist")


def test_hint_lines_returns_split_lines():
    lines = hint_lines("provider_missing_key", provider="gemini",
                       env_var="GEMINI_API_KEY")
    assert any("export GEMINI_API_KEY" in ln for ln in lines)
    assert any("Ollama" in ln for ln in lines)
    assert lines == format_hint("provider_missing_key", provider="gemini",
                                 env_var="GEMINI_API_KEY").splitlines()


# ---- CLI end-path tests -------------------------------------------------

def test_certify_fail_under_out_of_range_uses_hint():
    with tempfile.TemporaryDirectory() as tmp:
        result = runner.invoke(
            app, ["certify", tmp, "--fail-under", "150"]
        )
    assert result.exit_code != 0
    out = result.stdout + (result.stderr or "")
    assert "between 0 and 100" in out
    assert "75" in out  # team-grade target hint

def test_certify_below_threshold_emits_recovery_hint(tmp_path):
    """Certify --fail-under triggers the recovery hint when the score is below."""
    # Empty dir → certify will fail every axis → score 0 < 75.
    result = runner.invoke(
        app, ["certify", str(tmp_path), "--fail-under", "75"]
    )
    assert result.exit_code == 1
    out = result.stdout + (result.stderr or "")
    assert "below the 75/100 gate" in out
    assert "documentation" in out  # quick-wins guidance present


def test_wire_fail_emits_repair_hint_unless_suggest_or_json(tmp_path):
    """Default wire FAIL output ends with the recovery-hint block."""
    pkg = tmp_path / "pkg"
    a1 = pkg / "a1_at_functions"
    a2 = pkg / "a2_mo_composites"
    a1.mkdir(parents=True); a2.mkdir(parents=True)
    (a2 / "store.py").write_text(
        '"""a2 store."""\nclass Store:\n    pass\n', encoding="utf-8")
    (a1 / "h.py").write_text(
        "from ..a2_mo_composites.store import Store\n", encoding="utf-8")
    # Plain wire (no flags) → hint shows.
    plain = runner.invoke(app, ["wire", str(pkg)])
    assert plain.exit_code == 0
    out = plain.stdout + (plain.stderr or "")
    assert "Recovery options" in out
    assert "--suggest-repairs" in out
    # --suggest-repairs already gives guidance → don't double up.
    suggest = runner.invoke(app, ["wire", str(pkg), "--suggest-repairs"])
    suggest_out = suggest.stdout + (suggest.stderr or "")
    assert "Recovery options" not in suggest_out
    # --json → suppress the human-readable hint.
    j = runner.invoke(app, ["wire", str(pkg), "--json"])
    assert j.exit_code == 0
    j_out = j.stdout + (j.stderr or "")
    assert "Recovery options" not in j_out


def test_diff_not_a_manifest_uses_hint(tmp_path):
    """forge diff with a non-forge file emits the named hint, not a stack trace."""
    bad = tmp_path / "not_a_manifest.json"
    bad.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
    other = tmp_path / "also_not.json"
    other.write_text(json.dumps({"schema_version": "atomadic-forge.scout/v1",
                                  "symbol_count": 0}), encoding="utf-8")
    result = runner.invoke(app, ["diff", str(bad), str(other)])
    assert result.exit_code != 0
    out = result.stdout + (result.stderr or "")
    assert "not a Forge JSON manifest" in out
    assert "atomadic-forge." in out
