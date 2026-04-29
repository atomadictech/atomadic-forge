# Atomadic Forge — Agent Operating Manual

> **For agents (human or AI) shipping code into this repository.**
> Every commit since `0.2.2` follows the conventions below. They are not
> stylistic — they are load-bearing for the Golden Path
> (`launch/forge/GOLDEN_PATH-20260428.md`), the BEP convergence proof,
> the Atomadic-Standard self-certify CI gate, and the AAAA-Nexus safety
> composition. Break any of them and the gate flips red.

---

## 0. The seven-line agent contract

Before you write any code in this repo, you can recite these from memory:

1. **Read the Golden Path lane and week your work belongs to.** Cite
   them in the docstring you're about to write.
2. **No upward imports.** a0 imports nothing; a1 imports a0; a2 imports
   a0+a1; a3 imports a0+a1+a2; a4 imports any. `forge wire` refuses to
   merge violations.
3. **Pure where pure is possible.** a0 = data only. a1 = stateless
   pure functions. State lives in a2.
4. **F-coded errors.** Every user-visible error must carry a stable
   4-digit code (`F0042`), never reused or renumbered.
5. **Forward-compat schemas.** Every JSON shape Forge emits has a
   `schema_version`. Every new optional field defaults to
   `None` / `[]` / `{}`. Adding a *required* field is a major bump.
6. **Tests in the same commit.** No feature ships without a co-located
   test file. Snapshot tests for renderers, contract tests for schemas,
   smoke tests for CLI surfaces.
7. **Verdict at the end of every non-trivial PR description.** One of
   `PASS`, `REFINE`, `QUARANTINE`, `REJECT`. With evidence.

Violation of any of seven flips the BEP self-hosting CI gate red.

---

## 1. The Golden Path lane / week citation

**Every new file's docstring opens with the Golden Path lane and week
it belongs to.** Real example from master (`a0_qk_constants/receipt_schema.py`):

```python
"""Tier a0 — Forge Receipt JSON v1 schema.

Golden Path Lane A W0 deliverable. Lane A W1 fills in
``a1_at_functions/receipt_emitter.py`` ... Lane A W2 fills in
``a2_mo_composites/receipt_signer.py`` ...
"""
```

**Why this matters:** the codebase becomes a navigable map of the plan.
A new contributor (or agent) can grep `Golden Path Lane` and walk the
entire 9-month roadmap from the source. No external Trello — the plan
and the code are the same artifact.

**Pattern**:

- First sentence: `Tier aN — what this file is in 8 words.`
- Second paragraph: `Golden Path Lane <X> W<n> deliverable.`
- If paired with sibling files: name them and their lanes.
- If consumers exist downstream: name them and their lanes too.

---

## 2. The 5-tier monadic law (operational)

Every source file (Python `.py`, JS `.js`/`.mjs`/`.cjs`/`.jsx`, TS
`.ts`/`.tsx`) belongs to **exactly one** tier.

| Tier | Directory | What lives here | May import |
|---|---|---|---|
| **a0** | `a0_qk_constants/` | Constants, enums, TypedDicts | nothing |
| **a1** | `a1_at_functions/` | Pure stateless functions | a0 |
| **a2** | `a2_mo_composites/` | Stateful classes / clients / stores | a0, a1 |
| **a3** | `a3_og_features/` | Features composing a2 into capabilities | a0, a1, a2 |
| **a4** | `a4_sy_orchestration/` | CLI commands, entry points | a0–a3 |

**Quick decision tree**:

- "Constant / TypedDict / enum" → **a0**
- "Takes args, returns a value, no side effects, no env" → **a1**
- "Holds state across calls; HTTP session; reads files" → **a2**
- "Composes 2+ a2 objects into one capability" → **a3**
- "CLI handler that wires it all up" → **a4**

**Always run `forge wire src/atomadic_forge` before committing.**

### Real case study — the W4 F0042 catch (2026-04-29)

During GP-C W4 (`forge mcp serve`), an a3-import sneaked into a1 in
the first cut: `mcp_protocol.py` (a1, pure JSON-RPC framing) needed to
register an enforce-handler that lived in `mcp_server.py` (a3,
stateful loop). The naive solution was a lazy import in a1 — caught
by `forge wire` as an **F0042 upward import** mid-implementation.

