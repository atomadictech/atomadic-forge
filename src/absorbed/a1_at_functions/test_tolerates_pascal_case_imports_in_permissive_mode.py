"""Tests for the exported_api_check a1 module + its MCP wrapper."""

from __future__ import annotations

from atomadic_forge.a1_at_functions.exported_api_check import (
    APIClaim, check_exported_api, extract_claims,
)


def test_extract_claims_finds_backticked_idents():
    doc = '"""Module exports `release_notes_from_rows` and `build_index`."""'
    claims = extract_claims(doc)
    names = {c.name for c in claims}
    assert "release_notes_from_rows" in names
    assert "build_index" in names


def test_extract_claims_skips_short_and_stoplist():
    doc = '"""Has `cls`, `int`, `True`, `Path` (all ignored)."""'
    claims = extract_claims(doc)
    assert claims == []


def test_passes_when_function_present():
    src = (
        '"""Module: exports `foo_bar` for callers."""\n'
        'from __future__ import annotations\n'
        'def foo_bar(x):\n'
        '    return x + 1\n'
    )
    r = check_exported_api(src)
    assert r.ok
    assert "foo_bar" in r.resolved


def test_fails_when_function_missing():
    """The exact failure mode this gate is designed to catch."""
    src = (
        '"""Pure helper that exposes `release_notes_from_rows` '
        'for the caller."""\n'
        'from dataclasses import dataclass\n'
        '@dataclass(frozen=True)\n'
        'class ReleaseNotes:\n'
        '    pass\n'
        'def _row_to_entry(r):\n'
        '    return r\n'
    )
    r = check_exported_api(src)
    assert not r.ok
    assert "release_notes_from_rows" in r.unresolved
    assert "release_notes_from_rows" in r.detail


def test_tolerates_pascal_case_imports_in_permissive_mode():
    src = (
        '"""Returns `Path` and `OrderedDict` for paths."""\n'
        'from pathlib import Path\n'
        'from collections import OrderedDict\n'
        'def make_thing():\n'
        '    return Path("x"), OrderedDict()\n'
    )
    r = check_exported_api(src)
    assert r.ok


def test_strict_mode_fails_on_pascal_too():
    src = (
        '"""Promises `IsThereYet` (PascalCase) to exist."""\n'
        'def x(): return 1\n'
    )
    r = check_exported_api(src, strict=True)
    assert not r.ok


def test_handles_no_docstring():
    src = 'def x(): return 1\n'
    r = check_exported_api(src)
    assert r.ok
    assert "no module docstring" in r.detail


def test_handles_syntax_error():
    src = 'def broken(:'
    r = check_exported_api(src)
    assert not r.ok
    assert "syntax error" in r.detail


def test_signature_pattern_extracted():
    doc = (
        '"""\n'
        '    parse_thing(src) -> Result\n'
        'is the public entry.\n'
        '"""\n'
    )
    claims = extract_claims(doc)
    assert any(c.name == "parse_thing" for c in claims)


def test_mcp_tool_handler_registered():
    from atomadic_forge.a1_at_functions.mcp_protocol import TOOLS
    assert "exported_api_check" in TOOLS
    spec = TOOLS["exported_api_check"]
    assert spec["name"] == "exported_api_check"
    assert callable(spec["handler"])


def test_mcp_tool_handler_with_source():
    from atomadic_forge.a1_at_functions.mcp_protocol import TOOLS
    from pathlib import Path
    handler = TOOLS["exported_api_check"]["handler"]
    src = '"""Exports `do_thing`."""\ndef do_thing(): return 1\n'
    out = handler(Path("."), {"source": src})
    assert out["ok"] is True
    assert "do_thing" in out["resolved"]


def test_mcp_tool_handler_with_path(tmp_path):
    from atomadic_forge.a1_at_functions.mcp_protocol import TOOLS
    handler = TOOLS["exported_api_check"]["handler"]
    p = tmp_path / "m.py"
    p.write_text(
        '"""Exports `helper_function`."""\n'
        'def helper_function(x): return x\n',
        encoding="utf-8")
    out = handler(tmp_path, {"path": str(p)})
    assert out["ok"] is True


def test_mcp_tool_missing_args_returns_error():
    from atomadic_forge.a1_at_functions.mcp_protocol import TOOLS
    from pathlib import Path
    handler = TOOLS["exported_api_check"]["handler"]
    out = handler(Path("."), {})
    assert "error" in out


def test_mcp_tool_strict_flag_propagates():
    from atomadic_forge.a1_at_functions.mcp_protocol import TOOLS
    from pathlib import Path
    handler = TOOLS["exported_api_check"]["handler"]
    src = '"""Promises `BigClassName`."""\ndef x(): return 1\n'
    permissive = handler(Path("."), {"source": src})
    strict = handler(Path("."), {"source": src, "strict": True})
    assert permissive["ok"] is True
    assert strict["ok"] is False
