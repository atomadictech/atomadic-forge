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

Once registered, the agent gets **10 tools** + **4 resources** in its
tool list (after Codex-1..4 shipped). No additional setup.

Smoke test that the server is reachable:

```bash
printf '%s\n%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  '{"jsonrpc":"2.0","id":3,"method":"shutdown"}' \
  | forge mcp serve --project .
```

→ returns `serverInfo`, the 10 tool schemas (plus 4 `plan_*` verbs
when Codex-3 surface is queried), and `{}` for shutdown.

---

## The 10 MCP tools

| Tool | Returns | When the agent should call it |
|---|---|---|
| **`recon`** | tier + symbol distribution + per-language counts | First step of any agent action on an unfamiliar repo. Cheap, cached. |
| **`wire`** | upward-import violations with F-codes | Before *every* `WriteFile` / `Edit` that crosses tier boundaries. |
| **`certify`** | 0–100 score with structural / runtime / behavioral / operational breakdown | After a multi-file change, before deciding to commit. |
| **`enforce`** | F-code-routed mechanical fixes (with rollback) | When `wire` returns auto-fixable violations and the agent wants Forge to apply them. |
| **`audit_list`** | recent lineage entries with cycle-id + verdict + score | When the agent needs to see what changed historically (replay context). |
| **`agent_summary`** ← *Codex-1* | compact blocker summary (top issues, applyable fixes, validation commands) | At the start of any "improve this repo" loop. Returns a small JSON the agent can act on directly. |
| **`auto_plan`** ← *Codex-2* | a full `agent_plan/v1` card: ranked `top_actions[]` with `write_scope`, `risk`, `commands`, `applyable`, plus a `next_command` | When the agent wants Forge in **proposal-engine mode** — Forge ranks what to fix, the agent picks one, applies via `forge plan-apply`, re-plans. |
| **`context_pack`** ← *Codex-4* | `context_pack/v1` — repo purpose, pinned 5-tier law, tier_map, blockers digest, best-next-action, detected test commands, release gate, risky files, recent lineage, pinned `forge://` resources | **First call after `initialize`** — the agent's orientation bundle. Replaces 6+ separate calls with one round-trip. |
| **`preflight_change`** ← *Codex-4* | `preflight/v1` — per file: detected_tier, forbidden_imports, likely_tests, siblings_to_read; overall write_scope_too_broad flag | **Before** the agent emits any `WriteFile` / `Edit` — pre-edit guardrail. Verdict `REFINE` when scope > threshold. |
| **`score_patch`** ← *Codex-4* | `patch_score/v1` — architectural_risk (new upward imports), public_api_risk (`__init__.py`), release_risk (pyproject / version / CHANGELOG), test_risk, `needs_human_review` boolean, suggested validation commands | **After** the agent drafts a unified-diff but **before** applying it — diff-level risk preview. |

(Plus four `plan_list` / `plan_show` / `plan_step` / `plan_apply`
verbs from Codex-3 — same 1:1 mapping to the CLI verbs of the same
name.)

**Three integration tiers, by depth of coupling:**

1. **Lightweight**: agent calls `context_pack` once for orientation,
   then `wire` + `certify` before commit. Drop-in for any platform.
2. **Predictive**: agent adds `preflight_change` *before* every
   write and `score_patch` *after* drafting the diff *before*
   applying. Forge becomes the always-on senior engineer reviewing
   each step.
3. **Proposal-engine**: agent calls `auto_plan` for direction,
   `plan_apply` to execute, `enforce` for mechanical fixes. Forge
   drives; the agent supplies LLM context where Forge can't
   mechanize.

---

## The 4 MCP resources

| Resource URI | What it is | Use case |
|---|---|---|
| `forge://arch/tier-map` | Canonical normative tier graph (a0..a4 + allowed imports) | Agent's "what does this codebase claim to be?" reference |
| `forge://arch/law` | Declarative L3 rules (forbidden imports, naming conventions, effect lattice) | Pre-flight before the agent generates code |
| `forge://arch/lineage.jsonl` | Episodic L1 trace of every Forge run | Replay / debugging / audit |
| `forge://arch/attestation/{verdict_id}` | Signed Forge Receipt for a specific run | Provenance for a regulator or downstream consumer |

The `attestation/{id}` resource is the **convergence point** of the
BEP-1 architecture: same Receipt JSON the agent gets here is what
the terminal Card prints, what the GitHub Action posts to the PR, and
what the Conformity Statement CS-1 PDF wraps. *One artifact, five
surfaces.*

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
| Tools list returns 6 not 10 | Old `forge` install (pre-Codex-4) | `pip install -U atomadic-forge` (or `pip install -e .` from the repo) |
| `wire` says PASS but agent still hits import errors | Agent is running tests in a different working directory | `--project` should match the test cwd |
| `certify` returns score 90 instead of 100 | Project has no `.github/workflows/` and no `CHANGELOG.md` (operational axis is 0) | Add either; both are 5pts |
| Receipt's `signatures` is null | `AAAA_NEXUS_API_KEY` not set, or AAAA-Nexus endpoint not yet shipped | Soft-fail behavior — Receipt is still valid for local use |
| F0042 keeps re-firing after `enforce` | The agent is generating new upward imports faster than enforce can fix | The agent's prompt template needs the tier-map context (read `forge://arch/law` first) — or call `preflight_change` *before* every write |
| `preflight` returns `write_scope_too_broad: true` constantly | Agent intent is too coarse-grained | Split the intent into smaller atomic intents, or raise `--scope-threshold` if the work genuinely is wide |
| `score_patch` returns `needs_human_review` on every diff | Diffs touch `__init__.py` or pyproject reflexively | Strip those edits into a dedicated commit; the rest of the diff will score clean |

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
  repo. One call, one JSON, ten fields (purpose / law / tier_map /
  blockers / next-action / test-commands / release-gate / risky-files
  / lineage / pinned resources).
- **`preflight_change`** (CLI: `forge preflight`, MCP: `preflight_change`)
  — pre-edit guardrail. Per file: tier detected, tiers forbidden,
  likely tests, siblings to read. Returns `write_scope_too_broad =
  true` when the agent's intent fans out across more than 8 files
  (configurable). CLI exits 1 in that case so a pre-commit hook can
  block.
- **`score_patch`** (MCP-only: `score_patch`) — diff-level risk
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
