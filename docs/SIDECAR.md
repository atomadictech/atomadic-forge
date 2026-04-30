# `.forge` sidecar — v1.0

> **Status: v1.0 (Golden Path Lane D W8).** Parser + spec ship in
> 0.3.x. The cross-validator (W11), the LSP wiring (W12+), and the
> Lean4 `proves:` discharger (W20) are reserved.

A `.forge` sidecar is a YAML file that sits beside any source file
and declares the per-symbol contract that `forge wire` and `forge
certify` would otherwise infer heuristically. It is **opt-in,
gradual, and never required** — Forge runs cleanly against repos
with zero sidecars; sidecars are how a team ratchets in stronger
guarantees over time (TypeScript-adoption-curve style).

## File convention

```
src/pkg/users/auth.py        ← the source file
src/pkg/users/auth.py.forge  ← its sidecar
```

The same naming holds for `.js` / `.ts` / `.jsx` / `.tsx` / etc.
Sidecars are NOT `.py` files; they don't import, they don't execute.

## Worked example

`src/pkg/users/auth.py`:

```python
def login(username: str, password: str) -> str:
    """Authenticate, return a session token."""
    ...

def hash_password(plain: str) -> str:
    """Pure deterministic hash."""
    ...

def emit_login_event(user_id: str) -> None:
    """Observability emission."""
    ...
```

`src/pkg/users/auth.py.forge`:

```yaml
schema_version: atomadic-forge.sidecar/v1
target: users/auth.py

symbols:
  - name: login
    effect: NetIO
    tier: a3_og_features
    compose_with:
      - users.session.SessionStore.put
      - audit.audit_log.AuditLogger.append
    proves:
      - "lemma:login_emits_session"
      - "lemma:login_audit_trail"

  - name: hash_password
    effect: Pure
    tier: a1_at_functions
    proves:
      - "lemma:hash_is_deterministic"

  - name: emit_login_event
    effect: Logging
    tier: a3_og_features
    notes:
      - "fire-and-forget; failure must not block login"
```

## Required fields

| Field | Type | Notes |
|---|---|---|
| `schema_version` | string | Must be exactly `"atomadic-forge.sidecar/v1"` |
| `target` | string | Path of the source file the sidecar covers |
| `symbols` | list | One entry per public symbol you want to constrain |

A sidecar with zero `symbols` is structurally valid (it might
declare future intent) but the cross-validator (Lane D W11) treats
it as a no-op.

### Per-symbol required fields

| Field | Type | Notes |
|---|---|---|
| `name` | string | Must match a top-level symbol in the source |
| `effect` | enum | One of `Pure`, `IO`, `NetIO`, `KeyedCache`, `Logging`, `Random`, `Mutation` |

### Per-symbol optional fields

| Field | Type | Notes |
|---|---|---|
| `compose_with` | list of strings | Other symbols this one composes with (Bao-Rompf categorical effect functor — Lane D W20) |
| `proves` | list of strings | Lean4 obligation labels this symbol satisfies; W20 dispatches to `aethel-nexus-proofs` |
| `tier` | string | Pin the tier (otherwise inferred from path) |
| `notes` | list of strings | Free-form |

## Effect taxonomy

The seven kinds form a small categorical lattice (Bao-Rompf 2025):

| Effect | Meaning |
|---|---|
| `Pure` | No side effects; output is a function of input |
| `Random` | Non-deterministic input (rng / time / uuid) |
| `Logging` | Observability emission only; no business state change |
| `KeyedCache` | Writes to a content-addressed cache; idempotent re-runs |
| `IO` | Arbitrary I/O (filesystem, stdin/stdout) |
| `NetIO` | Network calls — flagged for Lane F W18 compliance review |
| `Mutation` | Mutates passed-in arguments — flagged for review |

Adding a new effect is additive (forward-compat). The parser
preserves unknown effects and warns; downstream tools may error.

## Forward-compat

- Unknown top-level fields are preserved in `extra`.
- Unknown effect kinds are warned but kept as-is.
- Future minors (v1.1+) may add fields; consumers MUST tolerate them.

## Where it plugs in

- **Today (v0.3.x):** parser ships in `a1_at_functions.sidecar_parser`.
  CLI verb: `forge sidecar parse <file>` (forthcoming in v0.3.x once
  this doc lands).
- **Lane D W11:** cross-validator compares declared effects against
  the source AST and flags drift.
- **Lane D W12:** `forge-lsp` exposes hover + diagnostics on `.forge`
  files in VS Code / Neovim.
- **Lane D W20:** Bao-Rompf compose-by-law checker discharges
  `proves:` clauses against the Lean4 corpus.

## Related

- [Receipt v1 wire format](RECEIPT.md)
- [F-codes registry](FORMALIZATION.md)
- [Golden Path Lane D](../launch/forge/GOLDEN_PATH-20260428.md)
