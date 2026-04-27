# Atomadic Forge

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: BSL-1.1](https://img.shields.io/badge/License-BSL--1.1-yellow.svg)](LICENSE)
[![Tests: 90 passing](https://img.shields.io/badge/Tests-90%20passing-green.svg)](tests/)

**The Architecture Compiler.** Absorbs Python codebases. Rebuilds into certified monadic structure. Enforces the 5-tier law across every file.

```bash
forge auto ./messy-repo ./out          # Dry-run: what would happen?
forge auto ./messy-repo ./out --apply  # Actually materialize
```

**What Forge does:**
- Walks any Python repo, classifies every symbol into one of 5 architectural tiers
- Materializes into a tier-organized tree with strict upward-only imports
- Detects architecture violations (upward imports, misclassified symbols)
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

Every Python file belongs to exactly one tier. **Tiers compose upward only** — never sideways, never downward.

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

1. **Python only (for now).** TypeScript / Rust / Go are on the roadmap. The monadic tiers are language-agnostic; the 0.1 AST walker is Python-specific.

2. **Building material, not shipping software.** `forge auto` output is a **tier-organised starter skeleton**, not a deployable app. Every `--apply` emits `STATUS.md` listing required follow-up:
   - Integration tests against real inputs
   - Runtime configuration (secrets, env vars, DB URLs)
   - Observability (logging, metrics, tracing)
   - Cross-symbol reconciliation (two `User` classes need unification, not duplication)

3. **Tier classification is heuristic.** Forge uses word-boundary tokens + body-state detection (mutable instance variables). The scout report logs the rationale per symbol so you can override misclassifications via `--override-tier`.

4. **No semantic merge.** Two `class User` from different repos don't auto-unify. Forge detects the collision via `--on-conflict` (rename | first | last | fail) and reports it. **You** decide how to reconcile.

5. **Auto-generated adapters are scaffolding.** The `synergy` pipeline emits adapters marked with `# REVIEW:` blocks. Read them. Refine them. They're templates, not production code.

6. **Certificates are not yet signed.** The conformance schema is finalized. Cryptographic signing ships in 0.2.

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
| **Atomadic Forge** | Absorb-and-emerge engine for developers (this repo) | 0.1.0 |
| **Atomadic Assistant** | Sovereign AI assistant with cognitive loop on Cloudflare | In development |

## License

[Business Source License 1.1](LICENSE). Free for non-production use.
Commercial license required for production. Change Date: 2030-04-27 →
Apache 2.0.

## Documentation

- **[Architecture guide](ARCHITECTURE.md)** — How Forge itself is built (monadic tiers, data flows, design)
- **[Contributing guide](CONTRIBUTING.md)** — How to extend Forge
- **[Changelog](CHANGELOG.md)** — Version history and roadmap

## For developers

**Forge itself is monadic.** Every source file belongs to one tier. The repo is a worked example:

```bash
python -m pytest tests/          # 90 tests, all passing
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
- ✓ Tested on reference Python repos
- ✓ 90 tests, all passing
- ✓ Schema finalized (conformance, lineage, scaffold)
- ✗ Not yet on PyPI (coming soon)
- ✗ Cryptographic signing (0.2)
