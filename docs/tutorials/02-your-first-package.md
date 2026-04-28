# 02 — Your first package

Going beyond presets: write your own intent string and watch Forge
produce a real package from it.

## The shape of a good intent

Forge prompts work best when your intent is **specific about**:

1. **The package name.** Forge respects the name you pass via `--package`.
2. **Tier placement.** "a1 pure functions … / a2 stateful class … / a4 cli."
3. **Concrete test assertions.** "tests/test_x.py with `assert foo('a')=='A'`."
4. **Absolute imports rooted at the package name** (Forge enforces this).

A weak intent: _"build a TODO list"_ — too open-ended; the LLM picks an
arbitrary architecture.

A strong intent:

> Build a tiny TODO list. Required: a0 TypedDict TodoItem(id:int, title:str,
> done:bool). a1 pure functions add_item(items:list, title:str)->list,
> mark_done(items:list, id:int)->list, list_pending(items:list)->list.
> a2 class TodoStore with self.items:list and add/done/list methods that
> delegate to the a1 helpers. a4 cli with argparse subcommands add/done/list.
> tests/test_todo.py with assert mark_done([{'id':1,'title':'a','done':False}],1)
> [0]['done']==True. Use absolute imports rooted at 'todo'.

## Run it

```bash
export GEMINI_API_KEY=$(your-key)
forge evolve run "<the intent above>" ./out \
    --package todo --auto 5 --provider gemini
```

You'll see something like:

```
Round │ Iters │ Files │ Symbols (Δ)    │ Score (Δ)      │ Wire │ Conv
──────┼───────┼───────┼────────────────┼────────────────┼──────┼──────
   0  │   1   │  10   │   5 (+5)       │ 90 (+90.0)     │ PASS │  Y
```

Convergence on Round 0 means the LLM nailed it first try. If it doesn't
converge:

- Round 0 score 60–80: structural good, behavior partial → next round
  the LLM gets test-failure feedback and writes real implementations.
- Round N stagnating at 60: the LLM hit a complexity ceiling for this
  task. Switch to a stronger provider (`--provider anthropic`).

## Inspect the output

```bash
ls ./out
# pyproject.toml  README.md  src/  tests/  .atomadic-forge/

cat ./out/README.md            # auto-generated showcase README
cat ./out/.atomadic-forge/EVOLVE_LOG.md
ls ./out/.atomadic-forge/transcripts/  # full LLM dialogue, every byte
```

The `transcripts/` folder contains every prompt Forge sent and every
response it got. **No black-box magic — you can audit every byte.**

## Iterate

If you want to refine the package, just re-run `forge evolve` against the
same output dir:

```bash
forge evolve run "<add this feature>" ./out --package todo --auto 3 \
    --provider gemini --seed ./out/src/todo
```

The `--seed` flag tells Forge to use the existing package as the catalog.
The LLM sees what's already there (via the `reuse` signal) and is pushed
to compose rather than re-emit.

## Common pitfalls

- **The LLM emits to a different package name than `--package`.** This is
  the wrong-package gameability hole. Forge 0.1.x mostly gates against it
  via the test-import filter; if you see the score climb while the
  requested package is empty, that's your signal.

- **Score plateaus at 60.** Tests are failing, behavior is broken. Open
  the transcript log for the most recent round and read the test-failure
  excerpts Forge fed to the LLM — they tell you exactly what assertion
  the LLM couldn't satisfy.

- **The LLM emits prose instead of JSON.** Forge has one auto-retry for
  this; if it persists across rounds, your intent is too long or the
  model is too small. Trim the intent or upgrade providers.
