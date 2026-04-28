# Changelog

## 0.1.1 — _forge init setup wizard + forge config management_

First-run experience: new users can configure Forge in 60 seconds without
touching environment variables or config files by hand.

### New commands

- `forge init` — top-level alias for the interactive setup wizard.
- `forge config wizard` — same wizard from within the config sub-group.
- `forge config show` — print the current merged config (local > global > defaults);
  API keys are masked automatically. `--json` for scripting.
- `forge config set KEY VALUE` — set a single key in the local (or `--global`) config file;
  booleans and numbers are auto-coerced.
- `forge config test [--provider P]` — live-test the configured LLM connection and
  print status, model, and round-trip latency.

### New modules (monadic tier placement)

| File | Tier | Purpose |
|------|------|---------|
| `a0_qk_constants/config_defaults.py` | a0 | `DEFAULT_CONFIG`, `ForgeConfig` TypedDict, file-location constants |
| `a1_at_functions/config_io.py` | a1 | `load_config`, `save_config`, `merge_configs`, `validate_config`, `read_config_file` |
| `a1_at_functions/provider_detect.py` | a1 | `detect_ollama`, `list_ollama_models`, `test_provider` |
| `a3_og_features/setup_wizard.py` | a3 | `run_wizard` — 5-step interactive wizard with rich panels |
| `commands/config_cmd.py` | a4 | Typer sub-app with `wizard`, `show`, `set`, `test` sub-commands |

### Config merge priority

`local .atomadic-forge/config.json` → `global ~/.atomadic-forge/config.json` → built-in defaults.
`None` values are skipped so keys always fall through to the next layer.

### Tests

56 new tests covering:
- All default key presence and value ranges
- `save_config` / `read_config_file` round-trip and error paths
- `merge_configs` all priority combinations
- `load_config` with and without local config files
- `validate_config` valid/invalid providers, scores, and URLs
- `detect_ollama` / `test_provider` error paths (monkeypatched urllib)
- CLI smoke: `config show`, `config show --json`, `config set`, `config test --json`, `init --help`

Total: **150 tests**, all passing.

---

## 0.1.0 — _Initial cut + 6 refine cycles + breakthrough + showcase_

First public-shaped release. Forged out of `ASS-ADE-SEED` by isolating the
absorb-and-emerge wedge, then sharpened across six refine cycles into a
genuine architecture substrate for AI-generated code.

### Pipeline verbs

- `forge auto` — scout + cherry + assimilate + wire + certify in one shot.
- `forge recon` / `forge cherry` / `forge finalize` — granular workflow.
- `forge wire` — upward-import scanner.
- `forge certify` — docs/tests/layout/imports/behavior score with stub-body penalty.
- `forge doctor` — environment diagnostic.

### Code-generation verbs (LLM-driven)

- `forge iterate run` — LLM ↔ Forge 3-way constraint loop.
- `forge evolve run --auto N` — recursive self-improvement; halts on
  convergence, regression (optional), or stagnation (3 flat rounds default).
- `forge demo run --preset NAME` — one-shot launch-video verb. Presets:
  `calc`, `kv`, `slug`, all live-validated against Gemini.
- `forge feature-then-emergent` — universal pipe: any feature → emergent scan.

### Specialty verbs (lazily registered)

- `forge emergent scan` — symbol-level composition discovery.
- `forge synergy scan` / `synergy implement` — feature-pair detection +
  auto-generated adapters.
- `forge commandsmith discover/sync/wrap/smoke` — auto-register CLI
  commands across the catalog.

### Refine cycle highlights

