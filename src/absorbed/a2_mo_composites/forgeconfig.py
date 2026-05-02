"""Tier a0 — config defaults and file-location constants for Atomadic Forge."""

from __future__ import annotations

from typing import TypedDict


class ForgeConfig(TypedDict, total=False):
    provider: str
    ollama_url: str
    ollama_model: str
    gemini_key: str | None
    anthropic_key: str | None
    openai_key: str | None
    default_target_score: float
    auto_apply: bool
    output_dir: str
    sources_dir: str
    package_prefix: str


DEFAULT_CONFIG: ForgeConfig = {
    "provider": "auto",
    "ollama_url": "http://localhost:11434",
    "ollama_model": "mistral:7b-instruct",
    "gemini_key": None,
    "anthropic_key": None,
    "openai_key": None,
    "default_target_score": 75.0,
    "auto_apply": False,
    "output_dir": "./forged",
    "sources_dir": "./sources",
    "package_prefix": "forged",
}

CONFIG_FILE_NAME = "config.json"
GLOBAL_CONFIG_DIR = "~/.atomadic-forge"
LOCAL_CONFIG_DIR = ".atomadic-forge"
