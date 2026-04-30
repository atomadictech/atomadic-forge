"""Tier a1 — pure manifest diff for atomadic-forge.* JSON reports.

Compares two Forge manifests (scout / cherry / assimilate / wire / certify /
synergy / emergent / any other forge schema) and emits a structured diff.

This module is pure: no file I/O, no subprocess, no a2+ imports. Callers
load JSON themselves and pass the parsed dicts in.
"""

from __future__ import annotations

from typing import Any

# Bound recursion + collection size so a 50MB manifest can never blow up.
_MAX_DEPTH = 6
_MAX_LIST_ITEMS = 100
_TRUNCATED = "...truncated"

_DIFF_SCHEMA = "atomadic-forge.diff/v1"
_FORGE_PREFIX = "atomadic-forge."


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _require_forge_manifest(m: Any, side: str) -> str:
    if not isinstance(m, dict):
        raise ValueError(
            f"{side} manifest is not a JSON object — expected a dict with a "
            f"`schema_version` starting with `{_FORGE_PREFIX}`."
        )
    sv = m.get("schema_version")
    if not isinstance(sv, str) or not sv.startswith(_FORGE_PREFIX):
        raise ValueError(
            f"{side} manifest has no recognisable forge `schema_version` — "
            f"expected a string starting with `{_FORGE_PREFIX}`, got {sv!r}."
        )
    return sv


def _schema_family(schema_version: str) -> str:
    """Strip the trailing `/vN`. `atomadic-forge.certify/v1` -> `atomadic-forge.certify`."""
    return schema_version.rsplit("/", 1)[0]


def _format_delta(n: int | float) -> str:
    if n == 0:
        return "0"
    return f"+{n}" if n > 0 else f"{n}"


def _bounded_list(items: list, depth: int) -> list:
    """Truncate long lists; recursively bound nested values."""
    if len(items) > _MAX_LIST_ITEMS:
        head = [_bound_value(v, depth + 1) for v in items[:_MAX_LIST_ITEMS]]
        head.append(_TRUNCATED)
        return head
    return [_bound_value(v, depth + 1) for v in items]


def _bound_value(v: Any, depth: int) -> Any:
    """Recursively cap depth + list size for safe inclusion in the diff."""
    if depth >= _MAX_DEPTH:
        if isinstance(v, dict | list):
            return _TRUNCATED
        return v
    if isinstance(v, dict):
        return {k: _bound_value(val, depth + 1) for k, val in v.items()}
    if isinstance(v, list):
        return _bounded_list(v, depth)
    return v


# --------------------------------------------------------------------------- #
# generic recursive diff
# --------------------------------------------------------------------------- #

def _walk(left: Any, right: Any, path: str, depth: int,
          added: list, removed: list, changed: list) -> None:
    """Recursive diff that respects _MAX_DEPTH and bounds list inclusions."""
    if depth >= _MAX_DEPTH:
        if left != right:
            changed.append({"path": path or "<root>",
                            "left": _TRUNCATED, "right": _TRUNCATED})
        return

    if isinstance(left, dict) and isinstance(right, dict):
        l_keys = set(left.keys())
        r_keys = set(right.keys())
        for k in sorted(r_keys - l_keys):
            sub = f"{path}.{k}" if path else k
            added.append({"path": sub, "value": _bound_value(right[k], depth + 1)})
        for k in sorted(l_keys - r_keys):
            sub = f"{path}.{k}" if path else k
            removed.append({"path": sub, "value": _bound_value(left[k], depth + 1)})
        for k in sorted(l_keys & r_keys):
            sub = f"{path}.{k}" if path else k
            _walk(left[k], right[k], sub, depth + 1, added, removed, changed)
        return

    if isinstance(left, list) and isinstance(right, list):
        # Treat lists as opaque values when they differ — element-wise diffs
        # explode in size for big manifests. Per-schema summaries below
        # handle the *interesting* lists (violations, candidates).
        if left != right:
            changed.append({
                "path": path or "<root>",
                "left": _bound_value(left, depth + 1),
                "right": _bound_value(right, depth + 1),
            })
        return

    if left != right:
        changed.append({
            "path": path or "<root>",
            "left": _bound_value(left, depth + 1),
            "right": _bound_value(right, depth + 1),
        })


