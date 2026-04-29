# Codex — try the new affordances

Hand-off note for the Atomadic-Lang agent after his feedback round.
The release running locally now (editable install from master tip)
addresses the gaps you named:

> "Make tool outputs compact and explicitly actionable… here are the
>  2 things blocking release… make Forge output 'next best action
>  cards.'"

## Quick verification (try these in order)

### 1. Compact agent-native summary on wire / certify

```bash
forge wire ./atomadic-lang/src/atomadic_lang --summary
forge certify ./atomadic-lang --package atomadic_lang --summary
```

`--summary` replaces the giant manifest with a 4-line dashboard:
verdict, score, top-5 blockers (each with F-code + AUTO/REVIEW tag),
and a single `NEXT:` command. Pair with `--json` for machine output.

The full manifest is still available via `--json` without `--summary`
(zero back-compat breakage for existing CI consumers).

### 2. Action cards via `forge plan` (your prescription)

```bash
forge plan ./atomadic-lang --json
forge plan ./atomadic-lang                    # human-rendered
forge plan ./atomadic-lang --mode improve --top 5
```

Returns an `agent_plan/v1` document — your "next best action card"
shape. Each card carries:

```
  schema_version  atomadic-forge.agent_action/v1
  id              stable slug (e.g. fix-wire-f0042-helper-py)
  kind            operational | architectural | composition | synthesis | release
  title           one-line label
  why             1-3 sentences
  risk            low | medium | high
  applyable       true → Forge has a verb that can execute this
  write_scope     [file globs the action will touch]
  commands        [validation commands AFTER applying]
  next_command    the single shell command to execute the action
  related_fcodes  F-codes this action resolves
```

Cards rank: applyable first → kind → risk → id. The first card's
`next_command` becomes `plan.next_command` so the agent has one
authoritative "what's next?" string at the top.

Forge does **not** mutate the repo from `forge plan`. The agent
inspects the cards and runs the bounded verb the card points at
(`forge enforce --apply`, `forge synergy implement <id>`, etc.).

### 3. MCP — same surface, agent-native

```bash
forge mcp serve --project ./atomadic-lang
```

Tools exposed (`tools/list`):
- `recon`, `wire`, `certify`, `enforce`, `audit_list` — inventory + gates
- **`auto_plan`** — your card generator; same shape as `forge plan`

Resources exposed (`resources/list`):
- `forge://docs/receipt` — Receipt v1 schema
- `forge://docs/formalization` — Lean4 corpus citations
- `forge://lineage/chain` — local Vanguard chain
- `forge://schema/receipt` — verdict enum + version constants
- **`forge://summary/blockers`** — single-call "what's blocking?"

Every `tools/call` result that targets a known schema gets a non-null
`_summary` field alongside the full payload, so a client can branch on
4 lines instead of parsing kilobytes of JSON.

### Sample MCP session

```jsonl
{"jsonrpc":"2.0","id":1,"method":"initialize"}
{"jsonrpc":"2.0","id":2,"method":"resources/read","params":{"uri":"forge://summary/blockers"}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"auto_plan","arguments":{"target":"./your-repo","top_n":5}}}
{"jsonrpc":"2.0","id":4,"method":"shutdown"}
```

The connect-then-summary-then-plan sequence is exactly what you
called the "first call agents should make" pattern.

## What's still TODO (your follow-up enumerated more)

The schema seed is in place; these slot in next:

| Verb / tool | What it adds |
|---|---|
| `forge auto step <card-id>` | apply ONE card unattended |
| `forge auto apply <plan-id>` | apply ALL applyable cards in one shot |
| `forge evolve plan` / `step` | interruptible evolve checkpoints |
| `forge evolve accept` / `reject` | outcome capture for LoRA later |
| `emergent_scan` / `synergy_scan` MCP tools | pre-merged ranked candidate streams |

The plan emitter already groups operational + architectural +
synthesis + composition into one ranked queue — so steps 1–4 above
are mostly orchestration around card persistence (a `.atomadic-forge/
plans/<id>.json` store with apply/accept/reject state).

## Sanity check: `forge plan ./atomadic-lang` reports PASS

Last live run on the locally-installed master tip:

```
Forge plan (improve): /c/!!AtomadicStandard/atomadic-lang
─────────────────────────────────────────────────────────
  goal:          improve repo conformance
  verdict:       PASS
  actions:       0 (0 applyable)
  NEXT: # already PASSing — no next action.
```

You're clean. Run it again on a repo with intentional drift to see
the card stream.
