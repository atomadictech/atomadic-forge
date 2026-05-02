# Changelog

## 0.5.2 - Agent ergonomics and language-aware guidance

Implements the first round of quality-of-life improvements from the
Forge agent review. This release makes Forge friendlier when an agent
uses it on JavaScript repos, documentation/research patches, or live
MCP connections.

### Added

- `forge mcp doctor` smoke-tests MCP stdio with framed `initialize`,
  `tools/list`, and `shutdown` requests. It reports version, project
  root, tool count, framed-stdio status, server exit code, and a
  recovery hint.
- `tools/list` entries now include a `cli_command` fallback so agents
  can switch from MCP to shell without guessing command names.
- Shared validation heuristics now detect `package.json` scripts,
  JS/TS tests, tier roots, and release-gate commands.

### Improved

- `context-pack` prefers `npm run verify` / `npm test` for JavaScript
  projects and derives `forge wire` gates from real tier roots.
- `preflight` recognizes non-code artifacts such as `docs/`,
  `research/`, `.github/`, and `cognition/guides/` as valid project
  memory instead of misplaced source.
- `select-tests` discovers JS/TS test files and avoids mirror pytest
  requirements for documentation-only changes.
- `score-patch` no longer treats docs/research-only diffs as code
  changes without tests, and emits language-aware validation commands
  when a project root is provided.
- `compose-tools verify_patch` now maps to
  `score_patch -> select_tests -> wire -> certify`.
- Hidden worktrees, experiment directories, build output, and
  `node_modules` are skipped when deriving release-gate wire roots.

### Tests

- Added regression tests for JavaScript validation selection,
  non-code artifact preflight, docs-only patch scoring, exact
  `verify_patch` recipe matching, MCP CLI fallback metadata, and
  `forge mcp doctor`.

---

## 0.5.1 — MCP stdio framing compatibility

Fixes `forge mcp serve` for MCP hosts that use LSP-style
`Content-Length` framing over stdio instead of newline-delimited JSON.
Modern Codex / VS Code MCP bridges can spawn the server, list tools,
and then send framed `tools/call` requests; before this patch Forge
could misread the frame header as JSON and leave the host waiting until
its tool-call timeout.

### Fixed

- `forge mcp serve` now accepts both newline-delimited JSON-RPC and
  `Content-Length` framed JSON-RPC on stdin.
- MCP responses are written in the same framing style as the request
  that triggered them, preserving compatibility with shell smoke tests
  and stricter MCP clients.
- The dispatcher now treats both `notifications/initialized` and
  `initialized` as no-response initialization notifications.
- The VS Code extension manifest version now tracks the `0.5.1`
  package release.

### Tests

- Added a framed stdio regression test for initialize → initialized →
  ping → shutdown.
- Verified framed `tools/call list_recipes` against the real
  `forge mcp serve` command.

---

## 0.3.5 — Copilot's Copilot CLI parity + GUI version sync

The MCP exposes 21 tools. Until 0.3.5, only 12 of them had CLI
front-doors — the other 9 were JSON-RPC-only, which meant a developer
or agent shell-running `forge` couldn't sample the same intelligence
without spawning the MCP server, speaking JSON-RPC, and parsing
`content[0].text`. This release closes the gap.

### Added — 9 new top-level CLI verbs

Every MCP-only Codex tool now has a CLI sibling that prints JSON to
stdout, suitable for piping into `jq`, scripts, or an agent's Bash
subprocess:

| Verb | Codex # | What it does |
|---|---|---|
| `forge explain-repo <root>` | #6 | Humane operational orientation: one-liner + core flow + do_not_break list + important tests + release state |
| `forge score-patch [--file diff.patch]` | #3 | Patch risk scorer: arch / test / public-API / release risk + needs_human_review boolean |
| `forge select-tests <intent> --file ... --file ...` | #7 | Minimum + full-confidence test sets per intent; mirror-name matches plus tier-mate tests |
| `forge rollback-plan --file ... --file ...` | #11 | Structured undo plan: files to remove, caches to clean, docs to restore, tests to rerun, risk level |
| `forge compose-tools <goal>` | #9 | Tool-use planner: keyword → ordered MCP tool sequence (orient / release_check / fix_violation / before_edit / verify_patch) |
| `forge why-did-this-change <file>` | #5 | Agent memory: every lineage entry + plan event that touched the file |
| `forge what-failed-last-time <area>` | #5 | Failed / rolled-back plan events matching an area substring |
| `forge adapt-plan --cap apply --cap shell` | #8 | Capability-aware card filtering: tag each card with recommended_handling |
| `forge load-policy <root>` | #10 | Read `[tool.forge.agent]` from pyproject.toml (protected_files / release_gate / max_files_per_patch / require_human_review_for) |

All verbs default to JSON output. None mutate the repo.

### Why this matters for agents

Before 0.3.5, an agent that wanted to compose a release-check tool
chain had to either spawn `forge mcp serve`, hand-craft a tools/call
JSON-RPC envelope, send it over stdio, and parse the wrapped text
content — or skip the intelligence entirely. After 0.3.5, the same
agent runs:

```bash
forge compose-tools "release_check" | jq .steps
forge select-tests "fix(api): rate limit" --file src/api/limit.py
forge score-patch --file my.diff
```

Three Bash calls. Same data. Zero JSON-RPC.

### GUI version sync

`forge-web` PWA + `forge-studio` Tauri both pull their version label
from `forge-ui-core`'s `ForgeShell.tsx` default. That default was
still pinned to `0.3.2`. Now `0.3.5` so both shells correctly identify
themselves at the bottom of the sidebar.

### Tests

902 passing, 2 skipped (no test changes — every new verb is a thin
wrapper around an already-tested a1 function).
`forge wire src/atomadic_forge` PASS, `forge certify .` holds at
**100/100**.

---

## 0.3.4 — `forge whoami` for agents and humans

Adds the agent-empowerment QOL win that 0.3.3 was missing: when the
MCP gate refuses with `subscription required`, agents (and humans)
need a cheap way to ask **"who is the gate seeing me as, and from
which source?"** without burning a real tool call. `forge whoami` is
that command.

### Added

- **`forge whoami`** new top-level CLI verb (and `--json` for scripted
  consumers). Returns:
  ```json
  {
    "ok": true,
    "source": "credentials_file" | "env" | "missing",
    "key_prefix": "fk_live_b3502…",
    "email": "tom@example.com",
    "plan": "pro",
    "verify_ok": true,
    "verify_reason": "",
    "credentials_path": "~/.atomadic-forge/credentials.toml",
    "env_var": "FORGE_API_KEY"
  }
  ```
  Resolution order matches the MCP gate exactly (env → credentials.toml).
  `--no-verify` skips the network roundtrip for offline triage.
- **6 new unit tests** for whoami covering missing-key, env-key,
  credentials-file-key, env-wins-over-file, --no-verify, and
  verify-rejection.

### Why this matters for agents

Before 0.3.4, an agent that hit `MCP error -32001: Forge subscription
required` had two options: ask the human to restart the MCP, or fail.
With 0.3.4 the agent can call `forge whoami --json` (via Bash) and
get a structured answer it can act on:

  * `source == "missing"` → tell the user to run `forge login`
  * `source == "credentials_file"` + `verify_ok == false` → key is
    revoked or stale; `forge login` again
  * `source == "env"` + `verify_ok == false` → CI env var is wrong
  * everything green → restart the MCP host (the running subprocess
    needs a respawn to see the new env)

This closes the loop for the auth experience — the agent can diagnose
its own failure mode.

### Tests

902 passing, 2 skipped. `forge wire src/atomadic_forge` PASS,
`forge certify .` holds at **100/100**.

---

## 0.3.3 — MCP gate reads credentials.toml + actionable error message

Hot-fix release. Closes the gap where `forge login` writes a key to
`~/.atomadic-forge/credentials.toml` but `forge mcp serve` rejects every
tool call with `Forge subscription required` because it only checks
`FORGE_API_KEY` env. After 0.3.3, `forge login` once is enough — every
MCP host (Claude Code / Cursor / Aider / Devin / VS Code Copilot) picks
the key up automatically with no shell-scoped env-var ritual.

### Added

- **`read_api_key_from_credentials_file(path)`** — pure a1 helper that
  parses `~/.atomadic-forge/credentials.toml` (the file `forge login`
  writes) and returns the `[forge_auth].api_key` value, only when it
  has the `fk_live_` prefix. Six new unit tests cover missing file,
  wrong prefix, missing section, malformed TOML, string-path argument,
  and the canonical login output.
- **MCP `_auth_check` falls back to credentials.toml** when
  `FORGE_API_KEY` is not in env. Resolution order is documented in the
  docstring: env first (CI / explicit override), then credentials file
  (one-time `forge login`).
