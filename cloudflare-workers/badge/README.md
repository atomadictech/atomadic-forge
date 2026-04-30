# forge-badge — Cloudflare Worker

Returns shields.io-compatible SVG badges for any repo that has
uploaded a Forge Receipt to the `FORGE_RECEIPTS` KV namespace.

This is the Lane C W3 deliverable from the Atomadic Forge Golden
Path. Pair with the `forge-action` GitHub Action (Lane C W1) — once
the action is configured to PUT receipts after every passing CI run,
any consuming repo gets a badge for free.

## Routes

| Path | Returns |
|---|---|
| `/badge/<owner>/<repo>.svg` | SVG badge for the repo's default branch |
| `/badge/<owner>/<repo>/<branch>.svg` | SVG badge for `<branch>` |
| `/badge/<owner>/<repo>.json` | shields.io [dynamic-badge JSON](https://shields.io/badges/dynamic-json-badge) — useful if you want shields.io to host the SVG instead |

Examples:

```markdown
![Forge certify](https://forge.atomadic.dev/badge/atomadictech/atomadic-forge.svg)
[![Forge certify on a PR branch](https://forge.atomadic.dev/badge/atomadictech/atomadic-forge/feat-x.svg)](https://github.com/atomadictech/atomadic-forge/tree/feat-x)
```

## Color rubric

| Verdict + score | Color |
|---|---|
| `PASS` and `score == 100` | green |
| `PASS` and `score >= 90` | yellow-green |
| `score >= 75` | yellow |
| `score >= 50` | orange |
| `score < 50` | red |
| no receipt yet (or KV miss) | grey, message `"no receipt"` |

## Storage shape

The Worker reads from a Workers KV namespace bound as
`FORGE_RECEIPTS`. Keys:

```
receipt:<owner>:<repo>:<branch>
```

Values are the raw `atomadic-forge.receipt/v1` JSON the Python
`forge certify --emit-receipt` produces. The Worker only reads the
top-level `verdict`, `certify.score`, `wire.verdict`,
`generated_at_utc`, and `forge_version` fields; everything else is
ignored.

## Deploy

```bash
cd cloudflare-workers/badge
npm install
wrangler login

# One-time: create the KV namespace and copy the printed id
# back into the [[kv_namespaces]] block of wrangler.toml.
wrangler kv namespace create FORGE_RECEIPTS

# Deploy.
wrangler deploy
```

Then point a custom domain (e.g. `forge.atomadic.dev`) at the
Worker via the Cloudflare dashboard.

## Populating receipts (forge-action)

The `forge-action` composite Action (Lane C W1) already produces a
Receipt as a CI artifact. Add an additional step to POST it to a
small `forge-receipt-uploader` Worker (Lane C W3 follow-up) which
authenticates with a shared secret and writes to the same KV
namespace. Until that uploader ships, populate keys manually:

```bash
wrangler kv key put \
  --namespace-id="<id>" \
  "receipt:atomadictech:atomadic-forge:main" \
  --path=.atomadic-forge/receipt.json
```

## Tests

The pure SVG / digest helpers are exported and tested in
`tests/test_badge_worker.py` (Python-side smoke against the
TypeScript source — uses `subprocess` to drive `node` only when
present). The full vitest suite ships with the Worker package
(`npm test` from this directory).

## Status

- **Today (Lane C W3):** Worker scaffold + SVG generator + KV
  read path + tests. Local-deploy-from-source flow works.
- **Lane C W3 follow-up (planned):** `forge-receipt-uploader`
  Worker with HMAC auth so `forge-action` can PUT directly without
  baking secrets into the consuming repo.
- **Lane B Studio (planned):** Studio renders the badge inline.

## License

Business Source License 1.1 — same as the parent
[`atomadic-forge`](../../LICENSE) package.
