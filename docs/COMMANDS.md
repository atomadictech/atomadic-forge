# Atomadic Forge — Command Reference

All verbs available in the `forge` CLI as of 0.2.0.

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

### `forge certify ROOT --package <name>`

Score docs, tests, layout, imports, importability, behavior, stub bodies.
Returns 0–100 honest score with component breakdown.

JS/TS-specific behaviour:
- `tests` PASS recognises `tests/*.test.{js,mjs,jsx,cjs,ts,tsx}`,
  `*.spec.*`, and the Jest `__tests__/` directory convention.
- `tier_layout` PASS counts JS-style top-level or nested `aN_*`
  directories anywhere under the repo root, not just under `src/<pkg>/`.
- The runtime-import smoke (+25 points) and behavioural pytest gate
  (+30 points) remain Python-only — JS/TS packages are scored on the
  +45 polyglot-aware structural axes.

## Code generation (LLM-driven)

### `forge iterate run "INTENT" OUTPUT`

LLM ↔ Forge 3-way loop (wire + certify + emergent + reuse). Configurable
provider (`auto | gemini | anthropic | openai | ollama | stub`).

```bash
forge iterate run "build a calculator CLI" ./out --provider gemini
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

### `forge commandsmith discover` / `sync` / `wrap` / `smoke`

Auto-register, document, and smoke-test every CLI command. Use after
`assimilate` to expose new features as live verbs.

### `forge doctor`

Environment diagnostic — version, Python, encoding, executable.

## LLM provider matrix

| Provider | Cost | Env var | Default model | Notes |
|----------|------|---------|---------------|-------|
| `gemini` | **free tier** | `GEMINI_API_KEY` | `gemini-2.5-flash` | 15 RPM / 1500 RPD on flash |
| `anthropic` | paid | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-latest` | highest quality |
| `openai` | paid | `OPENAI_API_KEY` | `gpt-4o-mini` | cheap GPT path |
| `ollama` | free, local | `FORGE_OLLAMA=1` (auto-resolve), `FORGE_OLLAMA_MODEL=…` | `qwen2.5-coder:7b` | offline + private |
| `stub` | free, offline | n/a | n/a | tests, CI, dry-runs |

Resolution order when `--provider auto`:
1. `GEMINI_API_KEY` / `GOOGLE_API_KEY`
2. `ANTHROPIC_API_KEY`
3. `OPENAI_API_KEY`
4. `FORGE_OLLAMA=1`
5. fallback to stub

## What every run produces

Every successful `forge iterate` / `evolve` / `demo` run writes:

```
<output>/
├── pyproject.toml          # PEP-621, console_script entry → installable
├── README.md               # Synthesised from actual symbols
├── .gitignore
├── src/<package>/
│   ├── a0_qk_constants/
│   ├── a1_at_functions/
│   ├── a2_mo_composites/
│   ├── a3_og_features/
│   ├── a4_sy_orchestration/
│   └── __init__.py
├── tests/
│   ├── conftest.py         # adds src/ to sys.path
│   └── test_*.py           # LLM-emitted, runs via pytest
├── DEMO.md                 # If invoked through forge demo
└── .atomadic-forge/
    ├── EVOLVE_LOG.md       # Append-only history of every run
    ├── evolve_log.jsonl    # Machine-readable mirror
    ├── scout.json
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
