"""Tier a1 — pure readers for .atomadic-forge lineage.jsonl + manifests.

Audit pain point (Lane D1): every ``--apply`` writes to lineage.jsonl,
but Forge ships no verb to query that file. Auditors and developers
have to ``cat`` and ``jq`` it. This module gives the CLI a clean
interface to surface what's there.

Pure: read-only, returns structured dicts. Side-effecting verbs
(``trend``, ``replay``) require lineage-shape extension and live in
their own lane; this module supports the inspection surface today.
"""
from __future__ import annotations

import json
from pathlib import Path

_DEFAULT_DIRNAME = ".atomadic-forge"
_LINEAGE_FILE = "lineage.jsonl"


def lineage_path(project_root: Path, *, dirname: str = _DEFAULT_DIRNAME) -> Path:
    """Return the absolute path of the lineage log under ``project_root``."""
    return Path(project_root).resolve() / dirname / _LINEAGE_FILE


def read_lineage(
    project_root: Path,
    *,
    dirname: str = _DEFAULT_DIRNAME,
    last: int | None = None,
) -> list[dict]:
    """Return lineage entries newest-last.

    ``last`` (optional): when set, return only the most recent N entries.
    Malformed lines are skipped silently — the lineage log is append-only
    and a corrupt line should not break inspection of the rest.
    """
    log = lineage_path(project_root, dirname=dirname)
    if not log.exists():
        return []
    entries: list[dict] = []
    for line in log.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    if last is not None and last >= 0:
        entries = entries[-last:]
    return entries


def list_artifacts(
    project_root: Path,
    *,
    dirname: str = _DEFAULT_DIRNAME,
) -> list[dict]:
    """Return one summary entry per distinct artifact name.

    Each summary names the artifact, its run count, the latest write
    timestamp, and the relative path. Sorted by latest write descending.
    """
    by_name: dict[str, dict] = {}
    for entry in read_lineage(project_root, dirname=dirname):
        name = entry.get("artifact", "")
        if not name:
            continue
        existing = by_name.get(name)
        if existing is None:
            by_name[name] = {
                "artifact": name,
                "run_count": 1,
                "latest_ts_utc": entry.get("ts_utc", ""),
                "path": entry.get("path", ""),
            }
        else:
            existing["run_count"] += 1
            ts = entry.get("ts_utc", "")
            if ts > existing["latest_ts_utc"]:
                existing["latest_ts_utc"] = ts
                existing["path"] = entry.get("path", "")
    return sorted(by_name.values(),
                  key=lambda d: d["latest_ts_utc"], reverse=True)


def load_manifest(
    project_root: Path,
    artifact: str,
    *,
    dirname: str = _DEFAULT_DIRNAME,
) -> dict | None:
    """Return the saved JSON manifest for ``artifact`` (e.g. 'scout',
    'cherry', 'wire', 'certify'). Returns None when no such manifest
    has been written.
    """
    candidate = Path(project_root).resolve() / dirname / f"{artifact}.json"
    if not candidate.exists():
        return None
    try:
        data = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None
