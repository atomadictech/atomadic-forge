# FAQ & Troubleshooting

## General questions

### What's the difference between Forge and a code formatter?

**Formatters** (Black, ruff) clean up whitespace and style.

**Forge** reorganizes architecture — moving symbols between tiers, enforcing import discipline, rebuilding structure.

Example:
- Black: `"hello"` → `"hello"` (no change if already formatted)
- Forge: A 500-line god class → splits into a0 (config), a1 (logic), a2 (state), a3 (orchestration)

### Is Forge a code generator?

No. Forge is a **code absorber**. It reorganizes code that already exists.

For **code generation**, use `forge iterate` or `forge evolve` (LLM loops).

### Can Forge handle non-Python languages?

**Yes — as of 0.2, Forge classifies JavaScript and TypeScript with the
same 5-tier law it has always applied to Python.** Walked extensions:
`.py`, `.js`, `.mjs`, `.cjs`, `.jsx`, `.ts`, `.tsx`. `node_modules/`,
`dist/`, `.next/`, `.wrangler/`, and other vendored / build directories
are skipped automatically; no Node install required.

`forge recon` reports per-language counts and a `primary_language`
verdict. `forge wire` detects upward imports in JS specifiers
(`"../a3_og_features/foo"`) the same way it does in Python `from`-imports;
each violation in the JSON report is tagged with `language`. `forge
certify` recognises JS test conventions (`*.test.*`, `*.spec.*`,
`__tests__/`) and JS-style `aN_*/` directories anywhere under the root.

