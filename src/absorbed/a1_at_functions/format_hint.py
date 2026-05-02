"""Tier a1 — named error-message templates with concrete recovery commands.

Audit pain point (Lane B4): every CLI error should end with a suggested
next step. ``GEMINI_API_KEY not set`` becomes ``GEMINI_API_KEY not set
— here are three ways to recover``. The point is: a developer who
just installed Forge should never have to alt-tab to Stack Overflow.

This module is pure: it returns formatted strings. The CLI layer
decides whether to ``typer.echo`` them, fold them into a
``typer.BadParameter``, or pipe them through structured JSON output.

Templates are looked up by stable name (e.g. ``provider_missing_key``)
so call sites can pass a dict of substitutions and we centralize wording
without touching every command. Adding a hint:

    HINT_TEMPLATES["my_new_hint"] = '''… {var} …'''
    format_hint("my_new_hint", var="x")
"""
from __future__ import annotations

HINT_TEMPLATES: dict[str, str] = {
    # ----- LLM provider errors -------------------------------------------
    "provider_missing_key": (
        "{provider!s} is selected but its API key is not set.\n"
        "\n"
        "Recovery options:\n"
        "  1. Set the key:           export {env_var!s}=<your-key>\n"
        "  2. Get a free Gemini key: https://aistudio.google.com/apikey\n"
        "  3. Use local Ollama:      export FORGE_OLLAMA=1 && "
        "ollama pull qwen2.5-coder:7b\n"
        "  4. Use the offline stub:  --provider stub  (for tests / CI)\n"
        "\n"
        "Verify with: forge config test --provider {provider!s}"
    ),
    # ----- Wire / tier errors --------------------------------------------
    "no_tier_dirs": (
        "No tier directories were found at {path!s}.\n"
        "\n"
        "Expected at least three of:\n"
        "  a0_qk_constants/   a1_at_functions/   a2_mo_composites/\n"
        "  a3_og_features/    a4_sy_orchestration/\n"
        "\n"
        "Did you forget to materialize? Try:\n"
        "  forge auto <source-repo> {path!s} --apply --package <name>\n"
    ),
    "wire_fail_with_violations": (
        "Wire scan found {count} upward-import violation(s).\n"
        "\n"
        "Recovery options:\n"
        "  1. Get repair suggestions: forge wire {path!s} --suggest-repairs\n"
        "  2. Get a JSON report:      forge wire {path!s} --json > wire.json\n"
        "  3. Gate this in CI:        forge wire {path!s} --fail-on-violations\n"
    ),
    # ----- Certify errors -------------------------------------------------
    "certify_below_threshold": (
        "Certify score {score}/100 is below the {threshold}/100 gate.\n"
        "\n"
        "Inspect what failed and the cheapest path to recover:\n"
        "  forge certify {path!s} --json | python -m json.tool\n"
        "\n"
        "Common quick wins:\n"
        "  - documentation: add a README.md (free 25 points)\n"
        "  - tests:         add tests/test_*.py (free 25 points)\n"
        "  - imports:       forge wire {path!s} --suggest-repairs\n"
    ),
    "fail_under_out_of_range": (
        "--fail-under must be between 0 and 100. Got: {value!r}\n"
        "\n"
        "Common values:\n"
        "  --fail-under 75   # team-grade target\n"
        "  --fail-under 90   # release-grade target\n"
    ),
    # ----- Manifest / file errors ----------------------------------------
    "not_a_forge_manifest": (
        "{path!s}: not a Forge JSON manifest.\n"
        "\n"
        "Expected a JSON object whose top-level `schema_version` field "
        "starts with `atomadic-forge.` (e.g. `atomadic-forge.scout/v1`, "
        "`atomadic-forge.wire/v1`, etc.).\n"
        "\n"
        "Forge manifests are written under .atomadic-forge/ when you run\n"
        "  forge auto / forge recon / forge cherry / forge finalize\n"
        "with --apply or pass through ManifestStore."
    ),
}


def format_hint(name: str, /, **fmt: object) -> str:
    """Return the named hint template with ``fmt`` substituted in.

    Raises KeyError on unknown hint names so typos surface in tests
    rather than at runtime in front of users.
    """
    if name not in HINT_TEMPLATES:
        raise KeyError(f"unknown hint template: {name!r}")
    return HINT_TEMPLATES[name].format(**fmt)


def hint_lines(name: str, /, **fmt: object) -> list[str]:
    """Same as ``format_hint`` but returns the lines as a list.

    Useful when a caller wants to prepend ``    `` to indent the hint
    inside a larger error block.
    """
    return format_hint(name, **fmt).splitlines()
