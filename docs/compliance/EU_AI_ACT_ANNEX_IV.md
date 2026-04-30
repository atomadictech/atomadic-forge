# EU AI Act Annex IV — Atomadic Forge Compliance Mapping

**Standard:** Regulation (EU) 2024/1689 of the European Parliament and of the
Council (the "EU AI Act"), Annex IV — Technical Documentation

**Forge artifact:** `ForgeReceiptV1` (`atomadic-forge.receipt/v1`)  
**CS-1 schema:** `atomadic-forge.cs1/v1`

---

## Purpose

Annex IV of the EU AI Act requires providers of high-risk AI systems to maintain
technical documentation that enables competent authorities to assess the system's
conformity with the Act.  This mapping shows exactly how each Annex IV paragraph
is satisfied by fields in the Atomadic Forge Receipt v1.

---

## Paragraph-by-Paragraph Mapping

### Annex IV §1 — General description of the AI system

**Citation:** Regulation (EU) 2024/1689, Annex IV, paragraph 1

| Annex IV requirement | Receipt field | Notes |
|---------------------|---------------|-------|
| System name and version | `project.name`, `forge_version` | Recorded at every emission |
| Intended purpose | `project.name`, `scout.tier_distribution` | Tier map shows intended architecture |
| Primary programming language | `project.language` | From `scout.primary_language` |
| Per-language file counts | `project.languages` | `{lang: file_count}` dict |
| Total symbol count | `scout.symbol_count` | Structural complexity proxy |
| Tier distribution | `scout.tier_distribution` | `{tier: symbol_count}` dict |

### Annex IV §2(a) — Training, validation and testing data

**Citation:** Regulation (EU) 2024/1689, Annex IV, paragraph 2(a)

| Annex IV requirement | Receipt field | Notes |
|---------------------|---------------|-------|
| Data description | `lean4_attestation.corpora[*].name` | Machine-checked corpus names |
| Data source / repository | `lean4_attestation.corpora[*].repo_url` | Auditable URL |
| Data version / commit | `lean4_attestation.corpora[*].ref_sha` | Exact commit SHA |
| Theorem count | `lean4_attestation.corpora[*].theorem_count` | Size of validation corpus |
| No admitted gaps | `lean4_attestation.corpora[*].sorry_count` | MUST equal 0 |
| Axiom inventory | `lean4_attestation.corpora[*].axiom_count` | SHOULD equal 0 |

**Standard Lean4 corpora cited:**

| Corpus | Theorems | Sorry | Axioms |
|--------|----------|-------|--------|
| `aethel-nexus-proofs` | 29 | 0 | 0 |
| `mhed-toe-codex-v22` | 538 | 0 | 0 |

### Annex IV §2(b) — Data governance and data management practices

**Citation:** Regulation (EU) 2024/1689, Annex IV, paragraph 2(b)

| Annex IV requirement | Receipt field | Notes |
|---------------------|---------------|-------|
| Traceability of structural changes | `lineage.lineage_path` | Vanguard ledger pointer |
| Tamper-evident audit log | `lineage.parent_receipt_hash` | SHA-256 of prior Receipt |
| Change sequence depth | `lineage.chain_depth` | Monotonically increasing |
| VCS metadata | `project.vcs.head_sha`, `project.vcs.branch` | Optional; present when emitted |

### Annex IV §3 — Description of monitoring, functioning and control

**Citation:** Regulation (EU) 2024/1689, Annex IV, paragraph 3

