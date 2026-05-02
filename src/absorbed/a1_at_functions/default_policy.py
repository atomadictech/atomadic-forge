"""Tier a1 — pure pyproject.toml [tool.forge.agent] policy reader.

Codex #10. Reads the policy block (if present) and returns an
AgentPolicy dict with defaults filled in for any missing fields.

Pure: one bounded read of pyproject.toml; no other I/O. Returns the
default policy unchanged when no pyproject / no [tool.forge.agent]
section exists — Forge never errors on policy absence.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from ..a0_qk_constants.policy_schema import (
    DEFAULT_MAX_FILES_PER_PATCH,
    DEFAULT_PROTECTED_FILES,
    DEFAULT_RELEASE_GATE,
    DEFAULT_REQUIRE_HUMAN_REVIEW_FOR,
    SCHEMA_VERSION_POLICY_V1,
    AgentPolicy,
)

# Python 3.11+ has stdlib tomllib; older versions need a fallback.
if sys.version_info >= (3, 11):
    import tomllib as _toml  # type: ignore[import-not-found]
else:  # pragma: no cover — Forge requires 3.10+, so this is rare path
    try:
        import tomli as _toml  # type: ignore[import-not-found]
    except ImportError:
        _toml = None  # type: ignore[assignment]


def default_policy() -> AgentPolicy:
    """The lenient baseline policy applied when no [tool.forge.agent]
    section is declared. Every field is mutable — caller can layer
    user overrides on top."""
    return AgentPolicy(
        schema_version=SCHEMA_VERSION_POLICY_V1,
        protected_files=list(DEFAULT_PROTECTED_FILES),
        release_gate=list(DEFAULT_RELEASE_GATE),
        max_files_per_patch=DEFAULT_MAX_FILES_PER_PATCH,
        require_human_review_for=list(DEFAULT_REQUIRE_HUMAN_REVIEW_FOR),
        extra={},
    )


def load_policy(project_root: Path) -> AgentPolicy:
    """Read [tool.forge.agent] from project_root/pyproject.toml.

    Returns the default policy with any user-declared values merged
    on top. Missing pyproject or missing section → defaults.
    Malformed TOML → defaults + a note in extra['_load_error'].
    """
    project_root = Path(project_root).resolve()
    policy = default_policy()

    pp = project_root / "pyproject.toml"
    if not pp.exists() or _toml is None:
        return policy
    try:
        data = _toml.loads(pp.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        policy["extra"] = {"_load_error": f"{type(exc).__name__}: {exc}"}
        return policy

    section = (data.get("tool") or {}).get("forge", {}).get("agent")
    if not isinstance(section, dict):
        return policy

    if isinstance(section.get("protected_files"), list):
        policy["protected_files"] = [str(s) for s in section["protected_files"]]
    if isinstance(section.get("release_gate"), list):
        policy["release_gate"] = [str(s) for s in section["release_gate"]]
    if isinstance(section.get("max_files_per_patch"), int):
        policy["max_files_per_patch"] = int(section["max_files_per_patch"])
    if isinstance(section.get("require_human_review_for"), list):
        policy["require_human_review_for"] = [
            str(s) for s in section["require_human_review_for"]
        ]
    # Forward-compat: any unrecognised keys preserved in extra.
    known = {
        "protected_files", "release_gate", "max_files_per_patch",
        "require_human_review_for",
    }
    extra: dict[str, Any] = {}
    for k, v in section.items():
        if k not in known:
            extra[k] = v
    if extra:
        policy["extra"] = extra
    return policy


def file_is_protected(path: str, policy: AgentPolicy) -> bool:
    """True when ``path`` matches any protected_files entry.

    Matching is exact-or-suffix: 'pyproject.toml' matches
    'pyproject.toml' and 'src/pkg/pyproject.toml' but NOT
    'src/pyproject_helper.py'.
    """
    protected = policy.get("protected_files") or []
    for p in protected:
        if path == p or path.endswith("/" + p) or Path(path).name == p:
            return True
    return False
