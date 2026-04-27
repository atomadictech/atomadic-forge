"""End-to-end test of the forge_pipeline run_auto path."""

from pathlib import Path

import pytest

from atomadic_forge.a3_og_features.forge_pipeline import (
    run_auto, run_cherry, run_finalize, run_recon,
)


def test_recon_classifies_sample_repo(sample_repo):
    report = run_recon(sample_repo)
    assert report["python_file_count"] == 2
    assert report["symbol_count"] >= 5
    # Counter has self.n = 0 → must promote to a2.
    by_qual = {s["qualname"]: s for s in report["symbols"]}
    assert by_qual["Counter"]["tier_guess"] == "a2_mo_composites"


def test_cherry_pick_all(sample_repo):
    run_recon(sample_repo)
    manifest = run_cherry(sample_repo, pick_all=True)
    assert len(manifest["items"]) >= 5


def test_auto_dry_run_does_not_write(tmp_path, sample_repo):
    output = tmp_path / "out"
    report = run_auto(target=sample_repo, output=output, apply=False)
    assert report["applied"] is False
    # Nothing should be written to output beyond the directory itself.
    assert not (output / "STATUS.md").exists()


def test_auto_apply_writes_tier_tree(tmp_path, sample_repo):
    output = tmp_path / "out"
    output.mkdir()
    report = run_auto(target=sample_repo, output=output, apply=True,
                      package="absorbed_demo")
    assert report["applied"] is True
    pkg_root = output / "src" / "absorbed_demo"
    assert pkg_root.exists()
    assert (pkg_root / "a1_at_functions").exists()
    assert (output / "STATUS.md").exists()
    # Status file must explicitly call out it's bootstrap material.
    status = (output / "STATUS.md").read_text(encoding="utf-8")
    assert "bootstrapped material" in status.lower()


def test_finalize_on_conflict_rename(tmp_path, sample_repo):
    output = tmp_path / "out"
    output.mkdir()
    # Build a manifest that picks the same symbol twice (synthetic).
    cherry = {
        "schema_version": "atomadic-forge.cherry/v1",
        "source_repo": str(sample_repo),
        "items": [
            {"qualname": "add", "target_tier": "a1_at_functions",
             "confidence": 0.7, "reasons": []},
            {"qualname": "add", "target_tier": "a1_at_functions",
             "confidence": 0.7, "reasons": []},
        ],
    }
    run_recon(sample_repo)
    report = run_finalize(target=sample_repo, output=output, apply=True,
                           package="dupe_demo", cherry_manifest=cherry,
                           on_conflict="rename")
    files = list((output / "src" / "dupe_demo" / "a1_at_functions").glob("*.py"))
    # __init__.py + add.py + add__alt.py
    assert any(f.name == "add__alt.py" for f in files)


def test_finalize_on_conflict_fail(tmp_path, sample_repo):
    output = tmp_path / "out"
    output.mkdir()
    cherry = {
        "schema_version": "atomadic-forge.cherry/v1",
        "source_repo": str(sample_repo),
        "items": [
            {"qualname": "add", "target_tier": "a1_at_functions",
             "confidence": 0.7, "reasons": []},
            {"qualname": "add", "target_tier": "a1_at_functions",
             "confidence": 0.7, "reasons": []},
        ],
    }
    run_recon(sample_repo)
    with pytest.raises(ValueError):
        run_finalize(target=sample_repo, output=output, apply=True,
                      package="fail_demo", cherry_manifest=cherry,
                      on_conflict="fail")
