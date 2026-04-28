"""Tier a1 — pure JavaScript / TypeScript surface parser.

Forge is a tier classifier, not a JS compiler. We extract the few things
the downstream pipeline needs from JS/TS source via regex:

  * top-level imports (ES6 ``import … from "x"`` and CommonJS ``require("x")``)
  * top-level exported symbols (``export const``, ``export function``,
    ``export class``, ``export default { fetch }`` Worker handlers)
  * cheap state / effect signals (the presence of ``class``, ``let`` at
    module level with subsequent reassignment, ``new`` constructors, and
    Cloudflare-Worker ``fetch`` / ``scheduled`` entry points)

Block comments and string literals are stripped before parsing so we don't
treat ``"import x"`` inside a string as a real import. Single-line ``//``
comments are stripped too. The parser is forgiving — malformed sources
produce an empty surface rather than raising.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# --- comment / string stripping -------------------------------------------

_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"(?<!:)//[^\n]*")
_STRING_RE = re.compile(
    r'"(?:\\.|[^"\\])*"'
    r"|'(?:\\.|[^'\\])*'"
    r"|`(?:\\.|[^`\\])*`",
    re.DOTALL,
)


def strip_comments(src: str) -> str:
    """Remove block + line comments. Pure."""
    src = _BLOCK_COMMENT_RE.sub("", src)
    src = _LINE_COMMENT_RE.sub("", src)
    return src


def strip_comments_and_strings(src: str) -> str:
    """Remove block comments, line comments, and string literals.

    Replaces strings with empty quotes so token positions are preserved
    enough for line-based regex.  Used for export / class / state checks
    where the *contents* of strings are noise.  Import parsers must use
    :func:`strip_comments` instead so the import specifier itself
    survives.
    """
    return _STRING_RE.sub('""', strip_comments(src))


# --- imports --------------------------------------------------------------

# ES6 forms we handle:
#   import "x"
#   import x from "y"
#   import { a, b } from "y"
#   import * as ns from "y"
#   import x, { a } from "y"
#   import type { X } from "y"   (TypeScript)
#   import("x")        ← dynamic import
_ES6_IMPORT_RE = re.compile(
    r"""
    \bimport\b
    (?:                            # any clause shape (or none for side-effect)
        \s+(?:type\s+)?            # optional 'type' for TS
        (?:[A-Za-z_$][\w$]*\s*,?\s*)? # default name
        (?:\{[^}]*\}\s*)?          # named-bindings { a, b }
        (?:\*\s*as\s+[A-Za-z_$][\w$]*\s*)? # namespace
        from\s*
    )?
    \s*
    [\"']([^\"']+)[\"']
    """,
    re.VERBOSE,
)
_DYNAMIC_IMPORT_RE = re.compile(r"""\bimport\s*\(\s*[\"']([^\"']+)[\"']""")
_REQUIRE_RE = re.compile(r"""\brequire\s*\(\s*[\"']([^\"']+)[\"']""")


def _mask_non_import_strings(src: str) -> str:
    """Mask string-literal *contents* unless they directly follow an
    ``import`` / ``from`` / ``require(`` token. Pure.

    The masked output preserves length and quote positions so subsequent
    regex matchers see the surrounding code unchanged.
    """
    out: list[str] = []
    i = 0
    n = len(src)
    keyword_re = re.compile(r"(?:^|[^A-Za-z0-9_$])(import|from|require)\s*\(?\s*$")
    while i < n:
        ch = src[i]
        if ch in ("'", '"', "`"):
            # find end of string
            j = i + 1
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == ch:
                    break
                j += 1
            # decide: was this string preceded by an import-context keyword?
            preceding = src[max(0, i - 40): i]
            preserve = bool(keyword_re.search(preceding))
            if preserve:
                out.append(src[i:j + 1])
            else:
                # mask: keep quote chars at the boundaries, blank middle
                if j < n:
                    out.append(ch + " " * max(0, j - i - 1) + ch)
                else:
                    out.append(ch + " " * (n - i - 1))
            i = j + 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def parse_imports(src: str) -> list[str]:
    """Return every imported module specifier in source-order, deduped.

    Detects ES6 ``import``, dynamic ``import()`` and CommonJS ``require()``.
    Comments are stripped first; non-import string literals are masked so
    a fake ``import x from 'y'`` inside a JS string never registers.
    """
    cleaned = _mask_non_import_strings(strip_comments(src))
    seen: list[str] = []
    for rx in (_ES6_IMPORT_RE, _DYNAMIC_IMPORT_RE, _REQUIRE_RE):
        for m in rx.finditer(cleaned):
            spec = m.group(1)
            if spec and spec not in seen:
                seen.append(spec)
    return seen


# --- exports / symbols ----------------------------------------------------

_EXPORT_FUNCTION_RE = re.compile(
    r"\bexport\s+(?:async\s+)?function\s+([A-Za-z_$][\w$]*)"
)
_EXPORT_CLASS_RE = re.compile(r"\bexport\s+class\s+([A-Za-z_$][\w$]*)")
_EXPORT_CONST_RE = re.compile(r"\bexport\s+(?:const|let|var)\s+([A-Za-z_$][\w$]*)")
_EXPORT_DEFAULT_OBJECT_OPEN_RE = re.compile(r"\bexport\s+default\s*\{")
_EXPORT_DEFAULT_FUNCTION_RE = re.compile(
    r"\bexport\s+default\s+(?:async\s+)?function(?:\s+([A-Za-z_$][\w$]*))?"
)
_EXPORT_DEFAULT_CLASS_RE = re.compile(
    r"\bexport\s+default\s+class(?:\s+([A-Za-z_$][\w$]*))?"
)
# CommonJS:  module.exports = { … }   exports.foo = …
_MODULE_EXPORTS_OBJECT_RE = re.compile(
    r"\bmodule\.exports\s*=\s*\{\s*([^}]{0,300})\}", re.DOTALL
)
_EXPORTS_PROPERTY_RE = re.compile(r"\bexports\.([A-Za-z_$][\w$]*)\s*=")

# Top-level (non-export) declarations we track for inferring tier.
_TOP_FUNCTION_RE = re.compile(
    r"^(?:async\s+)?function\s+([A-Za-z_$][\w$]*)", re.MULTILINE
)
_TOP_CLASS_RE = re.compile(r"^class\s+([A-Za-z_$][\w$]*)", re.MULTILINE)
_TOP_CONST_RE = re.compile(
    r"^(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=", re.MULTILINE
)


@dataclass
class JsSurface:
    """The parsed surface of a single JS/TS file."""

    imports: list[str] = field(default_factory=list)
    exported_functions: list[str] = field(default_factory=list)
    exported_classes: list[str] = field(default_factory=list)
    exported_consts: list[str] = field(default_factory=list)
    default_export_kind: str = ""  # "" | "object" | "function" | "class"
    default_export_keys: list[str] = field(default_factory=list)
    has_class: bool = False
    has_module_exports: bool = False
    has_worker_default_fetch: bool = False
    has_scheduled_handler: bool = False
    top_level_consts: list[str] = field(default_factory=list)
    top_level_functions: list[str] = field(default_factory=list)
    top_level_classes: list[str] = field(default_factory=list)
    statement_count: int = 0

    @property
    def all_exports(self) -> list[str]:
        seen: list[str] = []
        for name in (
            self.exported_functions
            + self.exported_classes
            + self.exported_consts
            + self.default_export_keys
        ):
            if name and name not in seen:
                seen.append(name)
        return seen


def _balance_braces(src: str, open_idx: int) -> int:
    """Return the index of the matching close brace for ``src[open_idx] == '{'``.

    Brace-counts while skipping string literals and comments. Returns
    ``-1`` if no match is found (malformed source).
    """
    if open_idx >= len(src) or src[open_idx] != "{":
        return -1
    depth = 0
    i = open_idx
    n = len(src)
    while i < n:
        ch = src[i]
        if ch == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            i = n if j == -1 else j + 1
            continue
        if ch == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            i = n if j == -1 else j + 2
            continue
        if ch in ("'", '"', "`"):
            j = i + 1
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == ch:
                    break
                j += 1
            i = j + 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _top_level_object_keys(src: str, open_idx: int) -> list[str]:
    """Extract identifier keys at depth-1 of the object starting at ``{``.

    Skips nested ``{}``, ``[]``, ``()`` blocks, comments and strings; reads
    only the leading identifier of each property. Tolerant — any token it
    doesn't recognise is silently skipped.
    """
    close = _balance_braces(src, open_idx)
    if close < 0:
        return []
    keys: list[str] = []
    i = open_idx + 1
    n = close
    while i < n:
        ch = src[i]
        # skip whitespace / commas
        if ch.isspace() or ch == ",":
            i += 1
            continue
        # skip comments
        if ch == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            i = n if j == -1 or j > n else j + 1
            continue
        if ch == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            i = n if j == -1 or j > n else j + 2
            continue
        # spread / computed keys we don't try to parse
        if ch in ("[", "."):
            i += 1
            continue
        # quoted-string key — skip its value
        if ch in ("'", '"', "`"):
            i = _skip_string(src, i) + 1
            continue
        # identifier?
        m = re.match(r"(?:async\s+)?(?:get\s+|set\s+)?([A-Za-z_$][\w$]*)",
                     src[i:n])
        if not m:
            i += 1
            continue
        name = m.group(1)
        if name not in ("async", "get", "set") and name not in keys:
            keys.append(name)
        # skip past identifier
        i += m.end()
        # skip past the value: jump to next top-level comma
        while i < n:
            c2 = src[i]
            if c2 == "{":
                e = _balance_braces(src, i)
                i = (e + 1) if e > i else (i + 1)
                continue
            if c2 == "[":
                e = _balance_brackets(src, i)
                i = (e + 1) if e > i else (i + 1)
                continue
            if c2 == "(":
                e = _balance_parens(src, i)
                i = (e + 1) if e > i else (i + 1)
                continue
            if c2 in ("'", '"', "`"):
                i = _skip_string(src, i) + 1
                continue
            if c2 == "/" and i + 1 < n and src[i + 1] == "/":
                j = src.find("\n", i)
                i = n if j == -1 or j > n else j + 1
                continue
            if c2 == "/" and i + 1 < n and src[i + 1] == "*":
                j = src.find("*/", i + 2)
                i = n if j == -1 or j > n else j + 2
                continue
            if c2 == ",":
                i += 1
                break
            i += 1
    return keys


def _skip_string(src: str, i: int) -> int:
    """Return the index of the closing quote of a string literal at ``src[i]``."""
    quote = src[i]
    j = i + 1
    n = len(src)
    while j < n:
        if src[j] == "\\":
            j += 2
            continue
        if src[j] == quote:
            return j
        j += 1
    return n - 1


def _balance_brackets(src: str, open_idx: int) -> int:
    return _balance_pair(src, open_idx, "[", "]")


def _balance_parens(src: str, open_idx: int) -> int:
    return _balance_pair(src, open_idx, "(", ")")


def _balance_pair(src: str, open_idx: int, opener: str, closer: str) -> int:
    if open_idx >= len(src) or src[open_idx] != opener:
        return -1
    depth = 0
    i = open_idx
    n = len(src)
    while i < n:
        ch = src[i]
        if ch in ("'", '"', "`"):
            i = _skip_string(src, i) + 1
            continue
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def parse_surface(src: str) -> JsSurface:
    """Return a ``JsSurface`` describing the file's exports + signals.

    Forgiving: any regex misfire on malformed source produces an empty
    field rather than raising. Block comments and string literals are
    stripped first so we don't pick up imports inside docs.
    """
    # Two views:
    #   ``cleaned``   — comments + string contents stripped (for surface regexes)
    #   ``no_comm``   — comments stripped only (for brace-walking, which needs
    #                    the real braces)
    cleaned = strip_comments_and_strings(src)
    no_comm = strip_comments(src)
    s = JsSurface()

    s.imports = parse_imports(src)
    s.exported_functions = _unique(_EXPORT_FUNCTION_RE.findall(cleaned))
    s.exported_classes = _unique(_EXPORT_CLASS_RE.findall(cleaned))
    s.exported_consts = _unique(_EXPORT_CONST_RE.findall(cleaned))

    default_obj = _EXPORT_DEFAULT_OBJECT_OPEN_RE.search(no_comm)
    default_fn = _EXPORT_DEFAULT_FUNCTION_RE.search(cleaned)
    default_cls = _EXPORT_DEFAULT_CLASS_RE.search(cleaned)
    if default_obj:
        s.default_export_kind = "object"
        # The match ends just past the opening ``{`` — step back one to point
        # at the brace.
        open_idx = default_obj.end() - 1
        s.default_export_keys = _top_level_object_keys(no_comm, open_idx)
        if "fetch" in s.default_export_keys:
            s.has_worker_default_fetch = True
        if "scheduled" in s.default_export_keys:
            s.has_scheduled_handler = True
    elif default_fn:
        s.default_export_kind = "function"
        if default_fn.group(1):
            s.default_export_keys = [default_fn.group(1)]
    elif default_cls:
        s.default_export_kind = "class"
        if default_cls.group(1):
            s.default_export_keys = [default_cls.group(1)]

    if _MODULE_EXPORTS_OBJECT_RE.search(cleaned):
        s.has_module_exports = True
    s.exported_consts.extend(
        n for n in _EXPORTS_PROPERTY_RE.findall(cleaned)
        if n not in s.exported_consts
    )

    s.top_level_functions = _unique(_TOP_FUNCTION_RE.findall(cleaned))
    s.top_level_classes = _unique(_TOP_CLASS_RE.findall(cleaned))
    s.top_level_consts = _unique(_TOP_CONST_RE.findall(cleaned))

    s.has_class = bool(s.top_level_classes or s.exported_classes)
    if not s.has_scheduled_handler and re.search(r"\bscheduled\s*\(", cleaned):
        s.has_scheduled_handler = True

    s.statement_count = sum(1 for line in cleaned.splitlines() if line.strip())
    return s


def _unique(items: list[str]) -> list[str]:
    seen: list[str] = []
    for x in items:
        if x and x not in seen:
            seen.append(x)
    return seen


# --- tier classification --------------------------------------------------

def classify_js_tier(*, path: str, surface: JsSurface) -> str:
    """Return the canonical tier directory for a JS/TS file.

    Honours an explicit ``aN_*`` directory placement first; otherwise infers
    from the parsed surface:

      * ``a4_sy_orchestration`` — Cloudflare Worker default ``{ fetch }``,
        scheduled handlers, top-level ``server.listen``, or a CLI shebang.
      * ``a0_qk_constants`` — only ``export const`` declarations, no
        functions, no classes.
      * ``a2_mo_composites`` — has a class or holds module-level state.
      * ``a3_og_features`` — directory hint or feature-flavoured name.
      * ``a1_at_functions`` — pure function module (default).
    """
    norm = path.replace("\\", "/").lower()
    for tier in (
        "a0_qk_constants",
        "a1_at_functions",
        "a2_mo_composites",
        "a3_og_features",
        "a4_sy_orchestration",
    ):
        if f"/{tier}/" in f"/{norm}/" or norm.startswith(f"{tier}/"):
            return tier

    if surface.has_worker_default_fetch or surface.has_scheduled_handler:
        return "a4_sy_orchestration"

    name = norm.rsplit("/", 1)[-1]
    if (
        name.endswith(("_main.js", "_cli.js", "_runner.js", "_server.js",
                       "_main.ts", "_cli.ts", "_runner.ts", "_server.ts"))
        or name in {"server.js", "main.js", "index.js", "worker.js",
                     "server.ts", "main.ts", "index.ts", "worker.ts"}
        or "/bin/" in f"/{norm}"
    ):
        # index.js / main.ts often *are* the top entry point of a package
        return "a4_sy_orchestration"

    only_consts = (
        surface.exported_consts
        and not surface.exported_functions
        and not surface.exported_classes
        and not surface.top_level_functions
        and not surface.top_level_classes
        and not surface.default_export_kind
    )
    if only_consts:
        return "a0_qk_constants"

    if surface.has_class:
        return "a2_mo_composites"

    if any(tag in name for tag in ("_feature", "_pipeline", "_gate", "_service")):
        return "a3_og_features"

    if any(
        tag in name
        for tag in ("_client", "_store", "_registry", "_core", "_state")
    ):
        return "a2_mo_composites"

    if any(
        tag in name
        for tag in ("_utils", "_helpers", "_validators", "_parsers",
                     "_format", "_formatter")
    ):
        return "a1_at_functions"

    return "a1_at_functions"


# --- effect inference -----------------------------------------------------

_NETWORK_RE = re.compile(
    r"\b(fetch|XMLHttpRequest|WebSocket|http\.request|https\.request)\b"
)
_FS_RE = re.compile(
    r"\b(fs\.(?:read|write|append|unlink|mkdir)|require\(['\"]fs['\"]\))"
)
_STATE_RE = re.compile(r"\b(let|var)\b")


def detect_js_effects(src: str) -> list[str]:
    """Cheap effect inference. Same shape as the Python ``detect_effects``."""
    cleaned = strip_comments_and_strings(src)
    effects: list[str] = []
    if _NETWORK_RE.search(cleaned) or _FS_RE.search(cleaned):
        effects.append("io")
    if "class " in cleaned or _STATE_RE.search(cleaned):
        effects.append("state")
    if not effects:
        return ["pure"]
    seen: list[str] = []
    for e in effects:
        if e not in seen:
            seen.append(e)
    return seen
