# 03 — The 5-tier monadic law

Why every file lives in exactly one tier, why tiers compose upward only,
and why Forge enforces this mechanically instead of leaving it as a
"best practice."

## The tiers

```
a4_sy_orchestration/   CLI, entry points, top-level orchestrators
        ↑
a3_og_features/        feature orchestrators (combine composites into capabilities)
        ↑
a2_mo_composites/      stateful classes, clients, registries, stores
        ↑
a1_at_functions/       pure stateless functions (validators, parsers, formatters)
        ↑
a0_qk_constants/       constants, enums, TypedDicts.  Zero logic.
```

**Compose upward, never downward.** A pure function never depends on a
stateful class. A CLI command orchestrates everything below it but
invents nothing new.

## Why this exact split

There's nothing magical about "5 tiers" — what matters is that each
tier has a **provable property**:

- **a0 has no behavior** → trivially testable, no mocks needed.
- **a1 has no I/O** → property-tested with random inputs, no fixtures.
- **a2 has state** → tests need setup/teardown, but no I/O.
- **a3 has orchestration** → integration tests with composites.
- **a4 has I/O** → end-to-end tests, real or mocked.

The architecture forces you to write **buildable-from-the-bottom** code.
You can't have an a1 function that secretly does I/O because Forge will
catch it. You can't have an a2 class that imports a3 because wire scan
will fail. The constraint is what makes mechanical verification possible.

## What changes when AI is generating

Without enforcement, AI-generated code degrades into a mush of:

- god-classes (everything in one file)
- circular imports (a2 imports a3 which imports a2)
- hidden coupling (a1 functions calling I/O via globals)
- naming chaos (the same concept spelled five ways)

With Forge enforcement, the LLM gets immediate, mechanical feedback:

> Wire scan: FAIL (1 violation)
> - `a1_at_functions/utils.py` imports `Registry` from tier
>   `a3_og_features` — upward import, illegal.

The LLM has to fix it before the score climbs. The fix is usually
mechanical (move the function, or split the import). The architectural
property holds even though the LLM has no human-style "feel" for
architecture.

## Naming conventions

| Tier | Naming pattern |
|------|---------------|
| a0 | `*_config.py`, `*_constants.py`, `*_types.py`, `*_enums.py` |
| a1 | `*_utils.py`, `*_helpers.py`, `*_validators.py`, `*_parsers.py` |
| a2 | `*_client.py`, `*_core.py`, `*_store.py`, `*_registry.py` |
| a3 | `*_feature.py`, `*_service.py`, `*_pipeline.py`, `*_gate.py` |
| a4 | `*_cmd.py`, `*_cli.py`, `*_runner.py`, `*_main.py` |

Forge's tier classifier uses these patterns + body-state detection
(does the class have `self.x = …`?) to make a tier guess. You can
override by placing the file in the desired tier directory — wire wins
over name.

## Mechanical verification

Run on any tier-organised package:

```bash
forge wire src/<package>
```

Output:

```
Wire scan: src/calc
  verdict:    PASS
  violations: 0
```

The same scanner runs in CI via `import-linter` (Forge ships a contract
in its own `pyproject.toml`). On any PR, the pipeline gates on the
contract — no upward imports merge.

## When the rule is wrong

Sometimes the right architecture isn't 5 tiers — embedded systems,
research notebooks, single-script tools. Forge isn't the right tool
for those.

For everything that's a multi-file Python codebase you intend to
maintain past 3 months, the 5-tier law is a useful constraint. The
proof is in the certify scores you see across runs.

## Read further

- [04-plug-in-llms.md](04-plug-in-llms.md) — choosing a generator.
- [05-multi-repo-absorb.md](05-multi-repo-absorb.md) — the absorb flow,
  applying the law to existing flat-layout repositories.
