"""Tier a1 — agent-native compact-blocker summaries.

Direct response to field feedback from Codex (the Atomadic-Lang
agent) after using earlier Forge releases:

> "Make tool outputs compact and explicitly actionable, because
>  agents thrive on 'here are the 2 things blocking release' more
>  than huge manifests."

Every Forge report (wire / certify / enforce) is structurally
correct but verbose. An agent consuming them via ``forge mcp serve``
or ``--json`` has to wade through dozens of KB to find the next
action. This module condenses any combination of those reports
into a 3-key shape:

    {
        "schema_version": "atomadic-forge.summary/v1",
        "verdict":        "PASS" | "FAIL" | ...,
        "score":          0-100,
        "blockers": [
            {"f_code": "F0050", "title": "...",
             "next_command": "echo '# my-pkg' > README.md",
             "severity": "error", "auto_fixable": true},
            ...
        ],
        "next_command":   "<the single fastest unblock>",
        "blocker_count":  N,
        "auto_fixable_count": M,
    }

Ranking is deterministic (so the same input always yields the same
ordered blockers): auto_fixable first (cheap wins), then by F-code
severity (error > warn > info), then by frequency in the report,
then by F-code value (lexicographic) as a tiebreak.

Pure: no I/O, no LLM call. The caller decides whether to print the
summary, embed it in an MCP response, or fold it into a Receipt's
notes field.
"""
from __future__ import annotations

from typing import Any, TypedDict

from ..a0_qk_constants.error_codes import (
    fcode_for_tier_violation,
    get_fcode,
)

_SEVERITY_RANK = {"error": 0, "warn": 1, "info": 2}


class Blocker(TypedDict, total=False):
    f_code: str
    title: str
    next_command: str
    severity: str
    auto_fixable: bool
    occurrences: int            # how many wire violations / issues fed this
    sample_path: str | None     # representative file (when applicable)


def _certify_blockers(
    certify_report: dict | None,
    *,
    package_root: str | None,
) -> list[Blocker]:
    if not certify_report:
        return []
    out: list[Blocker] = []
    if not certify_report.get("documentation_complete", True):
        out.append(_blocker(
            "F0050",
            next_command=(
                f"echo '# {package_root or 'your_package'}' > README.md"
                if package_root else "add a README.md with at least an H1 + a one-paragraph intro"
            ),
        ))
    if not certify_report.get("tests_present", True):
        out.append(_blocker(
            "F0051",
            next_command="mkdir -p tests && cat > tests/test_smoke.py "
                          "<<'PY'\nimport <pkg>\nPY",
        ))
    if not certify_report.get("tier_layout_present", True):
        out.append(_blocker(
            "F0052",
            next_command=(
                f"forge auto . ./out --apply --package "
                f"{package_root or 'your_pkg'}"
            ),
        ))
    if not certify_report.get("no_upward_imports", True):
        out.append(_blocker(
            "F0053",
            next_command=(
                f"forge wire {package_root or 'src/your_pkg'} "
                "--suggest-repairs && forge enforce "
                f"{package_root or 'src/your_pkg'} --apply"
            ),
        ))
    return out


def _wire_blockers(
    wire_report: dict | None,
    *,
    package_root: str | None,
) -> list[Blocker]:
    if not wire_report:
        return []
    violations = wire_report.get("violations") or []
    if not violations:
        return []
    # Group by F-code so duplicate violations of the same kind collapse
    # into one blocker with a sample path + occurrence count.
    by_fcode: dict[str, list[dict]] = {}
    for v in violations:
        code = v.get("f_code") or fcode_for_tier_violation(
            v.get("from_tier", ""), v.get("to_tier", ""))
        by_fcode.setdefault(code, []).append(v)
    out: list[Blocker] = []
    for code, group in by_fcode.items():
        sample = group[0]
        sample_file = sample.get("file", "")
        if get_fcode(code) and get_fcode(code).get("auto_fixable"):  # type: ignore[union-attr]
            cmd = (
                f"forge enforce {package_root or 'src/your_pkg'} --apply  "
                f"# resolves {code}"
            )
        else:
            cmd = (
                f"# review manually: {sample_file} cannot move mechanically; "
                "either invert the import direction or extract the symbol "
                "down to a lower tier."
            )
        out.append(_blocker(
            code,
            next_command=cmd,
            occurrences=len(group),
            sample_path=sample_file,
        ))
    return out


