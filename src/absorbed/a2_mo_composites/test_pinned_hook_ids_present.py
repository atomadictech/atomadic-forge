"""Tier verification — Golden Path Lane C W2: .pre-commit-hooks.yaml.

The pre-commit Hook spec is YAML. Tests parse the manifest and pin
the contract: every hook entry has the required fields, references
only Forge-native flags, and the hook IDs match the docs/CI_CD.md
recipe so consuming repos copy-paste-clean.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS_YAML = REPO_ROOT / ".pre-commit-hooks.yaml"
CI_CD_DOC = REPO_ROOT / "docs" / "CI_CD.md"

# Lane C W2 contract: these hook IDs are part of the published API.
# Renaming any of them is a breaking change for every consuming repo.
PINNED_HOOK_IDS: set[str] = {
    "forge-wire",
    "forge-certify",
    "forge-enforce-check",
}

# Same flag-coverage guard as the GitHub Action: every '--xxx' on a
# `forge ...` line must be in this set or the test fails before the
# hook ships broken.
EXPECTED_FORGE_FLAGS: set[str] = {
    "--fail-on-violations",
    "--fail-under",
    "--apply",
    "--json",
    "--package",
    "--print-card",
    "--emit-receipt",
    "--suggest-repairs",
}


def _load_hooks() -> list[dict]:
    return yaml.safe_load(HOOKS_YAML.read_text(encoding="utf-8"))


# ---- structural ---------------------------------------------------------

def test_hooks_yaml_exists_and_parses():
    assert HOOKS_YAML.exists()
    data = _load_hooks()
    assert isinstance(data, list) and len(data) >= 3


def test_every_hook_has_required_fields():
    for hook in _load_hooks():
        assert "id" in hook, f"hook missing id: {hook}"
        assert "name" in hook, f"hook missing name: {hook}"
        assert "description" in hook, f"hook missing description: {hook}"
        assert "entry" in hook, f"hook missing entry: {hook}"
        assert "language" in hook, f"hook missing language: {hook}"
        assert "additional_dependencies" in hook, (
            f"hook {hook.get('id')!r} missing additional_dependencies — "
            "consuming repos won't auto-install Forge in the venv"
        )


def test_pinned_hook_ids_present():
    actual = {h["id"] for h in _load_hooks()}
    missing = PINNED_HOOK_IDS - actual
    assert not missing, (
        f"hook IDs renamed/removed: {missing} (Lane C W2 contract drift)"
    )


def test_every_hook_installs_atomadic_forge():
    for hook in _load_hooks():
        deps = hook.get("additional_dependencies", [])
        assert any("atomadic-forge" in d for d in deps), (
            f"hook {hook['id']!r} does not install atomadic-forge — "
            "the venv would have no `forge` binary"
        )


# ---- flag-coverage guard -----------------------------------------------

def test_hooks_only_use_supported_forge_flags():
    """Mirror of the GitHub Action's flag-coverage test. The moment a
    flag is renamed in Forge or a new flag appears in the hook without
    a matching CLI change, this test fails.
    """
    flags: set[str] = set()
    for hook in _load_hooks():
        for arg in hook.get("args", []) or []:
            if isinstance(arg, str) and arg.startswith("--"):
                flags.add(arg.split("=", 1)[0])
    unrecognised = flags - EXPECTED_FORGE_FLAGS
    assert not unrecognised, (
        f"pre-commit hooks reference forge flags not in EXPECTED set: "
        f"{sorted(unrecognised)}"
    )


def test_wire_hook_has_native_fail_flag():
    by_id = {h["id"]: h for h in _load_hooks()}
    wire_args = by_id["forge-wire"].get("args", [])
    assert "--fail-on-violations" in wire_args


def test_certify_hook_has_native_fail_under():
    by_id = {h["id"]: h for h in _load_hooks()}
    certify_args = by_id["forge-certify"].get("args", [])
    assert "--fail-under" in certify_args
    # Threshold should be a numeric string between 0 and 100.
    idx = certify_args.index("--fail-under") + 1
    threshold = int(certify_args[idx])
    assert 0 <= threshold <= 100


def test_enforce_check_is_dry_run_not_apply():
    """forge-enforce-check is a dry-run advisory hook; it must NOT
    pass --apply (that would mutate the user's working tree mid-commit).
    Surfacing the planned moves is the value-add."""
    by_id = {h["id"]: h for h in _load_hooks()}
    enforce_args = by_id["forge-enforce-check"].get("args", []) or []
    assert "--apply" not in enforce_args, (
        "forge-enforce-check must not auto-mutate the working tree"
    )


# ---- stages -------------------------------------------------------------

def test_certify_stages_pre_push_only():
    """Certify is heavier than wire. Recommend pre-push so the per-
    commit loop stays fast. Wire stays on pre-commit + pre-push."""
    by_id = {h["id"]: h for h in _load_hooks()}
    certify_stages = by_id["forge-certify"].get("stages", [])
    assert "pre-push" in certify_stages
    # Should NOT include pre-commit (too slow to fire on every commit).
    assert "pre-commit" not in certify_stages


def test_wire_runs_on_both_commit_and_push():
    by_id = {h["id"]: h for h in _load_hooks()}
    wire_stages = by_id["forge-wire"].get("stages", [])
    assert "pre-commit" in wire_stages
    assert "pre-push" in wire_stages


def test_enforce_check_is_manual_only():
    """forge-enforce-check is opt-in via `pre-commit run --hook-stage manual`.
    Not on pre-commit / pre-push — too noisy for the default loop."""
    by_id = {h["id"]: h for h in _load_hooks()}
    stages = by_id["forge-enforce-check"].get("stages", [])
    assert stages == ["manual"]


# ---- docs/CI_CD.md cross-consistency -----------------------------------

def test_ci_cd_doc_mentions_pre_commit_hooks_yaml():
    """The CI/CD guide tells users about this manifest. If the doc
    drops the reference, that's a documentation regression."""
    if not CI_CD_DOC.exists():
        pytest.skip("docs/CI_CD.md not present")
    text = CI_CD_DOC.read_text(encoding="utf-8")
    assert ".pre-commit-hooks.yaml" in text


def test_ci_cd_doc_uses_native_fail_flags():
    """Mirror of the action test: the documented hook args must reference
    --fail-on-violations / --fail-under, not the python -c fallback."""
    if not CI_CD_DOC.exists():
        pytest.skip("docs/CI_CD.md not present")
    text = CI_CD_DOC.read_text(encoding="utf-8")
    assert "--fail-on-violations" in text
    assert "--fail-under" in text
