"""Regression tests for the source-cause Phase A repairs.

* sibling_refs detection — class refs in same source file are captured
* tier-promotion via ``has_self_assign`` — stateful classes promote a1→a2
* word-boundary tokens in classify_tier — ``atomadic`` no longer matches ``atom``
"""

from __future__ import annotations

from atomadic_forge.a1_at_functions.body_extractor import _extract_python_body
from atomadic_forge.a1_at_functions.classify_tier import classify_tier

_AGENTIC_SWARM_SRC = '''\
"""sibling-refs regression."""
from enum import Enum
from dataclasses import dataclass


class AgentRole(Enum):
    A = "a"


@dataclass
class AgentTask:
    role: AgentRole


class AgenticSwarm:
    def __init__(self):
        self.agents = {}
        self.history: list[AgentTask] = []

    def execute(self, role: AgentRole) -> AgentTask:
        return AgentTask(role)
'''


def test_sibling_refs_captured_for_extracted_class():
    extracted = _extract_python_body(_AGENTIC_SWARM_SRC, "AgenticSwarm")
    assert extracted is not None
    refs = set(extracted.sibling_refs)
    # Both AgentRole and AgentTask are referenced from inside AgenticSwarm
    # but defined as siblings in the same source file.
    assert "AgentRole" in refs
    assert "AgentTask" in refs


def test_state_markers_detected():
    extracted = _extract_python_body(_AGENTIC_SWARM_SRC, "AgenticSwarm")
    assert extracted is not None
    assert extracted.has_self_assign is True


def test_pure_class_has_no_state_markers():
    src = (
        "class PureContract:\n"
        "    SCHEMA = 'v1'\n"
        "    def shape(self) -> str:\n"
        "        return self.SCHEMA\n"
    )
    extracted = _extract_python_body(src, "PureContract")
    assert extracted is not None
    assert extracted.has_self_assign is False


def test_classify_tier_word_boundary_no_substring_false_positive():
    """Regression for the 'atomadic' contains 'atom' substring bug."""
    tier = classify_tier(name="AtomadicArchitectureMachine", kind="class",
                          path="atomadic-v2/src/atomadic/aam_v12.py")
    assert tier == "a2_mo_composites"


def test_classify_tier_promotes_with_body_signals():
    assert classify_tier(name="AgenticSwarm", kind="class",
                          path="atomadic-v2/src/atomadic/agentic_swarm.py") == "a2_mo_composites"
    assert classify_tier(
        name="AgenticSwarm", kind="class",
        path="atomadic-v2/src/atomadic/agentic_swarm.py",
        body_signals={"has_self_assign": True},
    ) == "a2_mo_composites"


def test_classify_tier_real_atom_token_still_works():
    """Word-boundary fix shouldn't break legitimate ``atom`` matches."""
    assert classify_tier(name="atom_validator", kind="function",
                          path="src/utils.py") == "a1_at_functions"
