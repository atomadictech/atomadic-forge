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


_SUMMARY_RE = re.compile(
    r"(?:(\d+)\s+failed)?,?\s*(?:(\d+)\s+passed)?,?\s*"
    r"(?:(\d+)\s+error)?,?\s*(?:(\d+)\s+skipped)?",
    re.IGNORECASE,
)
# Pytest's terminal summary line — matches both decorated and -q forms:
#   "===== 3 passed, 1 failed in 0.42s ====="
#   "1 passed in 0.03s"
#   "2 failed, 3 passed in 1.12s"
_FINAL_LINE_RE = re.compile(
    r"=*\s*"
    r"(?:(\d+)\s+failed)?,?\s*"
    r"(?:(\d+)\s+passed)?,?\s*"
    r"(?:(\d+)\s+error[s]?)?,?\s*"
    r"(?:(\d+)\s+skipped)?\s*"
    r"in\s+[\d.]+s",
    re.IGNORECASE,
)


def _parse_pytest_summary(stdout: str) -> tuple[int, int, int, int]:
    """Return ``(passed, failed, errors, skipped)`` parsed from pytest stdout."""
    passed = failed = errors = skipped = 0
    for line in reversed(stdout.splitlines()):
        m = _FINAL_LINE_RE.search(line)
        if m:
            failed = int(m.group(1) or 0)
            passed = int(m.group(2) or 0)
            errors = int(m.group(3) or 0)
            skipped = int(m.group(4) or 0)
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


def run_pytest(*, output_root: Path, package: str | None = None,
               tests_subdir: str = "tests",
               timeout_s: float = 60.0) -> TestRunReport:
    """Run ``pytest <tests_subdir>`` inside ``output_root``.

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
    env = {**os.environ}
    pp = env.get("PYTHONPATH", "")
    sep = ";" if sys.platform == "win32" else ":"
    new_pp = str(src_root) if not pp else f"{src_root}{sep}{pp}"
    env["PYTHONPATH"] = new_pp
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

    start = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(tests_dir),
             "--tb=line", "-q", "--no-header", "-p", "no:cacheprovider"],
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
