# Contributing to Atomadic Forge

## Setup

```bash
git clone <this-repo> atomadic-forge && cd atomadic-forge
pip install -e ".[dev]"
python -m pytest --basetemp .pytest_tmp_run
ruff check .
lint-imports
```

## The 5-tier law applies to Forge itself

Every PR is gated by:

```bash
forge wire src/atomadic_forge       # zero upward-import violations
pytest tests/                        # all pass
forge certify . --fail-under 90      # gate score ≥ 90
```

The `pyproject.toml` declares an `import-linter` contract that mirrors the
`forge wire` rule — CI runs both.

## File placement

- A pure function → `src/atomadic_forge/a1_at_functions/`
- A class with mutable state → `src/atomadic_forge/a2_mo_composites/`
- A feature orchestrator → `src/atomadic_forge/a3_og_features/`
- A CLI command surface → `src/atomadic_forge/commands/`
- A console-script entry point → `src/atomadic_forge/a4_sy_orchestration/cli.py`

## Tests

Every new module gets a `tests/test_<module>.py`. Tests are grouped by
function, not by class hierarchy. Stubs that always pass are not allowed
(`pytest.skip(...)` is fine; `assert True` is not).

## Documentation

If you add a verb, update `README.md`'s verb table and add a one-line
description to `CHANGELOG.md`. If the verb produces a JSON artifact, declare
its `schema_version` in `a0_qk_constants/forge_types.py`.

## Pull requests

CI runs on Python 3.10, 3.11, and 3.12. Before opening a PR, run:

```bash
python -m pytest --basetemp .pytest_tmp_run
ruff check .
lint-imports
python -m atomadic_forge.a4_sy_orchestration.cli wire src/atomadic_forge --json
python -m atomadic_forge.a4_sy_orchestration.cli commandsmith smoke --json
python -m atomadic_forge.a4_sy_orchestration.cli certify . --json --fail-under 100
```

Do not commit `.atomadic-forge/`, demo outputs, local Ollama transcripts,
API keys, or generated scratch directories.

## Commit style

```
<verb>(<area>): <imperative summary>

Why this matters / what it changes / migration notes if any.
```

Examples: `feat(emergent): downweight Any-bridges in chain ranker`,
`fix(wire): handle multi-tier paths under packages with inner namespaces`.
