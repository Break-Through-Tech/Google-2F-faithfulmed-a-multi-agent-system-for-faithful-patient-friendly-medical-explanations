"""Run Alicia's readability scorer on the Refiner's draft.

This helper does not rewrite clinical text. A passing draft becomes
``final_answer``; a draft that needs work returns its score and a suggestion
so the orchestrator can decide whether to request a rewrite. Any later rewrite
must go through the Verifier again before it is treated as final.
"""

from evaluation.readability import evaluate_readability


def run_readability(
    revised_draft: str,
    max_grade: float = 8,
    max_words: int | None = None,
) -> dict:
    """Score a revised draft and return fields for the shared ADK state.

    Args:
        revised_draft: Text produced by the Refiner.
        max_grade: Maximum Flesch-Kincaid grade level to pass.
        max_words: Optional word-count limit passed to the shared scorer.

    Returns:
        A JSON-serializable mapping with ``final_answer`` when the text passes,
        the full scorer result, a readable status, and a suggestion when it
        needs further work. The helper never edits the input text.
    """
    if not isinstance(revised_draft, str):
        raise TypeError("revised_draft must be a string.")

    score = evaluate_readability(
        revised_draft,
        max_grade=max_grade,
        max_words=max_words,
    )
    passes = score.get("status") == "ok" and score.get("passes_readability") is True

    if passes:
        suggestion = None
        status = "passed"
        final_answer = revised_draft
    elif score.get("status") != "ok":
        status = "invalid"
        final_answer = None
        suggestion = score.get("error", "Provide a non-empty explanation to score.")
    elif score.get("is_refusal"):
        status = "needs_review"
        final_answer = None
        suggestion = (
            "The scorer detected a refusal. Review whether this response is "
            "appropriate; readability simplification alone will not resolve it."
        )
    else:
        status = "needs_simplification"
        final_answer = None
        reasons = []
        grade = score.get("flesch_kincaid_grade")
        if grade is not None and not score.get("passes_grade_target", False):
            reasons.append(
                f"lower the Flesch-Kincaid grade from {grade} to {max_grade} or below"
            )
        if not score.get("passes_length_target", True):
            reasons.append(f"reduce the explanation to {max_words} words or fewer")
        suggestion = (
            "Simplify the wording while preserving every clinical fact and "
            "uncertainty; " + " and ".join(reasons) + "."
        )

    return {
        "final_answer": final_answer,
        "readability_status": status,
        "readability_pass": passes,
        "readability_score": score,
        "suggestion": suggestion,
        "faithfulness_recheck_required": False,
    }


if __name__ == "__main__":
    # Synthetic demonstration for the October contribution check.
    example = (
        "Your blood sugar was low. The test did not show a heart attack. "
        "Take your medicine as prescribed and call your care team if you feel worse."
    )
    import json

    print(json.dumps(run_readability(example), indent=2))