What's still Python-only:
- The runtime-import smoke check (the +25 score component for "package
  actually loads in a fresh subprocess").
- The behavioural pytest gate (the +30 component for "the package's own
  tests pass").

JS/TS-only packages are scored on the +45 polyglot-aware structural
axes (docs / tests-present / tier layout / upward-import discipline)
plus the stub-body penalty. Wiring `npm test` / Vitest into the
behavioural gate is on the 0.3 roadmap. Rust and Go remain on the
roadmap.

Try the showcase presets to see the pipeline against real JS source —
no LLM key needed:

```bash
forge demo run --preset js-counter   # clean JS package, certify 100/100
forge demo run --preset js-bad-wire  # one upward import; wire flags it
forge demo run --preset mixed-py-js  # Python tier + JS tier in one root
```

### What if my repo doesn't have tests or documentation?

Forge handles it. The output will score 0/25 on those checks:

```
  documentation:  0/25 (README.md not found)
  tests:         0/25 (tests/ not found)
```

But it will still absorb the code. The STATUS.md report will list tests and docs as required follow-up.

### Can I absorb multiple repos into one output?

Yes. Use `forge cherry` from repo-a, then `forge cherry` from repo-b, then `--on-conflict rename` to merge them:

```bash
forge cherry ./repo-a --pick all
# .atomadic-forge/cherry.json contains repo-a symbols

forge finalize ./repo-a ./output --apply --on-conflict rename --package merged

forge cherry ./repo-b --pick all
# Overwrites cherry.json with repo-b symbols

forge finalize ./repo-b ./output --apply --on-conflict rename --package merged
# Merges repo-b into the same output tree
```

Result: `output/src/merged/` contains both repos, with name collisions resolved via renaming.

## Installation & setup

### `pip install atomadic-forge` gives permission error

Try:
```bash
pip install --user atomadic-forge
# or
python -m pip install --user atomadic-forge
```

### Command `forge` not found

Install didn't register the CLI. Try:
```bash
python -m atomadic_forge --help
# or
pip install -e .
# (from the Forge repo)
```

### Tests are failing with httpbin errors

This is a known environment issue (httpbin/werkzeug version conflict). It's not Forge's code.

**Solution:**
```bash
pip uninstall pytest-httpbin -y
python -m pytest tests/
# Should pass (192 tests as of 0.2)
```

### DeprecationWarning about `datetime.utcnow()`

Fixed in the latest version. Update:
```bash
pip install --upgrade atomadic-forge
```

## Using forge auto

### Dry-run takes a long time

Dry-run still classifies every symbol and computes tiers. Large repos (5000+ files) can take time.

**Solution:** Use `forge recon` instead for just the analysis, without the full pipeline:
```bash
forge recon ./large-repo
# Faster: just stats, no full materialization
```

### Output has too many symbols I don't want

Use `forge cherry` to pick specific symbols:

```bash
forge cherry ./repo --pick ModuleA --pick ClassB
forge finalize ./repo ./output --apply
```

### Conflict resolution: what does `--on-conflict` do?

When two symbols have the same name (e.g., two `User` classes), Forge handles it:

- `rename` — Rename the second one (default): `User` → `User_1`
- `first` — Keep the first, skip the second
- `last` — Keep the last, overwrite the first
- `fail` — Error if a collision exists

```bash
# Keep only first repo's symbols
forge auto ./repo-a ./output --apply --on-conflict first

# Or rename collisions
forge auto ./repo-a ./output --apply --on-conflict rename
```

## Wire check (import violations)

### My code fails wire check. How do I fix it?

`forge wire` reports upward imports. Example:

```
a1_at_functions/utils.py: a1 ← a2_mo_composites.Store (upward import)
```

**This means:** `a1_at_functions/utils.py` imports from `a2_mo_composites/Store`, which is a tier violation.

**How to fix:**

**Option A:** Move `utils.py` to a higher tier (a2 or a3):

```bash
# Move the file
mv ./output/src/myapp/a1_at_functions/utils.py \
   ./output/src/myapp/a2_mo_composites/utils.py

# Update module docstring
# """Tier a2 — composite utilities"""
```

**Option B:** Extract pure logic into a1, leave stateful parts in a2:

```python
# a1_at_functions/parse_utils_pure.py
def parse_data(raw: str) -> dict:
    # Pure logic, no Store dependency
    return ...

# a2_mo_composites/data_processor.py
from ..a1_at_functions.parse_utils_pure import parse_data
from .Store import Store

def process_with_store(raw: str, store: Store) -> dict:
    parsed = parse_data(raw)  # Use pure helper
    return store.save(parsed)
```

**Option C:** Move the imported symbol to a lower tier:

```bash
# If Store's only job is to be used by a1 functions, 
# move Store from a2 to a1 (if it qualifies as pure)
```

### I'm getting "X violations" but the code works fine

Wire violations are **architectural**, not functional. Code can work fine but still violate the tiers.

Example: A pure function (a1) that imports a stateful class (a2) will *work*, but it violates the law because a1 should never depend on state.

**Why fix it?**
- Predictability: a1 functions are always composable without side effects
- Testability: Pure functions are trivial to test
- Maintainability: Clear boundaries prevent spaghetti code

Fix the violations before shipping.

## Certify scoring

### My code scores 50/100. How do I improve?

```
Certify: myapp
  documentation:       0/25 ← Add README.md
  tests:              25/25 ✓
  tier_layout:        25/25 ✓
  import_discipline:   0/25 ← Fix wire violations
  
  TOTAL: 50/100
```

**To reach 100:**
1. Add README.md and/or docs/ to reach 25/25 on documentation
2. Run `forge wire` and fix all violations to reach 25/25 on import_discipline

**To reach 75 (production-ready):**
- Fix the worst issues (documentation or import_discipline)
- Tests and tier_layout are usually OK after absorption

### Do I need 100/100 to ship?

No. 75+/100 is acceptable for production. But:
- Documentation (25 pts) is easy: add README.md
- Tests (25 pts) are worth doing (your existing tests are absorbed)
- Tier layout (25 pts) is automatic (Forge creates all 5 tiers)
- Import discipline (25 pts) is the hard one (requires manual fixes)

So aim for 75+ before shipping.

## LLM loops

### `forge iterate` generated bad code

Try:
1. Use a better provider (Claude > Gemini > GPT)
2. Be more specific in the intent prompt
3. Run more iterations (--max-iterations 5 instead of 3)
4. Inspect intermediate outputs and fix them manually

### Rate limit errors

```
Error: 429 Too Many Requests
```

**Solution:**
- Use local Ollama (no rate limits): `export FORGE_OLLAMA=1`
- Use stub provider for testing: `--provider stub`
- Wait a bit and retry

### API key not found

```
Error: GEMINI_API_KEY not set
```

**Solution:**
```bash
export GEMINI_API_KEY=your-key-here
# Then try again
```

### Code quality declining over rounds

Forge detects stagnation:

```
Halt reason: stagnation_detected
```

This means the score stopped improving. **Fix manually:**

```bash
# Inspect what's wrong
forge wire ./output/src/myapp
cat ./output/STATUS.md

# Manually fix the issues
# Then run another iteration
```

## Performance & scalability

### forge auto is slow on large repos (10k+ files)

Forge classifies every symbol. On very large codebases, this takes time.

**Workarounds:**
- Use `forge cherry` to pick specific modules, absorb in batches
- Use `--provider stub` to test the pipeline without LLM calls
- Run on a faster machine

### Can I run Forge on a CI/CD pipeline?

Yes. Example GitHub Actions:

```yaml
- name: Absorb and verify
  run: |
    pip install atomadic-forge
    forge auto ./src ./output --apply --package myapp
    forge wire ./output/src/myapp
    forge certify ./output --package myapp
```

Example GitLab CI:

```yaml
absorb:
  script:
    - pip install atomadic-forge
    - forge auto ./src ./output --apply --package myapp
    - forge wire ./output/src/myapp
    - forge certify ./output --package myapp
```

## Advanced questions

### Can I customize the tier classification?

Not yet, but the scout report logs the rationale per symbol. You can override manually by moving files after absorption.

### Can I extend Forge with custom verbs?

Yes (roadmap for 0.2). The output is JSON at each stage (scout, cherry, assimilate, wire, certify). You can write custom tools that pipe this JSON.

Example:

```bash
forge auto ./repo ./output --json | \
  jq '.tier_dist' | \
  custom_analysis_script.py
```

### How is Forge licensed?

Business Source License 1.1 (BSL-1.1):
- **Free for non-production use** (development, testing, learning)
- **Commercial license required for production**
- **Converts to Apache 2.0 on 2030-04-27**

## Getting help

### I found a bug

Open an issue on GitHub: [atomadictech/atomadic-forge/issues](https://github.com/atomadictech/atomadic-forge/issues)

Include:
- What you ran
- What you expected
- What actually happened
- Output of `forge doctor`

### I want to contribute

See [CONTRIBUTING.md](../CONTRIBUTING.md)

### I have a feature request

File an issue on GitHub with the `feature-request` label.

## Further reading

- [Getting started](01-getting-started.md)
- [Command reference](02-commands.md)
- [Tutorial: Absorb a real repo](03-tutorial.md)
- [LLM loops](04-llm-loops.md)
- [Architecture guide](../ARCHITECTURE.md)
