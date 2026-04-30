"""Tier a0 — language extensions and ignore lists Forge recognises.

Pure data. Determines which files Forge's recon, wire, and certify passes
include in their walks. Adding a language is a one-line change here.

Files Forge classifies into three buckets:
  * **source**       — code that participates in tier classification, wire
                       checks, and import-graph analysis.
  * **documentation** / **config** / **asset** — files that contribute to
                       repo *signals* (a README.md flips ``has_readme``,
                       a docs/ARCHITECTURE.md flips ``has_docs``) but are
                       NEVER counted as "untiered code" — they have no
                       tier identity and harshing the layout score on
                       their position would be wrong.

Plus an ignore list of directories Forge never recurses into (VCS internals,
package caches, build outputs, AI-tooling worktrees, etc.).
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

# Documentation: contributes positively to the docs signal; never tier-classified.
DOC_EXTS: Final[frozenset[str]] = frozenset({
    ".md", ".markdown", ".mdx", ".rst", ".txt", ".adoc", ".asciidoc",
})

# Config / data files: present-but-not-code.  Never count toward tier layout.
CONFIG_EXTS: Final[frozenset[str]] = frozenset({
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".env", ".lock", ".gitignore", ".editorconfig",
})

# Page / image / binary assets.  Same treatment as docs/config.
ASSET_EXTS: Final[frozenset[str]] = frozenset({
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
    ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp",
    ".pdf", ".docx", ".pptx", ".xlsx",
    ".woff", ".woff2", ".ttf", ".otf",
    ".mp3", ".mp4", ".wav", ".webm",
})

# Map a file extension to a canonical language label.
LANG_OF_EXT: Final[dict[str, str]] = {
    **{e: "python" for e in PYTHON_EXTS},
    **{e: "javascript" for e in JAVASCRIPT_EXTS},
    **{e: "typescript" for e in TYPESCRIPT_EXTS},
}

# Directories Forge never recurses into.  These hold tooling, caches, build
# outputs, agent worktrees, and dependencies — none of it is Atomadic's code.
IGNORED_DIRS: Final[frozenset[str]] = frozenset({
    # Version control
    ".git", ".hg", ".svn",
    # Package / language caches
    "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache",
    ".mypy_cache", ".tox", ".nox", ".cache",
    # Build outputs
    "dist", "build", "out", "target", ".next", ".nuxt", ".svelte-kit",
    "coverage", ".coverage", "htmlcov",
    # Virtualenvs
    ".venv", "venv", "env", ".env",
    # IDE / AI tooling
    ".vscode", ".idea", ".cursor", ".codeium", ".aider",
    ".claude", ".github",
    # Agent / worktree clutter
    "worktrees", ".worktrees",
    # Cloudflare / wrangler
    ".wrangler", ".wrangler-cache",
    # Atomadic-Forge's own scratch dir
    ".atomadic-forge",
})


def is_ignored_dir_name(name: str) -> bool:
    """Return True for directory names Forge should never recurse into."""
    return name in IGNORED_DIRS or name.startswith(".pytest_tmp")


def path_parts_contain_ignored_dir(parts: tuple[str, ...]) -> bool:
    """Return True when any path segment is an ignored directory name."""
    return any(is_ignored_dir_name(part) for part in parts)


def lang_for_path(path: str) -> str | None:
    """Return ``"python"`` / ``"javascript"`` / ``"typescript"`` or ``None``.

    Pure: only the suffix is consulted, never the file content.
    """
    s = path.lower()
    for ext, lang in LANG_OF_EXT.items():
        if s.endswith(ext):
            return lang
    return None


def file_class_for_path(path: str) -> str:
    """Return ``"source"`` / ``"documentation"`` / ``"config"`` / ``"asset"``
    / ``"other"`` — the broad class Forge treats this file as.

    Pure: only the path is consulted.  Used by certify to decide whether a
    file's location should affect tier-layout scoring (only ``source`` does).
    """
    p = path.lower()
    # Filename-based dotfile matches (no extension)
    base = p.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if base in {".gitignore", ".editorconfig", ".env"}:
        return "config"
    if base.startswith(".env."):
        return "config"
    if base in {"license", "license.md", "license.txt", "readme", "readme.md", "readme.rst"}:
        return "documentation"
    # Extension-based
    for ext in ALL_SOURCE_EXTS:
        if p.endswith(ext):
            return "source"
    for ext in DOC_EXTS:
        if p.endswith(ext):
            return "documentation"
    for ext in CONFIG_EXTS:
        if p.endswith(ext):
            return "config"
    for ext in ASSET_EXTS:
        if p.endswith(ext):
            return "asset"
    return "other"


def is_ignored_segment(segment: str) -> bool:
    """Return True if a path segment matches an ignored directory name.

    Kept for callers that still ask about one segment at a time; delegates
    to the same predicate used by full-path ignore checks.
    """
    return is_ignored_dir_name(segment)
