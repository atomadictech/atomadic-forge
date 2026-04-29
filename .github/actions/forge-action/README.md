# forge-action

[![Atomadic Forge](https://img.shields.io/badge/atomadic-forge-purple)](https://github.com/atomadictech/atomadic-forge)

A GitHub Action that runs **`forge wire` + `forge certify`** on a
tier-organized package and posts a **sticky PR comment** with the
rendered Receipt card. Composite action — no Docker, no extra runtime.

This is the Lane C W1 deliverable from the Atomadic Forge Golden Path.
Eventually moves to its own repo (`atomadictech/forge-action`); today
it ships in-tree under `.github/actions/forge-action/` so the action's
ref tracks the Forge release that emitted it.

---

## One-line install

In a consuming repo, add `.github/workflows/forge.yml`:

```yaml
name: Atomadic Forge — architecture gate
on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read
  pull-requests: write   # required to post the sticky comment

jobs:
  forge:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: atomadictech/atomadic-forge/.github/actions/forge-action@main
        with:
          package_root: src/your_package
          package_name: your_package
          fail_under: '75'
```

That's it. The action will:

1. Install Forge from the same ref the action checked out at.
2. Run `forge wire <package_root> --fail-on-violations --json` —
   exits 1 on any upward-import violation.
3. Run `forge certify . --fail-under <N> --emit-receipt
   .atomadic-forge/receipt.json --print-card --json` — exits 1 below
   the threshold.
4. Upload `wire.json`, `certify.json`, `receipt.json`, and the
   rendered card as a 14-day build artifact.
5. Post (or update) a single sticky PR comment with the rendered card
   and a one-line verdict summary.

---

## Inputs

| Name | Required | Default | Notes |
|---|---|---|---|
| `package_root` | yes | – | Tier-organized package path (e.g. `src/your_package`) |
| `project_root` | no | `.` | Project root passed to `forge certify` |
| `package_name` | no | `''` | Forwarded to `forge certify --package` |
| `fail_under` | no | `'75'` | Certify threshold; below this, the job fails |
| `receipt_path` | no | `.atomadic-forge/receipt.json` | Receipt JSON emit path (relative to `project_root`) |
| `python_version` | no | `'3.11'` | Python for the Forge install |
| `forge_ref` | no | (action ref) | Override which `atomadic-forge` ref to install |
| `comment_on_pr` | no | `'true'` | Set to `'false'` to skip the sticky comment |
| `upload_artifacts` | no | `'true'` | Set to `'false'` to skip the artifact upload |

## Outputs

| Name | Type | Notes |
|---|---|---|
| `certify_score` | string | The certify score (0–100) as text |
| `wire_verdict` | string | `PASS` or `FAIL` |
| `receipt_path` | string | Echoes back the input `receipt_path` |

---

## Soft-fail discipline

- **Wire and certify gates fail the job by themselves.** The
  `--fail-on-violations` and `--fail-under` flags are native (shipped
  in 0.2.x); no `python -c` workarounds.
- **The PR comment is best-effort.** When the workflow runs from a
  fork or without `pull-requests: write`, the comment step is skipped
  and the job still reports its real verdict via exit code.
- **The Receipt is signable.** When `AAAA_NEXUS_API_KEY` is available
  in the environment and the consuming workflow re-invokes `forge
  certify --sign`, the Receipt's `signatures.aaaa_nexus` field is
  populated. `forge-action` does not call `--sign` by default — most
  CI runs are unsigned dev attestations.

---

## What the sticky comment looks like

```
### Atomadic Forge — wire + certify

**wire:** `PASS` · **certify:** `100.0/100`

╔══════════════════════════════════════════════════════════╗
│ Atomadic Forge Receipt         atomadic-forge.receipt/v1 │
│ ✓ PASS                                       forge 0.2.2 │
│ atomadic-forge                                           │
│ CERTIFY                                      100.0 / 100 │
│   docs ✓  tests ✓  layout ✓  wire ✓                      │
│ WIRE                                PASS  (0 violations) │
│ SCOUT  952 symbols  (python)             952 tier-placed │
╚══════════════════════════════════════════════════════════╝

Posted by forge-action. The card and JSON receipt are also uploaded
as build artifacts on this run.
```

Updated in place on every push — never spams the PR.

---

## Status

- **Today (Lane C W1):** in-tree under `.github/actions/forge-action/`,
  ref-pinned to the consuming Forge release.
- **Lane C W12 (planned):** dedicated repo `atomadictech/forge-action`
  + Marketplace listing.
- **Lane C W16+ (planned):** GitHub App variant that opens weekly
  drift-PRs via `forge iterate --dry-run`.
