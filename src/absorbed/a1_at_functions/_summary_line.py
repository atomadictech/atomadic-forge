"""Tier a3 — pipeline-agnostic Emergent Scan overlay.

Every ASS-ADE phase that walks a catalog (scout, cherry-pick, assimilate,
rebuild, enhance, evolve) can call :func:`emergent_overlay_for_path` to
surface composition candidates that single-symbol heuristics would miss.

The overlay is a thin adapter:

  path → harvest_signatures → find_chains → rank_chains → top-N
       → return as a list of EmergentCandidateCard plus a small summary

Output is shaped so it slots into existing report dicts under an
``"emergent"`` key without disturbing the schema.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from ..a0_qk_constants.emergent_types import (
    EmergentCandidateCard,
    SymbolSignatureCard,
)
from ..a1_at_functions.emergent_compose import find_chains
from ..a1_at_functions.emergent_rank import rank_chains
from ..a1_at_functions.emergent_signature_extract import harvest_signatures

_CONFIG_DEFAULTS: dict[str, dict[str, Any]] = {
    "scout":       {"max_depth": 3, "top_n": 10, "domain_jump_required": True,
                     "require_pure": False, "score_floor": 30},
    "cherry-pick": {"max_depth": 3, "top_n": 15, "domain_jump_required": True,
                     "require_pure": False, "score_floor": 0},
    "assimilate":  {"max_depth": 3, "top_n": 25, "domain_jump_required": True,
                     "require_pure": False, "score_floor": 30},
    "rebuild":     {"max_depth": 3, "top_n": 25, "domain_jump_required": True,
                     "require_pure": False, "score_floor": 30},
    "enhance":     {"max_depth": 4, "top_n": 20, "domain_jump_required": False,
                     "require_pure": False, "score_floor": 20},
    "evolve":      {"max_depth": 4, "top_n": 30, "domain_jump_required": True,
                     "require_pure": True,  "score_floor": 50},
}


def _detect_package(src_root: Path) -> str:
    """Find the package name under ``src_root/<package>/__init__.py``.

    Returns the first directory containing an ``__init__.py``.  Falls back
    to ``"atomadic_forge"`` if nothing is found.
    """
    for child in sorted(src_root.iterdir()) if src_root.exists() else []:
        if child.is_dir() and (child / "__init__.py").exists():
            return child.name
    return "atomadic_forge"


def _src_root_of(repo: Path) -> Path:
    """Return ``<repo>/src`` if it exists, else ``repo``."""
    src = repo / "src"
    return src if src.exists() else repo


def emergent_overlay_for_path(
    repo_root: str | Path,
    *,
    phase: str = "scout",
    catalog: Iterable[SymbolSignatureCard] | None = None,
    package: str | None = None,
) -> dict[str, Any]:
    """Run an emergent scan over a repo (or pre-harvested catalog) for a phase.

    ``catalog`` lets phases that already harvested signatures pass them in
    instead of re-walking the tree (assimilate / rebuild build the catalog
    naturally as part of their flow).
    """
    cfg = dict(_CONFIG_DEFAULTS.get(phase, _CONFIG_DEFAULTS["scout"]))
    repo = Path(repo_root).resolve()
    src_root = _src_root_of(repo)
    pkg = package or _detect_package(src_root)

    if catalog is None:
        catalog = harvest_signatures(src_root, pkg)
    catalog_list: list[SymbolSignatureCard] = list(catalog)

    chains = find_chains(
        catalog_list,
        max_depth=cfg["max_depth"],
        max_chains=2_000,
        require_pure=cfg["require_pure"],
        domain_jump_required=cfg["domain_jump_required"],
    )
    candidates = rank_chains(chains, catalog=catalog_list, top_n=cfg["top_n"])
    floor = cfg["score_floor"]
    candidates = [c for c in candidates if c["score"] >= floor]

    by_domain: dict[str, int] = {}
    for c in catalog_list:
        by_domain[c["domain"]] = by_domain.get(c["domain"], 0) + 1

    return {
        "schema_version": "atomadic-forge.emergent.overlay/v1",
        "phase": phase,
        "src_root": str(src_root),
        "package": pkg,
        "catalog_size": len(catalog_list),
        "chain_count_considered": len(chains),
        "candidates": candidates,
        "config": cfg,
        "domain_inventory": by_domain,
        "summary_line": _summary_line(candidates, len(catalog_list), pkg, phase),
    }


def _summary_line(candidates: list[EmergentCandidateCard],
                  catalog_size: int, package: str, phase: str) -> str:
    if not candidates:
        return (
            f"emergent[{phase}]: 0 candidates over {package} ({catalog_size} symbols) — "
            "no novel composition above score floor"
        )
    top = candidates[0]
    return (
        f"emergent[{phase}]: {len(candidates)} candidate(s) over {package} "
        f"({catalog_size} symbols); top={top['name']} score={top['score']:.0f}"
    )


def boost_cherry_pick_targets(
    cherry_targets: list[dict[str, Any]],
    *,
    overlay: dict[str, Any],
    boost: float = 0.1,
) -> list[dict[str, Any]]:
    """Re-score cherry-pick targets using emergent participation.

    Each target gains ``boost`` per emergent chain it participates in.
    The augmented list is returned; the input is not mutated.
    """
    chains = [c["chain"]["chain"] for c in overlay.get("candidates", [])]
    flat = {q for chain in chains for q in chain}
    out: list[dict[str, Any]] = []
    for t in cherry_targets:
        sym = t.get("symbol") or {}
        qname = f"{sym.get('module','')}.{sym.get('qualname','')}"
        bumped = dict(t)
        if qname in flat:
            current = float(bumped.get("confidence", 0.0))
            bumped["confidence"] = min(1.0, current + boost)
            bumped.setdefault("reasons", []).append(
                "participates in emergent composition chain"
            )
        out.append(bumped)
    return out
