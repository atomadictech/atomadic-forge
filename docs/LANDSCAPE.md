# Atomadic Forge — Landscape

_Where Forge sits among the AI-coding tools, what it shares, and what's
genuinely uncommon._

## TL;DR comparison

| Tool | What it does | Where it stops | How Forge compares |
|------|--------------|----------------|--------------------|
| **GitHub Copilot** | Autocomplete in editor | Single-line / function scope; no architecture awareness | Forge enforces *architecture* on whatever Copilot wrote |
| **Cursor** | LLM-driven editor + chat | Excellent IDE, but no architectural law; codebases drift past 50k LOC | Forge is the architecture layer Cursor doesn't have |
| **Cognition Devin** | Autonomous SWE agent | $2B valuation, 13–15% real-world SWE-bench; expensive | Forge is the substrate for *any* agent; cheap, deterministic |
| **Replit Agent** | Build apps from prompts | Web-app focused; opinionated stack; closed ecosystem | Forge produces real Python packages you own and can ship anywhere |
| **Lovable / Bolt / V0** | Prompt → web frontend | Frontend-only; backends and complex logic break down | Forge is a polyglot substrate (Python + JavaScript/TypeScript today; Rust/Go on the roadmap) — the same 5-tier law governs Worker JS and Python back-ends in one repo |
| **GitHub Copilot Workspace** | Plan → patch → PR | Tied to GitHub; PR-shaped workflows; closed | Forge runs locally, no platform lock-in |
| **AutoGPT / MetaGPT / CrewAI** | Multi-agent orchestration | Frequently chaos; no architectural constraint | Forge gives any agent a hard constraint (the 5-tier law) |
| **import-linter / archunit** | Layered architecture checks | Static enforcement only; no generation | Forge enforces AND generates within the law |
| **AlphaEvolve / Voyager** | Self-improving narrow agent | Research-grade, narrow domains | Forge applies the same shape (recursive self-improvement) to mainstream code generation |
| **Sonar / Snyk Code / Codacy** | Static analysis + security | Reports problems; doesn't synthesize fixes | Forge is constructive — it produces *new* code that satisfies the rules |

## What's actually uncommon in Forge

There are three pieces that, in this combination, I haven't seen elsewhere:

### 1. The 3-way constraint-satisfaction loop

Almost all LLM-coding tools run a 2-way loop:
**LLM generates → tests/lints check → LLM iterates.**

Forge runs **3-way**:

1. **Hard constraint (`wire`)** — the 5-tier law; mechanical, deterministic.
2. **Score gap (`certify`)** — docs, tests, layout, importability, behavior.
3. **Compositional signal (`emergent` + `reuse`)** — *what existing symbols you ignored that would have satisfied the request*.

Cursor / Devin / Cognition feed errors back. None of them feed *missed
composition opportunities* back. That third signal is what makes the
catalog actually accrete capability instead of just expand by re-emission.

### 2. The behavioral certify

Score 100 doesn't mean "the architecture is legal" (that's wire). It
means "the package imports AND its own tests pass AND no stub bodies AND
the layout is correct AND the docs exist." Multiple positive signals,
provable from the artifact alone, no LLM trust required.

When a refine cycle exposes a new gameability hole (identity-function
stubs in cycle 4, wrong-package emission in cycle 6), Forge gets a new
gate — and the score gets harder to fake. That ratchet is the engine.

### 3. The emergent + synergy + commandsmith trinity

These are three pieces nobody else has packaged together:

- **emergent** — find type-compatible composition chains across the catalog.
- **synergy** — find feature-pair connections nobody wired and *generate* the adapter.
- **commandsmith** — auto-register every discoverable verb as a CLI command.

When you point Forge at itself, it suggests novel features, generates the
glue code, and registers them. We already used this loop *during this
session* to ship `forge demo` end-to-end. The loop is real; the
self-extension is testable.

## Where Forge does NOT compete

Be honest about this — it's how launch positioning survives contact with skeptics:

- **Forge is not an editor.** Don't try to use it like Cursor.
- **Forge is not an agent platform.** Don't try to use it like Devin.
- **Forge is not omnilingual yet.** As of 0.2 it classifies Python and
  JavaScript / TypeScript (`.py`, `.js`, `.mjs`, `.cjs`, `.jsx`, `.ts`,
  `.tsx`). Rust and Go are on the roadmap. The runtime-import smoke and
  behavioural pytest gates remain Python-only.
- **Forge is not a hosted service yet.** It runs on your machine.
- **Forge does not write production-ready apps from a prompt.** It produces
  bootstrapped, architecturally-coherent material that needs human review
  for runtime config, secrets, integration tests, and edge cases.

## Where Forge fits in your stack

Most teams will use Forge alongside their existing toolchain:

```
You write intent / spec
    │
    ▼
[Cursor / Copilot / Lovable]   ← rapid generation, in-editor flow
    │
    ▼
[Forge]                        ← architecture enforcement + behavior gating
    │       wire / certify / iterate
    │       3-way constraint-satisfaction loop
    │
    ▼
Real working package with:
- 5-tier architecture
- Behavioral test pass-ratio
- pip-installable
- Auto-generated README + transcripts
- Lineage logged
```

Cursor is the chair you sit in to write code. Forge is the rules of
construction the building has to follow. They're complements, not
replacements.

## Why this is urgent NOW

See [WHY_NOW.md](WHY_NOW.md). Short version: AI is generating 30–50% of
new code in many teams; the architectural debt that produces is
unsustainable; Forge is the pressure valve.
