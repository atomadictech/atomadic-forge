# Atomadic Forge — Release Messaging Kit

Use this file as the launch copy source of truth for v0.3.2.

## One-Liners

- The architecture compiler for AI-generated code.
- Use any coding agent you want. Run Forge before the codebase forgets
  its shape.
- Copilots write code. Forge keeps the repo architecturally honest.
- Absorb messy code. Enforce the 5-tier law. Emerge safer capabilities.
- AI made implementation cheap. Forge protects architecture.

## Short Product Description

Atomadic Forge is a polyglot architecture guardian for Python,
JavaScript, and TypeScript repos. It classifies code into a strict
5-tier monadic layout, detects upward-import violations, scores
architecture health, and gives coding agents MCP-native tools for
context, preflight, planning, test selection, and certification.

## Longer Description

AI coding agents can generate code faster than teams can review its
architecture. Atomadic Forge is the missing governance layer: it absorbs
messy or AI-generated repos, enforces a deterministic 5-tier import law,
and emits receipts that make architectural shape auditable in CI and
agent workflows.

Forge is not a replacement for Cursor, Claude Code, Copilot, Devin, or
Codex. It is the complement they need: an architectural substrate that
keeps generated code from turning into unowned, unstructured drift.

## HN Post Draft

Title:

```
Show HN: Forge — an architecture compiler for AI-generated code
```

Body:

```
Hi HN,

I built Atomadic Forge because AI coding agents made a new problem very
obvious: we can generate implementation faster than we can preserve
architecture.

Forge is a CLI + MCP server that scans Python, JavaScript, and TypeScript
repos, classifies files into a 5-tier monadic layout, detects upward
imports, scores architectural conformance, and gives coding agents tools
like context packs, preflight checks, score prediction, selected tests,
and receipts.

The core idea is opinionated:

  a0 constants -> a1 pure functions -> a2 stateful composites ->
  a3 features -> a4 orchestration

Higher tiers may import lower tiers. Lower tiers never import upward.
That single law gives AI agents a shape they can obey and CI can enforce.

It is not meant to replace Copilot/Cursor/Claude Code/Devin. Those tools
write code. Forge is the architectural guardrail for what they write.

Quick start:

  pip install atomadic-forge
  forge recon .
  forge wire src --fail-on-violations
  forge certify . --fail-under 80
  forge mcp serve --project .

Would love feedback from people using AI agents heavily: what
architecture failures are you seeing after the third or fourth generated
feature?
```

## X / Short-Form Thread

1. AI coding agents made code cheap. Architecture became the bottleneck.

2. Atomadic Forge is an architecture compiler for AI-generated code:
   Python, JavaScript, and TypeScript in one 5-tier law.

3. The law is simple:
   `a0 constants -> a1 pure functions -> a2 state -> a3 features -> a4 orchestration`
   Imports go upward only.

4. Copilot/Cursor/Claude Code/Devin write code. Forge keeps the repo
   from forgetting its shape.

5. Run:
   `pip install atomadic-forge`
   `forge recon .`
   `forge wire src --fail-on-violations`
   `forge certify .`

6. It also ships MCP tools for agents: context packs, preflight checks,
   score-patch, selected tests, recipes, repo explanation, and receipts.

7. Use any coding agent you want. Run Forge before generated code turns
   into architectural drift.

## LinkedIn / Launch Post

AI coding assistants are moving from novelty to daily infrastructure.
That changes the bottleneck.

The problem is no longer "can we generate code?" The problem is "can the
codebase keep a coherent architecture while code is generated at agent
speed?"

Atomadic Forge is built for that gap.

Forge is a polyglot architecture substrate for Python, JavaScript, and
TypeScript. It scans repos, classifies code into a 5-tier monadic layout,
detects upward-import violations, scores conformance, and exposes
agent-native MCP tools for planning, preflight, test selection, and
certification.

It is not a competitor to Copilot, Cursor, Claude Code, Devin, or Codex.
It is the layer that makes their output governable.

The core thesis:

AI made implementation cheap. Architecture is now the scarce resource.

Install:

```bash
pip install atomadic-forge
forge recon .
forge wire src --fail-on-violations
forge certify . --fail-under 80
```

## Cold Email: Developer / Founder

Subject: Keeping AI-generated code from turning into architecture debt

Hi [first name],

I saw [specific hook from their work]. I am reaching out because you look
like exactly the kind of builder who is already using AI coding tools
hard enough to hit the next bottleneck: architecture drift.

Atomadic Forge is a CLI + MCP server that sits beside tools like Cursor,
Claude Code, Copilot, Devin, and Codex. Those tools generate code. Forge
scans the repo, enforces a 5-tier import law, scores architectural
conformance, and gives agents context/preflight/test-selection tools so
generated changes stay governable.

Quick shape:

```bash
pip install atomadic-forge
forge recon .
forge wire src --fail-on-violations
forge certify . --fail-under 80
```

The bet is simple: AI made implementation cheap. Architecture is now the
scarce resource.

Would you be open to trying it on one AI-heavy repo and telling me where
the architecture check feels useful or too opinionated?

Thomas

## Cold Email: Journalist / Analyst

Subject: AI coding has a missing architecture layer

Hi [first name],

I read your piece on [specific hook]. One angle I think is under-covered:
AI coding agents are not just changing who writes code. They are changing
the rate at which architecture debt can accumulate.

Atomadic Forge is my attempt at the missing layer. It is an architecture
compiler for AI-generated code: a CLI + MCP server that classifies
Python/JS/TS repos into a strict 5-tier layout, detects upward-import
violations, scores conformance, and gives coding agents guardrails before
they modify the repo again.

The positioning is intentionally complementary:

Copilot/Cursor/Claude Code/Devin write code. Forge keeps the repo
architecturally honest.

If useful, I can send a short demo showing an AI-generated repo being
recon'd, wired, scored, and turned into an agent-readable action plan.

Thomas

## Demo Script

1. Start with the problem:
   "AI agents can now generate code faster than humans can preserve
   architecture."

2. Show a repo:
   `forge recon .`

3. Show architecture law:
   `forge wire src --fail-on-violations --suggest-repairs`

4. Show score:
   `forge certify . --fail-under 80`

5. Show agent-native layer:
   `forge mcp serve --project .`

6. Show why this is different:
   "This is not autocomplete. It is an architecture substrate for
   autocomplete-heavy teams."

## Launch Checklist

- PyPI page install works: `pip install atomadic-forge`.
- README first 10 minutes path works from a clean machine.
- `forge --help`, `forge doctor`, `forge recon .`, `forge certify .`
  all produce polished output.
- GitHub release notes link to `docs/MARKET_POSITIONING.md`.
- HN post avoids inflated claims and asks for specific feedback.
- Outreach copy frames Forge as a complement, not a Copilot rival.
- Demo video shows one concrete repo and one clear before/after.
