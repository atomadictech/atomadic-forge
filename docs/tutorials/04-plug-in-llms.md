# 04 — Plug in LLMs

Forge is the architecture substrate. The LLM is the generation engine.
The two are loosely coupled by design — same Forge, swap the model,
watch the trajectory carry harder tasks higher.

## The provider matrix

| Provider | Cost | Latency | Quality | When to use |
|----------|------|---------|---------|-------------|
| `nexus` / `aaaa-nexus` | paid | ~2–8s | Strong + guarded | Your AAAA-Nexus/HELIX agent path; best default when configured |
| `gemini` | **free tier** | ~2–5s | Strong | Best free option; daily quota resets |
| `anthropic` | paid (~$3/M tok) | ~3–8s | Highest code quality | Closing hard tasks; production runs |
| `openai` | paid (~$0.15/M tok mini, ~$2.50/M tok 4o) | ~2–6s | Strong | Cheap GPT path |
| `openrouter` | free tier available | ~2–10s | Model-dependent | Broad model access; good fallback when Gemini quota is exhausted |
| `ollama` | **free, local** | depends on hardware | Bounded by model size | Offline, private, unlimited |
| `stub` | free | instant | n/a (deterministic) | Tests, CI, dry-runs |

## Switching providers

`forge` resolves providers in this order when `--provider auto`:

1. `AAAA_NEXUS_API_KEY`
2. `ANTHROPIC_API_KEY`
3. `GEMINI_API_KEY` / `GOOGLE_API_KEY`
4. `OPENAI_API_KEY`
5. `OPENROUTER_API_KEY`
6. `FORGE_OLLAMA=1`
7. fallback to `stub`

You can always force a specific one:

```bash
forge evolve run "..." ./out --provider gemini    # forces Gemini
forge chat repl --provider nexus --context src     # chat through your agent
forge evolve run "..." ./out --provider ollama    # forces local
```

## Setting up each provider

### Gemini (free tier — recommended for getting started)

1. Get a free key at <https://aistudio.google.com/apikey>.
2. Set it as an env var:
   ```bash
   export GEMINI_API_KEY=$(your-key)
   ```
3. (Optional) override the model:
   ```bash
   export FORGE_GEMINI_MODEL=gemini-2.5-flash    # default
   # or gemini-2.0-flash if you hit 503s
   ```
4. Run: `forge evolve run "..." ./out --provider gemini`

Free tier limits as of early 2026: ~15 requests/minute, ~1500
requests/day on `gemini-2.5-flash`. A typical evolve run is 4–10
LLM calls, so you can do 100+ free runs per day.

### AAAA-Nexus / HELIX agent

```bash
export AAAA_NEXUS_API_KEY=an_...
forge chat ask "what should I do before release?" --provider nexus --context .
forge evolve run "..." ./out --provider nexus
```

`--provider auto` chooses this path first when the key is present. Override
with `--provider gemini`, `--provider openrouter`, etc. when you want a
different backend for one run.

### Anthropic Claude (paid)

```bash
export ANTHROPIC_API_KEY=$(your-key)
forge evolve run "..." ./out --provider anthropic
```

Default model is `claude-3-5-sonnet-latest`. Override via the env or
edit `llm_client.AnthropicClient.__init__` if you need to.

### OpenAI (paid)

```bash
export OPENAI_API_KEY=$(your-key)
forge evolve run "..." ./out --provider openai
```

Default model is `gpt-4o-mini` (cheap). For higher quality on hard
tasks, edit the client to use `gpt-4o`.

### OpenRouter (free tier available)

```bash
export OPENROUTER_API_KEY=sk-or-...
export FORGE_OPENROUTER_MODEL=google/gemma-3-27b-it:free
forge iterate run "..." ./out --provider openrouter
```

Some OpenRouter models reject system-role messages; Forge retries once with
the system instruction folded into the user prompt when that happens.

### Ollama (local, free)

```bash
ollama pull qwen2.5-coder:1.5b         # small fallback for busy machines
ollama pull qwen2.5-coder:7b           # 4–5 GB, recommended coding baseline
# or:
ollama pull codellama:7b-instruct       # 3.8 GB
ollama pull deepseek-r1:8b              # 5.2 GB, reasoning-tuned

export FORGE_OLLAMA=1
export FORGE_OLLAMA_MODEL=qwen2.5-coder:7b
forge evolve run "..." ./out --provider ollama
```

