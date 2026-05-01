"""Tier a4 — `forge whoami` orchestration command.

Resolves the current Forge authentication state and prints (or returns
as JSON) the email, plan, source (env vs credentials.toml), and verify
result. Pairs with `forge login`: after a successful login, `whoami`
confirms the credential file is being read and the verify endpoint
agrees with what's there.

Why a dedicated verb (and MCP tool):
  * Agents need to ASK "am I authenticated and what's my plan?" without
    burning a real tool call. Today an agent that hits "subscription
    required" has no cheap follow-up — `whoami` is that follow-up.
  * Humans running into MCP gate failures need a one-liner that says
    exactly which key the gate read and where it came from.
  * `--json` makes it scriptable in CI / shell wrappers.
"""

from __future__ import annotations

import json as _json
import os
from pathlib import Path
from typing import Annotated

import typer

from ..a0_qk_constants.auth_constants import API_KEY_ENV
from ..a1_at_functions.forge_auth import (
    read_api_key_from_credentials_file,
    read_api_key_from_env,
)
from ..a2_mo_composites.forge_auth_client import ForgeAuthClient

CREDENTIALS_FILE = Path("~/.atomadic-forge/credentials.toml").expanduser()


def _resolve_key(env: dict[str, str], creds_path: Path) -> tuple[str | None, str]:
    """Return (api_key, source) using the same resolution order the MCP gate uses.

    source ∈ {"env", "credentials_file", "missing"}.
    """
    env_key = read_api_key_from_env(env)
    if env_key:
        return env_key, "env"
    file_key = read_api_key_from_credentials_file(creds_path)
    if file_key:
        return file_key, "credentials_file"
    return None, "missing"


app = typer.Typer(
    no_args_is_help=False,
    help="Show the current Forge authentication state — email, plan, source.",
)


@app.callback(invoke_without_command=True)
def whoami_cmd(
    json_out: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Emit the result as JSON for scripted consumers.",
        ),
    ] = False,
    no_verify: Annotated[
        bool,
        typer.Option(
            "--no-verify",
            help="Skip the network verify roundtrip; just report the key shape "
                 "and source (useful when the verify endpoint is offline).",
        ),
    ] = False,
) -> None:
    """Resolve and print the current Forge auth state."""
    env_dict = dict(os.environ)
    api_key, source = _resolve_key(env_dict, CREDENTIALS_FILE)

    if api_key is None:
        result: dict = {
            "ok": False,
            "source": "missing",
            "email": "",
            "plan": "",
            "reason": (
                "No Forge subscription key configured. Run "
                "`forge login` to capture one, or export "
                f"{API_KEY_ENV}=fk_live_… in the environment."
            ),
            "credentials_path": str(CREDENTIALS_FILE),
        }
        if json_out:
            typer.echo(_json.dumps(result, indent=2))
        else:
            typer.echo("")
            typer.secho("  ✗ Not logged in.", fg="red")
            typer.echo("")
            typer.echo("    Run `forge login` to capture a key, or export")
            typer.echo(f"    {API_KEY_ENV}=fk_live_…")
            typer.echo(f"    Credentials path: {CREDENTIALS_FILE}")
        raise typer.Exit(code=1)

    # We have a key. Mask it for display (show first 11 chars of fk_live_xxx).
    masked = api_key[:11] + ("…" if len(api_key) > 11 else "")

    email = ""
    plan = ""
    verify_ok = False
    verify_reason = "(verification skipped via --no-verify)"

    if not no_verify:
        client = ForgeAuthClient()
        try:
            verify = client.verify(api_key)
            verify_ok = bool(verify.get("ok"))
            email = str(verify.get("email", "") or "")
            plan = str(verify.get("plan", "") or "")
            verify_reason = str(verify.get("reason", "") or "")
        except Exception as exc:  # noqa: BLE001 — show offline status to the user
            verify_reason = f"verify endpoint unreachable: {exc!r}"

    result = {
        "ok": verify_ok or no_verify,
        "source": source,
        "key_prefix": masked,
        "email": email,
        "plan": plan,
        "verify_ok": verify_ok,
        "verify_reason": verify_reason,
        "credentials_path": str(CREDENTIALS_FILE),
        "env_var": API_KEY_ENV,
    }

    if json_out:
        typer.echo(_json.dumps(result, indent=2))
        if not result["ok"]:
            raise typer.Exit(code=1)
        return

    typer.echo("")
    if result["ok"]:
        typer.secho(
            f"  ✓ Logged in as {email or '(unknown email)'}"
            f"{f' · plan: {plan}' if plan else ''}",
            fg="green",
        )
    else:
        typer.secho(f"  ✗ Auth failed: {verify_reason}", fg="red")

    typer.echo(f"    key:    {masked}")
    typer.echo(f"    source: {source}")
    if source == "credentials_file":
        typer.echo(f"    file:   {CREDENTIALS_FILE}")
    elif source == "env":
        typer.echo(f"    env:    {API_KEY_ENV}")
    typer.echo("")

    if not result["ok"]:
        raise typer.Exit(code=1)
