import unittest

from verifier_rubric import (
    CONTRADICTORY,
    EMPTY_ANSWER,
    FULLY_SUPPORTED,
    INVALID,
    IRRELEVANT,
    NEUTRAL,
    UNREFERENCED,
    WEAK,
    classify_answer,
    classify_sentence,
)


class VerifierRubricTests(unittest.TestCase):
    def test_supporting_required_sentence_is_fully_supported(self):
        self.assertEqual(
            classify_sentence("required", [{"evidence_relation": "supporting"}]),
            FULLY_SUPPORTED,
        )

    def test_missing_citations_are_unreferenced(self):
        self.assertEqual(classify_sentence("required", None), UNREFERENCED)
        self.assertEqual(classify_sentence("required", []), UNREFERENCED)

    def test_evidence_categories_are_distinguished(self):
        cases = {
            "neutral": NEUTRAL,
            "not relevant": IRRELEVANT,
            "invalid citation": INVALID,
            "contradicting": CONTRADICTORY,
        }
        for relation, expected in cases.items():
            with self.subTest(relation=relation):
                self.assertEqual(
                    classify_sentence("required", [{"evidence_relation": relation}]),
                    expected,
                )

    def test_mixed_supporting_evidence_is_weak(self):
        self.assertEqual(
            classify_sentence(
                "required",
                [
                    {"evidence_relation": "supporting"},
                    {"evidence_relation": "supporting"},
                ],
            ),
            FULLY_SUPPORTED,
        )
        self.assertEqual(
            classify_sentence(
                "required",
                [
                    {"evidence_relation": "supporting"},
                    {"evidence_relation": "neutral"},
                ],
            ),
            NEUTRAL,
        )
        self.assertEqual(
            classify_sentence("unnecessary", [{"evidence_relation": "supporting"}]),
            WEAK,
        )

    def test_answer_uses_highest_risk_category(self):
        sentences = [
            {
                "answer_sentence_relevance": "required",
                "citation_assessment": [{"evidence_relation": "supporting"}],
            },
            {
                "answer_sentence_relevance": "required",
                "citation_assessment": [{"evidence_relation": "contradicting"}],
            },
        ]
        self.assertEqual(classify_answer(sentences), CONTRADICTORY)

    def test_empty_answer_is_flagged_instead_of_fully_supported(self):
        self.assertEqual(classify_answer([]), EMPTY_ANSWER)
        self.assertEqual(classify_answer(iter(())), EMPTY_ANSWER)


if __name__ == "__main__":
    unittest.main()
