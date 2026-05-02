"""Tier a1 — pure unified-diff risk scorer.

Codex's 'Copilot's Copilot' primitive #3:

  > score_patch({diff}) — returns architecture risk, test risk,
  > public API risk, release risk, 'needs human review?' boolean,
  > suggested validation commands. Turns Forge into a PR reviewer
  > before the PR exists.

Pure: parses a unified-diff string, classifies per-file changes,
returns a structured risk report. Heuristic — false positives are
expected; the value is the structured prompt for the agent to
think about before applying the diff.
"""
from __future__ import annotations

import re
from typing import TypedDict

SCHEMA_VERSION_PATCH_SCORE_V1 = "atomadic-forge.patch_score/v1"


_FILE_HEADER_RE = re.compile(r"^\+\+\+ b/(.+?)(?:\t|\s|$)", re.MULTILINE)
_TIER_NAMES = (
    "a0_qk_constants", "a1_at_functions", "a2_mo_composites",
    "a3_og_features", "a4_sy_orchestration",
)
_PUBLIC_API_PATHS = ("__init__.py",)
_RELEASE_FILES = (
    "pyproject.toml", "setup.py", "setup.cfg", "package.json",
    "Cargo.toml", "version.py", "VERSION", "_version.py",
    "CHANGELOG.md", "LICENSE",
)
_FORBIDDEN_BY_TIER: dict[str, tuple[str, ...]] = {
    "a0_qk_constants": (
        "a1_at_functions", "a2_mo_composites",
        "a3_og_features", "a4_sy_orchestration",
    ),
    "a1_at_functions": (
        "a2_mo_composites", "a3_og_features", "a4_sy_orchestration",
    ),
    "a2_mo_composites": ("a3_og_features", "a4_sy_orchestration"),
    "a3_og_features":   ("a4_sy_orchestration",),
    "a4_sy_orchestration": (),
}


class PatchFileScore(TypedDict, total=False):
    path: str
    detected_tier: str | None
    added_lines: int
    removed_lines: int
    architectural_risk: bool
    public_api_risk: bool
    release_risk: bool
    notes: list[str]


class PatchScore(TypedDict, total=False):
    schema_version: str
    file_count: int
    total_added: int
    total_removed: int
    architectural_risk: bool
    test_risk: bool
    public_api_risk: bool
    release_risk: bool
    needs_human_review: bool
    files: list[PatchFileScore]
    suggested_validation_commands: list[str]
    notes: list[str]


def _split_diff_per_file(diff: str) -> list[tuple[str, str]]:
    """Return [(path, file_diff_text), ...] for a unified diff."""
    chunks: list[tuple[str, str]] = []
    current_path: str | None = None
    current: list[str] = []
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            # Flush prior chunk
            if current_path is not None and current:
                chunks.append((current_path, "\n".join(current)))
            current_path = line[len("+++ b/"):].split("\t", 1)[0].strip()
            current = []
        else:
            current.append(line)
    if current_path is not None and current:
        chunks.append((current_path, "\n".join(current)))
    return chunks


def _detect_tier(path: str) -> str | None:
    for part in path.split("/"):
        if part in _TIER_NAMES:
            return part
    return None


def _check_added_imports_against_tier(
    path: str, tier: str | None, diff_text: str,
) -> list[str]:
    """Look at '+' lines for upward imports against the file's tier."""
    if not tier:
        return []
    forbidden = _FORBIDDEN_BY_TIER.get(tier, ())
    if not forbidden:
        return []
    issues: list[str] = []
    for raw in diff_text.splitlines():
        if not raw.startswith("+") or raw.startswith("+++"):
            continue
        body = raw[1:].lstrip()
        if not body.startswith(("import ", "from ")):
            continue
        for f in forbidden:
            if f in body:
                issues.append(
                    f"new import in {path} references forbidden tier "
                    f"{f!r}: {body[:120]}"
                )
                break
    return issues


