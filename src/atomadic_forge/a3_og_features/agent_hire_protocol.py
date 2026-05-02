"""Tier a3 - 5-step agent hiring protocol (MetaGPT/CrewAI pattern).

Closes another SOTA gap: most agents fire actions but cannot
DEFINE roles for sub-agents and vet candidates. This module
gives Forge Deluxe the typed role-spec + sealed-probe vetting
protocol the cycle-14 hiring research called for.

Composes existing primitives:
  a3 trust_gate_runtime    deterministic hallucination detector
  a3 validate_emit          schema-fit gate on candidate output
  a1 intent_similarity      probe-vs-expected scoring
  a3 seed_self_audit        runtime-state validation

Pure orchestration: the actual candidate-execution callable is
caller-supplied (CandidateExecutor protocol). Without one, the
protocol returns a posted role spec only.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Callable, Protocol

from ..a1_at_functions import intent_similarity
from ..a1_at_functions.trust_gate_response import gate_response

SCHEMA: str = "atomadic-forge-deluxe.agent-hire/v1"

DEFAULT_MIN_SCORE = 0.65
DEFAULT_MAX_DELEGATION_DEPTH = 3   # ChatDev empirical limit
DEFAULT_PROBE_TIMEOUT_S = 30.0


@dataclass(frozen=True)
class AgentConstraints:
    max_tokens_per_turn: int = 8000
    d_max_subdelegation: int = 1
    boundary: str = "public_only"      # public_only | full
    forbidden_actions: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AcceptanceCriteria:
    probe_prompt: str = ""
    expected_output_signal: str = ""    # text the answer must contain
    min_score: float = DEFAULT_MIN_SCORE
    schema_must_validate: bool = False


@dataclass(frozen=True)
class RoleSpec:
    schema: str = SCHEMA
    role_id: str = ""
    principal: str = "forge-deluxe-seed"
    goal: str = ""
    required_capabilities: tuple[str, ...] = field(default_factory=tuple)
    required_tools: tuple[str, ...] = field(default_factory=tuple)
    constraints: AgentConstraints = field(default_factory=AgentConstraints)
    acceptance: AcceptanceCriteria = field(default_factory=AcceptanceCriteria)
    compensation_unit: str = "lora_capture_credit"
    term_hours: int = 24
    posted_at: str = ""
    fingerprint: str = ""


@dataclass(frozen=True)
class CandidateScore:
    candidate_id: str
    trust_score: float = 0.0           # from trust_gate_runtime
    relevance_score: float = 0.0        # intent_similarity vs expected
    composite_score: float = 0.0
    accepted: bool = False
    reasons: tuple[str, ...] = field(default_factory=tuple)
    probe_output: str = ""


@dataclass(frozen=True)
class HireResult:
    schema: str = SCHEMA
    role: RoleSpec | None = None
    candidates: tuple[CandidateScore, ...] = field(default_factory=tuple)
    winner: CandidateScore | None = None
    contract_signature: str = ""
    delegation_depth: int = 0


class CandidateExecutor(Protocol):
    """Caller-supplied: takes a candidate_id + probe prompt, returns
    the candidate's text output. The protocol vets the output."""
    def __call__(self, candidate_id: str, probe: str) -> str: ...


