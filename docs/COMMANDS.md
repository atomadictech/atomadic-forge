# Atomadic Forge — Command Reference

All verbs available in the `forge` CLI as of 0.2.2.

## Pipeline / absorption

### `forge auto SOURCE OUTPUT`

Flagship: scout → cherry-pick → assimilate → wire → certify in one shot.
Dry-run by default; `--apply` writes files. Walks `.py`, `.js`, `.mjs`,
`.cjs`, `.jsx`, `.ts`, `.tsx`. `node_modules/`, `dist/`, `.next/`,
`.wrangler/` and friends are skipped automatically.

```bash
forge auto ./legacy-repo ./out --package absorbed --apply
```

### `forge recon SOURCE`

Walk a repo, classify every public symbol by tier and effect, surface
recommendations. Writes `.atomadic-forge/scout.json`. Prints per-language
counts (`python files`, `javascript files`, `typescript files`) and a
`primary_language` verdict; emits a recommendation when JS/TS files exist
outside `aN_*` tier directories.

**Long-running progress (Lane B / Golden Path W2):** add `--progress`
to stream per-file scan status to stderr. Designed to feed the Forge
Studio progress pane and to make CI logs readable on 100K-LOC repos.

```bash
forge recon ./monorepo --progress 2>&1 | grep -v '^\[scout\]'   # detach progress from stdout
```

### `forge cherry SOURCE`

Build a cherry-pick manifest from the latest scout. Pass `--pick all` or
explicit qualnames.

### `forge finalize SOURCE OUTPUT`

Assimilate cherry-picked symbols + wire + certify. Honours `--on-conflict`
(`rename` / `first` / `last` / `fail` / `semantic`).

### `forge wire DIR`

Scan a tier-organized package for upward-import violations. Polyglot —
detects upward imports in JS/TS specifiers (`"../a3_og_features/foo"`)
and Python `from`-imports alike. Each violation in the JSON report
carries a `language` field (`"python"` / `"javascript"` / `"typescript"`).

**CI flags (Lane C / Golden Path W1):**
- `--fail-on-violations` — exits non-zero when any upward import is
  detected. Drop into `.github/workflows/*.yml` to gate every PR on
  monadic-law conformance.
- `--suggest-repairs` — emits a per-violation repair hint
  (move-target tier + suggested rename) and counts how many are
  auto-fixable. Populates the Receipt's `wire.auto_fixable` field.

```bash
forge wire src/atomadic_forge --fail-on-violations
forge wire src/atomadic_forge --suggest-repairs --json > wire.json
```

### `forge certify ROOT --package <name>`

Score docs, tests, layout, imports, importability, behavior, stub bodies.
Returns 0–100 honest score with component breakdown. Use
`--fail-under <score>` when this command should act as a CI gate.

**Receipt + signing flags (Lane A W1+W2 / Golden Path):**
- `--emit-receipt PATH` — writes a v1 Forge Receipt JSON to PATH.
  Auto-creates parent dirs. Schema at
  `a0_qk_constants/receipt_schema.py`; full spec in `docs/RECEIPT.md`.
- `--print-card` — prints the rendered 60×24 box-drawing card to
  stdout (the artifact the Lane E W2 viral demo screen-grabs).
- `--sign` — calls AAAA-Nexus `/v1/verify/forge-receipt` and embeds
  `{signature, key_id, issuer, issued_at_utc}` in the Receipt's
  `signatures.aaaa_nexus` block. Graceful-degradation on key /
  network / HTTP failures; never throws. Set `AAAA_NEXUS_API_KEY`.

```bash
forge certify . --emit-receipt out/receipt.json --sign --print-card
```

JS/TS-specific behaviour:
- `tests` PASS recognises `tests/*.test.{js,mjs,jsx,cjs,ts,tsx}`,
  `*.spec.*`, and the Jest `__tests__/` directory convention.
- `tier_layout` PASS counts JS-style top-level or nested `aN_*`
  directories anywhere under the repo root, not just under `src/<pkg>/`.
- The runtime-import smoke (+25 points) and behavioural pytest gate
  (+30 points) remain Python-only — JS/TS packages are scored on the
  +45 polyglot-aware structural axes.

## Audit / diff (Receipt-aware)

### `forge audit list` / `forge audit show <id>` / `forge audit log`

