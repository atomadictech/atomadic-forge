"""Tier a1 — pure feedback packer.

Takes the structured output of wire / certify / emergent / scout and packs
it into a markdown-shaped string that an LLM can act on.  Forge feeds this
back to the LLM each iteration of the generate-enforce loop.

The packing is designed to make the LLM's job easy:
* concrete file paths
* exact line content of violating imports
* explicit "fix this by …" hints when the rule is mechanical
* a single ``CHANGE_REQUEST`` block at the bottom describing what to emit next

System prompts come in language-specific variants (Python / JavaScript /
TypeScript) — the structural feedback (wire violations, score gaps, reuse
ratio) is language-agnostic, but the emit-format and import-style
instructions differ per language.
"""

from __future__ import annotations

from typing import Any

_SYSTEM_PROMPT_PYTHON = """\
You are a code-generation engine constrained by Atomadic Forge's 5-tier
monadic architecture.

Forge has ALREADY scaffolded the surrounding package for you:
  - ``pyproject.toml`` (PEP-621, with a console_script entry pointing at
    ``a4_sy_orchestration.cli:main``)
  - ``README.md`` describing the intent and layout
  - ``.gitignore``
  - ``tests/`` directory with ``conftest.py`` adding ``src/`` to ``sys.path``
  - All five tier directories with ``__init__.py``

You should focus on emitting the actual ``.py`` files (and ``test_*.py``
files in ``tests/``).  DO NOT re-emit pyproject.toml or README.md — they
are already correct.

The 5-tier law (compose UPWARD only):
  a0_qk_constants   — constants, enums, TypedDicts.  Imports nothing.
  a1_at_functions   — pure stateless functions.  Imports a0 only.
  a2_mo_composites  — stateful classes.  Imports a0, a1.
  a3_og_features    — feature orchestrators.  Imports a0, a1, a2.
  a4_sy_orchestration — CLI / entry points.  Imports a0–a3.

When you emit code, you MUST:
  1. Place each new file under the correct ``a{N}_*/`` directory.
  2. Never import upward (lower tier importing from higher tier).
  3. One responsibility per file.
  4. Module docstrings of the form: \"\"\"Tier aN — <one-line>.\"\"\"
  5. Write COMPLETE function bodies — no `pass`, no `NotImplementedError`,
     no `# TODO`, no `# Implement me!`.  If you don't know how to implement
     something, choose a simpler design rather than emit a stub.
  6. Use ABSOLUTE imports rooted at the package: `from <pkg>.a1_at_functions.foo
     import foo` — not relative imports, not bare names.
  7. Output as a JSON array of file objects ONLY — no prose, no fences:
       [{"path": "src/<pkg>/aN_…/foo.py", "content": "…"}, ...]
  8. SUBSTITUTE the actual package name into every `<pkg>` placeholder.
  9. Emit at least one ``test_*.py`` file under ``tests/`` exercising the
     public callables you just wrote.  Use simple ``assert`` statements
     and import via the absolute package path.

Example (intent: "calc with add() at a1, CLI at a4", package: "calc"):

[
  {"path": "src/calc/a1_at_functions/add.py",
   "content": "\\"\\"\\"Tier a1 — pure addition.\\"\\"\\"\\n\\ndef add(a: int, b: int) -> int:\\n    return a + b\\n"},
  {"path": "src/calc/a4_sy_orchestration/cli.py",
   "content": "\\"\\"\\"Tier a4 — CLI entry.\\"\\"\\"\\nimport argparse\\nfrom calc.a1_at_functions.add import add\\n\\ndef main():\\n    p = argparse.ArgumentParser()\\n    p.add_argument('a', type=int); p.add_argument('b', type=int)\\n    args = p.parse_args()\\n    print(add(args.a, args.b))\\n"}
]

Forge then materialises your output, runs wire + certify + import-smoke,
and feeds any violations back to you on the next turn.  An importable
package with real bodies scores high; stubs and broken imports lose points.
"""


