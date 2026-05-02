"""Tier a2 - 4-tier hierarchical memory (MemGPT/Park 2023 pattern).

Schema:
  M0  working context     in-memory, ~2-4k tokens, 1 cycle lifetime
  M1  core/pinned          SQLite memory_core, always-injected
  M2  episodic             SQLite memory_episodic + token-Jaccard recall
  M3  semantic/reflection  SQLite memory_reflection, distilled abstractions

Retrieval score (Park 2023):
  score = alpha*recency + beta*importance + gamma*relevance
  where recency = exp(-decay_rate * (now - last_access))
        importance = stored 0..1 score
        relevance = intent_similarity(query, content)

Composes:
  a1 intent_similarity      relevance signal (token Jaccard + difflib)
  a2 ledger_store           reuses sqlite connection pattern

Pure Python + stdlib sqlite3. No external embedding service - the
deterministic relevance proxy makes this air-gappable.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..a1_at_functions import intent_similarity

SCHEMA: str = "atomadic-forge-deluxe.hierarchical-memory/v1"

DEFAULT_DECAY_RATE = 0.0001       # per-second; ~half-life ~2h
DEFAULT_RECENCY_WEIGHT = 1.0
DEFAULT_IMPORTANCE_WEIGHT = 1.0
DEFAULT_RELEVANCE_WEIGHT = 1.5
DEFAULT_TTL_DAYS = 30
DEFAULT_DEDUP_THRESHOLD = 0.92
DEFAULT_REFLECTION_TRIGGER = 150.0   # Park 2023's threshold


@dataclass(frozen=True)
class CoreMemory:
    id: int = 0
    key: str = ""
    value: str = ""
    pinned_at: float = 0.0


@dataclass(frozen=True)
class EpisodicMemory:
    id: int = 0
    cycle_id: str = ""
    ts: float = 0.0
    kind: str = "thought"        # observation|thought|action|result
    content: str = ""
    importance: float = 0.5
    last_access: float = 0.0
    access_count: int = 0


@dataclass(frozen=True)
class ReflectionMemory:
    id: int = 0
    parent_ids: tuple[int, ...] = field(default_factory=tuple)
    abstract: str = ""
    confidence: float = 0.7
    created_ts: float = 0.0


@dataclass(frozen=True)
class RecallResult:
    schema: str = SCHEMA
    query: str = ""
    core: tuple[CoreMemory, ...] = field(default_factory=tuple)
    episodic: tuple[tuple[EpisodicMemory, float], ...] = field(default_factory=tuple)
    reflections: tuple[tuple[ReflectionMemory, float], ...] = field(default_factory=tuple)
    total_scanned: int = 0


class HierarchicalMemory:
    """4-tier memory store. Persistent via SQLite."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path),
                                       check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS memory_core (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  key TEXT UNIQUE NOT NULL,
                  value TEXT NOT NULL,
                  pinned_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memory_episodic (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  cycle_id TEXT NOT NULL,
                  ts REAL NOT NULL,
                  kind TEXT NOT NULL,
                  content TEXT NOT NULL,
                  importance REAL DEFAULT 0.5,
                  last_access REAL NOT NULL,
                  access_count INTEGER DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_episodic_ts
                  ON memory_episodic(ts);
                CREATE INDEX IF NOT EXISTS idx_episodic_imp
                  ON memory_episodic(importance);
                CREATE TABLE IF NOT EXISTS memory_reflection (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  parent_ids TEXT NOT NULL,
                  abstract TEXT NOT NULL,
                  confidence REAL NOT NULL,
                  created_ts REAL NOT NULL
                );
            """)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ─── M1 core / pinned ───────────────────────────────────────────
    def pin(self, key: str, value: str) -> CoreMemory:
        ts = time.time()
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO memory_core(key, value, pinned_at) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET "
                "value=excluded.value, pinned_at=excluded.pinned_at",
                (key, value, ts))
            row = self._conn.execute(
                "SELECT id, key, value, pinned_at FROM memory_core "
                "WHERE key=?", (key,)).fetchone()
            return CoreMemory(id=row["id"], key=row["key"],
                                value=row["value"],
                                pinned_at=row["pinned_at"])

    def core_all(self) -> list[CoreMemory]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, key, value, pinned_at FROM memory_core "
                "ORDER BY pinned_at DESC").fetchall()
        return [CoreMemory(id=r["id"], key=r["key"],
                            value=r["value"],
                            pinned_at=r["pinned_at"]) for r in rows]

    # ─── M2 episodic ────────────────────────────────────────────────
    def remember(self, *,
                   cycle_id: str, kind: str, content: str,
                   importance: float = 0.5) -> EpisodicMemory:
        ts = time.time()
        # Dedup vs existing episodic content via Jaccard
        with self._lock:
            existing = self._conn.execute(
                "SELECT id, content, access_count FROM memory_episodic "
                "WHERE kind=? ORDER BY ts DESC LIMIT 50",
                (kind,)).fetchall()
        for r in existing:
            sim = intent_similarity.similarity(content, r["content"])
            if sim.score >= DEFAULT_DEDUP_THRESHOLD:
                # Increment access count instead of inserting dup
                with self._lock, self._conn:
                    self._conn.execute(
                        "UPDATE memory_episodic SET "
                        "access_count = access_count + 1, "
                        "last_access = ? WHERE id = ?",
                        (ts, r["id"]))
                    row = self._conn.execute(
                        "SELECT * FROM memory_episodic WHERE id=?",
                        (r["id"],)).fetchone()
                return self._row_to_episodic(row)
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO memory_episodic(cycle_id, ts, kind, "
                "content, importance, last_access, access_count) "
                "VALUES (?, ?, ?, ?, ?, ?, 0)",
                (cycle_id, ts, kind, content, importance, ts))
            new_id = cur.lastrowid
            row = self._conn.execute(
                "SELECT * FROM memory_episodic WHERE id=?",
                (new_id,)).fetchone()
        return self._row_to_episodic(row)

    def _row_to_episodic(self, row) -> EpisodicMemory:
        return EpisodicMemory(
            id=row["id"], cycle_id=row["cycle_id"], ts=row["ts"],
            kind=row["kind"], content=row["content"],
            importance=row["importance"],
            last_access=row["last_access"],
            access_count=row["access_count"])

    # ─── M3 reflection ──────────────────────────────────────────────
    def reflect(self, *,
                  parent_ids: list[int],
                  abstract: str,
                  confidence: float = 0.7) -> ReflectionMemory:
        ts = time.time()
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO memory_reflection(parent_ids, abstract, "
                "confidence, created_ts) VALUES (?, ?, ?, ?)",
                (json.dumps(parent_ids), abstract, confidence, ts))
            return ReflectionMemory(
                id=cur.lastrowid, parent_ids=tuple(parent_ids),
                abstract=abstract, confidence=confidence,
                created_ts=ts)

    # ─── recall (Park 2023 score) ───────────────────────────────────
    def recall(self, query: str, *,
                  recency_weight: float = DEFAULT_RECENCY_WEIGHT,
                  importance_weight: float = DEFAULT_IMPORTANCE_WEIGHT,
                  relevance_weight: float = DEFAULT_RELEVANCE_WEIGHT,
                  decay_rate: float = DEFAULT_DECAY_RATE,
                  top_k: int = 8,
                  ) -> RecallResult:
        now = time.time()
        with self._lock:
            ep_rows = self._conn.execute(
                "SELECT * FROM memory_episodic ORDER BY ts DESC "
                "LIMIT 500").fetchall()
            rf_rows = self._conn.execute(
                "SELECT * FROM memory_reflection ORDER BY created_ts "
                "DESC LIMIT 200").fetchall()
        scored_episodic: list[tuple[EpisodicMemory, float]] = []
        for r in ep_rows:
            recency = pow(2.71828, -decay_rate * (now - r["last_access"]))
            relevance = intent_similarity.similarity(
                query, r["content"]).score
            score = (recency_weight * recency
                       + importance_weight * r["importance"]
                       + relevance_weight * relevance)
            scored_episodic.append(
                (self._row_to_episodic(r), score))
        scored_episodic.sort(key=lambda kv: -kv[1])
        scored_reflections: list[tuple[ReflectionMemory, float]] = []
        for r in rf_rows:
            relevance = intent_similarity.similarity(
                query, r["abstract"]).score
            recency = pow(2.71828, -decay_rate * (now - r["created_ts"]))
            score = (recency * 0.5 + relevance * 1.5
                       + r["confidence"] * 0.5)
            try:
                pids = tuple(json.loads(r["parent_ids"]))
            except (json.JSONDecodeError, TypeError):
                pids = ()
            scored_reflections.append((
                ReflectionMemory(
                    id=r["id"], parent_ids=pids,
                    abstract=r["abstract"],
                    confidence=r["confidence"],
                    created_ts=r["created_ts"],
                ), score))
        scored_reflections.sort(key=lambda kv: -kv[1])
        # Update last_access for top-k episodic returned
        if scored_episodic:
            top_ids = [e.id for e, _ in scored_episodic[:top_k]]
            with self._lock, self._conn:
                self._conn.executemany(
                    "UPDATE memory_episodic SET last_access=?, "
                    "access_count=access_count+1 WHERE id=?",
                    [(now, eid) for eid in top_ids])
        return RecallResult(
            query=query,
            core=tuple(self.core_all()),
            episodic=tuple(scored_episodic[:top_k]),
            reflections=tuple(scored_reflections[:top_k]),
            total_scanned=len(ep_rows) + len(rf_rows),
        )

    # ─── consolidation trigger (Park 2023) ──────────────────────────
    def reflection_due(self,
                          *, threshold: float = DEFAULT_REFLECTION_TRIGGER,
                          since_ts: float = 0.0) -> bool:
        """Returns True if accumulated importance since the last
        reflection exceeds threshold (Park's default = 150)."""
        with self._lock:
            row = self._conn.execute(
                "SELECT COALESCE(SUM(importance), 0) AS s "
                "FROM memory_episodic WHERE ts > ?",
                (since_ts,)).fetchone()
        return float(row["s"] or 0.0) >= threshold

    # ─── TTL pruning ────────────────────────────────────────────────
    def prune_stale(self,
                     *, ttl_days: int = DEFAULT_TTL_DAYS,
                     min_importance: float = 0.3,
                     min_access: int = 2) -> int:
        """Drop M2 episodic entries older than TTL with low importance
        AND low access. Returns count pruned."""
        cutoff = time.time() - ttl_days * 86400
        with self._lock, self._conn:
            cur = self._conn.execute(
                "DELETE FROM memory_episodic "
                "WHERE ts < ? AND importance < ? AND access_count < ?",
                (cutoff, min_importance, min_access))
            return cur.rowcount or 0