- **Actionable auth-error message** — when neither env nor credentials
  file yields a key, the JSON-RPC error now reads
  `"Forge subscription key not configured. Run forge login once …"`
  (was: `"FORGE_API_KEY not set or wrong prefix"`).

### Tests

896 passing, 2 skipped (was 841/2 at 0.3.2 — +6 new tests for the
credentials.toml fallback). `forge wire src/atomadic_forge` PASS,
`forge certify .` holds at **100/100**.

---

## 0.3.2 — Cyberpunk Forge Studio UI + recovery fixes

841 tests passing, 2 skipped. `forge wire src/atomadic_forge` PASS,
`forge certify .` = **100/100**.

### Added

- **Forge Studio cyberpunk UI reskin** — Full visual overhaul from
  slate/blue inline-styles to the Atomadic cyber design system.
  Tailwind v4 (`@tailwindcss/vite`), `motion` (Framer Motion v12),
  `lucide-react`. New primitives: `NeonButton`, `ActionableCard`,
  `ScoreGauge`, `PipelineStepper`. Collapsible sidebar with `layoutId`
  animated active indicator, mobile bottom bar.
- **ProjectScanDashboard** — animated stat cards, wire verdict banner,
  motion tier bars, F-code violation list with severity colours.
- **All panels reskinned** — ArchitectureGraph, ComplexityHeatmap,
  DebtCounter, AgentTopologyMap, ErrorBanner all use cyber palette.
- **`forge status` verb** — shows MCP connection status.

### Fixed

- **Wire scan phantom violations** — `.pytest_tmp_run/` test fixtures
  no longer pollute wire results; `path_parts_contain_ignored_dir()`
  now used throughout.
- **`forge audit list` / `forge audit log`** — default to CWD
  (`Path(".")`) instead of requiring explicit path argument.
- **DebtCounter** — `fCodeSeverity(v.f_code)` replaces broken
  `SEVERITY_WEIGHTS[v.severity]` (was always returning weight 1).
- **WireViolation TypeScript interface** — aligned with actual JSON
  schema (`f_code`, `from_tier`, `to_tier`).
- **ArchitectureGraph** — staircase node layout instead of single column.
- **`forge doctor`** — optional dep checks (complexipy, bandit, mypy).
- **`commandsmith smoke`** — `--include-core` flag tests all 23 core verbs.

## 0.3.1 — Golden Path lanes B/C/D/F/G ship

783 tests passing, 2 skipped. `forge wire src/atomadic_forge` PASS,
`forge certify .` = **100/100**.

### Added — Golden Path lanes shipped

- **Lane B (Studio)** — Tauri + React + TypeScript visual sandbox:
  Project Scan Dashboard, Architecture Graph (Cytoscape), Cognitive
  Heatmap, Real-Time Debt Counter, Agent Topology Map. `forge-studio/`.
- **Lane C W3 (Badge worker)** — Cloudflare Worker emitting
  shields.io-compatible SVG badges from Receipts in a `FORGE_RECEIPTS`
  KV namespace. `cloudflare-workers/badge/`.
- **Lane D W8 (Sidecar grammar)** — `.forge` v1.0 spec + parser. Per-
  symbol effect / compose_with / proves declarations.
  `a1.sidecar_parser`, `docs/SIDECAR.md`.
- **Lane D W11 (Sidecar validator)** — AST cross-check of `.forge`
  against source. 7 drift classes (S0000–S0006) promoted into the
  F-code namespace as F0100–F0106. `a1.sidecar_validator`,
  `forge sidecar parse / validate`.
- **Lane D W12 (LSP)** — `forge lsp serve` Content-Length framed JSON-
  RPC server. Live diagnostics, hover, goto-source for `.forge` files.
- **Lane D W14 (VS Code extension)** — `vscode-forge-extension/`.
  Language client wired to `forge lsp serve`.
- **Lane F W16-W18 (CS-1 + compliance)** — CS-1 Conformity Statement
  renderer + EU AI Act Annex IV / SR 11-7 / FDA PCCP / CMMC-AI / NIST
  AI RMF mappings. `a1.cs1_renderer`, `forge cs1`.
- **Lane G (Signing + SBOM + policy templates)** — Ed25519 local
  signer (soft-fail without `cryptography`), CycloneDX 1.5 SBOM
  emitter, three policy stances (strict / permissive / regulated),
  `--seed-determinism` on `forge auto`. `a1.local_signer`,
  `a1.sbom_emitter`, `forge sbom`, `--local-sign` on certify.

### Codex "Copilot's Copilot" — completed

All 12 items closed: compact summaries, action cards, context_pack,
preflight_change, score_patch, plan persistence (`plan-list / plan-
show / plan-step / plan-apply`), MCP `auto_plan` tool, `--version`,
`--score` field on summaries, agent_summary/v1 + agent_plan/v1
schemas, repo_explainer, tool_composer.

## Unreleased — _Pre-audit lanes + Golden Path Lane A W0_

Five commits since `v0.3.0`. Trajectory: 643 → **702 passing**, 2
skipped (+59). `forge wire src/atomadic_forge` PASS at every commit.
`forge certify .` = 100/100 held.

### Added — Lane D W12 forge-lsp stdio LSP server (`d23005f`)

Closes Lane D W12. **Editor-agnostic LSP server** gives every client
(VS Code, Neovim, Helix, IntelliJ) live diagnostics + hover +
goto-source on `.forge` sidecar files. The Lane D arc reaches the
in-editor surface — sidecar feedback now arrives where the agent
actually edits.

- **`a1_at_functions/lsp_protocol.py`** — pure dispatcher (~280 LOC).
  `dispatch_request(req, *, state) -> (responses, notifications)`.
  In-memory `LspState` document store keyed by URI.
  - `initialize` / `initialized` / `shutdown` / `exit` — handshake +
    clean shutdown
  - `textDocument/didOpen` / `didChange` / `didSave` / `didClose` —
    document lifecycle
  - `textDocument/hover` — markdown summary of the cursor's symbol
    (effect, tier, `compose_with`, `proves`)
  - `textDocument/definition` — goto-source: `name: login` line in
    `foo.py.forge` → `foo.py:login`
  - `textDocument/publishDiagnostics` (server-initiated) — emitted
    after every did{Open,Change,Save} with the validator's findings
    promoted to F0100-F0106 codes
  Pure: bounded I/O for source-file resolution only (no LSP-side
  shell-out, no LLM call).
- **`a3_og_features/lsp_server.py`** — stdio LSP framing (~70 LOC).
  `serve_stdio(*, stdin, stdout, stderr) -> int`. Reads
  Content-Length-framed JSON-RPC, dispatches, writes responses +
  notifications back. Bad JSON surfaces `-32700` without killing the
  loop.
- **`forge lsp serve`** — sub-app verb. Docstring includes VS Code +
  Neovim `lspconfig` snippets so consumers can drop the server in
  without hunting docs.

**Tests** (+18 in `tests/test_lsp_protocol.py`): handshake (4),
diagnostics (3), hover (2), definition (2), lifecycle (3), URI
parsing (2). 702 passing / 2 skipped (was 684).

### Added — Lane D W11 follow-up: F0100-F0106 sidecar drift codes (`7099360`)

Promotes the local `S0xxx` labels emitted by `sidecar_validator` into
the **global F-code registry** so downstream tools (`forge audit` /
`agent_summary` / `score_patch` / `plan-apply`) can address sidecar
drift in the same namespace as wire violations.

- **`a0_qk_constants/error_codes.py`** registry seeds:
  | F-code | Severity | What |
  |---|---|---|
  | `F0100` | error | sidecar source unparseable |
  | `F0101` | error | sidecar declares missing symbol |
  | `F0102` | warn | sidecar coverage incomplete |
  | `F0103` | error | `Pure`-declared violates purity |
  | `F0106` | warn | sidecar tier mismatch |
- **`SIDECAR_S_TO_F`** mapping (`S0000 -> F0100`, `S0001 -> F0101`,
  …) so the validator doesn't have to know the F-code seeding
  pattern.
- `ValidationFinding` gains an optional `f_code` field. Every
  finding whose `code` is in the mapping gets the registered F-code
  attached automatically before the report returns.

Lane D W8/W11 drift codes are now **first-class F-coded errors** —
addressable, dashboard-friendly, route-able through
`forge enforce` (when an auto-fix path lands in W14).

**Tests** (+2 in `tests/test_error_codes.py`): registry pinned set
extended with F0100-F0106 by name; `SIDECAR_S_TO_F` mapping pinned;
validator dogfood test confirms a synthesized `S0001` finding
carries `f_code='F0101'`. 684 passing.

### Added — Lane D W11 sidecar cross-validator (`60c174e`)

