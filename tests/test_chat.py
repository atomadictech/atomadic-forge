"""Tests for the Forge chat copilot command."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from atomadic_forge.a1_at_functions.chat_context import build_chat_context
from atomadic_forge.a4_sy_orchestration.cli import app

runner = CliRunner()


def test_chat_ask_stub_json_without_context():
    result = runner.invoke(app, [
        "chat", "ask", "hello forge",
        "--provider", "stub",
        "--no-cwd-context",
        "--json",
    ])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["schema_version"] == "atomadic-forge.chat/v1"
    assert data["provider"] == "stub"
    assert data["context"]["file_count"] == 0
    assert data["answer"].startswith("# stub response")


def test_chat_context_packs_files_and_skips_env(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    (tmp_path / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("def hello():\n    return 'hi'\n",
                                  encoding="utf-8")

    ctx = build_chat_context([tmp_path], cwd=tmp_path,
                             max_files=10, max_chars=8_000)

    paths = [f["path"] for f in ctx["files"]]
    assert "README.md" in paths
    assert "src/app.py" in paths
    assert ".env" not in paths
    assert "TOKEN=secret" not in ctx["context"]
