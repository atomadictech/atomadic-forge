# Atomadic Forge — Agents Guide

> **For agents *using* Forge — Cursor, Claude Code, Aider, Devin, Sweep,
> custom MCP clients.** This is the user-facing complement to the
> root-level [`AGENTS.md`](../AGENTS.md), which is for agents *building*
> Forge. Use this file when you want to consume Forge's normative
> architectural law from an agent platform.

---

## What Forge gives an agent that other tools don't

Most coding-agent platforms read code (RAG, repo-map, tree-sitter) and
write code (LLM emits a diff). Forge fills the gap between:

| Other tools answer | Forge answers |
|---|---|
| "what does this code do?" | "where does this code *belong*?" |
| "find all uses of X" | "which tier does X live in, and which tiers may import it?" |
| "is this test passing?" | "is this codebase **architecturally coherent** at the score Forge would publish?" |
| (post-hoc) "what's wrong with this PR?" | (predictive) "before you generate, here's the tier this file should land in" |

Forge is **normative, predictive, attested, polyglot.** That's the
4-axis differentiation. No other tool today combines all four.

---

## The 30-second integration

Add Forge to your MCP client config (Claude Desktop / Cursor /
Claude Code / Aider / your own):

```json
{
  "mcpServers": {
    "atomadic-forge": {
      "command": "forge",
      "args": ["mcp", "serve", "--project", "."],
      "transport": "stdio"
    }
  }
}
```

Once registered, the agent gets **24 tools** + **5 resources** in its
tool list. No
additional setup.

Smoke test that the server is reachable:

```bash
forge mcp doctor --project . --json
```

Returns Forge version, tool count, framed-stdio status, and the next
recovery command if the MCP host needs a restart.
Or against the installed CLI:

```bash
$ forge --version
atomadic-forge 0.5.3
```

The `--version` flag (and `-V`) is the canonical "Forge is wired in
correctly" smoke check — pin it in your setup scripts.

---

## The 23 MCP tools — by phase of an agent's lifecycle

| Inventory (read-only) | Action loop | Copilot's Copilot |
|---|---|---|
| `recon` | `auto_plan` | `context_pack` |
| `wire` | `auto_step` | `preflight_change` |
| `certify` | `auto_apply` | `score_patch` |
| `enforce` |  | `select_tests` |
| `audit_list` |  | `rollback_plan` |
| `agent_summary` |  | `explain_repo` |
|  |  | `adapt_plan` |
|  |  | `compose_tools` |
|  |  | `load_policy` |
|  |  | `why_did_this_change` |
|  |  | `what_failed_last_time` |
|  |  | `list_recipes` |
|  |  | `get_recipe` |
|  |  | `trust_gate_response` |
|  |  | `exported_api_check` |

**Inventory tools — read-only state queries.** Cheap; safe to call
in a loop:

| Tool | Returns | Call when |
|---|---|---|
| **`recon`** | tier + symbol distribution + per-language counts | First step on any unfamiliar repo. |
| **`wire`** | upward-import violations with F-codes | Before *every* edit that crosses tier boundaries. |
| **`certify`** | 0–100 score with structural / runtime / behavioral / operational breakdown | After a multi-file change, before commit. |
| **`enforce`** | F-code-routed mechanical fixes (with rollback) | When `wire` returns auto-fixable violations. |
| **`audit_list`** | recent lineage entries with cycle-id + verdict + score | When you need historical replay context. |
| **`agent_summary`** ← *Codex-1* | compact blocker summary | Start of an "improve this repo" loop. |

**Action-loop tools — propose / inspect / apply.** Implements the
proposal-engine pattern; agent stays in the loop:

| Tool | Returns | Call when |
|---|---|---|
| **`auto_plan`** ← *Codex-2* | full `agent_plan/v1` card with ranked `top_actions[]` (`write_scope`, `risk`, `commands`, `applyable`, `next_command`) | You want Forge to rank what to fix. |
| **`auto_step`** ← *Codex-3* | accept / reject / skip a single card; returns updated plan-state | You're walking a saved plan one card at a time. |
| **`auto_apply`** ← *Codex-3* | applies every `applyable` accepted card with rollback safety | You've vetted the plan and want one-shot execution. |

**Copilot's-Copilot tools — Codex-4 + Codex-5.** Forge becomes the
always-on senior engineer beside the coding agent:

| Tool | Schema | Call when |
|---|---|---|
| **`context_pack`** ← *Codex-4* | `context_pack/v1` — repo purpose, pinned 5-tier law, tier_map, blockers digest, best-next-action, detected test commands, release gate, risky files, recent lineage, pinned `forge://` resources | **First call after `initialize`** — orientation bundle. One round-trip replaces 6+ separate calls. |
| **`worktree_status`** | `worktree_status/v1` — git root, branch, upstream drift, dirty files, remotes, version surfaces, resolved `forge` command, stale-command detection, recommendations | **Before editing or release work** when there are multiple checkouts, stale MCP concerns, dirty trees, or version mismatches. |
| **`preflight_change`** ← *Codex-4* | `preflight/v1` — per file: detected_tier, forbidden_imports, likely_tests, siblings_to_read; overall write_scope_too_broad flag | **Before** every `WriteFile` / `Edit`. Verdict `REFINE` when scope > 8 files. |
| **`score_patch`** ← *Codex-4* | `patch_score/v1` — architectural_risk, public_api_risk, release_risk, test_risk, `needs_human_review`, suggested validation commands | **After** drafting a unified-diff but **before** applying. |
| **`select_tests`** ← *Codex-5* | `test_select/v1` — `minimum_set` (mirror match) + `full_set` (tier-mate) | "Which tests must I run for this change?" — feeds into the agent's iteration loop. |
| **`rollback_plan`** ← *Codex-5* | `rollback/v1` — files-to-remove, caches, tests-to-rerun, `risk_level` | "If I have to undo this patch, how?" `risk_level=high` when release files (`pyproject` / `CHANGELOG` / `LICENSE`) were touched. |
| **`explain_repo`** ← *Codex-5* | `explain/v1` — purpose, entry-points, do-not-break list, `release_state` (READY / BLOCKED) | Humane orientation card — same data as `context_pack` but human-readable summary. |
| **`adapt_plan`** ← *Codex-5* | `agent_plan_adapted/v1` — each card decorated with `recommended_handling`: `apply` / `delegate` / `ask_human` / `report_only` | "Filter this plan for *my* capabilities." Pass `agent_capabilities` in (`edit_files` / `run_commands` / `network` / `review` / `delegate`). |
| **`compose_tools`** ← *Codex-5* | ordered tool sequence | Goal-keyword → tool list. Recipes: `orient`, `release_check`, `fix_violation`, `before_edit`, `verify_patch`. |
| **`load_policy`** ← *Codex-5* | `policy/v1` from `pyproject.toml [tool.forge.agent]` | First-orientation. Tells you the repo's `protected_files`, `release_gate`, `max_files_per_patch`, `require_human_review_for`. Defaults are lenient when no policy declared. |
| **`why_did_this_change`** ← *Codex-5* | `why/v1` — lineage + plan-event entries referencing a file | "Why did this file get touched, historically?" |
| **`what_failed_last_time`** ← *Codex-5* | `what_failed/v1` — historical failures scoped to an area | "What went wrong here before — so I don't repeat it?" |
| **`list_recipes`** ← *Codex-5* | catalogue of golden-path recipes | First-orientation. Pre-baked: `release_hardening`, `add_cli_command`, `fix_wire_violation`, `add_feature`, `bump_version`, `fix_test_detection`, `publish_mcp`. |
| **`get_recipe`** ← *Codex-5* | `recipe/v1` — step-by-step plan | "Walk me through `release_hardening` step by step." |
| **`trust_gate_response`** | `trust_gate/v1` — response hallucination checks | Before sending generated implementation notes or code snippets back to a human. |
| **`exported_api_check`** | `exported_api_check/v1` — docstring/API promise verification | Before publishing generated modules that claim public functions in docs. |

Every `tools/list` entry includes a `cli_command` fallback. If the MCP
transport drops, use that command shape directly in the shell while
you restart the editor or MCP host. `tools/list` also includes the
Forge version and server source path so agents can detect stale MCP
hosts.

(Plus four `plan_list` / `plan_show` / `plan_step` / `plan_apply`
verbs from Codex-3 — same 1:1 mapping to the CLI verbs of the same
name.)

**Three integration tiers, by depth of coupling:**

