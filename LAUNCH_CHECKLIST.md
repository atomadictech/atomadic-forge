# Atomadic Forge — Launch Checklist (v0.6.0)

**Status:** Released to PyPI · 944 tests passing · forge certify 100/100 · CI green

Last refreshed: 2026-05-02

---

## What this checklist tracks

The Forge is a **Python CLI tool** (`atomadic-forge`). The desktop GUI,
web app, and VS Code extension live in their own repositories now —
this checklist covers the engine only.

Sister projects (separate repos / READMEs):

- **Tauri desktop app** → `atomadic-forge-tauri-studio`
- **Web PWA** → `atomadic-forge-site`
- **VS Code extension** → `atomadic-forge-vscode-ext`
- **Cloudflare badge Worker** → `atomadic-forge-cloudflare-workers`

---

## Engine (Python CLI) — `pip install atomadic-forge`

- [x] **Installation works** — `pip install -e ".[dev]"` succeeds
- [x] **All commands functional** — recon, auto, cherry, finalize, wire,
      certify, plan, plan-step, plan-apply, context-pack, preflight,
      enforce, doctor, recipes, sbom, cs1, iterate, evolve, emergent,
      synergy, audit, mcp serve, lsp serve, chat, demo, copilots
- [x] **Tests passing** — 944/944 (`pytest tests/ -q`), 2 skipped
- [x] **MCP server** — `forge mcp serve` exposes the full tool surface
      over JSON-RPC stdio (Cursor / Claude Code / Aider / Devin compatible)
- [x] **JSON output contracts** — every verb supports `--json`,
      schema-versioned (recipe v1, certify, agent_plan/v1, signed_receipt/v1)
- [x] **Receipts** — schema v1 with optional ed25519 + AAAA-Nexus signatures
- [x] **EU AI Act / FDA PCCP / SR 11-7 / CMMC-AI conformity** — `forge cs1`
      generates conformity statement from receipt
- [x] **Eats own dogfood** — `forge auto src/atomadic_forge ./out`
      materializes correctly; forge passes its own certify at 100/100
- [x] **Import discipline** — zero upward-import violations in forge itself
- [x] **PyPI registry** — published as `atomadic-forge` (latest: v0.6.0)

---

## v0.6.0 capabilities (new in this release)

- [x] **`dedup_engine`** — orchestrates intent_similarity + code_signature
      + research_note_distiller to catch duplicate research notes AND
      duplicate code logic at the gate
- [x] **`cost_circuit_breaker`** — multi-tier USD + token budgets
      (per-task / per-session / per-day) with hard-kill, soft-warn-at-80%,
      no-progress stuck detection. Defaults: $100/day, OpenHands-style
      MAX_ITERATIONS=100
- [x] **`hierarchical_memory`** — 4-tier MemGPT pattern (working / pinned
      core / episodic / reflection), Park-2023 recency × importance × relevance
      scoring, pure stdlib sqlite3 (air-gappable)
- [x] **`agent_hire_protocol`** — 5-step swarm SOP (sealed-probe vetting →
      trust gate → similarity check → contract → signed receipt) with D_max=3
- [x] **`--provider ling`** — Ling-2.6-1T (1T-param MoE, 262K context,
      SOTA SWE-bench) via OpenRouter at the **free tier**
- [x] **certify polish** — `health_summary`, `axes` with per-axis `how_to_fix`,
      `scan_duration_ms`, schema-stable across releases
- [x] **3 MCP fixes** — `recon` symbols overflow, `certify` xfailed parser,
      `auto_plan` PASS verdict scoring

---

## LLM provider matrix

| Provider | Cost | Default model | When to use |
|----------|------|---------------|-------------|
| `gemini` | free tier | `gemini-2.5-flash` | Best free cloud option |
| `nexus` | paid | (Nexus default) | Sovereign AI; trust-gated; revenue-routing |
| `anthropic` | paid | `claude-sonnet-4-6` | Highest code quality |
| `openai` | paid | `gpt-4o-mini` | Cheap GPT path |
| `openrouter` | free tier | `inclusionai/ling-2.6-1t:free` | Access 200+ models |
| `ling` | **free** | `inclusionai/ling-2.6-1t:free` | Frontier model, zero cost |
| `ollama` | free, local | `qwen2.5-coder:7b` | Offline; fully private |
| `stub` | free, offline | n/a | Tests, CI, dry-runs |

---

## Distribution

- [x] **PyPI** — `pip install atomadic-forge` (v0.6.0)
- [x] **GitHub Release** — [v0.6.0](https://github.com/atomadictech/atomadic-forge/releases/tag/v0.6.0)
- [x] **Live demo** — [forge.atomadic.tech](https://forge.atomadic.tech)
- [x] **MCP integration** — drop-in for Cursor / Claude Code / Aider / Devin
- [ ] **Homebrew tap** — future
- [ ] **conda-forge** — future

---

## Documentation

- [x] **Root** — README, ARCHITECTURE, CONTRIBUTING, EVOLUTION, SECURITY,
      CHANGELOG, AGENTS, LAUNCH_CHECKLIST
- [x] **docs/** — getting started, commands reference, tutorials, FAQ,
      compliance mappings (EU AI Act / SR 11-7 / FDA PCCP / CMMC-AI),
      release messaging, codex walkthrough
- [x] **Compliance** — `docs/compliance/` covers all four frameworks
- [ ] **Per-feature ADRs** — ongoing

---

## Repo hygiene

- [x] **`.gitignore`** — covers Python + Rust + JS + binaries
- [x] **No sister-project bloat** — Tauri / web / VS Code / Cloudflare
      moved to their own repos
- [x] **GitHub remote** — `git@github.com:atomadictech/atomadic-forge.git`
- [x] **CI workflows** — CI (3.10/3.11/3.12 matrix), forge self-certify,
      Customer Refactor (forge.atomadic.tech $499 fulfillment), Release
- [x] **Branch hygiene** — `main` only; stale lane branches purged

---

## Sign-off

**Engine:** ✅ PASS (944 tests, 100/100 certify, ruff clean, CI green)
**Distribution:** ✅ PASS (PyPI v0.6.0 published, GitHub Release live)
**Documentation:** ✅ PASS (root + docs/ all current to v0.6.0)
**Repo hygiene:** ✅ PASS (sister projects out, branches pruned, CI green)

**Overall verdict:** **PASS** — v0.6.0 is shippable, shipped, and live.
