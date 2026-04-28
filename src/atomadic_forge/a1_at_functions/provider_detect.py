"""Tier a1 — pure helpers for LLM provider detection and connection testing."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request


def detect_ollama(url: str) -> dict:
    """Ping Ollama at url; return availability, model list, and latency."""
    t0 = time.monotonic()
    try:
        tags_url = f"{url.rstrip('/')}/api/tags"
        with urllib.request.urlopen(tags_url, timeout=5) as resp:
            data = json.loads(resp.read())
        models = [m["name"] for m in data.get("models", [])]
        latency_ms = int((time.monotonic() - t0) * 1000)
        return {"available": True, "models": models, "url": url, "latency_ms": latency_ms}
    except (urllib.error.URLError, OSError, json.JSONDecodeError, KeyError):
        return {"available": False, "models": [], "url": url, "latency_ms": 0}


def list_ollama_models(url: str) -> list[str]:
    """Return model names available from Ollama at url."""
    return detect_ollama(url)["models"]


def test_provider(provider: str, config: dict) -> dict:
    """Test an LLM provider connection; return {ok, model, error, latency_ms}."""
    t0 = time.monotonic()

    if provider == "ollama":
        return _test_ollama(config, t0)

    if provider == "gemini":
        return _test_gemini(config, t0)

    if provider in ("anthropic", "claude"):
        return _test_anthropic(config, t0)

    if provider in ("openai", "gpt"):
        return _test_openai(config, t0)

    if provider == "auto":
        return _test_auto(config, t0)

    if provider == "stub":
        return {"ok": True, "model": "stub", "error": None,
                "latency_ms": int((time.monotonic() - t0) * 1000)}

    return {"ok": False, "model": "none",
            "error": f"Unknown provider {provider!r}", "latency_ms": 0}


# ── private helpers ──────────────────────────────────────────────────────────

def _test_ollama(config: dict, t0: float) -> dict:
    url = config.get("ollama_url", "http://localhost:11434")
    model = config.get("ollama_model", "mistral:7b-instruct")
    info = detect_ollama(url)
    latency_ms = int((time.monotonic() - t0) * 1000)
    if not info["available"]:
        return {"ok": False, "model": model,
                "error": f"Ollama not reachable at {url}", "latency_ms": latency_ms}
    if model not in info["models"] and info["models"]:
        return {"ok": False, "model": model,
                "error": f"Model {model!r} not found (available: {info['models']})",
                "latency_ms": latency_ms}
    return {"ok": True, "model": model, "error": None, "latency_ms": latency_ms}


def _test_gemini(config: dict, t0: float) -> dict:
    key = config.get("gemini_key") or ""
    if not key:
        return {"ok": False, "model": "gemini-2.5-flash",
                "error": "gemini_key not set", "latency_ms": 0}
    try:
        req = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            ok = resp.status == 200
        return {"ok": ok, "model": "gemini-2.5-flash", "error": None,
                "latency_ms": int((time.monotonic() - t0) * 1000)}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "model": "gemini-2.5-flash",
                "error": f"HTTP {exc.code}", "latency_ms": int((time.monotonic() - t0) * 1000)}
    except (urllib.error.URLError, OSError) as exc:
        return {"ok": False, "model": "gemini-2.5-flash",
                "error": str(exc), "latency_ms": int((time.monotonic() - t0) * 1000)}


def _test_anthropic(config: dict, t0: float) -> dict:
    key = config.get("anthropic_key") or ""
    model = "claude-sonnet-4-6"
    if not key:
        return {"ok": False, "model": model, "error": "anthropic_key not set", "latency_ms": 0}
    try:
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/models",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            ok = resp.status == 200
        return {"ok": ok, "model": model, "error": None,
                "latency_ms": int((time.monotonic() - t0) * 1000)}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "model": model,
                "error": f"HTTP {exc.code}", "latency_ms": int((time.monotonic() - t0) * 1000)}
    except (urllib.error.URLError, OSError) as exc:
        return {"ok": False, "model": model,
                "error": str(exc), "latency_ms": int((time.monotonic() - t0) * 1000)}


def _test_openai(config: dict, t0: float) -> dict:
    key = config.get("openai_key") or ""
    model = "gpt-4o-mini"
    if not key:
        return {"ok": False, "model": model, "error": "openai_key not set", "latency_ms": 0}
    try:
        req = urllib.request.Request(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            ok = resp.status == 200
        return {"ok": ok, "model": model, "error": None,
                "latency_ms": int((time.monotonic() - t0) * 1000)}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "model": model,
                "error": f"HTTP {exc.code}", "latency_ms": int((time.monotonic() - t0) * 1000)}
    except (urllib.error.URLError, OSError) as exc:
        return {"ok": False, "model": model,
                "error": str(exc), "latency_ms": int((time.monotonic() - t0) * 1000)}


def _test_auto(config: dict, t0: float) -> dict:
    url = config.get("ollama_url", "http://localhost:11434")
    info = detect_ollama(url)
    if info["available"]:
        model = config.get("ollama_model", "mistral:7b-instruct")
        return {"ok": True, "model": f"ollama/{model}", "error": None,
                "latency_ms": int((time.monotonic() - t0) * 1000)}
    for p, key_field in (
        ("gemini", "gemini_key"),
        ("anthropic", "anthropic_key"),
        ("openai", "openai_key"),
    ):
        if config.get(key_field):
            return test_provider(p, config)
    return {"ok": False, "model": "none",
            "error": "No provider available (Ollama unreachable, no API keys set)",
            "latency_ms": int((time.monotonic() - t0) * 1000)}
