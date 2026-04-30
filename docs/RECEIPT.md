# Forge Receipt — JSON wire format

> **Status: v1.0 (Golden Path Lane A W0).** This is the canonical
> format Forge emits for every `forge auto` / `forge certify` /
> `forge enforce` run. v1.1 / v1.2 / v2.0 are reserved (see [Versioning
> roadmap](#versioning-roadmap) below).

The Receipt is a single JSON object that bundles a Forge run's
verdict, evidence pointers, signatures, and Lean4 attestation
citations. It's the artifact that:

- a CI run uploads from `forge certify --emit-receipt receipt.json`
- a `forge mcp serve` resource exposes to coding agents
- the Cowork-style "62 → 5" terminal card (Lane A W1) renders
- Sigstore + AAAA-Nexus sign (Lane A W2)
- Vanguard chains together (Lane A W4)
- the EU AI Act / SR 11-7 / FDA / CMMC Conformity Statement CS-1
  (Lane F W16) embeds verbatim

**Core principle: a Receipt is the *only* object a regulator, an
acquirer, an insurer, or a downstream agent should need to verify a
Forge run.** Every other artifact under `.atomadic-forge/` is
referenced from the Receipt.

---

## Top-level shape

```json
{
  "schema_version": "atomadic-forge.receipt/v1",
  "generated_at_utc": "2026-04-28T17:42:11Z",
  "forge_version": "0.2.2",
  "verdict": "PASS",
  "project":           { ... },
  "certify":           { ... },
  "wire":              { ... },
  "scout":             { ... },
  "assimilate_digest": null,
  "artifacts":         [ ... ],
  "signatures":        { ... },
  "lean4_attestation": { ... },
  "lineage":           { ... },
  "compliance_mappings": {},
  "notes":             [],
  "extra":             {}
}
```

`schema_version` is the routing key. It always matches the regex
`^atomadic-forge\.receipt/v\d+(?:\.\d+)?$` so a single dispatcher in
any consuming tool can route any Receipt version emitted now or
later.

`verdict` is one of the four UEP v20 values:
**`PASS` · `FAIL` · `REFINE` · `QUARANTINE`**.

---

## Required fields

| Field | Type | Notes |
|---|---|---|
| `schema_version` | string | `"atomadic-forge.receipt/v1"` exactly for this version |
| `generated_at_utc` | ISO-8601 string | `YYYY-MM-DDTHH:MM:SSZ`, UTC, second resolution |
| `forge_version` | string | matches `atomadic_forge.__version__` at emit time |
| `verdict` | enum | `"PASS" \| "FAIL" \| "REFINE" \| "QUARANTINE"` |
| `project` | object | identifies the project under Receipt |
| `certify` | object | compact certify summary (score + per-axis flags) |
| `wire` | object | compact wire summary (verdict + counts) |
| `scout` | object | compact scout summary (symbol/tier/effect distributions) |

A Receipt missing any of these is structurally invalid and MUST be
rejected by consumers. The set is pinned in
`a0_qk_constants/receipt_schema.REQUIRED_RECEIPT_V1_FIELDS`.

---

## Optional fields (v1.0)

| Field | Type | Notes |
|---|---|---|
| `assimilate_digest` | string \| null | hex digest of the assimilation; present only on `--apply` runs |
| `artifacts` | list of `{name, path, sha256}` | pointers to `.atomadic-forge/*.json` evidence files |
| `signatures.sigstore` | object \| null | Rekor uuid + log_index; populated by Lane A W2 signer |
| `signatures.aaaa_nexus` | object \| null | base64 signature + key_id; from `/v1/verify/forge-receipt` |
| `lean4_attestation` | object | corpus citations (`aethel-nexus-proofs`, `mhed-toe-codex-v22`) |
| `lineage.lineage_path` | string | opaque Vanguard ledger pointer (Lane A W4) |
| `lineage.parent_receipt_hash` | string \| null | SHA-256 of the immediately prior Receipt |
| `lineage.chain_depth` | int | 1 for first Receipt; n+1 per successor |
| `compliance_mappings` | dict | `mapping_name → status`; populated at Lane F W18 |
| `notes` | list of strings | free-form human-facing notes |
| `extra` | dict | forward-compat escape hatch |

**Unsigned Receipts are valid.** The signature fields default to
`null`. A consumer that requires attestation MUST check
`signatures.sigstore` and/or `signatures.aaaa_nexus` independently.

---

## Worked example

A Receipt emitted from a clean `forge certify` run on a 14-symbol
Python project with both signatures populated and the Lean4 corpora
cited:

```json
{
  "schema_version": "atomadic-forge.receipt/v1",
  "generated_at_utc": "2026-04-28T17:42:11Z",
  "forge_version": "0.2.2",
  "verdict": "PASS",

  "project": {
    "name": "atomadic-forge",
    "root": "/home/thomas/atomadic-forge",
    "package": "atomadic_forge",
    "language": "python",
    "languages": { "python": 53, "javascript": 0, "typescript": 0 },
    "vcs": {
      "head_sha": "7cd840a6e9b4d2c0aa518c4e16bbd09f5e2d9a44",
      "short_sha": "7cd840a",
      "branch": "lane-d1-audit-verb",
      "remote_url": "https://github.com/atomadictech/atomadic-forge.git",
      "dirty": false
    }
  },

  "certify": {
    "score": 100.0,
    "axes": {
      "documentation_complete": true,
      "tests_present": true,
      "tier_layout_present": true,
      "no_upward_imports": true
    },
    "issues": []
  },

  "wire": {
    "verdict": "PASS",
    "violation_count": 0,
    "auto_fixable": 0
  },

  "scout": {
    "symbol_count": 412,
    "tier_distribution": {
      "a0_qk_constants": 31,
      "a1_at_functions": 217,
      "a2_mo_composites": 4,
      "a3_og_features": 22,
      "a4_sy_orchestration": 12
    },
    "effect_distribution": { "pure": 308, "state": 71, "io": 33 },
    "primary_language": "python"
  },

  "assimilate_digest": null,

  "artifacts": [
    {
      "name": "scout",
      "path": ".atomadic-forge/scout.json",
      "sha256": "f2c8a1...e9b5"
    },
    {
      "name": "wire",
      "path": ".atomadic-forge/wire.json",
      "sha256": "7d31bb...0c4a"
    },
    {
      "name": "certify",
      "path": ".atomadic-forge/certify.json",
      "sha256": "bc12fe...88a1"
    }
  ],

  "signatures": {
    "sigstore": {
      "rekor_uuid": "108e9e4f-ff8e-4f1c-a6d3-1b2c5d6e7f8a",
      "log_index": 79412118,
      "bundle_path": ".atomadic-forge/receipt.sigstore-bundle.json"
    },
    "aaaa_nexus": {
      "signature": "MEUCIQDk...3Q==",
      "key_id": "atomadic-forge-prod-v1",
      "issuer": "aaaa-nexus.atomadic.tech",
      "issued_at_utc": "2026-04-28T17:42:14Z",
      "verify_endpoint": "/v1/verify/forge-receipt"
    }
  },

  "lean4_attestation": {
    "corpora": [
      {
        "name": "aethel-nexus-proofs",
        "repo_url": "https://github.com/AAAA-Nexus/aethel-nexus-proofs",
        "ref_sha": "9f1c44...",
        "theorem_count": 29,
        "sorry_count": 0,
        "axiom_count": 0
      },
      {
        "name": "mhed-toe-codex-v22",
        "repo_url": "https://github.com/AAAA-Nexus/mhed-toe-codex",
        "ref_sha": "31bd09...",
        "theorem_count": 538,
        "sorry_count": 0,
        "axiom_count": 0
      }
    ],
    "total_theorems": 567,
    "summary": "29 + 538 = 567 machine-checked theorems, 0 sorry, 0 axioms."
  },

  "lineage": {
    "lineage_path": "vanguard://atomadic-forge/2026/04/28/7cd840a",
    "parent_receipt_hash": "5e4a...",
    "chain_depth": 9
  },

  "compliance_mappings": {},
  "notes": [],
  "extra": {}
}
```

A **failing** Receipt looks the same shape but with `verdict: "FAIL"`,
`certify.score < 100`, populated `certify.issues`, and
`wire.verdict: "FAIL"` with a non-zero `wire.violation_count`. The
signature blocks remain present — a Receipt of a failed run is still
a real artifact and is signed; the failure itself is the evidence.

---

## How verdict is decided

```
verdict = PASS         when wire.verdict == PASS
                       AND certify.score >= 100
                       AND signatures populated (when --sign)

verdict = FAIL         when wire.verdict == FAIL
                       OR certify.score < threshold
                       OR a required field is missing

verdict = REFINE       when the run completed but evidence is
                       incomplete (e.g. iterate halted on stagnation
                       at score < threshold)

verdict = QUARANTINE   when the run detected an anomaly that needs
                       human audit before re-emission (e.g. the
                       hysteresis ratchet > 0.5 — Golden Path Lane E
                       feature)
```

The threshold for PASS is configurable via `--fail-under N` on
`forge certify` (Golden Path Lane G1, already shipped).

---

## Forward-compat: how consumers should handle unknown fields

1. Read `schema_version`. If the major (`v1`) matches a known
   handler, dispatch to it.
2. The handler MUST tolerate unknown fields — Receipts emitted by a
   newer minor version will carry fields the consumer doesn't yet
   understand. Just preserve and pass through.
3. The handler SHOULD warn (not error) when it sees `extra` populated
   — that's the explicit forward-compat escape hatch and someone has
   written something there for a reason.
4. Never silently drop fields when re-emitting. Round-tripping a
   Receipt MUST be byte-identical except for fields the consumer
   explicitly modified.

---

## Versioning roadmap

| Version | Golden Path week | Adds |
|---|---|---|
| **v1.0** | W0 (this doc) | base schema |
| v1.1 | W8 (Lane A) | `polyglot_breakdown` — per-language certify split |
| v1.2 | W12 (Lane A) | `slsa_attestation` — Sigstore-bundle-compatible `slsa-provenance-ai/v1` predicate |
| v2.0 | W24 (Lane A) | `bao_rompf_witnesses` — full categorical effect signatures per public symbol; depends on Lane D `.forge` sidecar parser |

Minor versions (v1.x) are additive: every new field is optional and
existing consumers continue to work. Major bumps (v2.0) MAY add
required fields — those are flagged in `REQUIRED_RECEIPT_V*_FIELDS`
in [`receipt_schema.py`](../src/atomadic_forge/a0_qk_constants/receipt_schema.py).

---

## Related

- Schema source of truth:
  [`a0_qk_constants/receipt_schema.py`](../src/atomadic_forge/a0_qk_constants/receipt_schema.py)
- Emitter (Lane A W1): `a1_at_functions/receipt_emitter.py` *(forthcoming)*
- Card renderer (Lane A W1): `a1_at_functions/card_renderer.py` *(forthcoming)*
- Signer (Lane A W2): `a2_mo_composites/receipt_signer.py` *(forthcoming)*
- Lineage / Vanguard wire-up (Lane A W4): see [Golden Path](../launch/forge/GOLDEN_PATH-20260428.md) §2 Lane A
- Lean4 corpus citations: see
  [`docs/FORMALIZATION.md`](FORMALIZATION.md)
- CI integration: see [`docs/CI_CD.md`](CI_CD.md)