_SYSTEM_PROMPT_JS = """\
You are a code-generation engine constrained by Atomadic Forge's 5-tier
monadic architecture, emitting JavaScript (ES modules) for Cloudflare
Workers / Node 20+ / browsers.

Forge has ALREADY scaffolded the surrounding package for you:
  - ``package.json`` with ``"type": "module"`` so ES6 imports resolve
  - ``README.md`` describing the intent and layout
  - ``.gitignore``
  - All five tier directories (no ``__init__.py`` — ES modules don't need them)

You should focus on emitting the actual ``.js`` files.  DO NOT re-emit
``package.json`` or ``README.md`` — they are already correct.

The 5-tier law (compose UPWARD only):
  a0_qk_constants   — exported constants, enums, type-shape JSDoc.  Imports nothing.
  a1_at_functions   — pure stateless functions.  Imports a0 only.
  a2_mo_composites  — stateful classes / clients / stores.  Imports a0, a1.
  a3_og_features    — feature orchestrators.  Imports a0, a1, a2.
  a4_sy_orchestration — Worker entry / CLI / top-level dispatch.  Imports a0–a3.

When you emit code, you MUST:
  1. Place each new file under the correct ``a{N}_*/`` directory.
  2. Never import upward (lower tier importing from higher tier).
  3. One responsibility per file.
  4. File-leading docstring comment of the form: ``// Tier aN — <one-line>.``
  5. Write COMPLETE function bodies — no `throw new Error("not impl")`,
     no `// TODO`, no empty bodies that just return undefined.  If you
     don't know how to implement something, choose a simpler design.
  6. Use ES module syntax — ``import { x } from "./other.js"`` and
     ``export function …`` / ``export const …`` / ``export default …``.
     Cross-tier imports MUST include the full relative path with the
     ``.js`` extension: ``import { foo } from "../a1_at_functions/foo.js"``.
     No bare specifiers, no CommonJS ``require()``, no default-only exports
     for libraries (default-export the Worker handler at a4 ONLY).
  7. Output as a JSON array of file objects ONLY — no prose, no fences:
       [{"path": "<pkg>/aN_…/foo.js", "content": "…"}, ...]
  8. SUBSTITUTE the actual package name into every `<pkg>` placeholder.
     Note: there is NO ``src/`` prefix — the package directory sits at
     the output root.
  9. For a Cloudflare Worker, the a4 entry file exports a ``default``
     object with ``fetch(request, env, ctx)`` and/or ``scheduled(event,
     env, ctx)``.  Helpers it calls live in a1–a3.

Example (intent: "counter with increment() at a1, Worker at a4", package: "counter"):

[
  {"path": "counter/a1_at_functions/increment.js",
   "content": "// Tier a1 — pure increment.\\nexport function increment(n) { return n + 1; }\\n"},
  {"path": "counter/a4_sy_orchestration/worker.js",
   "content": "// Tier a4 — Worker entry.\\nimport { increment } from \\"../a1_at_functions/increment.js\\";\\nexport default {\\n  async fetch(request) {\\n    const url = new URL(request.url);\\n    const n = Number(url.searchParams.get(\\"n\\")) || 0;\\n    return new Response(String(increment(n)));\\n  }\\n};\\n"}
]

Forge then materialises your output, runs wire + certify, and feeds any
violations back to you on the next turn.  Clean ES-module imports score
high; broken imports and upward-tier violations lose points.
"""


def system_prompt(language: str = "python") -> str:
    """Return the language-appropriate system prompt for the LLM.

    ``language`` accepts ``"python"`` (default), ``"javascript"``, or
    ``"typescript"`` (typescript reuses the JS prompt today; tsconfig
    polish is on the 0.3 roadmap).
    """
    if language in ("javascript", "typescript"):
        return _SYSTEM_PROMPT_JS
    return _SYSTEM_PROMPT_PYTHON


def pack_initial_intent(intent: str, *, package: str = "absorbed",
                          seed_catalog: list[dict] | None = None,
                          language: str = "python") -> str:
    """Build the first-turn prompt: the user's intent + (optional) seed material."""
    if language in ("javascript", "typescript"):
        target_path = f"`{package}/` — emit files under the 5-tier layout below."
    else:
        target_path = f"`src/{package}/` — emit files under the 5-tier layout below."
    parts = [
        "# Intent",
        "",
        intent.strip(),
        "",
        "# Target package",
        target_path,
        "",
    ]
    if seed_catalog:
        # Deduplicate by qualname and prefer top-level symbols (no dots except class.method).
        seen: set[str] = set()
        unique_catalog: list[dict] = []
        for s in seed_catalog:
            qn = s.get("qualname", "")
            # Skip method-level duplicates; prefer class-level or module-level.
            base = qn.split(".")[0] if "." in qn else qn
            if base not in seen:
                seen.add(base)
                unique_catalog.append(s)
        MAX_SEEDS = 30
        parts.append(f"# Available building blocks ({len(seed_catalog)} symbols — {len(unique_catalog)} unique top-level; showing {min(MAX_SEEDS, len(unique_catalog))})")
        parts.append("")
        for s in unique_catalog[:MAX_SEEDS]:
            parts.append(
                f"- `{s.get('qualname','?')}`  "
                f"(tier `{s.get('tier_guess','?')}`, "
                f"effects {s.get('effects', [])})"
            )
        if len(unique_catalog) > MAX_SEEDS:
            parts.append(f"- … {len(unique_catalog) - MAX_SEEDS} more unique symbols available")
        parts.append("")
        if language in ("javascript", "typescript"):
            parts.append("Reuse these where possible — import from the "
                          f"corresponding `{package}/aN_*/<file>.js` paths "
                          "with relative ES-module specifiers.")
        else:
            parts.append("Reuse these where possible by importing from "
                          f"`{package}.aN_…` paths.")
        parts.append("")
    parts.extend([
        "# CHANGE_REQUEST",
        "",
        "Emit the initial set of files needed to satisfy the intent.  Output",
        "a JSON array of `{path, content}` objects only — no prose around it.",
    ])
    return "\n".join(parts)


