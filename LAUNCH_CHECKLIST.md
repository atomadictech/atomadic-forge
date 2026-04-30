# Atomadic Forge — Launch Checklist (v0.3.2)

**Status:** UI parity foundation shipped · 841 Python tests passing · Tauri + PWA builds green

Last refreshed: 2026-04-30

---

## What this checklist tracks

The forge has three faces today:

1. **Python CLI** (`atomadic_forge`) — the engine
2. **Tauri desktop app** (`forge-studio`) — primary user UI
3. **Next.js PWA** (`forge-web`) — same UI, browser-native, installable

All three must hold launch readiness simultaneously. Item-by-item below.

---

## Engine (Python CLI) — `pip install atomadic_forge`

- [x] **Installation works** — `pip install -e ".[dev]"` succeeds
- [x] **All commands functional** — recon, auto, cherry, finalize, wire, certify, plan, plan-step, plan-apply, context-pack, preflight, enforce, doctor, recipes, sbom, cs1, iterate, evolve, emergent, synergy, audit, mcp serve
- [x] **Tests passing** — 841/841 (`pytest tests/ -q`)
- [x] **MCP server** — `forge mcp serve` exposes 21 tools + 5 resources over JSON-RPC stdio
- [x] **JSON output contracts** — every verb supports `--json`, schema-versioned
- [x] **Receipts** — schema v1 / v1.1 / v1.2 / v2 with optional ed25519 + AAAA-Nexus signatures
- [x] **EU AI Act / FDA PCCP conformity** — `forge cs1` generates conformity statement from receipt
- [x] **Eats own dogfood** — `forge auto src/atomadic_forge ./out` materializes correctly
- [x] **Import discipline** — zero upward-import violations in forge itself
- [ ] **PyPI registry** — published as `atomadic-forge` (admin action)

---

## UI Architecture

- [x] **Monorepo** — pnpm workspace at `atomadic-forge/`
- [x] **Shared core** — `@atomadic/forge-ui-core` package with full ForgeClient interface, types, components, theme
- [x] **Identical UI guarantee** — both shells render the same `<ForgeShell client={…}/>` from core
- [x] **Transport abstraction** — `TauriForgeClient` (IPC), `HttpForgeClient` (fetch), `StubForgeClient` (tests)

---

## Forge Studio (Tauri desktop)

- [x] **Builds clean** — `pnpm --filter forge-studio build` (vite production)
- [x] **Bundle config** — `tauri.conf.json` valid, identifier `com.atomadic.forge-studio`
- [x] **Window** — 1400×900 default, min 900×600, centered
- [x] **Icons** — 32, 128, 128@2x, .ico (all valid RGBA)
- [x] **Tailwind v4 + cyberpunk theme** — tokens loaded from shared core
- [x] **Cytoscape architecture & topology graphs** — 2069 modules transformed
- [x] **MCP bridge** — Rust `forge_connect` / `forge_call_tool` / `forge_complexipy_score`
- [x] **Vitest unit tests** — 11/11 passing
- [ ] **Code-signing certificates** — Apple Developer ID + Microsoft Authenticode (admin action)
- [ ] **Auto-update channel** — Tauri updater wired (next session)

---

## Forge Web (Next.js 15 PWA)

- [x] **Builds clean** — `pnpm --filter forge-web build` (Turbopack)
- [x] **Identical UI** — imports `<ForgeShell>` from shared core, supplies HTTP client
- [x] **Manifest** — `/manifest.webmanifest` with 192/512 maskable icons
- [x] **Service worker** — `/sw.js` with shell-cache + SWR asset strategy + network-only API
- [x] **Install prompt** — `<InstallPwaButton>` handling `beforeinstallprompt`
- [x] **API routes** — `/api/forge/{connect,recon,wire,certify,plan,plan/[id]/step,doctor,tools,resources,receipt,complexity}`
- [x] **Forge runner** — `lib/forge-runner.ts` proxies to `python -m atomadic_forge` (configurable via `FORGE_BIN`)
- [ ] **Hosting target chosen** — Vercel / Cloudflare Pages / self-host (decision pending)
- [ ] **Custom domain** — `forge.atomadic.tech` (admin action)
- [ ] **CDN-cached app shell** — verify Cache-Control headers post-deploy

---

## Verb coverage in the UI

| Verb           | UI screen        | Wired |
|----------------|------------------|-------|
| recon          | Scan             | ✅    |
| wire           | Scan / Debt      | ✅    |
| certify        | Certify          | ✅    |
| receipt browse | Certify          | ✅    |
| plan           | Plan             | ✅    |
| plan-step      | Plan (Apply btn) | ✅    |
| doctor         | Doctor           | ✅    |
| tools/list     | Topology         | ✅    |
| resources/list | Topology         | ✅    |
| complexity     | Complexity       | ✅    |
| enforce        | (next session)   | ⏳    |
| auto           | (next session)   | ⏳    |
| cherry / finalize | (next session) | ⏳    |
| context-pack   | (next session)   | ⏳    |
| preflight      | (next session)   | ⏳    |
| iterate / evolve | (next session) | ⏳    |
| emergent / synergy | (next session) | ⏳  |
| recipes / sbom / cs1 | (next session) | ⏳ |

The `ForgeClient` interface already declares all of these — the screens
remain to be built.

---

## Testing

- [x] **Engine tests** — 841/841 passing
- [x] **Studio unit tests** — 11/11 passing (fCodeSeverity, debt math, brittleness)
- [x] **Studio Playwright smoke** — header, nav, drop-zone, empty states
- [ ] **Core component tests** (Vitest + RTL on `@atomadic/forge-ui-core`) — next session
- [ ] **Web Playwright e2e** — next session

---

## Documentation

- [x] **Engine** — README, ARCHITECTURE, CONTRIBUTING, EVOLUTION, SECURITY, CHANGELOG, docs/01–05
- [x] **forge-ui-core** — README with architecture diagram + usage examples
- [x] **forge-web** — README explaining shell role + run instructions
- [x] **LAUNCH_CHECKLIST** — this file (v0.3.2 reality)

---

## Repo state

- [x] **`.gitignore`** — covers Python + JS monorepo, build outputs, Cargo target
- [ ] **Pruned merged feature branches** — next session (9 stale branches detected)
- [x] **GitHub remote** — `git@github.com:atomadictech/atomadic-forge.git` configured

---

## Sign-off

**Engine:** ✅ PASS
**Tauri shell:** ✅ PASS (build verified, tests green)
**PWA shell:** ✅ PASS (build verified, PWA assets present)
**Shared core:** ✅ PASS (typecheck clean, public API stable)
**Verb coverage:** 🟡 REFINE (10/22 wired in UI, all in `ForgeClient`)
**Testing:** 🟡 REFINE (engine + studio green, core/web pending)

**Overall verdict:** **REFINE** — foundation shippable, verb-coverage expansion + tests scheduled for next session.
