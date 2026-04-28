# Atomadic Forge — Roadmap

_Version-paced. Each line is a real, tractable next step, not a vision._

## 0.1 — _Shipped_

- 5-tier monadic standard with `import-linter` contract
- `forge auto` / `recon` / `cherry` / `finalize` (absorption pipeline)
- `forge iterate` / `evolve` / `demo` (LLM-driven generation loop)
- 3-way constraint-satisfaction feedback (wire + certify + emergent + reuse)
- Behavioral pytest runner (closes identity-stub gameability)
- Per-package auto-scaffolding (pyproject + README + tests dir + tier inits)
- Tier `__init__` re-export rebuilder (idempotent, banner-gated)
- LLM provider matrix: Gemini (free tier) / Anthropic / OpenAI / Ollama / stub
- Auto-appending evolution log + transcript log per run
- 90+ pytest tests

## 0.2 — _Today (polyglot)_

JavaScript and TypeScript classified by the same 5-tier law as Python:

- **Polyglot file scanning** — `recon`, `wire`, `certify` walk `.py`,
  `.js`, `.mjs`, `.cjs`, `.jsx`, `.ts`, `.tsx`. `node_modules/` and
  friends skipped automatically.
- **Pure-Python JS parser** — ES6 / dynamic / CommonJS imports, exports,
  Worker default-`{ fetch, scheduled }` shape, class / state signals.
  No Node dependency.
- **Tier classification for JS/TS** — explicit `aN_*/` directory wins;
  otherwise inferred from surface signals (Worker → a4, class with
  state → a2, export-const-only → a0, pure-functions module → a1).
- **Polyglot wire-check** — upward-import detection for JS specifiers
  (`"../a3_og_features/foo"`) alongside Python `from`-imports; each
  violation tagged with `language`.
- **Polyglot certify** — JS test conventions (`*.test.*`, `*.spec.*`,
  `__tests__/`) and JS-style `aN_*/` directories anywhere under the
  root count toward `tests` and `tier_layout` PASS.
- **Per-language recon output** — `python files: N`, `javascript
  files: M`, `typescript files: K`, plus `primary_language` and
  recommendations.
- **Three static showcase demos** — `js-counter`, `js-bad-wire`,
  `mixed-py-js`. No LLM key required.
- **192 passing tests.**

The runtime-import smoke (+25 score points) and behavioural pytest gate
(+30 points) remain Python-only; JS/TS packages are scored on the +45
polyglot-aware structural axes.

## 0.3 — _Next 90 days_

Sharpening for adoption:

- **Adversarial test inputs** — Forge itself generates 3–5 random inputs
  for each emitted public function and asserts non-degenerate output.
  Catches gameable LLM-written tests.
- **GitHub Action variant** — `forge-action` runs on every PR, posts
  conformance report as a comment, blocks merge below threshold.
- **Hosted certify dashboard** — public read URL per project showing the
  conformance trajectory over time.
- **`forge serve` daemon** — long-lived process exposing a JSON-RPC API
  so editors and CI can pipe code through Forge as a service.
- **Cryptographic certificate signing** — bind the `signed_by` field to
  a real key, make certificates verifiable.
- **JS/TS behavioural gate** — wire `npm test` / Vitest into the
  certify scorer so JS packages can earn the +30 behavioural points
  the same way Python does.
- **Rust support** — apply the 5-tier law via tree-sitter parsing.

## 0.4 — _3–6 months_

Multi-language + ecosystem:

- Rust + Go first-class support
- Plugin system: per-language tier classifiers, per-language wire scanners
- Pypi-hosted release with the `forge` console script
- VS Code extension that surfaces wire violations inline
- Forge runs on PR diffs (not whole repos) for CI speed
- Multi-LLM ensemble (ask N providers in parallel, take the highest score)

## 1.0 — _12+ months_

The architecture-aware coding standard most teams default to:

- 5+ language support
- Verified-build artifacts (deterministic + signed)
- Synergy scan rolled into the iterate loop (suggests un-wired feature
  pairs at every turn)
- Self-modifying Forge: the synergy + commandsmith pipeline produces new
  Forge subcommands, runs them through the same certify gate, and adopts
  what survives
- LoRA adapters trained on Forge transcripts (so an open-source small
  model is competitive with paid frontier models on architecture-aware
  generation specifically)
- The architecture-substrate is the obvious thing to plug in front of
  Cursor / Devin / Cognition / Lovable — and they pay for the privilege

## What we will NOT do

For honesty's sake:

- We will not pretend Forge is AGI.
- We will not pretend it replaces Cursor or Devin.
- We will not promise a launch date until 0.2 is in CI on a real customer.
- We will not add features that don't pass their own certify check on the
  Forge repo itself.

## How to influence the roadmap

- Open an issue describing your use case.
- Submit a PR that satisfies `forge wire` + `forge certify` ≥ 90 on the
  Forge repo itself (i.e. eat its own dog food).
- Run `forge demo run` and post the trajectory.
