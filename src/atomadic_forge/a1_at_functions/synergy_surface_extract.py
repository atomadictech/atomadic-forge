"""Tier a1 — pure feature-surface extractor for the Synergy Scan.

Walks ``commands/`` modules + the unified CLI to build a
:class:`FeatureSurfaceCard` per CLI verb.  The card captures:

* CLI option names
* file-pattern args (anything ending in ``.json`` / ``.yaml`` / ``.md`` …)
* product mentions in help text (``--json-out``, ``--save``, ``MANIFEST``)
* schema strings (``atomadic-forge.<x>/v1``) referenced in source
* a phase hint (``recon`` / ``ingest`` / ``materialize`` / ``emit`` / …)
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from ..a0_qk_constants.synergy_types import FeatureSurfaceCard


_PHASE_VOCAB = {
    "recon": {"recon", "scout", "inventory", "discover"},
    "ingest": {"ingest", "scan", "harvest", "extract"},
    "plan": {"plan", "policy", "blueprint"},
    "materialize": {"materialize", "rebuild", "synth", "synthesise", "synthesize",
                    "wrap", "generate"},
    "certify": {"certify", "verify", "audit", "smoke", "lint"},
    "emit": {"emit", "save", "publish", "report", "manifest", "json-out"},
    "register": {"register", "wire", "sync", "install"},
}

_FILE_RE = re.compile(r"\b([\w\-./]+\.(?:json|yaml|yml|md|toml|txt))\b")
_SCHEMA_RE = re.compile(r"atomadic-forge\.[a-z0-9._\-]+/v\d+")


def _docstring(node: ast.AST) -> str:
    return (ast.get_docstring(node) or "").strip()


def _split_words(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9_\-]+", text or "")
            if len(w) >= 3}


def _phase_hint(words: set[str], help_text: str, name: str) -> str:
    haystack = words | {name.lower()}
    haystack |= _split_words(help_text)
    best, score = "misc", 0
    for phase, terms in _PHASE_VOCAB.items():
        hits = len(terms & haystack)
        if hits > score:
            best, score = phase, hits
    return best


def _option_args(fn: ast.FunctionDef) -> tuple[list[str], list[str]]:
    """Return (canonical option names, file-pattern hints)."""
    opts: list[str] = []
    files: list[str] = []
    for arg in fn.args.args:
        if arg.arg in ("self", "cls", "ctx"):
            continue
        opts.append(arg.arg.replace("_", "-"))
        ann = ast.unparse(arg.annotation) if arg.annotation else ""
        if "Path" in ann or "json" in ann.lower():
            files.append(arg.arg)
    return opts, files


def _typer_decorator_name(dec: ast.AST) -> str:
    if isinstance(dec, ast.Call):
        return _typer_decorator_name(dec.func)
    if isinstance(dec, ast.Attribute):
        return dec.attr
    if isinstance(dec, ast.Name):
        return dec.id
    return ""


def _is_typer_command(fn: ast.FunctionDef) -> bool:
    for d in fn.decorator_list:
        if _typer_decorator_name(d) == "command":
            return True
    return False


def _harvest_module(py_file: Path, module: str) -> list[FeatureSurfaceCard]:
    try:
        text = py_file.read_text(encoding="utf-8")
        tree = ast.parse(text)
    except (SyntaxError, OSError):
        return []
    schemas = sorted(set(_SCHEMA_RE.findall(text)))
    cards: list[FeatureSurfaceCard] = []
    module_help = _docstring(tree).split("\n", 1)[0].strip()
    # If module exposes its own ``app: typer.Typer`` (whole sub-CLI), make it
    # one feature whose 'verbs' are the @app.command()-decorated functions.
    has_typer_app = any(
        isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "app" for t in node.targets)
        for node in tree.body
    )
    inputs: list[str] = []
    input_files: list[str] = []
    outputs: list[str] = []
    output_files: list[str] = []
    vocab: set[str] = _split_words(module_help)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if not _is_typer_command(node) and node.name != "register":
                continue
            opts, files = _option_args(node)
            inputs.extend(opts)
            input_files.extend(files)
            doc = _docstring(node)
            vocab |= _split_words(doc)
            for hit in _FILE_RE.findall(doc):
                if any(t in opts for t in ("save", "out", "json")):
                    output_files.append(hit)
                else:
                    input_files.append(hit)
            for opt in opts:
                if "out" in opt or "save" in opt or "report" in opt or "json" in opt:
                    outputs.append(opt)
    if has_typer_app or any(node for node in tree.body
                            if isinstance(node, ast.FunctionDef)
                            and _is_typer_command(node)):
        name = py_file.stem
        cards.append(FeatureSurfaceCard(
            name=name.replace("_", "-").rstrip("-cli"),
            module=module,
            help_text=module_help,
            inputs=sorted(set(inputs)),
            input_files=sorted(set(input_files)),
            outputs=sorted(set(outputs)),
            output_files=sorted(set(output_files)),
            schemas=schemas,
            vocabulary=sorted(vocab),
            phase_hint=_phase_hint(vocab, module_help, name),
        ))
    return cards


def harvest_feature_surfaces(
    package_root: Path,
    package: str = "atomadic_forge",
) -> list[FeatureSurfaceCard]:
    """Walk ``<package_root>/<package>/commands/`` and harvest one card per file."""
    base = package_root / package / "commands"
    if not base.exists():
        return []
    out: list[FeatureSurfaceCard] = []
    for py in sorted(base.rglob("*.py")):
        if py.name.startswith("_"):
            continue
        rel = py.relative_to(package_root).with_suffix("")
        module = ".".join(rel.parts)
        out.extend(_harvest_module(py, module))
    # Also include the unified CLI's hand-wired top-level commands.
    unified = package_root / package / "a4_sy_orchestration" / "unified_cli.py"
    if unified.exists():
        out.extend(_harvest_module(unified, f"{package}.a4_sy_orchestration.unified_cli"))
    return out
