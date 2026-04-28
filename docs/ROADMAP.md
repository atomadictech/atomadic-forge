# Atomadic Forge — Roadmap

_Version-paced. Each line is a real, tractable next step, not a vision._

## 0.1 — _Today_

What ships:

- 5-tier monadic standard with `import-linter` contract
- `forge auto` / `recon` / `cherry` / `finalize` (absorption pipeline)
- `forge iterate` / `evolve` / `demo` (LLM-driven generation loop)
- 3-way constraint-satisfaction feedback (wire + certify + emergent + reuse)
- Behavioral pytest runner (closes identity-stub gameability)
- Per-package auto-scaffolding (pyproject + README + tests dir + tier inits)
- Tier `__init__` re-export rebuilder (idempotent, banner-gated)
- LLM provider matrix: Gemini (free tier) / Anthropic / OpenAI / Ollama / stub
- Auto-appending evolution log + transcript log per run
- 90+ pytest tests, all live-validated trajectories

**0.1 is shippable today.** Real packages emerge with honest scores.

## 0.2 — _Next 90 days_

Sharpening for adoption:

- **Wrong-package gating** — refuse to credit behavioral score when LLM
  emits to a package other than the one requested (partial fix shipped this
  session; more robust enforcement coming).
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
- **TypeScript proof-of-concept** — apply the 5-tier law to a TS package
  via tree-sitter parsing.

## 0.3 — _3–6 months_

Multi-language + ecosystem:

- TypeScript / JavaScript first-class support
- Rust support
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