**Fix**: the canonical injection refactor. The enforce-handler
registration moved to a3 where it belongs; a1 stayed pure. The MCP
server now passes the handler down at construction time. Wire scan
returned to PASS, all 21 W4 tests green, and the discipline held by
construction — not by accident.

**Lesson**: when an a1 module wants to register a callback or invoke
an a3 feature, the a1 module is misclassified — it has hidden
orchestration. Push the registration up; pass the handler down. The
F0042 catch isn't a bug, it's the law working.

---

## 3. F-code namespace discipline

Registry at `a0_qk_constants/error_codes.py`. 9 ranges:

| Range | Domain |
|---|---|
| F0001–F0009 | scout / classification (info) |
| F0010–F0019 | cherry-pick (warn) |
| F0040–F0049 | wire / upward-import violations |
| F0050–F0059 | certify axis failures |
| F0060–F0069 | stub detection |
| F0070–F0079 | import-repair |
| F0080–F0089 | assimilate conflicts |
| F0090–F0099 | receipt / signing |

**Rules**:

- Adding an F-code is **additive** (minor version).
- Removing or renumbering is a **major version bump**.
- The message string can change per locale; the F-code stays.
- `forge enforce` routes mechanical fixes by F-code.
- Reserved ranges F0020–F0039 and F0100+ are intentionally unused.

---

## 4. Schema versioning (forward-compat)

Every JSON wire format Forge emits — Receipt, scout report, wire report,
certify report, lineage entry — declares a `schema_version` matching
`^atomadic-forge\.<name>/v\d+(?:\.\d+)?$`.

**Rules** (mirror semver):

- **Patch**: bug fixes, no shape change
- **Minor**: adds optional fields with safe defaults
- **Major**: adds *required* fields, renames fields, changes types

Consumers must accept and ignore unknown fields. Producers MUST emit
`schema_version` and SHOULD emit every required field.

Real-world example — `receipt_schema.py` documents v1.0 → v1.1 (W8) →
v1.2 (W12) → v2.0 (W24) with each minor bump tied to a Golden Path
week and a specific reserved field name.

---

## 5. Test discipline

- **Every a1 file MUST have a co-located test in `tests/`.**
- **Snapshot tests for renderers** (e.g. `test_card_renderer.py`):
  pin the exact 60×24 output against a fixture.
- **Contract tests for schemas** (e.g. `test_receipt_schema.py`):
  every required field is asserted; every reserved field is asserted
  reserved; the regex is asserted.
- **Smoke tests for CLI surfaces**: every new command + flag is
  exercised end-to-end at least once.

**Test trajectory the dev agents have demonstrated**:

| Stage | Tests passing |
|---|---|
| Baseline `82deb95` | 301 |
| After audit Phase 1 (A1+H1+F) | 308 |
| After audit Phase 3 (D2+B4+D1) | 354 |
| After GP-A W0 | 363 |
| After GP-A W1 | 404 |
| After GP-A W1+W2+W5+W6 | 446 |
| After GP-C W1 (forge-action) | 464 |
| **Current** | **477** |

**+176 tests since baseline; wire scan PASS at every commit; certify
100/100 held.** This is the bar.

---

## 6. AAAA-Nexus composition (don't reimplement safety)

Forge **composes** AAAA-Nexus's safety primitives. It does not
reimplement them.

The Receipt's `signatures` / `lineage` / `lean4_attestation` fields are
**outward pointers** to:

- **Sigstore Rekor** (`signatures.sigstore.rekor_uuid`)
- **AAAA-Nexus signature** (`signatures.aaaa_nexus.signature` via
  `/v1/verify/forge-receipt`)
- **Vanguard ledger** (`lineage.lineage_path` via `/v1/forge/lineage`)
- **Aegis Proxy** (sits in front of `forge mcp serve` at Lane C W6)
- **`aethel-nexus-proofs`** Lean4 corpus (29 theorems, 0 sorry, 0 axioms)
- **MHED-TOE Codex V22** (538 theorems, 0 sorry)

**Graceful-degradation contract** (canonical, from `receipt_signer.py`):

| Failure | Receipt state |
|---|---|
| `AAAA_NEXUS_API_KEY` unset | unsigned + `"key not set"` note |
| HTTP 4xx (auth / rate / not-shipped) | unsigned + endpoint cached unavailable |
| HTTP 5xx / network error | unsigned + retry note |
| HTTP 200 | `signatures.aaaa_nexus` populated |

