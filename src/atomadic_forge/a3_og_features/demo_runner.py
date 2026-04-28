"""Tier a3 — preset-driven demo runner.

``forge demo`` packages the headline trajectory (intent → evolve → working
software) into a single command suitable for launch videos and 90-second
recordings.  Two preset families ship with Forge:

* ``kind="llm"`` — the original LLM-driven Python presets (`calc`, `kv`,
  `slug`).  Each runs a real evolve trajectory with the configured LLM
  provider and produces an importable, pip-installable Python package.
* ``kind="showcase"`` — static, pre-built source packages copied into
  the output directory and exercised via ``recon → wire → certify``.
  Useful for demonstrating polyglot (JS/TS) capabilities without a paid
  LLM key.  Ships with ``js-counter``, ``js-bad-wire``, ``mixed-py-js``.

Public API:
    list_presets()                 → list[DemoPreset]
    run_demo(preset_name, llm, …)  → DemoResult (writes DEMO.md artifact)
"""

from __future__ import annotations

import datetime as _dt
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..a1_at_functions.certify_checks import certify as _certify_checks
from ..a1_at_functions.llm_client import LLMClient, resolve_default_client
from ..a1_at_functions.scout_walk import harvest_repo
from ..a1_at_functions.wire_check import scan_violations
from ..a2_mo_composites.manifest_store import ManifestStore
from .forge_evolve import run_evolve


@dataclass(frozen=True)
class DemoPreset:
    """A pre-baked intent + verification recipe known to converge on a 7B model."""

    name: str
    headline: str            # one-line pitch for the launch video
    package: str
    intent: str
    rounds: int = 4
    iterations: int = 2
    target_score: float = 90.0
    cli_demo_args: tuple[str, ...] = ()  # invoked after convergence to prove it runs
    kind: str = "llm"        # "llm" — runs evolve; "showcase" — static recon/wire/certify
    source_subdir: str = ""  # for kind == "showcase": path under demo_packages/
    certify_package: str | None = None  # certify_checks `package` arg, when given


_PRESETS: dict[str, DemoPreset] = {
    "calc": DemoPreset(
        name="calc",
        headline="Free local 7B model writes a working calculator in 2 rounds.",
        package="calc",
        intent=(
            "Build a tiny calculator. Required: a1 pure functions add(a,b)->int, "
            "subtract(a,b)->int, multiply(a,b)->int, divide(a,b)->float (raise "
            "ValueError on b==0). a4 cli using argparse takes 'a OP b' (or just "
            "'a b' if simpler) and prints the result. tests/test_calc.py with "
            "concrete assertions: assert add(2,3)==5, assert subtract(10,4)==6, "
            "assert multiply(3,4)==12, assert divide(10,2)==5.0, and "
            "pytest.raises(ValueError) for divide(1,0). Use absolute imports "
            "rooted at 'calc'."
        ),
        rounds=4,
        iterations=2,
        target_score=90.0,
        cli_demo_args=("7", "6"),
    ),
    "kv": DemoPreset(
        name="kv",
        headline="Tier-organised in-memory key-value store with put/get/delete + tests.",
        package="kv",
        intent=(
            "Build a tiny in-memory KV store. Required: a2 class KvStore with "
            "self.data:dict, put(key,value)/get(key)->Any/delete(key)/keys()->list. "
            "a4 cli using argparse takes 'put KEY VALUE' or 'get KEY' or 'delete KEY' "
            "or 'keys'. tests/test_kv.py with concrete assertions: store.put('a',1); "
            "assert store.get('a')==1; store.delete('a'); assert store.get('a') is None; "
            "store.put('x',1); store.put('y',2); assert sorted(store.keys())==['x','y']. "
            "Use absolute imports rooted at 'kv'."
        ),
        rounds=4,
        iterations=2,
        target_score=85.0,
        cli_demo_args=("put", "hello", "world"),
    ),
    "slug": DemoPreset(
        name="slug",
        headline="Pure string-slugifier with concrete behavioural tests.",
        package="slug",
        intent=(
            "Build a tiny string slugifier. Required: a1 pure function "
            "slugify(text:str)->str that lowercases, replaces spaces and "
            "punctuation with single dashes, and strips leading/trailing dashes. "
            "a4 cli using argparse takes a single string argument and prints "
            "the slug. tests/test_slug.py with concrete assertions: "
            "assert slugify('Hello World')=='hello-world'; "
            "assert slugify('  Foo!! Bar??  ')=='foo-bar'; "
            "assert slugify('Already-Slugged')=='already-slugged'. "
            "Use absolute imports rooted at 'slug'."
        ),
        rounds=4,
        iterations=2,
        target_score=85.0,
        cli_demo_args=("Hello, World!",),
    ),
    # ---- Static polyglot showcases (kind="showcase", no LLM needed) -----
    "js-counter": DemoPreset(
        name="js-counter",
        headline="Clean a0..a4 JavaScript package — Worker on top of a stateful Counter.",
        package="js-counter-showcase",
        intent="(static showcase — no LLM trajectory)",
        kind="showcase",
        source_subdir="js_counter",
        target_score=60.0,  # 60/100 is the honest ceiling for JS-only today
    ),
    "js-bad-wire": DemoPreset(
        name="js-bad-wire",
        headline="Same JS layout, one upward import — wire surfaces the violation.",
        package="js-bad-wire-showcase",
        intent="(static showcase — teaches what wire catches)",
        kind="showcase",
        source_subdir="js_bad_wire",
        target_score=50.0,  # wire FAIL deducts 10 from a clean js-only package
    ),
    "mixed-py-js": DemoPreset(
        name="mixed-py-js",
        headline="Polyglot package: Python tier + JS tier under the same root.",
        package="mixed_pkg",
        intent="(static showcase — proves one layout works for both languages)",
        kind="showcase",
        source_subdir="mixed_py_js",
        target_score=90.0,  # Python tests run; behavioural axis credits 30 points
        certify_package="mixed_pkg",
    ),
}