# --------------------------------------------------------------------------- #
# per-schema summaries
# --------------------------------------------------------------------------- #

def _summary_certify(left: dict, right: dict) -> dict:
    summary: dict[str, Any] = {}
    l_score = left.get("score", 0) or 0
    r_score = right.get("score", 0) or 0
    summary["score_delta"] = _format_delta(r_score - l_score)

    axis_keys = (
        "documentation_complete", "tests_present", "tier_layout_present",
        "no_upward_imports", "no_stub_bodies", "package_importable",
        "ci_workflow_present", "changelog_present",
    )
    flips: list[dict] = []
    for k in axis_keys:
        if k not in left or k not in right:
            continue
        lv, rv = bool(left[k]), bool(right[k])
        if lv != rv:
            flips.append({"axis": k, "left": lv, "right": rv,
                          "direction": "regressed" if lv and not rv else "improved"})
    if flips:
        summary["axis_flips"] = flips

    l_ratio = left.get("test_pass_ratio")
    r_ratio = right.get("test_pass_ratio")
    if isinstance(l_ratio, int | float) and isinstance(r_ratio, int | float):
        summary["test_pass_ratio_delta"] = _format_delta(round(r_ratio - l_ratio, 4))
    return summary


def _summary_wire(left: dict, right: dict) -> dict:
    l_v = left.get("violations", []) or []
    r_v = right.get("violations", []) or []
    l_count = left.get("violation_count", len(l_v))
    r_count = right.get("violation_count", len(r_v))

    def _key(v: dict) -> tuple:
        return (v.get("file", ""), v.get("from_tier", ""),
                v.get("to_tier", ""), v.get("imported", ""))

    l_keys = {_key(v) for v in l_v if isinstance(v, dict)}
    r_keys = {_key(v) for v in r_v if isinstance(v, dict)}
    new_keys = r_keys - l_keys
    fixed_keys = l_keys - r_keys

    new_violations = [v for v in r_v if isinstance(v, dict) and _key(v) in new_keys]
    fixed_violations = [v for v in l_v if isinstance(v, dict) and _key(v) in fixed_keys]

    summary: dict[str, Any] = {
        "violations_delta": _format_delta(r_count - l_count),
        "left_verdict": left.get("verdict"),
        "right_verdict": right.get("verdict"),
    }
    if new_violations:
        summary["new_violations"] = _bounded_list(new_violations, 1)
    if fixed_violations:
        summary["fixed_violations"] = _bounded_list(fixed_violations, 1)
    return summary


def _summary_scout_like(left: dict, right: dict) -> dict:
    """Covers scout/v1 and assimilate/v1 — both have tier_distribution + symbol_count."""
    summary: dict[str, Any] = {}

    l_sc = left.get("symbol_count")
    r_sc = right.get("symbol_count")
    if isinstance(l_sc, int) and isinstance(r_sc, int):
        summary["symbol_count_delta"] = _format_delta(r_sc - l_sc)

    l_td = left.get("tier_distribution") or {}
    r_td = right.get("tier_distribution") or {}
    if isinstance(l_td, dict) and isinstance(r_td, dict):
        td_delta: dict[str, str] = {}
        for tier in sorted(set(l_td) | set(r_td)):
            lv = int(l_td.get(tier, 0) or 0)
            rv = int(r_td.get(tier, 0) or 0)
            if lv != rv:
                td_delta[tier] = _format_delta(rv - lv)
        if td_delta:
            summary["tier_distribution_delta"] = td_delta

    # assimilate adds components_emitted
    l_ce = left.get("components_emitted")
    r_ce = right.get("components_emitted")
    if isinstance(l_ce, int) and isinstance(r_ce, int):
        summary["components_emitted_delta"] = _format_delta(r_ce - l_ce)
    return summary