**The signer never throws.** Apply the same contract anywhere you
compose an outward AAAA-Nexus call.

---

## 7. Branch + commit hygiene

- **One Golden Path week per branch.** Format:
  `gp-lane-<X>-w<n>-<slug>` (lower-case, hyphenated, ≤ 60 chars).
  Examples already shipped: `gp-lane-a-w0-receipt-schema`,
  `gp-lane-a-w1-emitter-and-card`, `gp-lane-c-w1-forge-action`,
  `gp-lane-c-w2-precommit`.
- **Commit messages**: `feat(<area>):` / `fix(<area>):` / `docs(<area>):`
  prefix; close with the lane citation in parens —
  `feat(receipt): … (GP Lane A W2)`.
- **Fast-forward merge to master** when wire+certify+pytest pass. No
  squash, no rebase-into-merge: every Golden Path week deserves its
  own commit on master so the lineage tree maps 1:1 to the plan.
- **Delete merged branches** after fast-forward.
- **Branch checkouts wipe untracked working-tree files.** If you have
  durable doc work that isn't ready to commit yet, stash it (`git
  stash push -m "docs: cleanup-crew XYZ"`), don't leave it untracked.
- **The cleanup-crew-followon-\* stash pattern.** When the dev agent
  pivots from one Golden Path week's branch to the next while the
  cleanup-tail agent has tracked-modified doc edits in the working
  tree, the dev agent stashes them with a name like
  `cleanup-crew-followon-w<n>` *before* checkout. The stash queue is
  applied on master in batches (the same pattern that produced
  `e423cb4 docs: cleanup-crew CHANGELOG + COMMANDS catch-up through
  GP-A W0`). **Tracked-modified files survive this queue.**
  Untracked-new files — including new training docs like *this one*
  — do **not**, and must be either committed, stashed with
  `-u/--include-untracked`, or backed up outside the repo. The dev
  agent's stash discipline is itself an architectural invariant: it
  preserves cleanup-tail work without merging it prematurely into
  feature branches.

---

## 8. The verification lane (UEP v20)

**Never let an agent self-approve non-trivial work.** This repo's
verification lane is:

1. **The agent ships** the feature on a `gp-...` branch.
2. **A separate cleanup-tail agent** reads the commit, updates docs
   (CHANGELOG, COMMANDS, this guide), re-runs `pytest` + `forge
   certify` + `forge wire`, confirms gates pass.
3. **The CI self-host gate** re-confirms 100/100 from a clean checkout.
4. **The user / human reviewer** has the final merge authority.

If any of those four lanes flips red, the merge stops.

---

## 9. The wisdom note

The dev agents already exhibit every pattern in this guide. This file
exists not to teach them — they know — but to make the patterns
**inherited** rather than **rediscovered** when:

- A new dev agent starts (this file is its bootstrap).
- A human contributor opens a PR (this file is the convention sheet).
- An LLM-driven `forge iterate` run scaffolds new code (the prompt
  template references this file as the style anchor).

**Convergence is the load-bearing signal.** When 6+ lanes' worth of
work all exhibit the same seven invariants without coordination, those
invariants are real. This file makes them legible.

---

## 10. Quick reference

| Task | Command |
|---|---|
| Verify wire | `forge wire src/atomadic_forge` |
| Verify self-certify | `forge certify .` |
| Verify tests | `python -m pytest tests/` |
| Emit Receipt | `forge certify . --emit-receipt out.json` |
| Sign Receipt | `forge certify . --emit-receipt out.json --sign` |
| Print viral card | `forge certify . --print-card` |
| Apply mechanical fixes | `forge enforce src/...` |
| Browse lineage | `forge audit list` / `forge audit show <id>` |
| Diff two manifests | `forge diff a.json b.json` |

| Doc | Where |
|---|---|
| Golden Path roadmap | `launch/forge/GOLDEN_PATH-20260428.md` |
| BEP-1 breakthrough | `launch/forge/WOW-FORGE-BREAKTHROUGH-20260428.md` |
| Receipt wire format | `docs/RECEIPT.md` |
| Command reference | `docs/COMMANDS.md` |
| First-10-minutes | `docs/FIRST_10_MINUTES.md` |
| Changelog | `CHANGELOG.md` |
| **This guide** | `AGENTS.md` (you are here) |

---

*Atomadic Forge. Absorb. Enforce. Emerge. Tier-clean by construction.*
