"""Tier a1 — render a Forge Receipt as a 60×24 box-drawing card.

Golden Path Lane A W1 (paired with ``receipt_emitter.py``). This
renderer is what the "62 → 5" 30-second viral demo (Lane E W2)
screen-grabs and what ``forge auto`` / ``forge certify`` print at the
bottom of a successful run.

Pure: takes a Receipt dict and returns a string. No I/O, no imports
above a0. Snapshot-tested at ~60 columns wide; height is variable
but bounded (target ≤ 24 rows for 'fits in one mobile screenshot').

Style notes (so the output stays visually consistent across releases):
  * Single-line box drawing characters (U+2500..U+257F)
  * Title bar uses U+2550 (heavy horizontal) for visual weight
  * Verdict color hint emitted as a leading symbol (✓ / ✗ / ↻ / ⏸)
    so terminals without color can still distinguish the four
    verdicts. Caller may wrap with ANSI if desired.
  * Numeric fields right-aligned; labels left-aligned; one column of
    padding per side. No tabs, no trailing whitespace per row.
"""
from __future__ import annotations

from typing import Any

from ..a0_qk_constants.receipt_schema import ForgeReceiptV1, VALID_VERDICTS


_VERDICT_GLYPH: dict[str, str] = {
    "PASS":       "✓",
    "FAIL":       "✗",
    "REFINE":     "↻",
    "QUARANTINE": "⏸",
}


def _truncate(text: str, max_len: int) -> str:
    """Truncate ``text`` to ``max_len`` characters, adding an ellipsis
    when shortened. Returns ``text`` unchanged when already short enough.
    """
    if max_len <= 1:
        return text[:max_len]
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def _row(left: str, right: str, *, width: int) -> str:
    """Format a single content row inside a card of total ``width``.

    Layout: │ <left> .... <right> │
    Inner width = width - 4 (two box chars + two single-space pads).
    """
    inner = width - 4
    if inner <= 0:
        return ""
    if not right:
        return f"│ {_truncate(left, inner):<{inner}} │"
    pad = inner - len(left) - len(right)
    if pad < 1:
        # Right-align right; truncate left.
        max_left = max(0, inner - len(right) - 1)
        left = _truncate(left, max_left)
        pad = inner - len(left) - len(right)
        pad = max(1, pad)
    return f"│ {left}{' ' * pad}{right} │"


def _hr(width: int, *, heavy: bool = False) -> str:
    char = "═" if heavy else "─"
    return ("╔" if heavy else "├") + char * (width - 2) + ("╗" if heavy else "┤")


def _top(width: int) -> str:
    return "╔" + "═" * (width - 2) + "╗"


def _bottom(width: int) -> str:
    return "╚" + "═" * (width - 2) + "╝"


def _mid(width: int) -> str:
    return "├" + "─" * (width - 2) + "┤"


def _verdict_line(receipt: ForgeReceiptV1, *, width: int) -> str:
    verdict = str(receipt.get("verdict", "FAIL"))
    glyph = _VERDICT_GLYPH.get(verdict, "?")
    return _row(f"{glyph} {verdict}",
                f"forge {receipt.get('forge_version', '?')}",
                width=width)


def _certify_lines(receipt: ForgeReceiptV1, *, width: int) -> list[str]:
    cert: dict[str, Any] = dict(receipt.get("certify", {}))  # type: ignore[arg-type]
    score = cert.get("score", 0.0)
    axes: dict[str, Any] = dict(cert.get("axes", {}))  # type: ignore[arg-type]
    flag_glyph = lambda b: "✓" if b else "✗"  # noqa: E731
    rows: list[str] = []
    rows.append(_row("CERTIFY", f"{score:>5.1f} / 100", width=width))
    rows.append(_row(
        f"  docs {flag_glyph(axes.get('documentation_complete'))}  "
        f"tests {flag_glyph(axes.get('tests_present'))}  "
        f"layout {flag_glyph(axes.get('tier_layout_present'))}  "
        f"wire {flag_glyph(axes.get('no_upward_imports'))}",
        "",
        width=width,
    ))
    return rows


