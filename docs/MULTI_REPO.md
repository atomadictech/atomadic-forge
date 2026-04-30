# Multi-repo absorption

Forge absorbs more than one repository into a single tiered tree. The
common cases:

- **(a)** Two services with no symbol collisions — straight-through.
- **(b)** Two repos with a duplicate symbol (same `class User`) —
  conflict resolution.
- **(c)** Bulk-absorb 5+ repos into one umbrella package.

Each example below is end-to-end runnable. Replace paths with your own.

---

## (a) Two services, no collisions

You have two small services that have nothing in common except both are
Python: `repo-billing/` and `repo-notifications/`. You want one tiered
tree under `./merged/src/platform/`.

```bash
# Build a cherry manifest from each repo.
forge cherry ./repo-billing       --pick all
forge cherry ./repo-notifications --pick all

# Materialize them into the same destination.
forge auto ./repo-billing       ./merged --apply --package platform
forge auto ./repo-notifications ./merged --apply --package platform

# Verify and score.
forge wire    ./merged/src/platform
forge certify ./merged --package platform
```

Expected output (final wire scan):

```
Wire scan: ./merged/src/platform
  verdict:    PASS
  violations: 0
```

Result tree:

```
merged/
  src/platform/
    a0_qk_constants/    (constants from BOTH repos)
    a1_at_functions/    (pure functions from BOTH repos)
    a2_mo_composites/   (clients, stores from BOTH repos)
    a3_og_features/     (features from BOTH repos)
    a4_sy_orchestration/(CLI from BOTH repos)
  STATUS.md
  .atomadic-forge/      (lineage covers both absorptions)
```

**Troubleshooting:** if the second `forge auto` fails with "destination
not empty," you forgot the second `--apply` step uses the same target.
That's fine — re-run it with `--on-conflict last` to overwrite, or
`first` to keep the original. See section (b).

---

## (b) Duplicate `User` class

You have two repos that each define `class User`. The schemas differ.
Forge will not silently merge them — you must pick a resolution.

```bash
# Try the absorb. With no flag, --on-conflict defaults to fail
# (loud, safe).
forge auto ./repo-a ./out --apply --package userhub
forge auto ./repo-b ./out --apply --package userhub
# -> fails with: "symbol User already materialized in a2_mo_composites"
```

Pick one of these four flags on the second `forge auto`:

| Flag | What happens | When to use |
|------|--------------|-------------|
| `--on-conflict fail` | Abort the second absorb. **(default — safe)** | first time you see a collision; you want to read both before deciding |
| `--on-conflict rename` | Second symbol becomes `User__repo_b` | **recommended** — preserves both signatures, lets you reconcile by hand |
| `--on-conflict first` | Keep what landed first; drop the second | the second repo's `User` is the legacy one |
| `--on-conflict last` | Overwrite with the second; drop the first | the second repo is the newer/canonical version |

Recommended:

```bash
forge auto ./repo-b ./out --apply --package userhub --on-conflict rename
```

Expected output (excerpt):

```
materialized: 14 symbols
  renamed (collision): User -> User__repo_b
  renamed (collision): UserSession -> UserSession__repo_b
```

You now have both `User` and `User__repo_b` in
`a2_mo_composites/`. Forge does **not** unify them — that is a semantic
decision. Open both files, read both schemas, and write a single
`User` in `a2_mo_composites/user_core.py` that covers both. Delete the
two originals once you have ported their callers.

> Why `rename` is the default recommendation: `first` and `last`
> silently drop code, which means real behavior disappears from the
> output. `rename` preserves everything and forces a human to look.
> `fail` is correct when you have not yet decided — but it does not
> let you finish.

**Troubleshooting:** if `--on-conflict rename` produces names like
`User__a_b` that include a path fragment you do not like, override with
`--rename-template`:

```bash
forge auto ./repo-b ./out --apply --package userhub \
    --on-conflict rename --rename-template "{name}_v2"
```

---

## (c) Bulk-absorb 5 repos

You have five microservices and want one umbrella package
(`platform`).

```bash
REPOS=(billing notifications search analytics auth)
DEST=./platform-merged

# Phase 1 — recon all five so you know what you're getting into.
for r in "${REPOS[@]}"; do
    echo "=== $r ==="
    forge recon "./repo-$r"
done

# Phase 2 — absorb in series. First one creates the tree;
# subsequent ones merge into it. Use --on-conflict rename so
# nothing is silently dropped.
forge auto "./repo-${REPOS[0]}" "$DEST" --apply --package platform

for r in "${REPOS[@]:1}"; do
    forge auto "./repo-$r" "$DEST" --apply --package platform \
        --on-conflict rename
done

# Phase 3 — final wire + certify on the merged tree.
forge wire    "$DEST/src/platform"
forge certify "$DEST" --package platform
```

Expected resulting tree (truncated):

```
platform-merged/
  src/platform/
    a0_qk_constants/
      billing_constants.py
      notification_constants.py
      search_constants.py
      ...
    a2_mo_composites/
      billing_client.py
      notification_client.py
      search_index_core.py
      User.py
      User__repo_auth.py        # <- the rename
      ...
  STATUS.md
  .atomadic-forge/
    cherry.json                 # last cherry
    assimilate.json             # last assimilate
    lineage.jsonl               # ALL FIVE absorptions, append-only
```

### When to re-run cherry vs accept the merged manifest

After bulk absorption, ask: **"do I want one merged manifest, or do I
want to re-run cherry on the merged tree?"**

- **Accept the merged manifest** when the only thing you need is the
  union of symbols. The lineage shows you which symbol came from which
  repo; that is enough. This is the common case.

- **Re-run `forge cherry $DEST/src/platform --pick all`** when:
  - You want a *single* cherry manifest covering the merged tree (e.g.
    for downstream tooling that reads `cherry.json`), or
  - The collision-renamed symbols (`User__repo_auth`) need to be
    reclassified to a different tier than they originally landed in,
    and you want a new manifest reflecting that.

Re-running cherry is cheap (~10s on a 500-file tree) and idempotent.
When in doubt, re-run it — the second manifest is the source of truth.

**Troubleshooting:** if `forge wire` returns FAIL on the merged tree
even though each individual repo passed, the cause is almost always a
renamed symbol whose callers are now pointing across tiers. Open the
violation list, look for `User__repo_*` references, and either rename
the callers or move the symbol up a tier. See
[03-tutorial.md](03-tutorial.md) Step 8 for the fix-violations
playbook.
