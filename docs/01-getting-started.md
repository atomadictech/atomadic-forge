# Getting Started with Atomadic Forge

## What is Forge?

Forge absorbs Python repositories and rebuilds them into certified monadic structure. It enforces the 5-tier architectural law across every file, detects violations, and scores conformance.

**Key insight:** Forge is an architecture compiler, not a code generator. It reorganizes existing code.

## Before you start

- Python 3.10+
- pip or conda
- A Python repository you want to reorganize (or an LLM API key / local Ollama for code generation)

## Installation

```bash
# From PyPI (when available)
pip install atomadic-forge

# Or from source (development)
git clone https://github.com/atomadictech/atomadic-forge
cd atomadic-forge
pip install -e ".[dev]"
python -m pytest tests/  # Verify: 150 tests pass
```

## Step 0: Configure Forge (do this first)

Before running any Forge command, run the setup wizard. It takes 60 seconds and saves your LLM provider, API keys, and defaults so you never need to pass them on the command line.

```bash
forge init
```

The wizard walks you through 5 steps:

1. **LLM Provider** — Ollama (local, free), Gemini, Claude, OpenAI, or Auto
2. **Model** — lists available Ollama models; recommends best cloud model
3. **API key** — masked input, validated immediately (skipped for Ollama)
4. **Defaults** — target score, auto-apply toggle, output/source directories
5. **Verify** — tests the connection and prints a summary

Config is written to `.atomadic-forge/config.json` in the current directory.

```
╭─ Configuration Summary ──────────────────────────────╮
│                                                       │
│  Provider:      Ollama                                │
│  Model:         mistral:7b-instruct                   │
│  URL:           http://localhost:11434                 │
│  Target Score:  75/100                                │
│  Auto-Apply:    No (dry-run by default)               │
│  Output Dir:    ./forged                              │
│  Sources Dir:   ./sources                             │
│  Config File:   .atomadic-forge/config.json           │
│                                                       │
│  ✓ LLM connection tested — OK (245ms)                │
│  ✓ Python 3.12 detected                               │
│  ✓ Config saved                                       │
│                                                       │
╰───────────────────────────────────────────────────────╯
```

You can view or change individual settings at any time:

```bash
forge config show                          # print current config
forge config set provider ollama           # change provider
forge config set default_target_score 80   # change threshold
forge config test                          # test connection
```

## Your first run (5 minutes)

### 1. Analyze a repository (dry-run)

```bash
forge auto /path/to/any-python-repo ./output
```

This runs **completely safely** — nothing is written except to a temporary `.atomadic-forge/` diagnostic directory. You'll see:

```
Atomadic Forge — auto pipeline (DRY-RUN)
  source:        /path/to/any-python-repo
  destination:   ./output/absorbed
  symbols:       N
  cherry-picked: N
  components:    N
  tier_dist:     {a0: X, a1: Y, a2: Z, ...}
  wire verdict:  DRY_RUN
  certify score: 0/100

  (re-run with --apply to write the materialized tree)
```

### 2. Understand the analysis

```bash
forge recon /path/to/any-python-repo
```

Prints a human-readable summary:
- How many files in the repo
- How many public symbols detected
- Tier classification distribution (how many a0, a1, a2 symbols)
- Effect distribution (pure vs. stateful vs. I/O)

### 3. Commit to the rebuild

```bash
forge auto /path/to/any-python-repo ./output --apply --package my_project
```

Now Forge **actually writes**:
- `output/src/my_project/a0_qk_constants/` — Constants, enums, types
- `output/src/my_project/a1_at_functions/` — Pure functions
- `output/src/my_project/a2_mo_composites/` — Stateful classes
- `output/src/my_project/a3_og_features/` — Features
- `output/src/my_project/a4_sy_orchestration/` — CLI layer
- `output/STATUS.md` — What still needs work
- `output/.atomadic-forge/` — Provenance (scout, cherry, assimilate, certify reports)

### 4. Verify the result

```bash
# Check for import violations
forge wire ./output/src/my_project

# Score the result (docs, tests, layout, imports)
forge certify ./output --package my_project
```

Example output:

```
Wire scan: ./output/src/my_project
  verdict:    PASS (or FAIL with list of violations)
  violations: 0 (or N)

Certify: ./output/src/my_project
  documentation: 25/25 (README.md present)
  tests:         25/25 (tests/ directory present)
  tier_layout:   25/25 (all 5 tiers used)
  import_discipline: 0/25 (33 upward-import violations)
  
  TOTAL: 75/100
```

## Understanding the output

### The tier directories

Each tier contains a specific kind of code:

- **a0_qk_constants/** — Pure data: constants, enums, TypedDicts, config dataclasses. Zero logic, zero imports.
- **a1_at_functions/** — Pure stateless functions: validators, parsers, formatters. May import a0 only.
- **a2_mo_composites/** — Stateful classes: clients, registries, stores, managers. May import a0, a1.
- **a3_og_features/** — Feature modules combining composites. May import a0–a2.
- **a4_sy_orchestration/** — CLI commands, entry points, main orchestrators. May import a0–a3.

### STATUS.md

After `--apply`, Forge emits `STATUS.md` listing what still needs work:

1. Integration tests against real inputs
2. Runtime configuration (secrets, env vars, DB URLs)
3. Observability (logging, metrics, tracing)
4. Wire enforcement (if violations exist, fix them)
5. Certification (aim for ≥75/100 before shipping)

### .atomadic-forge/

This directory contains diagnostic JSON:

- `scout.json` — Symbol inventory, tier classifications, rationale
- `cherry.json` — Which symbols were cherry-picked
- `assimilate.json` — How symbols were materialized
- `wire.json` — Import violation scan results
- `certify.json` — Conformance scores
- `lineage.jsonl` — Append-only log of all artifacts created (provenance trail)

## Next steps

- Run `forge init` to configure your LLM provider (if you haven't already)
- Read the [Command Reference](02-commands.md) for details on each verb
- See [Tutorial: Absorb a Real Repo](03-tutorial.md) for a full walkthrough
- Learn [Advanced: LLM Loops](04-llm-loops.md) to generate code with Forge
- Check [FAQ & Troubleshooting](05-faq.md) for common issues

## Key concepts

**Dry-run by default:** No `--apply` means nothing is written (except diagnostics).

**Upward-only imports:** `a1` can never import from `a2–a4`. Violations are errors.

**Composition, not duplication:** Each tier uses verified building blocks from lower tiers. Higher tiers never reinvent logic.

**Honesty:** Every output includes a schema version and provenance. No black-box reports.