Closes Lane D W11. The W8 spec ships the *grammar*; W11 ships the
**verifier** that catches sidecar drift by cross-checking declared
effects against the source AST.

- **`a1_at_functions/sidecar_validator.py`** — pure (~120 LOC).
  `validate_sidecar(sidecar, *, source_text, source_path) ->
  ValidationReport` (`atomadic-forge.sidecar.validate/v1`). Pure AST
  walk + sidecar dict walk; no exec, no LLM, no network. Soft on
  parse failures (returns `verdict='unparseable'` instead of
  raising).
- **5-of-7 named drift classes detected today**:
  | Code | Class | Severity |
  |---|---|---|
  | `S0000` | source did not parse | `unparseable` |
  | `S0001` | sidecar declares a symbol the source doesn't have | error |
  | `S0002` | source has an undeclared public symbol | warn (gradual coverage is OK) |
  | `S0003` | `Pure`-declared symbol violates purity (IO, network, non-determinism in source) | error |
  | `S0006` | declared `tier` mismatches detected path tier | warn |
  | `S0005` | `compose_with` name resolution | reserved (W20) |
  | `S0007` | `proves:` clauses against Lean4 corpus | reserved (W20) |
- **CLI verbs**: `forge sidecar parse <file.forge>` and
  `forge sidecar validate <source.py>` — both `--json`-friendly,
  exit 1 on FAIL. The validator auto-resolves the sibling
  `<source>.forge` via `find_sidecar_for`.

**Reserved for later in Lane D**:
- **W12** — `forge-lsp` server (in-editor sidecar diagnostics).
- **W14** — VS Code extension (hover + diagnostics surface).
- **W18** — JetBrains plugin.
- **W20** — Bao-Rompf compose-by-law checker (`S0005`) + Lean4
  `proves:` discharger (`S0007`).

**Tests** (+11 in `tests/test_sidecar_validate.py`): happy path,
S0000-S0006 unit tests, CLI parse / validate FAIL / PASS.

### Added — Lane D W8 `.forge` sidecar v1.0 (`b4ad686`)

### Added — Lane D W8 `.forge` sidecar v1.0 (`b4ad686`)

The "**TypeScript for architecture**" paradigm from BEP-1, now real.
A `.forge` sidecar is a YAML file beside any source file
(`users/auth.py.forge`) that declares the per-symbol contract Forge
would otherwise infer heuristically. **Opt-in, gradual, never
required** — adoption-curve modeled on TypeScript itself.

- **Schema** `atomadic-forge.sidecar/v1` at
  `a0_qk_constants/sidecar_schema.py` — pinned by tests, pure a0
  (imports only `__future__` + `typing`).
  - **`EffectKind`** enum (the seven-effect categorical lattice from
    Bao-Rompf 2025): `Pure`, `IO`, `NetIO`, `KeyedCache`, `Logging`,
    `Random`, `Mutation`.
  - **`SidecarSymbol`** TypedDict: `name`, `effect`, `compose_with`,
    `proves`, `tier`, `notes`.
  - **`SidecarFile`** TypedDict: `schema_version`, `target`,
    `symbols`, `extra`.
- **Parser** at `a1_at_functions/sidecar_parser.py` — pure (~140 LOC):
  - `parse_sidecar_text(text, *, source) -> ParseResult`
  - `parse_sidecar_file(path) -> ParseResult`
  - `find_sidecar_for(source_file) -> Path` — convention:
    `users/auth.py` → `users/auth.py.forge`
  - YAML errors / missing files / non-mapping top-levels become
    structured `errors` lists; **never raise**. Unknown effects
    preserved with a warning (forward-compat). Unknown top-level
    fields preserved in `extra`.
- **Spec doc** at `docs/SIDECAR.md` — v1.0 grammar + worked example
  covering `NetIO` + `Pure` + `Logging` + `compose_with` + `proves`.
- `pyyaml >= 6, < 7` added as runtime dep (parser hard-requires).

**Reserved for later in Lane D:**
- **W11** — `sidecar_validate` (cross-check declared effects against
  source AST).
- **W12** — `forge-lsp` + VS Code extension (hover + diagnostics).
- **W20** — Bao-Rompf `compose_with` checker + Lean4 `proves:`
  discharger.

This shipment lands the **"five surfaces, one Receipt"** convergence
predicted by BEP-1: terminal Card, PR comment, README badge, MCP
resource, signed CS-1 PDF — and now the per-source-file effect
signature that makes the polyglot Receipt rendering precise rather
than heuristic.

**Tests** (+16 in `tests/test_sidecar.py`): schema (3), happy path
(4), error paths (5), forward-compat (3), tier discipline (1). 671
passing / 2 skipped (was 655). Wire scan PASS.

### Added — Codex-6 policy-as-code + recipes CLI + Receipt v1.1 (`c74670b`)

### Added — Codex-6 policy-as-code + recipes CLI + Receipt v1.1 (`c74670b`)

Three small but high-leverage additions on top of `v0.3.0`:

**(1) Policy-as-code is now ENFORCED, not just queryable.**

- `preflight_change` reads `[tool.forge.agent].max_files_per_patch`
  from `pyproject.toml` and uses it as the scope threshold (default
  remains 8 when no policy declared). An explicit caller-supplied
  `--scope-threshold` still wins.
- `preflight_change` tags any `proposed_file` matching
  `protected_files` with a per-file note **and** emits an overall
  "request human review" note listing the matches.
- `score_patch` grows an optional `project_root` kwarg. When provided
  AND `[tool.forge.agent]` declares `protected_files`, any diff
  touching a protected file forces `needs_human_review = True`
  regardless of diff size. Closes Codex's framing — *"Forge enforces
  the local social contract, not just the tier law."*

**(2) New CLI verb: `forge recipes [name]`** — same data the MCP
`list_recipes` / `get_recipe` tools return, but exposed for direct
human / shell-script use.

```bash
forge recipes                    # list every golden-path recipe
forge recipes release_hardening  # show one recipe (checklist +
                                 # file_scope_hints + validation_gate)
forge recipes --json | jq        # machine-readable
```

**(3) Receipt v1.1 — `polyglot_breakdown` field shipped (Lane A W8 seed).**

`ForgeReceiptV1` gains an optional `polyglot_breakdown` block
populated automatically by `build_receipt` from the scout report:

- per-language file counts
- per-language symbol counts
- `primary_language` verdict

Per-language certify scores stay for `v0.4` once the JS/TS
behavioural pytest gate lands (Golden Path Lane A W8 acceptance);
today's seed gives downstream consumers (Lane B Studio, Lane F CS-1
Conformity Statement, README badges) enough to render *"this repo is
80% Python, 15% TS"* directly from the Receipt.

This is the v1.0 → v1.1 bump promised in
`a0_qk_constants/receipt_schema.py`'s versioning roadmap (W8) — now
shipped one major lane ahead of W8 schedule.

**Tests** (+12 in `tests/test_codex_6_enforce_polyglot.py`): 655
passing / 2 skipped (was 643). Wire scan PASS.

## 0.3.0 — _Copilot's Copilot complete · 21 MCP tools · `forge --version` (`009d6d7`, tag `v0.3.0`)_

**The architectural control plane for AI coding agents.** Codex's
framing landed: Forge is not the agent — it's the always-on senior
engineer beside the agent. Cumulative trajectory since `0.2.2`
(reference `ee8b8cb`):

- **31 commits**, **+342 tests** (301 → **643 passing**, 2 skipped).
- `forge wire src/atomadic_forge` **PASS at every commit** —
  tier discipline held across the entire release.
- `forge certify .` = **100/100** held (pre-bump verification).
- `python -m build --no-isolation` produces a clean
  `atomadic_forge-0.3.0.tar.gz` + `atomadic_forge-0.3.0-py3-none-any.whl`.
- `forge mcp serve | tools/list` returns **21 tools** + 5 resources
  (pinned by tests).

**Lane status at v0.3.0**:
- **Lane A: 6-of-7 named deliverables shipped** (W2 RefAgent
  framework remains; recommended for a delegated agent).
- **Lane C: 3-of-6 shipped** (W1 forge-action, W2 pre-commit-hooks,
  W4 mcp serve).
- **Codex direction: 5-of-5 shipped** — Codex-1 (agent_summary),
  Codex-2 (agent_plan), Codex-3 (plan-apply chain), Codex-4
  (3 hero copilot's-copilot primitives), Codex-5 (full 12-item
  enumeration closed in one sweep).

Lane A is **6 weeks ahead of W0 baseline** — the entire critical-path
stack from schema → emitter → renderer → signer → F-codes → enforce
shipped on master.

### Added — pre-audit operational scaffolding

