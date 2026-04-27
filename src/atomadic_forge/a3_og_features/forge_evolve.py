"""Tier a3 — recursive self-improvement loop.

``forge evolve`` runs N rounds of ``iterate``, each round using the GROWING
catalog as the seed for the next.  Round 0 starts from the user's seed (or
empty); each accepted artifact joins the catalog; subsequent rounds see a
richer compositional context via emergent + reuse signals.

Honest scope: this is **narrow self-improvement within a defined search
space** — same shape as AlphaEvolve, AutoML-Zero, Voyager.  It is NOT a
path to AGI.  The catalog grows, compositions multiply, the LLM gets
richer feedback.  Whether the OUTPUT improves is bounded by the underlying
LLM's quality and the realism of the certify/wire signals.

Convergence rules:
* Round halts when iterate returns ``converged=True`` AND no new symbols
  were added vs. previous round (catalog stable).
* Hard cap: ``rounds`` parameter (default 5).
* Optional ``stop_on_regression``: halt if score drops between rounds.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any

from ..a1_at_functions.llm_client import LLMClient, resolve_default_client
from ..a1_at_functions.scout_walk import harvest_repo
from ..a2_mo_composites.manifest_store import ManifestStore
from .forge_loop import run_iterate


def run_evolve(
    intent: str,
    *,
    output: Path,
    package: str = "evolved",
    seed_repo: Path | None = None,
    llm: LLMClient | None = None,
    rounds: int = 3,
    iterations_per_round: int = 4,
    target_score: float = 75.0,
    stop_on_regression: bool = False,
) -> dict[str, Any]:
    """Recursive iterate.

    The growing package itself becomes the seed for the next round, so the
    LLM sees its own prior output as building blocks the next time around.
    """
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    llm = llm or resolve_default_client()
    pkg_root = output / "src" / package

    rounds_log: list[dict[str, Any]] = []
    last_symbol_count = 0
    last_score = 0.0
    current_seed = Path(seed_repo) if seed_repo else None

    for round_idx in range(rounds):
        report = run_iterate(
            intent,
            output=output,
            package=package,
            seed_repo=current_seed,
            llm=llm,
            max_iterations=iterations_per_round,
            target_score=target_score,
            apply=True,
        )
        # Re-scout the generated package to grow the catalog.
        catalog = harvest_repo(pkg_root) if pkg_root.exists() else {"symbols": [], "symbol_count": 0}
        symbol_count = catalog["symbol_count"]
        score = report.get("final_certify", {}).get("score", 0)
        delta = symbol_count - last_symbol_count

        round_record = {
            "round": round_idx,
            "iterations": report.get("iterations", 0),
            "files_written": report.get("files_written_total", 0),
            "symbol_count": symbol_count,
            "delta_symbols": delta,
            "score": score,
            "delta_score": round(score - last_score, 1),
            "wire_verdict": report.get("final_wire", {}).get("verdict", "?"),
            "converged": report.get("converged", False),
        }
        rounds_log.append(round_record)

        # Convergence checks
        if report.get("converged") and delta == 0:
            break
        if stop_on_regression and round_idx > 0 and round_record["delta_score"] < 0:
            round_record["halt_reason"] = "score regression"
            break

        # The growing package becomes the seed for the next round.
        current_seed = pkg_root if pkg_root.exists() else current_seed
        last_symbol_count = symbol_count
        last_score = score

    final_score = rounds_log[-1]["score"] if rounds_log else 0
    final_symbols = rounds_log[-1]["symbol_count"] if rounds_log else 0

    out: dict[str, Any] = {
        "schema_version": "atomadic-forge.evolve/v1",
        "intent": intent,
        "package": package,
        "output_root": str(output),
        "llm": llm.name,
        "rounds": rounds_log,
        "rounds_completed": len(rounds_log),
        "rounds_requested": rounds,
        "final_score": final_score,
        "final_symbol_count": final_symbols,
        "score_trajectory": [r["score"] for r in rounds_log],
        "symbol_trajectory": [r["symbol_count"] for r in rounds_log],
        "converged": rounds_log[-1].get("converged", False) if rounds_log else False,
        "generated_at_utc": _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    ManifestStore(output).save("evolve", out)
    return out
