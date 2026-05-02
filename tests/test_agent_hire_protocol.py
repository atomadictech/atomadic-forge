"""Tests for agent_hire_protocol cherry-picked from forge-deluxe-seed.

5-step hiring protocol composing trust_gate_response (a1) +
intent_similarity (a1) + sealed-probe vetting + D_max=3 enforcement.
"""

from __future__ import annotations

from atomadic_forge.a3_og_features.agent_hire_protocol import (
    AgentConstraints, RoleSpec,
    hire_for_role, post_role, vet_candidate,
)


def test_post_role_produces_typed_spec():
    role = post_role(
        role_id="code-reviewer-v1",
        goal="Review Python diffs",
        probe_prompt="Review this diff: ...",
        expected_output_signal="tier violation found",
        required_capabilities=("python_ast",),
        d_max_subdelegation=1,
    )
    assert isinstance(role, RoleSpec)
    assert role.role_id == "code-reviewer-v1"
    assert role.fingerprint != ""
    assert role.constraints.d_max_subdelegation == 1


def test_vet_candidate_scores_relevance():
    role = post_role(
        role_id="r", goal="g",
        probe_prompt="What is the tier of a pure function?",
        expected_output_signal="tier a1",
    )
    good = vet_candidate(
        role=role, candidate_id="cand-1",
        probe_output="A pure stateless function lives in tier a1.")
    bad = vet_candidate(
        role=role, candidate_id="cand-2",
        probe_output="I don't know.")
    assert good.composite_score > bad.composite_score


def test_hire_for_role_picks_winner():
    role = post_role(
        role_id="r", goal="g",
        probe_prompt="describe tier a1",
        expected_output_signal="pure stateless functions",
        min_score=0.3,
    )
    def exec_fn(cid, probe):
        if cid == "good":
            return "tier a1 holds pure stateless functions"
        return "no idea"
    result = hire_for_role(
        role=role, candidate_ids=("good", "bad"),
        executor=exec_fn, current_delegation_depth=0)
    assert result.winner is not None
    assert result.winner.candidate_id == "good"
    assert result.contract_signature != ""


def test_hire_respects_d_max():
    role = post_role(
        role_id="r", goal="g", probe_prompt="x",
        expected_output_signal="x", d_max_subdelegation=1)
    result = hire_for_role(
        role=role, candidate_ids=("c1",),
        executor=lambda cid, p: "x",
        current_delegation_depth=3)
    assert result.winner is None
    assert result.delegation_depth == 3


def test_hire_no_executor_returns_role_only():
    role = post_role(
        role_id="r", goal="g", probe_prompt="x",
        expected_output_signal="x")
    result = hire_for_role(
        role=role, candidate_ids=("c1",), executor=None)
    assert result.role is not None
    assert result.winner is None


def test_hire_handles_executor_exception():
    role = post_role(
        role_id="r", goal="g", probe_prompt="x",
        expected_output_signal="x")
    def bad_exec(cid, p):
        raise RuntimeError("network down")
    result = hire_for_role(
        role=role, candidate_ids=("c1",),
        executor=bad_exec)
    assert len(result.candidates) == 1
    assert result.candidates[0].composite_score == 0.0
    assert result.winner is None