Ollama runs local — fully private, no rate limits, no API key. The
quality ceiling is bounded by the model size; 7B models will plateau
around 60–90% on most tasks. 13B / 34B models close more gaps.

If your PC is busy, prefer the small profile:

```bash
export FORGE_OLLAMA=1
export FORGE_OLLAMA_MODEL=qwen2.5-coder:1.5b
export FORGE_OLLAMA_NUM_PREDICT=768
export FORGE_OLLAMA_TIMEOUT=180
forge chat ask "summarise this repo" --provider ollama --context .
```

If the machine is idle and you want stronger code output:

```bash
export FORGE_OLLAMA_MODEL=qwen2.5-coder:7b
export FORGE_OLLAMA_NUM_PREDICT=1536
export FORGE_OLLAMA_TIMEOUT=420
```

`FORGE_OLLAMA_NUM_PREDICT` caps generated tokens per call. Lower it first
if Ollama starts paging or crashing. `FORGE_OLLAMA_TIMEOUT` controls how
long Forge waits before surfacing a clean provider error.

Local bakeoff on April 28, 2026, using this repo as the seed:

| Model | Result | Notes |
|-------|--------|-------|
| `qwen2.5-coder:7b` | 7/10 requested rounds, final score 60, wire PASS | Best local coding baseline from the completed runs; halted on stagnation |
| `codellama:7b-instruct` | 10/10 rounds, final score 60, wire PASS | More symbols, slower, score dipped mid-run then recovered |
| `qwen2.5-coder:1.5b` | 10/10 rounds, final score 39, wire PASS | Stable on a busy PC; useful for smoke checks, not best for release-quality generation |
| `qwen3:8b` | partial output, timed out before evolve completed | Generated useful files but exceeded the default local timeout |
| `llama3.1:8b` / `deepseek-r1:8b` | provider failed with Ollama 500 in this local runtime | Retry after unloading other models or restarting Ollama |

### Stub (offline — for tests/CI)

```bash
forge evolve run "..." ./out --provider stub
```

Returns canned responses. Used by Forge's own pytest suite for
deterministic CI runs. Not useful for real generation.

## Picking the right provider for the task

| Task complexity | 7B local | Free Gemini | Paid GPT-4o-mini | Paid Sonnet |
|-----------------|----------|-------------|-------------------|-------------|
| Calculator / FizzBuzz | 90 | 90 | 90+ | 95+ |
| KV-store / slug | 70–90 | 90 | 95 | 95+ |
| Markdown converter | 50–60 (stuck) | 90 (1 round) | 95 | 95+ |
| JSON validator with rules | 50 | 80–90 | 90 | 95 |
| Tiny templating engine | 40 | 80 | 90 | 95 |

These are observed numbers from live `forge demo` and `forge evolve`
runs. The pattern: 7B models hit a complexity ceiling around the
markdown-converter level; 8B-13B local models climb a bit more; cloud
frontier models clear most "tutorial-grade" tasks.

## Transparency

Every prompt + response is logged to
`<output>/.atomadic-forge/transcripts/run-<ts>.jsonl`. The format:

```jsonl
{"kind":"system","content":"You are a code-generation engine...","ts_utc":"…"}
{"kind":"prompt","role":"user","content":"# Intent\n…","ts_utc":"…"}
{"kind":"response","role":"assistant","content":"[{\"path\":\"…\"}]","ts_utc":"…"}
{"kind":"prompt","role":"user","content":"# Forge feedback (iteration 1)…","ts_utc":"…"}
{"kind":"response","role":"assistant","content":"[…]","ts_utc":"…"}
```

This is the audit trail. Inspect it with `jq` or just `cat`.

## Best practices

- **Start with stub or local** while you tune the intent prompt.
- **Switch to Gemini** to validate the intent against a real model on
  free tier.
- **Switch to Sonnet/4o** only when you've hit a quality ceiling that
  matters and the task is worth the cost.
- **Don't paste API keys into shared chats.** Always env vars. Always.
