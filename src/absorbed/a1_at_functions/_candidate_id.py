"""Tier a1 — pure ranker for the Emergent Scan.

Score each :class:`CompositionChain` on how 'emergent' it is, then return
the top-N as :class:`EmergentCandidateCard`.

Score components (max 100):

* cross-domain bonus      ``+ 10 * (crosses_domains - 1)``     (0..30)
* cross-tier bonus        ``+ 8  * (crosses_tiers   - 1)``     (0..32)
* purity bonus            ``+ 10`` if all steps pure
* depth bonus             ``+ 6  * (len(chain) - 1)``           (0..18)
* novelty bonus           ``+ 10`` if final output type isn't already
                          the output of any single existing symbol

Output names are heuristic kebab-case combinations of distinct domains.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from ..a0_qk_constants.emergent_types import (
    CompositionChain,
    EmergentCandidateCard,
    SymbolSignatureCard,
)


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


def rank_chains(
    chains: Iterable[CompositionChain],
    *,
    catalog: list[SymbolSignatureCard],
    top_n: int = 25,
    novelty_unknown_outputs: bool = True,
) -> list[EmergentCandidateCard]:
    from .emergent_compose import is_anyish

    chains = list(chains)
    existing_outputs = {c["output"] for c in catalog}

    out: list[EmergentCandidateCard] = []
    for chain in chains:
        breakdown: dict[str, float] = {}
        breakdown["cross_domain"] = min(30, 10 * max(0, chain["crosses_domains"] - 1))
        breakdown["cross_tier"] = min(32, 8 * max(0, chain["crosses_tiers"] - 1))
        breakdown["pure"] = 10 if chain["pure"] else 0
        breakdown["depth"] = min(18, 6 * max(0, len(chain["chain"]) - 1))
        novelty_signals: list[str] = []
        novel = (chain["final_output_type"] not in existing_outputs)
        breakdown["novelty"] = 10 if (novelty_unknown_outputs and novel) else 0
        # Penalty for chains whose every bridge is Any-shaped — they're real
        # but uninformative.
        anyish_bridges = sum(1 for b in chain["bridges"] if is_anyish(b))
        if anyish_bridges:
            breakdown["any_penalty"] = -min(20, 6 * anyish_bridges)
        if novel:
            novelty_signals.append("final output type not produced by any single existing symbol")
        if chain["crosses_domains"] >= 3:
            novelty_signals.append("touches three or more domains")
        if chain["crosses_tiers"] >= 3:
            novelty_signals.append("spans three or more tiers")
        if chain["pure"]:
            novelty_signals.append("entirely pure — safe to materialise as a1/a3 with no I/O risk")
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
    # Dedupe candidate names, keep top by score per name
    seen: dict[str, EmergentCandidateCard] = {}
    for c in out:
        if c["name"] not in seen or seen[c["name"]]["score"] < c["score"]:
            seen[c["name"]] = c
    deduped = sorted(seen.values(), key=lambda c: c["score"], reverse=True)
    return deduped[:top_n]
