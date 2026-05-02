"""Tier a1 — pure CycloneDX 1.5 SBOM emitter.

Golden Path Lane G G3. Emits an ``atomadic-forge.sbom/v1`` document
wrapping a CycloneDX 1.5 JSON SBOM derived from a project's
``pyproject.toml`` ``[project].dependencies`` +
``[project.optional-dependencies].dev``.

Pure: no network, no file writes. Returns a dict ready for
``json.dumps``.
"""
from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path
from typing import Any

from .. import __version__

SCHEMA_VERSION_SBOM_V1 = "atomadic-forge.sbom/v1"
_CYCLONEDX_FORMAT = "CycloneDX"
_CYCLONEDX_SPEC_VERSION = "1.5"


def _now_utc_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalise_name(raw: str) -> str:
    """PEP 503 canonical name: lowercase, dashes/underscores/dots -> hyphens."""
    return re.sub(r"[-_.]+", "-", raw).lower()


def _parse_dep(dep: str) -> tuple[str, str]:
    """Return (canonical_name, version_spec) from a PEP 508 string."""
    dep = dep.strip()
    name_match = re.match(r"^([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)", dep)
    name = _normalise_name(name_match.group(1)) if name_match else dep.lower()
    ver_match = re.search(r"[><=!~]{1,3}([0-9][^,;\s\]]*)", dep)
    ver = ver_match.group(1).rstrip(",") if ver_match else "unspecified"
    return name, ver


def _read_pyproject_deps(project_root: Path) -> list[str]:
    """Return combined runtime + dev deps from ``pyproject.toml``."""
    pyproject = project_root / "pyproject.toml"
    if not pyproject.exists():
        return []
    try:
        text = pyproject.read_text(encoding="utf-8")
    except OSError:
        return []

    try:
        import tomllib  # noqa: PLC0415
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]  # noqa: PLC0415
        except ImportError:
            tomllib = None  # type: ignore[assignment]

    if tomllib is not None:
        try:
            data = tomllib.loads(text)
            project = data.get("project", {})
            deps: list[str] = list(project.get("dependencies") or [])
            opt = project.get("optional-dependencies") or {}
            deps.extend(opt.get("dev") or [])
            return deps
        except Exception:  # noqa: BLE001
            pass

    return _regex_extract_deps(text)


def _regex_extract_deps(text: str) -> list[str]:
    """Minimal TOML-free dep extraction."""
    deps: list[str] = []
    in_section = False
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^dependencies\s*=\s*\[", stripped):
            in_section = True
            inner = re.search(r"\[([^\]]*)\]", stripped)
            if inner:
                for tok in inner.group(1).split(","):
                    dep = tok.strip().strip("\"'")
                    if dep:
                        deps.append(dep)
                in_section = False
            continue
        if in_section:
            if stripped.startswith("]"):
                in_section = False
                continue
            dep = stripped.strip(",").strip("\"'").strip()
            if dep and not dep.startswith("#"):
                deps.append(dep)
    return deps


def _dep_to_component(dep: str) -> dict[str, Any]:
    name, version = _parse_dep(dep)
    return {
        "type": "library",
        "name": name,
        "version": version,
        "purl": f"pkg:pypi/{name}@{version}",
    }


def emit_sbom(
    *,
    project_root: Path | str,
    scout_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return an ``atomadic-forge.sbom/v1`` dict wrapping CycloneDX 1.5 JSON.

    Pulls deps from ``pyproject.toml`` ``[project].dependencies`` +
    ``[project.optional-dependencies].dev``.
    """
    project_root = Path(project_root).resolve()
    raw_deps = _read_pyproject_deps(project_root)
    components = [_dep_to_component(d) for d in raw_deps if d.strip()]

    now = _now_utc_iso()
    cyclonedx: dict[str, Any] = {
        "bomFormat": _CYCLONEDX_FORMAT,
        "specVersion": _CYCLONEDX_SPEC_VERSION,
        "version": 1,
        "metadata": {
            "timestamp": now,
            "tools": [
                {
                    "vendor": "Atomadic",
                    "name": "atomadic-forge",
                    "version": __version__,
                }
            ],
        },
        "components": components,
    }

    sbom: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION_SBOM_V1,
        "project_root": str(project_root),
        "generated_at_utc": now,
        "sbom": cyclonedx,
    }
    if scout_report is not None:
        sbom["scout_summary"] = {
            "symbol_count": int(scout_report.get("symbol_count", 0)),
            "primary_language": str(scout_report.get("primary_language", "python")),
        }
    return sbom