def _wire_line(receipt: ForgeReceiptV1, *, width: int) -> str:
    wire: dict[str, Any] = dict(receipt.get("wire", {}))  # type: ignore[arg-type]
    verdict = wire.get("verdict", "FAIL")
    n = wire.get("violation_count", 0)
    fixable = wire.get("auto_fixable", 0)
    if fixable:
        return _row("WIRE", f"{verdict}  ({n} viol, {fixable} auto-fix)",
                    width=width)
    return _row("WIRE", f"{verdict}  ({n} violation{'' if n == 1 else 's'})",
                width=width)


def _scout_line(receipt: ForgeReceiptV1, *, width: int) -> str:
    scout: dict[str, Any] = dict(receipt.get("scout", {}))  # type: ignore[arg-type]
    sym = scout.get("symbol_count", 0)
    lang = scout.get("primary_language", "?")
    tiers = scout.get("tier_distribution", {}) or {}
    tier_total = sum(int(v) for v in tiers.values())
    return _row(
        f"SCOUT  {sym} symbol{'' if sym == 1 else 's'}  ({lang})",
        f"{tier_total} tier-placed",
        width=width,
    )


def _project_line(receipt: ForgeReceiptV1, *, width: int) -> str:
    proj: dict[str, Any] = dict(receipt.get("project", {}))  # type: ignore[arg-type]
    name = str(proj.get("name", "?"))
    vcs: dict[str, Any] = dict(proj.get("vcs") or {})  # type: ignore[arg-type]
    short = vcs.get("short_sha") or vcs.get("head_sha", "")[:7]
    branch = vcs.get("branch")
    if short and branch:
        right = f"{branch}@{short}"
    elif short:
        right = short
    else:
        right = ""
    return _row(name, right, width=width)


def _attestation_line(receipt: ForgeReceiptV1, *, width: int) -> str:
    att: dict[str, Any] = dict(receipt.get("lean4_attestation") or {})  # type: ignore[arg-type]
    total = att.get("total_theorems", 0)
    if not total:
        return _row("LEAN4  (no attestation)", "", width=width)
    corpora = att.get("corpora") or []
    corpus_count = len(corpora)
    return _row(
        f"LEAN4  {total} theorem{'' if total == 1 else 's'} "
        f"across {corpus_count} corpus{'' if corpus_count == 1 else 'es'}",
        "0 sorry",
        width=width,
    )


def _signature_line(receipt: ForgeReceiptV1, *, width: int) -> str:
    sigs: dict[str, Any] = dict(receipt.get("signatures") or {})  # type: ignore[arg-type]
    has_sigstore = bool(sigs.get("sigstore"))
    has_nexus = bool(sigs.get("aaaa_nexus"))
    if has_sigstore and has_nexus:
        return _row("SIGNED  Sigstore + AAAA-Nexus", "", width=width)
    if has_sigstore:
        return _row("SIGNED  Sigstore", "", width=width)
    if has_nexus:
        return _row("SIGNED  AAAA-Nexus", "", width=width)
    return _row("UNSIGNED  (run --sign to attest)", "", width=width)


def render_receipt_card(
    receipt: ForgeReceiptV1,
    *,
    width: int = 60,
) -> str:
    """Render a Receipt as a multi-line box-drawing card.

    ``width`` defaults to 60. Terminal widths < 40 will look cramped
    (every label gets truncated); the function never raises on small
    widths but the output is best-effort below 40.
    """
    if width < 20:
        raise ValueError("card width must be >= 20")
    verdict = str(receipt.get("verdict", "FAIL"))
    if verdict not in VALID_VERDICTS:
        verdict = "FAIL"

    lines: list[str] = []
    lines.append(_top(width))
    title = "Atomadic Forge Receipt"
    lines.append(_row(title, receipt.get("schema_version", "?"), width=width))
    lines.append(_mid(width))
    lines.append(_verdict_line(receipt, width=width))
    lines.append(_project_line(receipt, width=width))
    lines.append(_mid(width))
    lines.extend(_certify_lines(receipt, width=width))
    lines.append(_wire_line(receipt, width=width))
    lines.append(_scout_line(receipt, width=width))
    lines.append(_mid(width))
    lines.append(_attestation_line(receipt, width=width))
    lines.append(_signature_line(receipt, width=width))
    ts = str(receipt.get("generated_at_utc", "?"))
    lines.append(_row("emitted", ts, width=width))
    lines.append(_bottom(width))
    return "\n".join(lines)
