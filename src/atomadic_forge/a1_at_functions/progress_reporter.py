"""Tier a1 — progress reporter factories for long-running walks.

Provides callable factories that produce ``(idx, total, label) -> None``
reporters suitable for passing to ``scout_walk.harvest_repo`` (and any
future long-running pipeline phase).

Pure-by-construction: the factories themselves perform no I/O. The
returned reporter writes to whatever stream is passed in (default
``sys.stderr``), which keeps the side effect at the *call site* under
the caller's control. Tests can pass an ``io.StringIO``; the CLI layer
passes ``sys.stderr``; ``progress=None`` skips reporting entirely.

Used by Lane B2 of the post-audit plan: long-running ``forge auto`` /
``forge recon`` invocations on large repos previously gave no on-screen
feedback, so users couldn't tell the tool from a hung process. This
module is the cheap fix.
"""
from __future__ import annotations

import sys
from collections.abc import Callable
from typing import IO


def make_stderr_reporter(
    *,
    every: int = 25,
    enabled: bool | None = None,
    stream: IO[str] | None = None,
    label: str = "scout",
) -> Callable[[int, int, str], None]:
    """Return a progress callback that writes to ``stream`` (default stderr).

    Arguments:
        every:    Emit a line every Nth file (plus always at the final
                  file). Keep ≥ 1.
        enabled:  Force-enable / disable. ``None`` = auto-detect: emit
                  only when ``stream`` is a TTY. CI tasks (non-TTY) get
                  silence by default; an explicit ``enabled=True`` forces
                  output regardless.
        stream:   Defaults to ``sys.stderr``.
        label:    Short tag included in each line (``scout``, etc.).

    Returns:
        A pure callback ``progress(idx, total, rel)`` suitable for
        passing into ``harvest_repo``. When the reporter is disabled
        (TTY check fails and ``enabled is not True``), the callback is
        a no-op — *not* ``None`` — so callers can pass it unconditionally.
    """
    if every < 1:
        raise ValueError("`every` must be >= 1")

    target = stream if stream is not None else sys.stderr
    if enabled is None:
        try:
            active = bool(target.isatty())
        except (AttributeError, ValueError):
            active = False
    else:
        active = bool(enabled)

    if not active:
        def _noop(idx: int, total: int, rel: str) -> None:
            return None
        return _noop

    def _report(idx: int, total: int, rel: str) -> None:
        # Emit on every Nth file, plus always on the final one so the
        # user sees the closing 100%-of-N line.
        if idx == total or (idx % every) == 0:
            try:
                target.write(
                    f"  [{label}] processed {idx}/{total} files "
                    f"(latest: {rel})\n"
                )
                target.flush()
            except (OSError, ValueError):
                # Stream closed or detached mid-run — degrade silently.
                pass

    return _report
