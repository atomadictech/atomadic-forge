<p align="center">
  <img src="assets/Atomadic-Forge-01.png" alt="Atomadic Forge" width="720"/>
</p>

# Atomadic Forge

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: BSL-1.1](https://img.shields.io/badge/License-BSL--1.1-yellow.svg)](LICENSE)
[![CI](https://github.com/atomadictech/atomadic-forge/actions/workflows/ci.yml/badge.svg)](https://github.com/atomadictech/atomadic-forge/actions/workflows/ci.yml)
[![Forge certify](https://img.shields.io/badge/forge_certify-100%2F100-brightgreen)](docs/SHOWCASE.md)

> **Absorb. Enforce. Emerge.** The architecture substrate for AI-generated code — now polyglot (Python, JavaScript, TypeScript).

Forge is a monadic-architecture engine that does three things no existing
tool combines:

1. **Absorbs** Python or JavaScript / TypeScript repositories into a verified
   5-tier layout.
2. **Enforces** the upward-only import law on every emitted file.
3. **Emerges** new capabilities by composing what already exists — and
   refuses to credit code that lies about what it does.

It's the substrate Cursor and Devin and Lovable don't have. It runs on
free local models, free cloud tiers, or paid frontier models — same
loop, swap the LLM, watch the trajectory carry harder tasks higher.

**Languages:** Python (`.py`), JavaScript (`.js` / `.mjs` / `.cjs` / `.jsx`),
TypeScript (`.ts` / `.tsx`). Cloudflare Workers, Node back-ends, and mixed
Python+JS repositories all classify in a single pass — no Node dependency,
`node_modules/` skipped automatically.

## Get started in 10 minutes

**Read [docs/FIRST_10_MINUTES.md](docs/FIRST_10_MINUTES.md).** It is
the canonical onboarding path: install, a 30-second offline demo, a
10-second free recon on your own repo, then a fork into either
"absorb existing code" or "generate from intent" with explicit cost,
privacy, and wallclock numbers.

For deeper paths once you have done the 10-minute path:

- [docs/MULTI_REPO.md](docs/MULTI_REPO.md) — absorb more than one repo at once.
- [docs/CI_CD.md](docs/CI_CD.md) — GitHub Actions, GitLab CI, pre-commit.
- [docs/AIR_GAPPED.md](docs/AIR_GAPPED.md) — offline / on-prem install.
- [docs/SHOWCASE.md](docs/SHOWCASE.md) — live trajectories of real runs.

### Polyglot recon (JS/TS in a single pass)

```bash
$ forge recon ./my-cloudflare-worker

Recon: ./my-cloudflare-worker
------------------------------------------------------------
  python files:     0
  javascript files: 4
  typescript files: 1
  primary language: javascript
  symbols:          17
  tier dist:        {'a0_qk_constants': 1, 'a1_at_functions': 2,
                     'a2_mo_composites': 1, 'a4_sy_orchestration': 1}
  effect dist:      {'pure': 9, 'state': 5, 'io': 3}
  recommendations:
    - JS/TS files are not yet split into aN_* tier directories —
      see suggested_tier per file in symbols[].
```

## Pipeline lanes

```bash
forge auto ./messy-repo ./out --apply       # Absorb a flat repo into 5-tier layout
forge evolve run "<intent>" ./out --auto 5  # LLM-driven recursive generation
forge demo run --preset NAME                # Click-to-launch-video preset
forge chat ask "what should I fix next?" --context .
```

**What Forge does:**
- Walks any Python or JavaScript/TypeScript repo, classifies every symbol into one of 5 architectural tiers
- Materializes into a tier-organized tree with strict upward-only imports
- Detects architecture violations (upward imports, misclassified symbols) — Python or JS, same law
- Scores conformance: documentation, tests, tier layout, import discipline
- Works with AI-generated code — absorbs it, fixes the architecture, ships it

**What Forge does NOT do:**
- Pretend `forge auto` magically finished your product; absorption creates a
  tiered starter skeleton. `iterate` / `evolve` can generate code through your
  configured LLM, but Forge still gates it with wire/certify feedback.
- Create semantic unification (two `User` classes stay two `User` classes)
- Bypass the 5-tier law (Forge itself passes its own `wire` scan 100%)
- Store secrets or credentials

## Why Forge exists

AI agents produce 30–50% of new code in many teams. The output is **fast and often correct**. But it's almost universally **architecturally incoherent**:

- God classes mixing concerns
- Leaky abstractions and circular imports
- Same concept named five different ways
- Test coverage is scattered
- No module organization

**Linters say "no."** Forge says **"yes, but reorganised like this"** and shows the diff.

Forge is **not a style checker**. It's an **architecture rebuilder**. It absorbs your code (including AI-generated code), re-tiers it, enforces the 5-tier monadic law, and emits a clean, verifiable structure with certification scores.

## The 5-tier monadic law

Every source file (Python `.py`, JavaScript `.js`/`.mjs`/`.cjs`/`.jsx`, or
TypeScript `.ts`/`.tsx`) belongs to exactly one tier. **Tiers compose upward
only** — never sideways, never downward.

```
  a4_sy_orchestration/       ← CLI, entry points, top-level orchestration
           ↑
  a3_og_features/            ← Feature modules (compose a2 into capabilities)
           ↑
  a2_mo_composites/          ← Stateful classes (clients, registries, stores)
           ↑
  a1_at_functions/           ← Pure functions (validators, parsers, formatters)
           ↑
  a0_qk_constants/           ← Constants, enums, TypedDicts (zero logic)
```

| Tier | Directory | What lives here | May import |
|------|-----------|-----------------|------------|
| **a0** | `a0_qk_constants/` | Constants, enums, TypedDicts, config | Nothing |
| **a1** | `a1_at_functions/` | Pure stateless functions | a0 only |
| **a2** | `a2_mo_composites/` | Stateful classes, clients, stores | a0, a1 |
| **a3** | `a3_og_features/` | Features combining composites | a0–a2 |
| **a4** | `a4_sy_orchestration/` | CLI commands, entry points | a0–a3 |

### Why the tiers work

Each tier is a layer of **verified building blocks**. Higher tiers never invent logic — they **compose** blocks from lower tiers. This means:

- **a0 is bulletproof:** no imports, no logic, 100% verifiable
- **a1 is isolated:** pure functions on pure data, trivial to test
- **a2 wraps logic:** state + verified building blocks, testable in isolation
- **a3 orchestrates:** combines composites into features, handles cross-cutting concerns
- **a4 glues everything:** CLI layer only, zero business logic

**Upward-only import law:** `forge wire` detects violations, `import-linter` enforces at CI, contract lives in `pyproject.toml`.

## Installation

PyPI is **coming soon**. Until then, install editable from source:

```bash
git clone https://github.com/atomadictech/atomadic-forge && cd atomadic-forge
pip install -e ".[dev]"
python -m pytest               # Verify the full local suite
python -m atomadic_forge --help
```

Then follow [docs/FIRST_10_MINUTES.md](docs/FIRST_10_MINUTES.md) for
the canonical first-run path (offline demo, free recon, then absorb or
generate).

## Code-from-intent (LLM-driven, with Forge as the architectural backbone)

Plug a free Gemini key in and let the loop produce architecturally-coherent
code from a paragraph of intent:

```bash
# Get a free key at https://aistudio.google.com/apikey
export GEMINI_API_KEY=your-key-here          # never commit this

# Single-shot generate (one user-intent → multi-turn LLM loop):
forge iterate run "build a tiny calculator CLI" ./out \
    --package calc --provider gemini --max-iterations 4

# Recursive self-improvement: N rounds, catalog grows each round:
forge evolve run "build a markdown-to-PDF service" ./out \
    --auto 5 --provider gemini --target-score 80

# Pre-flight (no LLM call) — print the system + first prompt:
forge iterate preflight "..." --package whatever
```

Every Python `iterate` / `evolve` run now ends with a deterministic quality
phase: Forge adds conservative missing docstrings, writes `docs/API.md` and
`docs/TESTING.md`, and creates `tests/test_generated_smoke.py` so the
package has import-smoke coverage even when the model forgets tests. These
generated tests are a floor; add behavior tests for real inputs before
shipping.

### Chat copilot

Use your configured AI agent as a Forge-aware terminal copilot. The chat
surface uses the same provider layer as `iterate` and `evolve`, and can pack
bounded repo context without sending `.env` or obvious secret files.

```bash
# One-shot question with repo context
forge chat ask "what should I run before release?" --context .

# Interactive session against your AAAA-Nexus agent
export AAAA_NEXUS_API_KEY=...
forge chat repl --provider nexus --context src --context docs

# Offline smoke test for scripts / CI
forge chat ask "hello" --provider stub --no-cwd-context --json
```

### LLM provider matrix

| Provider | Cost | Env var | Default model | When to use |
|----------|------|---------|---------------|-------------|
| `gemini` | **free tier** | `GEMINI_API_KEY` / `GOOGLE_API_KEY` | `gemini-2.5-flash` | Best free cloud option; override with `FORGE_GEMINI_MODEL` |
| `nexus` / `aaaa-nexus` | paid | `AAAA_NEXUS_API_KEY` | (Nexus default) | AAAA-Nexus sovereign AI; most reliable for long runs |
| `anthropic` | paid | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-latest` | Highest code quality |
| `openai` | paid | `OPENAI_API_KEY` | `gpt-4o-mini` | Cheap GPT path |
| `openrouter` | **free tier available** | `OPENROUTER_API_KEY` | `google/gemma-3-27b-it:free` | Access 200+ models; good fallback when Gemini quota exhausted; override with `FORGE_OPENROUTER_MODEL` |
| `ollama` | free, local | `FORGE_OLLAMA=1` | `qwen2.5-coder:7b` | Offline; fully private |
| `stub` | free, offline | n/a | n/a | Tests, CI, dry-runs |

`--provider auto` resolves in the code-defined order:
AAAA-Nexus, Anthropic, Gemini, OpenAI, OpenRouter, Ollama, then `stub`.
Explicit `--provider gemini` (or any other provider name) always wins.

For busy laptops or desktops, run Ollama with the small local profile:

```bash
export FORGE_OLLAMA=1
export FORGE_OLLAMA_MODEL=qwen2.5-coder:1.5b
export FORGE_OLLAMA_NUM_PREDICT=768
export FORGE_OLLAMA_TIMEOUT=180
forge chat ask "what should I fix next?" --provider ollama --context src
```

Use `qwen2.5-coder:7b` when the machine is idle and you want better code
quality. `FORGE_OLLAMA_NUM_PREDICT` caps each generation; lower it if
Ollama starts paging or crashing. `FORGE_OLLAMA_TIMEOUT` controls how long
Forge waits before returning a clear provider error.

## Commands: The absorb pipeline

**Flagship:** `forge auto` does everything in one shot.

| Command | Purpose | Typical use |
|---------|---------|-------------|
| **`forge auto`** | Scout → cherry-pick → materialize → wire → certify. *The main verb.* | `forge auto ./repo ./out --apply` |
| `forge recon` | Walk a repo, classify every symbol. Shows tier distribution. | `forge recon ./repo` |
| `forge cherry` | Build a cherry-pick manifest. Select specific symbols or `--pick all`. | `forge cherry ./repo --pick all` |
| `forge finalize` | Materialize, wire, certify. Run separately if needed. | `forge finalize ./repo ./out --apply` |
| `forge wire` | Scan a tier tree for upward-import violations. | `forge wire ./out/src/package` |
| `forge certify` | Score: documentation, tests, tier layout, import discipline. Use `--fail-under` for CI gates. | `forge certify ./out --package my_pkg --fail-under 90` |

### Specialty commands (LLM loops & composition)

| Command | Purpose |
|---------|---------|
| `forge iterate` | LLM loop: intent → code → absorb → wire → score → iterate. Single shot. |
| `forge evolve` | Recursive improvement: N rounds of iterate, catalog grows each round. |
| `forge chat` | Terminal copilot over Forge docs/source using the same AI provider layer. |
| `forge emergent` | Symbol-level composition discovery (find hidden wiring patterns). |
| `forge synergy` | Feature-pair detection + auto-generate adapters. |
| `forge commandsmith` | Auto-register CLI commands, regenerate `_registry.py`. |

## Targeted workflows

```bash
# Targeted: just see what's in a repo
forge recon ./repo

# Targeted: pick specific symbols
forge cherry ./repo --pick infer_tier --pick CherryPicker

# Targeted: merge two repos with conflict resolution
forge cherry ./repo-a --pick all
forge finalize ./repo-a ./out --apply --on-conflict rename

# Specialty: surface compositions across your own catalog
forge emergent scan
```

## Known limits (honest & concrete)

Forge ships with named limits. No overpromise.

1. **Python and JavaScript/TypeScript today; Rust / Go on the roadmap.** As of 0.2, `recon`, `wire`, and `certify` classify `.py`, `.js`, `.mjs`, `.cjs`, `.jsx`, `.ts`, and `.tsx`. The runtime-import smoke check (the +25 score component for "package actually loads in a fresh subprocess") and the behavioural pytest gate remain Python-only — JS/TS packages are scored on documentation, tests-present, tier layout, and upward-import discipline. The JS parser is regex + brace-walking, not a real AST; it handles the surface (imports, exports, class signals, Worker default-`{ fetch, scheduled }` shape) the tier law cares about.

2. **Building material, not shipping software.** `forge auto` output is a **tier-organised starter skeleton**, not a deployable app. Every `--apply` emits `STATUS.md` listing required follow-up:
   - Integration tests against real inputs
   - Runtime configuration (secrets, env vars, DB URLs)
   - Observability (logging, metrics, tracing)
   - Cross-symbol reconciliation (two `User` classes need unification, not duplication)

3. **Tier classification is heuristic.** Forge uses word-boundary tokens + body-state detection (mutable instance variables in Python; class declarations + module-level `let`/`var` in JS). The scout report logs the rationale per symbol so you can override misclassifications via `--override-tier`.

4. **No semantic merge.** Two `class User` from different repos don't auto-unify. Forge detects the collision via `--on-conflict` (rename | first | last | fail) and reports it. **You** decide how to reconcile.

5. **Auto-generated adapters are scaffolding.** The `synergy` pipeline emits adapters marked with `# REVIEW:` blocks. Read them. Refine them. They're templates, not production code.

6. **Certificates are not yet signed.** The conformance schema is finalized. Cryptographic signing remains on the 0.3 roadmap.

## Design philosophy

- **Absorb-first, generate-never.** Forge never writes code from scratch. It absorbs and reorganises code that already exists — including AI-generated code.

- **Dry-run by default.** No verb writes to disk without `--apply` or equivalent. Only `.atomadic-forge/` manifests (diagnostic reports) are written in dry-run mode.

- **The 5-tier law is non-negotiable.** Anything that ships with Forge passes its own `wire` scan. Forge's 53 source files live in a0–a4; it eats its own dogfood.

- **Honest output.** Every report includes `schema_version`. Every apply emits `STATUS.md` (required follow-up). Every artifact is provable and traced (lineage recorded in `.atomadic-forge/lineage.jsonl`).

- **Composability, not coupling.** Forge outputs JSON manifests at each stage (scout, cherry, assimilate, wire, certify). Pipe them. Script them. Build on them.

## Atomadic family

| Product | What it is | Status |
|---------|------------|--------|
| **AAAA-Nexus** | Trust/safety/payments substrate for autonomous agents | Live at [atomadic.tech](https://atomadic.tech) |
| **Atomadic Forge** | Absorb-and-emerge engine for developers (this repo) | v0.3.0 (21 MCP tools · `.forge` sidecar v1.0 · `forge-lsp` · 702 tests) |
| **Atomadic Assistant** | Sovereign AI assistant with cognitive loop on Cloudflare | In development |

## License

[Business Source License 1.1](LICENSE). Free for non-production use.
Commercial license required for production. Change Date: 2030-04-27 →
Apache 2.0.

## Documentation

- **[Showcase](docs/SHOWCASE.md)** — Live runs with live results (start here)
- **[Landscape](docs/LANDSCAPE.md)** — How Forge sits next to Cursor / Devin / Lovable / Copilot Workspace
- **[Why now](docs/WHY_NOW.md)** — The urgency case for an architecture substrate
- **[Commands](docs/COMMANDS.md)** — Full reference for all 13+ verbs
- **[Release checklist](docs/RELEASE_CHECKLIST.md)** — Shippability gates, CLI scenarios, local-model smoke checks
- **[Roadmap](docs/ROADMAP.md)** — 0.2 / 0.3 / 1.0 milestones
- **[Architecture guide](ARCHITECTURE.md)** — How Forge itself is built (monadic tiers, data flows, design)
- **[Security policy](SECURITY.md)** — Private vulnerability reporting and secret-handling expectations
- **[Tutorials](docs/tutorials/)** — Quickstart, your-first-package, the 5-tier law, plug-in-LLMs, multi-repo absorb
- **[Contributing guide](CONTRIBUTING.md)** — How to extend Forge
- **[Changelog](CHANGELOG.md)** — Version history and roadmap

## For developers

**Forge itself is monadic.** Every source file belongs to one tier. The repo is a worked example:

```bash
python -m pytest tests/          # 308 passing, 2 skipped
python -m atomadic_forge doctor  # Environment check
python -m atomadic_forge wire src/atomadic_forge  # Scan for violations
python -m atomadic_forge certify . --fail-under 100  # Score and gate the repo
```

**Before submitting a PR:**
1. Run the test suite — must pass
2. Run `ruff check src/ tests/` — code style check
3. Run `forge wire src/atomadic_forge` — import discipline
4. Update CHANGELOG.md

## Status

**Experimental, working, honest.**

- ✓ Tested end-to-end on its own codebase
- ✓ Tested on reference Python and JavaScript / TypeScript repos
- ✓ 308 tests, all passing (2 skipped)
- ✓ Schema finalized (conformance, lineage, scaffold)
- ✓ Polyglot — Python + JavaScript + TypeScript classified by the same 5-tier law (0.2)
- ✗ Not yet on PyPI (coming soon)
- ✗ Cryptographic signing (0.3)