- **`forge audit list / show / log`** (`7cd840a`, audit-D1) — surfaces
  the Vanguard lineage chain as a verb. Reads
  `.atomadic-forge/lineage.jsonl`; populates Receipt's
  `lineage.lineage_path` field at GP Lane A W4. New module:
  `a1_at_functions/lineage_reader.py`.
- **`forge wire --suggest-repairs`** (`4786836`, audit-D2) — emits a
  per-violation repair hint and an `auto_fixable` count; populates
  Receipt's `wire.auto_fixable` field. Prerequisite for `forge enforce`
  at GP Lane A W6.
- **`forge wire --fail-on-violations`** (`8385cea`, audit-G1) — exits
  non-zero when any upward import is detected. Drop-in CI gate
  consumed by `forge-action` at GP Lane C W1.
- **`forge diff MANIFEST_A MANIFEST_B`** (`6249e74`, audit-D4) —
  schema-aware compare of two scout/certify manifests. Powers Lane B's
  "Shadow Merge" view (W8) and Lane E's PR-comment delta.
- **`--progress` on `forge recon` / `forge auto`** (`ec59a75`, audit-B2)
  — per-file stderr progress line. New module:
  `a1_at_functions/progress_reporter.py`. Feeds Lane B Forge Studio's
  progress pane.
- **F-coded error hints in CLI errors** (`375fe85`, audit-B4) —
  recovery-template hints attached to common CLI failure modes.
  Scaffolding for Lane A W5's full F0001–F0099 catalog. New module:
  `a1_at_functions/error_hints.py`.
- **Pre-audit smoke test** (`b4c8579`, audit-H1) — pins file:line
  claims so `lane-plan.md` cannot drift from the source.
- **`docs/FIRST_10_MINUTES.md` consolidation** (`109e857`, audit-F) —
  unifies onboarding; `docs/CI_CD.md`, `docs/MULTI_REPO.md`,
  `docs/AIR_GAPPED.md` are the deeper paths.

### Added — Golden Path Lane A W0 (critical-path)

- **Forge Receipt JSON v1 wire-format schema** (`f6c487a`, GP-A W0) at
  `a0_qk_constants/receipt_schema.py` (278 LOC) + `docs/RECEIPT.md`
  (305 lines) + `tests/test_receipt_schema.py` (206 LOC). Versioning
  roadmap explicit (v1.0 → v1.1 W8 polyglot_breakdown → v1.2 W12
  slsa_attestation → v2.0 W24 bao_rompf_witnesses). Both Lean4 corpora
  cited (`aethel-nexus-proofs` — 29 theorems, 0 sorry, 0 axioms — and
  `mhed-toe-codex-v22` — 538 theorems, 0 sorry). All signing / lineage
  / attestation fields default to `None` so unsigned dev Receipts
  remain structurally valid. Tier-pure a0.

### Added — Golden Path Lane A W1 (emitter + card)

- **`receipt_emitter.py` + `card_renderer.py`** (`237c35f`, GP-A W1) —
  paired pure-a1 deliverables. Emitter is the inverse of the schema:
  pure transformer `(CertifyResult, WireReport, ScoutReport) →
  ForgeReceiptV1`. Card renderer is the 60×24 box-drawing renderer
  that powers the "62 → 5" viral demo (Lane E W2).
- **`forge certify --emit-receipt PATH`** writes a v1 Receipt JSON.
- **`forge certify --print-card`** prints the rendered card to stdout —
  the artifact the Lane E W2 demo screen-grabs.
- Both flags compose with `--json`, `--fail-under`, `--package`.

### Added — Golden Path Lane A W2 (signer)

- **`receipt_signer.py` + `forge certify --sign`** (`0670880`, GP-A W2).
  Stateful signer wrapping AAAA-Nexus `/v1/verify/forge-receipt` with
  graceful-degradation: missing API key, 4xx, 5xx, network error all
  fall back to unsigned-but-structurally-valid. The signer never
  throws.

### Added — Golden Path Lane A W5 (F-code registry)

- **F-code registry** (`f4c2548`, GP-A W5) at
  `a0_qk_constants/error_codes.py` — every Forge error now carries a
  stable 4-digit code (`F0042`-style) that is **never reused or
  renumbered**. 12 seed codes covering scout, cherry-pick, wire,
  certify, stub-detect, import-repair, assimilate, signing namespaces.
  Adding an F-code is additive; renumbering is a major schema bump.

### Added — Golden Path Lane A W6 (enforce)

- **`forge enforce`** (`b4e7ff2`, GP-A W6) — F-code-routed mechanical
  fixer. Pure planner at `a1_at_functions/enforce_planner.py` produces
  an `EnforceAction` list keyed by F-code; the executor applies them
  with rollback safety. Acceptance gate met: F0042 (a1 upward import)
  auto-resolvable; smoke covers 7 fix paths.

### Added — Golden Path Lane C W1 (forge-action)

- **`forge-action` composite GitHub Action + self-certify dogfood**
  (`dae64d1`, GP-C W1) — the Action's CI runs `forge certify .`
  against itself before publishing, propagating the BEP self-host gate
  pattern from Lane A to Lane C. Drop-in for any consuming repo via
  `.github/workflows/*.yml`.

### Added — Golden Path Lane C W2 (pre-commit hooks)

- **`.pre-commit-hooks.yaml` manifest** (`6c8a36b`, GP-C W2) — Husky-
  style capture: once one developer adds Forge to
  `.pre-commit-config.yaml`, every contributor inherits the gate. Hook
  runs `forge wire --fail-on-violations` (read-only by default; opt-in
  to fail-below via repo-side config). Powers the W3 distribution loop.

### Added — Golden Path Lane A W4 (Vanguard local chain)

- **Local Vanguard chain stub** (`a8e2c7e`, GP-A W4) — every Receipt
  now gets a real `lineage_path` populated from a content-addressed
  local chain, with the same graceful-degradation contract as the W2
  signer: when AAAA-Nexus `/v1/forge/lineage` ships, the publisher
  slots in transparently. Until then the chain is local-only and
  Receipt-verified. Closes Lane A W4.

### Added — Golden Path Lane A W3 (Compiler Feedback Loop)

- **`forge iterate --max-fix-rounds N`** (`6bae93b`, GP-A W3) — pure
  helper at `a1_at_functions/compiler_feedback.py` wired into
  `forge_loop.run_iterate`. The Compiler Agent of the RefAgent family:
  drives a build-error → fix loop iteratively until 100% compile or
  the round-budget is exhausted. Each iterate turn now runs
  `_run_fix_rounds` after the file write. Report includes a new
  `fix_rounds` field (count of fix iterations consumed).
- 8 new tests at `tests/test_compiler_feedback.py` — pure-module
  coverage + a stub-LLM `run_iterate` simulating broken-then-fixed
  sequences.

### Added — agent-native blocker summary surface (Codex-1 feedback)

- **`agent_summary` MCP tool + `a1_at_functions/agent_summary.py`**
  (`69d4ea9`) — pure helper that returns a compact, agent-friendly
  summary of the top blockers for a given project (certify axes
  failing, wire violations, stub bodies, missing CI/CHANGELOG). Seed
  for the broader Codex-direction redesign tracked on
  `gp-codex-2-agent-plan-cards` (return action cards instead of giant
  manifests). Exposed as a 6th MCP tool alongside the W4 surface.

### Added — Codex-2 agent plan cards (`atomadic-forge.agent_plan/v1`)

- **`agent_plan/v1` schema + `forge plan` + `auto_plan` MCP tool**
  (`c7ad6d8`, Codex-2) — sister schema to the Forge Receipt, tuned for
  proposal-engine mode: returns ranked "next best action" cards
  instead of giant manifests. New a0 schema at
  `a0_qk_constants/agent_plan_schema.py`, paired emitter at
  `a1_at_functions/agent_plan_emitter.py`, CLI verb `forge plan`, and
  a new MCP tool `auto_plan` exposed alongside the W4 surface (now 7
  tools total).
- Each plan card carries: `goal`, `top_actions[]` (with `id`, `kind`,
  `why`, `write_scope`, `risk`, `commands`, `applyable`),
  `next_command`, and a verdict (PASS / REFINE / QUARANTINE / REJECT).
- Same forward-compat schema discipline as the Receipt:
  `schema_version` regex, optional fields default to `None` / `[]`,
  consumers ignore unknown fields.

### Added — Codex-3 plan apply chain (`2cafbcc`)

- **`forge plan` `--save` + `plan-list` / `plan-show` / `plan-step` /
  `plan-apply` verbs + MCP tools** — closing the proposal-engine vision
  from Codex-1/2: agent inspects an emitted plan card → accepts /
  steps / applies → Forge applies the chosen actions with rollback
  safety → state persists across runs.
