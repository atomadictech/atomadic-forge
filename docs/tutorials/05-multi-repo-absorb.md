# 05 — Multi-repo absorb

Forge's other lane: take an existing flat-layout Python *or JavaScript /
TypeScript* repository and materialise it into a clean, tier-organised,
certifiable package. The CLI verbs are identical across languages —
`recon`, `cherry`, `finalize`, `wire`, `certify` all walk `.py`, `.js`,
`.mjs`, `.cjs`, `.jsx`, `.ts`, and `.tsx` in a single pass.

## When you'd do this

- You inherited a 50k-line legacy repo with no architecture.
- A teammate wrote a feature in their own repo and you want it absorbed
  into your codebase without copy-paste chaos.
- You're modernising — tier-organise as the precondition for any
  meaningful refactoring.

## The flow

```
your messy repo
      │
      ▼
[forge recon]  ← classify every public symbol; write scout.json
      │
      ▼
[forge cherry] ← pick which symbols to absorb (or --pick all)
      │
      ▼
[forge finalize <repo> <out>] ← materialise tier-organised output
      │
      ▼
out/
├── pyproject.toml          # ready to pip install -e
├── README.md               # auto-generated
├── src/<package>/          # 5-tier layout, fully wired
│   ├── a0_qk_constants/
│   ├── a1_at_functions/
│   ├── a2_mo_composites/
│   ├── a3_og_features/
│   └── a4_sy_orchestration/
├── tests/                  # conftest scaffolded
└── STATUS.md               # honest "what's still required before shipping"
```

## One-shot

```bash
forge auto ./legacy-repo ./out --package modern --apply
```

`forge auto` runs the whole chain. Add `--apply` only when you're ready
to write files (default is dry-run).

## Step-by-step (more control)

### 1. Recon

```bash
forge recon ./legacy-repo
```

Output:

```
Recon: ./legacy-repo
  python files: 87
  symbols:      342
  tier dist:    {'a0_qk_constants': 4, 'a1_at_functions': 198,
                  'a2_mo_composites': 71, 'a3_og_features': 20,
                  'a4_sy_orchestration': 49}
  effect dist:  {'pure': 215, 'state': 12, 'io': 87}
  recommendations:
    - High I/O ratio — consider pushing I/O to a4 boundaries.
    - No pure (a1) functions detected in module X — extract pure helpers.
```

`.atomadic-forge/scout.json` now contains the full classification.

### 2. Cherry-pick (review first)

```bash
forge cherry ./legacy-repo --pick all
```

Or pick specific symbols:

```bash
forge cherry ./legacy-repo --pick UserStore --pick authenticate --pick parse_email
```

This writes `.atomadic-forge/cherry.json` with the items you've selected
and Forge's confidence scores per item.

### 3. Finalize (with conflict resolution)

When two repos define the same symbol (e.g. both have `class User`),
Forge needs a strategy:

```bash
forge finalize ./legacy-repo ./out --apply --on-conflict rename
# rename:    keeps both, suffixes "__alt"
# first:     keep first-seen
# last:      keep last-seen, overwrite
# fail:      abort the run
```

For a single-repo absorption this rarely fires. For multi-repo merges
(combining ./repo-a and ./repo-b) it's the most important flag.

### 4. Verify

```bash
forge wire ./out/src/modern         # zero violations expected
forge certify ./out --package modern # honest 0–100 score
pip install -e ./out                 # actually install it
pytest ./out/tests/                  # run the absorbed tests
```

### 5. Read STATUS.md

Every `--apply` writes `STATUS.md` listing what's still required:

```
# Atomadic Forge — Assimilation Status

This directory was produced by `forge auto`.  It is **bootstrapped
material**, not a finished product.

What's here:
- 5-tier monadic layout (a0_qk_constants/ … a4_sy_orchestration/)
- Symbols ingested from 1 source repo(s)
- 271 components emitted

What's still required before shipping:
1. Integration tests against real inputs.
2. Runtime configuration — secrets, env vars, DB URLs.
3. Observability — logging, metrics, error reporting.
4. Wire enforcement — run `forge wire` and address any violations.
5. Certification — `forge certify` should hit ≥ 75 before public use.
```

This is honest; treat it as the to-do list, not as evidence of failure.

## What absorption does NOT do

- **Semantic merge.** Two `User` classes with different shapes won't be
  unified into one — they'll be renamed (or fail/first/last per
  `--on-conflict`).
- **Test generation.** Forge keeps existing tests; it doesn't write new
  ones for absorbed symbols.
- **Behavior verification.** The absorbed code probably runs, but its
  semantic correctness is your responsibility.

For LLM-driven generation (where Forge writes new code from intent), see
[02-your-first-package.md](02-your-first-package.md).
