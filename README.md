<p align="center">
  <img src="assets/Atomadic-Forge-01.png" alt="Atomadic Forge" width="720"/>
</p>

# Atomadic Forge

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: BSL-1.1](https://img.shields.io/badge/License-BSL--1.1-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-green.svg)](tests/)
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

## 90-second demo

```bash
pip install -e ".[dev]"
export GEMINI_API_KEY=$(your-free-key)   # https://aistudio.google.com/apikey

# LLM-driven Python packages (need an API key or local Ollama):
forge demo run --preset calc --provider gemini   # 30s, score 90/100
forge demo run --preset kv   --provider gemini   # ~70s, KvStore + tests + CLI
forge demo run --preset slug --provider gemini   # ~22s, regex slugifier

# Static polyglot showcases (no LLM key required — runs offline):
forge demo run --preset js-counter   # clean a0..a4 JS package; wire PASS, certify 60/100*
forge demo run --preset js-bad-wire  # JS package with an upward import — wire flags it
forge demo run --preset mixed-py-js  # Python tier + JS tier in the same root
```

The LLM presets produce real, importable, pip-installable Python packages
with auto-generated README, passing tests, and a logged transcript of
every LLM exchange. The polyglot showcase presets ship as pre-built
source — they exercise `recon → wire → certify` on existing code so you
can read the reports without spending a token. Live trajectories in
[`docs/SHOWCASE.md`](docs/SHOWCASE.md).

\* 60/100 is the honest ceiling for a JS-only package today. The +30
behavioural pytest axis remains Python-only; wiring `npm test` / Vitest
into that gate is on the 0.3 roadmap. The four polyglot-aware structural
checks (docs / tests-present / tier-layout / upward-import-discipline)
all PASS on `js-counter`. We're not going to fake the missing 30 points.

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
```

**What Forge does:**
- Walks any Python or JavaScript/TypeScript repo, classifies every symbol into one of 5 architectural tiers
- Materializes into a tier-organized tree with strict upward-only imports
- Detects architecture violations (upward imports, misclassified symbols) — Python or JS, same law
- Scores conformance: documentation, tests, tier layout, import discipline
- Works with AI-generated code — absorbs it, fixes the architecture, ships it

**What Forge does NOT do:**
- Write code from scratch (it absorbs and reorganizes existing code)
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

```bash
pip install atomadic-forge
```

Or, for development:

```bash
git clone https://github.com/atomadictech/atomadic-forge && cd atomadic-forge
pip install -e ".[dev]"
python -m pytest tests/        # Verify: 90 tests pass
python -m atomadic_forge --help
```

## Quick start (3 minutes)

```bash
# 1. Dry-run: what would Forge do to this repo?
forge auto /path/to/messy-repo ./output

# 2. Look at the analysis
forge recon /path/to/messy-repo

# 3. Actually apply the transformation
forge auto /path/to/messy-repo ./output --apply --package my_project

# 4. Check for import violations
forge wire ./output/src/my_project

# 5. Score the result (docs, tests, layout, imports)
forge certify ./output --package my_project
```

**What you get back:**
- `output/src/my_project/a0_qk_constants/` — Constants, enums, types
- `output/src/my_project/a1_at_functions/` — Pure helpers
- `output/src/my_project/a2_mo_composites/` — Stateful classes
- `output/src/my_project/a3_og_features/` — Features combining a2
- `output/src/my_project/a4_sy_orchestration/` — CLI entry points
- `output/STATUS.md` — What still needs work (tests, integration, config)
- `.atomadic-forge/` — Provenance: scout, cherry, assimilate, certify reports

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

### LLM provider matrix

| Provider | Cost | Env var | Default model | When to use |
|----------|------|---------|---------------|-------------|
| `gemini` | **free tier** | `GEMINI_API_KEY` | `gemini-2.5-flash` | Best free option; override with `FORGE_GEMINI_MODEL` |
| `anthropic` | paid | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-latest` | Highest code quality |
| `openai` | paid | `OPENAI_API_KEY` | `gpt-4o-mini` | Cheap GPT path |
| `ollama` | free, local | `FORGE_OLLAMA=1` | `qwen2.5-coder:7b` | Offline; fully private |
| `stub` | free, offline | n/a | n/a | Tests, CI, dry-runs |

`forge iterate` and `forge evolve` resolve providers in the order above when
`--provider auto` (the default) is used.  Explicit `--provider gemini` always
wins.

## Commands: The absorb pipeline

**Flagship:** `forge auto` does everything in one shot.

| Command | Purpose | Typical use |
|---------|---------|-------------|
| **`forge auto`** | Scout → cherry-pick → materialize → wire → certify. *The main verb.* | `forge auto ./repo ./out --apply` |
| `forge recon` | Walk a repo, classify every symbol. Shows tier distribution. | `forge recon ./repo` |
| `forge cherry` | Build a cherry-pick manifest. Select specific symbols or `--pick all`. | `forge cherry ./repo --pick all` |
| `forge finalize` | Materialize, wire, certify. Run separately if needed. | `forge finalize ./repo ./out --apply` |
| `forge wire` | Scan a tier tree for upward-import violations. | `forge wire ./out/src/package` |
| `forge certify` | Score: documentation, tests, tier layout, import discipline. | `forge certify ./out --package my_pkg` |

### Specialty commands (LLM loops & composition)

| Command | Purpose |
|---------|---------|
| `forge iterate` | LLM loop: intent → code → absorb → wire → score → iterate. Single shot. |
| `forge evolve` | Recursive improvement: N rounds of iterate, catalog grows each round. |
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
| **Atomadic Forge** | Absorb-and-emerge engine for developers (this repo) | 0.2.0 (polyglot — Python + JS/TS) |
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
- **[Roadmap](docs/ROADMAP.md)** — 0.2 / 0.3 / 1.0 milestones
- **[Architecture guide](ARCHITECTURE.md)** — How Forge itself is built (monadic tiers, data flows, design)
- **[Tutorials](docs/tutorials/)** — Quickstart, your-first-package, the 5-tier law, plug-in-LLMs, multi-repo absorb
- **[Contributing guide](CONTRIBUTING.md)** — How to extend Forge
- **[Changelog](CHANGELOG.md)** — Version history and roadmap

## For developers

**Forge itself is monadic.** Every source file belongs to one tier. The repo is a worked example:

```bash
python -m pytest tests/          # 212 tests, all passing
python -m atomadic_forge doctor  # Environment check
python -m atomadic_forge wire src/atomadic_forge  # Scan for violations
python -m atomadic_forge certify .  # Score the repo
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
- ✓ 212 tests, all passing
- ✓ Schema finalized (conformance, lineage, scaffold)
- ✓ Polyglot — Python + JavaScript + TypeScript classified by the same 5-tier law (0.2)
- ✗ Not yet on PyPI (coming soon)
- ✗ Cryptographic signing (0.3)