- New a2 composite `a2_mo_composites/plan_store.py` — append-only plan
  store + per-card state at `.atomadic-forge/plans/<id>.[state.]json`.
  `compute_plan_id` is **content-addressed** so re-emitting a
  structurally-identical plan yields the same id (re-emit-safe).
- New a3 feature `a3_og_features/forge_plan_apply.py` —
  `apply_card` / `apply_all_applyable` orchestrators with two routes:
  - architectural F0041–F0046 → `forge enforce --apply` (rollback-safe)
  - operational F0050 (docs missing) → bounded stub README writer
  Halts on first failed / rolled_back; records every event to plan state.

### Added — Codex-4 copilot's copilot (`fa50644`)

Direct response to Codex's "Forge is the architectural control plane
*around* any agent" directive. Three pure-a1 primitives + 3 MCP tools
+ 2 CLI verbs land Forge as the **always-on senior engineer** sitting
beside any coding agent:

- **`a1_at_functions/agent_context_pack.py`** — emits
  `atomadic-forge.context_pack/v1`. The bundle an agent should load
  on first orientation: repo purpose (README → pyproject → dirname),
  pinned 5-tier law, tier_map, blockers digest, best-next-action,
  detected test commands, release gate, risky files, recent lineage,
  pinned `forge://` resources.
- **`a1_at_functions/preflight_change.py`** — emits
  `atomadic-forge.preflight/v1`. Per-file: detected_tier,
  forbidden_imports, mirror-style likely_tests, siblings_to_read,
  cross-tier warnings, scope-too-broad flag at 8 files default.
- **`a1_at_functions/patch_scorer.py`** — emits
  `atomadic-forge.patch_score/v1`. Parses unified-diff and surfaces
  architectural_risk (new upward imports), public_api_risk
  (`__init__.py` touched), release_risk (pyproject / version /
  CHANGELOG / LICENSE), test_risk (code without tests), >200-line
  blast-radius flag → `needs_human_review` boolean + suggested
  validation commands.
- **3 new MCP tools**: `context_pack`, `preflight_change`,
  `score_patch` (registered alongside the W4 / Codex-1/2/3 surface —
  **10 tools total**). All three are pure-a1 — no a3 injection
  needed; they read from reports + filesystem only.
- **`forge context-pack [target] [--json]`** — runs scout + wire +
  certify, emits the bundle. The single command an agent should run
  on first orientation.
- **`forge preflight <intent> <file...> [--scope-threshold N] [--json]`** —
  pre-edit guardrail. CLI exits 1 when write_scope too broad.
  (`score_patch` is intentionally MCP-only — diff strings are
  awkward as positional CLI args.)
- **+29 tests** at `tests/test_copilots_copilot.py` (10 context_pack /
  10 preflight / 8 score_patch / 1 mcp_protocol update). Trajectory:
  **301 → 611 passing**, 2 skipped. `forge wire` PASS at every
  commit. `forge certify .` = **100/100** held.
