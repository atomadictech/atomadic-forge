# js-counter — Atomadic Forge showcase

A small JavaScript package laid out under the 5-tier monadic law.

```
js-counter/
├── a0_qk_constants/messages.js          # constants, no logic
├── a1_at_functions/format_count.js      # pure formatter helpers
├── a2_mo_composites/counter.js          # class Counter { value, … }
├── a3_og_features/counter_feature.js    # composes a1 + a2
├── a4_sy_orchestration/index.js         # Worker default { fetch, scheduled }
└── tests/counter.test.js                # exercised by forge certify
```

`forge recon`, `forge wire`, and `forge certify` all walk this tree
without any Node install. The wire scan is PASS; certify scores
60/100 — the honest ceiling for a JS-only package today, with the
+30 behavioural pytest axis still Python-only (wiring `npm test` is
on the 0.3 roadmap).
