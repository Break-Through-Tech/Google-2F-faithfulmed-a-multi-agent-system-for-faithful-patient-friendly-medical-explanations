"""Regression checks for the local readability handoff."""
import unittest
import pandas as pd
from evaluation.readability import (
    count_sentences, evaluate_readability, evaluate_outputs, summarize_results,
)


class ReadabilityTests(unittest.TestCase):
    def test_decimal_and_title(self):
        text = "Take 2.5 mg daily. Call Dr. Smith tomorrow."
        self.assertEqual(count_sentences(text), 2)
        self.assertIsNone(evaluate_readability(text)["smog_grade"])

    def test_empty_and_nontext(self):
        for text in [None, "", "  ", "...", "123"]:
            with self.subTest(text=text):
                self.assertEqual(evaluate_readability(text)["status"], "error")

    def test_smog_and_length(self):
        result = evaluate_readability("You feel ill. Get some rest. Call us tomorrow.", max_words=2)
        self.assertIsNotNone(result["smog_grade"])
        self.assertFalse(result["passes_length_target"])
        self.assertFalse(result["passes_readability"])

    def test_refusal_vs_disclaimer(self):
        self.assertTrue(evaluate_readability("I cannot help with this request.")["is_refusal"])
        self.assertFalse(evaluate_readability("I cannot help with this request.")["passes_readability"])
        self.assertFalse(evaluate_readability("Ask your doctor if you have questions.")["is_refusal"])

    def test_baseline_handoff_and_denominator(self):
        frame = pd.DataFrame([
            {"example_id": "a", "status": "ok", "model_output": "Get some rest."},
            {"example_id": "b", "status": "ok", "model_output": "I cannot help with this request."},
            {"example_id": "c", "status": "no_context", "model_output": ""},
            {"example_id": "d", "status": "ok", "model_output": ""},
        ])
        result = evaluate_outputs(frame)
        self.assertEqual(result.status.tolist(), frame.status.tolist())
        self.assertEqual(result.example_id.tolist(), frame.example_id.tolist())
        summary = summarize_results(result)
        self.assertEqual(summary["refusal_rate"], .5)
        self.assertEqual(summary["skipped_rows"], 1)
        self.assertEqual(summary["invalid_outputs"], 1)

    def test_empty_batch(self):
        self.assertIsNone(summarize_results(evaluate_outputs(pd.DataFrame(columns=["model_output"])))["refusal_rate"])


if __name__ == "__main__":
    unittest.main()
