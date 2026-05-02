"""``forge chat`` — chat copilot over Forge + optional repo context."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import click
import typer

from atomadic_forge.a1_at_functions.chat_context import (
    build_chat_context,
    chat_system_prompt,
    render_chat_prompt,
)
from atomadic_forge.a1_at_functions.provider_resolver import (
    PROVIDER_HELP,
    resolve_provider,
)

COMMAND_NAME = "chat"
COMMAND_HELP = "Chat with a Forge-aware AI copilot over optional repo context."


app = typer.Typer(no_args_is_help=True, help=COMMAND_HELP)


def _provider(name: str):
    try:
        return resolve_provider(name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


def _context_paths(context: list[Path] | None, cwd_context: bool) -> list[Path]:
    if context:
        return context
    return [Path.cwd()] if cwd_context else []


@app.command("ask")
def ask_cmd(
    message: Annotated[str, typer.Argument(help="Question or request for the copilot.")],
    provider: Annotated[str, typer.Option("--provider",
        help=PROVIDER_HELP)] = "auto",
    context: Annotated[list[Path] | None, typer.Option("--context", "-c",
        exists=True, file_okay=True, dir_okay=True, resolve_path=True,
        help="File or directory to include as bounded context. Repeatable.")] = None,
    cwd_context: Annotated[bool, typer.Option("--cwd-context/--no-cwd-context",
        help="Use the current directory as context when --context is omitted.")] = True,
    max_files: Annotated[int, typer.Option("--max-files",
        help="Maximum files to pack into the chat context.")] = 12,
    max_chars: Annotated[int, typer.Option("--max-chars",
        help="Maximum context characters sent to the provider.")] = 16_000,
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Ask one copilot question and print the answer."""
    llm = _provider(provider)
    ctx = build_chat_context(
        _context_paths(context, cwd_context),
        cwd=Path.cwd(),
        max_files=max_files,
        max_chars=max_chars,
    )
    prompt = render_chat_prompt(message, context=ctx["context"])
    try:
        answer = llm.call(prompt, system=chat_system_prompt())
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    if json_out:
        typer.echo(json.dumps({
            "schema_version": "atomadic-forge.chat/v1",
            "provider": llm.name,
            "message": message,
            "answer": answer,
            "context": {
                "file_count": ctx["file_count"],
                "char_count": ctx["char_count"],
                "files": ctx["files"],
            },
        }, indent=2, default=str))
        return
    typer.echo(answer.rstrip())


@app.command("repl")
def repl_cmd(
    provider: Annotated[str, typer.Option("--provider",
        help=PROVIDER_HELP)] = "auto",
    context: Annotated[list[Path] | None, typer.Option("--context", "-c",
        exists=True, file_okay=True, dir_okay=True, resolve_path=True,
        help="File or directory to include as bounded context. Repeatable.")] = None,
    cwd_context: Annotated[bool, typer.Option("--cwd-context/--no-cwd-context",
        help="Use the current directory as context when --context is omitted.")] = True,
    max_files: Annotated[int, typer.Option("--max-files")] = 12,
    max_chars: Annotated[int, typer.Option("--max-chars")] = 16_000,
) -> None:
    """Start an interactive copilot session. Type ``/exit`` to leave."""
    llm = _provider(provider)
    ctx = build_chat_context(
        _context_paths(context, cwd_context),
        cwd=Path.cwd(),
        max_files=max_files,
        max_chars=max_chars,
    )
    typer.echo(f"Forge chat copilot ({llm.name}). Type /exit to leave.")
    if ctx["file_count"]:
        typer.echo(f"Context: {ctx['file_count']} file(s), {ctx['char_count']} chars.")
    history: list[dict[str, str]] = []
    while True:
        try:
            message = typer.prompt("you").strip()
        except (EOFError, KeyboardInterrupt):
            typer.echo("")
            break
        if message.lower() in {"/exit", "/quit", "exit", "quit", ":q"}:
            break
        if not message:
            continue
        prompt = render_chat_prompt(message, context=ctx["context"], history=history)
        try:
            answer = llm.call(prompt, system=chat_system_prompt()).rstrip()
        except RuntimeError as exc:
            typer.secho(f"Provider error: {exc}", fg=typer.colors.RED, err=True)
            continue
        typer.echo("")
        typer.echo(answer)
        typer.echo("")
        history.extend([
            {"role": "user", "content": message},
            {"role": "assistant", "content": answer},
        ])
