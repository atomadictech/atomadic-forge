"""Tests for hierarchical_memory cherry-picked from forge-deluxe-seed.

4-tier MemGPT-pattern memory (M0 working / M1 core / M2 episodic /
M3 reflection) with Park-2023 recency×importance×relevance scoring.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from atomadic_forge.a2_mo_composites.hierarchical_memory import (
    HierarchicalMemory,
)


def test_pin_and_recall(tmp_path):
    mem = HierarchicalMemory(tmp_path / "mem.db")
    try:
        core = mem.pin("identity", "I am the agent")
        assert core.value == "I am the agent"
        all_core = mem.core_all()
        assert len(all_core) == 1
        assert all_core[0].key == "identity"
    finally:
        mem.close()


def test_episodic_dedup(tmp_path):
    mem = HierarchicalMemory(tmp_path / "mem.db")
    try:
        e1 = mem.remember(cycle_id="c1", kind="thought",
                            content="the plan looks solid")
        e2 = mem.remember(cycle_id="c1", kind="thought",
                            content="the plan looks solid")
        assert e1.id == e2.id
        assert e2.access_count == e1.access_count + 1
    finally:
        mem.close()


def test_recall_scores_by_relevance(tmp_path):
    mem = HierarchicalMemory(tmp_path / "mem.db")
    try:
        mem.remember(cycle_id="c", kind="thought",
                      content="kubernetes pod scheduling rules")
        mem.remember(cycle_id="c", kind="thought",
                      content="how to bake sourdough bread")
        r = mem.recall("kubernetes scheduling")
        assert r.episodic
        top_content = r.episodic[0][0].content
        assert "kubernetes" in top_content
    finally:
        mem.close()


def test_reflection_creates_abstraction(tmp_path):
    mem = HierarchicalMemory(tmp_path / "mem.db")
    try:
        e1 = mem.remember(cycle_id="c", kind="thought",
                            content="customer A asked about pricing")
        e2 = mem.remember(cycle_id="c", kind="thought",
                            content="customer B asked about pricing")
        ref = mem.reflect(parent_ids=[e1.id, e2.id],
                            abstract="Pricing questions are common.",
                            confidence=0.8)
        assert ref.abstract == "Pricing questions are common."
        assert ref.confidence == 0.8
        assert e1.id in ref.parent_ids
    finally:
        mem.close()


def test_prune_stale(tmp_path):
    mem = HierarchicalMemory(tmp_path / "mem.db")
    try:
        mem.remember(cycle_id="c", kind="thought", content="trivial",
                      importance=0.1)
        n = mem.prune_stale(ttl_days=-1, min_importance=0.3,
                              min_access=5)
        assert n >= 1
    finally:
        mem.close()


def test_reflection_due_threshold(tmp_path):
    mem = HierarchicalMemory(tmp_path / "mem.db")
    try:
        mem.remember(cycle_id="c", kind="thought",
                      content="mild observation", importance=0.5)
        assert not mem.reflection_due()
    finally:
        mem.close()
