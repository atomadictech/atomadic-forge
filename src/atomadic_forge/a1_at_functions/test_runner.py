"""Tier a1 — pure pytest runner for the generated package.

After every iterate turn, Forge runs ``pytest tests/`` against the
emitted code and credits the certify score by the pass-ratio.  This is
the *behavioral* check — wire/import says the package loads, but only a
running test says it actually does what was asked.

The runner is subprocess-based so it isolates from the parent process
state.  Returns a structured report with passed/failed/error counts plus
the trimmed pytest stdout/stderr for LLM feedback.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import TypedDict


class TestRunReport(TypedDict):
    schema_version: str        # "atomadic-forge.test_run/v1"
    tests_dir: str
    ran: bool                  # were any tests collected?
    passed: int
    failed: int
    errors: int
    skipped: int
    total: int
    pass_ratio: float          # 0.0 .. 1.0
    duration_ms: int
    pytest_summary: str        # last ~30 lines of stdout
    failure_excerpts: list[str]  # top-N failed test names + first lines of traceback


# Five independent per-metric patterns: each looks for its own keyword
# followed by a space and a count.  A single "in X.Xs" anchor line is
# required so we only match the final summary line, not progress dots.
# This tolerates xfailed/xpassed/deselected words between the counts.
_PYTEST_IN_RE      = re.compile(r"\bin\s+[\d.]+s", re.IGNORECASE)
_PYTEST_FAILED_RE  = re.compile(r"(\d+)\s+failed",  re.IGNORECASE)
_PYTEST_PASSED_RE  = re.compile(r"(\d+)\s+passed",  re.IGNORECASE)
_PYTEST_ERROR_RE   = re.compile(r"(\d+)\s+error",   re.IGNORECASE)
_PYTEST_SKIPPED_RE = re.compile(r"(\d+)\s+skipped", re.IGNORECASE)


def _parse_pytest_summary(stdout: str) -> tuple[int, int, int, int]:
    """Return ``(passed, failed, errors, skipped)`` parsed from pytest stdout."""
    passed = failed = errors = skipped = 0
    for line in reversed(stdout.splitlines()):
        if not _PYTEST_IN_RE.search(line):
            continue
        m = _PYTEST_FAILED_RE.search(line)
        if m:
            failed = int(m.group(1))
        m = _PYTEST_PASSED_RE.search(line)
        if m:
            passed = int(m.group(1))
        m = _PYTEST_ERROR_RE.search(line)
        if m:
            errors = int(m.group(1))
        m = _PYTEST_SKIPPED_RE.search(line)
        if m:
            skipped = int(m.group(1))
        break
    return passed, failed, errors, skipped

def _extract_failure_excerpts(stdout: str, max_failures: int = 5) -> list[str]:
    """Pull the FAILED test ids + a short excerpt of each traceback."""
    out: list[str] = []
    failed_ids: list[str] = []
    for line in stdout.splitlines():
        if line.startswith("FAILED "):
            # format: "FAILED tests/test_x.py::test_y - AssertionError: ..."
            failed_ids.append(line.replace("FAILED ", "").strip())
    for fid in failed_ids[:max_failures]:
        out.append(fid)
    return out


def _filter_tests_to_package(tests_dir: Path, package: str) -> list[str]:
    """Return list of test file paths whose imports reference ``package``.

    Closes the wrong-package gameability hole: an LLM that emits files into
    `forge_greeter` but tests for `forge_greeter` shouldn't credit the
    behavioural score against a request for `mdconv`.  This requires every
    counted test file to import the requested package.
    """
    out: list[str] = []
    for f in sorted(tests_dir.rglob("test_*.py")):
        if "__pycache__" in f.parts:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Match `from <pkg>.…` or `import <pkg>` (word-boundary).
        if re.search(rf"\b(?:from|import)\s+{re.escape(package)}\b", text):
            out.append(str(f))
    return out


def run_pytest(*, output_root: Path, package: str | None = None,
               tests_subdir: str = "tests",
               timeout_s: float = 60.0) -> TestRunReport:
    """Run ``pytest <tests_subdir>`` inside ``output_root``.

    When ``package`` is given, ONLY tests that import that package count
    toward the pass-ratio.  This prevents wrong-package gaming where the
    LLM emits code into ``forge_greeter`` but the request was ``mdconv`` —
    forge_greeter's tests would otherwise credit the score.

    ``PYTHONPATH`` is set so ``src/`` is importable without a pip install.
    Skips cleanly when the tests dir doesn't exist.
    """
    import time
    output_root = Path(output_root).resolve()
    tests_dir = output_root / tests_subdir
    src_root = output_root / "src"
    if not tests_dir.exists():
        return TestRunReport(
            schema_version="atomadic-forge.test_run/v1",
            tests_dir=str(tests_dir), ran=False, passed=0, failed=0,
            errors=0, skipped=0, total=0, pass_ratio=0.0, duration_ms=0,
            pytest_summary="(no tests/ directory)",
            failure_excerpts=[],
        )

    # Filter to tests that actually target the requested package.
    targeted: list[str] | None = None
    if package:
        targeted = _filter_tests_to_package(tests_dir, package)
        if not targeted:
            return TestRunReport(
                schema_version="atomadic-forge.test_run/v1",
                tests_dir=str(tests_dir), ran=True, passed=0, failed=0,
                errors=0, skipped=0, total=0, pass_ratio=0.0, duration_ms=0,
                pytest_summary=(
                    f"(no test files import package {package!r} — refused to "
                    "credit unrelated tests)"
                ),
                failure_excerpts=[],
            )
    env = {**os.environ}
    pp = env.get("PYTHONPATH", "")
    sep = ";" if sys.platform == "win32" else ":"
    new_pp = str(src_root) if not pp else f"{src_root}{sep}{pp}"
    env["PYTHONPATH"] = new_pp
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

    pytest_targets = targeted if targeted else [str(tests_dir)]
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", *pytest_targets,
             "-o", "addopts=", "--tb=line", "-q", "--no-header",
             "-p", "no:cacheprovider"],
            cwd=str(output_root), env=env,
            capture_output=True, text=True, timeout=timeout_s,
            encoding="utf-8", errors="replace",
        )
        duration_ms = int((time.perf_counter() - start) * 1000)
    except subprocess.TimeoutExpired:
        return TestRunReport(
            schema_version="atomadic-forge.test_run/v1",
            tests_dir=str(tests_dir), ran=True, passed=0, failed=0,
            errors=1, skipped=0, total=1, pass_ratio=0.0,
            duration_ms=int(timeout_s * 1000),
            pytest_summary=f"timeout after {timeout_s}s",
            failure_excerpts=[],
        )

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    passed, failed, errors, skipped = _parse_pytest_summary(stdout)
    total = passed + failed + errors  # skipped doesn't count toward ratio
    ratio = (passed / total) if total > 0 else 0.0

    # The combined output is what we pass back to the LLM.
    summary_lines = (stdout + ("\n" + stderr if stderr else "")).splitlines()
    summary = "\n".join(summary_lines[-40:]).strip()

    return TestRunReport(
        schema_version="atomadic-forge.test_run/v1",
        tests_dir=str(tests_dir),
        ran=total > 0 or errors > 0,
        passed=passed, failed=failed, errors=errors, skipped=skipped,
        total=total, pass_ratio=ratio, duration_ms=duration_ms,
        pytest_summary=summary,
        failure_excerpts=_extract_failure_excerpts(stdout),
    )
