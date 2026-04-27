"""Tier a1 — pure feedback packer.

Takes the structured output of wire / certify / emergent / scout and packs
it into a markdown-shaped string that an LLM can act on.  Forge feeds this
back to the LLM each iteration of the generate-enforce loop.

The packing is designed to make the LLM's job easy:
* concrete file paths
* exact line content of violating imports
* explicit "fix this by …" hints when the rule is mechanical
* a single ``CHANGE_REQUEST`` block at the bottom describing what to emit next
"""

from __future__ import annotations

from typing import Any


_SYSTEM_PROMPT = """\
You are a code-generation engine constrained by Atomadic Forge's 5-tier
monadic architecture.

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
  5. Output as a JSON array of file objects:
       [{"path": "src/<pkg>/aN_…/foo.py", "content": "…"}, …]

Forge will then materialise your output, run wire + certify, and feed any
violations back to you on the next turn.
"""


def system_prompt() -> str:
    return _SYSTEM_PROMPT


def pack_initial_intent(intent: str, *, package: str = "absorbed",
                          seed_catalog: list[dict] | None = None) -> str:
    """Build the first-turn prompt: the user's intent + (optional) seed material."""
    parts = [
        f"# Intent",
        f"",
        intent.strip(),
        f"",
        f"# Target package",
        f"`src/{package}/` — emit files under the 5-tier layout below.",
        f"",
    ]
    if seed_catalog:
        parts.append(f"# Available building blocks ({len(seed_catalog)} symbols)")
        parts.append("")
        for s in seed_catalog[:40]:
            parts.append(
                f"- `{s.get('qualname','?')}`  "
                f"(tier `{s.get('tier_guess','?')}`, "
                f"effects {s.get('effects', [])})"
            )
        if len(seed_catalog) > 40:
            parts.append(f"- … {len(seed_catalog) - 40} more symbols available")
        parts.append("")
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

    Tolerant of triple-backtick fences and prose around the JSON.  Returns []
    when no JSON array of file dicts is found.
    """
    import json as _json
    import re

    text = response.strip()
    # Strip code fences if present.
    fence = re.search(r"```(?:json)?\s*(\[.+?\])\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    # Locate the first balanced JSON array.
    start = text.find("[")
    if start == -1:
        return []
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
    if end == -1:
        return []
    try:
        data = _json.loads(text[start:end + 1])
    except _json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    out: list[dict[str, str]] = []
    for entry in data:
        if (isinstance(entry, dict)
                and "path" in entry and "content" in entry
                and isinstance(entry["path"], str)
                and isinstance(entry["content"], str)):
            out.append({"path": entry["path"], "content": entry["content"]})
    return out
