# Changelog

## Unreleased — _Pre-audit lanes + Golden Path Lane A W0_

10 commits accumulated since `0.2.2` ship, mapped onto the lanes in
`launch/forge/GOLDEN_PATH-20260428.md`. Test trajectory: **301 → 363
passing, 2 skipped**. `forge wire src/atomadic_forge` PASS at every
commit. `forge certify .` = **100/100** held.

### Added — pre-audit operational scaffolding

- **`forge audit list / show / log`** (`7cd840a`, audit-D1) — surfaces
  the Vanguard lineage chain as a verb. Reads
  `.atomadic-forge/lineage.jsonl`; populates Receipt's
  `lineage.lineage_path` field at GP Lane A W4. New module:
  `a1_at_functions/lineage_reader.py`.
- **`forge wire --suggest-repairs`** (`4786836`, audit-D2) — emits a
  per-violation repair hint and an `auto_fixable` count; populates
  Receipt's `wire.auto_fixable` field. Prerequisite for `forge enforce`
  at GP Lane A W6.
- **`forge wire --fail-on-violations`** (`8385cea`, audit-G1) — exits
  non-zero when any upward import is detected. Drop-in CI gate
  consumed by `forge-action` at GP Lane C W1.
- **`forge diff MANIFEST_A MANIFEST_B`** (`6249e74`, audit-D4) —
  schema-aware compare of two scout/certify manifests. Powers Lane B's
  "Shadow Merge" view (W8) and Lane E's PR-comment delta.
- **`--progress` on `forge recon` / `forge auto`** (`ec59a75`, audit-B2)
  — per-file stderr progress line. New module:
  `a1_at_functions/progress_reporter.py`. Feeds Lane B Forge Studio's
  progress pane.
- **F-coded error hints in CLI errors** (`375fe85`, audit-B4) —
  recovery-template hints attached to common CLI failure modes.
  Scaffolding for Lane A W5's full F0001–F0099 catalog. New module:
  `a1_at_functions/error_hints.py`.
- **Pre-audit smoke test** (`b4c8579`, audit-H1) — pins file:line
  claims so `lane-plan.md` cannot drift from the source.
- **`docs/FIRST_10_MINUTES.md` consolidation** (`109e857`, audit-F) —
  unifies onboarding; `docs/CI_CD.md`, `docs/MULTI_REPO.md`,
  `docs/AIR_GAPPED.md` are the deeper paths.

### Added — Golden Path Lane A W0 (critical-path)

- **Forge Receipt JSON v1 wire-format schema** (`f6c487a`, GP-A W0) at
  `a0_qk_constants/receipt_schema.py` (278 LOC) + `docs/RECEIPT.md`
  (305 lines) + `tests/test_receipt_schema.py` (206 LOC). Versioning
  roadmap explicit (v1.0 → v1.1 W8 polyglot_breakdown → v1.2 W12
  slsa_attestation → v2.0 W24 bao_rompf_witnesses). Both Lean4 corpora
  cited (`aethel-nexus-proofs` — 29 theorems, 0 sorry, 0 axioms — and
  `mhed-toe-codex-v22` — 538 theorems, 0 sorry). All signing / lineage
  / attestation fields default to `None` so unsigned dev Receipts
  remain structurally valid. Tier-pure a0 (imports limited to
  `__future__` and `typing`).

### Fixed

- **`datetime.utcnow()` deprecation sweep** (`3359fb6`, audit-A1) —
  replaced with `datetime.now(timezone.utc)` across a3 features.
  Prerequisite for the GP P1 self-certify gate.

### Documentation

- `docs/COMMANDS.md` updated with the 5 new user-facing surfaces:
  `forge audit list/show/log`, `forge diff`, `forge wire
  --fail-on-violations`, `forge wire --suggest-repairs`,
  `forge recon --progress`.

### Notes for downstream consumers

- The Receipt schema is **forward-compatible by design** — every new
  field defaults to `None` or `[]` / `{}`. Adding a *required* field is
  a major version bump; reserved field names are documented in the
  schema docstring.
- `forge wire --fail-on-violations` is the load-bearing primitive for
  the planned `atomadictech/forge-action` GitHub Action (GP Lane C W1).
- 9 audit-lane commits + 1 GP-A W0 commit currently sit on a feature
  branch. Cut as `0.3.0-rc1` when GP-A W1 (`receipt_emitter` +
  `card_renderer`) lands.

## 0.2.2 — _Operational axis + 100/100 self-certify_

`forge certify` now scores the full 0–100 range.  The v1 rubric topped
out at 90 (35 structural + 25 runtime + 30 behavioural) with 10 points
of reserved headroom that no axis credited.  This release closes the
gap with a new **operational axis** worth 10 points total:

| Axis | Points | Check |
|---|---|---|
| CI workflow present | 5 | `.github/workflows/*.yml` (or `.yaml`) — at least one non-empty file |
| Changelog / release notes | 5 | `CHANGELOG.md` (or `.rst`, `RELEASE_NOTES.md`, `HISTORY.md`, `NEWS.md`) ≥ 200 bytes at root |

Both checks are pure structural file-existence — no API calls, no slow
runtime paths.  The CI axis credits intent (a workflow exists); the
behavioural axis already credits actual test-pass behaviour, so there's
no double-counting.

### Added

- `check_ci_workflow(root)` — pure helper at `a1_at_functions/certify_checks.py`
- `check_changelog(root)` — pure helper at the same module
- `score_components.operational` — new key in the certify result dict
- `ci_workflow_present` and `changelog_present` — new top-level booleans
  in the certify result dict
- `detail.ci` and `detail.changelog` — new entries in the detail dict
- 22 new tests in `tests/test_certify_operational_axis.py` covering both
  helpers, the integrated 100/100 path, partial-credit (CI-only,
  changelog-only), and the issue/recommendation surfacing on misses
- README badge updated from 90/100 → 100/100

### Fixed

- The `# Score weights (sum to 100):` comment in `certify_checks.py` now
  actually sums to 100 (was 90 in v0.2.1; the reserved headroom is now
  spoken for).
- Forge's own self-certify: **90 → 100**.  299 passing tests, 1
  skipped (was 274 + 1).  Wire scan: PASS, 0 violations.
- `forge demo run` now exits non-zero when the generated CLI demo fails,
  while still writing the artifact for debugging.
- `commandsmith sync` now regenerates a Ruff-clean command registry.
- `forge certify --fail-under <score>` gives CI an explicit score gate.
- Certification scans ignore `.pytest_tmp*` scratch trees and generated
  smoke tests are Ruff-clean, so local verification does not depend on
  manual cleanup order.

### Notes for downstream certify consumers

If your tooling asserts on a specific score value (e.g. `assert
result["score"] == 90`), audit it: a project with `.github/workflows/`
and `CHANGELOG.md` will now legitimately score higher than before.
The fixture-based tests in `tests/test_stub_detector.py` were
unaffected because their temp roots don't include the operational-axis
files.

## 0.2.1 — _Provider resilience + forge stress-test fixes_

Discovered and fixed during a live stress-test: using Forge itself to
absorb 23,487 symbols from five major agent frameworks (langchain,
autogen, instructor, mem0, browser-use) while running `iterate`, `evolve`,
`emergent`, `synergy`, and `commandsmith` end-to-end.  All fixes are in the
forge source; the evolution run produced `generated/tool-agent` (60/100) and
`generated/sovereign` (74/100) plus 12 registered CLI commands (12/12 smoke PASS).

### Added

- `forge chat ask` and `forge chat repl` — a Forge-aware chat copilot that
  uses the same provider layer as `iterate` / `evolve`, supports `nexus`,
  `openrouter`, `gemini`, `anthropic`, `openai`, `ollama`, and `stub`, and
  packs bounded repo context while skipping `.env` and obvious secret files.
- Deterministic Python quality phases after generation: missing docstrings
  are filled, `docs/API.md` and `docs/TESTING.md` are created, and
  `tests/test_generated_smoke.py` is added before final certification.
- `.atomadic-forge/quality.json` records the docstring/docs/tests phase
  results for every Python `iterate` / `evolve` output.
- GitHub readiness assets: CI and release workflows, Dependabot config,
  bug/feature issue forms, PR template, security policy, and source
  distribution manifest.
- Shared provider resolver used by `chat`, `demo`, `iterate`, and `evolve`
  so aliases and help text no longer drift between commands.
- CLI UX docs for chat, offline demo expectations, corrected certify scoring,
  and the actual `--provider auto` resolution order.

### Bug fixes

**Bug 1 — `forge iterate` missing `nexus` provider**
`commands/iterate.py` had no `nexus`/`aaaa-nexus` case in `_resolve_provider()`
even though `forge evolve` already supported it.  Added
`if name in ("nexus", "aaaa-nexus", "aaaa_nexus", "helix"): return AAAANexusClient()`.

**Bug 2 — `forge iterate` missing `openrouter` provider**
No OpenRouter support existed anywhere in forge.  Added `OpenRouterClient` to
`a1_at_functions/llm_client.py` (OpenRouter's OpenAI-compatible endpoint,
default model `google/gemma-3-27b-it:free`).  Added `openrouter`/`router`
cases to both `iterate` and `evolve` provider resolvers.

