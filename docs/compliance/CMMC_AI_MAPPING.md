# DoD CMMC-AI — Controls Mapping

> **Framework:** Cybersecurity Maturity Model Certification (CMMC) 2.0  
> with Artificial Intelligence overlay aligned to NIST AI Risk Management  
> Framework 1.0 (January 2023) and DoD AI Adoption Strategy (2023)  
> **Scope:** Atomadic Forge v0.2+ (Receipt v1.0+)  
> **Maintained by:** Lane F (Golden Path W16–W20)

---

## Purpose

CMMC-AI extends the CMMC 2.0 framework with AI-specific controls aligned
to the NIST AI RMF's four functions: **GOVERN, MAP, MEASURE, MANAGE**.
This document maps each relevant CMMC-AI control to Forge Receipt fields.

> **Classification note:** Atomadic Forge is a developer-facing SDLC tool.
> It is not a DoD-contracted AI system. This mapping is for organizations
> building DoD-contracted software who use Forge in their development
> pipeline and need evidence that their AI-assisted development tooling
> satisfies CMMC-AI controls at Level 2.

---

## GOVERN Controls

### GOVERN 1.1 — AI risk policies are established, communicated, and enforced

| Control element | Receipt Field(s) | Evidence |
|---|---|---|
| Risk policy establishment | `schema_version`, `compliance_mappings` | Receipt schema versioning constitutes a documented policy on what every Forge run must produce; `compliance_mappings` provides per-framework status |
| Policy communication | CS-1 Markdown output | `forge cs1 . --out CS-1.md` produces a human-readable policy-compliance document |
| Policy enforcement | `certify.score`, `wire.verdict` | CI gate (`--fail-under`, `--fail-on-violations`) enforces policy programmatically |

### GOVERN 1.2 — Accountability for AI risk is assigned

| Control element | Receipt Field(s) | Evidence |
|---|---|---|
| Accountability assignment | `signatures.aaaa_nexus.issuer`, `signatures.aaaa_nexus.key_id` | AAAA-Nexus signature binds accountability to an issuer identity |
| Audit trail | `lineage.chain_depth`, `lineage.parent_receipt_hash` | Hash-linked Vanguard chain provides accountability record per change event |

### GOVERN 2.1 — Organizational teams understand their AI risk roles

| Control element | Receipt Field(s) | Evidence |
|---|---|---|
| Role clarity | `certify.axes` field names | Four explicitly named axes (documentation_complete, tests_present, tier_layout_present, no_upward_imports) map to role responsibilities |
| Documentation | `artifacts` list | Artifact pointers reference evidence files that each team role is responsible for producing |

---

## MAP Controls

### MAP 1.1 — AI risks are identified, characterized, and categorized

| Control element | Receipt Field(s) | Evidence |
|---|---|---|
| Risk identification | `wire.verdict`, `wire.violation_count` | Upward-import violations are the primary structural risk; exact count is reported |
| Risk characterization | F-codes (F0100–F0106) | F-code taxonomy categorizes each violation class (sidecar drift, tier-map mismatch, etc.) |
| Risk quantification | `certify.score` (0–100), `wire.auto_fixable` | Continuous score + auto-fixable count provide quantitative risk exposure |

### MAP 1.5 — AI risks are prioritized

| Control element | Receipt Field(s) | Evidence |
|---|---|---|
| Risk prioritization | `certify.issues` list | Issues are surfaced in order of structural severity |
| Prioritized action plan | `forge plan` output (agent_plan/v1) | `forge plan <root> --json` produces ranked action cards with risk labels (low/medium/high/critical) |

### MAP 2.2 — Scientific findings and organizational principles inform AI risk classification

| Control element | Receipt Field(s) | Evidence |
|---|---|---|
| Scientific grounding | `lean4_attestation.corpora` | Machine-checked Lean4 proofs constitute scientific validation of risk classification criteria |
| Organizational principles | `schema_version` versioning contract | Forward-compat rule (every optional field defaults to None) is a documented organizational principle encoded in the schema |

---

## MEASURE Controls