def compute_reuse_stats(scout_report: dict[str, Any] | None,
                          seed_catalog: list[dict] | None) -> dict[str, Any]:
    """Compute how much of the LLM's emitted symbols overlap with the seed catalog.

    A high reuse ratio = the LLM correctly composed existing pieces.  A low
    reuse ratio = it generated from scratch when it should have been
    importing.  This is the soft signal that distinguishes Forge's loop
    from Cursor / Devin / etc. — none of them feed reuse stats back to the
    generator.
    """
    if not scout_report or not seed_catalog:
        return {"reuse_ratio": 0.0, "novel_symbols": [],
                 "reused_symbols": [], "available_unused": []}
    available = {s["qualname"]: s for s in seed_catalog}
    emitted = {s["qualname"]: s for s in scout_report.get("symbols", [])}
    reused = sorted(emitted.keys() & available.keys())
    novel = sorted(set(emitted.keys()) - set(available.keys()))
    available_unused = sorted(set(available.keys()) - set(emitted.keys()))
    total_emitted = max(1, len(emitted))
    return {
        "reuse_ratio": round(len(reused) / total_emitted, 3),
        "reused_symbols": reused[:20],
        "novel_symbols": novel[:20],
        "available_unused": available_unused[:20],
    }


def pack_feedback(*, wire_report: dict[str, Any] | None = None,
                  certify_report: dict[str, Any] | None = None,
                  emergent_overlay: dict[str, Any] | None = None,
                  reuse_stats: dict[str, Any] | None = None,
                  iteration: int = 0) -> str:
    """Pack the next-turn prompt: violations + score gaps + emergent + reuse.

    The 3-way constraint-satisfaction signal that distinguishes Forge's loop
    from Cursor / Devin / Cognition: hard constraint (wire), score gap
    (certify), and compositional signal (emergent + reuse).
    """
    parts = [f"# Forge feedback (iteration {iteration})", ""]

    if wire_report:
        v_count = wire_report.get("violation_count", 0)
        verdict = wire_report.get("verdict", "?")
        parts.append(f"## Wire scan: **{verdict}** ({v_count} violation(s))")
        parts.append("")
        for v in wire_report.get("violations", [])[:20]:
            parts.append(
                f"- `{v['file']}` imports `{v['imported']}` "
                f"from tier `{v['to_tier']}` while sitting at tier "
                f"`{v['from_tier']}` — **upward import, illegal**."
            )
        if v_count == 0:
            parts.append("All imports compose upward only — no fixes needed here.")
        parts.append("")

    if certify_report:
        score = certify_report.get("score", 0)
        parts.append(f"## Certify score: **{score}/100**")
        parts.append("")
        for issue in certify_report.get("issues", []):
            parts.append(f"- {issue}")
        for rec in certify_report.get("recommendations", []):
            parts.append(f"  → {rec}")
        # Per-file stub callouts — actionable feedback the LLM can target.
        stubs = (certify_report.get("detail") or {}).get("stubs") or {}
        findings = stubs.get("findings") or []
        if findings:
            parts.append("")
            parts.append("**Stub bodies — replace with real implementations:**")
            for f in findings[:10]:
                parts.append(
                    f"  · `{f['file']}` line {f['lineno']} → "
                    f"`{f['qualname']}` ({f['kind']}): `{f['excerpt']}`"
                )
        # Runtime import error — paste the actual traceback so the LLM
        # can fix the exact failing import / syntax / path issue.
        smoke = (certify_report.get("detail") or {}).get("import_smoke")
        if smoke and not smoke.get("importable", True):
            parts.append("")
            parts.append("**Runtime import FAILED — package does not load:**")
            parts.append(f"  · error: `{smoke.get('error_kind')}` — "
                          f"{smoke.get('error_message')}")
            tb = smoke.get("traceback_excerpt") or ""
            if tb:
                parts.append("")
                parts.append("```text")
                parts.append(tb.strip())
                parts.append("```")
            parts.append("")
            parts.append("Fix the import error.  Common causes:")
            parts.append("  - missing module file or wrong tier directory")
            parts.append("  - relative import path uses old/wrong package name")
            parts.append("  - syntax error in an emitted file")

        # Behavioral test failures — the breakthrough signal.  Identity-
        # function stubs pass wire+import but fail tests.  Pasting the
        # pytest output lets the LLM see exactly which assertion broke.
        test_run = (certify_report.get("detail") or {}).get("test_run")
        if test_run and test_run.get("ran") and test_run.get("failed"):
            parts.append("")
            parts.append(
                f"**Tests FAILED: {test_run['failed']} of "
                f"{test_run['total']} "
                f"({test_run.get('pass_ratio', 0):.0%} pass-ratio)**"
            )
            for fid in (test_run.get("failure_excerpts") or [])[:5]:
                parts.append(f"  · `{fid}`")
            summary = (test_run.get("pytest_summary") or "").strip()
            if summary:
                parts.append("")
                parts.append("```text")
                parts.append(summary[:1500])
                parts.append("```")
            parts.append("")
            parts.append("Tests are the behavior gate.  An identity-function "
                          "implementation (e.g. `def f(x): return x`) passes "
                          "wire and import but fails its own tests.  Replace "
                          "stubs with implementations that satisfy the "
                          "assertions.")
        parts.append("")

    if reuse_stats:
        ratio = reuse_stats.get("reuse_ratio", 0.0)
        unused = reuse_stats.get("available_unused", [])
        parts.append(f"## Reuse signal: **{ratio:.0%}** of emitted symbols "
                      "match the seed catalog")
        if ratio < 0.3 and unused:
            parts.append("")
            parts.append("**Low reuse — these existing symbols would likely "
                          "satisfy your needs without re-implementation:**")
            for q in unused[:8]:
                parts.append(f"- `{q}`")
            parts.append("")
            parts.append("Compose existing symbols by importing them; only "
                          "emit new code where no existing symbol fits.")
        parts.append("")

    if emergent_overlay and emergent_overlay.get("candidates"):
        parts.append("## Emergent compositions (chains you could wire)")
        parts.append("")
        for c in emergent_overlay["candidates"][:5]:
            chain_str = " → ".join(c["chain"]["chain"][:4])
            parts.append(
                f"- **{c['name']}** (score {c['score']:.0f}): `{chain_str}`"
            )
        parts.append("")

    parts.extend([
        "# CHANGE_REQUEST",
        "",
        "Fix the violations and score gaps above.  Output a JSON array of",
        "`{path, content}` objects representing files to write or overwrite.",
        "Prefer composing existing symbols over emitting new ones.  Empty",
        "array means you have finished.",
    ])
    return "\n".join(parts)


