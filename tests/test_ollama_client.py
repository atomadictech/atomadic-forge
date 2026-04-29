"""Tests for the local Ollama LLM client."""

from __future__ import annotations

import json
import urllib.request

import pytest

from atomadic_forge.a1_at_functions.llm_client import OllamaClient


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps({"response": "ok"}).encode("utf-8")


def test_ollama_client_sends_configurable_timeout_and_token_budget(monkeypatch):
    captured: dict = {}

    def _fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["timeout"] = timeout
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
    client = OllamaClient(
        model="local-model:8b",
        base_url="http://ollama.local/",
        timeout_s=12.5,
        num_predict=256,
    )

    assert client.call("hello", system="be useful") == "ok"
    assert captured["url"] == "http://ollama.local/api/generate"
    assert captured["timeout"] == 12.5
    assert captured["body"]["model"] == "local-model:8b"
    assert captured["body"]["system"] == "be useful"
    assert captured["body"]["options"]["num_predict"] == 256


def test_ollama_client_reads_timeout_and_token_budget_from_env(monkeypatch):
    captured: dict = {}

    def _fake_urlopen(req, timeout=None):
        captured["timeout"] = timeout
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _FakeResponse()

    monkeypatch.setenv("FORGE_OLLAMA_TIMEOUT", "45")
    monkeypatch.setenv("FORGE_OLLAMA_NUM_PREDICT", "128")
    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)

    assert OllamaClient(model="m").call("hello", max_tokens=999) == "ok"
    assert captured["timeout"] == 45.0
    assert captured["body"]["options"]["num_predict"] == 128


def test_ollama_timeout_raises_actionable_error(monkeypatch):
    def _timeout(req, timeout=None):
        raise TimeoutError("slow model")

    monkeypatch.setattr(urllib.request, "urlopen", _timeout)
    client = OllamaClient(model="qwen3:8b", timeout_s=1)

    with pytest.raises(RuntimeError, match="Ollama timed out after 1s"):
        client.call("hello")
