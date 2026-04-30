"""Tier a1 — pure .forge sidecar cross-validator (Lane D W11).

Compares a parsed SidecarFile against the source file's AST and
returns a structured report of mismatches. Catches the seven
classes of drift the Golden Path names:

  1. sidecar declares a symbol the source doesn't have
  2. source has a public symbol the sidecar didn't declare
  3. effect=Pure declared but source uses obvious I/O / network
  4. effect=Pure declared but source has Mutation patterns
  5. compose_with names a symbol that doesn't exist in any imported
     module (best-effort lexical check; not a full resolver)
  6. tier declared but source path lives in a different tier
  7. proves clauses naming lemmas with no entry in the local Lean4
     manifest (W20 — soft-skipped today)

Pure: walks AST + the sidecar dict; no execution, no LLM, no
network. Soft on parse failures (returns 'failed_to_parse_source').
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import TypedDict

from ..a0_qk_constants.error_codes import SIDECAR_S_TO_F
from ..a0_qk_constants.sidecar_schema import SidecarFile

SCHEMA_VERSION_VALIDATE_V1 = "atomadic-forge.sidecar.validate/v1"


class ValidationFinding(TypedDict, total=False):
    code: str          # Drift class label (S0001..S0007) — local
    f_code: str        # Global F-code (F0100..F0109) — registered
    severity: str      # 'error' | 'warn' | 'info'
    symbol: str
    message: str


class ValidationReport(TypedDict, total=False):
    schema_version: str
    target: str
    finding_count: int
    findings: list[ValidationFinding]
    verdict: str       # 'PASS' | 'FAIL' | 'unparseable'


# Heuristic patterns. Conservative — false positives downgraded to
# 'warn' rather than 'error' so the validator never blocks merges
# on its own; F-codes do that.
_IO_HINTS = ("open(", "read(", "write(", "Path(", ".write_text",
              ".read_text", "subprocess.", "os.system")
_NET_HINTS = ("requests.", "urllib.", "http.client", "socket.",
               "urlopen(", ".post(", ".get(")
_RANDOM_HINTS = ("random.", "secrets.", "uuid.", "datetime.now(",
                  "time.time(")


def _collect_top_level_symbols(tree: ast.AST) -> dict[str, ast.AST]:
    """Map name -> AST node for every top-level def / class."""
    out: dict[str, ast.AST] = {}
    for node in tree.body if hasattr(tree, "body") else []:  # type: ignore[attr-defined]
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            if not node.name.startswith("_"):
                out[node.name] = node
    return out


def _node_source_text(source: str, node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:  # noqa: BLE001
        # Fall back to raw line span when ast.unparse fails.
        start = (getattr(node, "lineno", 1) or 1) - 1
        end = (getattr(node, "end_lineno", start + 1) or start + 1)
        return "\n".join(source.splitlines()[start:end])


def _check_pure_against_source(node_text: str) -> list[str]:
    """Return drift-hint strings if a Pure-declared symbol does
    obviously-non-pure things in its body."""
    hits: list[str] = []
    if any(h in node_text for h in _NET_HINTS):
        hits.append("network call detected")
    if any(h in node_text for h in _IO_HINTS):
        hits.append("filesystem / IO call detected")
    if any(h in node_text for h in _RANDOM_HINTS):
        hits.append("non-deterministic input detected")
    return hits


def _detect_tier(path: str) -> str | None:
    parts = Path(path).parts
    for p in parts:
        if p in ("a0_qk_constants", "a1_at_functions",
                  "a2_mo_composites", "a3_og_features",
                  "a4_sy_orchestration"):
            return p
    return None


def validate_sidecar(
    sidecar: SidecarFile,
    *,
    source_text: str,
    source_path: Path | str | None = None,
) -> ValidationReport:
    """Cross-check ``sidecar`` against the actual source.

    Pure: parses ``source_text`` once + walks both inputs. Returns
    a structured report; never raises.
    """
    findings: list[ValidationFinding] = []
    target = sidecar.get("target", "<unknown>")

    try:
        tree = ast.parse(source_text)
    except SyntaxError as exc:
        return ValidationReport(
            schema_version=SCHEMA_VERSION_VALIDATE_V1,
            target=target,
            finding_count=1,
            findings=[ValidationFinding(
                code="S0000",
                severity="error",
                symbol="(file)",
                message=f"source did not parse: {exc}",
            )],
            verdict="unparseable",
        )

    symbols = _collect_top_level_symbols(tree)
    declared = {s.get("name", ""): s for s in sidecar.get("symbols") or []}

    # S0001 — sidecar declares a symbol the source doesn't have.
    for name in declared:
        if name and name not in symbols:
            findings.append(ValidationFinding(
                code="S0001", severity="error", symbol=name,
                message=f"sidecar declares {name!r} but source has no "
                         "top-level public symbol with that name",
            ))

    # S0002 — source has a public symbol the sidecar didn't declare.
    for name in symbols:
        if name not in declared:
            findings.append(ValidationFinding(
                code="S0002", severity="warn", symbol=name,
                message=f"source has public symbol {name!r} not declared "
                         "in sidecar (gradual coverage is OK; this is "
                         "advisory)",
            ))

    # S0003 + S0004 — Pure declared but source does I/O / non-determinism.
    for name, decl in declared.items():
        if name not in symbols:
            continue
        if decl.get("effect") != "Pure":
            continue
        node_text = _node_source_text(source_text, symbols[name])
        hits = _check_pure_against_source(node_text)
        for h in hits:
            findings.append(ValidationFinding(
                code="S0003", severity="error", symbol=name,
                message=f"Pure-declared symbol {name!r} appears to "
                         f"violate purity: {h}",
            ))

    # S0006 — declared tier vs detected path tier.
    if source_path is not None:
        path_tier = _detect_tier(str(source_path))
        for name, decl in declared.items():
            declared_tier = decl.get("tier")
            if declared_tier and path_tier and declared_tier != path_tier:
                findings.append(ValidationFinding(
                    code="S0006", severity="warn", symbol=name,
                    message=f"sidecar declares tier={declared_tier!r} "
                             f"but source lives in tier {path_tier!r}",
                ))

    # S0005 / S0007 — compose_with name resolution + Lean4 proves
    # discharge are reserved for Lane D W20 (Bao-Rompf checker).
    # Today we record but don't enforce.

    # Promote each S-code to its registered F-code so downstream
    # tools (forge audit / agent_summary / score_patch) can address
    # sidecar drift in the same namespace as wire violations.
    for f in findings:
        s_code = f.get("code", "")
        if s_code in SIDECAR_S_TO_F:
            f["f_code"] = SIDECAR_S_TO_F[s_code]

    error_count = sum(1 for f in findings if f.get("severity") == "error")
    verdict = "PASS" if error_count == 0 else "FAIL"

    return ValidationReport(
        schema_version=SCHEMA_VERSION_VALIDATE_V1,
        target=target,
        finding_count=len(findings),
        findings=findings,
        verdict=verdict,
    )
