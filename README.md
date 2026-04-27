# Atomadic Forge

**Absorb · Enforce · Emerge.**

The architecture guardian for the age of AI-generated code.

```bash
pip install atomadic-forge

forge auto ./some-python-repo ./out
forge auto ./some-python-repo ./out --apply       # actually write files
```

Forge takes any Python repository, materialises it into a verified 5-tier
monadic architecture, enforces a strict upward-only import law on every
file, surfaces compositions across the catalog that the original authors
never wired, and (optionally) auto-registers each absorbed feature as a new
CLI command.

It is **not** a code generator. It does not write code from scratch. It
re-organises, enforces, and composes code that already exists — including
the code your AI agent just emitted.

## Why this exists

AI agents now produce 30–50% of new code in many teams. The output is fast,
often correct, and almost universally **architecturally incoherent** —
god classes, leaky abstractions, circular imports, the same concept spelled
five different ways. Linters say *no*. Forge says *"yes, but reorganised
like this"* and shows the diff.

## The 5-tier law

Every Python file belongs to exactly one tier. Tiers compose **upward only**:

| Tier | Directory | Lives here | May import |
|------|-----------|------------|------------|
| a0 | `a0_qk_constants/` | Constants, enums, TypedDicts | Nothing |
| a1 | `a1_at_functions/` | Pure functions | a0 |
| a2 | `a2_mo_composites/` | Stateful classes | a0, a1 |
| a3 | `a3_og_features/` | Feature orchestrators | a0–a2 |
| a4 | `a4_sy_orchestration/` | CLI / entry points | a0–a3 |

`forge wire` mechanically detects violations. `import-linter` enforces it
at CI. The contract lives in `pyproject.toml` so it travels with the repo.

## 60-second quickstart

```bash
# 1. Install (editable, while in development)
git clone <this-repo> atomadic-forge && cd atomadic-forge
pip install -e ".[dev]"

# 2. One-shot: absorb a repo end-to-end (dry-run by default)
forge auto path/to/legacy-repo ./out

# 3. Look at what would happen
forge recon path/to/legacy-repo

# 4. Commit to materialisation
forge auto path/to/legacy-repo ./out --apply --package my_absorbed

# 5. Verify the result
forge wire ./out/src/my_absorbed
forge certify ./out --package my_absorbed
```

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

## Verbs

### Core (the absorb chain)

| Verb | What it does |
|------|--------------|
| `forge auto` | Single command: scout → cherry → assimilate → wire → certify. Dry-run unless `--apply`. |
| `forge recon` | Walk a repo, classify every public symbol, write `.atomadic-forge/scout.json`. |
| `forge cherry` | Build a cherry-pick manifest from the latest scout. `--pick all` or explicit qualnames. |
| `forge finalize` | Materialise the cherry manifest into a tier-organised destination + run wire + certify. |
| `forge wire` | Scan a tier-organised package for upward-import violations. |
| `forge certify` | Score documentation, tests, layout, import discipline. |

### Specialty (advanced; lazily registered)

| Verb | What it does |
|------|--------------|
| `forge emergent` | Symbol-level composition discovery — find chains where the output of A flows into B in non-obvious ways. |
| `forge synergy` | Feature-level producer/consumer detection + auto-implement adapter generation. |
| `forge commandsmith` | Auto-register, document, and smoke-test every CLI command in `commands/`. |
| `forge feature-then-emergent` | Run any feature → fan its JSON output into emergent scan. The universal pipe. |

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

## Known limits (honest)

Forge ships with concrete capabilities and named limits — no overpromise.

1. **Python only.** TypeScript / Rust support is on the roadmap, not in 0.1.
2. **Building material, not finished software.** The output of `forge auto`
   is a tier-organised starter skeleton, not a deployable application. Every
   apply emits a `STATUS.md` listing required follow-up (integration tests,
   runtime config, secrets, observability).
3. **No semantic merge.** Two `class User` from different repos do not
   reconcile — Forge tracks the conflict via `--on-conflict` (rename / first
   / last / fail) but does not unify behaviour.
4. **Auto-generated adapters are scaffolding.** The synergy pipeline emits
   adapter modules with `# REVIEW:` markers. Run them, read them, refine.
5. **Tier classification is heuristic.** Word-boundary tokens + body-state
   detection. The scout report logs the rationale per symbol so you can
   override anything that classifies wrong.
6. **Conformance certificates are not yet cryptographically signed.** The
   schema is in place; the signing chain ships in 0.2.

## Design principles

- **Absorb-first, generate-never.** Forge never writes code from scratch.
  It re-organises code that already exists.
- **Dry-run by default.** No verb writes to disk without `--apply` or
  equivalent — except `.atomadic-forge/` manifests, which are diagnostic.
- **The 5-tier law is non-negotiable.** Anything that ships with Forge
  passes its own `wire` scan.
- **Honest output.** Every report dict has a `schema_version`. Every
  apply emits a `STATUS.md`. Every artifact is provable, not pitched.

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

## Status

**Experimental, working, honest.** Tested end-to-end on its own codebase
plus reference Python repos. Not yet shipped to a public registry.