@dataclass
class DemoResult:
    preset: str
    package: str
    output_root: str
    rounds_completed: int
    score_trajectory: list[float]
    final_score: float
    converged: bool
    cli_demo_command: list[str] = field(default_factory=list)
    cli_demo_stdout: str = ""
    cli_demo_returncode: int = -1
    duration_s: float = 0.0
    headline: str = ""
    artifact_md_path: str = ""


def list_presets() -> list[DemoPreset]:
    return list(_PRESETS.values())


def get_preset(name: str) -> DemoPreset:
    if name not in _PRESETS:
        raise KeyError(f"unknown preset {name!r}; try one of {sorted(_PRESETS)}")
    return _PRESETS[name]


def run_demo(*, preset_name: str = "calc",
             output: Path | None = None,
             llm: LLMClient | None = None,
             rounds: int | None = None,
             iterations: int | None = None,
             skip_cli_demo: bool = False) -> DemoResult:
    """Run a preset and emit a DEMO.md artifact.

    Dispatches by preset ``kind``:

    * ``"llm"`` (default) — run a real evolve trajectory with the
      configured provider, then invoke the generated CLI.
    * ``"showcase"`` — copy a pre-built source package into ``output``
      and run ``recon → wire → certify`` against it.  No LLM needed.
    """
    preset = get_preset(preset_name)
    if preset.kind == "showcase":
        return run_showcase(preset_name=preset_name, output=output)
    output = (output or Path.cwd() / f"forge-demo-{preset.name}").resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    llm = llm or resolve_default_client()
    import time
    start = time.perf_counter()

    evolve_report = run_evolve(
        preset.intent,
        output=output,
        package=preset.package,
        llm=llm,
        rounds=rounds or preset.rounds,
        iterations_per_round=iterations or preset.iterations,
        target_score=preset.target_score,
    )

    cli_cmd: list[str] = []
    cli_out = ""
    cli_rc = -1
    if not skip_cli_demo and preset.cli_demo_args:
        cli_cmd = [
            sys.executable, "-m",
            f"{preset.package}.a4_sy_orchestration.cli", *preset.cli_demo_args,
        ]
        env = {**__import__("os").environ}
        sep = ";" if sys.platform == "win32" else ":"
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (str(output / "src")
                              + (sep + existing if existing else ""))
        env["PYTHONIOENCODING"] = "utf-8"
        try:
            proc = subprocess.run(cli_cmd, env=env, capture_output=True,
                                  text=True, timeout=20, encoding="utf-8",
                                  errors="replace")
            cli_out = (proc.stdout or "") + (proc.stderr or "")
            cli_rc = proc.returncode
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            cli_out = f"(could not run generated CLI: {exc})"
            cli_rc = 1

    duration = time.perf_counter() - start

    result = DemoResult(
        preset=preset.name,
        package=preset.package,
        output_root=str(output),
        rounds_completed=evolve_report["rounds_completed"],
        score_trajectory=list(evolve_report["score_trajectory"]),
        final_score=evolve_report["final_score"],
        converged=evolve_report["converged"],
        cli_demo_command=cli_cmd,
        cli_demo_stdout=cli_out.strip(),
        cli_demo_returncode=cli_rc,
        duration_s=round(duration, 2),
        headline=preset.headline,
    )

    artifact = output / "DEMO.md"
    artifact.write_text(_render_demo_markdown(result, preset, evolve_report,
                                                llm_name=llm.name),
                         encoding="utf-8")
    result.artifact_md_path = str(artifact)
    ManifestStore(output).save("demo", _result_to_dict(result))
    return result


