"""Tier a0 — language extensions Forge recognises.

Pure data. Determines which files Forge's recon, wire, and certify passes
include in their walks. Adding a language is a one-line change here.
"""

from __future__ import annotations

from typing import Final


# Extensions Forge classifies as Python source.
PYTHON_EXTS: Final[frozenset[str]] = frozenset({".py"})

# Extensions Forge classifies as JavaScript source.
JAVASCRIPT_EXTS: Final[frozenset[str]] = frozenset({".js", ".mjs", ".cjs", ".jsx"})

# Extensions Forge classifies as TypeScript source.
TYPESCRIPT_EXTS: Final[frozenset[str]] = frozenset({".ts", ".tsx"})

# All source extensions Forge walks. Order matters only for stable iteration.
ALL_SOURCE_EXTS: Final[frozenset[str]] = (
    PYTHON_EXTS | JAVASCRIPT_EXTS | TYPESCRIPT_EXTS
)

# Map a file extension to a canonical language label.
LANG_OF_EXT: Final[dict[str, str]] = {
    **{e: "python" for e in PYTHON_EXTS},
    **{e: "javascript" for e in JAVASCRIPT_EXTS},
    **{e: "typescript" for e in TYPESCRIPT_EXTS},
}


def lang_for_path(path: str) -> str | None:
    """Return ``"python"`` / ``"javascript"`` / ``"typescript"`` or ``None``.

    Pure: only the suffix is consulted, never the file content.
    """
    s = path.lower()
    for ext, lang in LANG_OF_EXT.items():
        if s.endswith(ext):
            return lang
    return None
