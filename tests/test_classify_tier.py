"""Test the word-boundary tier classifier."""

from atomadic_forge.a1_at_functions.classify_tier import (
    classify_tier, detect_effects, word_tokens,
)


def test_word_tokens_no_substring_false_positive():
    """Regression: 'atom' must not match inside 'atomadic'."""
    tokens = word_tokens("AtomadicArchitectureMachine atomadic-v2")
    assert "atomadic" in tokens
    # The atom_tokens trigger is "atom" — it should not be derived from "atomadic".
    # word_tokens DOES include "atom" as a camelCase split? No — atomadic doesn't have a capital A inside.
    # So "atom" should NOT appear.
    assert "atom" not in tokens


def test_classify_tier_atomadic_class_lands_a2_not_a1():
    tier = classify_tier(name="AtomadicArchitectureMachine", kind="class",
                          path="atomadic-v2/src/atomadic/aam.py")
    assert tier == "a2_mo_composites"


def test_classify_tier_promotes_with_state():
    tier = classify_tier(
        name="UserBucket", kind="class", path="repo/store.py",
        body_signals={"has_self_assign": True},
    )
    assert tier == "a2_mo_composites"


def test_classify_tier_pure_function():
    assert classify_tier(name="add", kind="function", path="util.py") == "a1_at_functions"


def test_classify_tier_orchestration_main():
    assert classify_tier(name="main", kind="function", path="cli.py") == "a4_sy_orchestration"


def test_detect_effects_pure():
    import ast
    fn = ast.parse("def f(a, b):\n    return a + b\n").body[0]
    assert detect_effects(fn) == ["pure"]


def test_detect_effects_urllib_io():
    import ast
    src = "def fetch(url):\n    import urllib.request\n    return urllib.request.urlopen(url).read()\n"
    fn = ast.parse(src).body[0]
    assert "io" in detect_effects(fn)
