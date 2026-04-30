# Air-gapped install

Forge runs on networks with no outbound internet. This page covers the
SCIF / SIPR / on-prem regulated case.

> **Bottom line:** the absorb pipeline (`recon`, `auto`, `cherry`,
> `wire`, `certify`) is fully offline. The LLM-driven verbs
> (`iterate`, `evolve`, `chat`) are offline **only** when you use the
> `stub` or `ollama` provider. Everything else (`gemini`, `anthropic`,
> `openai`, `openrouter`, `aaaa-nexus`) requires network.

---

## Why air-gapped

You are deploying Forge inside a SCIF, on SIPRNet, on a regulated
hospital LAN, on a defense contractor's classified subnet, or any
on-prem environment where outbound HTTPS is blocked or audited. The
constraints we have seen in the wild:

- No `pip install` from PyPI; the package index is unreachable.
- No outbound LLM API calls; even Anthropic and OpenAI are blocked at
  the egress firewall.
- No `git clone` from GitHub; source has to be transferred via
  approved physical media.
- Local model weights are allowed if pre-staged; downloading them at
  runtime is not.

Forge is designed for this case. The whole product runs offline if you
stage the wheels and the model weights ahead of time.

---

## 1. Pre-stage Forge wheels

On a machine **with** internet (the "connected box"):

```bash
mkdir -p ./forge-wheels
pip download atomadic-forge -d ./forge-wheels
# Or, if Forge is not yet on PyPI:
git clone https://github.com/atomadictech/atomadic-forge
pip wheel ./atomadic-forge -w ./forge-wheels
pip download -r atomadic-forge/requirements.txt -d ./forge-wheels
```

Transfer `./forge-wheels` across the air gap (USB, write-once optical,
your approved data-transfer process).

On the air-gapped machine:

```bash
pip install --no-index --find-links forge-wheels/ atomadic-forge
forge --help    # confirm install
```

The `--no-index --find-links` pair tells pip to install only from the
local directory — no network call.

---

## 2. Pre-stage Ollama models

On the connected box:

```bash
ollama pull qwen2.5-coder:7b      # ~4.7 GB — recommended default
ollama pull qwen2.5-coder:1.5b    # ~1.0 GB — small fallback
ollama pull mistral:7b-instruct   # ~4.4 GB — alternative
```

The downloaded model blobs live under `~/.ollama/models/`. Transfer
that directory across the air gap and drop it into the same path on
the air-gapped box. Ollama will pick them up on next start.

> **Disk budget.** A useful local set is ~10 GB. Plan accordingly.

---

## 3. Tell Forge to use Ollama

Set these environment variables on the air-gapped machine:

```bash
export FORGE_OLLAMA=1
export FORGE_OLLAMA_MODEL=qwen2.5-coder:7b
export FORGE_OLLAMA_NUM_PREDICT=2048    # max tokens per LLM call
export FORGE_OLLAMA_TIMEOUT=600         # seconds before Forge gives up
```

| Var | Default | Use |
|-----|---------|-----|
| `FORGE_OLLAMA` | unset | Set to `1` to make Ollama the resolved provider when `--provider auto`. |
| `FORGE_OLLAMA_MODEL` | `qwen2.5-coder:7b` | Override per-run with `--model`. |
| `FORGE_OLLAMA_NUM_PREDICT` | model default | Cap each generation. Lower if Ollama starts paging. |
| `FORGE_OLLAMA_TIMEOUT` | 300 | Wallclock budget per LLM call. Air-gapped boxes are often slower; 600 is a safer default. |

Then run any LLM-driven verb explicitly against Ollama:

```bash
forge iterate run "build a tiny calculator CLI" ./out \
    --provider ollama --max-iterations 4
```

Or use `--provider auto` and rely on the env vars above to resolve to
Ollama.

---

## 4. What works fully offline

| Verb | Offline? |
|------|----------|
| `forge recon` | yes |
| `forge auto` | yes |
| `forge cherry` | yes |
| `forge finalize` | yes |
| `forge wire` | yes |
| `forge certify` | yes |
| `forge demo run --preset js-counter` (and other static presets) | yes |
| `forge iterate` / `evolve` / `chat` with `--provider stub` | yes |
| `forge iterate` / `evolve` / `chat` with `--provider ollama` | yes (after step 2) |

## What does **not** work offline

| Provider | Offline? | Why |
|----------|----------|-----|
| `gemini` | **no** | Calls `generativelanguage.googleapis.com`. |
| `anthropic` | **no** | Calls `api.anthropic.com`. |
| `openai` | **no** | Calls `api.openai.com`. |
| `openrouter` | **no** | Calls `openrouter.ai`. |
| `aaaa-nexus` / `nexus` | **no** | Calls AAAA-Nexus endpoint over HTTPS. |

If your air-gapped network forbids any of these, do not configure
their API keys — Forge will skip them in `--provider auto` resolution
and fall through to Ollama or stub.

---

## 5. End-to-end air-gapped smoke test

After steps 1–3, run this to confirm the install:

```bash
# Should classify the embedded showcase, no network needed.
forge demo run --preset js-counter

# Should ask local Ollama for a 4-round generation.
forge iterate run "build a tiny calculator CLI" ./out \
    --provider ollama --max-iterations 4

# Should score the result.
forge certify ./out --package calc
```

If all three succeed, your air-gapped install is healthy.

If `forge iterate` hangs, `FORGE_OLLAMA_TIMEOUT` is your friend — set
it higher and re-run. If Ollama returns "model not found," the model
blobs were not staged correctly under `~/.ollama/models/` on the
air-gapped box; re-do step 2.
