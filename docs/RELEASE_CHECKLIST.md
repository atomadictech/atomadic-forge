# Atomadic Forge Release Checklist

Use this as the shipping pass before tagging a release or recording a demo.

## Must Pass

- [ ] `python -m pytest --basetemp .pytest_tmp_run`
- [ ] `ruff check .`
- [ ] `lint-imports`
- [ ] `git diff --check`
- [ ] `forge commandsmith smoke --json`
- [ ] `forge doctor --json`
- [ ] `forge certify . --package atomadic_forge --fail-under 100`
- [ ] `python -m build`
- [ ] `python -m twine check dist/*`

## CLI UX Scenarios

- [ ] `forge --help` lists the core verbs and specialty verbs.
- [ ] `forge recon . --json` returns language counts and symbol totals.
- [ ] `forge auto <sample> <out>` dry-runs without writing a tier tree.
- [ ] `forge auto <sample> <out> --apply --package <name>` writes `STATUS.md`.
- [ ] `forge wire src/atomadic_forge --json` reports `PASS`.
- [ ] `forge chat ask "hello" --provider stub --no-cwd-context --json` returns the chat schema.
- [ ] `forge demo list --json` lists LLM and static showcase presets.
- [ ] `forge demo run --preset js-counter --skip-cli-demo` runs without an LLM key.
- [ ] A Python `forge iterate run ... --provider stub` output contains `.atomadic-forge/quality.json`, `docs/API.md`, `docs/TESTING.md`, and `tests/test_generated_smoke.py`.

## Local LLM Scenarios

- [ ] Busy-machine smoke:
  `FORGE_OLLAMA_MODEL=qwen2.5-coder:1.5b FORGE_OLLAMA_NUM_PREDICT=256 forge chat ask "Reply OK" --provider ollama --no-cwd-context`
- [ ] Idle-machine baseline:
  `FORGE_OLLAMA_MODEL=qwen2.5-coder:7b FORGE_OLLAMA_NUM_PREDICT=1536 forge evolve run "..." <out> --auto 3 --iterations 1 --provider ollama`
- [ ] Provider failures show a CLI error box/message, not a Python traceback.
- [ ] `.atomadic-forge/transcripts/` is written for iterate/evolve runs.

## Documentation

- [ ] README quickstart matches current command names.
- [ ] `docs/COMMANDS.md` provider matrix matches `PROVIDER_HELP`.
- [ ] `docs/tutorials/04-plug-in-llms.md` documents local model fallback settings.
- [ ] New commands have a page under `docs/commands/` or are listed in `docs/COMMANDS.md`.
- [ ] Known limits are explicit and not marketing-fluffed.
- [ ] Generated docs are clearly labeled as generated and do not overwrite human-authored `docs/API.md` or `docs/TESTING.md`.

## Release Notes

- [ ] Update `CHANGELOG.md` with user-facing changes.
- [ ] Note any local-model bakeoff results that changed default recommendations.
- [ ] Note migration steps for new env vars or provider behavior.
- [ ] Confirm version in `pyproject.toml` and package metadata.

## GitHub

- [ ] CI badge points at `.github/workflows/ci.yml`.
- [ ] Pull request template matches the current local gates.
- [ ] Bug and feature issue templates route users to reproducible reports.
- [ ] `SECURITY.md` points to private vulnerability reporting.
- [ ] Dependabot is enabled for GitHub Actions and pip metadata.
- [ ] Release workflow builds artifacts and publishes to PyPI only from a published, non-prerelease GitHub Release.