Surfaces the Vanguard lineage chain (Lane A / Golden Path W4) as a
verb. Each `forge auto` / `forge certify` run appends to
`.atomadic-forge/lineage.jsonl`; the `audit` family reads it.

- `forge audit list` — shows the most recent N entries with their
  cycle id, action, verdict, and certify score.
- `forge audit show <id>` — full record for a single entry, including
  the artifacts it referenced and the Receipt it produced.
- `forge audit log` — streams the full JSONL file (pipe-friendly for
  `jq`).

```bash
forge audit list --limit 20
forge audit show 7cd840a-fb89-4d61-a712-…
forge audit log | jq 'select(.verdict == "FAIL")'
```

### `forge diff MANIFEST_A MANIFEST_B`

Compare two `.atomadic-forge/scout.json` (or `certify.json`) manifests.
Schema-aware: reports added / removed / moved symbols, tier-distribution
deltas, effect-distribution deltas, and certify-score deltas with
component breakdown. The output feeds Lane B's "Shadow Merge" view in
Forge Studio (W8) and Lane E's PR-comment delta on the Forge Action.

```bash
forge diff baseline/scout.json head/scout.json --json > delta.json
```

### `forge enforce DIR`

F-code-routed mechanical fixer (Lane A W6 / Golden Path). Reads the
wire report, plans `EnforceAction`s keyed by F-code, applies them with
rollback safety. Each action records its undo so a failed apply leaves
the tree in its prior state.

Currently routes:
- **F0042** (a1 upward import) → move the importing file up to the
  higher tier
- 6 other auto-fixable F-codes (covered by smoke tests)

```bash
forge wire src/atomadic_forge --suggest-repairs --json | forge enforce -
```

### F-codes — citeable error catalog (Lane A W5)

Every Forge error carries a stable 4-digit code of the form `F0042`.
F-codes are part of the schema contract:

- **Adding** an F-code is additive (minor version)
- **Removing** or **renumbering** is a **major version bump**
- The message string can change per locale; the F-code stays
- F-codes power `forge enforce`'s mechanical fix routing

Namespace allocation (defined at `a0_qk_constants/error_codes.py`):

| Range | Domain |
|---|---|
| F0001–F0009 | scout / classification (info) |
| F0010–F0019 | cherry-pick (warn) |
| F0040–F0049 | wire / upward-import violations |
| F0050–F0059 | certify axis failures |
| F0060–F0069 | stub detection |
| F0070–F0079 | import-repair |
| F0080–F0089 | assimilate conflicts |
| F0090–F0099 | receipt / signing |

## Agent integration (MCP)

### `forge mcp serve`

Exposes the entire Forge pipeline (Receipt, wire, certify, enforce,
audit_list) as an **MCP** (Model Context Protocol) server over stdio
JSON-RPC (Lane C W4 / Golden Path). Any coding agent that speaks MCP —
Cursor, Claude Code, Aider, Devin, Sweep — can `mcp.add atomadic-forge`
and consume Forge's normative architectural law as a first-class tool.

**5 tools** exposed: `recon`, `wire`, `certify`, `enforce`, `audit_list`.
**4 resources** exposed (Receipt JSON, lineage chain, F-code registry,
attestation pointers).

```bash
# One-round-trip smoke against any project (incl. Forge itself):
printf '%s\n%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  '{"jsonrpc":"2.0","id":3,"method":"shutdown"}' \
| forge mcp serve --project .
```

Returns server info, **10 tool schemas** (`recon`, `wire`, `certify`,
`enforce`, `audit_list`, `agent_summary`, `auto_plan`, `context_pack`,
`preflight_change`, `score_patch` — plus the four `plan_list` /
`plan_show` / `plan_step` / `plan_apply` verbs from Codex-3), and a
clean shutdown. The soft-fail contract from `receipt_signer.py`
applies — every tool gracefully degrades when an upstream (e.g.,
AAAA-Nexus signing) is unreachable.

What this unlocks per Golden Path Lane C: the Forge Receipt JSON
becomes consumable by every major coding-agent platform via the same
schema as `forge certify --emit-receipt` — *one Receipt across
terminal Card / PR comment / README badge / MCP resource / signed PDF
CS-1*. The convergence the BEP-1 cycle predicted is now empirically
reachable from `mcp.tools.list`.

### `forge plan` — the proposal-engine surface