1. **Lightweight (3 tools)**: `context_pack` once for orientation,
   then `wire` + `certify` before commit. Drop-in for any platform.
2. **Predictive (8 tools)**: add `load_policy` + `select_tests` on
   orientation; `preflight_change` *before* every write;
   `score_patch` *after* drafting the diff. Forge is the always-on
   senior engineer reviewing each step.
3. **Proposal-engine (full 24 tools)**: `auto_plan` for direction,
   `adapt_plan` for capability-aware filtering, `auto_apply` to
   execute, `enforce` for mechanical fixes, `rollback_plan` if
   anything regresses, `why_did_this_change` /
   `what_failed_last_time` for historical context. Forge drives;
   the agent supplies LLM context where Forge can't mechanize.

`context_pack`, `preflight_change`, `select_tests`, and `score_patch`
are language-aware as of `0.5.2`: JavaScript projects with
`package.json` scripts get `npm run verify` / `npm test`, tier wire
commands are derived from real tier roots, and documentation paths
such as `docs/`, `research/`, `.github/`, and `cognition/guides/` are
treated as non-code artifacts rather than misplaced source.

---

## The 5 MCP resources

| Resource URI | What it is | Use case |
|---|---|---|
| `forge://docs/receipt` | The Receipt schema spec | Agent reads this to know what the Receipt JSON contract is. |
| `forge://docs/formalization` | Citations to `aethel-nexus-proofs` (29 theorems / 0 sorry) and `mhed-toe-codex-v22` (538 theorems / 0 sorry) | Agent presenting Forge to a regulator: cite the proof corpus. |
| `forge://lineage/chain` | Episodic L1 trace of every Forge run | Replay / debugging / audit. |
| `forge://schema/receipt` | Machine-readable JSON Schema for the Receipt | Agent doing type-checked Receipt parsing. |
| `forge://summary/blockers` | Same payload as `agent_summary` MCP tool | One-shot `resources/read` for clients that prefer resources over tools. |

The `attestation/{id}` resource is the **convergence point** of the
BEP-1 architecture: same Receipt JSON the agent gets here is what
the terminal Card prints, what the GitHub Action posts to the PR, and
what the Conformity Statement CS-1 PDF wraps. *One artifact, five
surfaces.*

---

## In-editor surface — `forge lsp serve` (Lane D W12)

When the agent is **co-driving with a human in an editor** (Cursor,
VS Code, Neovim, Helix, IntelliJ), MCP isn't the right surface for
sidecar feedback — it should land where the cursor is. Forge ships
an **LSP server** for that:

```bash
forge lsp serve   # speaks stdio JSON-RPC, LSP-spec-compliant
```

What the agent gets through the LSP surface:

- **`textDocument/publishDiagnostics`** — every sidecar drift
  finding from `sidecar_validator` published with its **F0100-F0106
  code**, so an agent reading the editor's "Problems" panel can
  route fixes through the same F-code namespace it already uses for
  wire violations and certify failures.
- **`textDocument/hover`** — markdown summary of the cursor's
  symbol (effect, tier, `compose_with`, `proves`).
- **`textDocument/definition`** — goto-source: `name: login` line
  in `foo.py.forge` jumps to `foo.py:login`.

VS Code + Neovim drop-in snippets are in
[`docs/COMMANDS.md`](COMMANDS.md) under `forge lsp serve`. The
packaged VS Code extension lives in its own repository
(`atomadic-forge-vscode-ext`); a JetBrains plugin is roadmap.

This is the third axis of agent integration — alongside the MCP
tool surface and the Receipt JSON wire format. **Coding agents
that wrap a real editor (Cursor, Continue, Aider) should consume
both the MCP surface AND the LSP surface** — MCP for the action
loop, LSP for the in-line drift feedback as the human types.

---

## The Forge Receipt — what it tells you

When an agent calls `certify` (or follows `forge auto`), it gets a
**Forge Receipt** back. Schema documented in [`docs/RECEIPT.md`](RECEIPT.md);
key fields the agent should read:

