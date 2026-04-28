"""Tier a3 — interactive 5-step setup wizard for Atomadic Forge configuration."""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

from atomadic_forge.a0_qk_constants.config_defaults import (
    CONFIG_FILE_NAME,
    DEFAULT_CONFIG,
    LOCAL_CONFIG_DIR,
)
from atomadic_forge.a1_at_functions.config_io import (
    load_config,
    save_config,
)
from atomadic_forge.a1_at_functions.provider_detect import (
    detect_ollama,
    test_provider,
)

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm, IntPrompt, Prompt
    from rich.table import Table
    _RICH = True
except ImportError:
    _RICH = False  # type: ignore[assignment]

_con: Console | None = Console() if _RICH else None  # type: ignore[type-arg]

_PROVIDER_MAP = {1: "ollama", 2: "gemini", 3: "anthropic", 4: "openai", 5: "auto"}
_PROVIDER_LABEL = {
    "ollama": "Ollama", "gemini": "Gemini", "anthropic": "Claude (Anthropic)",
    "openai": "OpenAI (GPT)", "auto": "Auto",
}


# ── display helpers ──────────────────────────────────────────────────────────

def _panel(title: str, lines: list[str]) -> None:
    if _RICH and _con:
        _con.print(Panel("\n".join(lines),
                         title=f"[bold cyan]{title}[/bold cyan]", expand=False))
    else:
        print(f"\n--- {title} ---")
        for line in lines:
            print(line)


def _prompt_str(prompt: str, default: str = "") -> str:
    if _RICH:
        return Prompt.ask(prompt, default=default)
    val = input(f"{prompt} [{default}]: ").strip()
    return val or default


def _prompt_int(prompt: str, default: int = 1) -> int:
    if _RICH:
        return IntPrompt.ask(prompt, default=default)
    raw = input(f"{prompt} [{default}]: ").strip()
    try:
        return int(raw)
    except ValueError:
        return default


def _prompt_confirm(prompt: str, default: bool = True) -> bool:
    if _RICH:
        return Confirm.ask(prompt, default=default)
    raw = input(f"{prompt} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes")


def _info(msg: str) -> None:
    if _RICH and _con:
        _con.print(f"  {msg}")
    else:
        print(f"  {msg}")


def _ok(msg: str) -> None:
    if _RICH and _con:
        _con.print(f"  [green]{msg}[/green]")
    else:
        print(f"  OK: {msg}")


def _warn(msg: str) -> None:
    if _RICH and _con:
        _con.print(f"  [yellow]{msg}[/yellow]")
    else:
        print(f"  Warning: {msg}")


# ── wizard steps ─────────────────────────────────────────────────────────────

def _step1_provider() -> str:
    """Step 1: LLM Provider selection."""
    _panel(
        "Atomadic Forge — Setup   [Step 1/5: LLM Provider]",
        [
            "[1] Ollama (local, free, private)",
            "[2] Gemini (Google)",
            "[3] Claude (Anthropic)",
            "[4] OpenAI (GPT)",
            "[5] Auto (detect best available)",
        ],
    )
    choice = _prompt_int("Select provider", default=5)
    return _PROVIDER_MAP.get(choice, "auto")


