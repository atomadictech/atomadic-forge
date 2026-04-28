"""Tier a1 — pure helpers for config file I/O, merging, and validation."""

from __future__ import annotations

import json
from pathlib import Path

from atomadic_forge.a0_qk_constants.config_defaults import (
    CONFIG_FILE_NAME,
    DEFAULT_CONFIG,
    GLOBAL_CONFIG_DIR,
    LOCAL_CONFIG_DIR,
)


def read_config_file(path: Path) -> dict:
    """Read a JSON config file; return empty dict if missing or malformed."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_config(project_dir: Path) -> dict:
    """Load config with priority: local > global > defaults."""
    defaults = dict(DEFAULT_CONFIG)
    global_path = Path(GLOBAL_CONFIG_DIR).expanduser() / CONFIG_FILE_NAME
    local_path = project_dir / LOCAL_CONFIG_DIR / CONFIG_FILE_NAME

    global_cfg = read_config_file(global_path)
    local_cfg = read_config_file(local_path)
    return merge_configs(local_cfg, global_cfg, defaults)


def save_config(config: dict, path: Path) -> None:
    """Write config dict as pretty-printed JSON; create parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")


def merge_configs(local: dict, global_: dict, defaults: dict) -> dict:
    """Merge configs with priority local > global > defaults; None values are skipped."""
    merged = dict(defaults)
    merged.update({k: v for k, v in global_.items() if v is not None})
    merged.update({k: v for k, v in local.items() if v is not None})
    return merged


def validate_config(config: dict) -> list[str]:
    """Return a list of validation issues; empty list means the config is valid."""
    issues: list[str] = []

    valid_providers = {"auto", "ollama", "gemini", "anthropic", "openai", "stub"}
    provider = config.get("provider", "auto")
    if provider not in valid_providers:
        issues.append(
            f"Unknown provider {provider!r}; choose from {sorted(valid_providers)}"
        )

    score = config.get("default_target_score", 75.0)
    if not isinstance(score, (int, float)) or not (0 <= float(score) <= 100):
        issues.append("default_target_score must be a number between 0 and 100")

    ollama_url = config.get("ollama_url", "")
    if ollama_url and not str(ollama_url).startswith(("http://", "https://")):
        issues.append("ollama_url must start with http:// or https://")

    return issues
