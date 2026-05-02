"""Tier a1 — pure planner for ``forge enforce``.

Golden Path Lane A W6 deliverable. Consumes a wire report with W5
F-codes attached and emits a list of mechanical fix actions. Pure:
the planner reads the wire report and inspects file paths only — it
does NOT mutate anything. Application is a separate concern (see
``a3/forge_enforce.py``).

Action shape:
    {
        "f_code":      "F0042",
        "action":      "move_file_up",
        "src":         "a1_at_functions/helper.py",
        "dest":        "a3_og_features/helper.py",
        "violations":  [<wire violation dict>, ...],
        "auto_apply":  true,
        "warnings":    [str, ...],   # populated when the move has risks
    }

The planner today implements one action: ``move_file_up`` for the six
canonical upward-import F-codes (F0041–F0046). F0040 (a0 importing
anything) and F0049 (unknown-shape) are emitted as ``review_manually``
actions with no auto_apply.

Pre-flight risks the planner detects (and surfaces as warnings, not
exceptions):
  * the destination path already exists (would clobber)
  * the source file has multiple distinct destination tiers across
    its violations (ambiguous; safest is review)
  * the source file is itself imported by other files in the package
    (those callers' imports would need rewriting — out of scope for
    W6 v1; W7 will own this)
"""
from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path
from typing import TypedDict


class EnforceAction(TypedDict, total=False):
    """One proposed mechanical fix. See module docstring."""
    f_code: str
    action: str             # 'move_file_up' | 'review_manually'
    src: str                # repo-relative posix path
    dest: str               # repo-relative posix path (move target)
    violations: list[dict]
    auto_apply: bool
    warnings: list[str]


def _file_imports_in_package(
    package_root: Path,
    target_relpath: str,
) -> list[str]:
    """Return repo-relative paths of files that import the target.

    Heuristic: looks for ``from <…>.target_module_name import``
    or ``from <…>.target_module_name`` patterns where target_module_name
    is the file stem of ``target_relpath``. Cheap regex-quality
    proxy for a real symbol-resolution pass; the W6 acceptance is
    "smoke covers 7 fix paths", not "full inbound-edge analysis".

    Used purely to populate ``warnings`` when a move could break
    inbound callers — the planner does not block on this signal.
    """
    target = Path(target_relpath)
    stem = target.stem
    if not stem or stem.startswith("_"):
        return []
    out: list[str] = []
    for f in package_root.rglob("*.py"):
        if f.is_dir():
            continue
        rel = f.relative_to(package_root).as_posix()
        if rel == target_relpath:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if f"import {stem}" not in text and f".{stem}" not in text:
            continue
        # Confirm via AST so we don't trip on string literals.
        try:
            tree = ast.parse(text, filename=str(f))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = (node.module or "").split(".")
                if stem in module:
                    out.append(rel)
                    break
                if any(alias.name == stem for alias in node.names):
                    out.append(rel)
                    break
            elif isinstance(node, ast.Import):
                if any(alias.name.endswith("." + stem) or alias.name == stem
                       for alias in node.names):
                    out.append(rel)
                    break
    return sorted(set(out))


def plan_actions(
    wire_report: dict,
    *,
    package_root: Path | None = None,
) -> list[EnforceAction]:
    """Group violations by file and emit one EnforceAction per file.

    A file with multiple violations to the same higher tier yields a
    single move action covering them all. A file with violations to
    DIFFERENT tiers gets a review_manually action with warnings.

    ``package_root`` (optional): when provided, the planner inspects
    inbound imports across the package and adds warnings; without it
    the action's warnings list stays empty.
    """
    by_file: dict[str, list[dict]] = defaultdict(list)
    for v in wire_report.get("violations", []) or []:
        by_file[v["file"]].append(v)

    actions: list[EnforceAction] = []
    for file_path, viols in sorted(by_file.items()):
        f_codes = {v.get("f_code", "") for v in viols}
        to_tiers = {v["to_tier"] for v in viols}
        # F0040 / F0049: not auto-fixable.
        if "F0040" in f_codes or "F0049" in f_codes or not f_codes:
            actions.append(EnforceAction(
                f_code=next(iter(f_codes)) if f_codes else "F0049",
                action="review_manually",
                src=file_path,
                dest="",
                violations=viols,
                auto_apply=False,
                warnings=[
                    "violation requires manual review (a0 special-case "
                    "or non-canonical tier shape)",
                ],
            ))
            continue
        # Multiple distinct destination tiers: ambiguous.
        if len(to_tiers) > 1:
            actions.append(EnforceAction(
                f_code=sorted(f_codes)[0],
                action="review_manually",
                src=file_path,
                dest="",
                violations=viols,
                auto_apply=False,
                warnings=[
                    f"file imports from multiple higher tiers ({sorted(to_tiers)}); "
                    "no single mechanical destination — review manually",
                ],
            ))
            continue
        # Single canonical move.
        target_tier = next(iter(to_tiers))
        src = file_path
        dest = f"{target_tier}/{Path(src).name}"
        warnings: list[str] = []
        if package_root is not None:
            try:
                inbound = _file_imports_in_package(package_root, src)
            except OSError:
                inbound = []
            if inbound:
                warnings.append(
                    f"{len(inbound)} other file(s) import this module — "
                    "their imports will need rewriting after the move: "
                    + ", ".join(inbound[:5])
                    + ("…" if len(inbound) > 5 else "")
                )
            dest_path = package_root / dest
            if dest_path.exists():
                warnings.append(
                    f"destination {dest} already exists; move would clobber"
                )
        actions.append(EnforceAction(
            f_code=sorted(f_codes)[0],
            action="move_file_up",
            src=src,
            dest=dest,
            violations=viols,
            auto_apply=not warnings,
            warnings=warnings,
        ))
    return actions


def summarize_plan(actions: list[EnforceAction]) -> dict:
    """Reduce a plan to summary stats. Used by CLI human + JSON output."""
    auto = sum(1 for a in actions if a.get("auto_apply"))
    review = sum(1 for a in actions if not a.get("auto_apply"))
    by_fcode: dict[str, int] = defaultdict(int)
    for a in actions:
        by_fcode[a.get("f_code", "F????")] += 1
    return {
        "schema_version": "atomadic-forge.enforce.plan/v1",
        "action_count": len(actions),
        "auto_apply_count": auto,
        "review_count": review,
        "by_fcode": dict(sorted(by_fcode.items())),
        "actions": list(actions),
    }
