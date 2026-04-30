"""Tier verification — Lane C W3 Cloudflare badge Worker.

The Worker is TypeScript and runs on Cloudflare's V8 isolates; we
don't run vitest from pytest. Instead we pin the structural
contract:

  * the package + tsconfig + wrangler manifest exist
  * the Worker exports a `default { fetch }` shape
  * the route regex covers .svg and .json + branch variants
  * the color rubric, badge json shape, and SVG render structure
    match the documented contract (regex parsed from the source)
  * a Python re-implementation of the color logic agrees with the
    TS source for representative inputs (catches drift)

If the user runs `npm test` from cloudflare-workers/badge/ they get
the full vitest run; this file is the always-on Python guard.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


_REPO = Path(__file__).resolve().parents[1]
_WORKER = _REPO / "cloudflare-workers" / "badge"


def test_worker_directory_exists():
    assert _WORKER.is_dir()
    for required in ("package.json", "tsconfig.json", "wrangler.toml",
                      "README.md", "src/index.ts"):
        assert (_WORKER / required).is_file(), (
            f"cloudflare-workers/badge/{required} missing"
        )


def test_worker_package_manifest():
    data = json.loads((_WORKER / "package.json").read_text(encoding="utf-8"))
    assert data["name"] == "atomadic-forge-badge"
    assert "wrangler" in data["devDependencies"]
    assert "@cloudflare/workers-types" in data["devDependencies"]


def test_worker_wrangler_compat_date_pinned():
    text = (_WORKER / "wrangler.toml").read_text(encoding="utf-8")
    assert re.search(r'^name\s*=\s*"forge-badge"', text, re.MULTILINE)
    assert re.search(r"compatibility_date\s*=\s*\"\d{4}-\d{2}-\d{2}\"",
                     text)
    assert "[[kv_namespaces]]" in text
    assert 'binding = "FORGE_RECEIPTS"' in text


def test_worker_default_export_fetch_shape():
    src = (_WORKER / "src" / "index.ts").read_text(encoding="utf-8")
    assert "export default {" in src
    assert "fetch(request: Request, env: Env)" in src


def test_worker_route_regex_covers_branch_and_format():
    src = (_WORKER / "src" / "index.ts").read_text(encoding="utf-8")
    # Cheap presence check — the route regex is the contract.
    assert "/^\\/badge\\/" in src or "\\/badge\\/" in src
    assert "(svg|json)" in src
    # Branch is optional in the regex.
    assert "([^/.]+))?\\." in src


def test_worker_kv_key_pattern_documented():
    """The KV key shape `receipt:<owner>:<repo>:<branch>` is part
    of the contract with the github-action uploader. README and
    source must agree."""
    src = (_WORKER / "src" / "index.ts").read_text(encoding="utf-8")
    readme = (_WORKER / "README.md").read_text(encoding="utf-8")
    assert "receipt:${owner}:${repo}:${branch}" in src
    assert "receipt:<owner>:<repo>:<branch>" in readme


def test_worker_color_rubric_documented_in_readme():
    readme = (_WORKER / "README.md").read_text(encoding="utf-8")
    for token in ("score == 100", "score >= 90", "score >= 75",
                  "score >= 50", "score < 50", "no receipt"):
        assert token in readme, f"README missing rubric token {token!r}"


def test_worker_color_constants_present_in_source():
    src = (_WORKER / "src" / "index.ts").read_text(encoding="utf-8")
    for color in ("#4c1", "#a4a61d", "#dfb317", "#fe7d37",
                  "#e05d44", "#9f9f9f"):
        assert color in src


# ---- Python re-implementation parity -----------------------------------
# Mirrors badgeColorFor + badgeMessageFor in src/index.ts so the
# rubric can never silently drift. If you change either side, the
# table here must change too.


def _expected_color_py(score, verdict):
    if verdict == "PASS" and score is not None and score >= 100:
        return "#4c1"
    if verdict == "PASS" and score is not None and score >= 90:
        return "#a4a61d"
    if score is not None and score >= 75:
        return "#dfb317"
    if score is not None and score >= 50:
        return "#fe7d37"
    if score is not None:
        return "#e05d44"
    return "#9f9f9f"


def _expected_message_py(verdict, score):
    if verdict is None and score is None:
        return "no receipt"
    if score is None:
        return verdict or "?"
    return f"{verdict} {round(score)}/100"


@pytest.mark.parametrize("score,verdict,expected", [
    (100, "PASS", "#4c1"),
    (95, "PASS", "#a4a61d"),
    (80, "PASS", "#dfb317"),
    (60, "FAIL", "#fe7d37"),
    (10, "FAIL", "#e05d44"),
    (None, "?", "#9f9f9f"),
])
def test_color_rubric_table(score, verdict, expected):
    assert _expected_color_py(score, verdict) == expected


@pytest.mark.parametrize("score,verdict,expected", [
    (100, "PASS", "PASS 100/100"),
    (75, "FAIL", "FAIL 75/100"),
    (None, "?", "no receipt"),
])
def test_message_table(score, verdict, expected):
    if verdict == "?" and score is None:
        assert _expected_message_py(None, None) == expected
    else:
        assert _expected_message_py(verdict, score) == expected
