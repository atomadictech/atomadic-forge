"""Tier a1 - agent validation command heuristics.

These helpers keep agent-facing tools language-aware without pulling
orchestration concerns into the pure planning layer.
"""
from __future__ import annotations

import json
from pathlib import Path

_TIER_NAMES = (
    "a0_qk_constants",
    "a1_at_functions",
    "a2_mo_composites",
    "a3_og_features",
    "a4_sy_orchestration",
)

_JS_TEST_SUFFIXES = (
    ".test.js", ".spec.js", ".test.mjs", ".spec.mjs",
    ".test.cjs", ".spec.cjs", ".test.ts", ".spec.ts",
    ".test.tsx", ".spec.tsx", ".test.jsx", ".spec.jsx",
)

_PY_TEST_SUFFIXES = (".py",)

_NON_CODE_PREFIXES = (
    "docs/",
    "doc/",
    "research/",
    "launch/",
    ".github/",
    "cognition/guides/",
)

_NON_CODE_NAMES = {
    "README",
    "README.md",
    "README.rst",
    "CHANGELOG.md",
    "LICENSE",
    "NOTICE",
}

_NON_CODE_SUFFIXES = (
    ".md", ".mdx", ".rst", ".txt", ".adoc", ".html", ".css", ".yml", ".yaml",
)


def _read_package_scripts(project_root: Path) -> dict[str, str]:
    package_json = project_root / "package.json"
    if not package_json.exists():
        return {}
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    scripts = data.get("scripts")
    if not isinstance(scripts, dict):
        return {}
    return {str(k): str(v) for k, v in scripts.items()}


def has_python_tests(project_root: Path) -> bool:
    for sub in ("tests", "test"):
        root = project_root / sub
        if not root.is_dir():
            continue
        if any(root.rglob("test_*.py")) or any(root.rglob("*_test.py")):
            return True
    return False


def has_javascript_tests(project_root: Path) -> bool:
    for sub in ("tests", "test"):
        root = project_root / sub
        if not root.is_dir():
            continue
        for test in root.rglob("*"):
            if test.is_file() and test.name.endswith(_JS_TEST_SUFFIXES):
                return True
    return False


def detect_test_commands(project_root: Path) -> list[str]:
    """Return the practical test commands for the detected project."""
    project_root = Path(project_root)
    cmds: list[str] = []
    scripts = _read_package_scripts(project_root)
    if "verify" in scripts:
        cmds.append("npm run verify")
    elif "test" in scripts:
        cmds.append("npm test")
    elif has_javascript_tests(project_root):
        cmds.append("node --test \"tests/**/*.test.js\"")

    if (project_root / "pyproject.toml").exists() or (
        not (project_root / "package.json").exists() and has_python_tests(project_root)
    ):
        cmds.append("python -m pytest")
    if (project_root / "tox.ini").exists():
        cmds.append("tox")
    if (project_root / "Cargo.toml").exists():
        cmds.append("cargo test")
    if (project_root / "Makefile").exists():
        try:
            mk = (project_root / "Makefile").read_text(
                encoding="utf-8", errors="replace")
            if "test:" in mk:
                cmds.append("make test")
        except OSError:
            pass
    return list(dict.fromkeys(cmds)) or ["# no test runner detected - add tests"]


def detect_tier_roots(project_root: Path) -> list[str]:
    """Find tier-organized roots relative to ``project_root``."""
    project_root = Path(project_root)
    roots: list[Path] = []
    skip_parts = {
        ".git", ".venv", "venv", "node_modules", "dist", "build",
        "experiments", ".atomadic-forge", "demo_packages",
    }
    for tier0 in project_root.rglob("a0_qk_constants"):
        if not tier0.is_dir() or any(
            part in skip_parts or part.startswith(".")
            for part in tier0.parts
        ):
            continue
        parent = tier0.parent
        child_names = {child.name for child in parent.iterdir() if child.is_dir()}
        if len(child_names.intersection(_TIER_NAMES)) >= 2:
            roots.append(parent)
    unique = sorted(set(roots), key=lambda p: (len(p.parts), str(p)))
    out: list[str] = []
    for root in unique:
        try:
            rel = root.relative_to(project_root).as_posix()
        except ValueError:
            rel = str(root)
        out.append("." if rel == "." else rel)
    return out


def release_gate_commands(project_root: Path) -> list[str]:
    """Return a language-aware release gate for agents."""
    project_root = Path(project_root)
    gate: list[str] = []
    if (project_root / "pyproject.toml").exists():
        gate.append("python -m ruff check .")
    gate.extend(detect_test_commands(project_root))
    for root in detect_tier_roots(project_root)[:2]:
        gate.append(f"forge wire {root} --fail-on-violations")
    gate.append("forge certify . --fail-under 75")
    return list(dict.fromkeys(gate))


def is_non_code_artifact(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    name = Path(normalized).name
    if name in _NON_CODE_NAMES:
        return True
    if normalized.startswith(_NON_CODE_PREFIXES):
        return True
    return name.endswith(_NON_CODE_SUFFIXES)


def preferred_full_test_command(project_root: Path) -> str:
    commands = detect_test_commands(project_root)
    return commands[0] if commands else "python -m pytest"


def command_for_selected_tests(project_root: Path, tests: list[str]) -> str:
    if not tests:
        return preferred_full_test_command(project_root)
    py_tests = [t for t in tests if t.endswith(_PY_TEST_SUFFIXES)]
    js_tests = [t for t in tests if t.endswith(_JS_TEST_SUFFIXES)]
    commands: list[str] = []
    if js_tests:
        commands.append(preferred_full_test_command(project_root))
    if py_tests:
        commands.append("python -m pytest " + " ".join(py_tests))
    return " && ".join(dict.fromkeys(commands)) or preferred_full_test_command(project_root)
