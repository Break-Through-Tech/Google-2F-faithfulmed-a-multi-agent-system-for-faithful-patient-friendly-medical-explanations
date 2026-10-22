"""Offline synthetic demonstration: python -m faithfulmed_demo.refiner_demo."""

import json

from faithfulmed_demo.roles.refiner import refine_state, run_refiner


def demo() -> dict:
    # Same pending-result fact as baseline/examples/synthetic_chest_pain.json.
    correction = "A nuclear stress test was done, but its result is still pending."
    source = ("A patient came to the hospital with chest pain. " + correction
              + " The patient will see a cardiologist in two weeks.")
    wrong = "Your stress test result was normal."
    draft = "You came to the hospital with chest pain.\n" + wrong + "\nYour follow-up is in two weeks."
    start = draft.index(wrong)
    verdict = {"faithful": False, "findings": [{
        "category": "unsupported", "start": start, "end": start + len(wrong),
        "original": wrong, "replacement": correction, "source_quote": correction,
        "reason": "The source says the result is pending, not normal.",
    }]}
    state = {"source_report": source, "draft": draft, "verdict": verdict}
    revised = refine_state(state)["revised_draft"]
    clean = run_refiner(revised, {"faithful": True, "findings": []})
    return {
        "mode": "deterministic synthetic fixture; verdict supplied, not a live Verifier",
        **state, "revised_draft": revised,
        "unflagged_text_preserved": revised == draft[:start] + correction + draft[start + len(wrong):],
        "clean_case_input": revised,
        "clean_verdict_preserves_input": clean == revised,
        "requires_verifier_recheck": True,
    }


if __name__ == "__main__":
    print(json.dumps(demo(), indent=2))
