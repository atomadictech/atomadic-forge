"""Tests for the dedup_engine cherry-pick from forge-deluxe-seed.

Cherry-pick origin: forge-deluxe-seed cycle 7 (`dedup_engine`,
`code_signature`, `intent_similarity`, `research_note_distiller`,
`cross_agent_intent_deduplicator`). Imports adapted from the seed's
`forge_deluxe_seed.*` namespace to atomadic-forge's `atomadic_forge.*`.
"""

from __future__ import annotations

from pathlib import Path

from atomadic_forge.a1_at_functions import intent_similarity
from atomadic_forge.a1_at_functions.code_signature import (
    function_overlap, signature_of,
)
from atomadic_forge.a1_at_functions.research_note_distiller import (
    distill_notes,
)
from atomadic_forge.a2_mo_composites.cross_agent_intent_deduplicator import (
    CrossAgentIntentDeduplicator,
)
from atomadic_forge.a3_og_features.dedup_engine import (
    dedup_code_tree, dedup_research_notes, run_dedup,
)


# ───────── intent_similarity ──────────

def test_intent_similarity_identical():
    r = intent_similarity.similarity("import killswitch",
                                       "import killswitch")
    assert r.score == 1.0


def test_intent_similarity_completely_different():
    r = intent_similarity.similarity("alpha bravo charlie",
                                       "delta echo foxtrot")
    assert r.score < 0.2


def test_intent_similarity_partial_overlap():
    r = intent_similarity.similarity("validate emit gate",
                                       "validate new module")
    assert 0.2 < r.score < 0.95


# ───────── code_signature ──────────

def test_signature_stable_under_rename():
    a = "def f(x):\n    return x + 1\n"
    b = "def g(y):\n    return y + 1\n"
    sa = signature_of(a)
    sb = signature_of(b)
    assert sa.functions[0].body_hash == sb.functions[0].body_hash
    assert sa.module_hash == sb.module_hash


def test_signature_breaks_on_logic_change():
    a = "def f(x):\n    return x + 1\n"
    b = "def f(x):\n    return x * 2\n"
    sa = signature_of(a)
    sb = signature_of(b)
    assert sa.functions[0].body_hash != sb.functions[0].body_hash


def test_signature_handles_syntax_error():
    sig = signature_of("def broken(:")
    assert sig.parse_ok is False


def test_function_overlap_finds_dupes():
    a = signature_of("def add(x, y): return x + y\n")
    b = signature_of(
        "def addition(p, q): return p + q\n"
        "def other(z): return z * 2\n"
    )
    overlap = function_overlap(a, b)
    assert len(overlap) == 1


# ───────── cross_agent_intent_deduplicator ──────────

def test_cross_agent_dedup_accepts_first_then_blocks():
    d = CrossAgentIntentDeduplicator()
    a = d.propose("agent-1", "find dead code in repo")
    b = d.propose("agent-2", "find dead code in the repo")
    assert a["verdict"] == "ACCEPT"
    assert b["verdict"] == "DUPLICATE"


def test_cross_agent_dedup_accepts_distinct():
    d = CrossAgentIntentDeduplicator()
    a = d.propose("agent-1", "find dead code")
    b = d.propose("agent-2", "render markdown")
    assert a["verdict"] == "ACCEPT"
    assert b["verdict"] == "ACCEPT"


# ───────── dedup_engine ──────────

def test_dedup_code_tree_finds_template_dupes(tmp_path):
    pkg = tmp_path / "src"
    pkg.mkdir()
    (pkg / "alpha.py").write_text("def f(x): return x + 1\n")
    (pkg / "beta.py").write_text("def g(y): return y + 1\n")
    (pkg / "gamma.py").write_text("def h(z): return z * z\n")
    groups, novel = dedup_code_tree(pkg)
    assert len(groups) == 1
    assert len(groups[0].duplicates) == 1
    assert len(novel) == 1


def test_dedup_research_notes_groups_near_duplicates(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "a.md").write_text(
        "# Import killswitch\n\n**Thesis:** block bad imports\n")
    (inbox / "b.md").write_text(
        "# Import Killswitch verb\n\n**Thesis:** block bad imports at the gate\n")
    (inbox / "c.md").write_text(
        "# PR badge GitHub action\n\n**Thesis:** advertise verified PRs\n")
    groups, novel = dedup_research_notes(inbox, threshold=0.50)
    assert len(groups) >= 1
    assert len(novel) >= 1


def test_run_dedup_full(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "a.md").write_text("# Foo\n\n**Thesis:** bar\n")
    code = tmp_path / "code"
    code.mkdir()
    (code / "x.py").write_text("def f(x): return x\n")
    report = run_dedup(
        research_inboxes=(inbox,), code_roots=(code,))
    assert report.files_scanned >= 1


# ───────── research_note_distiller ──────────

def test_distill_notes_extracts_capabilities():
    notes = [
        "# Foo capability\n\n**Thesis:** does foo well\n\nUses `foo_helper`.",
        "# Bar feature\n\n**Thesis:** does bar\n\nUses `bar_thing`.",
    ]
    d = distill_notes(notes)
    assert d.total_notes == 2
    # Extracts capability identifiers from backticks
    caps = set(d.unique_capabilities)
    assert "foo_helper" in caps
    assert "bar_thing" in caps
    # Builds a structured prompt
    assert d.prompt
    assert d.total_chars_original > 0
