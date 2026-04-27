"""Tier a1 — pure rebuilder for each tier's ``__init__.py`` re-exports.

After every iterate turn, Forge regenerates each ``aN_*/__init__.py`` so
every public name in the tier becomes importable via the tier path:

    from pkg.a1_at_functions import generate_slug, normalize_url

That style is what most LLMs (and humans) reach for, but it doesn't work
unless the tier's ``__init__.py`` re-exports.  Forge handles this
deterministically so the LLM's emitted code 'just works'.

Idempotent: running multiple times produces the same output.  The
generated banner ``# Auto-managed by atomadic-forge`` lets future runs
detect and refresh; hand-written init files without that banner are left
alone.
"""

from __future__ import annotations

import ast
from pathlib import Path


_BANNER = "# Auto-managed by atomadic-forge — re-exports every public name in this tier."
_INIT_TEMPLATE = (
    '"""Tier {tier} — re-exports."""\n'
    "{banner}\n"
    "\n"
    "{imports}"
    "\n"
    '__all__ = [{all_list}]\n'
)


def _public_names_in_module(py_file: Path) -> list[str]:
    """Return public function/class/constant names defined at module top level."""
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return []
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                names.append(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and not t.id.startswith("_"):
                    names.append(t.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and not node.target.id.startswith("_"):
                names.append(node.target.id)
    # de-dupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def render_tier_init(tier: str, *, modules: dict[str, list[str]]) -> str:
    """Render an ``__init__.py`` for one tier.

    ``modules`` is ``{module_stem: [public_name, ...]}`` for every ``.py``
    file in that tier dir (excluding ``__init__``).
    """
    if not modules:
        return f'"""Tier {tier} — empty."""\n'
    import_lines: list[str] = []
    flat_names: list[str] = []
    for module_stem in sorted(modules):
        names = sorted(modules[module_stem])
        if not names:
            continue
        joined = ", ".join(names)
        import_lines.append(f"from .{module_stem} import {joined}")
        flat_names.extend(names)
    if not import_lines:
        return f'"""Tier {tier} — empty."""\n'
    all_list = ", ".join(repr(n) for n in sorted(set(flat_names)))
    return _INIT_TEMPLATE.format(
        tier=tier,
        banner=_BANNER,
        imports="\n".join(import_lines) + "\n",
        all_list=all_list,
    )


def rebuild_tier_inits(package_root: Path) -> dict[str, str]:
    """Rebuild every ``aN_*/__init__.py`` under ``package_root``.

    Returns a map of ``relative_path -> new_content`` for the files that
    Forge re-generated (skips files without the banner — those are
    user-edited and we leave them alone).
    """
    package_root = Path(package_root)
    written: dict[str, str] = {}
    for tier_dir in sorted(package_root.iterdir()):
        if not tier_dir.is_dir():
            continue
        if not tier_dir.name.startswith(("a0_", "a1_", "a2_", "a3_", "a4_")):
            continue
        modules: dict[str, list[str]] = {}
        for py in sorted(tier_dir.glob("*.py")):
            if py.name == "__init__.py":
                continue
            names = _public_names_in_module(py)
            if names:
                modules[py.stem] = names
        new_text = render_tier_init(tier_dir.name, modules=modules)
        init = tier_dir / "__init__.py"
        # Don't clobber a hand-written init (no banner ⇒ assume user-managed).
        if init.exists():
            current = init.read_text(encoding="utf-8")
            if _BANNER not in current and current.strip() not in (
                "", f'"""{tier_dir.name}."""',
            ):
                continue
        init.write_text(new_text, encoding="utf-8")
        written[init.relative_to(package_root).as_posix()] = new_text
    return written
