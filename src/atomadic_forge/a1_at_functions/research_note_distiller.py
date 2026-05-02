"""Tier a1 - research note distiller.

Pure stateless distillation of research-note markdown into a single
compressed prompt suitable for one LLM inference call. Extracts H1
titles, Thesis lines, and backticked snake_case capability identifiers,
then emits a structured summary at well below 30% the original token
budget. CONTEXT + EVOLVE pillars.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_THESIS_RE = re.compile(r"\*\*Thesis:\*\*\s*(.+?)\s*$",
                          re.MULTILINE | re.IGNORECASE)
_IDENT_RE = re.compile(r"`([a-z][a-z0-9_]*)`")


@dataclass(frozen=True)
class DistilledNotes:
    total_notes: int
    total_chars_original: int
    total_chars_distilled: int
    compression_ratio: float
    unique_capabilities: list[str] = field(default_factory=list)
    prompt: str = ""


def _title(note: str) -> str:
    m = _TITLE_RE.search(note)
    return m.group(1).strip() if m else ""


def _thesis(note: str) -> str:
    m = _THESIS_RE.search(note)
    return m.group(1).strip() if m else ""


def _idents(note: str) -> list[str]:
    return list(_IDENT_RE.findall(note))


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def distill_notes(notes: list[str]) -> DistilledNotes:
    """Compress a batch of research notes into one structured prompt."""
    total_notes = len(notes)
    total_orig = sum(len(n) for n in notes)
    if total_notes == 0:
        empty = ("## Distilled research input (0 notes)\n\n"
                 "### Topics\n- (no titled notes)\n\n"
                 "### Capability identifiers proposed\n- (none extracted)\n\n"
                 "### Note volume\n0 notes, 0 -> 0 chars (0.00x)\n")
        return DistilledNotes(0, 0, len(empty), 0.0, [], empty)
    pairs = [(_title(n), _thesis(n)) for n in notes]
    all_idents: list[str] = []
    for n in notes:
        all_idents.extend(_idents(n))
    unique = _dedupe(all_idents)
    topics = "\n".join(
        f"- {t or '(untitled)'}: {th or '(no thesis)'}" for t, th in pairs
    ) or "- (no titled notes)"
    caps = ("- " + ", ".join(f"`{c}`" for c in unique)
            if unique else "- (none extracted)")
    body = (
        f"## Distilled research input ({total_notes} notes)\n\n"
        f"### Topics\n{topics}\n\n"
        f"### Capability identifiers proposed\n{caps}\n\n"
        f"### Note volume\n"
    )
    provisional = body + f"{total_notes} notes, {total_orig} -> 0 chars (0.00x)\n"
    chars_distilled = len(provisional)
    ratio = (chars_distilled / total_orig) if total_orig > 0 else 0.0
    prompt = body + (
        f"{total_notes} notes, {total_orig} -> "
        f"{chars_distilled} chars ({ratio:.2f}x)\n"
    )
    return DistilledNotes(
        total_notes=total_notes,
        total_chars_original=total_orig,
        total_chars_distilled=len(prompt),
        compression_ratio=ratio,
        unique_capabilities=unique,
        prompt=prompt,
    )