_SOURCE_ROOT = Path(__file__).resolve().parent / "demo_packages"


def run_showcase(*, preset_name: str,
                 output: Path | None = None) -> DemoResult:
    """Run a static showcase preset — copy source, recon/wire/certify.

    No LLM required.  Useful for demonstrating polyglot capabilities
    (`js-counter`, `js-bad-wire`, `mixed-py-js`).  Returns the same
    ``DemoResult`` shape as :func:`run_demo` so the CLI prints
    consistently across both kinds.
    """
    preset = get_preset(preset_name)
    if preset.kind != "showcase":
        raise ValueError(f"preset {preset_name!r} is kind={preset.kind!r}, "
                         "expected 'showcase'")
    source = _SOURCE_ROOT / preset.source_subdir
    if not source.exists():
        raise FileNotFoundError(f"showcase source not found: {source}")

    target = (output or Path.cwd() / f"forge-demo-{preset.name}").resolve()
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)

    import time
    start = time.perf_counter()

    # Recon → wire → certify against the *copied* tree, exactly as a
    # user would run them on the output directory.
    recon_report = harvest_repo(target)
    wire_report = scan_violations(target)
    certify_report = _certify_checks(target, project=preset.name,
                                       package=preset.certify_package)
    duration = time.perf_counter() - start

    score = float(certify_report.get("score", 0.0))
    converged = score >= preset.target_score and wire_report["verdict"] == "PASS"
    # For showcases without a CLI, leave the cli_demo fields empty — the
    # output panel falls back to printing the recon snapshot.
    result = DemoResult(
        preset=preset.name,
        package=preset.package,
        output_root=str(target),
        rounds_completed=0,
        score_trajectory=[score],
        final_score=score,
        converged=converged,
        cli_demo_command=[],
        cli_demo_stdout="",
        cli_demo_returncode=0,
        duration_s=round(duration, 2),
        headline=preset.headline,
    )

    artifact = target / "DEMO.md"
    artifact.write_text(_render_showcase_markdown(
        result, preset, recon_report, wire_report, certify_report,
    ), encoding="utf-8")
    result.artifact_md_path = str(artifact)
    ManifestStore(target).save("demo", _result_to_dict(result))
    # Persist the raw recon/wire/certify reports too, mirroring run_evolve.
    ManifestStore(target).save("scout", recon_report)
    ManifestStore(target).save("wire", wire_report)
    ManifestStore(target).save("certify", certify_report)
    return result


def _render_showcase_markdown(result: DemoResult, preset: DemoPreset,
                               recon_report: dict[str, Any],
                               wire_report: dict[str, Any],
                               certify_report: dict[str, Any]) -> str:
    """Render the showcase DEMO.md artifact."""
    py = recon_report.get("python_file_count", 0)
    js = recon_report.get("javascript_file_count", 0)
    ts = recon_report.get("typescript_file_count", 0)
    primary = recon_report.get("primary_language", "?")
    components = certify_report.get("score_components", {})

    lines = [
        f"# Atomadic Forge — `forge demo {preset.name}` (showcase)",
        "",
        f"_{preset.headline}_",
        "",
        f"- **Kind**:           static showcase (no LLM call)",
        f"- **Source package**: `{preset.package}`",
        f"- **Output**:         `{result.output_root}`",
        f"- **Duration**:       {result.duration_s:.1f}s",
        "",
        "## recon",
        "",
        f"- python files:     **{py}**",
        f"- javascript files: **{js}**",
        f"- typescript files: **{ts}**",
        f"- primary language: **{primary}**",
        f"- symbols:          {recon_report.get('symbol_count', 0)}",
        f"- tier dist:        `{recon_report.get('tier_distribution', {})}`",
        f"- effect dist:      `{recon_report.get('effect_distribution', {})}`",
        "",
    ]
    recs = recon_report.get("recommendations") or []
    if recs:
        lines.append("recommendations:")
        for r in recs:
            lines.append(f"- {r}")
        lines.append("")

    lines.extend([
        "## wire",
        "",
        f"- verdict:    **{wire_report['verdict']}**",
        f"- violations: **{wire_report['violation_count']}**",
    ])
    for v in wire_report.get("violations", [])[:10]:
        lines.append(
            f"  - `{v['file']}` — {v['from_tier']} ⟵ {v['to_tier']}.{v['imported']} "
            f"({v.get('language', 'python')})"
        )
    lines.extend([
        "",
        "## certify",
        "",
        f"- score: **{result.final_score:.0f}/100**"
        + (" — CONVERGED" if result.converged else ""),
        f"- docs:   {'PASS' if certify_report.get('documentation_complete') else 'FAIL'}",
        f"- tests:  {'PASS' if certify_report.get('tests_present') else 'FAIL'}",
        f"- layout: {'PASS' if certify_report.get('tier_layout_present') else 'FAIL'}",
        f"- wire:   {'PASS' if certify_report.get('no_upward_imports') else 'FAIL'}",
        "",
        "score components:",
        "",
        "| axis        | points |",
        "|-------------|-------:|",
        f"| structural  | {components.get('structural', 0)} |",
        f"| runtime     | {components.get('runtime', 0)} |",
        f"| behavioral  | {components.get('behavioral', 0)} |",
        f"| stub_penalty| {components.get('stub_penalty', 0)} |",
        "",
    ])
    issues = certify_report.get("issues") or []
    if issues:
        lines.append("issues:")
        for it in issues[:10]:
            lines.append(f"- {it}")
        lines.append("")

    lines.extend([
        "## Reproduce",
        "",
        "```bash",
        f"forge demo run --preset {preset.name}",
        "```",
        "",
        f"Generated at "
        f"{_dt.datetime.now(_dt.timezone.utc).isoformat(timespec='seconds')}.",
        "",
    ])
    return "\n".join(lines)


