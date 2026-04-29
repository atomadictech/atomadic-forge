"""Tier a1 — pure compiler-feedback prompt builder for the fix-round loop.

Golden Path Lane A W3 deliverable. Distinct from the regular iterate
turn:

  * regular turn   — wire + certify scores → LLM is asked to *improve
                     quality* (raise the score, fix violations,
                     etc.). Bounded by ``max_iterations``.
  * fix-round turn — import_smoke FAIL (or pytest collection error)
                     → LLM is asked to *fix the broken code* without
                     adding features. Bounded by ``max_fix_rounds``
                     PER iterate turn.

A fix-round is much cheaper (one error trace, no quality scoring) and
should always run before the next regular turn — otherwise the
regular turn shows the LLM a ``score=0`` because the package didn't
even import, and the LLM wastes the round chasing scoring instead of
the actual blocker.

Pure: takes an ``ImportSmokeReport`` (or ImportSmoke-shaped dict) and
returns a string. No I/O, no LLM call. The forge_loop orchestrator
owns when to invoke this.
"""
from __future__ import annotations


_FIX_ROUND_HEADER = (
    "FIX ROUND — your previous emission did not import. Do NOT add "
    "features; do NOT touch unrelated files. Output ONLY the minimum "
    "set of files needed to make the package importable.\n"
)

_FIX_ROUND_FOOTER = (
    "\nRespond with the standard JSON array of `{path, content}` "
    "objects. If you believe the package is already correct and the "
    "error is environmental (e.g. a missing 3rd-party dep), output "
    "the exact two characters `[]` and the loop will exit.\n"
)


def pack_compile_feedback(
    smoke_report: dict,
    *,
    package: str,
    fix_round_index: int,
    max_fix_rounds: int,
) -> str:
    """Build the fix-round prompt from an ImportSmokeReport-shape dict.

    Arguments:
      smoke_report     — dict with at least ``error_kind``,
                         ``error_message``, ``traceback_excerpt``.
      package          — the package name being iterated.
      fix_round_index  — 1-based current attempt within this turn.
      max_fix_rounds   — total budget so the LLM knows whether to
                         minimise the fix or give up cleanly.
    """
    if fix_round_index < 1:
        raise ValueError("fix_round_index must be >= 1")
    if max_fix_rounds < 1:
        raise ValueError("max_fix_rounds must be >= 1")

    kind = str(smoke_report.get("error_kind") or "ImportFailure")
    message = str(smoke_report.get("error_message") or "(no message)")
    trace = str(smoke_report.get("traceback_excerpt") or "").strip()

    parts: list[str] = [
        _FIX_ROUND_HEADER,
        f"  package:           {package}",
        f"  fix-round attempt: {fix_round_index} of {max_fix_rounds}",
        f"  error_kind:        {kind}",
        f"  error_message:     {message}",
    ]
    if trace:
        # Cap to avoid blowing the context window — the smoke
        # collector already trims stderr to ~600 chars.
        parts.append("\nTraceback excerpt:\n```\n" + trace[:1200] + "\n```")
    parts.append(_FIX_ROUND_FOOTER)
    return "\n".join(parts)


def should_fix_round(smoke_report: dict) -> bool:
    """Return True iff the smoke report names a fixable runtime error.

    'Fixable' means: there's a concrete error_kind and non-empty
    message we can show the LLM. Empty smoke (importable=True) returns
    False; environmental failures with no useful trace also return
    False so the orchestrator skips the round rather than re-prompting
    the LLM with nothing.
    """
    if smoke_report.get("importable"):
        return False
    kind = smoke_report.get("error_kind") or ""
    message = smoke_report.get("error_message") or ""
    return bool(kind and message)
