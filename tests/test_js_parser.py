"""Tier-agnostic tests for the pure JS / TS surface parser."""

from atomadic_forge.a1_at_functions.js_parser import (
    classify_js_tier, detect_js_effects, parse_imports, parse_surface,
    strip_comments_and_strings,
)


def test_strip_block_and_line_comments():
    src = """
    /* import 'should-not-be-found' */
    // import 'also-skip'
    import 'real-one';
    """
    assert "should-not-be-found" not in strip_comments_and_strings(src)
    assert "also-skip" not in strip_comments_and_strings(src)


def test_parse_es6_import_default():
    src = """import foo from "bar";"""
    assert parse_imports(src) == ["bar"]


def test_parse_es6_import_named():
    src = """import { a, b } from "../a1_at_functions/utils.js";"""
    assert parse_imports(src) == ["../a1_at_functions/utils.js"]


def test_parse_es6_import_namespace():
    src = """import * as ns from "x";"""
    assert parse_imports(src) == ["x"]


def test_parse_es6_import_mixed():
    src = """import a, { b, c } from "lib";"""
    assert parse_imports(src) == ["lib"]


def test_parse_es6_import_side_effect_only():
    src = """import "polyfill";"""
    assert parse_imports(src) == ["polyfill"]


def test_parse_dynamic_import():
    src = """const m = await import("./lazy.js");"""
    assert parse_imports(src) == ["./lazy.js"]


def test_parse_commonjs_require():
    src = """
    const fs = require('fs');
    const { join } = require("path");
    """
    assert parse_imports(src) == ["fs", "path"]


def test_parse_imports_dedupes():
    src = """import a from "x"; import b from "x"; const c = require("x");"""
    assert parse_imports(src) == ["x"]


def test_parse_imports_inside_string_literal_skipped():
    src = """const note = "import notreal from 'fake';"; import real from "ok";"""
    assert parse_imports(src) == ["ok"]


def test_parse_surface_exports_function():
    src = "export function add(a, b) { return a + b; }"
    s = parse_surface(src)
    assert s.exported_functions == ["add"]
    assert s.has_class is False


def test_parse_surface_exports_class():
    src = "export class Store { constructor() { this.x = 1; } }"
    s = parse_surface(src)
    assert s.exported_classes == ["Store"]
    assert s.has_class is True


def test_parse_surface_exports_const():
    src = "export const FOO = 42;\nexport const BAR = 'a';"
    s = parse_surface(src)
    assert s.exported_consts == ["FOO", "BAR"]


def test_parse_surface_default_object_with_fetch():
    src = """
    export default {
        async fetch(req, env) { return new Response("ok"); },
        scheduled() {},
    };
    """
    s = parse_surface(src)
    assert s.default_export_kind == "object"
    assert "fetch" in s.default_export_keys
    assert "scheduled" in s.default_export_keys
    assert s.has_worker_default_fetch is True
    assert s.has_scheduled_handler is True


def test_parse_surface_module_exports():
    src = "module.exports = { a: 1, b: 2 };\nexports.helper = () => 3;"
    s = parse_surface(src)
    assert s.has_module_exports is True
    assert "helper" in s.exported_consts


def test_classify_js_tier_explicit_directory_wins():
    s = parse_surface("export const X = 1;")
    assert classify_js_tier(path="src/a3_og_features/foo.js",
                              surface=s) == "a3_og_features"


def test_classify_js_tier_constants_only():
    s = parse_surface("export const KV = { A: 'a' };\nexport const N = 1;")
    assert classify_js_tier(path="lib/keys.js", surface=s) == "a0_qk_constants"


def test_classify_js_tier_pure_function():
    s = parse_surface("export function add(a, b) { return a + b; }")
    assert classify_js_tier(path="lib/math.js", surface=s) == "a1_at_functions"


def test_classify_js_tier_class_is_composite():
    s = parse_surface("class S { constructor() { this.x = 1; } }")
    assert classify_js_tier(path="lib/store.js", surface=s) == "a2_mo_composites"


def test_classify_js_tier_worker_default_fetch_is_orchestration():
    s = parse_surface("export default { async fetch(r) { return r; } };")
    assert classify_js_tier(path="cognition/cognition_worker.js",
                              surface=s) == "a4_sy_orchestration"


def test_classify_js_tier_index_js_is_orchestration():
    s = parse_surface("import x from './x.js';")
    assert classify_js_tier(path="thought-viewer/server.js",
                              surface=s) == "a4_sy_orchestration"


def test_detect_js_effects_io_via_fetch():
    src = "async function go() { return await fetch('https://x'); }"
    assert "io" in detect_js_effects(src)


def test_detect_js_effects_pure():
    src = "export function add(a, b) { return a + b; }"
    assert detect_js_effects(src) == ["pure"]
