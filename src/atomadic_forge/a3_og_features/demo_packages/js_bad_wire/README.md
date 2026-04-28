# js-bad-wire — Atomadic Forge teaching demo

This package is **structurally identical to `js-counter`** with one
deliberate sin: `a1_at_functions/echo.js` imports `formatGreeting` from
`a3_og_features/feature.js`. That's an upward import (a1 ⟵ a3) and
illegal under the 5-tier law.

`forge wire` should report:

```
Wire scan: …
  verdict:    FAIL
  violations: 1
    - a1_at_functions/echo.js: a1_at_functions ⟵ a3_og_features.../a3_og_features/feature.js
```

The JSON form tags the violation with `language: "javascript"` so
multi-language reports can group by source.

This is the demo to point at when someone asks, *"how does Forge catch
mistakes?"*. Run it, read the output, then look at the comment block in
`a1_at_functions/echo.js` for two ways to fix the violation.
