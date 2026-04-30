# Atomadic Forge — VS Code extension

Live diagnostics, hover, and goto-source on `.forge` sidecar files.
Thin wrapper around the `forge lsp serve` Python LSP that ships with
[`atomadic-forge`](https://github.com/atomadictech/atomadic-forge).

This is the Lane D W14 deliverable from the Atomadic Forge Golden
Path. Lane D W12 (`forge-lsp` server) ships as part of the main
`atomadic-forge` package; this extension is the editor surface.

## What you get

- **Diagnostics** — every save / edit re-validates the sidecar
  against its source AST. Drift surfaces as F-coded errors:
  - `F0100` source did not parse
  - `F0101` sidecar declares a missing symbol
  - `F0102` source has an undeclared public symbol
  - `F0103` Pure-declared symbol violates purity (IO / NetIO / Random)
  - `F0106` declared tier mismatches the source path's tier
- **Hover** — markdown summary of the cursor's symbol: effect, tier,
  compose_with, proves clauses.
- **Goto definition** — jump from `name: login` in `auth.py.forge` to
  `auth.py`'s `def login(...)`.

## Install

### Prerequisite

The Python `atomadic-forge` package must be installed and `forge` on
your PATH:

```bash
pip install atomadic-forge
forge --version   # should print 0.3.0+
forge lsp serve   # should print "forge-lsp: ready" then wait
```

### From the Marketplace

(Lane D W14: this listing is the `0.3.x` ship target.)

```
ext install atomadictech.atomadic-forge-vscode
```

### From source (today)

```bash
cd vscode-forge-extension
npm install
npm run compile
# then in VS Code: F5 to launch the Extension Development Host
```

## Configuration

| Setting | Default | Notes |
|---|---|---|
| `atomadicForge.serverPath` | `"forge"` | Override the `forge` binary path (e.g. `/path/to/venv/bin/forge`) |
| `atomadicForge.serverArgs` | `["lsp", "serve"]` | Args passed to `forge`. Don't change unless you know why. |
| `atomadicForge.trace.server` | `"off"` | `"messages"` or `"verbose"` to log LSP traffic to the output panel |

## Commands

| Command | Notes |
|---|---|
| `Atomadic Forge: Restart language server` | After upgrading `atomadic-forge` in your venv |
| `Atomadic Forge: Show LSP output` | Open the output channel for diagnostics + traces |

## Activation

The extension activates automatically when you open any file matching
`*.py.forge`, `*.ts.forge`, `*.js.forge`, `*.tsx.forge`, `*.jsx.forge`,
`*.mjs.forge`, or `*.cjs.forge`.

## Troubleshooting

**"forge LSP failed to start"** — your `forge` binary isn't on PATH.
Either:
- `pip install atomadic-forge` in the active Python environment, OR
- set `atomadicForge.serverPath` to an absolute path

**Diagnostics don't appear after editing** — check `Atomadic Forge:
Show LSP output`. The Python LSP logs every parse / validate to that
channel. Common cause: the source file (e.g. `auth.py`) is missing
or has a Python syntax error.

**Hover empty** — the hover only fires on a `name: <symbol>` line in
the sidecar. Position the cursor on that exact line.

## Status

- **Today (v0.3.x):** scaffold + LSP wiring + Marketplace-ready
  manifest. Local-install-from-source flow works.
- **Lane D W18 (planned):** JetBrains plugin parity (IntelliJ /
  PyCharm).
- **Lane D W20 (planned):** Bao-Rompf compose-by-law + Lean4 `proves:`
  discharge inline in the editor.

## License

Business Source License 1.1 — same as the parent
[`atomadic-forge`](../LICENSE) package. Free for non-production use;
commercial license required for production. Change Date 2030-04-27 →
Apache 2.0.
