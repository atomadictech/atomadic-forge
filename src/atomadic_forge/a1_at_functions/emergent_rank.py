"""Tier a1 — pure ranker for the Emergent Scan.

Score each :class:`CompositionChain` on how genuinely 'emergent' it is, then
return the top-N as :class:`EmergentCandidateCard`.

Score components (max ~130):

* cross-domain bonus       ``+ 12 * (crosses_domains - 1)``   (0 .. 36)
* cross-tier bonus         ``+ 8  * (crosses_tiers   - 1)``   (0 .. 32)
* purity bonus             ``+ 10`` if all steps pure
* depth bonus              ``+ 6  * (len(chain) - 1)``        (0 .. 18)
* gap bonus                ``+ 20`` if these domain(s) have no existing a3 feature
* specificity bonus        ``+ 15`` if every bridge carries a named type (no str/Any)
* novel composition        ``+ 10`` if all symbols come from distinct modules

Penalties:
* anyish bridge penalty    ``- 6  * anyish_bridge_count``
* primitive bridge penalty ``- 5  * primitive_bridge_count``

The ``gap_bonus`` and ``specificity`` signals are the main discriminators that
replace the broken v1 ``novelty`` check (which compared output types against the
catalog — always 0 because basic types always exist).
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from itertools import combinations

from ..a0_qk_constants.emergent_types import (
    CompositionChain,
    EmergentCandidateCard,
    SymbolSignatureCard,
)

_STOP_WORDS = frozenset({
    "feature", "pipeline", "engine", "runner", "service",
    "integration", "cmd", "tool", "gate",
})


def _candidate_id(chain: CompositionChain) -> str:
    h = hashlib.sha256("→".join(chain["chain"]).encode("utf-8")).hexdigest()
    return f"emrg-{h[:8]}"


def _suggest_name(chain: CompositionChain) -> str:
    seen: list[str] = []
    for d in chain["domains"]:
        if d not in seen:
            seen.append(d)
    return "-".join(seen[:4]) + "-pipeline"


def _suggested_tier(chain: CompositionChain) -> str:
    """A composition that touches multiple a2 composites is itself a3."""
    tiers = set(chain["tiers"])
    if "a4_sy_orchestration" in tiers:
        return "a4_sy_orchestration"
    if "a3_og_features" in tiers or len(tiers) >= 3:
        return "a3_og_features"
    if "a2_mo_composites" in tiers:
        return "a2_mo_composites"
    return "a1_at_functions"


def _summary(chain: CompositionChain) -> str:
    domains = " → ".join(chain["domains"])
    return (f"Compose {len(chain['chain'])} steps across {chain['crosses_domains']} "
            f"domain(s): {domains}; final output {chain['final_output_type']}")


def _build_covered_pairs(a3_feature_stems: list[str]) -> set[frozenset[str]]:
    """Build domain-pair coverage from existing a3 feature file stems.

    An a3 stem like ``emergent_feature`` covers the pair {emergent, feature};
    ``forge_evolve`` covers {forge, evolve}; etc.  Pairs present in this set
    are *already bridged* by an existing feature — domain pairs absent from the
    set are genuine gaps worth a gap_bonus.
    """
    covered: set[frozenset[str]] = set()
    for stem in a3_feature_stems:
        words = [
            w for w in re.split(r"[_\-]", stem.lower())
            if w and w not in _STOP_WORDS
        ]
        if len(words) >= 2:
            for pair in combinations(words, 2):
                covered.add(frozenset(pair))
    return covered


def rank_chains(
    chains: Iterable[CompositionChain],
    *,
    catalog: list[SymbolSignatureCard],
    top_n: int = 25,
    novelty_unknown_outputs: bool = True,  # kept for backwards-compat; no longer primary
    a3_feature_stems: list[str] | None = None,
) -> list[EmergentCandidateCard]:
    """Score chains and return the top-N emergent candidates.

    Parameters
    ----------
    chains:
        Output of :func:`find_chains`.
    catalog:
        Full symbol catalog (used for module-cooccurrence checks).
    top_n:
        Maximum candidates to return.
    a3_feature_stems:
        Stems of existing ``a3_og_features/`` files (e.g. ``["emergent_feature",
        "forge_evolve"]``).  Used to compute gap_bonus — chains that bridge domain
        pairs absent from this list get +20.  Pass ``None`` or ``[]`` to skip.
    """
    from .emergent_compose import is_anyish, is_primitive

    chains = list(chains)
    covered_pairs = _build_covered_pairs(a3_feature_stems or [])
    qual_to_module = {c["qualname"]: c["module"] for c in catalog}

    out: list[EmergentCandidateCard] = []
    for chain in chains:
        breakdown: dict[str, float] = {}
        novelty_signals: list[str] = []

        # ── Core structural signals ──────────────────────────────────────────
        breakdown["cross_domain"] = min(36, 12 * max(0, chain["crosses_domains"] - 1))
        breakdown["cross_tier"]   = min(32, 8  * max(0, chain["crosses_tiers"]   - 1))
        breakdown["pure"]         = 10 if chain["pure"] else 0
        breakdown["depth"]        = min(18, 6  * max(0, len(chain["chain"])       - 1))

        # ── Gap bonus: domain pair absent from all existing a3 features ──────
        chain_domains = list(dict.fromkeys(chain["domains"]))  # deduped, ordered
        gap = False
        if covered_pairs:
            for pair in combinations(chain_domains[:3], 2):
                if frozenset(pair) not in covered_pairs:
                    gap = True
                    novelty_signals.append(
                        f"domain pair [{' × '.join(sorted(pair))}] has no existing a3 feature"
                    )
                    break
        breakdown["gap_bonus"] = 20 if gap else 0

        # ── Specificity: all bridges carry named types (no str/Any) ──────────
        bridges = chain["bridges"]
        specific_count = sum(
            1 for b in bridges if not is_anyish(b) and not is_primitive(b)
        )
        breakdown["specificity"] = min(15, 5 * specific_count)
        if bridges and specific_count == len(bridges):
            novelty_signals.append(
                "all bridges carry specific named types — no str/Any intermediary"
            )

        # ── Novel composition: symbols from all-distinct modules ──────────────
        modules = [qual_to_module.get(q, q) for q in chain["chain"]]
        novel_comp = len(set(modules)) == len(chain["chain"])
        breakdown["novel_composition"] = 10 if novel_comp else 0
        if novel_comp:
            novelty_signals.append(
                "symbols drawn from distinct modules — first time composed together"
            )

        # ── Penalties ────────────────────────────────────────────────────────
        anyish_count = sum(1 for b in bridges if is_anyish(b))
        if anyish_count:
            breakdown["any_penalty"] = -min(20, 6 * anyish_count)

        primitive_count = sum(1 for b in bridges if is_primitive(b))
        if primitive_count:
            breakdown["primitive_penalty"] = -min(15, 5 * primitive_count)

        # ── Cosmetic signals (always emit for readability) ───────────────────
        if chain["crosses_domains"] >= 3:
            novelty_signals.append("touches three or more domains")
        if chain["crosses_tiers"] >= 3:
            novelty_signals.append("spans three or more tiers")
        if chain["pure"]:
            novelty_signals.append(
                "entirely pure — safe to materialise as a1/a3 with no I/O risk"
            )

        score = sum(breakdown.values())
        if score <= 0:
            continue

        out.append(EmergentCandidateCard(
            candidate_id=_candidate_id(chain),
            name=_suggest_name(chain),
            summary=_summary(chain),
            chain=chain,
            score=float(score),
            score_breakdown=breakdown,
            suggested_tier=_suggested_tier(chain),
            novelty_signals=novelty_signals,
        ))

    out.sort(key=lambda c: c["score"], reverse=True)
    # Deduplicate by suggested name, keep highest-scoring representative.
    seen: dict[str, EmergentCandidateCard] = {}
    for c in out:
        if c["name"] not in seen or seen[c["name"]]["score"] < c["score"]:
            seen[c["name"]] = c
    deduped = sorted(seen.values(), key=lambda c: c["score"], reverse=True)
    return deduped[:top_n]
