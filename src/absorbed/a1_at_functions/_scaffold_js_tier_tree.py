"""Wire scanner for JS/TS upward imports."""

from pathlib import Path

from atomadic_forge.a1_at_functions.wire_check import scan_violations


def _scaffold_js_tier_tree(root: Path) -> Path:
    """Build a JS-flavoured tier tree: <root>/aN_*/*.js."""
    for tier in ("a0_qk_constants", "a1_at_functions", "a2_mo_composites",
                  "a3_og_features", "a4_sy_orchestration"):
        (root / tier).mkdir(parents=True, exist_ok=True)
    return root


def test_wire_scan_clean_js_tree(tmp_path):
    base = _scaffold_js_tier_tree(tmp_path)
    (base / "a1_at_functions" / "math.js").write_text(
        "import { TYPES } from '../a0_qk_constants/types.js';\n"
        "export function add(a, b) { return a + b; }\n",
        encoding="utf-8",
    )
    (base / "a0_qk_constants" / "types.js").write_text(
        "export const TYPES = { A: 1 };\n", encoding="utf-8")
    report = scan_violations(base)
    assert report["verdict"] == "PASS"
    assert report["violation_count"] == 0


def test_wire_scan_detects_upward_es6_import(tmp_path):
    base = _scaffold_js_tier_tree(tmp_path)
    (base / "a1_at_functions" / "bad.js").write_text(
        "import { feat } from '../a3_og_features/feature.js';\n"
        "export function go() { return feat(); }\n",
        encoding="utf-8",
    )
    report = scan_violations(base)
    assert report["verdict"] == "FAIL"
    assert report["violation_count"] >= 1
    v = report["violations"][0]
    assert v["from_tier"] == "a1_at_functions"
    assert v["to_tier"] == "a3_og_features"
    assert v["language"] == "javascript"


def test_wire_scan_detects_upward_commonjs_require(tmp_path):
    base = _scaffold_js_tier_tree(tmp_path)
    (base / "a2_mo_composites" / "store.js").write_text(
        "const orchestrator = require('../a4_sy_orchestration/main.js');\n"
        "module.exports = { run: () => orchestrator.run() };\n",
        encoding="utf-8",
    )
    report = scan_violations(base)
    assert report["verdict"] == "FAIL"
    v = report["violations"][0]
    assert v["from_tier"] == "a2_mo_composites"
    assert v["to_tier"] == "a4_sy_orchestration"


def test_wire_scan_detects_upward_typescript(tmp_path):
    base = _scaffold_js_tier_tree(tmp_path)
    (base / "a1_at_functions" / "bad.ts").write_text(
        "import { Feat } from '../a3_og_features/feature';\n"
        "export const go = () => Feat();\n",
        encoding="utf-8",
    )
    report = scan_violations(base)
    assert report["verdict"] == "FAIL"
    v = next(v for v in report["violations"] if v["file"].endswith(".ts"))
    assert v["language"] == "typescript"


def test_wire_scan_skips_node_modules(tmp_path):
    base = _scaffold_js_tier_tree(tmp_path)
    nm = base / "a1_at_functions" / "node_modules" / "x"
    nm.mkdir(parents=True)
    (nm / "index.js").write_text(
        "import x from '../../../a3_og_features/feature.js';\n",
        encoding="utf-8",
    )
    report = scan_violations(base)
    assert report["verdict"] == "PASS"


def test_wire_scan_polyglot_violations(tmp_path):
    base = _scaffold_js_tier_tree(tmp_path)
    (base / "a1_at_functions" / "bad.py").write_text(
        "from demo.a3_og_features.feature import x\n", encoding="utf-8")
    (base / "a1_at_functions" / "bad.js").write_text(
        "import { y } from '../a3_og_features/feat.js';\n", encoding="utf-8")
    report = scan_violations(base)
    assert report["violation_count"] >= 2
    langs = {v["language"] for v in report["violations"]}
    assert {"python", "javascript"} <= langs
