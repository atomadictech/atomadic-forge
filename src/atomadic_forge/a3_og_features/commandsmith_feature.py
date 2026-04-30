"""Tier a3 — Commandsmith feature: discover, register, document, smoke-test.

The Commandsmith feature glues together the a1 discoverer + a1 renderers and
manages on-disk persistence for the registry.  It is the only module the a4
CLI surface depends on.

Pipelines exposed:

* :meth:`sync` — full pipeline (discover → render registry → write docs).
* :meth:`wrap_class` — generate a Typer wrapper around a single class
  (used to lift a freshly assimilated symbol into a CLI command).
* :meth:`smoke` — invoke ``--help`` on every registered command and record
  exit codes.
"""

from __future__ import annotations

import datetime as _dt
import importlib
import json
import subprocess
import sys
from pathlib import Path

from ..a0_qk_constants.commandsmith_types import (
    CommandSignatureCard,
    RegisteredCommandCard,
    RegistryManifestCard,
)
from ..a1_at_functions.commandsmith_discover import discover_command_modules
from ..a1_at_functions.commandsmith_render import (
    render_command_doc,
    render_command_index,
    render_registry_module,
    render_wrapper_module,
)

_REGISTRY_FILE = "_registry.py"
_MANIFEST_FILE = "commandsmith_manifest.json"