def parse_files_from_response(response: str) -> list[dict[str, str]]:
    """Best-effort: pull ``[{"path": …, "content": …}, …]`` out of an LLM reply.

    Tolerant of:
    - Triple-backtick fences (```json ... ```)
    - Prose before/after the JSON array
    - Truncated responses (extracts complete objects before the cutoff)
    Returns [] when no valid file dicts are found.
    """
    import json as _json
    import re

    text = response.strip()

    # Strategy 1: find JSON inside a code fence (greedy match for full array).
    fence = re.search(r"```(?:json|python)?\s*(\[[\s\S]*?\])\s*```", text, re.DOTALL)
    if fence:
        candidate = fence.group(1)
        try:
            data = _json.loads(candidate)
            if isinstance(data, list):
                return [e for e in data
                        if isinstance(e, dict)
                        and isinstance(e.get("path"), str)
                        and isinstance(e.get("content"), str)]
        except _json.JSONDecodeError:
            pass

    # Strategy 2: balanced-bracket scan starting at first '['.
    start = text.find("[")
    if start != -1:
        depth = 0
        end = -1
        for i, ch in enumerate(text[start:], start=start):
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end != -1:
            try:
                data = _json.loads(text[start:end + 1])
                if isinstance(data, list):
                    out = [e for e in data
                           if isinstance(e, dict)
                           and isinstance(e.get("path"), str)
                           and isinstance(e.get("content"), str)]
                    if out:
                        return out
            except _json.JSONDecodeError:
                pass

    # Strategy 3: tolerant extraction — grab every complete {"path":…,"content":…} object
    # even from a truncated/malformed array.  Uses a regex to find object boundaries.
    objects = []
    # Match objects that have at least "path" and "content" keys.
    obj_pattern = re.compile(
        r'\{\s*"path"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"content"\s*:\s*"((?:[^"\\]|\\.)*?)"\s*\}',
        re.DOTALL,
    )
    for m in obj_pattern.finditer(text):
        try:
            path = _json.loads(f'"{m.group(1)}"')
            content = _json.loads(f'"{m.group(2)}"')
            objects.append({"path": path, "content": content})
        except _json.JSONDecodeError:
            continue
    return objects
