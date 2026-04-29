# CI/CD integration

Copy-paste-ready integrations for running Forge gates in CI.

> **Roadmap note.** A native `--fail-below-score` flag is **Lane G1**
> future work. Today, you read the JSON output and exit non-zero
> yourself; the recipes below show exactly that. A signed-certificate
> output is **Lane G5** future work, and a published
> `atomadictech/forge-action` GitHub Action is **Lane G2** future work.
> Until those land, the patterns below are the canonical CI integration.

---

## GitHub Actions

`.github/workflows/forge-certify.yml`:

```yaml
name: forge-certify

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  certify:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Forge
        run: |
          # Until atomadic-forge is on PyPI, install from a pinned ref.
          pip install "git+https://github.com/atomadictech/atomadic-forge@v0.2.2"
          # Or, if you vendor wheels: pip install --no-index --find-links wheels/ atomadic-forge

      - name: Wire scan (upward-import discipline)
        run: |
          forge wire src/your_package --json > wire.json
          python -c "import json,sys; r=json.load(open('wire.json')); \
            sys.exit(0 if r.get('verdict')=='PASS' else 1)"

      - name: Certify (gate at score >= 75)
        run: |
          forge certify . --package your_package --json > certify.json
          python -c "import json,sys; r=json.load(open('certify.json')); \
            s=r.get('total_score',0); \
            print(f'forge certify score: {s}/100'); \
            sys.exit(0 if s >= 75 else 1)"

      - name: Upload reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: forge-reports
          path: |
            wire.json
            certify.json
            .atomadic-forge/
```

**What this does:**

- `forge wire --json` is parsed for `verdict == "PASS"`. Anything else
  fails the job.
- `forge certify --json` is parsed for `total_score`. Below 75 fails
  the job. Adjust the threshold to match your team's policy.
- Both reports plus the full `.atomadic-forge/` provenance directory
  are uploaded as build artifacts so reviewers can inspect them on the
  PR.

---

## GitLab CI

`.gitlab-ci.yml`:

```yaml
stages:
  - certify

forge-certify:
  stage: certify
  image: python:3.11-slim
  timeout: 10 minutes
  before_script:
    - pip install "git+https://github.com/atomadictech/atomadic-forge@v0.2.2"
  script:
    - forge wire src/your_package --json > wire.json
    - |
      python -c "import json,sys; r=json.load(open('wire.json')); \
        sys.exit(0 if r.get('verdict')=='PASS' else 1)"
    - forge certify . --package your_package --json > certify.json
    - |
      python -c "import json,sys; r=json.load(open('certify.json')); \
        s=r.get('total_score',0); \
        print(f'forge certify score: {s}/100'); \
        sys.exit(0 if s >= 75 else 1)"
  artifacts:
    when: always
    expire_in: 1 week
    paths:
      - wire.json
      - certify.json
      - .atomadic-forge/
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

Same shape as the Actions workflow: install, wire, certify, fail on
threshold, upload artifacts.

---

## pre-commit

For local-developer guard rails, expose Forge as a pre-commit hook.
Forge ships a `pre-commit-hooks.yaml` you can publish from this
repo. The shape is:

`.pre-commit-hooks.yaml` (in this repo):

```yaml
- id: forge-wire
  name: forge wire (upward-import discipline)
  description: Scan src/ for upward imports across the 5 tiers.
  entry: forge wire
  language: system
  pass_filenames: false
  args: [src]
  stages: [pre-commit, pre-push]

- id: forge-certify
  name: forge certify (architecture conformance)
  description: Score architecture conformance; fails below threshold.
  entry: bash -c 'forge certify . --json > /tmp/certify.json && \
    python -c "import json,sys; r=json.load(open(\"/tmp/certify.json\")); \
    sys.exit(0 if r.get(\"total_score\",0) >= 75 else 1)"'
  language: system
  pass_filenames: false
  stages: [pre-push]
```

Then in **the consuming repo's** `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/atomadictech/atomadic-forge
    rev: v0.2.2
    hooks:
      - id: forge-wire
      - id: forge-certify
```

The first file lives in *this* repo (Forge); the second is what your
users add to *their* repo. Run `pre-commit install` once and the gates
fire on every commit / push.

> Note: `forge certify` is heavier than `forge wire`. The hook above
> runs `wire` on every commit and `certify` only on push, which is the
> right tradeoff for most teams. Adjust the `stages:` list if your
> workflow differs.

---

## What's still on the roadmap

- **Lane G1** — a native `forge certify --fail-below-score 75` flag.
  Once shipped, every recipe above collapses to a single line. The
  current `python -c` workaround is intentionally explicit so the
  semantics survive the migration.
- **Lane G2** — `atomadictech/forge-action` GitHub Action. Once
  published, the GitHub Actions workflow above becomes
  `uses: atomadictech/forge-action@v1`.
- **Lane G5** — cryptographically signed certify reports. The schema
  is finalized; signing is not yet wired. Today, treat the JSON as
  authoritative-but-unsigned.

When those land, this page will be updated and the manual recipes will
be marked legacy (not deleted — a few teams will want to keep the
unsigned, dependency-free path).
