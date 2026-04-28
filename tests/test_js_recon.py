"""Recon over a synthetic JS-only repo: counts, languages, suggested_tier."""

from pathlib import Path

from atomadic_forge.a1_at_functions.scout_walk import harvest_repo


def _scaffold_js_repo(root: Path) -> None:
    """Lay down a minimal Atomadic-shaped JS repo: worker + chat + tests."""
    (root / "cognition").mkdir(parents=True)
    (root / "cognition" / "cognition_worker.js").write_text(
        "// Atomadic worker\n"
        "const KV = { A: 'a' };\n"
        "function decide(t) { return 'REST'; }\n"
        "export default {\n"
        "  async fetch(req, env) { return new Response('ok'); },\n"
        "  async scheduled(c, env) { }\n"
        "};\n",
        encoding="utf-8",
    )
    (root / "chat").mkdir()
    (root / "chat" / "chat.html").write_text("<html></html>", encoding="utf-8")
    (root / "thought-viewer").mkdir()
    (root / "thought-viewer" / "server.js").write_text(
        "const http = require('http');\n"
        "const server = http.createServer((req, res) => res.end('ok'));\n"
        "server.listen(3333);\n",
        encoding="utf-8",
    )
    (root / "tests").mkdir()
    (root / "tests" / "cognition.test.js").write_text(
        "import { test } from 'node:test';\n"
        "test('smoke', () => {});\n",
        encoding="utf-8",
    )


def test_recon_counts_js_files(tmp_path):
    _scaffold_js_repo(tmp_path)
    report = harvest_repo(tmp_path)
    assert report["javascript_file_count"] == 3
    assert report["python_file_count"] == 0
    assert report["primary_language"] == "javascript"


def test_recon_classifies_worker_as_a4(tmp_path):
    _scaffold_js_repo(tmp_path)
    report = harvest_repo(tmp_path)
    worker_syms = [
        s for s in report["symbols"]
        if s["file"] == "cognition/cognition_worker.js"
        and s["kind"] == "module"
    ]
    assert worker_syms, "expected module-level record for worker"
    assert worker_syms[0]["suggested_tier"] == "a4_sy_orchestration"


def test_recon_classifies_pure_const_module_as_a0(tmp_path):
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "keys.js").write_text(
        "export const KV = { STATE: 'cognition_state' };\n"
        "export const FAST_MODEL = 'gemma';\n",
        encoding="utf-8",
    )
    report = harvest_repo(tmp_path)
    keys_mod = [s for s in report["symbols"]
                 if s["file"] == "lib/keys.js" and s["kind"] == "module"][0]
    assert keys_mod["suggested_tier"] == "a0_qk_constants"


def test_recon_skips_node_modules(tmp_path):
    (tmp_path / "node_modules" / "lodash").mkdir(parents=True)
    (tmp_path / "node_modules" / "lodash" / "index.js").write_text(
        "module.exports = {};", encoding="utf-8")
    (tmp_path / "src.js").write_text("export const x = 1;", encoding="utf-8")
    report = harvest_repo(tmp_path)
    assert report["javascript_file_count"] == 1


def test_recon_typescript_counted(tmp_path):
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "store.ts").write_text(
        "export class Store {\n  constructor() { this.x = 1; }\n}\n",
        encoding="utf-8",
    )
    report = harvest_repo(tmp_path)
    assert report["typescript_file_count"] == 1
    assert report["primary_language"] == "typescript"


def test_recon_polyglot_python_plus_js(tmp_path):
    (tmp_path / "discord").mkdir()
    (tmp_path / "discord" / "bot.py").write_text(
        "def run():\n    return 'hi'\n", encoding="utf-8")
    (tmp_path / "cognition").mkdir()
    (tmp_path / "cognition" / "worker.js").write_text(
        "export default { async fetch() {} };\n", encoding="utf-8")
    report = harvest_repo(tmp_path)
    assert report["python_file_count"] == 1
    assert report["javascript_file_count"] == 1
    assert "javascript_file_count" in report
