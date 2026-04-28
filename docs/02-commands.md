# Command Reference

All Forge commands are available via `forge VERB [OPTIONS] [ARGS]`.

For help: `forge --help` or `forge VERB --help`.

## Setup and configuration

### forge init

**Start here.** Interactive 5-step wizard that configures your LLM provider, API keys, project defaults, and writes `.atomadic-forge/config.json`.

```bash
forge init
```

**What it does (5 steps):**

1. **LLM Provider** — choose Ollama, Gemini, Claude, OpenAI, or Auto
2. **Model selection** — lists available Ollama models; recommends cloud models
3. **API key** — masked password input with immediate validation (skipped for Ollama/Auto)
4. **Project defaults** — target score, auto-apply flag, output/source directories
5. **Verification** — tests the LLM connection and prints a configuration summary

**Example flow:**

```
╭─ Atomadic Forge — Setup   [Step 1/5: LLM Provider] ─╮
│                                                       │
│  [1] Ollama (local, free, private)                    │
│  [2] Gemini (Google)                                  │
│  [3] Claude (Anthropic)                               │
│  [4] OpenAI (GPT)                                     │
│  [5] Auto (detect best available)                     │
│                                                       │
╰───────────────────────────────────────────────────────╯
Select provider [5]:
```

After all steps, a summary panel is printed and config is saved to `.atomadic-forge/config.json`.

**Notes:**
- Completely safe to re-run; existing values are offered as defaults at every prompt.
- Use `forge config wizard` for the same wizard from within the `config` sub-group.
- Config priority: local `.atomadic-forge/config.json` → global `~/.atomadic-forge/config.json` → built-in defaults.

---

### forge config

Config management sub-group: show, set, test, wizard.

```bash
forge config SUBCOMMAND [OPTIONS]
```

**Subcommands:**

#### forge config show

Print the current merged configuration (local → global → defaults).

```bash
forge config show [--project DIR] [--json]
```

**Options:**
- `--project DIR` — project directory to load local config from (default: cwd)
- `--json` — emit a JSON object `{config: {...}, issues: [...]}`

**Example:**

```bash
forge config show
# Output:
# Atomadic Forge — config
# --------------------------------------------
#   provider                     auto
#   ollama_url                   http://localhost:11434
#   ollama_model                 mistral:7b-instruct
#   gemini_key                   (not set)
#   default_target_score         75.0
#   auto_apply                   False
#   output_dir                   ./forged
#   sources_dir                  ./sources
#   package_prefix               forged
#
#   Config is valid.

forge config show --json
```

API keys are automatically masked (first 8 + last 4 chars) in human-readable output.

---

#### forge config set

Set a single config key in the local (or global) config file.

```bash
forge config set KEY VALUE [--project DIR] [--global]
```

**Arguments:**
- `KEY` — config key to set (e.g. `provider`, `ollama_model`, `default_target_score`)
- `VALUE` — value to assign (automatically coerced: `true`/`false` → bool, numeric → int/float)

**Options:**
- `--project DIR` — project directory (default: cwd)
- `--global` — write to `~/.atomadic-forge/config.json` instead of `.atomadic-forge/config.json`

**Examples:**

```bash
# Set provider for this project
forge config set provider ollama

# Set target score (auto-coerced to float)
forge config set default_target_score 80.0

# Enable auto-apply globally
forge config set auto_apply true --global

# Set Ollama model
forge config set ollama_model qwen2.5-coder:7b
```

---

#### forge config test

Test the configured LLM provider connection.

```bash
forge config test [--project DIR] [--provider PROVIDER] [--json]
```

**Options:**
- `--provider PROVIDER` — override the configured provider for this test only
- `--project DIR` — project directory (default: cwd)
- `--json` — emit `{ok, model, error, latency_ms}`

**Examples:**

```bash
# Test whatever provider is configured
forge config test

# Test a specific provider
forge config test --provider ollama
forge config test --provider stub   # always succeeds, no network call

# JSON output (good for scripting)
forge config test --json
```

**Output:**

```
Provider test — ollama

  Status:    OK
  Model:     mistral:7b-instruct
  Latency:   143ms
```

---

#### forge config wizard

Same as `forge init` — runs the interactive 5-step setup wizard.

```bash
forge config wizard [--project DIR]
```

