"""Test the iterate + evolve loops with a deterministic StubLLM.

The StubLLM returns canned ``[{path, content}]`` responses so we can verify
the 3-way constraint-satisfaction loop runs end-to-end without a real LLM.
"""

from __future__ import annotations

import json
from pathlib import Path

from atomadic_forge.a1_at_functions.forge_feedback import (
    compute_reuse_stats, pack_feedback, parse_files_from_response,
)
from atomadic_forge.a1_at_functions.llm_client import StubLLMClient
from atomadic_forge.a3_og_features.forge_evolve import run_evolve
from atomadic_forge.a3_og_features.forge_loop import run_iterate


def test_parse_files_from_response_handles_fenced_json():
    blob = '''Some prose first.
```json
[{"path": "src/x/a1_at_functions/foo.py", "content": "def foo(): return 42\\n"}]
```
trailing prose.'''
    files = parse_files_from_response(blob)
    assert len(files) == 1
    assert files[0]["path"] == "src/x/a1_at_functions/foo.py"
    assert "def foo()" in files[0]["content"]


def test_parse_files_from_response_handles_inline_array():
    blob = (
        'Look at this: '
        '[{"path": "src/x/a0_qk_constants/types.py", "content": "X = 1\\n"}]'
    )
    files = parse_files_from_response(blob)
    assert len(files) == 1


def test_compute_reuse_stats_with_overlap():
    seed = [{"qualname": "add"}, {"qualname": "divide"}, {"qualname": "Counter.incr"}]
    scout = {"symbols": [{"qualname": "add"}, {"qualname": "subtract"}]}
    stats = compute_reuse_stats(scout, seed)
    assert stats["reuse_ratio"] == 0.5     # 1 of 2 emitted overlap
    assert "add" in stats["reused_symbols"]
    assert "subtract" in stats["novel_symbols"]


def test_pack_feedback_includes_all_three_signals():
    fb = pack_feedback(
        wire_report={"violation_count": 2, "verdict": "FAIL",
                      "violations": [{"file": "x.py", "from_tier": "a1_at_functions",
                                       "to_tier": "a3_og_features", "imported": "Foo"}]},
        certify_report={"score": 60, "issues": ["bad"], "recommendations": []},
        emergent_overlay={"candidates": [
            {"name": "alpha-pipeline", "score": 50,
              "chain": {"chain": ["pkg.a", "pkg.b"], "domains": ["a", "b"]}}
        ]},
        reuse_stats={"reuse_ratio": 0.1,
                      "available_unused": ["pkg.helpful_thing"],
                      "novel_symbols": [], "reused_symbols": []},
        iteration=2,
    )
    assert "Wire scan: **FAIL**" in fb
    assert "Certify score: **60/100**" in fb
    assert "Reuse signal: **10%**" in fb
    assert "Emergent compositions" in fb
    assert "pkg.helpful_thing" in fb


def test_iterate_with_stub_llm_writes_files(tmp_path):
    """The full loop runs and writes whatever files the stub emits."""
    canned = [
        json.dumps([
            {"path": "src/genstub/a1_at_functions/hello.py",
             "content": '"""Tier a1."""\ndef hello(): return "hi"\n'},
            {"path": "src/genstub/a4_sy_orchestration/cli.py",
             "content": '"""Tier a4."""\nfrom genstub.a1_at_functions.hello import hello\n'},
        ]),
        # Round 2: empty array signals "done"
        "[]",
    ]
    llm = StubLLMClient(canned=canned)
    output = tmp_path / "out"
    output.mkdir()
    report = run_iterate(
        "build a hello CLI",
        output=output,
        package="genstub",
        llm=llm,
        max_iterations=2,
        target_score=0.0,  # so we don't get stuck waiting for docs/tests
    )
    assert report["applied"] is True
    assert report["files_written_total"] >= 2
    assert (output / "src" / "genstub" / "a1_at_functions" / "hello.py").exists()


def test_iterate_preflight_no_apply(tmp_path):
    """--no-apply path returns the prompts without calling the LLM."""
    llm = StubLLMClient()
    report = run_iterate(
        "anything",
        output=tmp_path / "out",
        package="preview",
        llm=llm,
        apply=False,
    )
    assert report["applied"] is False
    assert "system_prompt" in report
    assert "first_prompt" in report
    assert llm.calls == 0  # no LLM invocation in pre-flight


def test_evolve_runs_two_rounds_with_stub(tmp_path):
    """Recursive evolve completes the requested rounds."""
    # Each round's iterate-loop does one initial turn then either a fix or
    # an empty-array signal.  We feed enough canned responses for 2 rounds.
    canned = (
        # Round 0 — emit a real public function so the catalog sees it.
        [json.dumps([
            {"path": "src/ev/a1_at_functions/seed.py",
             "content": '"""Tier a1 — seed."""\ndef seed_fn(x):\n    return x * 2\n'},
        ]), "[]"]
        # Round 1 — emit another function in a different tier.
        + [json.dumps([
            {"path": "src/ev/a2_mo_composites/store.py",
             "content": '"""Tier a2 — store."""\nclass Store:\n    def __init__(self):\n        self.data = {}\n    def put(self, k, v):\n        self.data[k] = v\n'},
        ]), "[]"]
    )
    llm = StubLLMClient(canned=canned)
    report = run_evolve(
        "grow",
        output=tmp_path / "out",
        package="ev",
        llm=llm,
        rounds=2,
        iterations_per_round=2,
        target_score=0.0,
    )
    assert report["rounds_completed"] >= 1
    assert report["final_symbol_count"] >= 1
    assert isinstance(report["score_trajectory"], list)
    assert isinstance(report["symbol_trajectory"], list)