- Live smoke against Codex's atomadic-lang downstream: `forge
  context-pack ./atomadic-lang` returned tier_map 282 files / 0
  blockers / `release_gate: ruff && pytest && wire && certify ≥ 75`.

Companion to Codex-1 (`69d4ea9`, agent_summary), Codex-2 (`c7ad6d8`,
agent_plan), and Codex-3 (`2cafbcc`, plan-apply chain).

### Added — Codex-5 Copilot's Copilot complete + `forge --version` (`276a092`)

Closed Codex's full 12-item "Copilot's Copilot" enumeration in one
sweep on top of the 3 hero primitives shipped in Codex-4. **Eight new
pure modules + 11 new MCP tools + one production-hardening flag.**
Total live MCP surface jumped from **10 → 21 tools**.

**8 new modules** (a0 + a1 only — pure, tier-clean):

| File | Codex # | Purpose |
|---|---|---|
| `a0_qk_constants/policy_schema.py` | #10 | `atomadic-forge.policy/v1` TypedDict + sane defaults (max_files_per_patch, protected_files, release_gate, require_human_review_for) |
| `a1_at_functions/policy_loader.py` | #10 | pure `pyproject.toml [tool.forge.agent]` reader + `file_is_protected` matcher (exact + suffix) |
| `a1_at_functions/test_selector.py` | #7 | `select_tests({changed_files, intent})` → `minimum` (mirror match) + `full` (tier-mate) test sets |
| `a1_at_functions/rollback_planner.py` | #11 | `rollback_plan({changed_files})` → files-to-remove, caches, tests-to-rerun, risk_level (low/medium/high — high if a release file like pyproject / version / CHANGELOG / LICENSE is touched) |
| `a1_at_functions/agent_memory.py` | #5 | `why_did_this_change({file})` + `what_failed_last_time({area})` → queries `.atomadic-forge/lineage.jsonl` and plan-state files |
| `a1_at_functions/repo_explainer.py` | #6 | humane operational orientation card — purpose, entry-points, do-not-break list, release_state derived from wire/certify |
| `a1_at_functions/plan_adapter.py` | #8 | capability-aware card filtering — `apply` / `delegate` / `ask_human` / `report_only` based on agent capabilities (`edit_files`, `run_commands`, `network`, `review`, `delegate`) |
| `a1_at_functions/tool_composer.py` | #9 | goal-keyword → ordered tool sequence; recipe library (`orient`, `release_check`, `fix_violation`, `before_edit`, `verify_patch`) |
| `a1_at_functions/recipes.py` | #12 | golden-path recipes — `release_hardening`, `add_cli_command`, `fix_wire_violation`, `add_feature`, `publish_mcp` (each a step-by-step playbook agents can `list` / `get`) |

**11 new MCP tools** registered alongside the W4 / Codex-1..4 surface:

`select_tests`, `rollback_plan`, `explain_repo`, `adapt_plan`,
`compose_tools`, `load_policy`, `why_did_this_change`,
`what_failed_last_time`, `list_recipes`, `get_recipe`. (`score_patch`
shipped in Codex-4 was the 11th; this commit takes the running total
from 10 → 21.)

**Production hardening:**

- **`forge --version` / `forge -V`** was throwing "Try forge --help".
  Added a root callback with an `is_eager` `--version` option that
  prints `atomadic-forge X.Y.Z` and exits 0. Test pins this.
- **`forge mcp serve --help`** docstring updated to enumerate the 21
  tools + 5 resources (was 8 / 5). MCP test pins the full set.

**Tests** (+32 in `tests/test_codex_5_complete.py` + 1 update in
`tests/test_mcp_protocol.py`): 643 passing / 2 skipped (was 611).
Each new module has v1-schema, dispatch, and edge-case coverage.

**Codex's 12-item enumeration is now FULLY shipped:**

| # | Item | Where |
|---|---|---|
| 1 | First-call context pack | `context_pack` (Codex-4 / `fa50644`) |
| 2 | Preflight before edit | `preflight_change` (Codex-4 / `fa50644`) |
| 3 | Patch risk scoring | `score_patch` (Codex-4 / `fa50644`) |
| 4 | Active guardrail | composed via `preflight_change` + `score_patch` + `auto_step` (no separate verb needed) |
| 5 | Agent memory / lineage | `why_did_this_change`, `what_failed_last_time` (Codex-5) |
| 6 | Explain this repo | `explain_repo` (Codex-5) |
| 7 | Test selection | `select_tests` (Codex-5) |
| 8 | Capability-aware planning | `adapt_plan` (Codex-5) |
| 9 | MCP tool composer | `compose_tools` (Codex-5) |
| 10 | Policy as code | `load_policy` (`[tool.forge.agent]`) (Codex-5) |
| 11 | Undo plan | `rollback_plan` (Codex-5) |
| 12 | Golden-path recipes | `list_recipes` / `get_recipe` (Codex-5) |

### Added — release-bump cosmetics (`009d6d7`)

- `pyproject.toml` `version = "0.3.0"`
- Tag `v0.3.0` pushed to `origin`
- Wheel + sdist confirmed via `python -m build --no-isolation`
- README badge bumped from `0.2.2 (100/100 certify + GitHub-ready)`
  to reflect the v0.3.0 21-tool architectural-control-plane surface
  (cleanup-crew rolling).

### Added — Codex docs walkthrough (`178d020`)

- New affordances walkthrough for the Atomadic-Lang downstream agent —
  concrete `try-these` snippets covering the agent flows AGENTS_GUIDE.md
  describes, runnable end-to-end against a fresh checkout.

### Added — Golden Path Lane C W4 (forge mcp serve)

- **`forge mcp serve`** (`9f63085`, GP-C W4) — stdio JSON-RPC server
  exposing the entire Forge pipeline to any coding agent that speaks
  MCP (Cursor, Claude Code, Aider, Devin, Sweep). 5 tools (`recon`,
  `wire`, `certify`, `enforce`, `audit_list`) + 4 resources, soft-fail
  contract, tier-clean. New modules:
  `a1_at_functions/mcp_protocol.py` (pure JSON-RPC framing),
  `a3_og_features/mcp_server.py` (stdio loop), CLI verb in
  `a4_sy_orchestration/cli.py`.
- **F0042 case study** during W4 development: an a3-import sneaking
  into a1 was caught by `forge wire` mid-implementation. Fix was the
  canonical injection refactor — the enforce handler registration moved
  to a3 where it belongs. Tier discipline held by construction.
- 21 new tests at `tests/test_mcp_protocol.py` covering the JSON-RPC
  init/tools-list/shutdown round-trip + every tool's
  inputSchema/outputSchema contract.
- **Live demo on Forge itself**:
  ```
  printf '%s\n%s\n%s\n' \
    '{"jsonrpc":"2.0","id":1,"method":"initialize"}' \
    '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
    '{"jsonrpc":"2.0","id":3,"method":"shutdown"}' \
    | forge mcp serve --project .
  ```
  Returns server info, 5 tools, clean shutdown — single round-trip
  proves the surface is reachable from any MCP client.

### Fixed

- **`datetime.utcnow()` deprecation sweep** (`3359fb6`, audit-A1) —
  replaced with `datetime.now(timezone.utc)` across a3 features.
  Prerequisite for the GP P1 self-certify gate.

### Documentation

- `docs/COMMANDS.md` updated with the 5 new user-facing surfaces:
  `forge audit list/show/log`, `forge diff`, `forge wire
  --fail-on-violations`, `forge wire --suggest-repairs`,
  `forge recon --progress`.

### Notes for downstream consumers

- The Receipt schema is **forward-compatible by design** — every new
  field defaults to `None` or `[]` / `{}`. Adding a *required* field is
  a major version bump; reserved field names are documented in the
  schema docstring.
- `forge wire --fail-on-violations` is the load-bearing primitive for
  the planned `atomadictech/forge-action` GitHub Action (GP Lane C W1).
- 9 audit-lane commits + 1 GP-A W0 commit currently sit on a feature
  branch. Cut as `0.3.0-rc1` when GP-A W1 (`receipt_emitter` +
  `card_renderer`) lands.

## 0.2.2 — _Operational axis + 100/100 self-certify_

`forge certify` now scores the full 0–100 range.  The v1 rubric topped
out at 90 (35 structural + 25 runtime + 30 behavioural) with 10 points
of reserved headroom that no axis credited.  This release closes the
gap with a new **operational axis** worth 10 points total:

| Axis | Points | Check |
|---|---|---|
| CI workflow present | 5 | `.github/workflows/*.yml` (or `.yaml`) — at least one non-empty file |
| Changelog / release notes | 5 | `CHANGELOG.md` (or `.rst`, `RELEASE_NOTES.md`, `HISTORY.md`, `NEWS.md`) ≥ 200 bytes at root |

Both checks are pure structural file-existence — no API calls, no slow
runtime paths.  The CI axis credits intent (a workflow exists); the
behavioural axis already credits actual test-pass behaviour, so there's
no double-counting.

### Added

- `check_ci_workflow(root)` — pure helper at `a1_at_functions/certify_checks.py`
- `check_changelog(root)` — pure helper at the same module
- `score_components.operational` — new key in the certify result dict
- `ci_workflow_present` and `changelog_present` — new top-level booleans
  in the certify result dict
- `detail.ci` and `detail.changelog` — new entries in the detail dict
- 22 new tests in `tests/test_certify_operational_axis.py` covering both
  helpers, the integrated 100/100 path, partial-credit (CI-only,
  changelog-only), and the issue/recommendation surfacing on misses
- README badge updated from 90/100 → 100/100

### Fixed

- The `# Score weights (sum to 100):` comment in `certify_checks.py` now
  actually sums to 100 (was 90 in v0.2.1; the reserved headroom is now
  spoken for).
- Forge's own self-certify: **90 → 100**.  299 passing tests, 1
  skipped (was 274 + 1).  Wire scan: PASS, 0 violations.
- `forge demo run` now exits non-zero when the generated CLI demo fails,
  while still writing the artifact for debugging.
- `commandsmith sync` now regenerates a Ruff-clean command registry.
- `forge certify --fail-under <score>` gives CI an explicit score gate.
- Certification scans ignore `.pytest_tmp*` scratch trees and generated
  smoke tests are Ruff-clean, so local verification does not depend on
  manual cleanup order.

### Notes for downstream certify consumers

If your tooling asserts on a specific score value (e.g. `assert
result["score"] == 90`), audit it: a project with `.github/workflows/`
and `CHANGELOG.md` will now legitimately score higher than before.
The fixture-based tests in `tests/test_stub_detector.py` were
unaffected because their temp roots don't include the operational-axis
files.

## 0.2.1 — _Provider resilience + forge stress-test fixes_

Discovered and fixed during a live stress-test: using Forge itself to
absorb 23,487 symbols from five major agent frameworks (langchain,
autogen, instructor, mem0, browser-use) while running `iterate`, `evolve`,
`emergent`, `synergy`, and `commandsmith` end-to-end.  All fixes are in the
forge source; the evolution run produced `generated/tool-agent` (60/100) and
`generated/sovereign` (74/100) plus 12 registered CLI commands (12/12 smoke PASS).

### Added

- `forge chat ask` and `forge chat repl` — a Forge-aware chat copilot that
  uses the same provider layer as `iterate` / `evolve`, supports `nexus`,
  `openrouter`, `gemini`, `anthropic`, `openai`, `ollama`, and `stub`, and
  packs bounded repo context while skipping `.env` and obvious secret files.
- Deterministic Python quality phases after generation: missing docstrings
  are filled, `docs/API.md` and `docs/TESTING.md` are created, and
  `tests/test_generated_smoke.py` is added before final certification.
- `.atomadic-forge/quality.json` records the docstring/docs/tests phase
  results for every Python `iterate` / `evolve` output.
- GitHub readiness assets: CI and release workflows, Dependabot config,
  bug/feature issue forms, PR template, security policy, and source
  distribution manifest.
- Shared provider resolver used by `chat`, `demo`, `iterate`, and `evolve`
  so aliases and help text no longer drift between commands.
- CLI UX docs for chat, offline demo expectations, corrected certify scoring,
  and the actual `--provider auto` resolution order.

### Bug fixes

**Bug 1 — `forge iterate` missing `nexus` provider**
`commands/iterate.py` had no `nexus`/`aaaa-nexus` case in `_resolve_provider()`
even though `forge evolve` already supported it.  Added
`if name in ("nexus", "aaaa-nexus", "aaaa_nexus", "helix"): return AAAANexusClient()`.

**Bug 2 — `forge iterate` missing `openrouter` provider**
No OpenRouter support existed anywhere in forge.  Added `OpenRouterClient` to
`a1_at_functions/llm_client.py` (OpenRouter's OpenAI-compatible endpoint,
default model `google/gemma-3-27b-it:free`).  Added `openrouter`/`router`
cases to both `iterate` and `evolve` provider resolvers.

**Bug 3 — `forge iterate` only accepted a single `--seed`**
`seed_repo: Path | None` rejected multiple seeds.  Changed to
`seed_repo: list[Path] | None` in both `commands/iterate.py` and
`a3_og_features/forge_loop.py`.  The seed catalog is now accumulated
from all provided `--seed` paths.

**Bug 4 — OpenRouter 400 on models without system-role support**
`gemma-3-27b-it` (and similar models) return HTTP 400
`"Developer instruction is not enabled"` when a `system` role message is
sent.  `OpenRouterClient.call()` now retries with the system prompt folded
into the user message on the first such failure.

**Bug 5 — `parse_files_from_response` failed on truncated JSON arrays**
When an LLM response was cut off mid-array the balanced-bracket scanner
returned `[]`, writing 0 files.  Added a third strategy: regex-based
extraction of complete `{"path", "content"}` objects from a partial array.
Also fixed the fence regex from non-greedy to greedy capture.

**Bug 6 — Seed catalog flooded the prompt with 460 K+ symbols**
Multiple large seeds (langchain + mem0) pushed 460 K+ symbols into the
prompt, confusing the LLM.  `pack_initial_intent()` now deduplicates
method-level entries to base class names and caps the display at 30 unique
top-level symbols.

**Bug 7 — SyntaxWarning noise from third-party forged files**
mem0's regex strings used invalid escapes (`\.`), causing Python
`SyntaxWarning` on every forge command that loaded the seed catalog.  Added
`warnings.filterwarnings("ignore", category=SyntaxWarning)` at CLI import
time in `a4_sy_orchestration/cli.py`.

**Bug 8 — `commandsmith smoke` referenced non-existent `unified_cli` module**
The smoke test invoked
`atomadic_forge.a4_sy_orchestration.unified_cli` which doesn't exist.
Changed to `atomadic_forge.a4_sy_orchestration.cli`.  The current command
surface now passes smoke test (12/12 PASS).

**Bug 9 — Generated synergy adapters referenced `unified_cli`**
The synergy-implement template hardcoded `unified_cli` in subprocess calls.
Replaced with `cli` in all three generated adapter files
(`emergent_then_synergy.py`, `synergy_then_emergent.py`,
`evolve_then_iterate.py`) and registered them in `cli.py`.

**Bug 10 — `forge certify` stub scan recursed into `forged/` directories**
When certifying a project root without a `src/` directory,
`detect_stubs` ran `rglob("*.py")` on the full tree — including 17 727
stub skeletons in `forged/*/src/` — dragging the score from 60 → 20/100.
`certify_checks.py` now sets `src_for_stubs = None` and skips stub
detection entirely when there is no `src/` layout.

### New / changed modules

| File | Tier | Change |
|------|------|--------|
| `a1_at_functions/llm_client.py` | a1 | `OpenRouterClient` added; `resolve_default_client()` includes openrouter in auto-chain |
| `commands/iterate.py` | a4 | nexus + openrouter providers; multi-seed `list[Path]` |
| `commands/evolve.py` | a4 | nexus + openrouter providers |
| `a3_og_features/forge_loop.py` | a3 | multi-seed accumulation loop |
| `a1_at_functions/forge_feedback.py` | a1 | 3-strategy tolerant JSON parser; seed dedup + 30-symbol cap |
| `a4_sy_orchestration/cli.py` | a4 | SyntaxWarning suppressor; 3 new synergy adapters registered |
| `a3_og_features/commandsmith_feature.py` | a3 | smoke test CLI path fixed |
| `a1_at_functions/certify_checks.py` | a1 | stub scan scoped to `src/` only; no-src fallback skips scan |
| `commands/emergent_then_synergy.py` | a4 | new — emergent → synergy pipeline adapter |
| `commands/synergy_then_emergent.py` | a4 | new — synergy → emergent pipeline adapter |
| `commands/evolve_then_iterate.py` | a4 | new — evolve → iterate pipeline adapter |

### Provider matrix (updated)

| Provider | Cost | Env var | Default model |
|----------|------|---------|---------------|
| `gemini` | free tier | `GEMINI_API_KEY` / `GOOGLE_AI_STUDIO_KEY` | `gemini-2.5-flash` |
| `nexus` / `aaaa-nexus` | paid | `AAAA_NEXUS_API_KEY` | (Nexus default) |
| `anthropic` | paid | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-latest` |
| `openai` | paid | `OPENAI_API_KEY` | `gpt-4o-mini` |
| `openrouter` | free tier available | `OPENROUTER_API_KEY` | `google/gemma-3-27b-it:free` |
| `ollama` | free, local | `FORGE_OLLAMA=1` | `qwen2.5-coder:7b` |
| `stub` | free, offline | n/a | n/a |

