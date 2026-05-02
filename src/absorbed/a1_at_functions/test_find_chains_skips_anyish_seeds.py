"""Test the emergent type-matcher + chain finder."""
from __future__ import annotations

from atomadic_forge.a0_qk_constants.emergent_types import SymbolSignatureCard
from atomadic_forge.a1_at_functions.emergent_compose import (
    find_chains,
    is_anyish,
    types_compatible,
)


def _card(name: str, *, inputs: list[tuple[str, str]], output: str,
          tier: str = "a1_at_functions", domain: str = "x",
          is_pure: bool = True) -> SymbolSignatureCard:
    return SymbolSignatureCard(
        name=name, qualname=f"pkg.{name}", module="pkg", tier=tier,
        domain=domain, inputs=inputs, output=output, is_pure=is_pure,
        docstring="",
    )


def test_types_compatible_exact_match():
    assert types_compatible("Path", "Path")
    assert types_compatible("list[str]", "list[str]")


def test_types_compatible_optional_widens():
    assert types_compatible("Path", "Optional[Path]")
    assert types_compatible("Path | None", "Path")


def test_types_compatible_collection_variance():
    assert types_compatible("list[str]", "Iterable[str]")
    assert types_compatible("list[int]", "Sequence[int]")
    # but with strict mode, generic-vs-concrete must align.
    assert not types_compatible("list", "list[int]", strict=True)
    assert types_compatible("list", "list[int]", strict=False)


def test_strict_refuses_any_bridge():
    assert types_compatible("Any", "Path", strict=False)
    assert not types_compatible("Any", "Path", strict=True)
    assert not types_compatible("Path", "Any", strict=True)


def test_is_anyish_classifies_dict_str_any():
    assert is_anyish("Any")
    assert is_anyish("dict[str, Any]")
    assert is_anyish("Mapping[str, Any]")
    assert not is_anyish("list[Path]")
    assert not is_anyish("CherryPickResult")


def test_find_chains_skips_anyish_seeds():
    cards = [
        _card("noisy", inputs=[("x", "Any")], output="dict[str, Any]"),
        _card("clean", inputs=[("p", "Path")], output="Symbol"),
        _card("consumes_symbol", inputs=[("s", "Symbol")], output="Report"),
    ]
    chains = find_chains(cards, max_depth=3, drop_anyish_seeds=True,
                         strict_types=True, domain_jump_required=False)
    seeds = {chain["chain"][0] for chain in chains}
    assert "pkg.noisy" not in seeds
    # The clean → consumes chain should still exist.
    paths = {tuple(c["chain"]) for c in chains}
    assert ("pkg.clean", "pkg.consumes_symbol") in paths
