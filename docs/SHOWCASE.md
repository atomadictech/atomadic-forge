<p align="center">
  <img src="../assets/Atomadic-Forge-01.png" alt="Atomadic Forge" width="640"/>
</p>

# Atomadic Forge — Showcase

_Live `forge demo` and `forge evolve` runs against Gemini 2.5 Flash on
free tier and codellama:7b-instruct on Ollama. Same loop, same constraint
substrate, swap the LLM, watch the trajectory carry harder tasks higher.
**As of 0.2, the same constraint substrate also classifies JavaScript and
TypeScript** — the polyglot showcases at the bottom of this page run
without an LLM key._

## LLM-driven Python presets

| Preset | Headline | Trajectory | Final | Duration | Wire | Tests |
|--------|----------|------------|-------|---------:|------|-------|
| `calc` | 4 pure arithmetic functions + CLI + tests | `90 → 90 → 90` | **90/100** | 29.7s | PASS | PASS |
| `kv`   | In-memory KvStore (`put/get/delete/keys`) + CLI + tests | `90 → 90` | **90/100** | 71.8s | PASS | PASS |
| `slug` | URL slugifier with concrete behavioural assertions | `86 → 90` | **90/100** | 21.5s | PASS | PASS |

Run any of them yourself:

```bash
export GEMINI_API_KEY=your-key                      # free tier OK
forge demo run --preset calc --provider gemini
forge demo run --preset kv   --provider gemini
forge demo run --preset slug --provider gemini
```

## Polyglot static showcases (no LLM key required)

| Preset | What it shows | Wire | Tests | Certify |
|--------|---------------|------|-------|---------|
| `js-counter` | A clean `a0..a4` JavaScript package — Worker-style `index.js` (a4) on top of a `Counter` class (a2), pure helpers (a1), and a constants module (a0) | PASS | PASS | **60/100** (max for a JS-only package today) |
| `js-bad-wire` | The same package shape with one deliberate sin: `a1_at_functions/echo.js` imports from `a3_og_features/counter_feature.js`. Wire surfaces the violation with `language: "javascript"`. | FAIL (1) | PASS | 50/100 |
| `mixed-py-js` | Python `a1_at_functions/util.py` plus a JS `a4_sy_orchestration/server.js` under the same root — proof that one layout works for both languages. | PASS | PASS | 60+/100 |

```bash
forge demo run --preset js-counter
forge demo run --preset js-bad-wire
forge demo run --preset mixed-py-js
```

These run offline — no API key, no Ollama, no network. They demonstrate
the `recon → wire → certify` pipeline on pre-built source the way a
reviewer would expect to see it.

**Why 60/100 is the JS ceiling today (and not a bug):** the certify
score has six axes — docs / tests-present / tier-layout /
upward-import-discipline / runtime-importability / behavioural
test-pass-ratio. The first four are polyglot-aware as of 0.2 (worth
+45 points). The +25 runtime importability check (`python -c "import
<pkg>"` in a fresh subprocess) credits a JS-only package vacuously
because there's no `--package` to import — net +25. The +30
behavioural axis, however, is wired only to pytest. Wiring `npm test`
/ Vitest into the behavioural gate is on the 0.3 roadmap. Until then,
60/100 with `wire: PASS` and `tests: PASS` is the honest ceiling for a
JS-only package — and we're not going to fake the missing 30 points.

---

## What Gemini actually wrote

### `calc/a1_at_functions/divide.py`

```python
"""Tier a1 — pure division."""

def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a / b
```

### `kv/a2_mo_composites/kv_store.py`

```python
"""Tier a2 — In-memory Key-Value store."""

from typing import Any, List, Optional


class KvStore:
    """A simple in-memory key-value store."""

    def __init__(self) -> None:
        self.data: dict[str, Any] = {}

    def put(self, key: str, value: Any) -> None:
        self.data[key] = value

    def get(self, key: str) -> Optional[Any]:
        return self.data.get(key)

    def delete(self, key: str) -> None:
        self.data.pop(key, None)

    def keys(self) -> List[str]:
        ...
```

### `slug/a1_at_functions/slugify.py`

```python
"""Tier a1 — pure string slugification."""
import re

def slugify(text: str) -> str:
    """Converts a string into a URL-friendly slug.

    - Lowercases the text.
    - Replaces spaces and punctuation with single dashes.
    - Strips leading/trailing dashes.
    """
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    return text
```

---

## Real CLI invocations (live)

