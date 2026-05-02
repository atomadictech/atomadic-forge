"""Tier a1 — runtime import smoke for a generated package.

Wire/tier discipline tells you the architecture is legal.  It does NOT
tell you the code actually loads — a syntax error, a missing import, or a
relative-import gone wrong all pass wire-check but fail at runtime.

This module spawns a Python subprocess and tries
``python -c "import <pkg>"`` with the appropriate ``PYTHONPATH``.  Returns
a structured report Forge can fold into certify and into LLM feedback.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TypedDict


class ImportSmokeReport(TypedDict):
    schema_version: str       # "atomadic-forge.import_smoke/v1"
    package: str
    src_root: str
    importable: bool
    duration_ms: int
    error_kind: str           # "" | "SyntaxError" | "ImportError" | "ModuleNotFoundError" | "Other"
    error_message: str        # short
    traceback_excerpt: str    # last ~600 chars of stderr


def _classify_error(stderr: str) -> str:
    if not stderr:
        return ""
    lowered_lines = [ln for ln in stderr.splitlines() if ln.strip()]
    last = lowered_lines[-1] if lowered_lines else ""
    for kind in ("ModuleNotFoundError", "ImportError", "SyntaxError",
                 "AttributeError", "NameError", "TypeError",
                 "IndentationError"):
        if kind in last or kind in stderr:
            return kind
    return "Other"


def _short_message(stderr: str) -> str:
    if not stderr:
        return ""
    lines = [ln for ln in stderr.splitlines() if ln.strip()]
    return lines[-1][:200] if lines else stderr[:200]


def import_smoke(*, output_root: Path, package: str,
                 timeout_s: float = 30.0) -> ImportSmokeReport:
    """Try ``python -c 'import <package>'`` with src-layout PYTHONPATH.

    ``output_root`` is the parent of ``src/`` (the directory that contains
    a ``src/<package>/`` materialized by Forge).
    """
    output_root = Path(output_root).resolve()
    src_root = output_root / "src"
    if not (src_root / package).exists():
        return ImportSmokeReport(
            schema_version="atomadic-forge.import_smoke/v1",
            package=package, src_root=str(src_root),
            importable=False, duration_ms=0,
            error_kind="ModuleNotFoundError",
            error_message=f"package {package!r} not present under {src_root}",
            traceback_excerpt="",
        )
    import time
    env = {**__import__("os").environ}
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (str(src_root) + (";" if existing_pp else "") + existing_pp
                          if sys.platform == "win32"
                          else str(src_root) + (":" if existing_pp else "") + existing_pp)
    env["PYTHONIOENCODING"] = "utf-8"
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, "-c", f"import {package}"],
            env=env, capture_output=True, text=True, timeout=timeout_s,
            encoding="utf-8", errors="replace",
        )
        duration_ms = int((time.perf_counter() - start) * 1000)
    except subprocess.TimeoutExpired:
        return ImportSmokeReport(
            schema_version="atomadic-forge.import_smoke/v1",
            package=package, src_root=str(src_root),
            importable=False, duration_ms=int(timeout_s * 1000),
            error_kind="TimeoutExpired",
            error_message=f"import timed out after {timeout_s}s",
            traceback_excerpt="",
        )
    importable = proc.returncode == 0
    stderr = proc.stderr or ""
    return ImportSmokeReport(
        schema_version="atomadic-forge.import_smoke/v1",
        package=package, src_root=str(src_root),
        importable=importable, duration_ms=duration_ms,
        error_kind="" if importable else _classify_error(stderr),
        error_message="" if importable else _short_message(stderr),
        traceback_excerpt="" if importable else stderr[-600:],
    )