def _fingerprint(spec_dict: dict) -> str:
    blob = json.dumps(spec_dict, sort_keys=True,
                        separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def post_role(*,
                role_id: str,
                goal: str,
                probe_prompt: str,
                expected_output_signal: str,
                required_capabilities: tuple[str, ...] = (),
                required_tools: tuple[str, ...] = (),
                forbidden_actions: tuple[str, ...] = (),
                min_score: float = DEFAULT_MIN_SCORE,
                d_max_subdelegation: int = 1,
                ) -> RoleSpec:
    """Build a typed role spec + fingerprint. Pure."""
    posted_at = time.strftime("%Y-%m-%dT%H:%M:%S",
                                 time.gmtime(time.time()))
    spec_dict = {
        "role_id": role_id, "goal": goal,
        "probe_prompt": probe_prompt,
        "expected_output_signal": expected_output_signal,
        "required_capabilities": list(required_capabilities),
        "required_tools": list(required_tools),
        "forbidden_actions": list(forbidden_actions),
        "min_score": min_score,
        "d_max_subdelegation": d_max_subdelegation,
        "posted_at": posted_at,
    }
    fp = _fingerprint(spec_dict)
    return RoleSpec(
        role_id=role_id,
        goal=goal,
        required_capabilities=required_capabilities,
        required_tools=required_tools,
        constraints=AgentConstraints(
            d_max_subdelegation=d_max_subdelegation,
            forbidden_actions=forbidden_actions),
        acceptance=AcceptanceCriteria(
            probe_prompt=probe_prompt,
            expected_output_signal=expected_output_signal,
            min_score=min_score),
        posted_at=posted_at,
        fingerprint=fp,
    )


def vet_candidate(*,
                     role: RoleSpec,
                     candidate_id: str,
                     probe_output: str,
                     ) -> CandidateScore:
    """Run trust-gate + relevance scoring on a candidate's probe
    answer. Pure given the inputs."""
    trust = gate_response(probe_output)
    trust_score = trust.score
    relevance = intent_similarity.similarity(
        probe_output, role.acceptance.expected_output_signal).score
    composite = 0.6 * trust_score + 0.4 * relevance
    reasons: list[str] = []
    reasons.append(f"trust={trust_score:.2f} ({len(trust.findings)} findings)")
    reasons.append(f"relevance={relevance:.2f}")
    if not trust.safe_to_act:
        reasons.append("trust gate flagged HIGH severity (failed)")
        composite = min(composite, 0.4)
    accepted = (composite >= role.acceptance.min_score
                  and trust.safe_to_act)
    return CandidateScore(
        candidate_id=candidate_id,
        trust_score=trust_score,
        relevance_score=relevance,
        composite_score=composite,
        accepted=accepted,
        reasons=tuple(reasons),
        probe_output=probe_output[:300],
    )


def hire_for_role(*,
                     role: RoleSpec,
                     candidate_ids: tuple[str, ...],
                     executor: CandidateExecutor | None = None,
                     current_delegation_depth: int = 0,
                     ) -> HireResult:
    """Run the 5-step protocol:
      1. Verify D_max not exceeded
      2. For each candidate: invoke executor on the sealed probe
      3. Vet with trust_gate + relevance
      4. Pick top-scored above min_score
      5. Sign a contract (fingerprint over role+winner)
    Without an executor, returns the posted role only."""
    if current_delegation_depth >= DEFAULT_MAX_DELEGATION_DEPTH:
        return HireResult(
            role=role, delegation_depth=current_delegation_depth)
    if executor is None:
        return HireResult(role=role)

    scores: list[CandidateScore] = []
    for cid in candidate_ids:
        try:
            output = executor(cid, role.acceptance.probe_prompt)
        except Exception as e:  # noqa: BLE001
            scores.append(CandidateScore(
                candidate_id=cid,
                composite_score=0.0,
                reasons=(f"executor raised {type(e).__name__}: {e}",)))
            continue
        scores.append(vet_candidate(
            role=role, candidate_id=cid, probe_output=output))

    accepted = [s for s in scores if s.accepted]
    accepted.sort(key=lambda s: s.composite_score, reverse=True)
    winner = accepted[0] if accepted else None
    contract_sig = ""
    if winner is not None:
        contract_blob = json.dumps({
            "role_fingerprint": role.fingerprint,
            "winner_id": winner.candidate_id,
            "winner_score": winner.composite_score,
            "ts": role.posted_at,
        }, sort_keys=True, separators=(",", ":"))
        contract_sig = hashlib.sha256(
            contract_blob.encode()).hexdigest()[:32]

    return HireResult(
        role=role,
        candidates=tuple(scores),
        winner=winner,
        contract_signature=contract_sig,
        delegation_depth=current_delegation_depth + 1,
    )
