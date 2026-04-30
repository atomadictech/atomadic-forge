# FDA PCCP — Atomadic Forge Compliance Mapping

**Standard:** FDA Guidance: Artificial Intelligence/Machine Learning (AI/ML)-Based
Software as a Medical Device (SaMD) Action Plan (January 2021); Predetermined
Change Control Plan (PCCP) for Machine Learning-Enabled Medical Devices (Draft
Guidance, April 2023)

**Forge artifact:** `ForgeReceiptV1` (`atomadic-forge.receipt/v1`)  
**CS-1 schema:** `atomadic-forge.cs1/v1`

---

## Purpose

The FDA PCCP framework allows manufacturers of AI/ML-based medical devices to
pre-specify the types of modifications they plan to make and the controls in place
to manage associated risks, enabling the FDA to review and authorize changes without
requiring a new premarket submission for each modification.

This mapping shows how Atomadic Forge Receipt fields satisfy PCCP documentation
obligations.

---

## Section-by-Section Mapping

### PCCP §II.A — Description of Modifications

**Citation:** FDA Guidance, Predetermined Change Control Plan for ML-Enabled Medical
Devices (Draft 2023), Section II.A — Description of Planned Modifications

| PCCP requirement | Receipt field | Notes |
|-----------------|---------------|-------|
| Modification description | `lineage.lineage_path` | Vanguard ledger pointer to full diff |
| Prior state link | `lineage.parent_receipt_hash` | SHA-256 of the immediately prior Receipt |
| Modification sequence | `lineage.chain_depth` | Monotonically increasing integer |
| Emission timestamp | `generated_at_utc` | UTC ISO-8601; pins the modification event |
| VCS commit at modification | `project.vcs.head_sha` | Full commit SHA |
| VCS branch | `project.vcs.branch` | Branch name at emission |
| Working-tree state | `project.vcs.dirty` | True if uncommitted changes existed |

The parent hash chain (`lineage.parent_receipt_hash`) links successive Receipts
into an auditable modification sequence recoverable via Vanguard
`/v1/forge/lineage`.

### PCCP §II.B — Methodology for Implementing and Validating Modifications

**Citation:** FDA Guidance, Predetermined Change Control Plan for ML-Enabled Medical
Devices (Draft 2023), Section II.B — Methodology for Implementing and Validating
Predetermined Modifications

| PCCP requirement | Receipt field | Notes |
|-----------------|---------------|-------|
| Formal validation methodology | `lean4_attestation.corpora` | Machine-checked Lean4 proofs |
| Total theorem count | `lean4_attestation.total_theorems` | Sum across all corpora |
| No admitted gaps | `lean4_attestation.corpora[*].sorry_count` | MUST equal 0 |
| Structural validation checklist | `certify.axes` | 4-axis structural gate |
| Documentation axis | `certify.axes.documentation_complete` | README.md or ≥2 docs/*.md |
| Test presence axis | `certify.axes.tests_present` | tests/test_*.py present |
| Tier layout axis | `certify.axes.tier_layout_present` | ≥3 tier directories |
| Import discipline axis | `certify.axes.no_upward_imports` | Wire scan PASS |
| Aggregate validation score | `certify.score` | 0..100; PASS requires ≥ threshold |

**Lean4 validation methodology:**

Each Lean4 corpus cited in `lean4_attestation` represents a machine-checked proof
corpus that validates the mathematical invariants of the system.  The `sorry_count = 0`
constraint ensures that no theorem has been admitted without proof, providing the
strongest available evidence of validation completeness under PCCP §II.B.

Atomadic standard validation corpora:

| Corpus | Theorems | Sorry | Validation claim |
|--------|----------|-------|-----------------|
| `aethel-nexus-proofs` | 29 | 0 | Structural invariants of the Atomadic monadic composition law |
| `mhed-toe-codex-v22` | 538 | 0 | Mathematical foundations of the tier-effect type system |

### PCCP §II.C — Performance Monitoring Plan

**Citation:** FDA Guidance, Predetermined Change Control Plan for ML-Enabled Medical
Devices (Draft 2023), Section II.C — Performance Monitoring Plan for Predetermined
Modifications

| PCCP requirement | Receipt field | Notes |
|-----------------|---------------|-------|
| Timestamped monitoring event | `generated_at_utc` | UTC ISO-8601 |
| Immutable attestation | `signatures.sigstore.rekor_uuid` | Sigstore Rekor UUID |
| Verifiable log entry | `signatures.sigstore.log_index` | Rekor log index |
| Independent attestation | `signatures.aaaa_nexus.signature` | AAAA-Nexus signature |
| Attestation timestamp | `signatures.aaaa_nexus.issued_at_utc` | Nexus issuance time |
| Verification endpoint | `signatures.aaaa_nexus.verify_endpoint` | `/v1/verify/forge-receipt` |
| Evidence file inventory | `artifacts` | Pointers to all `.atomadic-forge/*.json` files |
| Evidence integrity | `artifacts[*].sha256` | SHA-256 of each artifact |

The continuous monitoring record is the time-series of Receipts in
`.atomadic-forge/lineage.jsonl`, one per `forge auto` run.

---

## Schema Versioning Table

PCCP §II.A requires that modification types and controls be pre-specified.
The Forge Receipt schema version encodes this:

| Receipt schema | Changes introduced | PCCP relevance |
|---------------|-------------------|----------------|
| `v1.0` | Base schema | §II.A–§II.C baseline |
| `v1.1` | `polyglot_breakdown` (per-language counts) | §II.A: new modification type tracked |
| `v1.2` | `slsa_attestation` (SLSA provenance) | §II.C: additional monitoring signal |
| `v2.0` | `bao_rompf_witnesses` (categorical proofs) | §II.B: deeper validation methodology |

Each schema bump is a pre-specified modification type under PCCP §II.A.

---

## Lean4 Attestation as PCCP §II.B Evidence

PCCP §II.B requires that the methodology for validating modifications be documented
and pre-specified.  Machine-checked Lean4 proofs satisfy this requirement because:

1. **Pre-specified:** the proof corpus (name, repo_url) is recorded in the Receipt
   before emission, not after.
2. **Machine-checked:** the proofs are verified by the Lean4 theorem prover, not
   by human inspection.
3. **Zero sorry:** the `sorry_count = 0` constraint means no theorem was admitted
   without proof.
4. **Version-pinned:** the `ref_sha` field pins the corpus to an exact commit,
   enabling reproduction of the validation at any future audit.

---

## Gap Analysis

| PCCP section | Coverage | Gap |
|-------------|----------|-----|
| §II.A Description of modifications | **Full** | None |
| §II.B Validation methodology | **Full** | Non-structural performance metrics (accuracy, AUC) not in scope |
| §II.C Performance monitoring | **Full** | Requires `--sign` for full Sigstore coverage; unsigned receipts have partial coverage |
