"""Tests for Tier a1 — pure helpers in ``forge_auth``.

Golden Path Lane C W5 — these tests pin the contract the a2 client
relies on: env parsing, key-shape validation, request shaping, and
the deterministic project-path hash. No HTTP, no monkeypatching of
urllib — that's a2's territory (test_forge_auth_a2.py).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from atomadic_forge.a0_qk_constants.auth_constants import (
    API_KEY_ENV,
    API_KEY_PREFIX,
)
from atomadic_forge.a1_at_functions.forge_auth import (
    build_usage_log_request,
    build_verify_request,
    hash_project_path,
    is_valid_api_key_shape,
    parse_verify_response,
    read_api_key_from_env,
)


# ---- read_api_key_from_env --------------------------------------------

def test_read_api_key_returns_none_when_env_missing():
    assert read_api_key_from_env({}) is None


def test_read_api_key_returns_none_for_empty_string():
    assert read_api_key_from_env({API_KEY_ENV: ""}) is None
    assert read_api_key_from_env({API_KEY_ENV: "   "}) is None


def test_read_api_key_strips_whitespace_and_returns_value():
    out = read_api_key_from_env({API_KEY_ENV: "  fk_live_abc123  "})
    assert out == "fk_live_abc123"


def test_read_api_key_rejects_wrong_prefix():
    assert read_api_key_from_env({API_KEY_ENV: "fk_test_abc"}) is None
    assert read_api_key_from_env({API_KEY_ENV: "sk-1234"}) is None
    assert read_api_key_from_env({API_KEY_ENV: "fk_LIVE_abc"}) is None  # case sensitive


def test_read_api_key_accepts_minimal_valid_key():
    assert read_api_key_from_env({API_KEY_ENV: "fk_live_x"}) == "fk_live_x"


# ---- is_valid_api_key_shape -------------------------------------------

def test_is_valid_shape_rejects_non_string():
    assert is_valid_api_key_shape(None) is False  # type: ignore[arg-type]
    assert is_valid_api_key_shape(123) is False  # type: ignore[arg-type]
    assert is_valid_api_key_shape(b"fk_live_x") is False  # type: ignore[arg-type]


def test_is_valid_shape_rejects_prefix_only():
    assert is_valid_api_key_shape(API_KEY_PREFIX) is False


def test_is_valid_shape_rejects_wrong_prefix():
    assert is_valid_api_key_shape("fk_test_x") is False
    assert is_valid_api_key_shape("xyz_live_x") is False
    assert is_valid_api_key_shape("") is False


def test_is_valid_shape_accepts_well_formed_key():
    assert is_valid_api_key_shape("fk_live_abc") is True
    assert is_valid_api_key_shape("  fk_live_abc  ") is True  # trims first


def test_is_valid_shape_rejects_whitespace_only_after_prefix():
    # "fk_live_   " has prefix but no real content after stripping.
    assert is_valid_api_key_shape("fk_live_") is False


# ---- build_verify_request ---------------------------------------------

def test_build_verify_request_shape():
    body = build_verify_request("fk_live_test")
    assert body == {"api_key": "fk_live_test"}


def test_build_verify_request_does_not_include_extra_fields():
    body = build_verify_request("fk_live_xyz")
    assert set(body.keys()) == {"api_key"}


# ---- parse_verify_response --------------------------------------------

def test_parse_verify_handles_non_dict():
    out = parse_verify_response("not a dict")  # type: ignore[arg-type]
    assert out["ok"] is False
    assert "non-object" in out["reason"]


def test_parse_verify_success_path():
    out = parse_verify_response({
        "ok": True,
        "email": "u@example.com",
        "plan": "pro",
        "reason": "",
    })
    assert out["ok"] is True
    assert out["email"] == "u@example.com"
    assert out["plan"] == "pro"


def test_parse_verify_default_for_missing_fields():
    out = parse_verify_response({"ok": False})
    assert out["ok"] is False
    assert out["email"] == ""
    assert out["plan"] == ""
    # When ok is False and no reason given, parser supplies a default.
    assert out["reason"]


def test_parse_verify_coerces_truthy_int_ok():
    out = parse_verify_response({"ok": 1, "email": "a@b.c"})
    assert out["ok"] is True


def test_parse_verify_treats_non_bool_string_as_false():
    out = parse_verify_response({"ok": "yes", "email": "a@b.c"})
    # We only accept bool / int for `ok`. Strings are rejected.
    assert out["ok"] is False


# ---- build_usage_log_request ------------------------------------------

def test_build_usage_log_request_shape():
    body = build_usage_log_request("fk_live_x", "wire", "deadbeef")
    assert body == {
        "api_key": "fk_live_x",
        "tool": "wire",
        "project_hash": "deadbeef",
    }


def test_build_usage_log_request_does_not_include_path():
    """Telemetry must never carry raw paths — only their hashes."""
    body = build_usage_log_request("fk_live_x", "certify", "abc")
    assert "project_path" not in body
    assert "path" not in body


# ---- hash_project_path ------------------------------------------------

def test_hash_project_path_returns_hex_sha256(tmp_path: Path):
    h = hash_project_path(tmp_path)
    # SHA-256 hex is 64 chars.
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_hash_project_path_is_deterministic(tmp_path: Path):
    a = hash_project_path(tmp_path)
    b = hash_project_path(tmp_path)
    assert a == b


def test_hash_project_path_resolves_relative(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a = hash_project_path(".")
    expected = hashlib.sha256(
        str(tmp_path.resolve()).encode("utf-8"),
    ).hexdigest()
    assert a == expected


def test_hash_project_path_differs_for_different_paths(tmp_path: Path):
    a = hash_project_path(tmp_path)
    b = hash_project_path(tmp_path / "nested")
    assert a != b
