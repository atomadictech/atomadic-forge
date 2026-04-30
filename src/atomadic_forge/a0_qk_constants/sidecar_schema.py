"""Tier a0 — .forge sidecar v1.0 wire-format schema.

Golden Path Lane D W8 deliverable. The sidecar is a YAML file that
sits beside any source file (e.g. ``src/pkg/auth.py.forge``) and
declares the per-symbol contract:

  effect:        what side effects each function performs
                  (NetIO | KeyedCache | Logging | Pure | IO)
  compose_with:  named symbols this one lawfully composes with
                  (Bao-Rompf categorical effect functor — Lane D W20)
  proves:        Lean4 proof obligation labels this symbol satisfies
                  (Lane D W20 dispatches against aethel-nexus-proofs)

a0 invariant: pure data shape, imports limited to __future__ + typing.
The reader (a1.sidecar_parser) parses YAML into these dicts; the
validator (Lane D W11) cross-checks against the source file's AST.
"""
from __future__ import annotations

from typing import Literal, TypedDict

SCHEMA_VERSION_SIDECAR_V1 = "atomadic-forge.sidecar/v1"


# v1 effect taxonomy — Bao-Rompf 2025 categorical effect lattice.
EffectKind = Literal[
    "Pure",         # no side effects
    "IO",           # arbitrary I/O (filesystem, stdin/stdout)
    "NetIO",        # network calls
    "KeyedCache",   # writes to a content-addressed cache
    "Logging",      # observability emission only
    "Random",       # non-deterministic input (rng / time / uuid)
    "Mutation",     # mutates passed-in arguments
]

VALID_EFFECTS: tuple[str, ...] = (
    "Pure", "IO", "NetIO", "KeyedCache", "Logging", "Random", "Mutation",
)


class SidecarSymbol(TypedDict, total=False):
    """One symbol's contract within a sidecar file.

    Required:
      name              — must match a top-level symbol in the source
      effect            — one of VALID_EFFECTS

    Optional:
      compose_with      — ['module.symbol', ...] this symbol composes with
      proves            — ['lemma_name', ...] obligations this discharges
      tier              — caller may pin the tier (otherwise inferred)
      notes             — free-form
    """
    name: str
    effect: EffectKind
    compose_with: list[str]
    proves: list[str]
    tier: str
    notes: list[str]


class SidecarFile(TypedDict, total=False):
    """The full sidecar document.

    Required:
      schema_version    — atomadic-forge.sidecar/v1
      target            — path of the source file this sidecar covers
      symbols           — list of SidecarSymbol; one per public symbol
    """
    schema_version: str
    target: str
    symbols: list[SidecarSymbol]
    # Forward-compat: future minors may add fields. Consumers MUST
    # tolerate unknown keys.
    extra: dict[str, object]


REQUIRED_SIDECAR_FIELDS: tuple[str, ...] = (
    "schema_version", "target", "symbols",
)
REQUIRED_SYMBOL_FIELDS: tuple[str, ...] = ("name", "effect")