```json
{
  "schema_version": "atomadic-forge.receipt/v1",
  "verdict": "PASS | FAIL | REFINE | QUARANTINE",
  "certify": {
    "score": 100,
    "components": { "structural": 35, "runtime": 25, "behavioral": 30, "operational": 10 }
  },
  "wire": { "verdict": "PASS", "violation_count": 0, "auto_fixable": 0 },
  "scout": { "tier_distribution": { "a0": 14, "a1": 258, ... } },
  "signatures": { "aaaa_nexus": { ... } },
  "lean4_attestation": { "corpora": [...] },
  "lineage": { "lineage_path": "..." }
}
```

**Decision rules for the agent**:

- `verdict == "PASS"` → safe to commit / merge
- `verdict == "FAIL"` → at least one structural gate failed; check `certify.issues`
- `verdict == "REFINE"` → in flight; re-run after the next change
- `verdict == "QUARANTINE"` → human audit needed; do not auto-merge

If `signatures.aaaa_nexus` is populated, the Receipt is **signed by
AAAA-Nexus** — the agent can present it to a downstream consumer
(another agent, a regulator, a CI gate) as proof of structural
conformance.

---

## F-codes — the citeable error catalog

Every error Forge surfaces carries a stable 4-digit code. Agents
should pivot, dashboard, and route on these — never on the message
strings (those can change per locale).

| Range | Domain | Most common |
|---|---|---|
| F0001–F0009 | scout / classification | F0001 unclassifiable symbol |
| F0010–F0019 | cherry-pick | F0011 ambiguous qualname |
| F0040–F0049 | wire / upward-import | **F0042 a1 imports from a3+** ← most common |
| F0050–F0059 | certify axis failures | F0050 missing README, F0051 no tests |
| F0060–F0069 | stub detection | F0061 `pass`-only function body |
| F0070–F0079 | import-repair | F0070 conflicting move-target |
| F0080–F0089 | assimilate conflicts | F0081 colliding qualnames |
| F0090–F0099 | receipt / signing | F0091 AAAA-Nexus signing 4xx |

**`forge enforce` routes mechanical fixes by F-code.** When `wire`
returns auto-fixable F-codes, the agent can either:

1. Hand them to `enforce` for automatic resolution (rollback-safe), or
2. Read the suggested repair and apply it itself (preferred when the
   agent's broader context implies a different fix shape).

Either way, the F-code is the contract.

---

## Common agent flows

### Flow 1 — "Improve this repo" (the highest-leverage entry point)

```
agent: agent_summary({ "project": "." })
forge: { "verdict": "REFINE", "top_issues": [
          { "f_code": "F0050", "summary": "README.md is short", "auto_fixable": false, "fix_hint": "..." },
          { "f_code": "F0042", "summary": "a1_at_functions/foo.py imports a3_og_features.bar",
            "auto_fixable": true, "next_command": "forge enforce src/ --f-codes F0042" }
        ], "next_command": "forge enforce src/ --f-codes F0042 --apply" }
agent: enforce({ "scope": "src/", "f_codes": ["F0042"], "apply": true })
forge: { "applied": 1, "rollback": "...", "new_receipt": { ... certify.score: 92 → 95 ... } }
```

### Flow 2 — "Generate code that lands in the right tier"

```
agent: needs to add a new feature; calls wire on a hypothetical placement first
agent: wire({ "scope": "src/", "include_proposed": "src/a1_at_functions/new_helper.py" })
forge: { "verdict": "PASS", "tier_recommendation": "a1_at_functions" }
agent: writes the file knowing it will pass wire BEFORE the LLM emits
```

### Flow 3 — "Verify before merge"

```
agent: certify({ "project": ".", "package": "atomadic_forge" })
forge: { "score": 100, "verdict": "PASS", "signatures": { "aaaa_nexus": {...} } }
agent: PR description includes Receipt's lineage_path + score
human: merges with confidence; the Receipt provenance survives in lineage.jsonl
```

---

## Receipt-as-PR-comment (consume it from the agent)

When the agent calls `certify`, the Receipt JSON is the agent's
deliverable for the PR description / sticky comment. A typical
agent-emitted PR comment:

```
**Forge** · 100/100 · Δ +5 vs main
- a0 14 · a1 258 · a2 58 · a3 52 · a4 14
- wire 0 · stub 0 · Lean4 ✓ · AAAA-Nexus signed nx-7f3…
- Reproduce: `forge certify . --pr ${{ github.event.pull_request.number }}`
```

This is what the [`atomadictech/forge-action`](https://github.com/atomadictech/forge-action)
GitHub Action emits automatically when installed. Agents using Forge
locally can produce the same artifact.

---

## Soft-fail contract — Forge is always usable

Forge composes AAAA-Nexus's safety primitives but **never throws** on
upstream failure. Examples the agent should expect:

| Upstream | Behavior |
|---|---|
| `AAAA_NEXUS_API_KEY` unset | Receipt is structurally valid; `signatures` is null; `note` says `"key not set"` |
| AAAA-Nexus 4xx (auth / rate / endpoint not shipped) | unsigned + endpoint cached unavailable for the run |
| AAAA-Nexus 5xx / network error | unsigned + retry note |
| AAAA-Nexus 200 | Receipt's `signatures.aaaa_nexus` populated |
| Lean4 corpus unreachable | `lean4_attestation` is null; `note` cites the corpus URL |

**Unsigned-but-structurally-valid is always the fallback.** This means
local-development agents (no network, no API key) can still consume
Forge's normative answer; only the *attestation chain* is missing.

---

## Best practices for agent integrations

1. **Call `agent_summary` first**, not `recon`/`certify`/`wire` separately. It pre-merges the queue.
2. **Cache `recon` output** — it's cheap to compute but pure. The Receipt's `lineage_path` lets the agent confirm the cache is valid.
3. **Pivot on F-codes**, never error message strings.
4. **Read `signatures`, `lean4_attestation`, `lineage`** before claiming "Forge approved" externally.
5. **Use `enforce` for F-codes you don't have context to fix** — it's rollback-safe.
6. **Surface the Receipt to humans** when relevant (PR comments, CI logs, error dialogs).
7. **Never compose your own architectural rules** — read `forge://arch/law` and respect what Forge says.

---

## Common gotchas

| Symptom | Likely cause | Fix |
|---|---|---|
| Tools list returns 0 tools | MCP client didn't pass `--project .` | Check args in MCP config |
| Tools list returns < 23 (e.g. 21 or 10) | Old `forge` install | `pip install -U atomadic-forge` (or `pip install -e .` from the repo). Pin `forge --version >= 0.5.3`. |
| `wire` says PASS but agent still hits import errors | Agent is running tests in a different working directory | `--project` should match the test cwd |
| `certify` returns score 90 instead of 100 | Project has no `.github/workflows/` and no `CHANGELOG.md` (operational axis is 0) | Add either; both are 5pts |
| Receipt's `signatures` is null | `AAAA_NEXUS_API_KEY` not set, or AAAA-Nexus endpoint not yet shipped | Soft-fail behavior — Receipt is still valid for local use |
| F0042 keeps re-firing after `enforce` | The agent is generating new upward imports faster than enforce can fix | The agent's prompt template needs the tier-map context (read `forge://arch/law` first) — or call `preflight_change` *before* every write |
| `preflight` returns `write_scope_too_broad: true` constantly | Agent intent is too coarse-grained, OR the repo declares `[tool.forge.agent].max_files_per_patch < 8` (Codex-6) | Split the intent into smaller atomic intents, or raise `--scope-threshold`. Read `load_policy` first to see what the repo allows. |
| `score_patch` returns `needs_human_review` on every diff | Diffs touch `__init__.py` or pyproject reflexively, OR a path matched `[tool.forge.agent].protected_files` (Codex-6) | Strip those edits into a dedicated commit. Or call `load_policy` first to know what's protected. |
| `preflight` flags every file in a perfectly-sized patch as "request human review" | One of the proposed files matched `protected_files` in the repo's policy | This is intentional — `protected_files` are the social contract. Surface to the human reviewer instead of auto-applying. |

---

## Now shipped — proposal-engine + copilot's-copilot (Codex-2/3/4)

`atomadic-forge.agent_plan/v1` shipped at master (`c7ad6d8`) — sister
schema to the Receipt, optimized for proposal-engine mode. Agents get:

- **`forge plan`** — emits a ranked `agent_plan/v1` JSON card to stdout
- **`auto_plan` MCP tool** — same shape returned via the MCP server
  (the 7th tool in the server's `tools/list`)
- **Action cards** — small JSON objects the agent can inspect, edit,
  and apply with explicit `write_scope`, `risk`, `commands`, and
  `applyable` flags

Schema doc: see the `atomadic-forge.agent_plan/v1` block in
`a0_qk_constants/agent_plan_schema.py` (and the matching narrative in
`docs/COMMANDS.md` under `forge plan`).

### Now shipped — Codex-3 plan apply chain

Codex-3 closed the plan loop at master (`2cafbcc`):

- **`forge plan --save`** — persists a plan to
  `.atomadic-forge/plans/<id>.json` (append-only).
- **`forge plan-list`** — lists every saved plan with status counts.
- **`forge plan-show <id>`** — prints a saved plan's cards + per-card
  state (`pending` / `applied` / `rejected` / `skipped`).
- **`forge plan-step <id> <card_id> --accept|--reject|--skip`** —
  marks a single card and writes a sidecar `.state.json`.
- **`forge plan-apply <id>`** — executes every `applyable` accepted
  card. Routing:
  - `F0041`–`F0046` (architectural / wire) → `forge enforce --apply`
    (rollback-safe, AST-driven).
  - `F0050` (docs missing) → bounded stub README writer.
- **MCP tools** — `plan_list`, `plan_show`, `plan_step`, `plan_apply`
  match the CLI verbs one-for-one.

Implementation lives in:
- `a2_mo_composites/plan_store.py` — append-only plan + state store
- `a3_og_features/forge_plan_apply.py` — `apply_card` /
  `apply_all_applyable` orchestrators

### Now shipped — Codex-4 copilot's copilot (`fa50644`)

Three pure-a1 primitives that turn Forge into the **architectural
control plane around any coding agent**:

- **`context_pack`** (CLI: `forge context-pack`, MCP: `context_pack`) —
  the orientation bundle the agent loads on first contact with a
  repo. One call, one JSON, ten baseline fields (purpose / law /
  tier_map / blockers / next-action / test-commands / release-gate /
  risky-files / lineage / pinned resources). When the task is already
  known, call it with `focus`, `intent`, and `files` to get targeted
  file context, preflight, selected tests, and suggested next steps in
  the same payload.
- **`preflight_change`** (CLI: `forge preflight`, MCP: `preflight_change`)
  — pre-edit guardrail. Per file: tier detected, tiers forbidden,
  likely tests, siblings to read. Returns `write_scope_too_broad =
  true` when the agent's intent fans out across more than 8 files
  (configurable). CLI exits 1 in that case so a pre-commit hook can
  block.
- **`score_patch`** (CLI: `forge score-patch`, MCP: `score_patch`) — diff-level risk
  preview. Given a unified-diff string, surfaces architectural_risk
  (new upward imports), public_api_risk (`__init__.py` touched),
  release_risk (pyproject / version / CHANGELOG / LICENSE), test_risk
  (code without tests), >200-line blast-radius flag → composite
  `needs_human_review` boolean + suggested validation commands.

Implementation lives in three pure-a1 modules (no a3 injection
needed; they read from reports + filesystem only):

- `a1_at_functions/agent_context_pack.py`
- `a1_at_functions/preflight_change.py`
- `a1_at_functions/patch_scorer.py`

Tests: 611 passing (was 582 before Codex-4; +29 net). `forge wire`
PASS at every commit, `forge certify .` = 100/100 held.

Watch [CHANGELOG.md](../CHANGELOG.md) for the next round.

---

## Quick reference

```bash
# Smoke
forge mcp serve --project .

# One-shot summary
forge mcp serve --project . <<< '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"agent_summary","arguments":{}}}'

# Reproduce a Receipt
forge certify . --emit-receipt out.json --sign

# Print the Forge Card (paste-ready for PRs / chat)
forge certify . --print-card
```

| What | Where |
|---|---|
| Schema for the Receipt | [`docs/RECEIPT.md`](RECEIPT.md) |
| All commands | [`docs/COMMANDS.md`](COMMANDS.md) |
| Agents *building* Forge (dev contract) | [`AGENTS.md`](../AGENTS.md) |
| First-10-minutes onboarding | [`docs/FIRST_10_MINUTES.md`](FIRST_10_MINUTES.md) |
| Strategic landscape | [`docs/LANDSCAPE.md`](LANDSCAPE.md) |
| **This guide** | `docs/AGENTS_GUIDE.md` (you are here) |

---

*Atomadic Forge. Absorb. Enforce. Emerge. Tier-clean by construction.*
