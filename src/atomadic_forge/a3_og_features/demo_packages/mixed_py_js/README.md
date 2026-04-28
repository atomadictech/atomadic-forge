# mixed-py-js — Atomadic Forge polyglot showcase

A repository with a Python package on one side and a JavaScript Worker
on the other, both governed by the same 5-tier monadic law.

```
mixed-py-js/
├── pyproject.toml
├── README.md
├── src/
│   └── mixed_pkg/
│       ├── __init__.py
│       ├── a0_qk_constants/        # Python tier a0
│       └── a1_at_functions/        # Python tier a1 (pure)
├── web/
│   ├── a1_at_functions/format_status.js   # JS tier a1
│   └── a4_sy_orchestration/server.js      # JS tier a4 (Worker)
└── tests/
    ├── conftest.py
    ├── test_mixed.py             # Python tests (pytest)
    └── status.test.js            # JS test (recognised by certify)
```

`forge recon .` reports per-language counts (Python + JavaScript) and
calls out which `aN_*` directories were detected. `forge wire` runs the
upward-import scan over both languages in one pass; each violation in
the JSON form is tagged with `language: "python" | "javascript"`.
`forge certify` counts the JS test file alongside the Python tests and
recognises both the `src/mixed_pkg/aN_*/` (Python convention) and
top-level `web/aN_*/` (JS convention) tier directories.