---

## Core commands (the absorb pipeline)

### forge auto

**Flagship command.** Scout → cherry-pick → materialize → wire → certify in one shot.

```bash
forge auto TARGET OUTPUT [OPTIONS]
```

**Arguments:**
- `TARGET` — Path to source repository to absorb
- `OUTPUT` — Path where materialized tier tree will be written

**Options:**
- `--package NAME` — Python package name (default: `absorbed`)
- `--apply` — Actually write files (default: dry-run)
- `--on-conflict STRATEGY` — How to handle name collisions: `rename` | `first` | `last` | `fail` (default: `rename`)
- `--json` — Output JSON instead of human-readable

**Example:**

```bash
# Dry-run: see what would happen
forge auto ./legacy-repo ./output

# Actually apply
forge auto ./legacy-repo ./output --apply --package myapp

# Apply with conflict strategy
forge auto ./repo-a ./output --apply --package merged --on-conflict rename
```

**Output:**
- Materialized tier tree at `output/src/PACKAGE/`
- STATUS.md listing required follow-up
- .atomadic-forge/ diagnostics (scout, cherry, assimilate, wire, certify)

---

### forge recon

Walk a repository, classify every public symbol, show tier/effect
distributions. Polyglot: walks Python (`.py`), JavaScript
(`.js`/`.mjs`/`.cjs`/`.jsx`), and TypeScript (`.ts`/`.tsx`) in a single
pass; `node_modules/`, `dist/`, `.next/`, `.wrangler/` and friends are
skipped automatically.

```bash
forge recon TARGET [OPTIONS]
```

**Arguments:**
- `TARGET` — Path to repository to analyze

**Options:**
- `--json` — Output full JSON report (includes per-symbol rationale and `suggested_tier`)

**Example (Python repo):**

```bash
forge recon ./repo
# Recon: ./repo
# ------------------------------------------------------------
#   python files:     45
#   javascript files: 0
#   typescript files: 0
#   primary language: python
#   symbols:          222
#   tier dist:        {a0: 7, a1: 130, a2: 42, a3: 32, a4: 11}
#   effect dist:      {pure: 210, state: 0, io: 12}
```

**Example (JavaScript / Cloudflare Worker repo):**

```bash
forge recon ./my-worker
# Recon: ./my-worker
# ------------------------------------------------------------
#   python files:     0
#   javascript files: 4
#   typescript files: 1
#   primary language: javascript
#   symbols:          17
#   tier dist:        {a0: 1, a1: 2, a2: 1, a4: 1}
#   effect dist:      {pure: 9, state: 5, io: 3}
#   recommendations:
#     - JS/TS files are not yet split into aN_* tier directories —
#       see suggested_tier per file in symbols[].
```

The JSON output contains a `language_distribution` map keyed by
`"python"` / `"javascript"` / `"typescript"`, and per-symbol
`suggested_tier` so you can see where Forge would place each file under
the 5-tier law.

```bash
forge recon ./repo --json > report.json
```

---

### forge cherry

Build a cherry-pick manifest (which symbols to absorb).

```bash
forge cherry TARGET [OPTIONS]
```

**Arguments:**
- `TARGET` — Path to repository

**Options:**
- `--pick all` — Include all symbols (default)
- `--pick QUALNAME` — Include specific symbol (repeat to add more)

**Example:**

```bash
# Pick all symbols
forge cherry ./repo --pick all

# Pick specific symbols only
forge cherry ./repo --pick Module.function --pick Class
```

**Output:**
- Cherry manifest at `.atomadic-forge/cherry.json`

---

### forge finalize

Materialize, wire, certify (the second half of the absorb pipeline).

Useful if you want to customize the cherry-pick before materialization.

```bash
forge finalize TARGET OUTPUT [OPTIONS]
```

**Arguments:**
- `TARGET` — Repository or path with `.atomadic-forge/cherry.json`
- `OUTPUT` — Destination for materialized tree

**Options:**
- `--apply` — Write files
- `--package NAME` — Python package name

**Example:**

```bash
# Step 1: Scout and cherry-pick
forge recon ./repo
forge cherry ./repo --pick all

# Step 2: Materialize
forge finalize ./repo ./output --apply --package myapp
```

---

### forge wire