def _step2_model(provider: str, config: dict) -> dict:
    """Step 2: Model selection; returns config key updates."""
    updates: dict = {}

    if provider == "ollama":
        url = config.get("ollama_url", DEFAULT_CONFIG["ollama_url"])
        _info(f"Checking Ollama at [cyan]{url}[/cyan]..." if _RICH else f"Checking Ollama at {url}...")
        info = detect_ollama(url)

        if not info["available"]:
            new_url = _prompt_str("  Ollama URL", default=url)
            updates["ollama_url"] = new_url
            info = detect_ollama(new_url)
        else:
            updates["ollama_url"] = url

        if info["available"] and info["models"]:
            lines = [f"  Ollama detected at {info['url']}", "  Available models:"]
            for i, m in enumerate(info["models"][:8], 1):
                lines.append(f"    [{i}] {m}")
            _panel("Step 2/5: Model Selection", lines)
            choice = _prompt_int("  Select model", default=1)
            idx = max(0, min(choice - 1, len(info["models"]) - 1))
            updates["ollama_model"] = info["models"][idx]
        else:
            _warn("Ollama not reachable — using default model")
            updates["ollama_model"] = config.get("ollama_model", DEFAULT_CONFIG["ollama_model"])

    elif provider == "gemini":
        _panel("Step 2/5: Model Selection", [
            "  Gemini models:",
            "    [1] gemini-2.5-flash (recommended — free tier)",
            "    [2] gemini-2.5-pro",
        ])
        choice = _prompt_int("  Select model", default=1)
        updates["gemini_model"] = {1: "gemini-2.5-flash", 2: "gemini-2.5-pro"}.get(choice, "gemini-2.5-flash")

    elif provider in ("anthropic", "claude"):
        _panel("Step 2/5: Model Selection", [
            "  Claude models:",
            "    [1] claude-sonnet-4-6 (recommended)",
            "    [2] claude-opus-4-7",
            "    [3] claude-haiku-4-5-20251001 (fastest)",
        ])
        choice = _prompt_int("  Select model", default=1)
        updates["anthropic_model"] = {
            1: "claude-sonnet-4-6",
            2: "claude-opus-4-7",
            3: "claude-haiku-4-5-20251001",
        }.get(choice, "claude-sonnet-4-6")

    elif provider in ("openai", "gpt"):
        _panel("Step 2/5: Model Selection", [
            "  OpenAI models:",
            "    [1] gpt-4o-mini (recommended — cost-effective)",
            "    [2] gpt-4o",
        ])
        choice = _prompt_int("  Select model", default=1)
        updates["openai_model"] = {1: "gpt-4o-mini", 2: "gpt-4o"}.get(choice, "gpt-4o-mini")

    else:  # auto
        _panel("Step 2/5: Model Selection", [
            "  Auto mode: Forge picks the best available provider automatically.",
            "  Priority: Ollama (local, free) → Gemini → Anthropic → OpenAI",
        ])

    return updates


def _step3_api_key(provider: str, config: dict) -> dict:
    """Step 3: API key input for cloud providers (skipped for Ollama/auto)."""
    cloud = {"gemini": ("gemini_key", "aistudio.google.com/app/apikey"),
             "anthropic": ("anthropic_key", "console.anthropic.com"),
             "openai": ("openai_key", "platform.openai.com/api-keys")}
    if provider not in cloud:
        return {}

    key_field, url = cloud[provider]
    existing = config.get(key_field) or ""
    _panel(f"Step 3/5: API Key — {_PROVIDER_LABEL.get(provider, provider)}", [
        f"  Get your key at: {url}",
        "  (press Enter to keep existing key; leave blank to skip)",
    ])

    if existing:
        masked = existing[:8] + "..." + existing[-4:] if len(existing) > 12 else "***"
        keep = _prompt_confirm(f"  Keep existing key ({masked})?", default=True)
        if keep:
            return {}

    raw = getpass.getpass(f"  Paste your {_PROVIDER_LABEL.get(provider, provider)} API key: ").strip()
    if not raw:
        return {}

    updates = {key_field: raw}
    _info("Validating key...")
    result = test_provider(provider, {**config, **updates})
    if result["ok"]:
        _ok(f"Key valid ({result['latency_ms']}ms)")
    else:
        _warn(f"Validation warning: {result['error']}")
    return updates


def _step4_project_defaults(config: dict) -> dict:
    """Step 4: Target score, auto-apply, and directory defaults."""
    _panel("Step 4/5: Project Defaults", [
        "  Configure default behaviour for forge commands.",
    ])
    updates: dict = {}

    cur_score = config.get("default_target_score", DEFAULT_CONFIG["default_target_score"])
    raw = _prompt_str("  Default target score (0–100)", default=str(cur_score))
    try:
        updates["default_target_score"] = float(raw)
    except ValueError:
        updates["default_target_score"] = float(cur_score)

    cur_auto = bool(config.get("auto_apply", DEFAULT_CONFIG["auto_apply"]))
    updates["auto_apply"] = _prompt_confirm(
        "  Auto-apply by default (skip --apply flag)?", default=cur_auto
    )

    cur_out = config.get("output_dir", DEFAULT_CONFIG["output_dir"])
    updates["output_dir"] = _prompt_str("  Output directory", default=cur_out)

    cur_src = config.get("sources_dir", DEFAULT_CONFIG["sources_dir"])
    updates["sources_dir"] = _prompt_str("  Sources directory", default=cur_src)

    cur_prefix = config.get("package_prefix", DEFAULT_CONFIG["package_prefix"])
    updates["package_prefix"] = _prompt_str("  Default package prefix", default=cur_prefix)

    return updates


