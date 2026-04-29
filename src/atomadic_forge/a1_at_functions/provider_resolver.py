"""Tier a1 — shared LLM provider resolver."""

from __future__ import annotations

import os

from .llm_client import (
    AAAANexusClient,
    AnthropicClient,
    GeminiClient,
    LLMClient,
    OllamaClient,
    OpenAIClient,
    OpenRouterClient,
    StubLLMClient,
    resolve_default_client,
)

PROVIDER_HELP = (
    "auto | nexus | aaaa-nexus | gemini | anthropic | openai | "
    "openrouter | ollama | stub"
)


def resolve_provider(name: str = "auto") -> LLMClient:
    """Resolve a user-facing provider name to an ``LLMClient`` instance."""
    provider = (name or "auto").lower()
    if provider == "stub":
        return StubLLMClient()
    if provider in ("nexus", "aaaa-nexus", "aaaa_nexus", "helix"):
        return AAAANexusClient()
    if provider in ("anthropic", "claude"):
        return AnthropicClient()
    if provider in ("gemini", "google"):
        return GeminiClient(model=os.environ.get("FORGE_GEMINI_MODEL",
                                                 "gemini-2.5-flash"))
    if provider in ("openai", "gpt"):
        return OpenAIClient()
    if provider in ("openrouter", "router"):
        return OpenRouterClient()
    if provider == "ollama":
        return OllamaClient(
            model=os.environ.get("FORGE_OLLAMA_MODEL", "qwen2.5-coder:7b"),
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
    if provider == "auto":
        return resolve_default_client()
    raise ValueError(f"unknown provider: {name!r}; expected {PROVIDER_HELP}")
