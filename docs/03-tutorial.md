# Tutorial: Absorb a Real Repository

> **Looking for the canonical first-10-minutes path?** See [FIRST_10_MINUTES.md](FIRST_10_MINUTES.md). This document covers a deeper specific topic.

In this tutorial, we'll absorb a small real Python repository into monadic structure, fix the violations, and certify the result.

## Setup

**Prerequisites:**
- Forge installed: `pip install atomadic-forge`
- A Python repository to absorb (we'll use a small example)

**Time:** ~20 minutes

## Step 1: Clone a test repository

For this tutorial, let's use a small, real repo. Clone a simple Python project:

```bash
# Example: a small but real repo
git clone https://github.com/requests/requests ./test-repo
cd test-repo

# Or use any other Python repo you'd like to modernize
```

For this walkthrough, I'll use a small CLI tool as an example (any ~50-file Python repo works).

## Step 2: Analyze the repository (recon)

Before absorbing, let's see what we're dealing with:

```bash
cd /path/to/workspace
forge recon ./test-repo
```

**Expected output:**

```
Recon: ./test-repo
--------------------------------------------
  python files: 45
  symbols:      312
  tier dist:    {'a2_mo_composites': 89, 'a0_qk_constants': 18, 'a3_og_features': 62, 'a1_at_functions': 125, 'a4_sy_orchestration': 18}
  effect dist:  {'pure': 280, 'state': 22, 'io': 10}
```

**What this tells us:**
- 45 Python files with 312 public symbols
- Heavy a1 (functions) — good sign
- Some a2 (stateful classes) — expected for libraries
- Some a4 (CLI/orchestration) — expected for CLI tools
- Mostly pure functions — clean codebase

## Step 3: Dry-run the absorption (auto without --apply)

Now let's see what Forge would do without actually writing files:

```bash
forge auto ./test-repo ./output
```

**Expected output:**

```
Atomadic Forge — auto pipeline (DRY-RUN)
--------------------------------------------
  source:        ./test-repo
  destination:   ./output/absorbed
  symbols:       312
  cherry-picked: 312
  components:    312
  tier_dist:     {'a2_mo_composites': 89, 'a0_qk_constants': 18, 'a3_og_features': 62, 'a1_at_functions': 125, 'a4_sy_orchestration': 18}
  wire verdict:  DRY_RUN
  certify score: 0/100

  (re-run with --apply to write the materialized tree)
```

**What happened:**
- Forge walked the repo
- Classified 312 symbols into tiers
- Would materialize them into 5 tier directories
- Dry-run means nothing was written (yet)

## Step 4: Actually materialize (auto with --apply)

Now let's commit to the absorption:

```bash
forge auto ./test-repo ./output --apply --package test_project
```

This writes actual files. Let's see what was created:

```bash
ls -la ./output/src/test_project/
```

**Expected output:**

```
total 80
drwxr-xr-x  1 user  staff   256 Apr 27 12:34 .
drwxr-xr-x  1 user  staff   256 Apr 27 12:34 ..
-rw-r--r--  1 user  staff    83 Apr 27 12:34 __init__.py
drwxr-xr-x  1 user  staff   320 Apr 27 12:34 a0_qk_constants
drwxr-xr-x  1 user  staff   320 Apr 27 12:34 a1_at_functions
drwxr-xr-x  1 user  staff   320 Apr 27 12:34 a2_mo_composites
drwxr-xr-x  1 user  staff   320 Apr 27 12:34 a3_og_features
drwxr-xr-x  1 user  staff   320 Apr 27 12:34 a4_sy_orchestration
```

## Step 5: Inspect the materialized structure

Let's see what's in each tier:

```bash
# Constants and enums
ls ./output/src/test_project/a0_qk_constants/
# Example: session_types.py, config_constants.py, error_codes.py

# Pure functions
ls ./output/src/test_project/a1_at_functions/ | head -10
# Example: parse_url_helpers.py, validate_headers.py, format_response.py

# Stateful classes
ls ./output/src/test_project/a2_mo_composites/ | head -10
# Example: session_client.py, connection_pool_core.py, auth_handler.py

# Features combining composites
ls ./output/src/test_project/a3_og_features/ | head -10
# Example: http_request_flow.py, redirect_handling_feature.py, retry_logic.py

# CLI and orchestration
ls ./output/src/test_project/a4_sy_orchestration/
# Example: cli.py, main.py
```

## Step 6: Check the status report

Forge created a status report telling us what still needs work:

```bash
cat ./output/STATUS.md
```

**Expected output:**

```
# Atomadic Forge — Assimilation Status

This directory was produced by `forge auto` / `forge finalize`.
It is **bootstrapped material**, not a finished product.

## What's here
- 5-tier monadic layout (a0_qk_constants/ … a4_sy_orchestration/)
- Symbols ingested from 1 source repo(s)
- 312 components emitted
- Digest: 3f7a4c2e1d9b5a8c

## What's still required before shipping
1. **Integration tests** against real inputs
2. **Runtime configuration** — secrets, env vars, DB URLs
3. **Observability** — logging, metrics, error reporting
4. **Wire enforcement** — run `forge wire` and address violations
5. **Certification** — `forge certify` should hit ≥75 before public use
```

## Step 7: Wire check (detect import violations)

Now let's scan for upward-import violations:

```bash
forge wire ./output/src/test_project
```

**Likely output:**

```
Wire scan: ./output/src/test_project
  verdict:    FAIL
  violations: 8
    - a1_at_functions/parse_utils.py: a1 ← a2_mo_composites.Session (upward import)
    - a0_qk_constants/error_codes.py: a0 ← a1_at_functions.validate_code
    - a3_og_features/retry_flow.py: a3 ← a4_sy_orchestration.cli_logger
    ... (more violations)
```

**What this means:**
- 8 symbols were classified into tiers such that they have upward imports
- These are **indicators that the tier classification is heuristic** — some hand-tuning may be needed

## Step 8: Inspect and fix violations

Let's look at the first violation:

```bash
head -20 ./output/src/test_project/a1_at_functions/parse_utils.py
```

**Example:**

```python
"""Tier a1 — pure URL parsing utilities."""

from ..a2_mo_composites.Session import Session  # ← VIOLATION: a1 importing a2

def parse_with_session(url: str, session: Session) -> dict:
    """..."""
    # Uses session object
    return session.extract(url)
```

**How to fix:**

Option A: Move `parse_with_session` to a3 (it's a feature, not a pure function):

```bash
# Move the file to a3_og_features
mv ./output/src/test_project/a1_at_functions/parse_utils.py \
   ./output/src/test_project/a3_og_features/parse_workflow.py

# Update the module docstring
# Tier a3 — parse workflow combining Session and pure helpers
```

Option B: Extract the pure part into a1, leave the stateful part in a3:

```python
# a1_at_functions/url_parser_pure.py (pure)
def parse_url(url: str) -> dict:
    # No dependencies on a2+
    return ...

# a3_og_features/url_parsing_service.py (feature)
from ..a2_mo_composites.Session import Session
from ..a1_at_functions.url_parser_pure import parse_url

def parse_with_session(url: str, session: Session) -> dict:
    parsed = parse_url(url)  # Use pure helper
    return session.extract_from(parsed)
```

**Repeat for all violations.** Once fixed:

```bash
forge wire ./output/src/test_project
# Should now return: verdict: PASS (0 violations)
```

## Step 9: Certify

Score the materialized structure:

```bash
forge certify ./output --package test_project
```

**Example output:**

```
Certify: test_project
  documentation:       25/25 ✓ (README.md + docs/ present)
  tests:               25/25 ✓ (tests/ directory present)
  tier_layout:         25/25 ✓ (all 5 tiers used)
  import_discipline:   0/25 ✗ (8 upward-import violations from wire)
  
  TOTAL: 75/100
```

**After fixing violations:**

```bash
forge certify ./output --package test_project
# Expected: 100/100 if README + tests + all tiers used + wire clean
```

## Step 10: Review the provenance trail

Inspect what Forge recorded:

```bash
cat ./output/.atomadic-forge/lineage.jsonl
```

**Example:**

```json
{"ts_utc": "2026-04-27T12:34:56Z", "artifact": "scout", "path": ".atomadic-forge/scout.json"}
{"ts_utc": "2026-04-27T12:34:56Z", "artifact": "cherry", "path": ".atomadic-forge/cherry.json"}
{"ts_utc": "2026-04-27T12:34:57Z", "artifact": "assimilate", "path": ".atomadic-forge/assimilate.json"}
{"ts_utc": "2026-04-27T12:34:58Z", "artifact": "wire", "path": ".atomadic-forge/wire.json"}
{"ts_utc": "2026-04-27T12:34:58Z", "artifact": "certify", "path": ".atomadic-forge/certify.json"}
```

This is your audit trail.

## Summary

You've successfully:
1. ✓ Analyzed a repo with `recon`
2. ✓ Dry-run the absorption with `auto`
3. ✓ Materialized with `--apply`
4. ✓ Detected violations with `wire`
5. ✓ Fixed the violations (by hand)
6. ✓ Scored the result with `certify`
7. ✓ Reviewed the provenance trail

The output is now:
- A clean, tier-organized codebase
- All upward imports fixed
- Full provenance (who did what, when)
- A conformance certificate (75–100/100)

## Next steps

- Integrate real tests (Forge absorbed the test files into tier directories too)
- Add missing observability (logging, metrics)
- Deploy the absorbed codebase
- Use `forge emergent` to discover hidden composition chains
- Use `forge synergy` to auto-generate adapters between features

For more, see:
- [Command Reference](02-commands.md)
- [LLM Loops](04-llm-loops.md)
- [FAQ](05-faq.md)
