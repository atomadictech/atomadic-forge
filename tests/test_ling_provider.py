"""Tests for the Ling-2.6-1T / OpenRouter provider wiring."""

from __future__ import annotations

from atomadic_forge.a1_at_functions.llm_client import OpenRouterClient
from atomadic_forge.a1_at_functions.provider_resolver import (
    PROVIDER_HELP,
    resolve_provider,
)


def test_openrouter_default_model_is_ling():
    client = OpenRouterClient()
    assert client.model == "inclusionai/ling-2.6-1t:free"


def test_openrouter_alias_router_resolves():
    assert isinstance(resolve_provider("openrouter"), OpenRouterClient)
    assert isinstance(resolve_provider("router"), OpenRouterClient)


def test_ling_provider_resolves_to_openrouter_with_ling_model():
    client = resolve_provider("ling")
    assert isinstance(client, OpenRouterClient)
    assert client.model == "inclusionai/ling-2.6-1t:free"


def test_provider_help_lists_ling():
    assert "ling" in PROVIDER_HELP
    assert "openrouter" in PROVIDER_HELP


def test_unknown_provider_raises():
    import pytest
    with pytest.raises(ValueError):
        resolve_provider("not-a-real-provider")