Scan a tier-organized package for upward-import violations. Polyglot —
detects violations in Python `from`-imports and JS/TS module specifiers
(`"../a3_og_features/foo"`) alike. `node_modules/` is skipped.

```bash
forge wire PACKAGE [OPTIONS]
```

**Arguments:**
- `PACKAGE` — Path to tier-organized package root (a0, a1, a2, a3, a4 directories)

**Options:**
- `--json` — Output JSON violation list (each violation includes `language: "python" | "javascript" | "typescript"`)

**Example (Python):**

```bash
forge wire ./output/src/myapp

# Wire scan: ./output/src/myapp
#   verdict:    FAIL
#   violations: 5
#     - a1_at_functions/helper.py: a1 ← a2_mo_composites.Store (upward import)
#     - a0_qk_constants/config.py: a0 ← a1_at_functions.parse_config
#     ... (list of violations)
```

**Example (JavaScript):**

```bash
forge wire ./packages/web

# Wire scan: ./packages/web
#   verdict:    FAIL
#   violations: 1
#     - a1_at_functions/echo.js: a1 ⟵ a3_og_features.../a3_og_features/feature.js
```

The JSON form makes the language explicit:

```json
{
  "schema_version": "atomadic-forge.wire/v1",
  "violations": [
    {
      "file": "a1_at_functions/echo.js",
      "from_tier": "a1_at_functions",
      "to_tier": "a3_og_features",
      "imported": "../a3_og_features/feature.js",
      "language": "javascript"
    }
  ],
  "verdict": "FAIL"
}
```

**What violations mean:**
- `a1 ← a2` — Function imports from Composite (illegal)
- `a0 ← a1` — Constant imports from Function (illegal)
- Other tiers can import upward but are constrained by their layer

**Fixing violations:**
Move the offending import to a higher tier, or move the imported symbol to a lower tier.

---

### forge certify

Score conformance: documentation, tests, tier layout, import discipline,
runtime importability (Python only), and behavioural pytest pass-ratio
(Python only). Polyglot-aware where it can be:

- `tests` PASS recognises Python (`tests/test_*.py`, `*_test.py`) AND
  JavaScript / TypeScript (`tests/*.test.{js,mjs,jsx,cjs,ts,tsx}`,
  `*.spec.*`, and the Jest `__tests__/` directory convention).
- `tier_layout` PASS counts JS-style top-level or nested `aN_*`
  directories anywhere under the repo root, not just under
  `src/<pkg>/`. Failure messages name how many tiers were found and
  which (e.g. *"found 2 tier directories (a1_at_functions,
  a4_sy_orchestration); need 3+"*).
- The runtime-import smoke (+25 points, runs `python -c "import <pkg>"`
  in a fresh subprocess) and the behavioural pytest gate (+30 points)
  remain Python-only. JS/TS-only packages are scored on the +45
  polyglot-aware structural axes (docs / tests-present / tier layout /
  upward-import discipline).

```bash
forge certify OUTPUT [OPTIONS]
```

**Arguments:**
- `OUTPUT` — Path to materialized tree (or root with `--package`)

**Options:**
- `--package NAME` — Python package name (if not in root)
- `--json` — Output JSON

**Example:**

```bash
forge certify ./output --package myapp

# Output:
# Certify: myapp
#   documentation: 25/25 ✓ (README.md present)
#   tests:         25/25 ✓ (tests/ directory present)
#   tier_layout:   25/25 ✓ (5/5 tiers used)
#   import_discipline: 0/25 ✗ (5 violations from wire)
#   
#   TOTAL: 75/100 (needs work: fix upward imports)
```

**Scoring:**
- 25 points each for: documentation, tests, tier layout, import discipline
- 100/100 = gold standard
- ≥75 = acceptable for production
- <50 = needs significant work

---

## LLM loop commands

### forge iterate

LLM loop: user intent → code → absorb → wire → score → iterate.

Single shot (one user prompt → N iterations → done).

```bash
forge iterate SUBCOMMAND [OPTIONS]
```

**Subcommands:**
- `run "INTENT" OUTPUT` — Execute the loop
- `preflight "INTENT"` — Dry-run (show system prompt + first user prompt, no LLM call)

