"""Tier a1 — pluggable LLM client interface.

Forge is the architecture substrate.  An LLM is the generation engine.
This module defines the contract between the two: a single ``call(prompt,
system) -> str`` interface, plus four ready-to-use implementations:

* :class:`AnthropicClient` — Claude.  Reads ``ANTHROPIC_API_KEY``.
* :class:`OpenAIClient`    — GPT.    Reads ``OPENAI_API_KEY``.
* :class:`GeminiClient`    — Google AI Studio (free tier).  Reads ``GEMINI_API_KEY``.
* :class:`OllamaClient`    — local.  Talks to ``http://localhost:11434``.
* :class:`StubLLMClient`   — deterministic, used by tests and dry-runs.

The client is intentionally minimal — Forge feeds it structured feedback
from wire/certify/emergent and asks for code in return.  The LLM's job is
generation; Forge's job is keeping that generation in line with the
5-tier law.

Free-tier note: ``gemini-2.5-flash`` and ``gemini-2.0-flash`` are free at
Google AI Studio (15 RPM, ~1500 RPD).  Get a key at
https://aistudio.google.com/apikey then ``export GEMINI_API_KEY=…``.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Callable, Protocol


class LLMClient(Protocol):
    """Minimal contract every Forge LLM backend implements."""

    name: str

    def call(self, prompt: str, *, system: str = "",
             max_tokens: int = 4096, temperature: float = 0.2) -> str:
        ...


class StubLLMClient:
    """Deterministic stub for tests + offline runs.

    Configure with a ``responder(prompt, system) -> str`` callable, or pass
    a list of canned responses for sequential calls.
    """

    name = "stub"

    def __init__(self, *, responder: Callable[[str, str], str] | None = None,
                 canned: list[str] | None = None):
        self._responder = responder
        self._canned = list(canned or [])
        self._calls = 0

    def call(self, prompt: str, *, system: str = "",
             max_tokens: int = 4096, temperature: float = 0.2) -> str:
        self._calls += 1
        if self._responder is not None:
            return self._responder(prompt, system)
        if self._canned:
            return self._canned.pop(0) if self._canned else ""
        return f"# stub response (call #{self._calls})\n"

    @property
    def calls(self) -> int:
        return self._calls


class AnthropicClient:
    """Claude via the Messages API."""

    name = "anthropic"

    def __init__(self, *, model: str = "claude-3-5-sonnet-latest",
                 api_key_env: str = "ANTHROPIC_API_KEY"):
        self.model = model
        self._api_key_env = api_key_env

    def call(self, prompt: str, *, system: str = "",
             max_tokens: int = 4096, temperature: float = 0.2) -> str:
        api_key = os.environ.get(self._api_key_env, "")
        if not api_key:
            raise RuntimeError(
                f"{self._api_key_env} not set — cannot call Anthropic API"
            )
        body = json.dumps({
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system or "You are a coding assistant.",
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        # Concatenate text blocks; ignore tool-use blocks for this minimal client.
        return "".join(b.get("text", "") for b in data.get("content", [])
                        if b.get("type") == "text")


class OpenAIClient:
    """GPT via the Chat Completions API."""

    name = "openai"

    def __init__(self, *, model: str = "gpt-4o-mini",
                 api_key_env: str = "OPENAI_API_KEY"):
        self.model = model
        self._api_key_env = api_key_env

    def call(self, prompt: str, *, system: str = "",
             max_tokens: int = 4096, temperature: float = 0.2) -> str:
        api_key = os.environ.get(self._api_key_env, "")
        if not api_key:
            raise RuntimeError(
                f"{self._api_key_env} not set — cannot call OpenAI API"
            )
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body = json.dumps({
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        choices = data.get("choices") or []
        return choices[0]["message"]["content"] if choices else ""


class GeminiClient:
    """Google Gemini via the Generative Language API.

    Free-tier models confirmed working (verified live during dev):
      * ``gemini-2.5-flash``        — high-quality default (free tier)
      * ``gemini-2.0-flash``        — older, more stable on free tier
      * ``gemini-2.5-pro``          — better reasoning; check tier in AI Studio
      * ``gemini-3.1-pro-preview``  — newest; check tier in AI Studio

    Override the default via ``FORGE_GEMINI_MODEL=<id>`` env var.  Concrete
    rate limits live on your AI Studio dashboard:
    https://aistudio.google.com/rate-limit
    """

    name = "gemini"

    def __init__(self, *, model: str = "gemini-2.5-flash",
                 api_key_env: str = "GEMINI_API_KEY"):
        self.model = model
        self._api_key_env = api_key_env

    def call(self, prompt: str, *, system: str = "",
             max_tokens: int = 4096, temperature: float = 0.2) -> str:
        api_key = (os.environ.get(self._api_key_env)
                   or os.environ.get("GOOGLE_API_KEY")
                   or "")
        if not api_key:
            raise RuntimeError(
                f"{self._api_key_env} (or GOOGLE_API_KEY) not set — "
                "get a free key at https://aistudio.google.com/apikey"
            )
        body_dict: dict[str, object] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if system:
            body_dict["systemInstruction"] = {"parts": [{"text": system}]}
        body = json.dumps(body_dict).encode("utf-8")
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{self.model}:generateContent?key={api_key}")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"content-type": "application/json"},
            method="POST",
        )
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:400]
                if exc.code == 429:
                    raise RuntimeError(
                        "Gemini quota exceeded. Either: (1) wait for daily "
                        "reset, (2) use a different free key, or (3) fall "
                        "back to local generation with `--provider ollama`. "
                        f"Detail: {detail[:200]}"
                    ) from exc
                if exc.code in (500, 502, 503, 504):
                    # transient — retry with exponential backoff
                    last_error = RuntimeError(f"Gemini {exc.code}: {detail[:200]}")
                    import time
                    time.sleep(1.5 ** attempt)
                    continue
                raise RuntimeError(f"Gemini API error {exc.code}: {detail}") from exc
        else:
            raise last_error or RuntimeError("Gemini API: 3 retries exhausted")
        candidates = data.get("candidates") or []
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)


class OllamaClient:
    """Local Ollama daemon."""

    name = "ollama"

    def __init__(self, *, model: str = "qwen2.5-coder:7b",
                 base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def call(self, prompt: str, *, system: str = "",
             max_tokens: int = 4096, temperature: float = 0.2) -> str:
        body = json.dumps({
            "model": self.model,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
            "system": system,
            "prompt": prompt,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=body,
            headers={"content-type": "application/json"},
            method="POST",
        )
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=300) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "")
            except urllib.error.HTTPError as exc:
                if exc.code in (500, 502, 503, 504):
                    import time
                    last_exc = RuntimeError(f"Ollama {exc.code} at {self.base_url}")
                    time.sleep(2.0 * (attempt + 1))
                    continue
                raise RuntimeError(f"Ollama HTTP {exc.code}: {exc}") from exc
            except urllib.error.URLError as exc:
                raise RuntimeError(
                    f"Ollama unreachable at {self.base_url} — "
                    f"is `ollama serve` running? Detail: {exc}"
                ) from exc
        raise last_exc or RuntimeError("Ollama: 3 retries exhausted")


def resolve_default_client() -> LLMClient:
    """Pick a client based on which env var is set; fall back to stub.

    Resolution order (free-tier-friendly first):
      1. GEMINI_API_KEY / GOOGLE_API_KEY → GeminiClient (free tier)
      2. ANTHROPIC_API_KEY               → AnthropicClient
      3. OPENAI_API_KEY                  → OpenAIClient
      4. FORGE_OLLAMA=1                  → OllamaClient (local, free)
      5. otherwise                       → StubLLMClient (offline)
    """
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return GeminiClient(model=os.environ.get("FORGE_GEMINI_MODEL",
                                                   "gemini-2.5-flash"))
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicClient()
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAIClient()
    if os.environ.get("FORGE_OLLAMA"):
        return OllamaClient(model=os.environ.get("FORGE_OLLAMA_MODEL",
                                                  "qwen2.5-coder:7b"))
    return StubLLMClient()
