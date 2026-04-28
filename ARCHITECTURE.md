# Atomadic Forge — Architecture

## The 5-tier monadic standard

```
a4_sy_orchestration/    CLI, entry points, top-level orchestrators
        ↑
a3_og_features/         Feature modules (combine composites into capabilities)
        ↑
a2_mo_composites/       Stateful classes (clients, registries, stores)
        ↑
a1_at_functions/        Pure stateless functions (validators, parsers)
        ↑
a0_qk_constants/        Constants, enums, TypedDicts. Zero logic.
```

**Compose upward, never downward.** A pure function never depends on a
stateful class. A CLI command orchestrates everything below it but invents
nothing new.

## Hard rules

1. One tier per file. A pure function → a1. A class with state → a2. A CLI
   entry point → a4. Split if in doubt.
2. Never import upward. `a1` cannot import from `a2`–`a4`. `a0` cannot
   import anything.
3. Compose, don't rewrite. Before writing new logic, check whether the
   building block already exists. If it does, import it.
4. Small, focused files. One responsibility per file.
5. Every new file gets a module docstring: `"""Tier a1 — pure helpers."""`.

## Forge's own layout

```
src/atomadic_forge/
├── a0_qk_constants/        # tier_names, forge_types, lang_extensions, *_types.py
├── a1_at_functions/        # classify_tier, scout_walk, cherry_pick, wire_check,
│                            # certify_checks, body_extractor, import_repair,
│                            # js_parser, commandsmith_*, emergent_*, synergy_*
├── a2_mo_composites/       # manifest_store
├── a3_og_features/         # forge_pipeline (run_auto/run_recon/run_cherry/run_finalize),
│                            # emergent_feature, synergy_feature, commandsmith_feature,
│                            # demo_runner + demo_packages/ (static showcase presets)
├── a4_sy_orchestration/    # cli.py — Typer app with `auto` flagship
└── commands/               # Per-verb Typer modules (specialty surfaces)
```

`tests/` mirrors the same shape. `pyproject.toml` declares a layered
`import-linter` contract — `tox -e import-linter` (or just running the
contracts directly) blocks CI on any violation.

## File scanner (polyglot)

Forge classifies Python AND JavaScript / TypeScript source. Two small
modules carry the language layer; everything downstream stays
language-agnostic:

- `a0_qk_constants/lang_extensions.py` — canonical extension sets
  (`PYTHON_EXTS = {.py}`, `JAVASCRIPT_EXTS = {.js, .mjs, .cjs, .jsx}`,
  `TYPESCRIPT_EXTS = {.ts, .tsx}`) + the pure `lang_for_path` lookup.
  Adding a language is a one-line change here.
- `a1_at_functions/js_parser.py` — pure regex + brace-walker that extracts
  what the rest of the pipeline needs from JS/TS without a Node dependency:
  ES6 / dynamic / CommonJS imports, top-level exports (including
  `export default { fetch, scheduled }` Worker shape), cheap effect /
  state signals, and a `classify_js_tier` that honours explicit `aN_*`
  placement first, then infers from surface signals.

`scout_walk.iter_source_files` walks every recognised extension in one
pass and skips vendored / build / cache directories
(`node_modules`, `dist`, `build`, `coverage`, `.next`, `.nuxt`,
`.wrangler`, `.turbo`, plus the Python equivalents). `wire_check`
classifies each file by the tier directory it lives in and dispatches
to a Python-AST or JS-regex import scanner. `certify_checks` recognises
JS test conventions (`*.test.*`, `*.spec.*`, `__tests__/`) alongside
the Python `tests/test_*.py` shape.

The behavioural pytest runner and the runtime-import smoke check remain
Python-only — they're the +55 score components that prove "the package
actually does what its tests say." JS / TS packages are scored on the
+45 polyglot-aware structural axes (docs, tests-present, tier layout,
upward-import discipline).

## Principal data flows

### `forge auto` (flagship)

```
target_repo
    │
    ▼
[a1] scout_walk.harvest_repo  →  scout report (.atomadic-forge/scout.json)
    │
    ▼
[a1] cherry_pick.select_items →  cherry manifest (.atomadic-forge/cherry.json)
    │
    ▼
[a3] forge_pipeline.run_finalize
       ├─ copy each picked symbol's source file into a{N}/<slug>.py
       ├─ emit STATUS.md
       ├─ [a1] wire_check.scan_violations
       └─ [a1] certify_checks.certify
    │
    ▼
output/                 STATUS.md + tier tree + .atomadic-forge/assimilate.json
```

### Specialty pipelines

- `forge emergent scan` walks the tier tree, builds a typed signature graph,
  and surfaces composition chains via `find_chains` + `rank_chains`.
- `forge synergy scan` walks `commands/`, builds `FeatureSurfaceCard`s, and
  detects 5 synergy kinds (json_artifact, in_memory_pipe, phase_omission,
  shared_schema, shared_vocabulary).
- `forge commandsmith sync` regenerates the auto-loaded `commands/_registry.py`
  + per-command Markdown + smoke results.

## Conformance

`forge certify` produces a `CertifyResult` with four mechanical checks:

1. Documentation: README.md OR ≥2 docs/*.md
2. Tests: tests/test_*.py OR tests/*_test.py present
3. Tier layout: ≥3 tier directories present
4. Import discipline: zero upward-import violations

Score = 100 - 25 per failed check. Each check has a `detail` block with
the evidence used.

## Provenance

Every `--apply` writes to `.atomadic-forge/lineage.jsonl` — append-only
JSON Lines with timestamp + artifact name + relative path. This is the
trail an auditor follows; the cryptographic signing chain is on the
roadmap (0.2) and the schema (`atomadic-forge.<x>/v1`) already names what
it'll sign.
