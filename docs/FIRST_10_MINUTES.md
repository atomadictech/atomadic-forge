# Forge in 10 minutes

This is the **canonical onboarding path**. One linear sequence, no
contradictions. If you finish this page you will have run Forge against
both the offline showcase and a real repository.

> Looking for the sub-pages? `docs/01-getting-started.md`,
> `docs/03-tutorial.md`, and `docs/tutorials/01-quickstart.md` go deeper
> on individual topics. They all assume you have already done the path
> on this page.

---

## 0. Install (60 seconds)

Forge is not yet on PyPI. For now there is exactly **one** install path:

```bash
git clone https://github.com/atomadictech/atomadic-forge
cd atomadic-forge
pip install -e ".[dev]"
forge --help
```

Requirements: Python 3.10+. No Node.js install needed even for JS/TS
repos — the JS parser is pure Python.

When `pip install atomadic-forge` lands on PyPI we will update this
page. Until then, use the editable install above.

---

## 1. 30-second offline demo (no key)

```bash
forge demo run --preset js-counter
```

What happens (~10s wallclock):

- Forge writes a clean a0..a4 JavaScript counter package into
  `./forge-demo-js-counter/`.
- It runs `recon`, `wire`, and `certify` on the result.
- It prints a `DEMO.md` with the verdict (wire PASS, certify ~60/100 —
  see the README for why JS-only ceilings at 60).

You have now seen the absorb-wire-certify pipeline end-to-end **without
spending an API token or installing a model**. If this works, your
install is good.

> Why 60/100 and not 100? The +25 runtime-import smoke gate and the +30
> behavioural pytest gate are Python-only today. JS scores on the four
> structural axes (docs, tests-present, tier layout, import discipline).

---

## 2. 10-second free analysis (no key)

Point Forge at a repo you actually care about and let it tell you what
it sees:

```bash
forge recon /path/to/your-repo
```

Wallclock: ~10 seconds for repos under a few hundred files.

You get a one-screen summary: file count by language, symbol count, the
tier distribution Forge would assign, and an effect distribution
(pure / state / io). No files written. No network call. No key.

This is the cheapest meaningful question you can ask Forge.

---

## 3. Pick a branch

Now decide what you actually want.

> **Decision rule:** if the code already exists, use **3a — absorb**.
> If you only have an idea and want Forge to generate the code, use
> **3b — generate from intent**. Do not run both on the same target.

### 3a. Absorb an existing repo

You have code. You want it re-tiered into the 5-tier layout, scored,
and gated.

```bash
# Step 1 — dry-run (~30 seconds, writes nothing under your repo,
# only diagnostics under .atomadic-forge/).
forge auto /path/to/your-repo ./output

# Step 2 — apply for real.
forge auto /path/to/your-repo ./output --apply --package my_project

# Step 3 — confirm imports flow upward only.
forge wire ./output/src/my_project

# Step 4 — score the result.
forge certify ./output --package my_project
```

Expected: `forge wire` returns PASS or a small list of upward-import
violations to triage; `forge certify` returns 60-100/100 depending on
docs, tests, and wire cleanliness.

This branch needs **no** API key — `forge auto` rewrites architecture,
it does not call an LLM unless you opt into `iterate` / `evolve`.

For deep-dive on this branch: [03-tutorial.md](03-tutorial.md).

### 3b. Generate from intent

You only have a paragraph describing what you want. You want Forge to
ask an LLM to draft the code, then absorb the result and gate it.

```bash
# Get a free key from https://aistudio.google.com/apikey
export GEMINI_API_KEY=your-key-here   # never commit this

# 4 rounds of intent -> code -> absorb -> wire -> score, on Gemini.
# Wallclock: 60-120s.
forge iterate run "build a tiny calculator CLI" ./out \
    --package calc --provider gemini --max-iterations 4
```

Expected: a real, importable, pip-installable Python package under
`./out`, with passing tests, a generated README, and a transcript of
every LLM exchange under `./out/.atomadic-forge/`.

For deep-dive on this branch: [04-llm-loops.md](04-llm-loops.md).

---

## 4. Pick a provider (cost / privacy / quality)

| Provider | Cost | Privacy | Quality | Pick when |
|----------|------|---------|---------|-----------|
| `stub` | $0 | fully offline | n/a | tests, CI dry-runs, scripts |
| `ollama` | $0 | fully local | medium | $0 budget AND privacy required |
| `gemini` | free tier | cloud (Google) | high | $0 budget, network OK — **default recommendation** |
| `anthropic` | paid | cloud (Anthropic) | highest | quality matters more than cost |

`stub` and `ollama` are the only fully offline providers. Anything else
will make a network call. See [AIR_GAPPED.md](AIR_GAPPED.md) if you are
on a SCIF / SIPR / on-prem regulated network.

`forge iterate run … --provider auto` resolves in this order if no
explicit `--provider` is given: AAAA-Nexus, Anthropic, Gemini, OpenAI,
OpenRouter, Ollama, then `stub`. First one with credentials wins.

---

## 5. Wallclock cheatsheet

These are realistic wallclock numbers on a developer laptop. Network
latency varies; treat as floors, not promises.

| Step | Provider | Wallclock |
|------|----------|-----------|
| `forge demo run --preset js-counter` | none | ~10s |
| `forge recon ./repo` | none | ~10s for <500 files |
| `forge auto ./repo ./out` (dry-run) | none | ~30s |
| `forge auto ./repo ./out --apply` | none | ~45s |
| `forge wire ./out/src/pkg` | none | <5s |
| `forge certify ./out --package pkg` | none | ~5s |
| `forge iterate run "..." --max-iterations 4` | gemini | 60-120s |
| `forge iterate run "..." --max-iterations 4` | anthropic | 90-180s |
| `forge iterate run "..." --max-iterations 4` | ollama qwen2.5-coder:7b | 4-10 min |
| `forge evolve run "..." --auto 5` | gemini | 5-12 min |

Add ~10-30% if your machine is busy.

---

## 6. What's next

You now know enough to use Forge productively. For specific topics:

- [02-commands.md](02-commands.md) — every CLI verb, flag by flag.
- [03-tutorial.md](03-tutorial.md) — step-by-step absorption walkthrough on a real repo.
- [04-llm-loops.md](04-llm-loops.md) — `iterate`, `evolve`, prompts, the loop.
- [05-faq.md](05-faq.md) — troubleshooting, common gotchas.
- [tutorials/](tutorials/) — quickstart tutorials and the JS / TS path.
- **[AGENTS_GUIDE.md](AGENTS_GUIDE.md)** — using Forge from a coding
  agent (Cursor / Claude Code / Aider / Devin / Copilot / Codex) via
  the built-in MCP server. One config snippet, **24 tools**, 5
  resources. The fastest way to put Forge in front of every PR your
  team's agents touch.
- [MULTI_REPO.md](MULTI_REPO.md) — absorbing more than one repo at once.
- [CI_CD.md](CI_CD.md) — GitHub Actions, GitLab CI, pre-commit.
- [AIR_GAPPED.md](AIR_GAPPED.md) — offline / on-prem install.
- [RECEIPT.md](RECEIPT.md) — the canonical JSON wire format Forge emits
  (reach for this once you start scripting around `forge certify
  --emit-receipt`).
- [FORMALIZATION.md](FORMALIZATION.md) — paper citations for the certify gates.

If something on this page contradicts what you read in another doc,
**this page wins** and the other doc is the bug. File an issue.
