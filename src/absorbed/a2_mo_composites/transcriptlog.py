"""Tier a1 — append-only LLM transcript logger.

For full transparency, every prompt sent to the LLM and every response
received is appended to ``.atomadic-forge/transcripts/<run-id>.jsonl``.

Operators can audit exactly what Forge asked the LLM and exactly what the
LLM emitted.  No black-box magic — every byte is on disk.

Usage:
    log = TranscriptLog(project_root, run_id="evolve-20260427T0815")
    log.append("system", system_prompt)
    log.append("user", user_prompt, role="prompt")
    log.append("assistant", llm_response, role="response")
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any


class TranscriptLog:
    """Append-only JSONL log of every LLM exchange in a Forge run."""

    def __init__(self, project_root: Path, run_id: str | None = None,
                 dirname: str = ".atomadic-forge") -> None:
        self.project_root = Path(project_root).resolve()
        self.run_id = run_id or _dt.datetime.now(_dt.timezone.utc).strftime(
            "run-%Y%m%dT%H%M%S")
        self.dir = self.project_root / dirname / "transcripts"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / f"{self.run_id}.jsonl"
        self._turn = 0
        if not self.path.exists():
            self._write_meta()

    def _write_meta(self) -> None:
        self._raw_append({
            "schema_version": "atomadic-forge.transcript/v1",
            "ts_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "kind": "meta",
            "run_id": self.run_id,
        })

    def append(self, kind: str, content: str, *,
               role: str = "", llm: str = "",
               extra: dict[str, Any] | None = None) -> None:
        """Append one entry.

        ``kind`` is e.g. ``"prompt"``, ``"response"``, ``"system"``, ``"meta"``.
        ``role`` is for chat-shape compat (``"system"|"user"|"assistant"``).
        """
        self._turn += 1
        self._raw_append({
            "schema_version": "atomadic-forge.transcript/v1",
            "ts_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "turn": self._turn,
            "kind": kind,
            "role": role,
            "llm": llm,
            "content": content,
            "content_len": len(content or ""),
            "extra": extra or {},
        })

    def _raw_append(self, entry: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