**Bug 3 — `forge iterate` only accepted a single `--seed`**
`seed_repo: Path | None` rejected multiple seeds.  Changed to
`seed_repo: list[Path] | None` in both `commands/iterate.py` and
`a3_og_features/forge_loop.py`.  The seed catalog is now accumulated
from all provided `--seed` paths.

**Bug 4 — OpenRouter 400 on models without system-role support**
`gemma-3-27b-it` (and similar models) return HTTP 400
`"Developer instruction is not enabled"` when a `system` role message is
sent.  `OpenRouterClient.call()` now retries with the system prompt folded
into the user message on the first such failure.

**Bug 5 — `parse_files_from_response` failed on truncated JSON arrays**
When an LLM response was cut off mid-array the balanced-bracket scanner
returned `[]`, writing 0 files.  Added a third strategy: regex-based
extraction of complete `{"path", "content"}` objects from a partial array.
Also fixed the fence regex from non-greedy to greedy capture.

**Bug 6 — Seed catalog flooded the prompt with 460 K+ symbols**
Multiple large seeds (langchain + mem0) pushed 460 K+ symbols into the
prompt, confusing the LLM.  `pack_initial_intent()` now deduplicates
method-level entries to base class names and caps the display at 30 unique
top-level symbols.

**Bug 7 — SyntaxWarning noise from third-party forged files**
mem0's regex strings used invalid escapes (`\.`), causing Python
`SyntaxWarning` on every forge command that loaded the seed catalog.  Added
`warnings.filterwarnings("ignore", category=SyntaxWarning)` at CLI import
time in `a4_sy_orchestration/cli.py`.

**Bug 8 — `commandsmith smoke` referenced non-existent `unified_cli` module**
The smoke test invoked
`atomadic_forge.a4_sy_orchestration.unified_cli` which doesn't exist.
Changed to `atomadic_forge.a4_sy_orchestration.cli`.  The current command
surface now passes smoke test (12/12 PASS).

**Bug 9 — Generated synergy adapters referenced `unified_cli`**
The synergy-implement template hardcoded `unified_cli` in subprocess calls.
Replaced with `cli` in all three generated adapter files
(`emergent_then_synergy.py`, `synergy_then_emergent.py`,
`evolve_then_iterate.py`) and registered them in `cli.py`.

**Bug 10 — `forge certify` stub scan recursed into `forged/` directories**
When certifying a project root without a `src/` directory,
`detect_stubs` ran `rglob("*.py")` on the full tree — including 17 727
stub skeletons in `forged/*/src/` — dragging the score from 60 → 20/100.
`certify_checks.py` now sets `src_for_stubs = None` and skips stub
detection entirely when there is no `src/` layout.

### New / changed modules

| File | Tier | Change |
|------|------|--------|
| `a1_at_functions/llm_client.py` | a1 | `OpenRouterClient` added; `resolve_default_client()` includes openrouter in auto-chain |
| `commands/iterate.py` | a4 | nexus + openrouter providers; multi-seed `list[Path]` |
| `commands/evolve.py` | a4 | nexus + openrouter providers |
| `a3_og_features/forge_loop.py` | a3 | multi-seed accumulation loop |
| `a1_at_functions/forge_feedback.py` | a1 | 3-strategy tolerant JSON parser; seed dedup + 30-symbol cap |
| `a4_sy_orchestration/cli.py` | a4 | SyntaxWarning suppressor; 3 new synergy adapters registered |
| `a3_og_features/commandsmith_feature.py` | a3 | smoke test CLI path fixed |
| `a1_at_functions/certify_checks.py` | a1 | stub scan scoped to `src/` only; no-src fallback skips scan |
| `commands/emergent_then_synergy.py` | a4 | new — emergent → synergy pipeline adapter |
| `commands/synergy_then_emergent.py` | a4 | new — synergy → emergent pipeline adapter |
| `commands/evolve_then_iterate.py` | a4 | new — evolve → iterate pipeline adapter |

### Provider matrix (updated)

| Provider | Cost | Env var | Default model |
|----------|------|---------|---------------|
| `gemini` | free tier | `GEMINI_API_KEY` / `GOOGLE_AI_STUDIO_KEY` | `gemini-2.5-flash` |
| `nexus` / `aaaa-nexus` | paid | `AAAA_NEXUS_API_KEY` | (Nexus default) |
| `anthropic` | paid | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-latest` |
| `openai` | paid | `OPENAI_API_KEY` | `gpt-4o-mini` |
| `openrouter` | free tier available | `OPENROUTER_API_KEY` | `google/gemma-3-27b-it:free` |
| `ollama` | free, local | `FORGE_OLLAMA=1` | `qwen2.5-coder:7b` |
| `stub` | free, offline | n/a | n/a |

---

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