def _summary_synergy(left: dict, right: dict) -> dict:
    l_c = left.get("candidates", []) or []
    r_c = right.get("candidates", []) or []
    l_count = left.get("candidate_count", len(l_c))
    r_count = right.get("candidate_count", len(r_c))

    def _id(c: dict) -> str:
        return str(c.get("candidate_id", ""))

    l_ids = {_id(c) for c in l_c if isinstance(c, dict)}
    r_ids = {_id(c) for c in r_c if isinstance(c, dict)}
    new = sorted(r_ids - l_ids)
    dropped = sorted(l_ids - r_ids)

    summary: dict[str, Any] = {
        "candidate_count_delta": _format_delta(r_count - l_count),
    }
    if new:
        summary["new_candidates"] = new[:_MAX_LIST_ITEMS]
    if dropped:
        summary["dropped_candidates"] = dropped[:_MAX_LIST_ITEMS]
    return summary


def _summary_emergent(left: dict, right: dict) -> dict:
    summary: dict[str, Any] = {}
    l_cs = left.get("catalog_size")
    r_cs = right.get("catalog_size")
    if isinstance(l_cs, int) and isinstance(r_cs, int):
        summary["catalog_size_delta"] = _format_delta(r_cs - l_cs)
    l_ch = left.get("chain_count_considered")
    r_ch = right.get("chain_count_considered")
    if isinstance(l_ch, int) and isinstance(r_ch, int):
        summary["chain_count_delta"] = _format_delta(r_ch - l_ch)
    # candidate-level diff matches synergy
    cand_diff = _summary_synergy(left, right)
    if "candidate_count_delta" in cand_diff:
        summary["candidate_count_delta"] = cand_diff["candidate_count_delta"]
    if "new_candidates" in cand_diff:
        summary["new_candidates"] = cand_diff["new_candidates"]
    if "dropped_candidates" in cand_diff:
        summary["dropped_candidates"] = cand_diff["dropped_candidates"]
    return summary


_SUMMARY_BY_FAMILY: dict[str, Any] = {
    "atomadic-forge.certify": _summary_certify,
    "atomadic-forge.wire": _summary_wire,
    "atomadic-forge.scout": _summary_scout_like,
    "atomadic-forge.assimilate": _summary_scout_like,
    "atomadic-forge.synergy.scan": _summary_synergy,
    "atomadic-forge.emergent.scan": _summary_emergent,
}


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #

def diff_manifests(left: dict, right: dict) -> dict:
    """Compare two forge manifests and return a structured diff.

    Both manifests must declare a ``schema_version`` that starts with
    ``atomadic-forge.`` — otherwise raise ``ValueError``.
    """
    l_schema = _require_forge_manifest(left, "left")
    r_schema = _require_forge_manifest(right, "right")

    l_family = _schema_family(l_schema)
    r_family = _schema_family(r_schema)
    compatible = l_family == r_family

    summary: dict[str, Any] = {}
    if compatible:
        builder = _SUMMARY_BY_FAMILY.get(l_family)
        if builder is not None:
            summary = builder(left, right)

    added: list = []
    removed: list = []
    changed: list = []
    _walk(left, right, "", 0, added, removed, changed)

    # Truncate the generic walks too — keep the diff manifest itself bounded.
    if len(added) > _MAX_LIST_ITEMS:
        added = added[:_MAX_LIST_ITEMS] + [_TRUNCATED]
    if len(removed) > _MAX_LIST_ITEMS:
        removed = removed[:_MAX_LIST_ITEMS] + [_TRUNCATED]
    if len(changed) > _MAX_LIST_ITEMS:
        changed = changed[:_MAX_LIST_ITEMS] + [_TRUNCATED]

    return {
        "schema_version": _DIFF_SCHEMA,
        "left_schema": l_schema,
        "right_schema": r_schema,
        "compatible": compatible,
        "summary": summary,
        "added": added,
        "removed": removed,
        "changed": changed,
    }
