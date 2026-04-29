# 06 — JavaScript / TypeScript quickstart

The shortest path from "I have a JS repo" to "Forge classified it,
flagged the upward imports, and gave me a score."

## What's polyglot in 0.2

`forge recon`, `forge wire`, and `forge certify` all walk `.py`, `.js`,
`.mjs`, `.cjs`, `.jsx`, `.ts`, and `.tsx` in a single pass. The same
5-tier monadic law (`a0_qk_constants/` / `a1_at_functions/` /
`a2_mo_composites/` / `a3_og_features/` / `a4_sy_orchestration/`)
applies. `node_modules/`, `dist/`, `.next/`, `.wrangler/`, `.turbo/`,
`coverage/`, and other vendored / build directories are skipped
automatically. **No Node install required** — the JS parser is pure
Python.

What stays Python-only:

- The runtime-import smoke check (`python -c "import <pkg>"` in a fresh
  subprocess; +25 score points).
- The behavioural pytest gate (+30 score points).

JS / TS-only packages are scored on the +45 polyglot-aware structural
axes (docs / tests-present / tier layout / upward-import discipline)
plus the stub-body penalty.

## 0. See the polyglot pipeline run offline

Three static showcase presets ship with Forge — they exercise
`recon → wire → certify` on pre-built source you can read after the
fact. **No LLM key needed.**

```bash
forge demo run --preset js-counter   # clean a0..a4 JS package, certify 60/100
forge demo run --preset js-bad-wire  # the same package with one upward
                                     # import; wire flags it
forge demo run --preset mixed-py-js  # one Python tier + one JS tier
                                     # under the same root
```

Each writes to `./forge-demo-<preset>/` with a `DEMO.md` artifact
summarising the scan results.

## 1. Run recon on your own JS / TS repo

```bash
forge recon ./my-cloudflare-worker
```

Expected output (Worker-style repo):

```
Recon: ./my-cloudflare-worker
------------------------------------------------------------
  python files:     0
  javascript files: 4
  typescript files: 1
  primary language: javascript
  symbols:          17
  tier dist:        {'a4_sy_orchestration': 1, 'a2_mo_composites': 1,
                     'a1_at_functions': 2, 'a0_qk_constants': 1}
  effect dist:      {'pure': 9, 'state': 5, 'io': 3}
  recommendations:
    - JS/TS files are not yet split into aN_* tier directories —
      see suggested_tier per file in symbols[].
```

The JSON form (`forge recon ./repo --json`) gives you `suggested_tier`
per file:

```json
{
  "schema_version": "atomadic-forge.scout/v1",
  "language_distribution": {"python": 0, "javascript": 4, "typescript": 1},
  "primary_language": "javascript",
  "symbols": [
    {
      "qualname": "<module>",
      "file": "src/index.js",
      "language": "javascript",
      "suggested_tier": "a4_sy_orchestration",
      "rationale": "default-export object with fetch handler"
    },
    {
      "qualname": "Counter",
      "file": "src/counter.js",
      "language": "javascript",
      "suggested_tier": "a2_mo_composites",
      "rationale": "exported class with instance state"
    }
  ]
}
```

## 2. Reorganise into tier directories

For a JS repo, the tier directories live wherever your source root is
(no `src/<package>/` requirement — JS-style top-level `aN_*/` works
fine). A clean Worker layout looks like:

```
my-cloudflare-worker/
├── package.json
├── README.md
├── a0_qk_constants/
│   └── messages.js          # const messages = {...}; export const ...
├── a1_at_functions/
│   ├── format_count.js      # pure functions
│   └── parse_request.js
├── a2_mo_composites/
│   └── counter.js           # class Counter { ... }
├── a3_og_features/
│   └── counter_feature.js   # composes a1 + a2
├── a4_sy_orchestration/
│   └── index.js             # export default { fetch, scheduled }
└── tests/
    └── counter.test.js
```

You can move files manually, or run `forge auto` to generate this
shape from a flat-layout repo. (`forge auto` for JS is still
language-shape-aware — file copies, no transpilation.)

## 3. Wire-scan it

```bash
forge wire ./my-cloudflare-worker
```

If everything's legal:

```
Wire scan: ./my-cloudflare-worker
  verdict:    PASS
  violations: 0
```

If `a1_at_functions/format_count.js` accidentally imports from
`a3_og_features/counter_feature.js`, the scan returns:

```
Wire scan: ./my-cloudflare-worker
  verdict:    FAIL
  violations: 1
    - a1_at_functions/format_count.js: a1_at_functions ⟵ a3_og_features.../a3_og_features/counter_feature.js
```

The JSON form is explicit about the language:

```json
{
  "violations": [
    {
      "file": "a1_at_functions/format_count.js",
      "from_tier": "a1_at_functions",
      "to_tier": "a3_og_features",
      "imported": "../a3_og_features/counter_feature.js",
      "language": "javascript"
    }
  ],
  "verdict": "FAIL"
}
```

## 4. Certify it

```bash
forge certify ./my-cloudflare-worker
```

Expected (clean JS-only package):

```
Certify: ./my-cloudflare-worker
  score: 60/100
  docs:  PASS
  tests: PASS
  layout:PASS
  wire:  PASS
```

JS-specific behaviours of `certify`:

- `tests` PASS recognises `tests/*.test.{js,mjs,jsx,cjs,ts,tsx}`,
  `*.spec.*`, and the Jest `__tests__/` directory convention.
- `tier_layout` PASS counts JS-style top-level or nested `aN_*/`
  directories anywhere under the repo root.

Without a `--package` argument (i.e. JS-only repo), the runtime
importability check is vacuously credited — you're scored on the
polyglot structural axes plus the +25 runtime axis. The +30
behavioural axis (currently wired only to pytest) is the honest gap;
that's why a fully clean JS-only package tops out at 60/100. Wiring
`npm test` / Vitest into the behavioural gate is on the 0.3 roadmap.

To hit 100/100 today, mix in Python tests that exercise the JS
behaviour through a thin Python wrapper, or wait for 0.3.

## 5. Mixed Python + JS in one repo

If you have a Python back-end and a Worker front-end living together,
Forge handles them with the same verbs:

```bash
forge recon .
# python files: 12, javascript files: 5,
# primary_language: python, …

forge wire ./src/my_python_pkg     # scans the Python package
forge wire ./web                    # scans the JS package

# Or run certify across the whole root:
forge certify .
```

The `mixed-py-js` showcase preset is a one-command end-to-end demo of
this layout:

```bash
forge demo run --preset mixed-py-js
```

## Common pitfalls

- **JS file outside any tier directory.** `recon` will assign a
  `suggested_tier` based on surface signals; move the file under the
  matching `aN_*/` directory to make the verdict stable.
- **Upward import via relative path.** `import x from
  '../a3_og_features/foo.js'` is an upward import if the source file
  lives at `a1_at_functions/...`. Move the consumer up, or move the
  imported symbol down.
- **TypeScript path-aliases.** Forge reads the literal specifier; if
  you use `@/foo` aliases, pair the alias with explicit `aN_*/`
  segments somewhere in the path so the wire scanner can see the tier.

## Read further

- [01-quickstart.md](01-quickstart.md) — the LLM-driven Python
  flagship demo.
- [03-the-five-tier-law.md](03-the-five-tier-law.md) — why the law
  applies the same way across languages.
- [05-multi-repo-absorb.md](05-multi-repo-absorb.md) — applying the
  same flow to flat-layout JS/TS repos.
