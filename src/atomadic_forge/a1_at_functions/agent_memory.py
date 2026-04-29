"""Tier a1 — agent memory queries (Codex #5).

Codex's prescription:

  > Make .atomadic-forge/ a real agent memory substrate. Future
  > agents can ask: why_did_this_change({file}),
  > what_failed_last_time({area}). That's gold.

Pure: queries lineage.jsonl + plan state files. No I/O beyond those
two read paths.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

from .lineage_reader import read_lineage


SCHEMA_VERSION_WHY_V1 = "atomadic-forge.why/v1"
SCHEMA_VERSION_WHAT_FAILED_V1 = "atomadic-forge.what_failed/v1"


class WhyDidThisChange(TypedDict, total=False):
    schema_version: str
    file: str
    related_lineage: list[dict]
    related_plan_events: list[dict]
    summary: str


class WhatFailedLastTime(TypedDict, total=False):
    schema_version: str
    area: str
    failures: list[dict]
    summary: str


def why_did_this_change(
    *,
    file: str,
    project_root: Path,
) -> WhyDidThisChange:
    """Return every lineage + plan event referencing ``file``.

    Heuristic: an entry 'references' the file when:
      * the entry's `path` field equals or contains the file path
      * the entry is a plan event whose card.write_scope contains it

    Pure: read-only lineage + plan-state walks.
    """
    project_root = Path(project_root).resolve()
    lineage = read_lineage(project_root)
    related_lineage = [
        entry for entry in lineage
        if entry.get("path", "") == file
        or file in entry.get("path", "")
    ]

    plan_events: list[dict] = []
    plans_dir = project_root / ".atomadic-forge" / "plans"
    if plans_dir.is_dir():
        import json
        for state_file in plans_dir.glob("*.state.json"):
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for ev in state.get("events", []):
                detail = ev.get("detail") or {}
                # Direct path match in detail (e.g. README write).
                if isinstance(detail.get("written"), str) \
                        and detail["written"] == file:
                    plan_events.append({**ev,
                                          "plan_id": state.get("plan_id")})
                    continue
                if file in str(detail):
                    plan_events.append({**ev,
                                          "plan_id": state.get("plan_id")})

    if related_lineage or plan_events:
        last_ts = ""
        for entry in related_lineage + plan_events:
            ts = entry.get("ts_utc", "")
            if ts > last_ts:
                last_ts = ts
        summary = (
            f"{file} appears in {len(related_lineage)} lineage entries "
            f"and {len(plan_events)} plan events; latest activity "
            f"{last_ts or '(unknown)'}."
        )
    else:
        summary = f"no recorded forge activity references {file}."

    return WhyDidThisChange(
        schema_version=SCHEMA_VERSION_WHY_V1,
        file=file,
        related_lineage=related_lineage,
        related_plan_events=plan_events,
        summary=summary,
    )


def what_failed_last_time(
    *,
    area: str,
    project_root: Path,
) -> WhatFailedLastTime:
    """Return plan events with status 'failed' or 'rolled_back' that
    relate to ``area`` (matched as a substring of card_id / detail).
    """
    project_root = Path(project_root).resolve()
    failures: list[dict] = []
    plans_dir = project_root / ".atomadic-forge" / "plans"
    if plans_dir.is_dir():
        import json
        for state_file in plans_dir.glob("*.state.json"):
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for ev in state.get("events", []):
                if ev.get("status") not in {"failed", "rolled_back"}:
                    continue
                blob = (ev.get("card_id", "") + " " +
                        str(ev.get("detail", "")))
                if not area or area.lower() in blob.lower():
                    failures.append({**ev,
                                       "plan_id": state.get("plan_id")})
    summary = (
        f"{len(failures)} prior failure(s) referencing area={area!r}."
        if failures
        else f"no prior failures recorded for area={area!r}."
    )
    return WhatFailedLastTime(
        schema_version=SCHEMA_VERSION_WHAT_FAILED_V1,
        area=area,
        failures=failures,
        summary=summary,
    )
