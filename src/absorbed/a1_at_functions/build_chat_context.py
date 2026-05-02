"""Tier a1 — bounded repo context for the Forge chat copilot."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..a0_qk_constants.lang_extensions import IGNORED_DIRS, file_class_for_path

_CONTEXT_CLASSES = {"source", "documentation", "config"}
_SENSITIVE_NAMES = {".env", ".env.local", ".envrc"}
_SENSITIVE_SUBSTRINGS = ("secret", "credential", "private_key")
_SENSITIVE_SUFFIXES = (".pem", ".key", ".p12", ".pfx")
_MAX_FILE_CHARS = 4_000


def chat_system_prompt() -> str:
    """System prompt for chat-only copilot sessions."""
    return (
        "You are Atomadic Forge's chat copilot. Help the user operate this "
        "CLI product, understand repo structure, plan safe commands, and wire "
        "AI-agent workflows through Forge's provider layer. Be concise, be "
        "specific, and prefer concrete commands. If repository context is "
        "provided, ground your answer in it. Do not claim you executed a "
        "command; you are only responding to the chat prompt."
    )


def build_chat_context(paths: list[Path], *, cwd: Path,
                       max_files: int = 12,
                       max_chars: int = 16_000) -> dict[str, Any]:
    """Pack selected repo files into a bounded Markdown context block."""
    cwd = cwd.resolve()
    files = _collect_context_files(paths, cwd=cwd)[:max_files]
    chunks: list[str] = []
    used = 0
    included: list[dict[str, Any]] = []
    for file_path in files:
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        truncated_file = len(text) > _MAX_FILE_CHARS
        if truncated_file:
            text = text[:_MAX_FILE_CHARS] + "\n... [file truncated]\n"
        rel = _rel_display(file_path, cwd)
        chunk = f"### {rel}\n\n```{_fence_lang(file_path)}\n{text}\n```\n"
        remaining = max_chars - used
        if remaining <= 0:
            break
        truncated_context = len(chunk) > remaining
        if truncated_context:
            chunk = chunk[:remaining] + "\n... [context budget exhausted]\n"
        chunks.append(chunk)
        used += len(chunk)
        included.append({
            "path": rel,
            "chars": min(len(text), _MAX_FILE_CHARS),
            "truncated": truncated_file or truncated_context,
        })
        if truncated_context:
            break
    return {
        "context": "\n".join(chunks).strip(),
        "files": included,
        "file_count": len(included),
        "char_count": used,
    }


def render_chat_prompt(message: str, *, context: str = "",
                       history: list[dict[str, str]] | None = None) -> str:
    """Render one chat turn with optional context and prior turns."""
    parts = [
        "# User request",
        message.strip(),
    ]
    if history:
        parts.extend(["", "# Prior chat"])
        for turn in history[-8:]:
            role = turn.get("role", "user")
            content = turn.get("content", "").strip()
            if content:
                parts.append(f"{role}: {content}")
    if context:
        parts.extend(["", "# Repository context", context])
    return "\n".join(parts).strip() + "\n"


def _collect_context_files(paths: list[Path], *, cwd: Path) -> list[Path]:
    out: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        p = path if path.is_absolute() else cwd / path
        if not p.exists():
            continue
        candidates = [p] if p.is_file() else sorted(p.rglob("*"))
        for candidate in candidates:
            if not candidate.is_file():
                continue
            if _ignored(candidate, cwd):
                continue
            if _sensitive(candidate):
                continue
            if file_class_for_path(candidate.as_posix()) not in _CONTEXT_CLASSES:
                continue
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            out.append(resolved)
    return sorted(out, key=lambda p: (_priority(p), p.as_posix().lower()))


def _ignored(path: Path, cwd: Path) -> bool:
    try:
        parts = path.resolve().relative_to(cwd).parts
    except ValueError:
        parts = path.parts
    return any(part in IGNORED_DIRS for part in parts)


def _sensitive(path: Path) -> bool:
    name = path.name.lower()
    return (
        name in _SENSITIVE_NAMES
        or name.endswith(_SENSITIVE_SUFFIXES)
        or any(piece in name for piece in _SENSITIVE_SUBSTRINGS)
    )


def _priority(path: Path) -> tuple[int, int]:
    name = path.name.lower()
    stem = path.stem.lower()
    if name.startswith("readme"):
        return (0, len(path.parts))
    if name in {"pyproject.toml", "package.json"}:
        return (1, len(path.parts))
    if "docs" in {p.lower() for p in path.parts}:
        return (2, len(path.parts))
    if "src" in {p.lower() for p in path.parts}:
        return (3, len(path.parts))
    if stem.startswith("test_") or name.endswith(".test.js"):
        return (4, len(path.parts))
    return (5, len(path.parts))


def _rel_display(path: Path, cwd: Path) -> str:
    try:
        return path.relative_to(cwd).as_posix()
    except ValueError:
        return path.as_posix()


def _fence_lang(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".py": "python",
        ".js": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".jsx": "jsx",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".md": "markdown",
        ".toml": "toml",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
    }.get(ext, "")
