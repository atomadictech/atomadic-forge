"""Tier a1 - deterministic semantic fingerprint for Python source.

Pure stateless. Given a Python source string, returns stable hashes
that survive renames, whitespace changes, and comment edits but
break on real logic changes. The atomic primitive that makes
"never reinvent the wheel" enforceable: two modules with identical
function-shape signatures are duplicate logic.

PREVENT pillar - block duplicate emits at the gate before they ship.

Returned shape::

    ModuleSignature(
        schema="atomadic-forge.code-signature/v1",
        module_hash="<hex>",        # full-module shape hash
        functions=[FunctionSignature(...), ...],
        classes=[ClassSignature(...), ...],
        imports=("os", "ast", ...),  # sorted top-level imports
    )

Two ModuleSignatures with the same ``module_hash`` are byte-stable
duplicates of each other's logic, regardless of identifier names
or formatting.
"""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass, field

SCHEMA: str = "atomadic-forge.code-signature/v1"


@dataclass(frozen=True)
class FunctionSignature:
    name: str
    arg_count: int
    is_async: bool
    body_hash: str       # hash of normalized AST (no identifiers)
    calls: tuple[str, ...]  # sorted set of names this function calls


@dataclass(frozen=True)
class ClassSignature:
    name: str
    method_count: int
    has_state: bool      # __init__ assigns to self.X
    body_hash: str


@dataclass(frozen=True)
class ModuleSignature:
    schema: str = SCHEMA
    module_hash: str = ""
    functions: tuple[FunctionSignature, ...] = field(default_factory=tuple)
    classes: tuple[ClassSignature, ...] = field(default_factory=tuple)
    imports: tuple[str, ...] = field(default_factory=tuple)
    parse_ok: bool = True


def _normalize_ast(node: ast.AST) -> str:
    """Walk an AST node and emit a string of just the structural
    shape - no identifier names, no string literals, no docstrings.
    Two functions with identical control flow + call shape get
    identical normalized output regardless of variable names."""
    parts: list[str] = []
    for sub in ast.walk(node):
        cls = type(sub).__name__
        # Capture structural detail without leaking identifiers.
        if isinstance(sub, ast.Constant):
            parts.append(f"C:{type(sub.value).__name__}")
        elif isinstance(sub, ast.BinOp):
            parts.append(f"B:{type(sub.op).__name__}")
        elif isinstance(sub, ast.Compare):
            ops = "/".join(type(o).__name__ for o in sub.ops)
            parts.append(f"Cmp:{ops}")
        elif isinstance(sub, ast.UnaryOp):
            parts.append(f"U:{type(sub.op).__name__}")
        elif isinstance(sub, (ast.For, ast.While, ast.If, ast.Try,
                                ast.With, ast.Return, ast.Raise,
                                ast.Assign, ast.AugAssign, ast.AnnAssign,
                                ast.FunctionDef, ast.AsyncFunctionDef,
                                ast.ClassDef, ast.Lambda, ast.ListComp,
                                ast.DictComp, ast.SetComp, ast.GeneratorExp,
                                ast.Import, ast.ImportFrom, ast.Call,
                                ast.Attribute, ast.Subscript)):
            parts.append(cls)
    return "|".join(parts)


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _called_names(func_node: ast.AST) -> tuple[str, ...]:
    """Set of names called inside a function body. Used to detect
    'this module just wraps existing primitives' (good reuse) vs
    'this module reimplements logic locally' (bad)."""
    out: set[str] = set()
    for sub in ast.walk(func_node):
        if isinstance(sub, ast.Call):
            f = sub.func
            if isinstance(f, ast.Name):
                out.add(f.id)
            elif isinstance(f, ast.Attribute):
                out.add(f.attr)
    return tuple(sorted(out))


def _has_self_assign(func_node: ast.FunctionDef) -> bool:
    for stmt in ast.walk(func_node):
        if isinstance(stmt, ast.Assign):
            for tgt in stmt.targets:
                if (isinstance(tgt, ast.Attribute)
                        and isinstance(tgt.value, ast.Name)
                        and tgt.value.id == "self"):
                    return True
    return False


def _signature_function(node: ast.FunctionDef | ast.AsyncFunctionDef
                         ) -> FunctionSignature:
    body_hash = _hash(_normalize_ast(node))
    return FunctionSignature(
        name=node.name,
        arg_count=len(node.args.args) + len(node.args.kwonlyargs),
        is_async=isinstance(node, ast.AsyncFunctionDef),
        body_hash=body_hash,
        calls=_called_names(node),
    )


def _signature_class(node: ast.ClassDef) -> ClassSignature:
    methods = [n for n in node.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    has_state = any(_has_self_assign(m) for m in methods
                     if isinstance(m, ast.FunctionDef)
                     and m.name == "__init__")
    body_hash = _hash(_normalize_ast(node))
    return ClassSignature(
        name=node.name,
        method_count=len(methods),
        has_state=has_state,
        body_hash=body_hash,
    )


def _top_level_imports(tree: ast.Module) -> tuple[str, ...]:
    out: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                out.add(node.module)
    return tuple(sorted(out))


def signature_of(source: str) -> ModuleSignature:
    """Pure: source -> ModuleSignature with stable shape hashes."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ModuleSignature(parse_ok=False, module_hash=_hash(source))

    funcs: list[FunctionSignature] = []
    classes: list[ClassSignature] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.append(_signature_function(node))
        elif isinstance(node, ast.ClassDef):
            classes.append(_signature_class(node))

    imports = _top_level_imports(tree)
    # Module hash is order-invariant over functions + classes;
    # sort by body_hash so two files with same content in different
    # order collide.
    fn_hashes = sorted(f.body_hash for f in funcs)
    cls_hashes = sorted(c.body_hash for c in classes)
    blob = "|".join(fn_hashes + cls_hashes + list(imports))
    return ModuleSignature(
        module_hash=_hash(blob),
        functions=tuple(funcs),
        classes=tuple(classes),
        imports=imports,
        parse_ok=True,
    )


def function_overlap(a: ModuleSignature, b: ModuleSignature
                       ) -> tuple[FunctionSignature, ...]:
    """Functions present in both modules with identical body_hash.
    Use to spot 'this new module reimplements N functions that
    already exist' before accepting an emit."""
    a_by_hash = {f.body_hash: f for f in a.functions}
    return tuple(f for f in b.functions if f.body_hash in a_by_hash)
