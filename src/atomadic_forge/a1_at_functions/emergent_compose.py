"""Tier a1 — pure composition discovery.

Given a list of :class:`SymbolSignatureCard`, find chains where the output of
one symbol is type-compatible with an input of another.

Type compatibility is intentionally loose — we work on annotation text:

* exact identical text                  → match
* ``T`` ↔ ``Optional[T]`` / ``T | None`` → match
* ``Iterable[T]`` ↔ ``list[T]`` / ``Sequence[T]`` / ``Collection[T]`` → match (T equal)
* ``Any`` ↔ anything                    → match
* generic vs concrete (``list`` ↔ ``list[str]``) → match (looser side wins)

Chain enumeration is bounded to depth ``max_depth`` (default 3) so the search
space stays tractable even on a 600-symbol catalog.
"""

from __future__ import annotations

import re
from typing import Iterable

from ..a0_qk_constants.emergent_types import (
    CompositionChain,
    SymbolSignatureCard,
)


_OPTIONAL_RE = re.compile(r"^Optional\[(.+)\]$|^(.+)\s*\|\s*None$|^None\s*\|\s*(.+)$")
_GENERIC_RE = re.compile(r"^(\w+)\[(.+)\]$")
_COLLECTION_FAMILY = {"list", "List", "Sequence", "Iterable", "Collection",
                      "tuple", "Tuple", "set", "Set", "frozenset"}


def _strip_optional(t: str) -> str:
    t = t.strip()
    m = _OPTIONAL_RE.match(t)
    if m:
        return next(g for g in m.groups() if g is not None).strip()
    return t


def _outer(t: str) -> tuple[str, str | None]:
    """Return (outer name, inner) for ``Outer[Inner]``, else (t, None)."""
    m = _GENERIC_RE.match(t.strip())
    if not m:
        return t.strip(), None
    return m.group(1), m.group(2).strip()


def _normalize(t: str) -> str:
    return _strip_optional(t).replace(" ", "")


def types_compatible(produced: str, consumed: str,
                     *, strict: bool = False) -> bool:
    """Return True if the producer's output text can flow into the consumer.

    ``strict`` (default False keeps behaviour permissive for backwards-compat):
    when True, treat ``Any`` as a non-match unless the partner is also ``Any``,
    and refuse generic-collection variance unless inner types align.  Strict
    mode is what :func:`find_chains` uses to filter out the noisy ``dict[str,
    Any] → dict[str, Any]`` chains that dominate the catalog.
    """
    p = _normalize(produced)
    c = _normalize(consumed)
    if not p or not c:
        return False
    if p == c:
        return True
    if "Any" in (p, c):
        if strict:
            return False
        return True
    p_outer, p_inner = _outer(p)
    c_outer, c_inner = _outer(c)
    if p_outer in _COLLECTION_FAMILY and c_outer in _COLLECTION_FAMILY:
        if p_inner is None and c_inner is None:
            return True
        if p_inner is None or c_inner is None:
            return not strict
        return types_compatible(p_inner, c_inner, strict=strict)
    if p_outer == c_outer and (p_inner is None or c_inner is None):
        return not strict
    return False


def is_anyish(t: str) -> bool:
    """Is this type spec a noisy 'Any-shaped' carrier?"""
    n = _normalize(t)
    if n == "Any":
        return True
    outer, inner = _outer(n)
    if inner and "Any" in inner:
        return True
    if outer in {"dict", "Dict", "Mapping"} and (inner is None or "Any" in (inner or "")):
        return True
    return False


def _consumer_inputs(card: SymbolSignatureCard) -> list[str]:
    return [t for _, t in card["inputs"]]


def find_chains(
    cards: Iterable[SymbolSignatureCard],
    *,
    max_depth: int = 3,
    max_chains: int = 5_000,
    require_pure: bool = False,
    domain_jump_required: bool = False,
    strict_types: bool = True,
    drop_anyish_seeds: bool = True,
) -> list[CompositionChain]:
    """Enumerate type-compatible chains across the catalog.

    A chain is a sequence ``[c1, c2, …]`` where ``c_{i+1}`` has at least one
    input compatible with ``c_i``'s output, and no card appears twice.

    Parameters bound the search:

    * ``max_depth`` — chain length cap.
    * ``max_chains`` — early-stop hard cap on returned chains.
    * ``require_pure`` — only purely-inferred symbols can participate.
    * ``domain_jump_required`` — at least two distinct domains in the chain.
    * ``strict_types`` — refuse ``Any``-as-bridge matches.  Cuts the noise
      from ``dict[str, Any] → dict[str, Any]`` chains that dominate the
      catalog when most signatures are loosely typed.
    * ``drop_anyish_seeds`` — skip seeding chains from symbols whose output
      is a generic ``dict``/``Mapping``/``Any`` carrier.  Such symbols are
      bottlenecks (they connect to half the catalog) and produce many
      look-alike candidates.
    """
    catalog = [c for c in cards if not (require_pure and not c["is_pure"])]
    by_qual = {c["qualname"]: c for c in catalog}
    out: list[CompositionChain] = []

    def consumers_of(produced: str) -> list[SymbolSignatureCard]:
        return [
            c for c in catalog
            if any(types_compatible(produced, ti, strict=strict_types)
                   for ti in _consumer_inputs(c))
        ]

    def extend(prefix: list[SymbolSignatureCard]) -> None:
        if len(out) >= max_chains:
            return
        if len(prefix) >= max_depth:
            _record(prefix)
            return
        last = prefix[-1]
        nexts = consumers_of(last["output"])
        used = {c["qualname"] for c in prefix}
        progressed = False
        for nxt in nexts:
            if nxt["qualname"] in used:
                continue
            progressed = True
            extend(prefix + [nxt])
            if len(out) >= max_chains:
                return
        if not progressed:
            _record(prefix)

    def _record(prefix: list[SymbolSignatureCard]) -> None:
        if len(prefix) < 2:
            return
        domains = [p["domain"] for p in prefix]
        tiers = [p["tier"] for p in prefix]
        if domain_jump_required and len(set(domains)) < 2:
            return
        bridges: list[str] = []
        for i in range(len(prefix) - 1):
            bridges.append(prefix[i]["output"])
        chain = CompositionChain(
            chain=[p["qualname"] for p in prefix],
            bridges=bridges,
            tiers=tiers,
            domains=domains,
            crosses_domains=len(set(domains)),
            crosses_tiers=len(set(tiers)),
            final_output_type=prefix[-1]["output"],
            pure=all(by_qual[q]["is_pure"] for q in (p["qualname"] for p in prefix)),
        )
        out.append(chain)

    seeds = [c for c in catalog
             if not (drop_anyish_seeds and is_anyish(c["output"]))]
    for seed in seeds:
        extend([seed])
        if len(out) >= max_chains:
            break
    return out
