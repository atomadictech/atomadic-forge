# Command Reference

All Forge commands are available via `forge VERB [OPTIONS] [ARGS]`.

For help: `forge --help` or `forge VERB --help`.

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

Walk a repository, classify every public symbol, show tier/effect distributions.

```bash
forge recon TARGET [OPTIONS]
```

**Arguments:**
- `TARGET` — Path to repository to analyze

**Options:**
- `--json` — Output full JSON report (includes per-symbol rationale)

**Example:**

```bash
forge recon ./repo
# Output:
# Recon: ./repo
# ----
#   python files: 45
#   symbols:      222
#   tier dist:    {a0: 7, a1: 130, a2: 42, a3: 32, a4: 11}
#   effect dist:  {pure: 210, state: 0, io: 12}

forge recon ./repo --json > report.json
# Full report with classification rationale per symbol
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

Scan a tier-organized package for upward-import violations.

```bash
forge wire PACKAGE [OPTIONS]
```

**Arguments:**
- `PACKAGE` — Path to tier-organized package root (a0, a1, a2, a3, a4 directories)

**Options:**
- `--json` — Output JSON violation list

**Example:**

```bash
forge wire ./output/src/myapp

# Output:
# Wire scan: ./output/src/myapp
#   verdict:    FAIL
#   violations: 5
#     - a1_at_functions/helper.py: a1 ← a2_mo_composites.Store (upward import)
#     - a0_qk_constants/config.py: a0 ← a1_at_functions.parse_config
#     ... (list of violations)
```

**What violations mean:**
- `a1 ← a2` — Function imports from Composite (illegal)
- `a0 ← a1` — Constant imports from Function (illegal)
- Other tiers can import upward but are constrained by their layer

**Fixing violations:**
Move the offending import to a higher tier, or move the imported symbol to a lower tier.

---

### forge certify

Score conformance: documentation, tests, tier layout, import discipline.

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
