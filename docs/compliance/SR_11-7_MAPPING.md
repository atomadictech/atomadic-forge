# Federal Reserve SR 11-7 — Model Risk Management Mapping

> **Framework:** SR Letter 11-7 — Guidance on Model Risk Management (April 2011,  
> updated 2021 SR 11-7 FAQ)  
> **Scope:** Atomadic Forge v0.2+ (Receipt v1.0+)  
> **Maintained by:** Lane F (Golden Path W16–W20)

---

## Purpose

SR 11-7 requires banking organizations to manage the risk associated with
models used in material business decisions. This document maps SR 11-7
sections to Forge Receipt fields that provide the required model-validation
evidence and governance record.

> **Classification note:** Forge's deterministic structural-analysis pipeline
> (certify + wire) is a **rule engine**, not an SR 11-7 model. However, Forge's
> LLM-based generation features (iterate/evolve/chat) may be considered AI
> models under SR 11-7 §III.A if used in model-development workflows. The
> Receipt is the validation and governance record for both.

---

## Mapping Table

| SR 11-7 Section | Requirement | Receipt Field(s) | Evidence |
|---|---|---|---|
| §III.A — Model Definition | Identify whether the system qualifies as a model | `schema_version`, `verdict`, `certify`, `wire` | Deterministic rule-engine output; verdict + score are analytical outputs derived from source-code inputs without estimation/forecasting |
| §III.B — Model Inventory | Maintain an inventory of all models in use | `project.name`, `project.package`, `forge_version`, `generated_at_utc` | Each Receipt entry constitutes one model-inventory row; `forge_version` pins the model version |
| §IV — Model Validation | Independent validation: conceptual soundness, outcome analysis, ongoing monitoring | `certify.score`, `certify.axes`, `wire.verdict`, `lean4_attestation` | Lean4 corpora provide conceptual soundness (machine-checked proofs); certify axes provide outcome analysis; lineage chain provides ongoing monitoring evidence |
| §IV.A — Conceptual Soundness | Evaluate theoretical basis and assumptions | `lean4_attestation.corpora`, `lean4_attestation.total_theorems` | 567 machine-checked theorems across two corpora (0 sorry); assumptions are stated in the ASS-ADE MONADIC_DEVELOPMENT.md specification |
| §IV.B — Ongoing Monitoring | Track model performance over time | `lineage.chain_depth`, `lineage.parent_receipt_hash`, `generated_at_utc` | Vanguard chain provides time-stamped, hash-linked performance record across all Receipt generations |
| §IV.C — Outcome Analysis | Evaluate model outputs against known benchmarks | `certify.score`, `wire.violation_count`, `wire.verdict` | Certify score is calibrated 0–100; violation count is exact; reproducibility instructions in CS-1 §Q5 enable benchmark comparison |
| §V — Governance | Three lines of defense; independent validation; documentation | `signatures.sigstore`, `signatures.aaaa_nexus`, `lineage.lineage_path` | Sigstore Rekor entry provides independent third-party attestation; AAAA-Nexus signature provides organizational sign-off; lineage path enables audit trail |
| §V.A — Documentation | Maintain model documentation throughout lifecycle | All Receipt fields + `artifacts` list | Receipt `artifacts` points to `.atomadic-forge/` evidence files (certify.json, wire.json, scout.json); full lineage in `.atomadic-forge/lineage.jsonl` |
| §V.B — Validation Independence | Validate independently from development | `signatures.aaaa_nexus.issuer`, `signatures.sigstore.rekor_uuid` | AAAA-Nexus signing occurs via `/v1/verify/forge-receipt` endpoint independent of the local Forge process; Sigstore Rekor provides public, independent log |

---

## Lean4 Attestation as Conceptual Soundness Evidence (SR 11-7 §IV.A)

SR 11-7 §IV.A requires validators to "evaluate the reasonableness and
appropriateness of model inputs, processing, and outputs." The Lean4
corpora cited in every signed Receipt provide:

| Requirement | Evidence |
|---|---|
| Theoretical basis documented | ASS-ADE MONADIC_DEVELOPMENT.md (5-tier law) + Lean4 proofs |
| Assumptions stated and justified | `aethel-nexus-proofs` ref `abc1234` — 29 theorems, 0 sorry |
| Mathematical properties verified | `mhed-toe-codex-v22` ref `def5678` — 538 theorems, 0 sorry |

A Receipt with no `lean4_attestation` or `sorry_count > 0` provides
partial conceptual soundness evidence only.

---

## Ongoing Monitoring Record (SR 11-7 §IV.B)

The Vanguard lineage chain at `.atomadic-forge/lineage.jsonl` satisfies
SR 11-7 §IV.B ongoing-monitoring requirements:

```
chain entry n:
  parent_receipt_hash: sha256(<receipt n-1>)
  chain_depth:         n
  generated_at_utc:    YYYY-MM-DDTHH:MM:SSZ
  lineage_path:        vanguard://chain/<project>/<n>
```

To query the chain:

```bash
forge audit list --project <root>      # human-readable
forge audit list --project <root> --json | jq '.entries[]'
```

---

## Signature Status and Governance (SR 11-7 §V)

| Signatures status | SR 11-7 §V posture |
|---|---|
| `SIGNED (Sigstore + AAAA-Nexus)` | Full independent attestation — satisfies §V validation-independence requirement |
| `PARTIAL (Sigstore only)` | Partial — public log present, organizational sign-off absent |
| `PARTIAL (AAAA-Nexus only)` | Partial — organizational sign-off present, public log absent |
| `UNSIGNED` | Local development posture — escalate before model governance sign-off |

---

## Gap Analysis

| SR 11-7 requirement | Coverage | Gap |
|---|---|---|
| Model inventory | Full (per Receipt) | Organizations must aggregate Receipts into their enterprise model inventory |
| Conceptual soundness | Full (when Lean4 corpora present) | Generation features need separate conceptual soundness evaluation |
| Outcome analysis | Full (certify/wire axes) | Stochastic generation outcomes are not covered |
| Ongoing monitoring | Full (lineage chain) | — |
| Independent validation | Full (when signed) | UNSIGNED receipts require manual governance escalation |
| Documentation | Full | — |

---

*For the complete CS-1 Conformity Statement see [CS-1.md](CS-1.md).*
