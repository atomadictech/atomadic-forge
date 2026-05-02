"""Test that forge_evolve halts on stagnation (3 flat rounds)."""

from atomadic_forge.a1_at_functions.llm_client import StubLLMClient
from atomadic_forge.a3_og_features.forge_evolve import run_evolve


def test_stagnation_halts_evolve(tmp_path):
    """Stub LLM that emits empty responses every turn → flat catalog → halt."""
    # Empty-array means "done" per round, so each round terminates fast.
    canned = ["[]"] * 50
    llm = StubLLMClient(canned=canned)
    output = tmp_path / "out"
    output.mkdir()
    report = run_evolve(
        "anything",
        output=output,
        package="stagnant",
        llm=llm,
        rounds=10,
        iterations_per_round=1,
        target_score=100.0,
        stagnation_threshold=3,
    )
    # We requested 10 rounds but stagnation should trigger before 10 complete.
    assert report["rounds_completed"] < 10
    assert report["halt_reason"] in ("stagnation", "converged",
                                       "rounds_exhausted")


def test_stagnation_disabled_runs_all_rounds(tmp_path):
    """stagnation_threshold=0 disables the early-halt."""
    llm = StubLLMClient(canned=["[]"] * 50)
    output = tmp_path / "out"
    output.mkdir()
    report = run_evolve(
        "anything",
        output=output,
        package="stagnant_off",
        llm=llm,
        rounds=4,
        iterations_per_round=1,
        target_score=100.0,
        stagnation_threshold=0,
    )
    assert report["rounds_completed"] == 4
    # Halt reason will be rounds_exhausted since we didn't converge.
    assert report["halt_reason"] in ("rounds_exhausted", "converged")
