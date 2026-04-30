"""Tier a1 — append-only evolution log.

Every successful evolve / demo run appends a row to a shared
``.atomadic-forge/EVOLVE_LOG.md`` markdown table at the project root,
plus a JSONL line for machine consumption.  Forge documents its own
history so operators can see every artifact that has ever been produced.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any

_TABLE_HEADER = (
    "| When (UTC) | Preset / Intent | Package | LLM | Rounds | Trajectory | Final | Verdict |\n"
    "|------------|-----------------|---------|-----|-------:|------------|------:|---------|"
)
_LOG_FILENAME = "EVOLVE_LOG.md"
_JSONL_FILENAME = "evolve_log.jsonl"


def _ensure_log_dir(project_root: Path) -> Path:
    d = project_root / ".atomadic-forge"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _intent_short(intent: str, max_len: int = 70) -> str:
    one_line = " ".join(intent.split())
    if len(one_line) <= max_len:
        return one_line
    return one_line[:max_len - 1] + "…"


def append_evolve_run(
    *,
    project_root: Path,
    package: str,
    intent: str,
    llm_name: str,
    rounds_completed: int,
    score_trajectory: list[float],
    final_score: float,
    converged: bool,
    halt_reason: str = "",
    extra: dict[str, Any] | None = None,
) -> Path:
    """Append a row to the evolve log markdown + jsonl."""
    log_dir = _ensure_log_dir(project_root)
    md_path = log_dir / _LOG_FILENAME
    jsonl_path = log_dir / _JSONL_FILENAME
    ts = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    arc = " → ".join(f"{s:.0f}" for s in score_trajectory)
    verdict = (
        "PASS" if (converged and final_score >= 75)
        else "REFINE" if final_score >= 50
        else "STAGNATED" if halt_reason == "stagnation"
        else "FAIL"
    )

    if not md_path.exists():
        md_path.write_text(
            "# Atomadic Forge — Evolution Log\n\n"
            "Auto-appended by every `forge evolve` / `forge demo` run.\n\n"
            f"{_TABLE_HEADER}\n",
            encoding="utf-8",
        )
    row = (
        f"| {ts} | {_intent_short(intent)} | `{package}` | `{llm_name}` "
        f"| {rounds_completed} | `{arc}` | **{final_score:.0f}** | {verdict} |\n"
    )
    with md_path.open("a", encoding="utf-8") as f:
        f.write(row)

    entry = {
        "schema_version": "atomadic-forge.evolve_log/v1",
        "ts_utc": ts,
        "package": package,
        "intent": intent,
        "llm": llm_name,
        "rounds_completed": rounds_completed,
        "score_trajectory": score_trajectory,
        "final_score": final_score,
        "converged": converged,
        "halt_reason": halt_reason,
        "verdict": verdict,
        "extra": extra or {},
    }
    with jsonl_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")

    return md_path
