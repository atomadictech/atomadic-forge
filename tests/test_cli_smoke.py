"""Smoke tests against the unified CLI entry."""

import json

import typer.testing

from atomadic_forge.a4_sy_orchestration.cli import app

runner = typer.testing.CliRunner()


def test_doctor_runs():
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "atomadic_forge_version" in data


def test_help_lists_chat():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "chat" in result.stdout


def test_recon_runs(sample_repo):
    result = runner.invoke(app, ["recon", str(sample_repo), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["python_file_count"] == 2


def test_auto_dry_run(tmp_path, sample_repo):
    output = tmp_path / "out"
    output.mkdir()
    result = runner.invoke(
        app, ["auto", str(sample_repo), str(output), "--json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["applied"] is False


def test_auto_apply(tmp_path, sample_repo):
    output = tmp_path / "out"
    output.mkdir()
    result = runner.invoke(
        app, ["auto", str(sample_repo), str(output), "--apply",
              "--package", "absorbed_smoke", "--json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["applied"] is True
    assert (output / "STATUS.md").exists()
    assert (output / "src" / "absorbed_smoke" / "a1_at_functions").exists()


def test_certify_runs(tmp_path, sample_repo):
    output = tmp_path / "out"
    output.mkdir()
    runner.invoke(app, ["auto", str(sample_repo), str(output), "--apply",
                         "--package", "absorbed_cert"])
    result = runner.invoke(app, ["certify", str(output),
                                  "--package", "absorbed_cert", "--json"])
    assert result.exit_code in (0, 1)  # may FAIL if no docs/tests added — schema-valid either way
    data = json.loads(result.stdout)
    assert data["schema_version"] == "atomadic-forge.certify/v1"


def test_certify_fail_under_controls_exit_status(tmp_path, sample_repo):
    output = tmp_path / "out"
    output.mkdir()
    runner.invoke(app, ["auto", str(sample_repo), str(output), "--apply",
                         "--package", "absorbed_gate"])
    result = runner.invoke(app, ["certify", str(output),
                                  "--package", "absorbed_gate",
                                  "--fail-under", "100", "--json"])
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["score"] < 100


def test_evolve_runtime_errors_are_cli_friendly(monkeypatch, tmp_path):
    from atomadic_forge.commands import evolve as evolve_cmd

    def _boom(*args, **kwargs):
        raise RuntimeError("local provider unavailable")

    monkeypatch.setattr(evolve_cmd, "run_evolve", _boom)
    result = runner.invoke(
        app,
        ["evolve", "run", "build", str(tmp_path / "out"), "--provider", "stub"],
    )
    combined = result.output + getattr(result, "stderr", "")
    assert result.exit_code != 0
    assert "local provider unavailable" in combined
    assert "Traceback" not in combined
