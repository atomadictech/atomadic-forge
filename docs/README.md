# Atomadic Forge Documentation

Welcome to the Forge documentation. Forge is a polyglot architecture
substrate — as of 0.2 it classifies Python and JavaScript / TypeScript
under the same 5-tier monadic law. Start with the guide that matches
your goal:

## 🚀 New to Forge?

Start here: **[Getting Started](01-getting-started.md)** (5 minutes)

- What Forge is and what it does
- Installation instructions
- Your first absorption (dry-run → apply → verify)
- JavaScript / TypeScript quick example

For a JS/TS-only walk-through, jump to
**[tutorials/06-javascript-quickstart.md](tutorials/06-javascript-quickstart.md)**.

## 📚 How-to guides

### [Command Reference](02-commands.md)
Detailed documentation of every command:
- `forge auto` — The flagship command
- `forge recon`, `forge cherry`, `forge finalize` — The absorption pipeline
- `forge wire`, `forge certify` — Verification and scoring
- `forge iterate`, `forge evolve` — LLM-driven code generation
- Specialty commands: `emergent`, `synergy`, `commandsmith`

### [Tutorial: Absorb a Real Repository](03-tutorial.md)
Step-by-step walkthrough:
1. Analyze a repo with `recon`
2. Dry-run with `auto`
3. Materialize with `--apply`
4. Detect violations with `wire`
5. Fix violations manually
6. Score with `certify`
7. Inspect the provenance trail

### [LLM Loops: Code Generation with Architecture](04-llm-loops.md)
Generate code from intent using AI:
- `forge iterate` — Single-shot generation (N rounds)
- `forge evolve` — Recursive improvement (catalog grows each round)
- Provider setup (Gemini, Claude, GPT, Ollama, Stub)
- Tips for better code quality
- Examples and troubleshooting

## ❓ FAQ & Troubleshooting

**[FAQ](05-faq.md)** — Common questions:
- General questions (formatter vs. Forge, code generation vs. absorption)
- Installation & setup (permission errors, missing commands)
- Using `forge auto` (dry-runs, conflicts, symbol picking)
- Wire violations (how to fix upward imports)
- Certify scoring (how to improve scores)
- LLM loops (rate limits, bad code quality)
- Performance & scalability
- Advanced topics (customization, extensions)

## 🏗️ Architecture

See [ARCHITECTURE.md](../ARCHITECTURE.md) for details on Forge's own design:
- The 5-tier monadic standard (a0–a4)
- Data flows (scout → cherry → assimilate → wire → certify)
- Principal commands and their implementation
- Conformance scoring

## 📖 Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for:
- How to build Forge locally
- Running the test suite
- Coding conventions (Forge itself follows monadic tiers)
- Submitting PRs

## 🔗 Quick links

- **GitHub:** https://github.com/atomadictech/atomadic-forge
- **License:** [BSL-1.1](../LICENSE) (free for non-production, commercial license for production, converts to Apache 2.0 in 2030)
- **Status:** Experimental, working, honest (0.1.0)

## 📊 Versions

This documentation is for **Atomadic Forge 0.2.0**.

- **0.1.0** — Initial release
  - Core absorption pipeline
  - LLM loops (iterate, evolve)
  - 90+ passing tests
  - Python only

- **0.2.0** (current) — Polyglot
  - JavaScript and TypeScript classified under the same 5-tier law
  - Pure-Python JS parser (no Node dependency); `node_modules/` skipped
  - Wire scan, certify checks, recon recommendations all polyglot-aware
  - Three new static showcase demo presets (`js-counter`, `js-bad-wire`, `mixed-py-js`)
  - Canonical `IGNORED_DIRS` + file-class taxonomy (source / docs / config / asset) and nested-`docs/`/`guides/` discovery
  - 212 passing tests

- **0.3.0** (roadmap)
  - Rust support
  - Cryptographic signing of conformance certificates
  - GitHub Action variant + hosted certify dashboard
  - Semantic merge (intelligent handling of duplicate classes)
  - IDE plugins (VS Code, JetBrains)

## 💡 Pro tips

1. **Always dry-run first:** `forge auto ./repo ./out` (no `--apply`)
2. **Use JSON for scripting:** `--json` flag outputs machine-readable format
3. **Check the STATUS.md:** Tells you what still needs work
4. **Read the provenance trail:** `.atomadic-forge/lineage.jsonl` is your audit log
5. **Start with `recon`:** Understand the repo before absorbing it

## 🆘 Need help?

- **Errors during absorption?** See [FAQ: Using forge auto](05-faq.md#using-forge-auto)
- **Import violations?** See [FAQ: Wire check](05-faq.md#wire-check-import-violations)
- **LLM quality issues?** See [FAQ: LLM loops](05-faq.md#llm-loops)
- **Found a bug?** Open an issue on [GitHub](https://github.com/atomadictech/atomadic-forge/issues)

---

**Ready?** Start with [Getting Started](01-getting-started.md).