---

## 0.2.0 — _Polyglot (JavaScript / TypeScript) support_

Forge is no longer Python-only. `recon`, `wire`, and `certify` now classify
JavaScript and TypeScript files into the same 5-tier monadic layout that has
always governed Python source. The same constraint substrate now answers for
Cloudflare Workers, Node back-ends, React-Native modules, and any mixed-language
repository — without adding a Node dependency to Forge itself.

### What landed

- **Polyglot file scanning.** `recon` walks `.py`, `.js`, `.mjs`, `.cjs`,
  `.jsx`, `.ts`, and `.tsx` in a single pass. `node_modules/`, `.next/`,
  `.wrangler/`, `dist/`, `build/`, `coverage/`, and `.turbo/` are skipped
  automatically.
- **Pure-Python JS parser.** ES6 `import` (named, default, namespace,
  side-effect, `import type` for TS), dynamic `import()`, and CommonJS
  `require()` (including destructured) are all parsed via regex + a
  brace-walking surface scanner. Comments and string literals are stripped
  first so a fake `import x from 'y'` inside a string never registers.
- **Tier classification for JS/TS.** Files placed inside an `aN_*` directory
  obey the law strictly. Files outside get a `suggested_tier` inferred from
  their character — a Cloudflare Worker default-`{ fetch, scheduled }` is a4,
  a class-with-state module is a2, an `export-const`-only module is a0, and so on.
- **Polyglot wire-check.** Upward-import detection works against JS specifiers
  like `"../a3_og_features/foo"` exactly as it works for Python `from`-imports.
  Each violation now carries a `language` field (`"python"` / `"javascript"`
  / `"typescript"`) so reports can group by source.