**Options (for `run`):**
- `--package NAME` — Python package name
- `--provider PROVIDER` — LLM provider: `gemini` | `anthropic` | `openai` | `ollama` | `stub` | `auto` (default: `auto`)
- `--max-iterations N` — Max rounds (default: 4)

**Environment variables:**
- `GEMINI_API_KEY` — For `--provider gemini`
- `ANTHROPIC_API_KEY` — For `--provider anthropic`
- `OPENAI_API_KEY` — For `--provider openai`
- `FORGE_OLLAMA=1` — Enable Ollama (must be running on localhost:11434)

**Example:**

```bash
export GEMINI_API_KEY=your-key-here

# Dry-run: see system prompt + first user message
forge iterate preflight "Build a tiny calculator CLI"

# Execute with Gemini (free tier)
forge iterate run "Build a tiny calculator CLI" ./output \
    --package calc --provider gemini --max-iterations 4

# Execute with Claude (paid)
export ANTHROPIC_API_KEY=sk-...
forge iterate run "..." ./output --provider anthropic

# Use local Ollama (free, fully private)
# First: ollama run qwen2.5-coder:7b
forge iterate run "..." ./output --provider ollama
```

**Output:**
- Materialized code at `output/src/PACKAGE/`
- Transcript of LLM loop iterations in `iterate.json`
- Wire violations and certify scores logged per round

---

### forge evolve

Recursive self-improvement: N rounds of `iterate`, catalog grows each round.

```bash
forge evolve SUBCOMMAND [OPTIONS]
```

**Subcommands:**
- `run "INTENT" OUTPUT` — Execute N rounds

**Options:**
- `--auto N` — Run exactly N rounds
- `--target-score SCORE` — Keep improving until reaching score (default: none)
- `--package NAME` — Python package name
- `--provider PROVIDER` — LLM provider (see `iterate`)

**Example:**

```bash
# Run exactly 5 rounds
forge evolve run "Build a markdown-to-PDF service" ./output \
    --auto 5 --provider gemini --package pdf_service

# Run until reaching score of 80/100
forge evolve run "..." ./output \
    --target-score 80 --provider gemini
```

**How it works:**
1. Round 1: Generate initial code from intent
2. Round 2: Absorb round 1 code, identify missing pieces, generate new features
3. Round 3: Absorb rounds 1+2, improve further
4. ... repeat until `--auto N` rounds or `--target-score` reached

**Output:**
- Final merged code at `output/src/PACKAGE/`
- Per-round reports showing score trajectory
- Halt reason (`rounds_exhausted` | `target_score_reached` | `stagnation_detected`)

---

## Specialty commands

### forge emergent

Symbol-level composition discovery — find chains where output of A flows into B.

```bash
forge emergent SUBCOMMAND [OPTIONS]
```

**Subcommands:**
- `scan [PACKAGE]` — Scan a tier tree, return composition chains

**Example:**

```bash
forge emergent scan ./output/src/myapp
# Returns: Chains where the return type of func A is input type to func B
```

---

### forge synergy

Feature-level producer/consumer detection + auto-generate adapters.

```bash
forge synergy SUBCOMMAND [OPTIONS]
```

**Subcommands:**
- `scan [PACKAGE]` — Detect synergies (5 kinds: json_artifact, in_memory_pipe, etc.)
- `implement` — Auto-generate adapter modules (marked with `# REVIEW:`)

**Example:**

```bash
forge synergy scan ./output/src/myapp
forge synergy implement ./output/src/myapp
```

---

### forge commandsmith

Auto-register CLI commands and regenerate `_registry.py`.

```bash
forge commandsmith SUBCOMMAND [OPTIONS]
```

**Subcommands:**
- `discover` — Find all CLI commands in `commands/`
- `sync` — Regenerate registry + docs + smoke-test results

**Example:**

```bash
forge commandsmith sync ./output/src/myapp
```

---

## Utility commands

### forge doctor

Print environment diagnostic.

```bash
forge doctor
```

**Output:**
```
Atomadic Forge — doctor
  atomadic_forge_version   0.1.0
  python                   3.12.10
  executable               /usr/bin/python3.12
  platform                 linux
  stdout_encoding          utf-8
```

---

## Global options

All commands support:
- `--help` — Show help text
- `--version` — Print version and exit

## Exit codes

- 0 — Success
- 1 — Error (see stderr)
- 2 — Usage error (wrong args)
