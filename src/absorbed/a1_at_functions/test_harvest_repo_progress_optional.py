"""Tier verification — Lane B2: progress reporter + harvest_repo plumbing.

Covers the progress callback contract end-to-end:
  * pure callback: harvest_repo accepts a callable and invokes it once
    per source file with (idx, total, rel)
  * factory: make_stderr_reporter respects ``every`` and ``enabled``
  * CLI plumbing: ``forge recon --progress`` emits to stderr; ``--json``
    suppresses the reporter even when --progress is set.
"""
from __future__ import annotations

import io

import typer.testing

from atomadic_forge.a1_at_functions.progress_reporter import (
    make_stderr_reporter,
)
from atomadic_forge.a1_at_functions.scout_walk import harvest_repo
from atomadic_forge.a4_sy_orchestration.cli import app

runner = typer.testing.CliRunner()


def test_harvest_repo_invokes_progress_per_file(sample_repo):
    """harvest_repo calls progress(idx, total, rel) once per source file."""
    calls: list[tuple[int, int, str]] = []
    report = harvest_repo(sample_repo, progress=lambda i, t, r: calls.append((i, t, r)))
    assert report["python_file_count"] == 2
    assert len(calls) == 2
    assert calls[0][0] == 1 and calls[1][0] == 2  # 1-indexed
    assert all(c[1] == 2 for c in calls)  # total == 2
    assert {c[2] for c in calls} == {"pure.py", "io_runner.py"}


def test_harvest_repo_progress_optional(sample_repo):
    """progress=None must remain a valid call (default, no-op)."""
    report = harvest_repo(sample_repo)
    assert report["symbol_count"] >= 1


def test_stderr_reporter_disabled_when_not_tty():
    """A StringIO is not a TTY → the factory returns a no-op."""
    stream = io.StringIO()
    reporter = make_stderr_reporter(stream=stream, every=1)
    reporter(1, 10, "x.py")
    reporter(10, 10, "z.py")
    assert stream.getvalue() == ""


def test_stderr_reporter_force_enabled_writes_lines():
    stream = io.StringIO()
    reporter = make_stderr_reporter(stream=stream, every=1, enabled=True,
                                    label="test")
    reporter(1, 5, "a.py")
    reporter(2, 5, "b.py")
    out = stream.getvalue()
    assert "[test] processed 1/5" in out
    assert "[test] processed 2/5" in out
    assert "a.py" in out and "b.py" in out


def test_stderr_reporter_every_throttles():
    """``every=3`` → emit on indexes 3, 6, 9, and always on the final."""
    stream = io.StringIO()
    reporter = make_stderr_reporter(stream=stream, every=3, enabled=True)
    for i in range(1, 11):  # 10 files
        reporter(i, 10, f"f{i}.py")
    out = stream.getvalue()
    # Should see lines for 3, 6, 9, and 10 (final). Not 1, 2, 4, 5, 7, 8.
    assert "processed 3/10" in out
    assert "processed 6/10" in out
    assert "processed 9/10" in out
    assert "processed 10/10" in out
    assert "processed 1/10" not in out
    assert "processed 4/10" not in out


def test_stderr_reporter_invalid_every_raises():
    import pytest
    with pytest.raises(ValueError):
        make_stderr_reporter(every=0)


def test_recon_json_suppresses_progress(sample_repo):
    """--json output must not be polluted by progress lines (machine path)."""
    result = runner.invoke(
        app, ["recon", str(sample_repo), "--json", "--progress"]
    )
    assert result.exit_code == 0
    # stdout is the JSON; stderr would carry progress. CliRunner mixes
    # them by default — but our impl explicitly disables the reporter
    # when --json is set, so neither stream should contain the label.
    assert "[scout] processed" not in result.stdout
    assert "[scout] processed" not in (result.stderr or "")


def test_recon_no_progress_flag_does_not_crash(sample_repo):
    """Sanity: --no-progress short-circuits the reporter cleanly."""
    result = runner.invoke(
        app, ["recon", str(sample_repo), "--no-progress"]
    )
    assert result.exit_code == 0