def _step5_verify_and_save(final_config: dict, project_dir: Path, config_path: Path) -> dict:
    """Step 5: Test LLM connection, save config, print summary."""
    _panel("Step 5/5: Verification", ["  Testing LLM connection and saving config..."])

    provider = final_config.get("provider", "auto")
    test_result = test_provider(provider, final_config)
    python_ver = f"{sys.version_info.major}.{sys.version_info.minor}"

    save_config(final_config, config_path)

    try:
        rel_path = config_path.relative_to(project_dir)
    except ValueError:
        rel_path = config_path  # type: ignore[assignment]

    model = test_result.get("model", "unknown")
    target_score = final_config.get("default_target_score", DEFAULT_CONFIG["default_target_score"])
    auto_apply = final_config.get("auto_apply", DEFAULT_CONFIG["auto_apply"])
    output_dir = final_config.get("output_dir", DEFAULT_CONFIG["output_dir"])
    sources_dir = final_config.get("sources_dir", DEFAULT_CONFIG["sources_dir"])
    ollama_url = final_config.get("ollama_url", DEFAULT_CONFIG["ollama_url"])

    llm_ok = test_result["ok"]
    llm_line = (
        f"✓ LLM connection tested — OK ({test_result['latency_ms']}ms)"
        if llm_ok
        else f"✗ LLM: {test_result.get('error', 'failed')}"
    )

    if _RICH and _con:
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Key", style="bold")
        table.add_column("Value")
        table.add_row("Provider:", _PROVIDER_LABEL.get(provider, provider))
        table.add_row("Model:", model)
        if provider == "ollama":
            table.add_row("URL:", ollama_url)
        table.add_row("Target Score:", f"{target_score}/100")
        table.add_row("Auto-Apply:", "Yes" if auto_apply else "No (dry-run by default)")
        table.add_row("Output Dir:", output_dir)
        table.add_row("Sources Dir:", sources_dir)
        table.add_row("Config File:", str(rel_path))
        _con.print()
        _con.print(Panel(table, title="[bold green]Configuration Summary[/bold green]",
                         expand=False))
        color = "green" if llm_ok else "yellow"
        _con.print(f"\n  [{color}]{llm_line}[/{color}]")
        _con.print(f"  [green]✓ Python {python_ver} detected[/green]")
        _con.print(f"  [green]✓ Config saved to {rel_path}[/green]\n")
    else:
        print("\n--- Configuration Summary ---")
        print(f"  Provider:      {_PROVIDER_LABEL.get(provider, provider)}")
        print(f"  Model:         {model}")
        if provider == "ollama":
            print(f"  URL:           {ollama_url}")
        print(f"  Target Score:  {target_score}/100")
        print(f"  Auto-Apply:    {'Yes' if auto_apply else 'No (dry-run by default)'}")
        print(f"  Output Dir:    {output_dir}")
        print(f"  Sources Dir:   {sources_dir}")
        print(f"  Config File:   {rel_path}")
        print(f"\n  {llm_line}")
        print(f"  Python {python_ver} detected")
        print(f"  Config saved to {rel_path}")

    return {"test": test_result, "config_path": str(config_path)}


# ── public entry point ────────────────────────────────────────────────────────

def run_wizard(project_dir: Path) -> dict:
    """Run all 5 wizard steps interactively and return the final saved config."""
    config: dict = dict(load_config(project_dir))

    config["provider"] = _step1_provider()
    config.update(_step2_model(config["provider"], config))
    config.update(_step3_api_key(config["provider"], config))
    config.update(_step4_project_defaults(config))

    config_path = project_dir / LOCAL_CONFIG_DIR / CONFIG_FILE_NAME
    _step5_verify_and_save(config, project_dir, config_path)

    return config
