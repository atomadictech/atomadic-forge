# Forge Studio

Desktop Visual Sandbox for Atomadic Forge — Tauri v2 + React + TypeScript.
Connects to `forge mcp serve` over stdio JSON-RPC for live architecture, debt, and complexity data.

## Requirements

| Dependency | Min version |
|---|---|
| Rust / Cargo | 1.77 |
| Node.js | 20 |
| pnpm | 9 |
| `forge` on PATH | 0.1.0 (`pip install atomadic-forge`) |

## Quick Start

```bash
cd forge-studio
pnpm install
pnpm tauri dev
```

## Golden Path Lane B Milestones

| Week | Deliverable |
|---|---|
| W4 | Tauri scaffold + MCP stdio transport |
| W5 | Project Scan Dashboard + Architecture Graph |
| W6 | Complexity Heatmap + Real-Time Debt Counter |
| W7 | Agent Topology Map |

## Features

**W5 Project Scan** — Drop folder → recon scan → tier distribution + symbol counts.
Brittleness = 1 - (autofixable/total). Click tier bar → drill into file list.

**W5 Architecture Graph** — Cytoscape.js renders 5 tiers. Edges = upward-only import law.
Click node → filter scan dashboard.

**W6 Complexity Heatmap** — complexipy per file, 0(green)→100(red). Graceful degradation:
install notice when complexipy missing.

**W6 Debt Counter** — CISQ: error=4, warn=2, info=1 × hourly_rate ($80 default).
Polls wire every 5s; counter flashes green on violation drop.

**W7 Agent Topology** — tools/list + resources/list on connect. Solid=tools, dashed=resources.
Live edge pulse on hover.

## MCP Transport

stdio only (v0). Rust spawns `forge mcp serve --project-root <path>` via `std::process::Command`,
performs initialize handshake, routes all tool calls through Tauri invoke bridge.
Clear error when forge not on PATH.

## State Management

Zustand for UI/connection state + React Query for server-state caching.

## Testing

```bash
pnpm test       # Vitest unit (no Tauri bridge)
pnpm test:e2e   # Playwright smoke (requires pnpm dev)
pnpm typecheck  # TypeScript strict
```

## Bundle Size

<8 MB JS. Manual chunks: react, cytoscape, @tanstack/react-query.