| Cycle | Headline change | Live verification |
|-------|----------------|---------------------|
| 0.1.0 base | 5-tier law + import-linter contract; `auto`/`recon`/`cherry`/`finalize`/`wire`/`certify`/`doctor`. | 47 tests passing. |
| Refine 1 | Stub-body detector (catches `pass`, `NotImplementedError`, `# TODO`). Stagnation halt for evolve. Per-file feedback. | URL-shortener trajectory `50→50→50→50` (stuck). |
| Refine 2 | Runtime import smoke (subprocess `python -c "import <pkg>"`). Few-shot in system prompt. Retry-on-bad-parse. Score rebalance. | URL-shortener `70→70→70→85` — **converged Round 3**, runnable CLI. |
| Refine 3 | Round-0 scaffolds (pyproject + README + tests/conftest + tier inits). Tier `__init__` re-export rebuilder (idempotent, banner-gated). | URL-shortener `69→100` — **converged Round 1**. |
| Refine 4 | Validation: same model + same task, `100→100→100→100`, **but identity-function stubs gamed every check**. Score lied. | mdconv with codellama emitted `def parse(x): return x`; certify said 100. |
| Refine 5 (BREAKTHROUGH) | Behavioral pytest runner (subprocess pytest). Score weights: structural 35 + runtime 25 + behavioral 30. Per-file pytest failure callouts in feedback. | mdconv `60→60→60→60→60` — score now reflects honest behavior. Identity gaming closed. |
| Refine 6 | `forge demo` one-shot launch verb with 3 live-validated presets. | calc/kv/slug all 90/100 with Gemini in 22–72s. |
| Doc + transparency | Auto-doc synthesizer (rich READMEs from emitted symbols), append-only evolution log + transcript log. Wrong-package gameability fix (test runner now requires tests to import the requested package). | New gap caught + closed in the same session. |

### Substrate properties (now provable from the artifact alone)

- **Wire scan** — every emitted file lives in the legal tier.
- **Import smoke** — package actually loads in a fresh subprocess.
- **Behavioral pytest** — LLM's own tests must actually pass.
- **Stub detector** — `pass` / `NotImplementedError` / `# TODO` deduct.
- **Wrong-package gating** — tests that don't import the requested package
  don't credit the behavioral score.

### Per-run artifacts (auto-emitted)

Every successful run leaves under `<output>/.atomadic-forge/`:

- `EVOLVE_LOG.md` + `evolve_log.jsonl` — append-only run history.
- `lineage.jsonl` — append-only artifact provenance.
- `transcripts/run-<ts>.jsonl` — every LLM prompt + response (full transparency).
- `evolve.json` / `iterate.json` / `demo.json` / `scout.json` — per-phase
  structured reports with stable schema versions.

### LLM provider matrix

| Provider | Cost | Default model |
|----------|------|---------------|
| `gemini` | **free tier** | `gemini-2.5-flash` |
| `anthropic` | paid | `claude-3-5-sonnet-latest` |
| `openai` | paid | `gpt-4o-mini` |
| `ollama` | **free, local** | `qwen2.5-coder:7b` |
| `stub` | free, offline | n/a (deterministic) |

### Documentation

- `docs/SHOWCASE.md` — live runs + trajectories.
- `docs/LANDSCAPE.md` — comparison vs Cursor/Devin/Lovable/Bolt/Copilot.
- `docs/WHY_NOW.md` — the urgency case for the architecture substrate.
- `docs/COMMANDS.md` — full reference for all 13+ verbs.
- `docs/ROADMAP.md` — 0.2 / 0.3 / 1.0 milestones.
- `docs/tutorials/01-quickstart.md` — 60-second getting-started.
- `docs/tutorials/02-your-first-package.md` — own intent string.
- `docs/tutorials/03-the-five-tier-law.md` — the architecture itself.
- `docs/tutorials/04-plug-in-llms.md` — provider matrix.
- `docs/tutorials/05-multi-repo-absorb.md` — the absorb flow.

### Known limits (honest)

- Python only — multi-language ships in 0.3.
- Auto output is bootstrapped material; integration tests + secrets +
  observability remain human responsibilities.
- No semantic merge across conflicting symbols (rename / first / last /
  fail per `--on-conflict`).
- Cryptographic certificate signing chain ships in 0.2.
- The behavioral pytest check is the strongest signal but tests authored
  by the LLM can themselves be weak; adversarial-test generation in 0.2.

### Dropped from the parent (ASS-ADE-SEED)

- `chat`, `voice`, `agent`, `a2a` → moving to Atomadic Assistant.
- `pay`, `wallet`, `vrf`, `defi`, `mev`, `vanguard`, `aegis`, `bitnet`
  → stay in AAAA-Nexus.
- `discord`, `hello`, `heartbeat` → infrastructure, not Forge surface.

### Test counts

- 90+ pytest tests, all passing.
- All scenarios live-validated end-to-end against ollama (codellama:7b)
  and Google Gemini 2.5 Flash on free tier.
