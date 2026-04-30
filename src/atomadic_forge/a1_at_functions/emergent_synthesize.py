"""Tier a1 — pure source synthesiser for an :class:`EmergentCandidateCard`.

Renders a Python module that wires the chain's components together as a new
feature.  The generator is conservative: it imports each step by qualname,
calls them in order, and returns a typed result dict.  Manual review is
expected — this is scaffolding, not a finished feature.
"""

from __future__ import annotations

from ..a0_qk_constants.emergent_types import EmergentCandidateCard


def _imports_for(chain_qualnames: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for q in chain_qualnames:
        module, _, name = q.rpartition(".")
        # qualnames may include a class-qualified method (``Mod.Class.method``).
        if "." in name:  # method case
            continue
        line = f"from {module} import {name}"
        if line in seen:
            continue
        seen.add(line)
        out.append(line)
    return out


def render_emergent_feature(card: EmergentCandidateCard) -> str:
    chain = card["chain"]
    qualnames = chain["chain"]
    bridges = chain["bridges"]
    name = card["name"].replace("-", "_")
    imports = _imports_for(qualnames)
    summary = card["summary"].replace('"""', "'''")
    novelty = "; ".join(card["novelty_signals"]) or "(none)"
    score = card["score"]
    breakdown = ", ".join(f"{k}={v:g}" for k, v in card["score_breakdown"].items())

    lines: list[str] = [
        '"""',
        f"Auto-synthesized by ``atomadic-forge emergent synthesize {card['candidate_id']}``.",
        "",
        f"Suggested name: {card['name']}",
        f"Suggested tier: {card['suggested_tier']}",
        f"Score:          {score:.0f}  ({breakdown})",
        f"Novelty:        {novelty}",
        "",
        "Composition chain:",
    ]
    for i, q in enumerate(qualnames):
        lines.append(f"  {i+1}. {q}")
        if i < len(bridges):
            lines.append(f"     -- output: {bridges[i]} -->")
    lines.extend([
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import Any",
        "",
    ])
    lines.extend(imports)
    lines.append("")
    lines.append(f"def run_{name}(seed: Any) -> dict[str, Any]:")
    lines.append(f'    """Wired composition for {card["name"]}.')
    lines.append("")
    lines.append(f"    Summary: {summary}")
    lines.append('    """')
    lines.append("    trace: list[Any] = []")
    lines.append("    value = seed")
    for i, q in enumerate(qualnames):
        _module, _, callable_name = q.rpartition(".")
        if "." in callable_name:
            # method case — fall back to a noop trace step rather than guessing
            # the receiver.  Manual wiring required.
            lines.append(
                f"    # NOTE: step {i+1} is a method ({callable_name}); "
                "wire the receiver manually."
            )
            lines.append(f"    trace.append(({q!r}, 'unwired-method'))")
            continue
        lines.append(f"    value = {callable_name}(value)")
        lines.append(f"    trace.append(({q!r}, value))")
    lines.append("    return {'final': value, 'trace': trace}")
    lines.append("")
    return "\n".join(lines) + "\n"