def _file_score(path: str, diff_text: str) -> PatchFileScore:
    added = sum(1 for line in diff_text.splitlines()
                 if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff_text.splitlines()
                   if line.startswith("-") and not line.startswith("---"))
    tier = _detect_tier(path)
    notes: list[str] = []
    arch_risk = False
    api_risk = False
    rel_risk = False

    upward = _check_added_imports_against_tier(path, tier, diff_text)
    if upward:
        arch_risk = True
        notes.extend(upward)

    if path.endswith(_PUBLIC_API_PATHS):
        api_risk = True
        notes.append(
            f"{path} is a public-export surface; an unintended "
            "deletion can break downstream callers"
        )

    base = path.split("/")[-1]
    if base in _RELEASE_FILES or path.endswith(_RELEASE_FILES):
        rel_risk = True
        notes.append(
            f"{path} is a release-control file; review version bump "
            "+ changelog impact before merging"
        )

    return PatchFileScore(
        path=path,
        detected_tier=tier,
        added_lines=added,
        removed_lines=removed,
        architectural_risk=arch_risk,
        public_api_risk=api_risk,
        release_risk=rel_risk,
        notes=notes,
    )


def score_patch(diff: str, *, project_root: object | None = None) -> PatchScore:
    """Score a unified-diff string. Returns the patch_score/v1 shape.

    Empty or unparseable diffs return a low-risk report with a note
    instead of raising — the agent should never see a traceback when
    asking 'is this safe?'.

    Codex-6: when ``project_root`` is provided AND that project has a
    [tool.forge.agent] policy with protected_files, any diff touching
    a protected file is flagged as ``needs_human_review``.
    """
    if not diff or not diff.strip():
        return PatchScore(
            schema_version=SCHEMA_VERSION_PATCH_SCORE_V1,
            file_count=0, total_added=0, total_removed=0,
            architectural_risk=False, test_risk=False,
            public_api_risk=False, release_risk=False,
            needs_human_review=False, files=[],
            suggested_validation_commands=[],
            notes=["empty diff — nothing to score"],
        )

    chunks = _split_diff_per_file(diff)
    files = [_file_score(p, txt) for p, txt in chunks]

    arch_risk = any(f["architectural_risk"] for f in files)
    api_risk = any(f["public_api_risk"] for f in files)
    rel_risk = any(f["release_risk"] for f in files)

    src_paths = [f for f in files
                 if not f["path"].startswith(("tests/", "test/"))
                 and not f["path"].endswith(("_test.py",))]
    test_paths = [f for f in files
                   if f["path"].startswith(("tests/", "test/"))
                   or f["path"].endswith(("_test.py",))]
    test_risk = bool(src_paths) and not test_paths

    notes: list[str] = []
    if test_risk:
        notes.append(
            "code changed without tests touched — add coverage or "
            "explicitly justify why existing tests are sufficient"
        )
    if not chunks:
        notes.append(
            "diff parsed but no '+++ b/<path>' headers found — "
            "unified-diff format expected"
        )

    # Codex-6: respect [tool.forge.agent] protected_files when a
    # project_root is provided. Lazy import to avoid a circular path.
    protected_hits: list[str] = []
    if project_root is not None:
        try:
            from pathlib import Path as _Path

            from .policy_loader import file_is_protected, load_policy
            policy = load_policy(_Path(str(project_root)))
            for f in files:
                if file_is_protected(f["path"], policy):
                    protected_hits.append(f["path"])
                    f.setdefault("notes", []).append(
                        "policy: file listed in protected_files — needs review"
                    )
        except Exception:  # noqa: BLE001
            pass

    needs_review = arch_risk or api_risk or rel_risk or bool(protected_hits) or (
        sum(f["added_lines"] for f in files) > 200
    )
    if protected_hits:
        notes.append(
            f"diff touches {len(protected_hits)} file(s) listed in "
            "[tool.forge.agent] protected_files — needs_human_review=True"
        )
    if needs_review and "review" not in " ".join(notes):
        notes.append(
            "needs_human_review=True because of architectural / "
            "public-API / release / large-patch risk — do NOT auto-merge"
        )

    return PatchScore(
        schema_version=SCHEMA_VERSION_PATCH_SCORE_V1,
        file_count=len(files),
        total_added=sum(f["added_lines"] for f in files),
        total_removed=sum(f["removed_lines"] for f in files),
        architectural_risk=arch_risk,
        test_risk=test_risk,
        public_api_risk=api_risk,
        release_risk=rel_risk,
        needs_human_review=needs_review,
        files=files,
        suggested_validation_commands=[
            "forge wire src --fail-on-violations",
            "python -m pytest",
            "forge certify . --fail-under 75",
        ],
        notes=notes,
    )