Emits an `atomadic-forge.agent_plan/v1` JSON card — sister schema to
the Forge Receipt, tuned for proposal-engine mode. Returns a ranked
list of "next best action" cards instead of a giant manifest. Lane C
direction (Codex-2 follow-up).

```bash
forge plan . --json > plan.json
```

Each plan emits:

```json
{
  "schema_version": "atomadic-forge.agent_plan/v1",
  "verdict": "REFINE",
  "goal": "...",
  "top_actions": [
    {
      "id": "ci-release-hardening",
      "kind": "operational",
      "why": "Forge certify score blocked by missing CI",
      "write_scope": [".github/workflows/ci.yml", "CHANGELOG.md"],
      "risk": "low",
      "commands": ["python -m pytest", "forge certify ."],
      "applyable": true
    }
  ],
  "next_command": "forge plan apply ci-release-hardening --apply"
}
```

The `auto_plan` MCP tool returns the same JSON to a coding agent in
one round-trip. See [`docs/AGENTS_GUIDE.md`](AGENTS_GUIDE.md) for
agent flows that consume this surface.

### `forge plan-list` / `forge plan-show` / `forge plan-step` / `forge plan-apply`

Persistence + apply chain for the proposal-engine (Codex-3 follow-up).
Each `forge plan ... --save` writes a plan to
`.atomadic-forge/plans/<id>.json` (id is content-addressed, so
re-emitting an identical plan yields the same id — **re-emit-safe**).

```bash
# Save a fresh plan for later inspection
forge plan . --save --json > /dev/null

# List recent plans for this project
forge plan-list

# Read a saved plan card
forge plan-show <plan-id>

# Apply one card from a plan (rollback-safe)
forge plan-step <plan-id> <card-id> --apply

# Apply every card with applyable=true in one shot
forge plan-apply <plan-id> --apply
```

Apply routing (defined at `a3_og_features/forge_plan_apply.py`):
- **F0041–F0046** (architectural / wire violations) → `forge enforce --apply`
- **F0050** (docs missing) → bounded stub README writer
- All routes are **rollback-safe** — failed applies leave the tree
  untouched and the plan-state file records why.

State trace: every step / apply event is appended to
`.atomadic-forge/plans/<id>.state.json` so an agent can resume after a
failed apply or audit a historical plan.

### `forge context-pack [TARGET]` (Codex-4)

Emits an `atomadic-forge.context_pack/v1` JSON bundle — the single
command an active coding agent should run on **first orientation** to
a repo. Wraps scout + wire + certify and adds:

- `repo_purpose` — first paragraph of README, falling back to
  pyproject description, then dirname.
- `architecture_law` — pinned 5-tier law text (so the agent doesn't
  have to look it up).
- `tier_map`, `blockers_summary`, `best_next_action`.
- `test_commands` — detected from pyproject / tox.ini / package.json /
  Cargo.toml / Makefile.
- `release_gate` — the canonical `ruff && pytest && wire && certify
  ≥ 75` recipe.
- `risky_files`, `recent_lineage`, `pinned_resources`.

```bash
forge context-pack . --json > context.json
```

Agents that prefer MCP can call the matching `context_pack` tool over
JSON-RPC for the same payload in one round-trip.

### `forge preflight INTENT FILE...` (Codex-4)

Pre-edit guardrail. For each proposed file the agent intends to
write, emits `atomadic-forge.preflight/v1` with:

- `detected_tier` — by path-segment match against tier names.
- `forbidden_imports` — tiers above this file's tier (read-only, but
  the agent should treat as hard rules before drafting).
- `likely_tests` — mirror-style: `tests/test_<stem>.py`,
  `<stem>_test.py`, etc.
- `siblings_to_read` — first 5 `.py` siblings in the same dir.
- Overall `write_scope_too_broad` flag (default threshold = 8 files;
  override with `--scope-threshold N`).

```bash
forge preflight 'Add a parser helper' \
    src/atomadic_forge/a1_at_functions/parser.py
```

Exits **1** when `write_scope_too_broad` is true — designed to be
called from a pre-commit hook or an agent's tool-use loop. Add
`--json` for machine-readable output.

(`score_patch` — diff-scoring of a candidate unified-diff — is
intentionally MCP-only. Diff strings are awkward as positional CLI
args; agents pipe the diff through the `score_patch` MCP tool
instead.)

