# Forge Studio (moved)

The desktop GUI (Tauri 2 + React + TypeScript) is no longer part of the
`atomadic-forge` repository. It lives in its own project so this repo
stays a focused Python CLI tool.

**New location:** `atomadic-forge-tauri-studio` (separate repo)

The Studio still talks to `forge mcp serve` over JSON-RPC stdio, exactly
as before — only the build tree was split.

## Why the move

`atomadic-forge` is the Python engine. The Studio is a TypeScript/Rust
desktop app with its own toolchain (pnpm, Vite, Cargo). Bundling both in
one repo meant carrying ~3 GB of Rust build artifacts and ~500 MB of
node_modules in every clone. Splitting them keeps the Python repo lean
(under 30 MB) without giving up the GUI roadmap.

## What lives here now

The Forge engine surfaces every Studio capability as a CLI verb or MCP
tool:

| What you wanted in Studio | How to get it from the engine |
|---|---|
| Architecture graph | `forge recon --json` (tier distributions + symbol map) |
| Complexity heatmap | `forge certify --json` includes complexity scoring axis |
| Debt counter | `forge wire --json` returns violations with severity |
| Agent topology | `forge mcp serve` exposes `tools/list` + `resources/list` |
| Live scoring | The Cloudflare badge Worker (separate repo) embeds the score |

If you want the desktop UI specifically, clone
`atomadic-forge-tauri-studio` and follow its README.
