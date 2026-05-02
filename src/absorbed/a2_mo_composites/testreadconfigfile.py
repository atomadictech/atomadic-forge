"""Tests for config defaults, config I/O, merge logic, validation, and CLI smoke."""

from __future__ import annotations

import json
import urllib.error

import pytest
from typer.testing import CliRunner

import atomadic_forge.a1_at_functions.provider_detect as _pd
from atomadic_forge.a0_qk_constants.config_defaults import (
    CONFIG_FILE_NAME,
    DEFAULT_CONFIG,
    GLOBAL_CONFIG_DIR,
    LOCAL_CONFIG_DIR,
)
from atomadic_forge.a1_at_functions.config_io import (
    load_config,
    merge_configs,
    read_config_file,
    save_config,
    validate_config,
)
from atomadic_forge.a4_sy_orchestration.cli import app

detect_ollama = _pd.detect_ollama
list_ollama_models = _pd.list_ollama_models
check_provider = _pd.test_provider  # aliased: 'test_provider' at module scope triggers pytest collection

runner = CliRunner()


# ── Tier a0: config_defaults ─────────────────────────────────────────────────

class TestDefaults:
    def test_required_keys_present(self):
        required = {
            "provider", "ollama_url", "ollama_model",
            "default_target_score", "auto_apply",
            "output_dir", "sources_dir", "package_prefix",
        }
        assert required.issubset(DEFAULT_CONFIG.keys())

    def test_default_provider_is_auto(self):
        assert DEFAULT_CONFIG["provider"] == "auto"

    def test_default_target_score_in_range(self):
        score = DEFAULT_CONFIG["default_target_score"]
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_default_auto_apply_is_false(self):
        assert DEFAULT_CONFIG["auto_apply"] is False

    def test_config_file_name(self):
        assert CONFIG_FILE_NAME == "config.json"

    def test_local_config_dir(self):
        assert LOCAL_CONFIG_DIR == ".atomadic-forge"

    def test_global_config_dir_starts_with_tilde(self):
        assert GLOBAL_CONFIG_DIR.startswith("~")

    def test_ollama_url_is_http(self):
        assert DEFAULT_CONFIG["ollama_url"].startswith("http://")


# ── Tier a1: read_config_file / save_config ───────────────────────────────────

