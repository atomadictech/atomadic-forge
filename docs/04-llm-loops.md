# LLM Loops: Code Generation with Architecture

Forge integrates LLM-driven code generation with automatic absorption and verification. Write a user intent, let the loop generate code, absorb it, fix the architecture, score it, iterate.

## Why LLM loops?

Traditional code generation produces architecturally incoherent output:
- Scattered classes, mixed concerns
- Circular imports, god classes
- Tests scattered across files
- Tier violations everywhere

**Forge's approach:**
1. LLM generates code from user intent
2. Forge absorbs the code into tiers
3. Forge detects violations and scores it
4. LLM reads the violations and improves
5. Repeat until score is high or max iterations reached

Result: **Architecturally coherent code, generated from scratch.**

## Providers

Forge supports multiple LLM providers. Choose based on cost, privacy, quality:

| Provider | Cost | Quality | Privacy | Notes |
|----------|------|---------|---------|-------|
| **Gemini** | Free tier | High | No | Best free option; requires API key |
| **Anthropic (Claude)** | Paid ($) | Highest | No | Highest code quality; requires API key |
| **OpenAI (GPT)** | Paid ($$) | High | No | Fast and capable; requires API key |
| **Ollama** | Free | Medium | Yes | Fully local; runs on your machine |
| **Stub** | Free | Low | Yes | Offline testing; no actual LLM calls |

## Setup

### Gemini (free tier, recommended for trying it out)

```bash
# Get a free key
# Visit: https://aistudio.google.com/apikey
# Copy your API key

export GEMINI_API_KEY=your-key-here

# Test the setup
forge iterate preflight "Build a hello-world CLI"
```

### Anthropic (Claude)

```bash
export ANTHROPIC_API_KEY=sk-your-key-here

forge iterate run "Build a REST API client" ./output \
    --package api_client --provider anthropic
```

### OpenAI (GPT)

```bash
export OPENAI_API_KEY=sk-your-key-here

forge iterate run "Build a web scraper" ./output \
    --package scraper --provider openai
```

### Ollama (fully local & private)

```bash
# First, install Ollama: https://ollama.ai
# Then start the server:
ollama serve

# In another terminal, pull a model:
ollama pull qwen2.5-coder:7b

# Then run Forge:
export FORGE_OLLAMA=1

forge iterate run "Build a file backup tool" ./output \
    --package backup --provider ollama
```

### Stub (for testing, offline)

```bash
# Stub provider returns boilerplate code without calling any LLM
# Useful for testing the pipeline

forge iterate run "Build anything" ./output \
    --provider stub --max-iterations 1
```

## forge iterate: Single-shot generation

Generate code from user intent in one go. The loop runs for `--max-iterations` rounds, each round getting feedback from the previous iteration.

```bash
forge iterate run "INTENT" OUTPUT [OPTIONS]
```

**Options:**
- `--package NAME` — Python package name (default: `generated`)
- `--provider PROVIDER` — LLM provider (default: `auto` which tries gemini→anthropic→openai→ollama)
- `--max-iterations N` — Max rounds (default: 4)

### Example 1: Simple CLI tool

```bash
export GEMINI_API_KEY=your-key

forge iterate run "Build a CLI tool that converts CSV to JSON" ./output \
    --package csv2json --provider gemini --max-iterations 3
```

**What happens:**
1. **Round 1:** Forge prompts the LLM: "Build a CLI tool that converts CSV to JSON using monadic architecture..."
2. LLM generates code (a0 constants, a1 parsers, a2 CSV reader, a3 conversion flow, a4 CLI)
3. Forge absorbs the code into tiers
4. Forge wires (detects violations) and scores
5. **Round 2:** Forge shows LLM the violations and scores, asks for improvements
6. LLM fixes the violations
7. **Round 3:** Another round of feedback and improvement
8. **Output:** Final code at `output/src/csv2json/` with scores and transcript

### Example 2: Web scraper with retries

```bash
forge iterate run \
  "Build a web scraper that handles rate limits and retries with exponential backoff" \
  ./output --package web_scraper --provider anthropic --max-iterations 5
```

### Preflight (dry-run, no LLM call)

See what prompts Forge will send to the LLM without actually calling it:

```bash
forge iterate preflight "Build a task queue processor"
```

**Output:**
```
Forge LLM Loop — Preflight

System prompt:
  [10+ lines of detailed architecture instruction]

First user message:
  "Build a task queue processor"

(no API call made)
```

## forge evolve: Recursive improvement

Keep improving the code over multiple iterations, with the catalog growing each round.

**Round 1:** Generate initial code
**Round 2:** Absorb round 1, identify gaps, generate new features
**Round 3:** Absorb rounds 1–2, improve existing features further
**…**

```bash
forge evolve run "INTENT" OUTPUT [OPTIONS]
```

**Options:**
- `--auto N` — Exactly N rounds
- `--target-score SCORE` — Keep going until reaching score (e.g., 80/100)
- `--package NAME` — Python package name
- `--provider PROVIDER` — LLM provider

### Example: Build a complete markdown-to-PDF service in N rounds