| Annex IV requirement | Receipt field | Notes |
|---------------------|---------------|-------|
| Automated architectural monitoring | `wire.verdict` | PASS or FAIL |
| Violation count | `wire.violation_count` | Count of import-layer violations |
| Auto-remediable violations | `wire.auto_fixable` | Eligible for `forge wire --apply` |
| Documentation check | `certify.axes.documentation_complete` | README.md or ≥2 docs/*.md |
| Test presence check | `certify.axes.tests_present` | tests/test_*.py |
| Tier layout check | `certify.axes.tier_layout_present` | ≥3 tier directories |
| Import discipline check | `certify.axes.no_upward_imports` | Wire scan PASS |
| Aggregate certify score | `certify.score` | 0..100; default threshold 100.0 |

### Annex IV §4 — Description of changes and performance

**Citation:** Regulation (EU) 2024/1689, Annex IV, paragraph 4

| Annex IV requirement | Receipt field | Notes |
|---------------------|---------------|-------|
| Link to prior structural state | `lineage.parent_receipt_hash` | SHA-256 of previous Receipt |
| Change sequence number | `lineage.chain_depth` | n+1 for each successor |
| Full diff retrieval | `lineage.lineage_path` | Dereference via Vanguard `/v1/forge/lineage` |
| Emission timestamp | `generated_at_utc` | UTC ISO-8601; pins the change event |

### Annex IV §5 — Post-market monitoring plan

**Citation:** Regulation (EU) 2024/1689, Annex IV, paragraph 5

| Annex IV requirement | Receipt field | Notes |
|---------------------|---------------|-------|
| Timestamped attestation chain | `signatures.sigstore.rekor_uuid` | Sigstore Rekor entry UUID |
| Verifiable log index | `signatures.sigstore.log_index` | Rekor log index |
| Sigstore bundle | `signatures.sigstore.bundle_path` | Path to sigstore bundle file |
| AAAA-Nexus attestation | `signatures.aaaa_nexus.signature` | Base64-encoded Ed25519 |
| Attestation key ID | `signatures.aaaa_nexus.key_id` | Key identifier |
| Attestation issuer | `signatures.aaaa_nexus.issuer` | e.g. `aaaa-nexus.atomadic.tech` |
| Verification endpoint | `signatures.aaaa_nexus.verify_endpoint` | `/v1/verify/forge-receipt` |

---

## Lean4 Corpus Attestation Table

Every Forge Receipt that claims EU AI Act compliance MUST cite at least one
Lean4 corpus with `sorry_count = 0`.  The standard Atomadic corpora are:

| Corpus | Repository | Theorems | Sorry | Axioms | Status |
|--------|-----------|----------|-------|--------|--------|
| `aethel-nexus-proofs` | Internal | 29 | 0 | 0 | Attesting |
| `mhed-toe-codex-v22` | Internal | 538 | 0 | 0 | Attesting |

---

## Reproducibility Instructions

To independently verify a CS-1 artifact:

1. Retrieve the Receipt from `artifacts[name="receipt"].path` (relative to project root).
2. Hash the Receipt file with SHA-256; compare to `lineage.parent_receipt_hash` of the next Receipt in chain.
3. Clone each `lean4_attestation.corpora[*].repo_url` at the recorded `ref_sha`.
4. Run `lake build` in each corpus repo; confirm `sorry_count = 0`.
5. Verify the Sigstore Rekor entry at `signatures.sigstore.rekor_uuid`.
6. Call AAAA-Nexus `/v1/verify/forge-receipt` with the Receipt payload and `signatures.aaaa_nexus`.

---

## Gap Analysis

| Annex IV paragraph | Coverage | Gap |
|-------------------|----------|-----|
| §1 General description | **Full** | None |
| §2(a) Training data | **Full** | Non-Lean4 data sources not yet tracked in Receipt |
| §2(b) Data governance | **Full** | None |
| §3 Monitoring | **Full** | None |
| §4 Changes | **Full** | None |
| §5 Post-market | **Full** | Rekor entry requires `--sign` flag; unsigned receipts have partial coverage |
| §6 Risk management | **Partial** | Lane E QUARANTINE / hysteresis logic covers §6; not yet in CS-1 |
| §7 Accuracy metrics | **Partial** | Certify score is a structural proxy; task-accuracy metrics are out of scope |
| §8 Cybersecurity | **Partial** | CMMC-AI mapping covers cybersecurity baseline; dedicated Lane H planned |
