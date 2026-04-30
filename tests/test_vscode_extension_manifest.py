"""Tier verification — Lane D W14 VS Code extension manifest.

The extension itself is TypeScript and lives in
vscode-forge-extension/; we don't run a full VS Code test harness
in pytest. Instead we pin the manifest contract:

  * package.json parses
  * activation hooks the right glob + languageId
  * the LSP transport is stdio (matches forge lsp serve)
  * commands + configuration knobs match the README
  * the language id is 'forge' (matches a1.lsp_protocol's clients)
  * version pin lines up with atomadic-forge's main package
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


_REPO = Path(__file__).resolve().parents[1]
_EXTENSION = _REPO / "vscode-forge-extension"
_MANIFEST = _EXTENSION / "package.json"


def _load_manifest() -> dict:
    return json.loads(_MANIFEST.read_text(encoding="utf-8"))


def test_extension_directory_exists():
    assert _EXTENSION.is_dir()
    for required in ("package.json", "tsconfig.json",
                      "language-configuration.json", "README.md",
                      ".gitignore", ".vscodeignore"):
        assert (_EXTENSION / required).is_file(), (
            f"vscode-forge-extension/{required} missing"
        )


def test_extension_ts_entry_present():
    assert (_EXTENSION / "src" / "extension.ts").is_file()


def test_manifest_parses():
    data = _load_manifest()
    assert isinstance(data, dict)


def test_manifest_top_level_fields():
    data = _load_manifest()
    for f in ("name", "displayName", "description", "version",
              "publisher", "license", "main", "activationEvents",
              "contributes", "engines", "dependencies"):
        assert f in data, f"package.json missing top-level {f!r}"


def test_manifest_engine_vscode_pinned():
    data = _load_manifest()
    assert data["engines"]["vscode"].startswith("^1.")


def test_manifest_publisher_atomadictech():
    data = _load_manifest()
    assert data["publisher"] == "atomadictech"


def test_manifest_language_id_pinned():
    """The LSP server (a1.lsp_protocol) emits diagnostics for files
    the client tags with documentSelector. The agreed languageId is
    'forge'. Renaming this is breaking."""
    data = _load_manifest()
    languages = data["contributes"]["languages"]
    assert any(l["id"] == "forge" for l in languages)
    forge_lang = next(l for l in languages if l["id"] == "forge")
    assert ".forge" in forge_lang["extensions"]


def test_manifest_activates_on_dot_forge_files():
    data = _load_manifest()
    events = data["activationEvents"]
    assert "onLanguage:forge" in events
    # Plus workspaceContains for the common source-file companions.
    assert any(e.startswith("workspaceContains:**/*.py.forge")
               for e in events)


def test_manifest_lsp_dependency_present():
    data = _load_manifest()
    deps = data["dependencies"]
    assert "vscode-languageclient" in deps


def test_manifest_configuration_knobs():
    """The three configuration knobs documented in the README must
    exist verbatim — config drift between manifest + README breaks
    user expectations."""
    data = _load_manifest()
    props = data["contributes"]["configuration"]["properties"]
    for key in ("atomadicForge.serverPath",
                "atomadicForge.serverArgs",
                "atomadicForge.trace.server"):
        assert key in props, f"manifest missing {key!r}"
    # Default args spawn `forge lsp serve` — matches our CLI verb.
    assert props["atomadicForge.serverArgs"]["default"] == ["lsp", "serve"]
    assert props["atomadicForge.serverPath"]["default"] == "forge"


def test_manifest_commands():
    data = _load_manifest()
    commands = {c["command"] for c in data["contributes"]["commands"]}
    assert "atomadicForge.restartServer" in commands
    assert "atomadicForge.showOutput" in commands


def test_extension_ts_uses_stdio_transport():
    """The TypeScript entry must use TransportKind.stdio (matches
    forge lsp serve's framing). Any other transport silently breaks."""
    src = (_EXTENSION / "src" / "extension.ts").read_text(encoding="utf-8")
    assert "TransportKind.stdio" in src
    assert "vscode-languageclient/node" in src


def test_extension_version_matches_package():
    """The VS Code extension version should track atomadic-forge's
    main package version so users don't get out-of-step LSP / extension
    pairs."""
    from atomadic_forge import __version__
    data = _load_manifest()
    assert data["version"] == __version__


def test_extension_document_selector_covers_polyglot_sidecars():
    """Sidecar parser supports .py / .ts / .js / .tsx / .jsx / .mjs /
    .cjs / .forge — manifest's documentSelector should match the same
    polyglot surface so the LSP fires across languages."""
    src = (_EXTENSION / "src" / "extension.ts").read_text(encoding="utf-8")
    for ext in ("*.py.forge", "*.ts.forge", "*.js.forge",
                "*.tsx.forge", "*.jsx.forge", "*.mjs.forge",
                "*.cjs.forge"):
        assert ext in src, f"documentSelector missing {ext!r}"
