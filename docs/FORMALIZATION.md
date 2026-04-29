# Formalization: how the certify checks map to the papers

This page is a **citation map**, not a re-derivation. It connects the
gates that `forge certify` actually runs to the formal claims in two
papers:

- **AAM v1.0** — *The Atomadic Architecture Machine: Effect-Constrained
  Cross-Language Program Synthesis via Unified E-Graph Knowledge
  Graphs.* The architecture-substrate paper. Defines the effect lattice
  (a0..a4), the upward-only composition law, and the certification
  axes.
- **BEP v1.0** — *The Breakthrough Engine Protocol: Convergence
  Theorem.* The iterative-improvement paper. Proves that the
  iterate/evolve loop converges and that the converged specification is
  locally optimal.

Each Forge gate cites the paper section that justifies it. If a claim
on this page does not match a paper section, the page is the bug — file
an issue.

---

## The seven gates `forge certify` runs

Forge certify scores out of **100** in two layers:

**Structural axes (4 × 25 = 100 baseline):**

1. **documentation** (25 pts)
2. **tests-present** (25 pts)
3. **tier_layout** (25 pts)
4. **import_discipline** (25 pts)

**Behavioural axes (Python-only today, +25 / +30 over baseline when earned):**

5. **runtime-import smoke** (+25 pts)
6. **behavioural pytest** (+30 pts)

JS / TS packages cap at **60/100** today: they earn the four
structural axes, but the +25 runtime-import smoke and +30 behavioural
pytest are Python-only. Wiring `npm test` / Vitest into the
behavioural axis is on the 0.3 roadmap.

---

## Mapping each gate to the papers

### Gate 1 — `documentation` (25 pts)

**What it checks.** A `README.md` is present and a `docs/` directory
contains at least one substantive document.

**Why it is in the certify schema.** AAM §4 (Governance Runtime)
treats documentation as a first-class governance artifact: a tier tree
with no human-readable narrative cannot be audited, only mechanically
verified. The certify score therefore refuses to award a "complete"
verdict to an undocumented tree, even one that passes every other
gate.

**Citation.** AAM §4 (Governance Runtime); AAM §5.4 (Threats to
Validity, item on documentation drift).

---

### Gate 2 — `tests-present` (25 pts)

**What it checks.** A `tests/` directory exists and contains at least
one test file.

**Why it is in the certify schema.** AAM §3.4 (Effect-Constrained
Grammar Derivation) requires that emitted code be testable in
isolation tier-by-tier. The presence of a tests directory is the
weakest possible witness of that requirement — a structural pre-check
before the behavioural gates run.

**Citation.** AAM §3.4 (Effect-Constrained Grammar Derivation); AAM
§5.1 (Core Pipeline Pseudocode, test-emission step).

---

### Gate 3 — `tier_layout` (25 pts)

**What it checks.** All five tier directories
(`a0_qk_constants/`, `a1_at_functions/`, `a2_mo_composites/`,
`a3_og_features/`, `a4_sy_orchestration/`) are present and non-empty.

**Why it is in the certify schema.** AAM §2.1 (Formal Definition of the
Atomadic Effect Lattice) defines the five-tier ordering as the lattice
*L = {a0 < a1 < a2 < a3 < a4}*. A tree missing one of the five tiers
is not a valid element of the lattice, so the upward-only composition
law (Gate 4) cannot be evaluated against it.

**Citation.** AAM §2.1 (Formal Definition); AAM §2.2 (Grounding in
2025 Effect Systems Research).

---

### Gate 4 — `import_discipline` (25 pts)

**What it checks.** Every import in the tree flows upward only:
`aN` may import from `a0..a(N-1)`, never from `a(N+1)..a4`. Sideways
imports within the same tier are allowed; downward imports are not.