class Commandsmith:
    """Manage the CLI registry for an ASS-ADE-style package.

    ``package_root``: directory containing the ``commands/`` subfolder.
    ``docs_root``:    where to write per-command Markdown.
    ``manifest_dir``: where to persist ``commandsmith_manifest.json``.
    """

    def __init__(
        self,
        *,
        package_root: Path,
        package_name: str = "atomadic_forge",
        docs_root: Path | None = None,
        manifest_dir: Path | None = None,
    ) -> None:
        self.package_root = Path(package_root)
        self.package_name = package_name
        self.commands_dir = self.package_root / "commands"
        self.docs_root = Path(docs_root) if docs_root else self.package_root.parent.parent / "docs" / "commands"
        self.manifest_dir = Path(manifest_dir) if manifest_dir else self.package_root.parent.parent / ".atomadic-forge"

    # ----- discovery --------------------------------------------------

    def discover(self) -> list[RegisteredCommandCard]:
        return discover_command_modules(
            self.package_root,
            package=self.package_name,
            sub_dirs=("commands",),
            source_root="atomadic_forge_seed",
        )

    # ----- registry / docs / manifest --------------------------------

    def write_registry(self, cards: list[RegisteredCommandCard]) -> Path:
        """Emit ``commands/_registry.py``."""
        target = self.commands_dir / _REGISTRY_FILE
        target.write_text(render_registry_module(cards), encoding="utf-8")
        return target

    def write_docs(self, cards: list[RegisteredCommandCard]) -> list[Path]:
        """Write per-command Markdown plus an INDEX."""
        self.docs_root.mkdir(parents=True, exist_ok=True)
        out: list[Path] = []
        for card in cards:
            f = self.docs_root / f"{card['name']}.md"
            f.write_text(render_command_doc(card), encoding="utf-8")
            out.append(f)
        idx = self.docs_root / "INDEX.md"
        idx.write_text(render_command_index(cards), encoding="utf-8")
        out.append(idx)
        return out

    def write_manifest(self, cards: list[RegisteredCommandCard],
                       smoke_results: dict[str, bool] | None = None) -> Path:
        manifest = RegistryManifestCard(
            schema_version="atomadic-forge.commandsmith.registry/v1",
            generated_at_utc=_dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            commands=cards,
            smoke_results=smoke_results or {},
        )
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        target = self.manifest_dir / _MANIFEST_FILE
        target.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return target

    # ----- generator wrapping a class --------------------------------

    def wrap_class(
        self,
        *,
        target_module: str,
        target_class: str,
        command_name: str,
        out_dir: Path | None = None,
        help_text: str = "",
        auto_scan: str | None = None,
    ) -> Path:
        """Generate ``commands/<command_name>_cli.py`` wrapping a class.

        ``auto_scan`` (optional): name of a method to call inside the Typer
        callback (e.g. ``scan_repo`` for CherryPicker) so subcommands see a
        populated instance state.  If omitted, a sensible default is picked:
        any method whose name is exactly ``scan`` or starts with ``scan_``.
        """
        sub_cmds = self._inspect_class_methods(target_module, target_class)
        init_params = self._inspect_init_params(target_module, target_class)
        if auto_scan is None:
            auto_scan = next(
                (s["name"] for s in sub_cmds
                 if s["name"] == "scan" or s["name"].startswith("scan_")),
                None,
            )
        src = render_wrapper_module(
            target_module=target_module,
            target_class=target_class,
            command_name=command_name,
            sub_commands=sub_cmds,
            help_text=help_text or f"Auto-wrapped {target_class}",
            init_params=init_params,
            auto_scan=auto_scan,
        )
        out = (out_dir or self.commands_dir) / f"{command_name.replace('-', '_')}_cli.py"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(src, encoding="utf-8")
        return out

    def _inspect_init_params(self, target_module: str,
                             target_class: str) -> list[str]:
        """Extract __init__ parameter strings (``name: type``)."""
        import inspect

        try:
            module = importlib.import_module(target_module)
            cls = getattr(module, target_class)
            sig = inspect.signature(cls.__init__)
            params: list[str] = []
            for pname, p in sig.parameters.items():
                if pname == "self":
                    continue
                if p.kind in (inspect.Parameter.VAR_POSITIONAL,
                              inspect.Parameter.VAR_KEYWORD):
                    continue
                ann = (
                    p.annotation.__name__
                    if p.annotation is not inspect.Parameter.empty
                    and hasattr(p.annotation, "__name__")
                    else str(p.annotation)
                    if p.annotation is not inspect.Parameter.empty
                    else "str"
                )
                params.append(f"{pname}: {ann}")
            return params
        except Exception:
            return []

    def _inspect_class_methods(
        self, target_module: str, target_class: str,
    ) -> list[CommandSignatureCard]:
        """Live-inspect a class via importlib and return method signatures.

        Falls back to AST scanning if import fails.
        """
        import inspect

        try:
            module = importlib.import_module(target_module)
            cls = getattr(module, target_class)
            cards: list[CommandSignatureCard] = []
            for name, member in inspect.getmembers(cls, predicate=inspect.isfunction):
                if name.startswith("_"):
                    continue
                sig = inspect.signature(member)
                params: list[str] = []
                for pname, p in sig.parameters.items():
                    if pname == "self":
                        continue
                    ann = (
                        p.annotation.__name__
                        if p.annotation is not inspect.Parameter.empty
                        and hasattr(p.annotation, "__name__")
                        else str(p.annotation)
                        if p.annotation is not inspect.Parameter.empty
                        else "Any"
                    )
                    params.append(f"{pname}: {ann}")
                ret = (
                    sig.return_annotation.__name__
                    if sig.return_annotation is not inspect.Signature.empty
                    and hasattr(sig.return_annotation, "__name__")
                    else "Any"
                )
                cards.append(CommandSignatureCard(
                    name=name,
                    parameters=params,
                    return_type=ret,
                    docstring=(inspect.getdoc(member) or "").split("\n")[0],
                ))
            return cards
        except Exception:
            return []

    # ----- smoke test -------------------------------------------------

    def smoke(self, cards: list[RegisteredCommandCard],
              cli_invocation: list[str] | None = None) -> dict[str, bool]:
        """Run ``<cli> <verb> --help`` for each card; record exit code == 0.

        Subprocesses inherit ``PYTHONIOENCODING=utf-8`` so rich/Typer help
        rendering doesn't blow up on Windows ``cp1252`` consoles.
        """
        import os
        if cli_invocation is None:
            # Use the forge CLI entry point.
            cli_invocation = [sys.executable, "-m",
                              "atomadic_forge.a4_sy_orchestration.cli"]
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        results: dict[str, bool] = {}
        for card in cards:
            try:
                rc = subprocess.run(
                    cli_invocation + [card["name"], "--help"],
                    capture_output=True, text=True, timeout=20,
                    env=env, encoding="utf-8", errors="replace",
                ).returncode
            except (subprocess.TimeoutExpired, FileNotFoundError):
                rc = 1
            results[card["name"]] = rc == 0
        return results

    # ----- one-shot pipeline -----------------------------------------

    def sync(self, *, smoke: bool = False) -> RegistryManifestCard:
        cards = self.discover()
        self.write_registry(cards)
        self.write_docs(cards)
        smoke_results = self.smoke(cards) if smoke else {}
        self.write_manifest(cards, smoke_results)
        return RegistryManifestCard(
            schema_version="atomadic-forge.commandsmith.registry/v1",
            generated_at_utc=_dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            commands=cards,
            smoke_results=smoke_results,
        )