```bash
$ python -m kv.a4_sy_orchestration.cli put hello world
Stored: hello = world

$ python -m calc.a4_sy_orchestration.cli 7 + 6
13      # (calc CLI takes 'a OP b' as Gemini correctly interpreted the prompt)

$ python -m slug.a4_sy_orchestration.cli "Hello, World!"
hello-world
```

---

## Why this matters

These three runs landed in the score range that *previously was unreachable*
without being gamed. Five refine cycles ago, the same loop with the same
prompts produced `def parse(x): return x` and certify said 100/100.

The breakthrough that closed the gameability ceiling:

1. **Wire scan** — every emitted file lives in the legal tier.
2. **Import smoke** — the package actually loads (catches syntax/import errors).
3. **Behavioral pytest run** — the LLM's own tests must actually pass.
4. **Stub detector** — `pass`, `NotImplementedError`, `# TODO` markers deduct.

When all three positive signals + zero stub penalty fire, you reach the
score plateau (90 here, would be 100 if the run included its own README/docs
and a richer test count). Gemini hit that plateau on every preset, on the
first or second round, in under 75 seconds each.

## What this proves

- **Forge is the architectural backbone**, the LLM is the engine.
- The substrate is **adversarial to bullshit**: stubs don't pass, identity
  functions don't pass, broken imports don't pass.
- The same loop carries any pluggable LLM (`--provider gemini|anthropic|
  openai|ollama|stub`).
- A free 7B local model (`codellama:7b-instruct`) reaches honest 60-90 on
  these tasks; Gemini 2.5 Flash on free tier reaches 90+ across the board.
- The substrate doesn't change. The LLM changes. The trajectory speaks.

## Reproducibility

All three demos are baked into Forge as presets:

```bash
forge demo list
forge demo run --preset calc
forge demo run --preset kv
forge demo run --preset slug
```

Each preset writes a per-run `DEMO.md` artifact alongside the generated
package, plus the manifest at `.atomadic-forge/demo.json`.

---

## Bonus run: the redemption + the gap it exposed

The same markdown-converter intent that codellama:7b plateaued on
(score `60 → 60 → 60 → 60 → 60`, identity-function stubs that gamed
every check) was rerun against Gemini 2.5 Flash:

| LLM | Same intent | Trajectory | Time | Verdict |
|-----|-------------|-----------|-----:|---------|
| codellama:7b-instruct | mdconv | `60 → 60 → 60 → 60 → 60` (5 rounds) | ~3 min | Stuck — model can't write a real parser |
| gemini-2.5-flash | mdconv | `90` (1 round, converged) | ~30s | Score 90/100, real implementations |

**Redemption confirmed.** Same Forge, same intent, swap the model,
watch the trajectory carry the harder task higher.

### …And a real gap surfaced in the same run

Gemini emitted code into a *different package name* (`forge_greeter`,
a greeting utility — apparently the LLM thought it was a more elegant
solution!) instead of the requested `mdconv`. Score still hit 90 because
Forge's behavioral check counted tests for the wrong package as
satisfying the request.

**This is the kind of gap Forge needs to find — and did.** The fix was
shipped in the same session: the test runner now refuses to credit
behavioral score against tests that don't import the requested package.
This is exactly the ratchet pattern: every refine cycle exposes a new
gameability hole, the ratchet tightens, the score gets harder to fake.

```python
# atomadic_forge/a1_at_functions/test_runner.py
def _filter_tests_to_package(tests_dir: Path, package: str) -> list[str]:
    """Return list of test file paths whose imports reference `package`.

    Closes the wrong-package gameability hole: an LLM that emits files
    into `forge_greeter` but tests for `forge_greeter` shouldn't credit
    the behavioural score against a request for `mdconv`.
    """
```

## Why this matters

These trajectories are the receipts behind the
[architecture-substrate hypothesis](LANDSCAPE.md):

- **Free 7B local model** (`codellama:7b-instruct`) → honest 60–90 score
  across task complexity. Plateaus where model capability ends.
- **Free cloud Gemini** (`gemini-2.5-flash`) → 90+ across all preset tasks,
  closes the gap codellama couldn't.
- **Same Forge, swap the LLM** — the substrate is the constant. The
  generator is the variable. The trajectory tells you which one is
  bottlenecking.

That's the whole pitch. Every line of it is a thing you can re-run in
under 2 minutes with `forge demo run`.

---

_Generated by Atomadic Forge 0.1.0._