```bash
export ANTHROPIC_API_KEY=sk-...

forge evolve run "Build a markdown-to-PDF conversion service" ./output \
    --auto 5 --package md2pdf --provider anthropic
```

**What happens:**
- **Round 1:** LLM generates: markdown parser (a1), PDF builder (a2), conversion pipeline (a3), CLI (a4)
- **Round 2:** Absorbs round 1, detects that PDF handling is incomplete, prompts LLM to add: font handling, table layouts, images
- **Round 3:** Absorbs rounds 1–2, detects no tests, prompts for: unit tests, integration tests
- **Round 4:** Absorbs all, detects missing logging, prompts for observability
- **Round 5:** Final polish, documentation

**Output:** Fully-functional, tested, documented service in 5 rounds

### With target score

```bash
forge evolve run "Build a REST API for a bookstore" ./output \
    --target-score 85 --provider ollama --package bookstore_api
```

Keeps running rounds until certify score reaches 85/100.

## Understanding the loop feedback

Each iteration, Forge shows the LLM:

```json
{
  "round": 2,
  "previous_code_location": "./output/src/package/",
  "wire_verdict": "FAIL",
  "wire_violations": [
    {
      "file": "a1_at_functions/database_query.py",
      "violation": "a1 ← a2_mo_composites.DatabaseConnection (upward import)"
    }
  ],
  "certify_score": 62,
  "certify_details": {
    "documentation": 0,
    "tests": 25,
    "tier_layout": 25,
    "import_discipline": 12
  },
  "feedback": "Move database_query to a2 or extract pure parsing logic to a1. Add README."
}
```

The LLM reads this and improves.

## Tips for better results

### 1. Be specific about the intent

**Bad:**
```bash
forge iterate run "Build a web app" ./output
```

**Good:**
```bash
forge iterate run "Build a REST API server with user authentication, JWT tokens, and role-based access control using FastAPI" ./output
```

### 2. Mention architectural concerns

```bash
forge iterate run "Build a task queue processor. Use a monadic 5-tier architecture. Tier a1 should contain pure functions for task parsing and validation. Tier a2 should handle queue persistence. Tier a3 should orchestrate retry logic and dead-letter handling." ./output
```

### 3. Use higher-quality providers for complex features

- Gemini: Good for simple features, free
- Claude: Best for complex, multi-component systems
- GPT-4: Fast and capable, good middle ground

### 4. Iterate in rounds, not one huge round

```bash
# Instead of:
forge iterate run "Build a complex system" ./output --max-iterations 1

# Do:
forge iterate run "Build a complex system" ./output --max-iterations 5
# or
forge evolve run "..." ./output --auto 5
```

### 5. Inspect intermediate outputs

```bash
# After round 2, before proceeding to round 3:
forge wire ./output/src/myapp
forge certify ./output --package myapp

# Read STATUS.md to see what's missing
cat ./output/STATUS.md
```

## Troubleshooting

### Provider not found

```
Error: Provider 'gemini' not configured
```

**Solution:** Set the environment variable:
```bash
export GEMINI_API_KEY=your-key
```

### API rate limits

```
Error: 429 Too Many Requests
```

**Solution:**
- Reduce `--max-iterations`
- Use `ollama` (local, unlimited)
- Use `stub` for testing the pipeline before real calls

### Code quality issues

If the LLM is generating low-quality code, try:
- Use Claude (Anthropic) instead of Gemini
- Be more specific about requirements
- Run more iterations
- Inspect intermediate outputs and provide manual fixes

### Stagnation detection

Forge detects if the code quality is not improving over rounds:

```
Halt reason: stagnation_detected
(score hasn't improved in last 2 rounds)
```

**Solution:** Manually fix the issues and run another round, or switch LLM providers.

## Examples

### Example 1: CSV processor (3 min)

```bash
export GEMINI_API_KEY=your-key

forge iterate run "Build a CSV file processor that validates headers, parses rows, and exports to JSON. Use a monadic 5-tier architecture with a0 constants, a1 validators, a2 parsers, a3 processor, a4 CLI." ./output --package csv_proc --provider gemini --max-iterations 3

# Inspect results
forge certify ./output --package csv_proc
cat ./output/STATUS.md
```

### Example 2: Markdown converter (5 min)

```bash
export ANTHROPIC_API_KEY=sk-...

forge iterate run "Build a markdown-to-HTML converter with support for code blocks, tables, and inline formatting. Tier a1: parse markdown syntax. Tier a2: AST builder. Tier a3: HTML rendering pipeline." ./output --package md2html --provider anthropic --max-iterations 5
```

### Example 3: Recursive improvement (10 min)

```bash
forge evolve run "Build a REST API server for managing a to-do list with user accounts, task categories, and due dates" ./output --auto 5 --provider gemini --package todo_api

# Monitor progress
cat ./output/.atomadic-forge/evolve.json | jq '.score_trajectory'
```

## Next steps

- [Command Reference](02-commands.md) — Detailed command options
- [FAQ](05-faq.md) — Common questions
- [Forge Architecture](../ARCHITECTURE.md) — How Forge itself works
