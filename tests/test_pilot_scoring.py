import pytest

from evaluation.pilot_scoring import restore_quote


def test_restores_markdown_and_whitespace_to_exact_source():
    source = "* **Dose:** Take 5 mg\n  daily."
    restored = restore_quote("Dose: Take 5 mg daily.", source)
    assert restored in source
    assert restored == "Dose:** Take 5 mg\n  daily."


@pytest.mark.parametrize("quote", ["Take 50 mg daily.", "Take 5 mg weekly.", "Take five mg daily.", "Do not take 5 mg daily."])
def test_rejects_semantic_changes(quote):
    with pytest.raises(ValueError):
        restore_quote(quote, "Take 5 mg daily.")


def test_rejects_ambiguous_formatting_match():
    with pytest.raises(ValueError):
        restore_quote("Dose: 5 mg", "**Dose:** 5 mg\n**Dose:** 5 mg")


def test_preserves_literal_multiplication():
    with pytest.raises(ValueError):
        restore_quote("2  5 mg", "2 * 5 mg")