## Code generation (LLM-driven)

### `forge iterate run "INTENT" OUTPUT`

LLM ↔ Forge 3-way loop (wire + certify + emergent + reuse). Configurable
provider (`auto | gemini | nexus | aaaa-nexus | anthropic | openai | openrouter | ollama | stub`).
Pass `--seed PATH` (repeatable) to supply absorbed-repo symbol catalogs as
building-block hints for the LLM.

**Compiler Feedback Loop (Lane A W3 / Golden Path):** add
`--max-fix-rounds N` to drive a build-error → fix loop until 100%
compile or the round-budget is exhausted. The Compiler Agent (pure
helper at `a1_at_functions/compiler_feedback.py`) re-prompts the LLM
with the build's stderr until the emit compiles. Result report carries
a new `fix_rounds` field counting the fix iterations consumed.

```bash
forge iterate run "build a calculator CLI" ./out --provider gemini

# Multi-seed + compiler-loop: build from absorbed framework patterns
# and auto-recover from compile errors (up to 5 fix rounds per turn):
forge iterate run "build a tool-use agent" ./out \
    --seed ./forged/langchain-picks \
    --seed ./forged/mem0-picks \
    --provider nexus \
    --max-fix-rounds 5
```

### `forge evolve run "INTENT" OUTPUT --auto N`

Recursive self-improvement: N rounds of `iterate`, each round seeded by
the prior round's growing catalog. Halts on convergence, regression
(optional), or stagnation (3 flat rounds default).

### `forge demo run --preset NAME`

One-shot launch verb. Two preset families:

- **LLM-driven Python presets** (`calc`, `kv`, `slug`) — preset evolve +
  post-run CLI invocation + DEMO.md artifact. Each writes to
  `./forge-demo-<preset>/` and emits a stunning README synthesised from
  the actual emitted code. Requires an LLM (Gemini free tier, Ollama,
  Anthropic, OpenAI, or stub).
- **Static polyglot showcases** (`js-counter`, `js-bad-wire`,
  `mixed-py-js`) — pre-built source packages used to exercise
  `recon → wire → certify` on real JS/TS/polyglot code. **No LLM
  required.** Each writes a `DEMO.md` summarising the scan results.

```bash
forge demo list                          # all presets, both kinds
forge demo run --preset calc             # LLM Python preset
forge demo run --preset js-counter       # static JS showcase, runs offline
```

Expected offline showcase scores:

| Preset | Purpose | Expected |
|--------|---------|----------|
| `js-counter` | Clean JS tier layout | `wire PASS`, `certify 60/100` |
| `js-bad-wire` | Teaches upward-import failure | `wire FAIL`, `certify 50/100` |
| `mixed-py-js` | Python + JS in one root | `wire PASS`, `certify 90/100` |

### `forge chat ask "QUESTION"`

Forge-aware chat copilot. Uses the same provider layer as `iterate` and
`evolve`, with optional bounded repo context.

```bash
forge chat ask "what should I fix before release?" --context .
forge chat repl --provider nexus --context src --context docs
forge chat ask "hello" --provider stub --no-cwd-context --json
```

Context rules:
- `--context PATH` is repeatable and accepts files or directories.
- If no `--context` is provided, the current directory is packed by default.
- `.env`, key/certificate files, ignored directories, assets, and binary-ish
  files are skipped.
- `--max-files` and `--max-chars` bound what is sent to the provider.

### `forge feature-then-emergent run FEATURE -- ARGS`

Universal pipe: run any Forge feature, fan its JSON output into emergent
scan to surface compositions.

## Discovery / introspection

### `forge emergent scan`

Walk a tier package, build the type-compatibility graph, surface ranked
composition chains the LLM didn't think to write.

### `forge synergy scan` / `forge synergy implement <id> <report>`

Find feature/CLI producer-consumer pairs that aren't wired yet. Optionally
auto-generate the adapter module.

### `forge emergent-then-synergy`

Pipeline adapter: emergent scan → synergy scan in one step. Surfaces
composition chains and immediately finds producer/consumer wiring
opportunities.

### `forge synergy-then-emergent`

Pipeline adapter: synergy scan → emergent scan. Useful for discovering
type-compatible emergent chains for features synergy already identified.

### `forge evolve-then-iterate`