def _blocker(
    f_code: str,
    *,
    next_command: str,
    occurrences: int = 1,
    sample_path: str | None = None,
) -> Blocker:
    entry = get_fcode(f_code)
    if entry is None:
        return Blocker(
            f_code=f_code,
            title=f"unregistered F-code: {f_code}",
            next_command=next_command,
            severity="error",
            auto_fixable=False,
            occurrences=occurrences,
            sample_path=sample_path,
        )
    return Blocker(
        f_code=f_code,
        title=entry["title"],
        next_command=next_command,
        severity=entry["severity"],
        auto_fixable=entry["auto_fixable"],
        occurrences=occurrences,
        sample_path=sample_path,
    )


def _rank(blocker: Blocker) -> tuple[int, int, int, str]:
    """Stable ranking: auto_fixable first, then severity, then frequency
    (descending), then F-code lex order."""
    return (
        0 if blocker.get("auto_fixable") else 1,
        _SEVERITY_RANK.get(blocker.get("severity", "error"), 0),
        -int(blocker.get("occurrences", 1)),
        blocker.get("f_code", ""),
    )


def summarize_blockers(
    *,
    wire_report: dict | None = None,
    certify_report: dict | None = None,
    package_root: str | None = None,
    top_n: int = 5,
) -> dict[str, Any]:
    """Compact-blocker summary for agent consumption (Codex feedback).

    Either ``wire_report`` or ``certify_report`` (or both) may be
    None; the function returns whatever blockers it can derive.
    ``top_n`` (default 5) caps the returned blocker list — the
    blocker_count field always reflects the FULL count regardless.
    """
    if top_n < 1:
        raise ValueError("top_n must be >= 1")

    blockers = _certify_blockers(certify_report, package_root=package_root)
    blockers.extend(_wire_blockers(wire_report, package_root=package_root))
    blockers.sort(key=_rank)

    auto = sum(1 for b in blockers if b.get("auto_fixable"))
    # Codex feedback: bare-wire callers have no certify score; render
    # 'no score' instead of a misleading 0/100. None signals 'unknown'.
    score = (certify_report or {}).get("score") if certify_report is not None else None
    if certify_report is None and wire_report is not None:
        # Bare-wire callers: derive a coarse verdict from wire alone.
        verdict = wire_report.get("verdict", "FAIL")
    elif wire_report is not None and (certify_report or {}).get("score", 0) >= 100 \
            and wire_report.get("verdict") == "PASS":
        verdict = "PASS"
    elif certify_report is not None and not blockers:
        verdict = "PASS"
    else:
        verdict = "FAIL"

    next_command = blockers[0]["next_command"] if blockers else (
        "# already PASSing — re-run on the next change."
    )

    return {
        "schema_version": "atomadic-forge.summary/v1",
        "verdict": verdict,
        "score": score,
        "blocker_count": len(blockers),
        "auto_fixable_count": auto,
        "blockers": list(blockers[:top_n]),
        "next_command": next_command,
    }


def render_summary_text(summary: dict, *, width: int = 60) -> str:
    """Single-screen plain-text rendering of the summary.

    Designed for human terminals AND for agent consumption: every
    line is short, every blocker fits on 2 lines, the next-command
    is the very last visible row.
    """
    if width < 30:
        raise ValueError("width must be >= 30")
    lines: list[str] = []
    verdict = summary.get("verdict", "?")
    score = summary.get("score", 0)
    n = summary.get("blocker_count", 0)
    auto = summary.get("auto_fixable_count", 0)
    glyph = {"PASS": "✓", "FAIL": "✗", "REFINE": "↻", "QUARANTINE": "⏸"}.get(
        verdict, "?")
    score_part = (f"score {score:.0f}/100   "
                  if isinstance(score, int | float) else "")
    lines.append(f"{glyph} {verdict}   {score_part}"
                  f"{n} blocker{'' if n == 1 else 's'} "
                  f"({auto} auto-fixable)")
    lines.append("─" * width)
    if not summary.get("blockers"):
        lines.append("(no blockers)")
    for i, b in enumerate(summary.get("blockers", []), 1):
        tag = "AUTO" if b.get("auto_fixable") else "REVIEW"
        title = b.get("title", "")
        prefix = f" {i}. [{b.get('f_code', 'F????')}] [{tag}] "
        # Cap the WHOLE row at width, not just the title.
        budget = max(0, width - len(prefix))
        if len(title) > budget:
            title = title[: max(0, budget - 1)] + "…"
        lines.append(prefix + title)
        cmd = b.get("next_command", "").strip()
        if cmd:
            short = cmd if len(cmd) < width - 6 else cmd[: width - 7] + "…"
            lines.append(f"    → {short}")
    lines.append("─" * width)
    nc = summary.get("next_command", "").strip()
    if nc:
        lines.append(f"NEXT: {nc[: width - 6]}")
    return "\n".join(lines)