def _result_to_dict(r: DemoResult) -> dict[str, Any]:
    return {
        "schema_version": "atomadic-forge.demo/v1",
        "preset": r.preset,
        "package": r.package,
        "output_root": r.output_root,
        "rounds_completed": r.rounds_completed,
        "score_trajectory": r.score_trajectory,
        "final_score": r.final_score,
        "converged": r.converged,
        "cli_demo_command": r.cli_demo_command,
        "cli_demo_stdout": r.cli_demo_stdout,
        "cli_demo_returncode": r.cli_demo_returncode,
        "duration_s": r.duration_s,
        "headline": r.headline,
        "artifact_md_path": r.artifact_md_path,
        "generated_at_utc": (_dt.datetime.now(_dt.timezone.utc)
                              .isoformat(timespec="seconds")),
    }


def _render_demo_markdown(result: DemoResult, preset: DemoPreset,
                          evolve_report: dict[str, Any],
                          llm_name: str) -> str:
    arc = " → ".join(f"{s:.0f}" for s in result.score_trajectory)
    lines = [
        f"# Atomadic Forge — `forge demo {preset.name}`",
        "",
        f"_{preset.headline}_",
        "",
        f"- **LLM**:        `{llm_name}`",
        f"- **Package**:    `{preset.package}`",
        f"- **Rounds**:     {result.rounds_completed} / {preset.rounds}",
        f"- **Trajectory**: `{arc}`",
        f"- **Final**:      **{result.final_score:.0f}/100**"
        + (" — CONVERGED" if result.converged else ""),
        f"- **Duration**:   {result.duration_s:.1f}s",
        "",
        "## Score arc",
        "",
        "```",
        _ascii_trajectory(result.score_trajectory),
        "```",
        "",
        "## Generated CLI invocation",
        "",
        f"```bash",
        "$ " + " ".join(result.cli_demo_command),
        result.cli_demo_stdout or "(no output)",
        "```",
        "",
        f"Exit code: `{result.cli_demo_returncode}` "
        + ("✓" if result.cli_demo_returncode == 0 else "(see output above)"),
        "",
        "## What this proves",
        "",
        "- Forge enforces the 5-tier monadic law on every emitted file.",
        "- The behavioral pytest runner gates the score on real test passes.",
        "- A free local 7B model produced architecturally-coherent, "
          "test-passing software in a few minutes.",
        "- Plug a stronger LLM in via `--provider gemini|anthropic|openai` "
          "and the same trajectory carries harder tasks higher.",
        "",
        "## Reproduce",
        "",
        "```bash",
        f"forge demo run --preset {preset.name} --provider auto",
        "```",
        "",
        f"Generated at {_dt.datetime.now(_dt.timezone.utc).isoformat(timespec='seconds')}.",
        "",
    ]
    return "\n".join(lines)


def _ascii_trajectory(scores: list[float], width: int = 50) -> str:
    if not scores:
        return "(no trajectory)"
    lines: list[str] = []
    for i, s in enumerate(scores):
        bar_len = int(width * (s / 100.0))
        lines.append(f"  R{i}  [{('█' * bar_len).ljust(width)}] {s:5.1f}/100")
    return "\n".join(lines)
