"""Tier a1 — pluggable LLM client interface.

Forge is the architecture substrate.  An LLM is the generation engine.
This module defines the contract between the two: a single ``call(prompt,
system) -> str`` interface, plus several ready-to-use implementations:

* :class:`AnthropicClient`  — Claude.  Reads ``ANTHROPIC_API_KEY``.
* :class:`OpenAIClient`     — GPT.    Reads ``OPENAI_API_KEY``.
* :class:`GeminiClient`     — Google AI Studio (free tier).  Reads ``GEMINI_API_KEY``.
* :class:`AAAANexusClient`  — AAAA-Nexus inference (Cloudflare-Workers-AI
  upstream, BitNet/HELIX wrappers, built-in hallucination guard).  Reads
  ``AAAA_NEXUS_API_KEY``.  Each call is billed at $0.015 by the upstream
  Nexus account — usage drives revenue while passing through the
  anti-hallucination trust gate on every response.
* :class:`OllamaClient`     — local.  Talks to ``http://localhost:11434``.
* :class:`StubLLMClient`    — deterministic, used by tests and dry-runs.

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
from collections.abc import Callable
from typing import Protocol


class LLMClient(Protocol):
    """Minimal contract every Forge LLM backend implements."""

    name: str

    def call(self, prompt: str, *, system: str = "",
             max_tokens: int = 4096, temperature: float = 0.2) -> str:
        ...


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int | None) -> int | None:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


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


class AAAANexusClient:
    """AAAA-Nexus inference — Cloudflare-Workers-AI upstream with HELIX guards.

    Hits ``POST /v1/inference`` on the public Nexus Worker.  Every call:

    * Goes through the anti-hallucination trust gate (returns confidence,
      flagged-bool, trust-floor metadata in ``helix.anti_hallucination``).
    * Is billed at $0.015 against the Nexus account that owns the API
      key, so Forge usage drives Nexus revenue automatically.
    * Falls back internally on the upstream side: AAAA_LLM service
      binding → Cloudflare Workers AI REST.  No client-side fallback
      logic needed.

    Configuration:
      * ``AAAA_NEXUS_API_KEY`` — required Bearer token.
      * ``AAAA_NEXUS_URL``     — override base URL (default: the public
                                  Atomadic-Tech worker).
      * ``AAAA_NEXUS_WRAPPER`` — choose ``helix-standard`` (default),
                                  ``bitnet-standard``, or any wrapper
                                  exposed by ``GET /v1/agents/capabilities``.

    The response shape is OpenAI-compatible — ``choices[0].message.content``
    is the only field Forge reads.  HELIX/BitNet metadata (compression,
    confidence, trust floor) is preserved on the raw response but not
    returned by ``call()``; callers wanting that signal can subclass.
    """

    name = "aaaa-nexus"

    DEFAULT_BASE_URL = "https://aaaa-nexus.atomadictech.workers.dev"
    WRAPPER_PATHS = {
        "helix-standard":  "/v1/inference",
        "helix-stream":    "/v1/inference/stream",
        "bitnet-standard": "/v1/bitnet/inference",
        "bitnet-stream":   "/v1/bitnet/inference/stream",
    }

    def __init__(self, *, base_url: str | None = None,
                 api_key_env: str = "AAAA_NEXUS_API_KEY",
                 wrapper: str | None = None):
        self.base_url = (base_url
                         or os.environ.get("AAAA_NEXUS_URL")
                         or self.DEFAULT_BASE_URL).rstrip("/")
        self._api_key_env = api_key_env
        self.wrapper = (wrapper
                        or os.environ.get("AAAA_NEXUS_WRAPPER")
                        or "helix-standard")
        if self.wrapper not in self.WRAPPER_PATHS:
            raise ValueError(
                f"unknown AAAA-Nexus wrapper: {self.wrapper!r} — expected "
                f"one of {list(self.WRAPPER_PATHS)}"
            )

    def call(self, prompt: str, *, system: str = "",
             max_tokens: int = 4096, temperature: float = 0.2) -> str:
        api_key = os.environ.get(self._api_key_env, "")
        if not api_key:
            raise RuntimeError(
                f"{self._api_key_env} not set — cannot call AAAA-Nexus inference"
            )
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        # The Nexus inference endpoint validates the body strictly — only
        # ``messages`` is on the public schema today, extra fields like
        # ``max_tokens`` / ``temperature`` get a 403.  Keep the payload
        # minimal; upstream picks reasonable defaults for the wrapper.
        body = json.dumps({"messages": messages}).encode("utf-8")
        endpoint = self.base_url + self.WRAPPER_PATHS[self.wrapper]
        req = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                # AAAA-Nexus auth: the storefront worker reads ``X-API-Key``
                # (NOT ``Authorization: Bearer``) and matches against keys
                # registered in NONCE_CACHE KV.  Sending only Bearer falls
                # through to the 3-call/day/IP trial path with HTTP 402.
                # We send both headers so the same client also works against
                # any future Bearer-style endpoint without a code change.
                "X-API-Key": api_key,
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                # Cloudflare Worker WAF rejects urllib's default UA
                # ("Python-urllib/3.x") with a 403.  Identify ourselves
                # explicitly so the request looks like a real client.
                "User-Agent": "atomadic-forge/0.2 (AAAANexusClient)",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        # If the upstream's hallucination guard flagged the response with
        # very low confidence, surface it as a runtime warning — the loop
        # will likely produce a poor file emit and we want the signal in
        # logs rather than silently passing through.
        helix = data.get("helix") or {}
        ah = helix.get("anti_hallucination") or {}
        if ah.get("flagged") and ah.get("confidence", 1.0) < 0.3:
            # Soft warning — Forge's certify gate will catch quality issues
            # downstream; we just emit a stderr breadcrumb here.
            import sys as _sys
            print(
                f"[aaaa-nexus] anti-hallucination flagged response "
                f"(confidence={ah.get('confidence'):.3f}, "
                f"trust_floor={ah.get('trust_floor'):.3f})",
                file=_sys.stderr,
            )
        choices = data.get("choices") or []
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "") or ""


class OllamaClient:
    """Local Ollama daemon."""

    name = "ollama"

    def __init__(self, *, model: str = "qwen2.5-coder:7b",
                 base_url: str = "http://localhost:11434",
                 timeout_s: float | None = None,
                 num_predict: int | None = None):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s if timeout_s is not None else _env_float(
            "FORGE_OLLAMA_TIMEOUT", 300.0
        )
        self.num_predict = num_predict if num_predict is not None else _env_int(
            "FORGE_OLLAMA_NUM_PREDICT", None
        )

    def call(self, prompt: str, *, system: str = "",
             max_tokens: int = 4096, temperature: float = 0.2) -> str:
        num_predict = self.num_predict if self.num_predict is not None else max_tokens
        body = json.dumps({
            "model": self.model,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max(1, num_predict)},
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
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
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
            except TimeoutError as exc:
                raise RuntimeError(
                    f"Ollama timed out after {self.timeout_s:g}s while using "
                    f"model {self.model!r}. Try a smaller local model, set "
                    "`FORGE_OLLAMA_NUM_PREDICT` lower, or raise "
                    "`FORGE_OLLAMA_TIMEOUT`."
                ) from exc
        raise last_exc or RuntimeError("Ollama: 3 retries exhausted")


class OpenRouterClient:
    """OpenRouter — routes to 200+ models via OpenAI-compatible API.

    Reads ``OPENROUTER_API_KEY``.  Default model: ``deepseek/deepseek-chat-v3-0324:free``
    (free tier).  Override via ``FORGE_OPENROUTER_MODEL`` env var.
    """

    name = "openrouter"

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, *, model: str | None = None,
                 api_key_env: str = "OPENROUTER_API_KEY"):
        self.model = (model
                      or os.environ.get("FORGE_OPENROUTER_MODEL")
                      or "google/gemma-3-27b-it:free")
        self._api_key_env = api_key_env

    def call(self, prompt: str, *, system: str = "",
             max_tokens: int = 4096, temperature: float = 0.2) -> str:
        api_key = os.environ.get(self._api_key_env, "")
        if not api_key:
            raise RuntimeError(
                f"{self._api_key_env} not set — cannot call OpenRouter API"
            )
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body_dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        last_error: Exception | None = None
        for attempt in range(3):
            body = json.dumps(body_dict).encode("utf-8")
            req = urllib.request.Request(
                self.BASE_URL,
                data=body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://atomadic.tech",
                    "X-Title": "Atomadic Forge",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:600]
                if exc.code == 400 and "instruction" in detail.lower() and attempt == 0:
                    # Model doesn't support system role — fold it into user turn.
                    merged = f"[System instructions]\n{system}\n\n[User]\n{prompt}" if system else prompt
                    body_dict = {
                        "model": self.model,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "messages": [{"role": "user", "content": merged}],
                    }
                    continue
                if exc.code == 429:
                    import time
                    last_error = RuntimeError(f"OpenRouter 429: {detail[:200]}")
                    time.sleep(2.0 * (attempt + 1))
                    continue
                if exc.code in (500, 502, 503, 504):
                    import time
                    last_error = RuntimeError(f"OpenRouter {exc.code}: {detail[:200]}")
                    time.sleep(1.5 ** attempt)
                    continue
                raise RuntimeError(f"OpenRouter API error {exc.code}: {detail}") from exc
        else:
            raise last_error or RuntimeError("OpenRouter API: 3 retries exhausted")
        choices = data.get("choices") or []
        return choices[0]["message"]["content"] if choices else ""


def resolve_default_client() -> LLMClient:
    """Pick a client based on which env var is set; fall back to stub.

    Resolution order (sovereign-revenue-first → free-tier → paid → local):
      1. AAAA_NEXUS_API_KEY              → AAAANexusClient (every call
                                            bills upstream Nexus account
                                            $0.015 with built-in
                                            hallucination guard)
      2. ANTHROPIC_API_KEY               → AnthropicClient
      3. GEMINI_API_KEY / GOOGLE_API_KEY → GeminiClient (free tier)
      4. OPENAI_API_KEY                  → OpenAIClient
      5. FORGE_OLLAMA=1                  → OllamaClient (local, free)
      6. otherwise                       → StubLLMClient (offline)

    AAAA-Nexus comes first because it's the only path that simultaneously
    (a) generates revenue for the operator, (b) trust-gates every response
    through the HELIX anti-hallucination layer, and (c) records the call
    in the Nexus audit log automatically.
    """
    if os.environ.get("AAAA_NEXUS_API_KEY"):
        return AAAANexusClient()
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicClient()
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return GeminiClient(model=os.environ.get("FORGE_GEMINI_MODEL",
                                                   "gemini-2.5-flash"))
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAIClient()
    if os.environ.get("OPENROUTER_API_KEY"):
        return OpenRouterClient()
    if os.environ.get("FORGE_OLLAMA"):
        return OllamaClient(model=os.environ.get("FORGE_OLLAMA_MODEL",
                                                  "qwen2.5-coder:7b"),
                            base_url=os.environ.get("OLLAMA_BASE_URL",
                                                    "http://localhost:11434"))
    return StubLLMClient()
