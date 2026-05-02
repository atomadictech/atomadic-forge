"""Tests for the trust_gate_response a1 module + its MCP wrapper."""

from __future__ import annotations

from atomadic_forge.a1_at_functions.trust_gate_response import (
    TrustVerdict,
    gate_response,
)


def test_clean_response_high_score():
    v = gate_response("Plain prose with no claims or code.")
    assert isinstance(v, TrustVerdict)
    assert v.safe_to_act
    assert v.score > 0.9


def test_unresolved_import_flagged():
    response = (
        "Use this:\n```python\n"
        "import totally_made_up_xyz_pkg_zzz\n```\n"
    )
    v = gate_response(response)
    assert any(f.category == "unresolved_import" for f in v.findings)


def test_syntax_error_in_code_block_flagged():
    response = "```python\ndef broken(:\n```"
    v = gate_response(response)
    assert any(f.category == "syntax_error" for f in v.findings)
    assert not v.safe_to_act


def test_false_capability_claim_with_known_list():
    response = "Forge has `quantum_teleporter` for free."
    v = gate_response(
        response,
        known_capabilities=["recon", "wire", "certify"])
    assert any(f.category == "false_claim" for f in v.findings)
    assert not v.safe_to_act


def test_real_capability_claim_passes():
    response = "Forge has `recon` for tier-mapping a repo."
    v = gate_response(
        response,
        known_capabilities=["recon", "wire", "certify"])
    false_claims = [f for f in v.findings if f.category == "false_claim"]
    assert len(false_claims) == 0


def test_placeholder_url_flagged():
    v = gate_response("See https://example.com/...")
    assert any(f.category == "bad_url" for f in v.findings)


def test_stub_pattern_in_code_block_flagged():
    response = "```python\ndef foo():\n    pass\n```"
    v = gate_response(response)
    assert any(f.category == "stub_pattern" for f in v.findings)


def test_local_pkg_prefix_skips_imports():
    response = (
        "```python\n"
        "from atomadic_forge.a1_at_functions.recon import scan\n"
        "```\n"
    )
    v = gate_response(response, local_pkg_prefix="atomadic_forge")
    unresolved = [f for f in v.findings
                    if f.category == "unresolved_import"]
    assert len(unresolved) == 0


def test_score_decreases_with_findings():
    clean = gate_response("plain text")
    dirty = gate_response(
        "Forge has `fabricated_thing`.\n"
        "```python\nimport not_a_real_pkg_zzz\n```",
        known_capabilities=["real_thing"])
    assert dirty.score < clean.score


def test_mcp_tool_handler_registered():
    from atomadic_forge.a1_at_functions.mcp_protocol import TOOLS
    assert "trust_gate_response" in TOOLS
    spec = TOOLS["trust_gate_response"]
    assert spec["name"] == "trust_gate_response"
    assert callable(spec["handler"])


def test_mcp_tool_handler_runs():
    from atomadic_forge.a1_at_functions.mcp_protocol import TOOLS
    handler = TOOLS["trust_gate_response"]["handler"]
    from pathlib import Path
    out = handler(Path("."), {"response": "Plain text."})
    assert "score" in out
    assert "safe_to_act" in out
    assert out["safe_to_act"] is True


def test_mcp_tool_missing_response_returns_error():
    from pathlib import Path

    from atomadic_forge.a1_at_functions.mcp_protocol import TOOLS
    handler = TOOLS["trust_gate_response"]["handler"]
    out = handler(Path("."), {})
    assert "error" in out
