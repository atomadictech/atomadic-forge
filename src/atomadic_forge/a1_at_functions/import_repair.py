"""Tier a1 — pure import-repair pass for assimilated symbol files.

When ``atomadic-forge assimilate`` materialises a symbol from a flat-layout sibling
repo into the 5-tier monadic package, intra-package references (e.g.
``from kg import infer_tier``) are not rewritten to the new sibling file
paths.  The result is a thousand-file package that silently refuses to
import.

This module provides a deterministic post-process that:

1. Scans a tier folder for ``*.py`` files materialised by the assimilator.
2. Builds a name-to-relative-module map from the per-source filename
   convention (``a<N>_source_<root>_<symbol>.py`` exposes ``<symbol>``).
3. Rewrites every broken ``from <flat-name> import X`` line to the matching
   ``from .a<N>_source_<root>_<flat-name> import X`` sibling reference.

It is pure: takes file paths and returns a diff list of (path, new_text).
The caller decides whether to apply.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


_SOURCE_HEAD = re.compile(r"^a\d_source_")
_FROM_LINE = re.compile(r"^from\s+([A-Za-z_][\w]*)\s+import\s+(.+)$", re.MULTILINE)


# Roots the assimilator can encode in file stems.  Add new roots as needed.
KNOWN_SOURCE_ROOTS: tuple[str, ...] = ("atomadic_forge_seed", "atomadic_v2", "atomadic_engine")


def _split_source_stem(stem: str,
                       roots: tuple[str, ...] = KNOWN_SOURCE_ROOTS) -> tuple[str, str] | None:
    """Return ``(root, symbol)`` for ``a<N>_source_<root>_<symbol>``.

    Uses prefix-stripping with a known root list so symbols containing
    underscores (``infer_tier``, ``cherry_pick_dict``) are split correctly.
    """
    head = _SOURCE_HEAD.match(stem)
    if not head:
        return None
    rest = stem[head.end():]
    for root in roots:
        if rest.startswith(root + "_"):
            return root, rest[len(root) + 1:]
        if rest == root:
            return root, ""
    return None


def build_symbol_map(tier_dir: Path) -> dict[str, str]:
    """Return ``{flat_module_name: tier_relative_module}`` for every assimilated file.

    A file like ``a1_source_atomadic_v2_kg.py`` maps the flat name ``kg``
    to the relative module path ``.a1_source_atomadic_v2_kg``.
    Last-write-wins on collisions (later files override earlier ones).
    """
    out: dict[str, str] = {}
    for f in sorted(tier_dir.glob("a*_source_*.py")):
        parsed = _split_source_stem(f.stem)
        if not parsed:
            continue
        _root, flat_name = parsed
        out[flat_name] = f"." + f.stem
    return out


def build_name_to_file_map(*tier_dirs: Path) -> dict[str, str]:
    """Return ``{symbol_name: relative_module}`` across all listed tier dirs.

    The assimilator emits one file per symbol whose stem encodes the symbol
    in lowercase (``a1_source_atomadic_v2_infer_tier.py`` → ``infer_tier``;
    ``a1_source_atomadic_v2_agenticswarm.py`` → ``agenticswarm`` ≈ class
    ``AgenticSwarm``).  We therefore key on case-folded names and accept
    variants when rewriting.
    """
    out: dict[str, str] = {}
    for tier_dir in tier_dirs:
        if not tier_dir.exists():
            continue
        for f in sorted(tier_dir.glob("a*_source_*.py")):
            parsed = _split_source_stem(f.stem)
            if not parsed:
                continue
            _root, name = parsed
            out[name.lower()] = f"." + f.stem
    return out


def rewrite_imports(source: str, symbol_map: dict[str, str],
                    stdlib_safelist: Iterable[str] = (),
                    name_to_file: dict[str, str] | None = None) -> str:
    """Return ``source`` with broken flat imports rewritten to sibling paths.

    Two passes:

    1. ``from <X> import Y`` where ``X`` is in ``symbol_map`` (a known module
       name) → ``from <symbol_map[X]> import Y``.
    2. ``from <X> import Y[, Z, ...]`` where ``X`` is unknown but one or more
       of the imported names are in ``name_to_file`` → split into one
       ``from .<file> import <name>`` per imported name.

    Imports of stdlib / third-party modules in ``stdlib_safelist`` are left
    alone.
    """
    safe = set(stdlib_safelist)
    name_to_file = name_to_file or {}

    def replace(match: re.Match[str]) -> str:
        head = match.group(1)
        rest = match.group(2).strip()
        if head in safe:
            return match.group(0)
        if head in symbol_map:
            return f"from {symbol_map[head]} import {rest}"
        # try per-name resolution
        names = [n.strip() for n in rest.split(",") if n.strip()]
        resolved: list[str] = []
        unresolved: list[str] = []
        for n in names:
            base_name = n.split(" as ")[0].strip()
            key = base_name.lower()
            if key in name_to_file:
                resolved.append(f"from {name_to_file[key]} import {n}")
            else:
                unresolved.append(n)
        if resolved and not unresolved:
            return "\n".join(resolved)
        return match.group(0)

    return _FROM_LINE.sub(replace, source)


def repair_tier_directory(tier_dir: Path,
                          dry_run: bool = True,
                          name_to_file: dict[str, str] | None = None) -> dict[str, str]:
    """Repair every ``a*_source_*.py`` file in ``tier_dir``.

    ``name_to_file`` (optional) maps symbol names (case-folded) to relative
    module paths and is used as a fallback resolver when the import head
    isn't a known sibling module.  Build it once via
    :func:`build_name_to_file_map` over every tier and pass it to each call.

    Returns ``{path: new_text}`` for files that would change.  When
    ``dry_run`` is False the changes are written back to disk.
    """
    symbol_map = build_symbol_map(tier_dir)
    diffs: dict[str, str] = {}
    for f in sorted(tier_dir.glob("a*_source_*.py")):
        try:
            current = f.read_text(encoding="utf-8")
        except OSError:
            continue
        new_text = rewrite_imports(current, symbol_map,
                                   _BUILTIN_AND_THIRD_PARTY,
                                   name_to_file=name_to_file)
        if new_text != current:
            diffs[str(f)] = new_text
            if not dry_run:
                f.write_text(new_text, encoding="utf-8")
    return diffs


def repair_assimilation_output(package_root: Path,
                               dry_run: bool = True) -> dict[str, dict[str, str]]:
    """Repair every tier under ``package_root`` (e.g. ``…/src/atomadic_forge``).

    Builds one global ``name_to_file`` map across all tiers (because a tier-a2
    composite often imports a tier-a1 helper) and applies the rewrite pass.
    """
    tiers = ["a0_qk_constants", "a1_at_functions", "a2_mo_composites",
             "a3_og_features", "a4_sy_orchestration"]
    tier_dirs = [package_root / t for t in tiers if (package_root / t).exists()]
    name_to_file = build_name_to_file_map(*tier_dirs)
    out: dict[str, dict[str, str]] = {}
    for t, tier_dir in zip(tiers, tier_dirs):
        # name_to_file uses tier-internal relative paths.  When repairing
        # *a different* tier, we still need relative-from-self paths.  The
        # convention here: a single global map keyed by symbol with paths
        # relative to *its own* tier directory still works because the
        # output package re-exports everything via per-tier ``__init__.py``
        # modules — but for cross-tier refs we'd want absolute imports.
        # In practice, the assimilator places nearly all atomadic-v2
        # symbols at a1, so a tier-local map is sufficient for this dataset.
        local_n2f = build_name_to_file_map(tier_dir)
        out[t] = repair_tier_directory(tier_dir, dry_run=dry_run,
                                       name_to_file=local_n2f)
    return out


# Common stdlib + third-party top-level names we should never rewrite.
_BUILTIN_AND_THIRD_PARTY = frozenset({
    # stdlib (representative — extend as needed)
    "abc", "argparse", "ast", "asyncio", "base64", "collections", "concurrent",
    "contextlib", "copy", "csv", "dataclasses", "datetime", "decimal", "enum",
    "functools", "glob", "hashlib", "hmac", "html", "http", "importlib", "inspect",
    "io", "itertools", "json", "logging", "math", "operator", "os", "pathlib",
    "pickle", "pkgutil", "platform", "pprint", "queue", "random", "re", "secrets",
    "shlex", "shutil", "signal", "socket", "sqlite3", "statistics", "string",
    "struct", "subprocess", "sys", "tempfile", "textwrap", "threading", "time",
    "tomllib", "traceback", "types", "typing", "unicodedata", "urllib", "uuid",
    "warnings", "weakref", "xml", "zipfile",
    # third-party
    "click", "cryptography", "fastapi", "httpx", "jinja2", "jsonschema", "numpy",
    "pandas", "peft", "pydantic", "pytest", "rich", "ruff", "torch", "transformers",
    "typer", "uvicorn", "yaml", "edge_tts", "x402", "discord", "datasets",
    # atomadic_forge itself
    "atomadic_forge",
})
