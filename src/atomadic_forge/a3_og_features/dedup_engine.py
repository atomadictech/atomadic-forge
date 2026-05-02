"""Tier a3 - dedup engine. Walks research notes AND code modules,
groups duplicates, emits a ConsolidationReport that drives:

  * 'this research note restates known capability X' -> auto-archive
  * 'this code module is byte-stable equivalent of existing Y' -> reject
  * 'this proposal is novel' -> accept and route to synthesis

The "never reinvent the wheel" engine.  Composes existing primitives
exclusively:

  a1 intent_similarity         (token Jaccard + difflib ratio)
  a1 research_note_distiller   (extract title + thesis + identifiers)
  a1 code_signature            (AST semantic fingerprint)
  a2 cross_agent_intent_deduplicator  (sliding-window scorer)

Produces no new primitives; orchestrates the four above to cover
both research-note dedup and code-logic dedup with a single entry
point.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from ..a1_at_functions import intent_similarity
from ..a1_at_functions.code_signature import signature_of, ModuleSignature
from ..a1_at_functions.research_note_distiller import (
    DistilledNotes, distill_notes,
)
from ..a2_mo_composites.cross_agent_intent_deduplicator import (
    CrossAgentIntentDeduplicator,
)

SCHEMA: str = "atomadic-forge.dedup-engine/v1"


@dataclass(frozen=True)
class ResearchDupGroup:
    canonical: str        # path of the note kept as canonical
    duplicates: tuple[str, ...]
    reason: str           # similarity score + matched tokens


@dataclass(frozen=True)
class CodeDupGroup:
    module_hash: str
    canonical: str        # path of the module kept as canonical
    duplicates: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class NovelCandidate:
    path: str             # research note or code file
    kind: str             # "research" | "code"
    identifiers: tuple[str, ...]


@dataclass(frozen=True)
class ConsolidationReport:
    schema: str = SCHEMA
    research_groups: tuple[ResearchDupGroup, ...] = field(default_factory=tuple)
    code_groups: tuple[CodeDupGroup, ...] = field(default_factory=tuple)
    novel: tuple[NovelCandidate, ...] = field(default_factory=tuple)
    files_scanned: int = 0


# ────────────────────────── research dedup ─────────────────────────

def _read_md_dir(d: Path) -> list[tuple[Path, str]]:
    out: list[tuple[Path, str]] = []
    if not d.exists():
        return out
    for p in sorted(d.glob("*.md")):
        try:
            out.append((p, p.read_text(encoding="utf-8",
                                          errors="replace")))
        except OSError:
            continue
    return out


def dedup_research_notes(inbox: Path,
                           *, threshold: float = 0.72,
                           ) -> tuple[list[ResearchDupGroup], list[Path]]:
    """Compose research_note_distiller + intent_similarity to group
    near-duplicate notes by (title + thesis) similarity. Returns
    (duplicate_groups, novel_paths)."""
    notes = _read_md_dir(inbox)
    distilled = distill_notes([content for _, content in notes])
    # Build per-note canonical text using title + thesis if present.
    canonical_texts: list[str] = []
    for _, content in notes:
        # Use first H1 + first **Thesis:** line as the dedup key.
        title = ""
        thesis = ""
        for line in content.splitlines():
            line = line.strip()
            if not title and line.startswith("# "):
                title = line[2:].strip()
            if not thesis and line.lower().startswith("**thesis:**"):
                thesis = line.split(":", 1)[1].strip(" *")
            if title and thesis:
                break
        canonical_texts.append((title + " " + thesis).strip()
                                or content[:200])

    # Group: index i is a dup of j if similarity(canonical[i], canonical[j])
    # >= threshold and j < i. The first-seen wins canonical status.
    groups: dict[int, list[int]] = defaultdict(list)
    canonical_of: dict[int, int] = {}
    for i, text_i in enumerate(canonical_texts):
        merged = False
        for canon_i, members in groups.items():
            r = intent_similarity.similarity(text_i,
                                              canonical_texts[canon_i])
            if r.score >= threshold:
                members.append(i)
                canonical_of[i] = canon_i
                merged = True
                break
        if not merged:
            groups[i] = [i]
            canonical_of[i] = i

    dup_groups: list[ResearchDupGroup] = []
    novel_paths: list[Path] = []
    for canon_i, members in groups.items():
        canon_path, _ = notes[canon_i]
        if len(members) == 1:
            novel_paths.append(canon_path)
        else:
            dup_paths = [str(notes[m][0]) for m in members if m != canon_i]
            dup_groups.append(ResearchDupGroup(
                canonical=str(canon_path),
                duplicates=tuple(dup_paths),
                reason=f"sim>={threshold} on title+thesis",
            ))
    return dup_groups, novel_paths


# ────────────────────────── code dedup ─────────────────────────────

def dedup_code_tree(root: Path,
                      *, skip_parts: tuple[str, ...] = ("foreign",
                                                          "__pycache__",
                                                          ".pytest_cache"),
                      ) -> tuple[list[CodeDupGroup], list[Path]]:
    """Compose code_signature over a Python source tree. Groups
    modules by module_hash; reports any group of size > 1 as a
    duplicate. Returns (duplicate_groups, novel_paths)."""
    by_hash: dict[str, list[Path]] = defaultdict(list)
    for p in sorted(root.rglob("*.py")):
        if any(part in skip_parts for part in p.parts):
            continue
        if p.name.startswith("__"):
            continue
        try:
            sig = signature_of(p.read_text(encoding="utf-8",
                                             errors="replace"))
        except OSError:
            continue
        if sig.parse_ok and (sig.functions or sig.classes):
            by_hash[sig.module_hash].append(p)

    dup_groups: list[CodeDupGroup] = []
    novel_paths: list[Path] = []
    for h, paths in by_hash.items():
        if len(paths) == 1:
            novel_paths.append(paths[0])
        else:
            canon = paths[0]
            dups = [str(p) for p in paths[1:]]
            dup_groups.append(CodeDupGroup(
                module_hash=h,
                canonical=str(canon),
                duplicates=tuple(dups),
                reason=f"identical AST shape hash ({len(paths)} modules)",
            ))
    return dup_groups, novel_paths


# ────────────────────────── orchestrator ───────────────────────────

def run_dedup(*,
                research_inboxes: tuple[Path, ...] = (),
                code_roots: tuple[Path, ...] = (),
                research_threshold: float = 0.72,
                ) -> ConsolidationReport:
    """Top-level entry. Walks each research-inbox dir and code-tree
    root, returns one consolidated report."""
    all_research_groups: list[ResearchDupGroup] = []
    all_code_groups: list[CodeDupGroup] = []
    novel: list[NovelCandidate] = []
    files_scanned = 0

    for inbox in research_inboxes:
        groups, novels = dedup_research_notes(
            inbox, threshold=research_threshold)
        all_research_groups.extend(groups)
        files_scanned += sum(1 for _ in inbox.glob("*.md")) if inbox.exists() else 0
        for p in novels:
            novel.append(NovelCandidate(
                path=str(p), kind="research", identifiers=()))

    for root in code_roots:
        groups, novels = dedup_code_tree(root)
        all_code_groups.extend(groups)
        files_scanned += sum(1 for _ in root.rglob("*.py")) if root.exists() else 0
        for p in novels:
            try:
                sig = signature_of(p.read_text(encoding="utf-8",
                                                 errors="replace"))
                idents = tuple(f.name for f in sig.functions[:8])
            except OSError:
                idents = ()
            novel.append(NovelCandidate(
                path=str(p), kind="code", identifiers=idents))

    return ConsolidationReport(
        research_groups=tuple(all_research_groups),
        code_groups=tuple(all_code_groups),
        novel=tuple(novel),
        files_scanned=files_scanned,
    )
