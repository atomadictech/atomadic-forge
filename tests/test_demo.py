"""Tests for the `forge demo` runner."""

from __future__ import annotations

from pathlib import Path

import pytest

from atomadic_forge.a1_at_functions.llm_client import StubLLMClient
from atomadic_forge.a3_og_features.demo_runner import (
    get_preset, list_presets, run_demo,
)


def test_list_presets_returns_three():
    presets = list_presets()
    names = [p.name for p in presets]
    assert "calc" in names
    assert "kv" in names
    assert "slug" in names


def test_get_preset_unknown_raises():
    with pytest.raises(KeyError):
        get_preset("does-not-exist")


def test_run_demo_with_stub_writes_artifact(tmp_path):
    """Stub LLM emits empty arrays — demo still produces a valid DEMO.md."""
    out = tmp_path / "demo-out"
    result = run_demo(
        preset_name="calc",
        output=out,
        llm=StubLLMClient(canned=["[]"] * 30),
        rounds=1,
        iterations=1,
        skip_cli_demo=True,
    )
    assert result.preset == "calc"
    assert result.output_root == str(out)
    assert Path(result.artifact_md_path).exists()
    md = Path(result.artifact_md_path).read_text(encoding="utf-8")
    assert "forge demo calc" in md
    assert "Score arc" in md


def test_run_demo_rejects_unknown_preset(tmp_path):
    with pytest.raises(KeyError):
        run_demo(
            preset_name="garbage",
            output=tmp_path / "x",
            llm=StubLLMClient(),
            rounds=1, iterations=1,
            skip_cli_demo=True,
        )
