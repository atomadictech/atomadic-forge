# Changelog

## 0.2.0 — _Polyglot (JavaScript / TypeScript) support_

Forge is no longer Python-only. `recon`, `wire`, and `certify` now classify
JavaScript and TypeScript files into the same 5-tier monadic layout that has
always governed Python source. The same constraint substrate now answers for
Cloudflare Workers, Node back-ends, React-Native modules, and any mixed-language
repository — without adding a Node dependency to Forge itself.

### What landed

- **Polyglot file scanning.** `recon` walks `.py`, `.js`, `.mjs`, `.cjs`,
  `.jsx`, `.ts`, and `.tsx` in a single pass. `node_modules/`, `.next/`,
  `.wrangler/`, `dist/`, `build/`, `coverage/`, and `.turbo/` are skipped
  automatically.
- **Pure-Python JS parser.** ES6 `import` (named, default, namespace,
  side-effect, `import type` for TS), dynamic `import()`, and CommonJS
  `require()` (including destructured) are all parsed via regex + a
  brace-walking surface scanner. Comments and string literals are stripped
  first so a fake `import x from 'y'` inside a string never registers.
- **Tier classification for JS/TS.** Files placed inside an `aN_*` directory
  obey the law strictly. Files outside get a `suggested_tier` inferred from
  their character — a Cloudflare Worker default-`{ fetch, scheduled }` is a4,
  a class-with-state module is a2, an `export-const`-only module is a0, and so on.
- **Polyglot wire-check.** Upward-import detection works against JS specifiers
  like `"../a3_og_features/foo"` exactly as it works for Python `from`-imports.
  Each violation now carries a `language` field (`"python"` / `"javascript"`
  / `"typescript"`) so reports can group by source.
- **Polyglot certify.**
  - `tests` PASS recognises `tests/*.test.{js,mjs,jsx,cjs,ts,tsx}`,
    `*.spec.*`, and the Jest `__tests__/` convention alongside Python's
    `tests/test_*.py` and `*_test.py`.
  - Tier-layout PASS counts JS-style top-level or nested `aN_*` directories
    anywhere under the repo root, not just under `src/<pkg>/`.
  - Failure messages are now specific (e.g. *"found 2 tier directories
    (a1_at_functions, a4_sy_orchestration); need 3+"*).
- **Per-language recon output.** `forge recon` prints
  `python files: N`, `javascript files: M`, `typescript files: K`, plus a
  `primary_language` verdict and a `recommendations` list when JS/TS files
  exist outside tier directories.
- **Three static showcase demo presets.** `forge demo` now ships
  `js-counter` (clean a0..a4 JS package; wire PASS, certify 60/100 —
  the honest ceiling for a JS-only package while behavioural scoring
  remains Python-only), `js-bad-wire` (deliberately upward-imports —
  wire surfaces the violation with `language: "javascript"`), and
  `mixed-py-js` (one Python tier and one JS tier under the same root).
  These run *without an LLM* — they showcase recon/wire/certify on
  pre-built source, no API key required.

### New / changed modules (monadic tier placement)

| File | Tier | Purpose |
|------|------|---------|
| `a0_qk_constants/lang_extensions.py` | a0 (new) | Canonical `.py` / `.js` / `.mjs` / `.cjs` / `.jsx` / `.ts` / `.tsx` extension sets + `lang_for_path` lookup |
| `a1_at_functions/js_parser.py` | a1 (new) | Pure regex + brace-walker for ES6 / CommonJS imports, exports, default-object handlers (Worker shape), state signals, tier classifier, effect detector |
| `a1_at_functions/scout_walk.py` | a1 (extended) | Walks JS/TS as well as Python; per-file `suggested_tier`; per-language counts in the report |
| `a1_at_functions/wire_check.py` | a1 (extended) | Polyglot upward-import scanner; each violation carries a `language` field; `node_modules/` and `__pycache__/` skipped |
| `a1_at_functions/certify_checks.py` | a1 (extended) | `tests` and `tier_layout` checks recognise JS conventions; specific failure messages |
| `a4_sy_orchestration/cli.py` | a4 (extended) | `forge recon` prints per-language counts and detected `primary_language` |
| `a3_og_features/demo_runner.py` | a3 (extended) | `DemoPreset.kind` (`"llm"` / `"showcase"`) + `run_showcase` for static-package demos |
| `a3_og_features/demo_packages/` | a3 (new) | Source files for `js-counter`, `js-bad-wire`, `mixed-py-js` showcase presets |

### Tests

42 new tests for the JS/TS scanner (ES6 / dynamic / CommonJS imports,
TypeScript imports, comment + string-literal stripping, classifying a
`worker.js` as a4, classifying a constants module as a0, JS-only repo
recon, TypeScript counted, JS/TS upward-import detection in wire, JS
test recognition in certify, polyglot tier-layout detection, and the
specific layout-failure message), plus 20 follow-up tests for the
canonical `IGNORED_DIRS` list, the file-class taxonomy
(`source` / `documentation` / `config` / `asset` / `other`), and
nested-`docs/` / `guides/` discovery in `check_documentation`.

Total: **212 tests**, all passing.

### Atomadic recon proof point

| Repo state | Python | JavaScript | Primary | Certify |
|------------|-------:|-----------:|---------|--------:|
| Atomadic — before 0.2 | 1 | 0 (not seen) | python | 45/100 (tests FAIL) |
| Atomadic — after  0.2 | 1 | 3 | javascript | 50/100 (tests PASS via `cognition.test.js`; layout still FAIL with specific reason: "0 tier directories present") |

The remaining gap is real architecture work, not Forge limitation.

### Known limits (still honest)

- The JS parser is regex-based, not a real AST. It handles the surface
  (imports / exports / class / default-object handlers / state signals)
  the tier law cares about. JSX expressions, decorators, and exotic-shape
  TypeScript generics are silently ignored where they would not affect the
  tier verdict.
- The runtime importability check (the +25 score component for "package
  actually loads in a fresh subprocess") remains Python-only. JS/TS packages
  are scored on documentation, tests, layout, and upward-import discipline;
  the behavioural pytest gate stays a Python-side check too.
- Rust / Go support is still on the roadmap.

---

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
