"""Tier a1 — pure .forge sidecar parser (Lane D W8).

Reads a YAML sidecar file and returns a structured ``SidecarFile``
dict. Validates required fields + effect-kind enum membership.
Pure: one bounded read; never raises on unknown fields (preserved
in ``extra``).

Lane D W11 will add the cross-validator (compares the sidecar's
declared effects against the source AST). Lane D W20 will dispatch
the ``proves:`` clauses through the Lean4 obligation discharger.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

import yaml

from ..a0_qk_constants.sidecar_schema import (
    REQUIRED_SIDECAR_FIELDS,
    REQUIRED_SYMBOL_FIELDS,
    SCHEMA_VERSION_SIDECAR_V1,
    VALID_EFFECTS,
    SidecarFile,
    SidecarSymbol,
)


class SidecarParseError(ValueError):
    """Raised when a sidecar file is malformed beyond soft recovery."""


class ParseResult(TypedDict, total=False):
    schema_version: str
    sidecar: SidecarFile | None
    errors: list[str]
    warnings: list[str]


def parse_sidecar_text(text: str, *, source: str = "<inline>") -> ParseResult:
    """Parse a YAML sidecar string and return a structured result.

    Returns a ParseResult with sidecar=None + populated errors when
    the document is unrecoverable; otherwise sidecar is the typed
    dict and warnings list any soft issues (unknown effect kinds
    are downgraded to warnings, not errors).
    """
    out: ParseResult = {
        "schema_version": SCHEMA_VERSION_SIDECAR_V1,
        "sidecar": None,
        "errors": [],
        "warnings": [],
    }
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        out["errors"].append(f"YAML parse error in {source}: {exc}")
        return out
    if not isinstance(data, dict):
        out["errors"].append(
            f"{source}: top-level must be a mapping, got "
            f"{type(data).__name__}"
        )
        return out
    for f in REQUIRED_SIDECAR_FIELDS:
        if f not in data:
            out["errors"].append(f"{source}: missing required field {f!r}")
    declared_schema = data.get("schema_version", "")
    if declared_schema and declared_schema != SCHEMA_VERSION_SIDECAR_V1:
        out["warnings"].append(
            f"{source}: declares schema_version={declared_schema!r}; "
            f"expected {SCHEMA_VERSION_SIDECAR_V1!r}"
        )
    if out["errors"]:
        return out

    raw_symbols = data.get("symbols") or []
    if not isinstance(raw_symbols, list):
        out["errors"].append(
            f"{source}: 'symbols' must be a list, got "
            f"{type(raw_symbols).__name__}"
        )
        return out
    parsed_symbols: list[SidecarSymbol] = []
    for i, raw in enumerate(raw_symbols):
        if not isinstance(raw, dict):
            out["errors"].append(
                f"{source}: symbols[{i}] must be a mapping"
            )
            continue
        for f in REQUIRED_SYMBOL_FIELDS:
            if f not in raw:
                out["errors"].append(
                    f"{source}: symbols[{i}] missing required {f!r}"
                )
        if not isinstance(raw.get("name", ""), str):
            out["errors"].append(
                f"{source}: symbols[{i}].name must be a string"
            )
            continue
        effect = str(raw.get("effect", ""))
        if effect and effect not in VALID_EFFECTS:
            out["warnings"].append(
                f"{source}: symbols[{i}] effect={effect!r} not in "
                f"VALID_EFFECTS — preserved as-is for forward-compat"
            )
        sym = SidecarSymbol(name=str(raw["name"]),
                              effect=effect)  # type: ignore[typeddict-item]
        if isinstance(raw.get("compose_with"), list):
            sym["compose_with"] = [str(s) for s in raw["compose_with"]]
        if isinstance(raw.get("proves"), list):
            sym["proves"] = [str(s) for s in raw["proves"]]
        if isinstance(raw.get("tier"), str):
            sym["tier"] = raw["tier"]
        if isinstance(raw.get("notes"), list):
            sym["notes"] = [str(s) for s in raw["notes"]]
        parsed_symbols.append(sym)

    if out["errors"]:
        return out

    sidecar: SidecarFile = SidecarFile(
        schema_version=SCHEMA_VERSION_SIDECAR_V1,
        target=str(data["target"]),
        symbols=parsed_symbols,
    )
    # Forward-compat: stash any unrecognised top-level keys.
    known = set(REQUIRED_SIDECAR_FIELDS)
    extra = {k: v for k, v in data.items() if k not in known}
    if extra:
        sidecar["extra"] = extra
    out["sidecar"] = sidecar
    return out


def parse_sidecar_file(path: Path) -> ParseResult:
    """Read a sidecar file from disk and parse it."""
    path = Path(path)
    if not path.exists():
        return {
            "schema_version": SCHEMA_VERSION_SIDECAR_V1,
            "sidecar": None,
            "errors": [f"sidecar file not found: {path}"],
            "warnings": [],
        }
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {
            "schema_version": SCHEMA_VERSION_SIDECAR_V1,
            "sidecar": None,
            "errors": [f"could not read {path}: {exc}"],
            "warnings": [],
        }
    return parse_sidecar_text(text, source=str(path))


def find_sidecar_for(source_file: Path) -> Path:
    """Convention: ``users/auth.py`` → ``users/auth.py.forge``."""
    p = Path(source_file)
    return p.with_suffix(p.suffix + ".forge")