- **Polyglot certify.**
  - `tests` PASS recognises `tests/*.test.{js,mjs,jsx,cjs,ts,tsx}`,
    `*.spec.*`, and the Jest `__tests__/` convention alongside Python's
    `tests/test_*.py` and `*_test.py`.
  - Tier-layout PASS counts JS-style top-level or nested `aN_*` directories
    anywhere under the repo root, not just under `src/<pkg>/`.
  - Failure messages are now specific (e.g. *"found 2 tier directories
    (a1_at_functions, a4_sy_orchestration); need 3+"*).
- **Per-language recon output.** `forge recon` prints
  `python files: N`, `javascript files: M`, `typescript files: K`, plus a
  `primary_language` verdict and a `recommendations` list when JS/TS files
  exist outside tier directories.
- **Three static showcase demo presets.** `forge demo` now ships
  `js-counter` (clean a0..a4 JS package; wire PASS, certify 60/100 —
  the honest ceiling for a JS-only package while behavioural scoring
  remains Python-only), `js-bad-wire` (deliberately upward-imports —
  wire surfaces the violation with `language: "javascript"`), and
  `mixed-py-js` (one Python tier and one JS tier under the same root).
  These run *without an LLM* — they showcase recon/wire/certify on
  pre-built source, no API key required.

### New / changed modules (monadic tier placement)

| File | Tier | Purpose |
|------|------|---------|
| `a0_qk_constants/lang_extensions.py` | a0 (new) | Canonical `.py` / `.js` / `.mjs` / `.cjs` / `.jsx` / `.ts` / `.tsx` extension sets + `lang_for_path` lookup |
| `a1_at_functions/js_parser.py` | a1 (new) | Pure regex + brace-walker for ES6 / CommonJS imports, exports, default-object handlers (Worker shape), state signals, tier classifier, effect detector |
| `a1_at_functions/scout_walk.py` | a1 (extended) | Walks JS/TS as well as Python; per-file `suggested_tier`; per-language counts in the report |
| `a1_at_functions/wire_check.py` | a1 (extended) | Polyglot upward-import scanner; each violation carries a `language` field; `node_modules/` and `__pycache__/` skipped |
| `a1_at_functions/certify_checks.py` | a1 (extended) | `tests` and `tier_layout` checks recognise JS conventions; specific failure messages |
| `a4_sy_orchestration/cli.py` | a4 (extended) | `forge recon` prints per-language counts and detected `primary_language` |
| `a3_og_features/demo_runner.py` | a3 (extended) | `DemoPreset.kind` (`"llm"` / `"showcase"`) + `run_showcase` for static-package demos |
| `a3_og_features/demo_packages/` | a3 (new) | Source files for `js-counter`, `js-bad-wire`, `mixed-py-js` showcase presets |

### Tests

42 new tests for the JS/TS scanner (ES6 / dynamic / CommonJS imports,
TypeScript imports, comment + string-literal stripping, classifying a
`worker.js` as a4, classifying a constants module as a0, JS-only repo
recon, TypeScript counted, JS/TS upward-import detection in wire, JS
test recognition in certify, polyglot tier-layout detection, and the
specific layout-failure message), plus 20 follow-up tests for the
canonical `IGNORED_DIRS` list, the file-class taxonomy
(`source` / `documentation` / `config` / `asset` / `other`), and
nested-`docs/` / `guides/` discovery in `check_documentation`.

Total: **212 tests**, all passing.

### Atomadic recon proof point

| Repo state | Python | JavaScript | Primary | Certify |
|------------|-------:|-----------:|---------|--------:|
| Atomadic — before 0.2 | 1 | 0 (not seen) | python | 45/100 (tests FAIL) |
| Atomadic — after  0.2 | 1 | 3 | javascript | 50/100 (tests PASS via `cognition.test.js`; layout still FAIL with specific reason: "0 tier directories present") |

The remaining gap is real architecture work, not Forge limitation.

### Known limits (still honest)

- The JS parser is regex-based, not a real AST. It handles the surface
  (imports / exports / class / default-object handlers / state signals)
  the tier law cares about. JSX expressions, decorators, and exotic-shape
  TypeScript generics are silently ignored where they would not affect the
  tier verdict.
- The runtime importability check (the +25 score component for "package
  actually loads in a fresh subprocess") remains Python-only. JS/TS packages
  are scored on documentation, tests, layout, and upward-import discipline;
  the behavioural pytest gate stays a Python-side check too.
- Rust / Go support is still on the roadmap.

---

## 0.1.1 — _forge init setup wizard + forge config management_

First-run experience: new users can configure Forge in 60 seconds without
touching environment variables or config files by hand.

### New commands

- `forge init` — top-level alias for the interactive setup wizard.
- `forge config wizard` — same wizard from within the config sub-group.
- `forge config show` — print the current merged config (local > global > defaults);
  API keys are masked automatically. `--json` for scripting.
- `forge config set KEY VALUE` — set a single key in the local (or `--global`) config file;
  booleans and numbers are auto-coerced.
- `forge config test [--provider P]` — live-test the configured LLM connection and
  print status, model, and round-trip latency.

### New modules (monadic tier placement)

| File | Tier | Purpose |
|------|------|---------|
| `a0_qk_constants/config_defaults.py` | a0 | `DEFAULT_CONFIG`, `ForgeConfig` TypedDict, file-location constants |
| `a1_at_functions/config_io.py` | a1 | `load_config`, `save_config`, `merge_configs`, `validate_config`, `read_config_file` |
| `a1_at_functions/provider_detect.py` | a1 | `detect_ollama`, `list_ollama_models`, `test_provider` |
| `a3_og_features/setup_wizard.py` | a3 | `run_wizard` — 5-step interactive wizard with rich panels |
| `commands/config_cmd.py` | a4 | Typer sub-app with `wizard`, `show`, `set`, `test` sub-commands |

### Config merge priority

`local .atomadic-forge/config.json` → `global ~/.atomadic-forge/config.json` → built-in defaults.
`None` values are skipped so keys always fall through to the next layer.

### Tests

56 new tests covering:
- All default key presence and value ranges
- `save_config` / `read_config_file` round-trip and error paths
- `merge_configs` all priority combinations
- `load_config` with and without local config files
- `validate_config` valid/invalid providers, scores, and URLs
- `detect_ollama` / `test_provider` error paths (monkeypatched urllib)
- CLI smoke: `config show`, `config show --json`, `config set`, `config test --json`, `init --help`

Total: **150 tests**, all passing.

---

## 0.1.0 — _Initial cut + 6 refine cycles + breakthrough + showcase_

First public-shaped release. Forged out of `ASS-ADE-SEED` by isolating the
absorb-and-emerge wedge, then sharpened across six refine cycles into a
genuine architecture substrate for AI-generated code.

### Pipeline verbs

- `forge auto` — scout + cherry + assimilate + wire + certify in one shot.
- `forge recon` / `forge cherry` / `forge finalize` — granular workflow.
- `forge wire` — upward-import scanner.
- `forge certify` — docs/tests/layout/imports/behavior score with stub-body penalty.
- `forge doctor` — environment diagnostic.

### Code-generation verbs (LLM-driven)

- `forge iterate run` — LLM ↔ Forge 3-way constraint loop.
- `forge evolve run --auto N` — recursive self-improvement; halts on
  convergence, regression (optional), or stagnation (3 flat rounds default).
- `forge demo run --preset NAME` — one-shot launch-video verb. Presets:
  `calc`, `kv`, `slug`, all live-validated against Gemini.
- `forge feature-then-emergent` — universal pipe: any feature → emergent scan.

### Specialty verbs (lazily registered)

- `forge emergent scan` — symbol-level composition discovery.
- `forge synergy scan` / `synergy implement` — feature-pair detection +
  auto-generated adapters.
- `forge commandsmith discover/sync/wrap/smoke` — auto-register CLI
  commands across the catalog.

### Refine cycle highlights

| Cycle | Headline change | Live verification |
|-------|----------------|---------------------|
| 0.1.0 base | 5-tier law + import-linter contract; `auto`/`recon`/`cherry`/`finalize`/`wire`/`certify`/`doctor`. | 47 tests passing. |
| Refine 1 | Stub-body detector (catches `pass`, `NotImplementedError`, `# TODO`). Stagnation halt for evolve. Per-file feedback. | URL-shortener trajectory `50→50→50→50` (stuck). |
| Refine 2 | Runtime import smoke (subprocess `python -c "import <pkg>"`). Few-shot in system prompt. Retry-on-bad-parse. Score rebalance. | URL-shortener `70→70→70→85` — **converged Round 3**, runnable CLI. |
| Refine 3 | Round-0 scaffolds (pyproject + README + tests/conftest + tier inits). Tier `__init__` re-export rebuilder (idempotent, banner-gated). | URL-shortener `69→100` — **converged Round 1**. |
| Refine 4 | Validation: same model + same task, `100→100→100→100`, **but identity-function stubs gamed every check**. Score lied. | mdconv with codellama emitted `def parse(x): return x`; certify said 100. |
| Refine 5 (BREAKTHROUGH) | Behavioral pytest runner (subprocess pytest). Score weights: structural 35 + runtime 25 + behavioral 30. Per-file pytest failure callouts in feedback. | mdconv `60→60→60→60→60` — score now reflects honest behavior. Identity gaming closed. |
| Refine 6 | `forge demo` one-shot launch verb with 3 live-validated presets. | calc/kv/slug all 90/100 with Gemini in 22–72s. |
| Doc + transparency | Auto-doc synthesizer (rich READMEs from emitted symbols), append-only evolution log + transcript log. Wrong-package gameability fix (test runner now requires tests to import the requested package). | New gap caught + closed in the same session. |

### Substrate properties (now provable from the artifact alone)

- **Wire scan** — every emitted file lives in the legal tier.
- **Import smoke** — package actually loads in a fresh subprocess.
- **Behavioral pytest** — LLM's own tests must actually pass.
- **Stub detector** — `pass` / `NotImplementedError` / `# TODO` deduct.
- **Wrong-package gating** — tests that don't import the requested package
  don't credit the behavioral score.

### Per-run artifacts (auto-emitted)

Every successful run leaves under `<output>/.atomadic-forge/`:

- `EVOLVE_LOG.md` + `evolve_log.jsonl` — append-only run history.
- `lineage.jsonl` — append-only artifact provenance.
- `transcripts/run-<ts>.jsonl` — every LLM prompt + response (full transparency).
- `evolve.json` / `iterate.json` / `demo.json` / `scout.json` — per-phase
  structured reports with stable schema versions.

### LLM provider matrix

| Provider | Cost | Default model |
|----------|------|---------------|
| `gemini` | **free tier** | `gemini-2.5-flash` |
| `anthropic` | paid | `claude-3-5-sonnet-latest` |
| `openai` | paid | `gpt-4o-mini` |
| `ollama` | **free, local** | `qwen2.5-coder:7b` |
| `stub` | free, offline | n/a (deterministic) |

### Documentation

- `docs/SHOWCASE.md` — live runs + trajectories.
- `docs/LANDSCAPE.md` — comparison vs Cursor/Devin/Lovable/Bolt/Copilot.
- `docs/WHY_NOW.md` — the urgency case for the architecture substrate.
- `docs/COMMANDS.md` — full reference for all 13+ verbs.
- `docs/ROADMAP.md` — 0.2 / 0.3 / 1.0 milestones.
- `docs/tutorials/01-quickstart.md` — 60-second getting-started.
- `docs/tutorials/02-your-first-package.md` — own intent string.
- `docs/tutorials/03-the-five-tier-law.md` — the architecture itself.
- `docs/tutorials/04-plug-in-llms.md` — provider matrix.
- `docs/tutorials/05-multi-repo-absorb.md` — the absorb flow.

### Known limits (honest)

- Python only — multi-language ships in 0.3.
- Auto output is bootstrapped material; integration tests + secrets +
  observability remain human responsibilities.
- No semantic merge across conflicting symbols (rename / first / last /
  fail per `--on-conflict`).
- Cryptographic certificate signing chain ships in 0.2.
- The behavioral pytest check is the strongest signal but tests authored
  by the LLM can themselves be weak; adversarial-test generation in 0.2.

### Dropped from the parent (ASS-ADE-SEED)

- `chat`, `voice`, `agent`, `a2a` → moving to Atomadic Assistant.
- `pay`, `wallet`, `vrf`, `defi`, `mev`, `vanguard`, `aegis`, `bitnet`
  → stay in AAAA-Nexus.
- `discord`, `hello`, `heartbeat` → infrastructure, not Forge surface.

### Test counts

- 90+ pytest tests, all passing.
- All scenarios live-validated end-to-end against ollama (codellama:7b)
  and Google Gemini 2.5 Flash on free tier.
