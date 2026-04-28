"""Tier a1 — pure helpers for mixed_pkg. May import a0 only."""

from mixed_pkg.a0_qk_constants import GREETING_PREFIX, MAX_NAME_LEN


def greet(name: str) -> str:
    """Return ``"hello, <name>"`` with a length cap. Pure."""
    safe = name[:MAX_NAME_LEN].strip() or "world"
    return f"{GREETING_PREFIX}, {safe}"


def length_within(name: str) -> bool:
    """Return True if the name is at most MAX_NAME_LEN characters. Pure."""
    return len(name) <= MAX_NAME_LEN
