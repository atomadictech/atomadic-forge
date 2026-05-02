"""Tier a4 — `forge` CLI parity for the Codex 'Copilot's Copilot' surface.

These verbs were already exposed via MCP (tools/call) but had no CLI
front-door. That gap meant a developer or agent shell-running `forge`
couldn't sample the same intelligence the MCP exposes — they had to
spawn the MCP server, speak JSON-RPC, and parse `content[0].text`.

This module surfaces every MCP-only tool as a top-level CLI verb that
prints JSON to stdout, suitable for piping into jq, scripts, or an
agent's Bash subprocess. Each verb is a thin a4 orchestrator around
the a1 implementation — no business logic lives here.

Verbs added:
  * forge explain-repo <project_root>      — Codex #6 humane orientation
  * forge score-patch                      — Codex #3 patch risk scorer (diff on stdin or --file)
  * forge select-tests <project_root>      — Codex #7 minimum + full-confidence test sets
  * forge rollback-plan <project_root>     — Codex #11 structured undo plan
  * forge compose-tools <goal>             — Codex #9 tool-use planner (goal keyword)
  * forge why-did-this-change <file>       — Codex #5 lineage history for a file
  * forge what-failed-last-time <area>     — Codex #5 failures matching an area substring
  * forge adapt-plan                       — Codex #8 capability-aware card filtering (plan on stdin/--file)
  * forge load-policy <project_root>       — Codex #10 [tool.forge.agent] reader

All verbs default to printing JSON. None mutate the repo.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Annotated

import typer

from ..a1_at_functions.agent_memory import (
    what_failed_last_time as _what_failed_last_time,
)
from ..a1_at_functions.agent_memory import why_did_this_change as _why_did_this_change
from ..a1_at_functions.patch_scorer import score_patch as _score_patch
from ..a1_at_functions.plan_adapter import adapt_plan as _adapt_plan
from ..a1_at_functions.policy_loader import load_policy as _load_policy
from ..a1_at_functions.repo_explainer import explain_repo as _explain_repo
from ..a1_at_functions.rollback_planner import rollback_plan as _rollback_plan
from ..a1_at_functions.test_selector import select_tests as _select_tests
from ..a1_at_functions.tool_composer import compose_tools as _compose_tools


def _to_jsonable(obj: object) -> object:
    """Convert dataclasses, Paths, sets to JSON-serializable form."""
    if is_dataclass(obj):
        return asdict(obj)  # type: ignore[arg-type]
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    return obj


def _emit(result: object) -> None:
    """Print JSON to stdout. Used by every verb in this module."""
    typer.echo(json.dumps(_to_jsonable(result), indent=2, default=str))


def _read_stdin_or_file(file: Path | None) -> str:
    if file is not None:
        return Path(file).read_text(encoding="utf-8")
    if sys.stdin.isatty():
        raise typer.BadParameter(
            "no input on stdin and --file not given. Pipe a diff via stdin or pass --file path.txt"
        )
    return sys.stdin.read()


# ---- Top-level Typer apps (one per verb) -------------------------------

explain_app = typer.Typer(no_args_is_help=False, help="Codex #6 — humane operational orientation.")
score_app = typer.Typer(no_args_is_help=False, help="Codex #3 — patch risk scorer.")
tests_app = typer.Typer(no_args_is_help=False, help="Codex #7 — minimum + full-confidence test sets.")
rollback_app = typer.Typer(no_args_is_help=False, help="Codex #11 — structured undo plan.")
compose_app = typer.Typer(no_args_is_help=False, help="Codex #9 — tool-use planner.")
why_app = typer.Typer(no_args_is_help=False, help="Codex #5 — agent memory: lineage for a file.")
failed_app = typer.Typer(no_args_is_help=False, help="Codex #5 — failed events matching an area.")
adapt_app = typer.Typer(no_args_is_help=False, help="Codex #8 — capability-aware card filtering.")
policy_app = typer.Typer(no_args_is_help=False, help="Codex #10 — read [tool.forge.agent] policy.")


@explain_app.callback(invoke_without_command=True)
def explain_repo_cmd(
    project_root: Annotated[
        Path,
        typer.Argument(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    ] = Path("."),
    depth: Annotated[str, typer.Option("--depth")] = "agent",
) -> None:
    _emit(_explain_repo(project_root=project_root, depth=depth))


@score_app.callback(invoke_without_command=True)
def score_patch_cmd(
    file: Annotated[
        Path | None,
        typer.Option(
            "--file", "-f",
            help="Read the unified diff from this file. Without --file, reads from stdin.",
        ),
    ] = None,
    project_root: Annotated[
        Path,
        typer.Option("--project-root", "-p", exists=True, file_okay=False, resolve_path=True),
    ] = Path("."),
) -> None:
    diff = _read_stdin_or_file(file)
    _emit(_score_patch(diff, project_root=project_root))


@tests_app.callback(invoke_without_command=True)
def select_tests_cmd(
    intent: Annotated[str, typer.Argument(help="One-line description of the intent.")] ,
    files: Annotated[
        list[str],
        typer.Option(
            "--file", "-f",
            help="Repeat for each changed file. Example: --file src/a/b.py --file src/a/c.py",
        ),
    ] = [],
    project_root: Annotated[
        Path,
        typer.Option("--project-root", "-p", exists=True, file_okay=False, resolve_path=True),
    ] = Path("."),
) -> None:
    _emit(_select_tests(
        intent=intent,
        changed_files=list(files),
        project_root=project_root,
    ))


@rollback_app.callback(invoke_without_command=True)
def rollback_plan_cmd(
    files: Annotated[
        list[str],
        typer.Option(
            "--file", "-f",
            help="Repeat for each changed file you want a rollback plan for.",
        ),
    ] = [],
    project_root: Annotated[
        Path,
        typer.Option("--project-root", "-p", exists=True, file_okay=False, resolve_path=True),
    ] = Path("."),
) -> None:
    _emit(_rollback_plan(changed_files=list(files), project_root=project_root))


@compose_app.callback(invoke_without_command=True)
def compose_tools_cmd(
    goal: Annotated[str, typer.Argument(help="One-line goal keyword (orient / release_check / ...).")] ,
) -> None:
    _emit(_compose_tools(goal=goal))


@why_app.callback(invoke_without_command=True)
def why_cmd(
    file: Annotated[str, typer.Argument(help="File path to look up (relative or absolute).")] ,
    project_root: Annotated[
        Path,
        typer.Option("--project-root", "-p", exists=True, file_okay=False, resolve_path=True),
    ] = Path("."),
) -> None:
    _emit(_why_did_this_change(file=file, project_root=project_root))


@failed_app.callback(invoke_without_command=True)
def failed_cmd(
    area: Annotated[str, typer.Argument(help="Substring match against the area string.")] ,
    project_root: Annotated[
        Path,
        typer.Option("--project-root", "-p", exists=True, file_okay=False, resolve_path=True),
    ] = Path("."),
) -> None:
    _emit(_what_failed_last_time(area=area, project_root=project_root))


@adapt_app.callback(invoke_without_command=True)
def adapt_plan_cmd(
    capabilities: Annotated[
        list[str],
        typer.Option(
            "--cap", "-c",
            help="Repeat for each capability the agent advertises (e.g. -c apply -c shell).",
        ),
    ] = [],
    file: Annotated[
        Path | None,
        typer.Option(
            "--file", "-f",
            help="Read the agent_plan/v1 JSON from this file. Without --file, reads from stdin.",
        ),
    ] = None,
) -> None:
    plan_text = _read_stdin_or_file(file)
    plan = json.loads(plan_text)
    _emit(_adapt_plan(plan, agent_capabilities=list(capabilities)))


@policy_app.callback(invoke_without_command=True)
def policy_cmd(
    project_root: Annotated[
        Path,
        typer.Argument(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    ] = Path("."),
) -> None:
    policy = _load_policy(project_root)
    _emit(policy)


# Public registry — cli.py imports this and registers each.
COPILOTS_VERBS: list[tuple[str, "typer.Typer", str]] = [
    ("explain-repo",        explain_app,  "Codex #6 — humane operational orientation of any repo."),
    ("score-patch",         score_app,    "Codex #3 — patch risk scorer (diff via stdin or --file)."),
    ("select-tests",        tests_app,    "Codex #7 — minimum + full-confidence test sets per intent."),
    ("rollback-plan",       rollback_app, "Codex #11 — structured undo plan for a set of changed files."),
    ("compose-tools",       compose_app,  "Codex #9 — tool-use planner: keyword → ordered MCP tool sequence."),
    ("why-did-this-change", why_app,      "Codex #5 — lineage + plan events that touched a file."),
    ("what-failed-last-time", failed_app, "Codex #5 — failed/rolled-back plan events matching an area."),
    ("adapt-plan",          adapt_app,    "Codex #8 — capability-aware card filtering (plan via stdin or --file)."),
    ("load-policy",         policy_app,   "Codex #10 — read [tool.forge.agent] policy from pyproject.toml."),
]