### MEASURE 2.5 — AI system performance is measured

| Control element | Receipt Field(s) | Evidence |
|---|---|---|
| Performance metrics | `certify.score`, `wire.verdict`, `scout.symbol_count` | Three quantitative metrics measured deterministically on every run |
| Tamper-evident measurement | `signatures.aaaa_nexus`, `signatures.sigstore.rekor_uuid` | AAAA-Nexus signature + Sigstore Rekor entry make measurement results tamper-evident |
| Longitudinal tracking | `lineage.chain_depth`, `generated_at_utc` | Chain depth + UTC timestamp provide time-series performance record |

### MEASURE 2.9 — AI system performance metrics are documented and traceable

| Control element | Receipt Field(s) | Evidence |
|---|---|---|
| Metrics documentation | `certify.axes` (4 binary flags + continuous score) | Each axis is documented in `a0_qk_constants/receipt_schema.py` `ReceiptCertifyAxes` |
| Traceability | `artifacts` list (sha256 per artifact) | Each artifact pointer carries a SHA-256 for integrity verification; reproducibility instructions in CS-1 §Q5 |

### MEASURE 4.1 — AI risk measurements are documented

| Control element | Receipt Field(s) | Evidence |
|---|---|---|
| Risk measurement documentation | `wire.violation_count`, `wire.auto_fixable` | Violation count and auto-fixable fraction are numeric risk measurements |
| Measurement provenance | `generated_at_utc`, `forge_version` | UTC timestamp + pinned version enable reconstruction of measurement context |

---

## MANAGE Controls

### MANAGE 1.3 — Responses to identified AI risks are prioritized and implemented

| Control element | Receipt Field(s) | Evidence |
|---|---|---|
| Response prioritization | `certify.issues` | Issues list is ordered by severity |
| Mechanical remediation | `wire.auto_fixable` | Auto-fixable violations can be resolved by `forge enforce --apply` |
| Ranked action plan | `forge plan` action cards | `applyable` cards can be executed by `forge plan-apply` |

### MANAGE 2.2 — Mechanisms to document identified AI risks are in place

| Control element | Receipt Field(s) | Evidence |
|---|---|---|
| Risk documentation | `certify.issues`, `wire.violations` (in wire.json) | Issues list + full violation detail in `.atomadic-forge/wire.json` |
| Persistent record | `lineage.lineage_path` | Vanguard chain at `.atomadic-forge/lineage.jsonl` is the append-only risk record |

### MANAGE 4.1 — Residual risks are monitored

| Control element | Receipt Field(s) | Evidence |
|---|---|---|
| Residual risk monitoring | `certify.score`, `lineage.chain_depth` | Score trend across chain depth shows whether residual risk is growing or shrinking |
| Monitoring query | `forge audit list --json` | Human-readable + machine-readable lineage query |

---

## CMMC Level 2 Readiness Summary

| NIST AI RMF Function | CMMC-AI Controls covered | Receipt coverage |
|---|---|---|
| GOVERN | 1.1, 1.2, 2.1 | Full (when signed) |
| MAP | 1.1, 1.5, 2.2 | Full |
| MEASURE | 2.5, 2.9, 4.1 | Full (when signed) |
| MANAGE | 1.3, 2.2, 4.1 | Full |

**UNSIGNED receipts:** GOVERN 1.2 and MEASURE 2.5 tamper-evidence controls
are not satisfied. Escalate to organization signing policy before CMMC-AI
Level 2 assessment.

---

## Lean4 Attestation and MAP 2.2

The Lean4 corpora cited in Receipt `lean4_attestation` satisfy CMMC-AI
MAP 2.2's requirement that "scientific findings inform AI risk
classification":

| Corpus | Theorems | Claim backed |
|---|---|---|
| `aethel-nexus-proofs` | 29, 0 sorry | Monadic composition law: tiers compose upward only |
| `mhed-toe-codex-v22` | 538, 0 sorry | Wire-scan completeness and soundness |

---

*For the complete CS-1 Conformity Statement see [CS-1.md](CS-1.md).*
