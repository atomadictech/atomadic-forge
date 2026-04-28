# 01 — Quickstart (60 seconds)

This is the shortest path from "never seen Forge" to "watching it
generate a working Python package."

## Install

```bash
git clone <this-repo> atomadic-forge && cd atomadic-forge
pip install -e ".[dev]"
forge doctor   # confirms install
```

## Choose a generator

Forge needs an LLM to do the actual writing. Pick the cheapest path
that works for you:

```bash
# Free local (recommended for testing — no quota, fully private):
ollama pull qwen2.5-coder:7b
export FORGE_OLLAMA=1
export FORGE_OLLAMA_MODEL=qwen2.5-coder:7b

# OR free cloud (Google AI Studio):
export GEMINI_API_KEY=$(your-free-key)
```

## Run the headline demo

```bash
forge demo run --preset calc
```

Forge will:

1. Scaffold a complete Python package skeleton (pyproject + README +
   tier dirs + tests/conftest).
2. Ask the LLM to emit the calculator code as a JSON array of files.
3. Materialise those files, run the wire scan, run the LLM's own tests.
4. Iterate until certify passes (typically 1–3 rounds).
5. Invoke the generated CLI as a smoke test.
6. Write `DEMO.md` summarising the run.

The whole thing finishes in 30–90 seconds depending on your LLM. The
final output is a real, importable, pip-installable Python package.

## Verify

```bash
cd ./forge-demo-calc
forge certify . --package calc
pytest tests/
python -m calc.a4_sy_orchestration.cli 7 + 6
```

## Polyglot quickstart (JavaScript / TypeScript)

`forge` classifies JS / TS the same way it classifies Python — no Node
install required. Try the offline showcases:

```bash
forge demo run --preset js-counter   # clean JS package, certify 100/100
forge demo run --preset js-bad-wire  # the same package with one upward
                                     # import — wire flags it
forge demo run --preset mixed-py-js  # one Python tier + one JS tier
                                     # under the same root
```

Each writes to `./forge-demo-<preset>/` and emits a `DEMO.md` summarising
what `recon`, `wire`, and `certify` saw. No LLM key needed — these run
offline against pre-built source. See
[06-javascript-quickstart.md](06-javascript-quickstart.md) for a full
walk-through with your own JS repo.

## Next

- [02-your-first-package.md](02-your-first-package.md) — building from
  your own intent string.
- [03-the-five-tier-law.md](03-the-five-tier-law.md) — why every file
  has to live in exactly one tier.
- [04-plug-in-llms.md](04-plug-in-llms.md) — switching providers.
- [06-javascript-quickstart.md](06-javascript-quickstart.md) — running
  the polyglot pipeline on your own JS / TS repo.
