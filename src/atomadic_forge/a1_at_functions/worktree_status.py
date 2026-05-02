"""Tier a1 - agent worktree status.

Agents frequently lose time because they are in the wrong checkout, on
the wrong remote, carrying stale local edits, or invoking a globally
installed ``forge`` that is not the source tree they are editing. This
module emits a compact, structured report before the agent mutates a
repo.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TypedDict

SCHEMA_VERSION_WORKTREE_STATUS_V1 = "atomadic-forge.worktree_status/v1"


class WorktreeStatus(TypedDict, total=False):
    schema_version: str
    project_root: str
    git_root: str | None
    is_git_repo: bool
    branch: str
    head: str
    upstream: str
    ahead: int
    behind: int
    dirty: bool
    changed_files: list[str]
    remotes: dict[str, str]
    declared_version: str | None
    package_version: str | None
    version_mismatch: bool
    python_executable: str
    forge_command_path: str
    forge_command_version: str
    forge_command_stale: bool
    recommendations: list[str]


def _run_git(project_root: Path, args: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=project_root,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 1, ""
    return proc.returncode, proc.stdout.rstrip()


def _git_root(project_root: Path) -> str | None:
    rc, out = _run_git(project_root, ["rev-parse", "--show-toplevel"])
    return out if rc == 0 and out else None


def _branch(project_root: Path) -> str:
    rc, out = _run_git(project_root, ["branch", "--show-current"])
    if rc == 0 and out:
        return out
    rc, out = _run_git(project_root, ["rev-parse", "--short", "HEAD"])
    return f"detached:{out}" if rc == 0 and out else ""


def _head(project_root: Path) -> str:
    rc, out = _run_git(project_root, ["rev-parse", "--short", "HEAD"])
    return out if rc == 0 else ""


def _upstream(project_root: Path) -> str:
    rc, out = _run_git(project_root, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    return out if rc == 0 else ""


def _ahead_behind(project_root: Path, upstream: str) -> tuple[int, int]:
    if not upstream:
        return 0, 0
    rc, out = _run_git(project_root, ["rev-list", "--left-right", "--count", f"HEAD...{upstream}"])
    if rc != 0 or not out:
        return 0, 0
    parts = out.split()
    if len(parts) != 2:
        return 0, 0
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return 0, 0


def _changed_files(project_root: Path, *, limit: int) -> list[str]:
    rc, out = _run_git(project_root, ["status", "--short"])
    if rc != 0 or not out:
        return []
    return out.splitlines()[:limit]


def _remotes(project_root: Path) -> dict[str, str]:
    rc, out = _run_git(project_root, ["remote", "-v"])
    remotes: dict[str, str] = {}
    if rc != 0:
        return remotes
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[2] == "(fetch)":
            remotes[parts[0]] = parts[1]
    return remotes


def _read_declared_version(project_root: Path) -> str | None:
    pyproject = project_root / "pyproject.toml"
    if not pyproject.exists():
        return None
    try:
        text = pyproject.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = re.search(r"^version\s*=\s*['\"]([^'\"]+)['\"]", text, re.MULTILINE)
    return match.group(1) if match else None


def _read_package_version(project_root: Path) -> str | None:
    init_py = project_root / "src" / "atomadic_forge" / "__init__.py"
    if not init_py.exists():
        return None
    try:
        text = init_py.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", text)
    return match.group(1) if match else None


def _forge_command_version() -> tuple[str, str]:
    path = shutil.which("forge") or ""
    if not path:
        return "", ""
    try:
        proc = subprocess.run(
            [path, "--version"],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return path, ""
    return path, (proc.stdout or proc.stderr).strip()


def worktree_status(*, project_root: Path, max_files: int = 20) -> WorktreeStatus:
    """Return git/version/install state for an agent's current checkout."""
    project_root = Path(project_root).resolve()
    git_root = _git_root(project_root)
    is_git_repo = git_root is not None
    root = Path(git_root) if git_root else project_root
    branch = _branch(root) if is_git_repo else ""
    upstream = _upstream(root) if is_git_repo else ""
    ahead, behind = _ahead_behind(root, upstream) if is_git_repo else (0, 0)
    changed = _changed_files(root, limit=max_files) if is_git_repo else []
    declared = _read_declared_version(root)
    package = _read_package_version(root)
    command_path, command_version = _forge_command_version()
    command_stale = bool(
        declared and command_version and declared not in command_version
    )
    recommendations: list[str] = []
    if not is_git_repo:
        recommendations.append("not a git repo - verify the project_root before editing")
    if changed:
        recommendations.append("dirty worktree - inspect changed_files before applying patches")
    if behind:
        recommendations.append(f"branch is behind {upstream} by {behind} commit(s) - fetch/rebase before release work")
    if ahead:
        recommendations.append(f"branch is ahead of {upstream} by {ahead} commit(s) - push or open a PR after validation")
    if declared and package and declared != package:
        recommendations.append("pyproject version and atomadic_forge.__version__ differ")
    if command_stale:
        recommendations.append("resolved forge command is stale relative to this checkout; reinstall or use python -m atomadic_forge")
    if not recommendations:
        recommendations.append("worktree clean and version surfaces look aligned")
    return WorktreeStatus(
        schema_version=SCHEMA_VERSION_WORKTREE_STATUS_V1,
        project_root=str(project_root),
        git_root=str(root) if is_git_repo else None,
        is_git_repo=is_git_repo,
        branch=branch,
        head=_head(root) if is_git_repo else "",
        upstream=upstream,
        ahead=ahead,
        behind=behind,
        dirty=bool(changed),
        changed_files=changed,
        remotes=_remotes(root) if is_git_repo else {},
        declared_version=declared,
        package_version=package,
        version_mismatch=bool(declared and package and declared != package),
        python_executable=sys.executable,
        forge_command_path=command_path,
        forge_command_version=command_version,
        forge_command_stale=command_stale,
        recommendations=recommendations,
    )
