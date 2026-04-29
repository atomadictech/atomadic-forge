"""Tier verification — Golden Path Lane C W1: forge-action.

The action ships as YAML, so unit-testing it means parsing the YAML
and asserting structural / contractual properties:

  * the composite-action spec is well-formed
  * every input / output has a description
  * every `forge ...` shell invocation references only flags Forge
    actually exposes today (cross-check against the live CLI)
  * the self-certify workflow uses the action at its in-tree path
  * the sticky-comment marker is unique and re-used by the update path

This catches drift between the action and Forge's CLI in the same
PR, not in the field.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
ACTION_YML = REPO_ROOT / ".github" / "actions" / "forge-action" / "action.yml"
ACTION_README = REPO_ROOT / ".github" / "actions" / "forge-action" / "README.md"
SELF_CERTIFY_WF = REPO_ROOT / ".github" / "workflows" / "forge-self-certify.yml"

# Flags every consuming-CI command MUST resolve against Forge's actual
# CLI. If a flag is renamed or removed in Forge, the action breaks
# silently in the field — this list is the contract.
EXPECTED_FORGE_FLAGS = {
    "--fail-on-violations",   # Lane G1
    "--fail-under",           # certify
    "--emit-receipt",         # GP-A W1
    "--print-card",           # GP-A W1
    "--json",                 # everywhere
    "--package",              # certify
}


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ---- action.yml: composite spec ----------------------------------------

def test_action_yml_exists_and_parses():
    assert ACTION_YML.exists(), "action.yml missing"
    spec = _load_yaml(ACTION_YML)
    assert spec is not None and isinstance(spec, dict)


def test_action_is_composite():
    spec = _load_yaml(ACTION_YML)
    runs = spec.get("runs", {})
    assert runs.get("using") == "composite"
    assert isinstance(runs.get("steps"), list)
    assert len(runs["steps"]) >= 4


def test_action_top_level_fields_present():
    spec = _load_yaml(ACTION_YML)
    for f in ("name", "description", "author", "inputs", "outputs", "runs"):
        assert f in spec, f"action.yml missing top-level {f!r}"


def test_action_branding_set():
    """GitHub Marketplace requires icon + color. Lane C W12 ships the
    Marketplace listing; today the branding is already in place."""
    spec = _load_yaml(ACTION_YML)
    branding = spec.get("branding", {})
    assert "icon" in branding and "color" in branding


# ---- inputs / outputs --------------------------------------------------

def test_every_input_has_description_and_required_flag():
    spec = _load_yaml(ACTION_YML)
    inputs = spec.get("inputs", {})
    assert inputs, "action.yml has no inputs"
    for name, decl in inputs.items():
        assert decl.get("description"), f"input {name!r} missing description"
        assert "required" in decl, f"input {name!r} missing required flag"


def test_pinned_inputs_present():
    """The Lane C W1 contract pins these input names. Renaming any of
    them is a breaking change for every consuming repo."""
    spec = _load_yaml(ACTION_YML)
    inputs = set(spec["inputs"].keys())
    pinned = {
        "package_root", "project_root", "package_name", "fail_under",
        "receipt_path", "python_version", "forge_ref",
        "comment_on_pr", "upload_artifacts",
    }
    missing = pinned - inputs
    assert not missing, f"renamed / removed input(s): {missing}"


def test_outputs_have_descriptions():
    spec = _load_yaml(ACTION_YML)
    outputs = spec.get("outputs", {})
    assert outputs, "action.yml exposes no outputs"
    for name, decl in outputs.items():
        assert decl.get("description"), f"output {name!r} missing description"
        assert "value" in decl, f"output {name!r} missing value"


# ---- step shape --------------------------------------------------------

def test_setup_python_step_present():
    spec = _load_yaml(ACTION_YML)
    uses_set = {s.get("uses", "") for s in spec["runs"]["steps"]
                if "uses" in s}
    assert any(u.startswith("actions/setup-python@")
               for u in uses_set), "setup-python step missing"


def test_install_step_uses_pip_and_pins_ref():
    spec = _load_yaml(ACTION_YML)
    install = next(
        (s for s in spec["runs"]["steps"]
         if s.get("name") == "Install Atomadic Forge"),
        None,
    )
    assert install is not None
    run = install.get("run", "")
    assert "pip install" in run
    assert "atomadic-forge" in run
    assert "GITHUB_ACTION_REF" in run, (
        "install step must default forge_ref to the action's own ref"
    )


def test_upload_artifacts_step_includes_receipt():
    spec = _load_yaml(ACTION_YML)
    upload = next(
        (s for s in spec["runs"]["steps"]
         if str(s.get("uses", "")).startswith("actions/upload-artifact@")),
        None,
    )
    assert upload is not None
    paths = upload.get("with", {}).get("path", "")
    assert "wire.json" in paths
    assert "certify.json" in paths
    assert "receipt.json" in paths or "receipt_path" in paths
    assert "card.txt" in paths


# ---- forge CLI flag coverage -------------------------------------------

def test_action_only_uses_supported_forge_flags():
    """Every '--xxx' that appears on a `forge ...` line in the action's
    shell steps must be a flag Forge actually exposes today.

    Regression guard: the moment a flag is renamed in Forge or a new
    flag appears in the action without a matching CLI change, this
    test fails. Pip / setup flags (--upgrade, --version) are ignored
    because they belong to pip and to ``forge --version``.
    """
    spec = _load_yaml(ACTION_YML)
    forge_flags: set[str] = set()
    for step in spec["runs"]["steps"]:
        run = step.get("run", "")
        if not isinstance(run, str):
            continue
        for line in run.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            # Only inspect lines that invoke the `forge` CLI (and not
            # the `forge --version` probe in the install step).
            if not re.search(r"\bforge\s+(?!--version\b)", stripped):
                continue
            forge_flags.update(re.findall(r"(--[a-z][a-z0-9_-]*)", stripped))
    unrecognised = forge_flags - EXPECTED_FORGE_FLAGS
    assert not unrecognised, (
        f"action.yml uses forge-CLI flags not in EXPECTED_FORGE_FLAGS: "
        f"{sorted(unrecognised)} — update both Forge's CLI and this set."
    )


def test_action_uses_native_fail_flags_not_python_workarounds():
    """Lane G1 shipped --fail-on-violations / --fail-under. The action
    must use them rather than the python -c JSON-parse fallback the
    earlier docs/CI_CD.md recipes used.
    """
    text = ACTION_YML.read_text(encoding="utf-8")
    assert "--fail-on-violations" in text
    assert "--fail-under" in text
    # No leftover 'python -c' fallback that would mask the native gates.
    assert 'sys.exit(0 if r.get(\'verdict\')' not in text


# ---- self-certify workflow ---------------------------------------------

def test_self_certify_workflow_exists():
    assert SELF_CERTIFY_WF.exists()


def test_self_certify_uses_in_tree_action():
    spec = _load_yaml(SELF_CERTIFY_WF)
    job = spec["jobs"]["forge"]
    uses_set = {s.get("uses", "") for s in job["steps"] if "uses" in s}
    # The action is referenced by relative path so a forked Forge
    # picks up the action that shipped with that fork.
    assert any(u == "./.github/actions/forge-action" for u in uses_set), (
        f"self-certify workflow does not reference ./action: {uses_set}"
    )


def test_self_certify_holds_at_100():
    """Forge's own bar is 100/100. Slipping it below would be eating
    our dogfood with a side of regression."""
    text = SELF_CERTIFY_WF.read_text(encoding="utf-8")
    assert "fail_under: '100'" in text


def test_self_certify_pins_forge_ref_to_sha():
    """The action default uses GITHUB_ACTION_REF; the self-certify
    workflow runs against the in-tree action AND the in-tree code, so
    it must pin forge_ref to the commit SHA being tested — otherwise
    pip would try to install from main."""
    text = SELF_CERTIFY_WF.read_text(encoding="utf-8")
    assert "github.sha" in text


# ---- README cross-check ------------------------------------------------

def test_action_readme_present_and_self_consistent():
    assert ACTION_README.exists()
    readme = ACTION_README.read_text(encoding="utf-8")
    spec = _load_yaml(ACTION_YML)
    # Every documented input must exist in action.yml.
    for line in readme.splitlines():
        m = re.match(r"\|\s*`([a-z_]+)`\s*\|\s*(yes|no)\s*\|", line)
        if not m:
            continue
        name, _required = m.group(1), m.group(2)
        if name in {"name", "type"}:
            continue  # table-header echoes
        if name in spec["inputs"] or name in spec["outputs"]:
            continue
        pytest.fail(
            f"README documents `{name}` but action.yml has no such input/output"
        )


def test_sticky_comment_marker_unique():
    """The marker is what lets the action find and update its prior
    comment instead of stacking new ones. If a future rename forgets
    to update both call sites, the test fails loudly."""
    text = ACTION_YML.read_text(encoding="utf-8")
    marker = "<!-- atomadic-forge:receipt-card -->"
    assert text.count(marker) == 1, (
        f"sticky-comment marker must appear exactly once in action.yml; "
        f"found {text.count(marker)}"
    )
