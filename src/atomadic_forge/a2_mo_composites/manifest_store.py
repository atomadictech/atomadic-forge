"""Tier a2 — stateful manifest read/write.

Persists scout / cherry / assimilate / certify reports under a project's
``.atomadic-forge/`` directory, and records run lineage.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any


_DEFAULT_DIRNAME = ".atomadic-forge"


class ManifestStore:
    """Append-only store for Forge artifacts beneath a project root."""

    def __init__(self, project_root: Path, *, dirname: str = _DEFAULT_DIRNAME):
        self.project_root = Path(project_root).resolve()
        self.dir = self.project_root / dirname
        self.dir.mkdir(parents=True, exist_ok=True)

    def save(self, name: str, payload: dict[str, Any]) -> Path:
        target = self.dir / f"{name}.json"
        target.write_text(json.dumps(payload, indent=2, default=str),
                          encoding="utf-8")
        self._append_lineage(name, target)
        return target

    def load(self, name: str) -> dict[str, Any] | None:
        target = self.dir / f"{name}.json"
        if not target.exists():
            return None
        return json.loads(target.read_text(encoding="utf-8"))

    def _append_lineage(self, name: str, path: Path) -> None:
        log = self.dir / "lineage.jsonl"
        entry = {
            "ts_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "artifact": name,
            "path": str(path.relative_to(self.project_root).as_posix()),
        }
        with log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
