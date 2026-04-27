"""Tier a1 — pure discovery for the Commandsmith CLI registry.

Walks a directory tree of would-be command modules and returns a list of
:class:`RegisteredCommandCard` describing what each module exports.

Three recognised surfaces:

* **typer_app** — module exposes a top-level ``app: typer.Typer``.
* **register_fn** — module exposes ``register(app: typer.Typer) -> None``.
* **wrapped_class** — module exposes a public class plus a class-level
  ``COMMAND_NAME`` attribute, indicating it should be wrapped by the
  generator (see ``commandsmith_render``).

This module is pure: it only reads files and parses AST.  It NEVER imports
the modules it describes — that lives in tier a2 / a3 to keep a1 import-safe.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable

from ..a0_qk_constants.commandsmith_types import (
    CommandSignatureCard,
    RegisteredCommandCard,
)


_PUBLIC = lambda name: not name.startswith("_")  # noqa: E731 — short pure helper


def _module_for(path: Path, package_root: Path, package: str) -> str:
    rel = path.relative_to(package_root)
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join([package, *parts]) if parts else package


def _docstring_first_line(node: ast.AST) -> str:
    doc = ast.get_docstring(node) or ""
    first = doc.strip().split("\n", 1)[0] if doc else ""
    return first.strip()


def _collect_signature(fn: ast.FunctionDef) -> CommandSignatureCard:
    params: list[str] = []
    for arg in fn.args.args:
        ann = ast.unparse(arg.annotation) if arg.annotation else "Any"
        params.append(f"{arg.arg}: {ann}")
    ret = ast.unparse(fn.returns) if fn.returns else "Any"
    return CommandSignatureCard(
        name=fn.name,
        parameters=params,
        return_type=ret,
        docstring=_docstring_first_line(fn),
    )


def _detect_surface(tree: ast.Module) -> tuple[str, str, bool, list[ast.AST], str]:
    """Return (surface, help_text, hidden, sub_command_nodes, command_name)."""
    has_typer_app = False
    has_register_fn = False
    has_command_name_const = False
    command_name = ""
    help_text = _docstring_first_line(tree)
    hidden = False
    classes: list[ast.ClassDef] = []
    register_fn: ast.FunctionDef | None = None

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id == "app":
                        has_typer_app = True
                    elif target.id == "COMMAND_NAME":
                        has_command_name_const = True
                        if isinstance(node.value, ast.Constant) and isinstance(
                            node.value.value, str
                        ):
                            command_name = node.value.value
                    elif target.id == "COMMAND_HELP":
                        if isinstance(node.value, ast.Constant) and isinstance(
                            node.value.value, str
                        ):
                            help_text = node.value.value
                    elif target.id == "COMMAND_HIDDEN":
                        if isinstance(node.value, ast.Constant) and isinstance(
                            node.value.value, bool
                        ):
                            hidden = node.value.value
        elif isinstance(node, ast.FunctionDef) and node.name == "register":
            has_register_fn = True
            register_fn = node
        elif isinstance(node, ast.ClassDef) and _PUBLIC(node.name):
            classes.append(node)

    if has_typer_app:
        return ("typer_app", help_text, hidden, [], command_name)
    if has_register_fn:
        nodes: list[ast.AST] = [register_fn] if register_fn else []
        return ("register_fn", help_text, hidden, nodes, command_name)
    if has_command_name_const and classes:
        classes[0]._commandsmith_name = command_name  # type: ignore[attr-defined]
        return ("wrapped_class", help_text, hidden, classes, command_name)
    return ("", "", False, [], "")


def discover_command_modules(
    package_root: Path,
    package: str,
    sub_dirs: Iterable[str] = ("commands",),
    source_root: str = "atomadic_forge_seed",
) -> list[RegisteredCommandCard]:
    """Scan ``<package_root>/<sub_dir>`` files for command surfaces.

    Returns a sorted list of :class:`RegisteredCommandCard`.
    Files starting with ``_`` (incl. ``__init__.py``) are ignored.
    """
    cards: list[RegisteredCommandCard] = []
    for sub in sub_dirs:
        base = package_root / sub
        if not base.exists():
            continue
        for py_file in sorted(base.rglob("*.py")):
            if py_file.name.startswith("_"):
                continue
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except (SyntaxError, OSError):
                continue
            surface, help_text, hidden, sub_nodes, explicit_name = _detect_surface(tree)
            if not surface:
                continue
            sub_cmds: list[CommandSignatureCard] = []
            for node in sub_nodes:
                if isinstance(node, ast.FunctionDef):
                    sub_cmds.append(_collect_signature(node))
                elif isinstance(node, ast.ClassDef):
                    for body in node.body:
                        if isinstance(body, ast.FunctionDef) and _PUBLIC(body.name):
                            sub_cmds.append(_collect_signature(body))
            name = py_file.stem
            if surface == "wrapped_class":
                cls = next(
                    (c for c in sub_nodes if isinstance(c, ast.ClassDef)), None
                )
                custom = getattr(cls, "_commandsmith_name", "") if cls else ""
                if custom:
                    name = custom
            # Explicit COMMAND_NAME wins for any surface (e.g. wrappers strip
            # the trailing ``_cli`` suffix to expose a cleaner verb).
            if explicit_name:
                name = explicit_name
            cards.append(
                RegisteredCommandCard(
                    name=name.replace("_", "-"),
                    module=_module_for(py_file, package_root, package),
                    surface=surface,  # type: ignore[arg-type]
                    help_text=help_text,
                    hidden=hidden,
                    sub_commands=sub_cmds,
                    source_root=source_root,
                )
            )
    return sorted(cards, key=lambda c: c["name"])
