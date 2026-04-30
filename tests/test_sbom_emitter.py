"""Tests for a1/sbom_emitter.py — CycloneDX 1.5 SBOM emission.

Covers:
  - schema_version is 'atomadic-forge.sbom/v1'
  - bomFormat is 'CycloneDX', specVersion is '1.5'
  - components parsed from pyproject.toml (runtime + dev)
  - purl format: pkg:pypi/<name>@<version>
  - missing pyproject.toml -> empty components, no exception
  - scout_report summary included when provided
  - name normalisation (underscores -> hyphens)
  - JSON serialisability
"""
from __future__ import annotations

import json
from pathlib import Path

from atomadic_forge.a1_at_functions.sbom_emitter import (
    SCHEMA_VERSION_SBOM_V1,
    emit_sbom,
)

_PYPROJECT_MINIMAL = """
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "my-pkg"
version = "1.0.0"
dependencies = [
    "requests>=2.28,<3",
    "click>=8,<9",
]

[project.optional-dependencies]
dev = [
    "pytest>=7",
]
"""

_PYPROJECT_UNDERSCORE = """
[project]
name = "my_pkg"
version = "1.0.0"
dependencies = [
    "my_dep>=1.0",
]
"""


def _write_pyproject(tmp_path: Path, content: str) -> Path:
    (tmp_path / "pyproject.toml").write_text(content, encoding="utf-8")
    return tmp_path


def test_schema_version(tmp_path):
    _write_pyproject(tmp_path, _PYPROJECT_MINIMAL)
    sbom = emit_sbom(project_root=tmp_path)
    assert sbom["schema_version"] == SCHEMA_VERSION_SBOM_V1


def test_cyclonedx_format_and_spec_version(tmp_path):
    _write_pyproject(tmp_path, _PYPROJECT_MINIMAL)
    bom = emit_sbom(project_root=tmp_path)["sbom"]
    assert bom["bomFormat"] == "CycloneDX"
    assert bom["specVersion"] == "1.5"
    assert bom["version"] == 1


def test_metadata_timestamp_present(tmp_path):
    _write_pyproject(tmp_path, _PYPROJECT_MINIMAL)
    ts = emit_sbom(project_root=tmp_path)["sbom"]["metadata"]["timestamp"]
    assert ts.endswith("Z")


def test_metadata_tools_present(tmp_path):
    _write_pyproject(tmp_path, _PYPROJECT_MINIMAL)
    tools = emit_sbom(project_root=tmp_path)["sbom"]["metadata"]["tools"]
    assert any(t["name"] == "atomadic-forge" for t in tools)


def test_components_from_runtime_deps(tmp_path):
    _write_pyproject(tmp_path, _PYPROJECT_MINIMAL)
    names = [c["name"] for c in emit_sbom(project_root=tmp_path)["sbom"]["components"]]
    assert "requests" in names
    assert "click" in names


def test_components_include_dev_deps(tmp_path):
    _write_pyproject(tmp_path, _PYPROJECT_MINIMAL)
    names = [c["name"] for c in emit_sbom(project_root=tmp_path)["sbom"]["components"]]
    assert "pytest" in names


def test_component_fields(tmp_path):
    _write_pyproject(tmp_path, _PYPROJECT_MINIMAL)
    for comp in emit_sbom(project_root=tmp_path)["sbom"]["components"]:
        assert comp["type"] == "library"
        assert comp["name"]
        assert comp["version"]
        assert comp["purl"].startswith("pkg:pypi/")


def test_purl_format(tmp_path):
    _write_pyproject(tmp_path, _PYPROJECT_MINIMAL)
    comps = emit_sbom(project_root=tmp_path)["sbom"]["components"]
    req = next(c for c in comps if c["name"] == "requests")
    assert req["purl"] == f"pkg:pypi/requests@{req['version']}"


def test_name_normalisation(tmp_path):
    _write_pyproject(tmp_path, _PYPROJECT_UNDERSCORE)
    names = [c["name"] for c in emit_sbom(project_root=tmp_path)["sbom"]["components"]]
    assert "my-dep" in names
    assert "my_dep" not in names


def test_missing_pyproject_returns_empty_components(tmp_path):
    sbom = emit_sbom(project_root=tmp_path)
    assert sbom["sbom"]["components"] == []
    assert sbom["schema_version"] == SCHEMA_VERSION_SBOM_V1


def test_scout_summary_included_when_provided(tmp_path):
    _write_pyproject(tmp_path, _PYPROJECT_MINIMAL)
    scout = {"symbol_count": 42, "primary_language": "python"}
    sbom = emit_sbom(project_root=tmp_path, scout_report=scout)
    assert sbom["scout_summary"]["symbol_count"] == 42


def test_scout_summary_absent_when_not_provided(tmp_path):
    _write_pyproject(tmp_path, _PYPROJECT_MINIMAL)
    assert "scout_summary" not in emit_sbom(project_root=tmp_path)


def test_sbom_is_json_serialisable(tmp_path):
    _write_pyproject(tmp_path, _PYPROJECT_MINIMAL)
    sbom = emit_sbom(project_root=tmp_path)
    reloaded = json.loads(json.dumps(sbom))
    assert reloaded["schema_version"] == SCHEMA_VERSION_SBOM_V1