Pipeline adapter: evolve run → iterate run on the evolved catalog. Applies a
final single-shot refinement after recursive self-improvement converges.

### `forge commandsmith discover` / `sync` / `wrap` / `smoke`

Auto-register, document, and smoke-test every CLI command. Use after
`assimilate` to expose new features as live verbs.

### `forge doctor`

Environment diagnostic — version, Python, encoding, executable.

## LLM provider matrix

| Provider | Cost | Env var | Default model | Notes |
|----------|------|---------|---------------|-------|
| `gemini` | **free tier** | `GEMINI_API_KEY` / `GOOGLE_API_KEY` | `gemini-2.5-flash` | 15 RPM / 1500 RPD on flash |
| `nexus` / `aaaa-nexus` | paid | `AAAA_NEXUS_API_KEY` | (Nexus default) | most reliable for long iterative runs |
| `anthropic` | paid | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-latest` | highest quality |
| `openai` | paid | `OPENAI_API_KEY` | `gpt-4o-mini` | cheap GPT path |
| `openrouter` | **free tier available** | `OPENROUTER_API_KEY` | `google/gemma-3-27b-it:free` | 200+ models; good fallback when Gemini quota exhausted; override with `FORGE_OPENROUTER_MODEL` |
| `ollama` | free, local | `FORGE_OLLAMA=1` (auto-resolve), `FORGE_OLLAMA_MODEL=…` | `qwen2.5-coder:7b` | offline + private; tune with `FORGE_OLLAMA_NUM_PREDICT`, `FORGE_OLLAMA_TIMEOUT`, `OLLAMA_BASE_URL` |
| `stub` | free, offline | n/a | n/a | tests, CI, dry-runs |

Resolution order when `--provider auto`:
1. `AAAA_NEXUS_API_KEY`
2. `ANTHROPIC_API_KEY`
3. `GEMINI_API_KEY` / `GOOGLE_API_KEY`
4. `OPENAI_API_KEY`
5. `OPENROUTER_API_KEY`
6. `FORGE_OLLAMA=1`
7. fallback to `stub`

Local Ollama controls:

```bash
# Low-load profile for a busy machine.
export FORGE_OLLAMA_MODEL=qwen2.5-coder:1.5b
export FORGE_OLLAMA_NUM_PREDICT=768
export FORGE_OLLAMA_TIMEOUT=180

# Better coding baseline when the machine is idle.
export FORGE_OLLAMA_MODEL=qwen2.5-coder:7b
export FORGE_OLLAMA_NUM_PREDICT=1536
export FORGE_OLLAMA_TIMEOUT=420
```

`FORGE_OLLAMA_NUM_PREDICT` caps the generated tokens for each provider call.
Use it to keep local runs from overloading a busy PC. Provider errors are
reported as normal CLI errors instead of raw Python tracebacks.

## What every run produces

Every successful `forge iterate` / `evolve` / `demo` run writes:

```
<output>/
├── pyproject.toml          # PEP-621, console_script entry → installable
├── README.md               # Synthesised from actual symbols
├── .gitignore
├── docs/
│   ├── API.md              # Generated public-symbol reference
│   └── TESTING.md          # Generated test/run guidance
├── src/<package>/
│   ├── a0_qk_constants/
│   ├── a1_at_functions/
│   ├── a2_mo_composites/
│   ├── a3_og_features/
│   ├── a4_sy_orchestration/
│   └── __init__.py
├── tests/
│   ├── conftest.py         # adds src/ to sys.path
│   ├── test_generated_smoke.py # Forge-created import-smoke tests
│   └── test_*.py           # LLM- or human-authored behavioral tests
├── DEMO.md                 # If invoked through forge demo
└── .atomadic-forge/
    ├── EVOLVE_LOG.md       # Append-only history of every run
    ├── evolve_log.jsonl    # Machine-readable mirror
    ├── scout.json
    ├── quality.json        # Docstring/docs/tests phase report
    ├── iterate.json
    ├── evolve.json
    ├── demo.json
    ├── lineage.jsonl       # Append-only artifact provenance
    └── transcripts/
        └── run-<ts>.jsonl  # Every LLM prompt + response (full transparency)
```

Every artifact has a `schema_version`. Every JSON file is documented and
re-readable. The full LLM transcript is on disk so operators can audit
exactly what was asked and exactly what was emitted.