**Why it is in the certify schema.** This *is* the AAM core invariant.
AAM §2.1 states the upward-only law as the single composition rule of
the lattice. AAM §3.5 (Cross-Language Generation via E-Graph
Extraction) shows that violating it produces non-extractable e-graphs
— i.e. the architecture loses the cross-language generation property
the paper is named for.

This gate is the strictest: any single violation drops the score from
25 to 0 on this axis. There is no partial credit.

**Citation.** AAM §2.1 (Formal Definition, upward-only law); AAM §3.5
(Cross-Language Generation).

---

### Gate 5 — `runtime-import smoke` (+25 pts, Python-only)

**What it checks.** The materialized package actually loads in a fresh
Python subprocess: `python -c "import your_package"` exits 0. This is
weaker than running tests but stronger than a static AST check.

**Why it is in the certify schema.** AAM §5.1 (Core Pipeline
Pseudocode) lists "package imports cleanly in a fresh interpreter" as
a discrete gate between structural conformance and behavioural
verification. It catches the class of bugs where the AST is valid, the
imports are upward-only, but a circular initialization or missing
runtime dependency makes the package unusable.

**Why JS/TS does not get this gate yet.** AAM §5.4 (Threats to
Validity) explicitly flags polyglot runtime gating as a v0.3 roadmap
item: the equivalent for JS would be an `npm test` invocation, which
requires a Node toolchain we do not yet bundle.

**Citation.** AAM §5.1 (Core Pipeline Pseudocode); AAM §5.4 (Threats
to Validity, polyglot section).

---

### Gate 6 — `behavioural pytest` (+30 pts, Python-only)

**What it checks.** `pytest` runs against the materialized package and
all collected tests pass. Failures or errors collapse this axis to 0.

**Why it is in the certify schema.** AAM §5.1 specifies a behavioural
verification step distinct from the structural axes. This is *the*
gate that distinguishes a tier-correct package from a working package.

**Connection to BEP convergence.** When the certify score is fed back
into `forge iterate` / `forge evolve` as the evaluation function E,
BEP Theorem 1 (Monotonic Improvement) guarantees that successive
rounds do not regress, and BEP Theorem 2 (Convergence) guarantees the
iterate/evolve loop terminates at a fixed point. The behavioural axis
is the dominant signal driving that monotonic improvement: the four
structural axes saturate quickly at 100/100 (25+25+25+25), so the
remaining headroom is the +30 behavioural axis plus the +25
runtime-import axis. BEP Corollary 4 (Self-Hosting Property) is what
lets us trust that "Forge generated this package, then certified it
itself" is a meaningful claim rather than circular.

**Citation.** AAM §5.1 (Core Pipeline Pseudocode); BEP §3 Theorem 1
(Monotonic Improvement); BEP §3 Theorem 2 (Convergence); BEP §3
Corollary 4 (Self-Hosting Property).

---

## What is *not* yet formalized

The following are roadmap items, not current claims:

- **Cryptographic signing** of certify reports — the schema is final,
  the signing pipeline is Lane G5.
- **Global optimality** of the iterate/evolve fixed point — BEP §5
  flags this as a strengthening direction; today we have only local
  optimality (BEP Theorem 3).
- **Polyglot behavioural gating** — JS / TS today caps at 60/100
  because the +25 / +30 axes are Python-only. AAM §5.4 lists this as
  v0.3.
- **Effect-system soundness proof** for the JS regex-based parser —
  AAM §3.1 (4-Layer Universal AST Normalization) treats this as
  honest-but-incomplete: the Python AST path is sound, the JS path is
  syntactic.

When any of these land, this page will be updated and the relevant
gate description will gain a new citation.

---

## Source papers (read these for the proofs)

- `C:\!!AtomadicStandard\research\Atomadic_Architecture_Machine_v1_Paper.md`
- `C:\!!AtomadicStandard\research\BEP_Convergence_Theorem_v1.0.md`

These are private research artifacts. The public-facing summary is
this page plus [SHOWCASE.md](SHOWCASE.md).