class TestReadConfigFile:
    def test_missing_file_returns_empty_dict(self, tmp_path):
        assert read_config_file(tmp_path / "nope.json") == {}

    def test_bad_json_returns_empty_dict(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("not valid json", encoding="utf-8")
        assert read_config_file(bad) == {}

    def test_reads_valid_json(self, tmp_path):
        cfg = {"provider": "ollama", "score": 80.0}
        path = tmp_path / "config.json"
        path.write_text(json.dumps(cfg), encoding="utf-8")
        assert read_config_file(path) == cfg


class TestSaveConfig:
    def test_creates_file(self, tmp_path):
        path = tmp_path / "sub" / "config.json"
        save_config({"provider": "stub"}, path)
        assert path.exists()

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "a" / "b" / "c" / "config.json"
        save_config({}, path)
        assert path.parent.is_dir()

    def test_round_trip(self, tmp_path):
        cfg = {"provider": "gemini", "auto_apply": True, "score": 90.0}
        path = tmp_path / "config.json"
        save_config(cfg, path)
        assert read_config_file(path) == cfg

    def test_output_is_pretty_json(self, tmp_path):
        path = tmp_path / "config.json"
        save_config({"k": "v"}, path)
        raw = path.read_text(encoding="utf-8")
        assert "\n" in raw  # pretty-printed


# ── Tier a1: merge_configs ────────────────────────────────────────────────────

class TestMergeConfigs:
    def test_local_wins_over_global_and_defaults(self):
        result = merge_configs({"x": 1}, {"x": 2}, {"x": 9})
        assert result["x"] == 1

    def test_global_wins_over_defaults(self):
        result = merge_configs({}, {"x": 2}, {"x": 9})
        assert result["x"] == 2

    def test_defaults_fill_missing_keys(self):
        result = merge_configs({}, {}, {"a": 1, "b": 2})
        assert result == {"a": 1, "b": 2}

    def test_none_in_local_skipped_falls_to_global(self):
        result = merge_configs({"p": None}, {"p": "gemini"}, {"p": "auto"})
        assert result["p"] == "gemini"

    def test_none_in_global_skipped_falls_to_defaults(self):
        result = merge_configs({}, {"p": None}, {"p": "auto"})
        assert result["p"] == "auto"

    def test_full_three_layer_priority(self):
        result = merge_configs(
            {"a": 1},
            {"a": 2, "b": 3},
            {"a": 9, "b": 9, "c": 9},
        )
        assert result == {"a": 1, "b": 3, "c": 9}

    def test_empty_all_layers_returns_empty(self):
        assert merge_configs({}, {}, {}) == {}


# ── Tier a1: load_config ──────────────────────────────────────────────────────

class TestLoadConfig:
    def test_returns_dict(self, tmp_path):
        assert isinstance(load_config(tmp_path), dict)

    def test_falls_back_to_defaults_when_no_files(self, tmp_path):
        cfg = load_config(tmp_path)
        assert cfg["provider"] == DEFAULT_CONFIG["provider"]
        assert cfg["default_target_score"] == DEFAULT_CONFIG["default_target_score"]

    def test_local_config_overrides_defaults(self, tmp_path):
        local_dir = tmp_path / LOCAL_CONFIG_DIR
        local_dir.mkdir()
        (local_dir / CONFIG_FILE_NAME).write_text(
            json.dumps({"provider": "anthropic"}), encoding="utf-8"
        )
        cfg = load_config(tmp_path)
        assert cfg["provider"] == "anthropic"

    def test_local_config_merges_with_defaults(self, tmp_path):
        local_dir = tmp_path / LOCAL_CONFIG_DIR
        local_dir.mkdir()
        (local_dir / CONFIG_FILE_NAME).write_text(
            json.dumps({"provider": "gemini"}), encoding="utf-8"
        )
        cfg = load_config(tmp_path)
        # Local key present
        assert cfg["provider"] == "gemini"
        # Defaults still filled in
        assert "auto_apply" in cfg
        assert "output_dir" in cfg

    def test_all_default_keys_present_even_without_local_file(self, tmp_path):
        cfg = load_config(tmp_path)
        for key in DEFAULT_CONFIG:
            assert key in cfg, f"Missing key {key!r} in loaded config"


# ── Tier a1: validate_config ──────────────────────────────────────────────────

class TestValidateConfig:
    def test_default_config_is_valid(self):
        assert validate_config(dict(DEFAULT_CONFIG)) == []

    def test_all_valid_providers_accepted(self):
        for p in ("auto", "ollama", "gemini", "anthropic", "openai", "stub"):
            cfg = {**DEFAULT_CONFIG, "provider": p}
            issues = validate_config(cfg)
            assert not any("Unknown provider" in i for i in issues), \
                f"Provider {p!r} was unexpectedly rejected"

    def test_invalid_provider_raises_issue(self):
        cfg = {**DEFAULT_CONFIG, "provider": "banana"}
        issues = validate_config(cfg)
        assert any("banana" in i or "provider" in i.lower() for i in issues)

    def test_score_above_100_raises_issue(self):
        cfg = {**DEFAULT_CONFIG, "default_target_score": 150.0}
        issues = validate_config(cfg)
        assert len(issues) > 0

    def test_score_below_0_raises_issue(self):
        cfg = {**DEFAULT_CONFIG, "default_target_score": -1.0}
        issues = validate_config(cfg)
        assert len(issues) > 0

    def test_score_exactly_0_is_valid(self):
        cfg = {**DEFAULT_CONFIG, "default_target_score": 0.0}
        assert validate_config(cfg) == []

    def test_score_exactly_100_is_valid(self):
        cfg = {**DEFAULT_CONFIG, "default_target_score": 100.0}
        assert validate_config(cfg) == []

    def test_bad_ollama_url_raises_issue(self):
        cfg = {**DEFAULT_CONFIG, "ollama_url": "ftp://not-valid"}
        issues = validate_config(cfg)
        assert any("ollama_url" in i or "http" in i for i in issues)

    def test_valid_https_ollama_url_accepted(self):
        cfg = {**DEFAULT_CONFIG, "ollama_url": "https://my-ollama-server.example.com"}
        issues = validate_config(cfg)
        assert not any("ollama_url" in i for i in issues)

    def test_empty_ollama_url_is_valid(self):
        cfg = {**DEFAULT_CONFIG, "ollama_url": ""}
        assert validate_config(cfg) == []


# ── Tier a1: provider_detect ──────────────────────────────────────────────────

class TestDetectOllama:
    def test_unavailable_when_urlopen_raises(self, monkeypatch):
        def _fail(*_args, **_kwargs):
            raise urllib.error.URLError("connection refused")
        monkeypatch.setattr("urllib.request.urlopen", _fail)

        result = detect_ollama("http://localhost:11434")
        assert result["available"] is False
        assert result["models"] == []
        assert result["latency_ms"] == 0

    def test_unavailable_on_oserror(self, monkeypatch):
        def _fail(*_args, **_kwargs):
            raise OSError("no route")
        monkeypatch.setattr("urllib.request.urlopen", _fail)

        result = detect_ollama("http://localhost:11434")
        assert result["available"] is False

    def test_url_preserved_in_result(self, monkeypatch):
        def _fail(*_args, **_kwargs):
            raise urllib.error.URLError("refused")
        monkeypatch.setattr("urllib.request.urlopen", _fail)

        url = "http://myhost:9999"
        result = detect_ollama(url)
        assert result["url"] == url


class TestListOllamaModels:
    def test_returns_empty_list_when_unavailable(self, monkeypatch):
        def _fail(*_args, **_kwargs):
            raise urllib.error.URLError("refused")
        monkeypatch.setattr("urllib.request.urlopen", _fail)

        assert list_ollama_models("http://localhost:11434") == []


class TestTestProvider:
    def test_unknown_provider_returns_not_ok(self):
        result = check_provider("purple-unicorn", {})
        assert result["ok"] is False
        assert "Unknown provider" in (result["error"] or "")

    def test_stub_provider_always_ok(self):
        result = check_provider("stub", {})
        assert result["ok"] is True
        assert result["model"] == "stub"
        assert result["error"] is None

    def test_gemini_without_key_returns_not_ok(self):
        result = check_provider("gemini", {"gemini_key": None})
        assert result["ok"] is False
        assert "gemini_key" in (result["error"] or "")

    def test_anthropic_without_key_returns_not_ok(self):
        result = check_provider("anthropic", {"anthropic_key": None})
        assert result["ok"] is False
        assert "anthropic_key" in (result["error"] or "")

    def test_openai_without_key_returns_not_ok(self):
        result = check_provider("openai", {"openai_key": None})
        assert result["ok"] is False
        assert "openai_key" in (result["error"] or "")

    def test_auto_without_ollama_or_keys_returns_not_ok(self, monkeypatch):
        def _fail(*_args, **_kwargs):
            raise urllib.error.URLError("refused")
        monkeypatch.setattr("urllib.request.urlopen", _fail)

        result = check_provider("auto", dict(DEFAULT_CONFIG))
        assert result["ok"] is False

    def test_result_shape_always_present(self):
        for p in ("gemini", "anthropic", "openai", "stub", "unknown"):
            result = check_provider(p, {})
            assert "ok" in result
            assert "model" in result
            assert "error" in result
            assert "latency_ms" in result


# ── CLI smoke: forge config show / forge init --help ─────────────────────────

class TestCliSmoke:
    def test_config_show_runs(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["config", "show", "--project", str(tmp_path)])
        assert result.exit_code == 0
        assert "provider" in result.stdout

    def test_config_show_json(self, tmp_path):
        result = runner.invoke(app, ["config", "show", "--json",
                                      "--project", str(tmp_path)])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "config" in data
        assert "issues" in data

    def test_config_set_writes_value(self, tmp_path):
        result = runner.invoke(app, [
            "config", "set", "provider", "stub",
            "--project", str(tmp_path),
        ])
        assert result.exit_code == 0
        cfg_path = tmp_path / LOCAL_CONFIG_DIR / CONFIG_FILE_NAME
        assert cfg_path.exists()
        saved = json.loads(cfg_path.read_text())
        assert saved["provider"] == "stub"

    def test_config_set_coerces_bool(self, tmp_path):
        runner.invoke(app, ["config", "set", "auto_apply", "true",
                             "--project", str(tmp_path)])
        cfg_path = tmp_path / LOCAL_CONFIG_DIR / CONFIG_FILE_NAME
        saved = json.loads(cfg_path.read_text())
        assert saved["auto_apply"] is True

    def test_config_set_coerces_float(self, tmp_path):
        runner.invoke(app, ["config", "set", "default_target_score", "80.5",
                             "--project", str(tmp_path)])
        cfg_path = tmp_path / LOCAL_CONFIG_DIR / CONFIG_FILE_NAME
        saved = json.loads(cfg_path.read_text())
        assert saved["default_target_score"] == pytest.approx(80.5)

    def test_config_test_json(self, tmp_path):
        result = runner.invoke(app, [
            "config", "test", "--json", "--provider", "stub",
            "--project", str(tmp_path),
        ])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["ok"] is True

    def test_init_help(self):
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "wizard" in result.stdout.lower() or "setup" in result.stdout.lower()

    def test_config_help(self):
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "wizard" in result.stdout.lower() or "show" in result.stdout.lower()
