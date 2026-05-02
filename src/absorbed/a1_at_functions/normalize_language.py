"""Tier a0 — generation language constants for forge iterate / evolve.

Forge's generator loop (``forge iterate``, ``forge evolve``) emits source
code in a target language.  The default has always been Python; this module
adds JavaScript and TypeScript as first-class targets so an LLM can produce
Cloudflare-Worker-shaped or Node-shaped tier scaffolds with the same loop.

Pure data.  Determines:
  * ``PKG_ROOT_TEMPLATE`` — where Forge writes the generated package
    (Python uses ``output/src/<pkg>/`` for pip-install compatibility;
    JS/TS use ``output/<pkg>/`` because there's no ``src/`` PEP).
  * ``ALLOWED_FILE_EXTS`` — what file suffixes ``_safe_path`` accepts.
    Forge rejects any other suffix to prevent the LLM from emitting
    polyglot junk into a single-language tree.
  * ``MAIN_EXT`` — the canonical primary extension (``.py`` / ``.js`` /
    ``.ts``) used in scaffolded tier file names.
  * ``EMITS_INIT_FILES`` — whether Forge generates ``__init__.py``-style
    package indices (Python only).
  * ``EMITS_PYPROJECT`` — whether Forge writes ``pyproject.toml`` (Python
    only).  JS/TS scaffolds get a minimal ``package.json`` instead.

This is intentionally small.  More language-specific knobs (e.g. tsconfig
generation, vitest vs node:test) belong in scaffold helpers, not here.
"""

from __future__ import annotations

from typing import Final, Literal

Language = Literal["python", "javascript", "typescript"]

LANGUAGES: Final[tuple[Language, ...]] = ("python", "javascript", "typescript")

DEFAULT_LANGUAGE: Final[Language] = "python"


# Package-root templates.  The keys are language names; values are
# format strings with a single ``{package}`` substitution that gets
# joined to the user's ``output`` directory.
PKG_ROOT_TEMPLATE: Final[dict[Language, str]] = {
    "python":     "src/{package}",
    "javascript": "{package}",
    "typescript": "{package}",
}


# File suffixes Forge will accept from an LLM emit, per language.  Every
# other suffix is silently dropped by ``_safe_path``.  Note all languages
# allow ``.md`` (READMEs / per-file documentation) and the relevant config
# file (``.toml`` for Python, ``.json`` for JS/TS).
ALLOWED_FILE_EXTS: Final[dict[Language, frozenset[str]]] = {
    "python":     frozenset({".py", ".md", ".toml"}),
    "javascript": frozenset({".js", ".mjs", ".cjs", ".jsx",
                              ".json", ".md"}),
    "typescript": frozenset({".ts", ".tsx", ".js", ".mjs",
                              ".json", ".md"}),
}


# Canonical primary extension used when Forge scaffolds tier files.
MAIN_EXT: Final[dict[Language, str]] = {
    "python":     ".py",
    "javascript": ".js",
    "typescript": ".ts",
}


# Whether Forge emits Python-style package indices (``__init__.py``).
# JS/TS use ES module exports directly — no per-directory index file
# is required for imports to resolve.
EMITS_INIT_FILES: Final[dict[Language, bool]] = {
    "python":     True,
    "javascript": False,
    "typescript": False,
}


# Whether Forge writes a ``pyproject.toml`` at the output root.
# JS/TS scaffolds get a minimal ``package.json`` from a different helper.
EMITS_PYPROJECT: Final[dict[Language, bool]] = {
    "python":     True,
    "javascript": False,
    "typescript": False,
}


def normalize_language(value: str | None) -> Language:
    """Coerce a user-supplied language string into the canonical Language.

    Accepts ``"python" | "javascript" | "js" | "typescript" | "ts"`` (and
    common aliases).  Returns the canonical Language literal.  Raises
    ``ValueError`` if the input is not recognised.

    ``None`` returns the default language (``"python"``) so callers can
    pass through optional CLI flags without branching.
    """
    if value is None:
        return DEFAULT_LANGUAGE
    v = value.strip().lower()
    if v in ("python", "py"):
        return "python"
    if v in ("javascript", "js", "node"):
        return "javascript"
    if v in ("typescript", "ts"):
        return "typescript"
    raise ValueError(
        f"unknown language: {value!r} — expected one of {list(LANGUAGES)}"
    )


def pkg_root_for(language: Language, package: str) -> str:
    """Return the package-root path *relative to the output directory*.

    Pure: no I/O.  Caller joins this against their output ``Path``.
    """
    return PKG_ROOT_TEMPLATE[language].format(package=package)
