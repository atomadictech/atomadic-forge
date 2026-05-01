"""Tests for `forge whoami` (Tier a4).

Covers the four states: missing-key, env-key, credentials-file-key,
and verify-failure. Uses CliRunner so the test mirrors what an agent
or shell user would see, not just internal state.
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from atomadic_forge.a4_sy_orchestration import whoami_cmd


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def fake_creds(tmp_path, monkeypatch):
    """Point CREDENTIALS_FILE at a tmp path and ensure env is empty."""
    creds = tmp_path / "credentials.toml"
    monkeypatch.setattr(whoami_cmd, "CREDENTIALS_FILE", creds)
    monkeypatch.delenv("FORGE_API_KEY", raising=False)
    return creds


class _StubClient:
    """Stand-in for ForgeAuthClient — returns whatever `verify` is patched to."""

    def __init__(self, result: dict):
        self._result = result

    def verify(self, _api_key: str) -> dict:
        return self._result


def test_whoami_missing_key_exits_1(runner, fake_creds):
    out = runner.invoke(whoami_cmd.app, [])
    assert out.exit_code == 1
    assert "Not logged in" in out.output
    assert "forge login" in out.output


def test_whoami_missing_key_json(runner, fake_creds):
    out = runner.invoke(whoami_cmd.app, ["--json"])
    assert out.exit_code == 1
    body = json.loads(out.output)
    assert body["ok"] is False
    assert body["source"] == "missing"


def test_whoami_reads_credentials_file_when_no_env(
    runner, fake_creds, monkeypatch,
):
    fake_creds.write_text(
        '[forge_auth]\napi_key = "fk_live_abcdef123"\n', encoding="utf-8",
    )
    monkeypatch.setattr(
        whoami_cmd, "ForgeAuthClient",
        lambda: _StubClient({"ok": True, "email": "tom@example.com", "plan": "pro"}),
    )
    out = runner.invoke(whoami_cmd.app, ["--json"])
    assert out.exit_code == 0
    body = json.loads(out.output)
    assert body["ok"] is True
    assert body["source"] == "credentials_file"
    assert body["email"] == "tom@example.com"
    assert body["plan"] == "pro"
    assert body["key_prefix"].startswith("fk_live_")


def test_whoami_prefers_env_over_credentials_file(
    runner, fake_creds, monkeypatch,
):
    """Env wins over credentials file (CI / explicit override behavior)."""
    fake_creds.write_text(
        '[forge_auth]\napi_key = "fk_live_FILEKEY999"\n', encoding="utf-8",
    )
    monkeypatch.setenv("FORGE_API_KEY", "fk_live_ENVKEY777")
    monkeypatch.setattr(
        whoami_cmd, "ForgeAuthClient",
        lambda: _StubClient({"ok": True, "email": "ci@example.com", "plan": "ci"}),
    )
    out = runner.invoke(whoami_cmd.app, ["--json"])
    assert out.exit_code == 0
    body = json.loads(out.output)
    assert body["source"] == "env"
    assert body["key_prefix"].startswith("fk_live_ENV")


def test_whoami_no_verify_skips_network(runner, fake_creds, monkeypatch):
    fake_creds.write_text(
        '[forge_auth]\napi_key = "fk_live_offline"\n', encoding="utf-8",
    )
    # If verify were called, this would explode. --no-verify must skip it.
    monkeypatch.setattr(
        whoami_cmd, "ForgeAuthClient",
        lambda: (_ for _ in ()).throw(RuntimeError("verify must not be called")),
    )
    out = runner.invoke(whoami_cmd.app, ["--no-verify", "--json"])
    assert out.exit_code == 0
    body = json.loads(out.output)
    assert body["ok"] is True
    assert body["verify_ok"] is False
    assert "skipped" in body["verify_reason"]


def test_whoami_verify_rejection_exits_1(runner, fake_creds, monkeypatch):
    fake_creds.write_text(
        '[forge_auth]\napi_key = "fk_live_revoked"\n', encoding="utf-8",
    )
    monkeypatch.setattr(
        whoami_cmd, "ForgeAuthClient",
        lambda: _StubClient({"ok": False, "reason": "key revoked", "email": "", "plan": ""}),
    )
    out = runner.invoke(whoami_cmd.app, ["--json"])
    assert out.exit_code == 1
    body = json.loads(out.output)
    assert body["ok"] is False
    assert body["verify_ok"] is False
    assert "revoked" in body["verify_reason"]
