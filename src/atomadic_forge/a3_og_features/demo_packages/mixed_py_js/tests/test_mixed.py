"""Behavioural tests for mixed_pkg — recognised by forge certify."""

from __future__ import annotations

from mixed_pkg.a1_at_functions import greet, length_within


def test_greet_returns_prefixed_name() -> None:
    assert greet("Forge") == "hello, Forge"


def test_greet_handles_empty_name() -> None:
    assert greet("") == "hello, world"


def test_length_within_caps() -> None:
    assert length_within("ok")
    assert not length_within("x" * 200)
