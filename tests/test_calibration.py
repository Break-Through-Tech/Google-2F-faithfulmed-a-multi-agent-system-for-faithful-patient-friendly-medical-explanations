"""Calibration needs isolated questions, hidden labels, and auditable retries."""

import json
import tempfile
import unittest
from pathlib import Path

from evaluation.calibrate_verifier import (judge_payload, prepare_suite, run_suite,
                                           summarize_predictions)


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        data = []
        for i in range(6):
            sentences = []
            for j, relation in enumerate(["supporting", "neutral", "invalid citation", "not relevant"]):
                sentences.append({"answer_sentence_id": str(j), "answer_sentence": f"Claim {i}-{j} [12345].",
                    "citation_assessment": [{"cited_pmid": "12345", "evidence_relation": relation,
                        "evidence_support": f"Evidence {i}-{j}." if j < 2 else None}]})
            data.append({"question_id": str(i), "question": f"Question {i}?",
                "machine_generated_answers": {"M1": {"answer_sentences": sentences},
                                              "M2": {"answer_sentences": sentences}}})
        self.path = self.directory / "source.json"
        self.path.write_text(json.dumps(data), encoding="utf-8")
        self.suite = prepare_suite(self.path, per_class=2)

    def test_deterministic_split_has_no_question_overlap(self):
        self.assertEqual(self.suite, prepare_suite(self.path, per_class=2))
        self.assertFalse(set(self.suite["question_groups"]["development"]) &
                         set(self.suite["question_groups"]["heldout"]))
        for split, cases in self.suite["splits"].items():
            self.assertTrue({c["question_id"] for c in cases} <= set(self.suite["question_groups"][split]))

    def test_missing_evidence_and_duplicate_answers_are_reported(self):
        excluded = self.suite["exclusions_and_deduplication"]
        self.assertEqual(excluded["invalid_citation_validity_not_assessed"], 12)
        self.assertEqual(excluded["no_evidence_excerpt"], 12)
        self.assertEqual(excluded["repeated_pair_records"], 12)

    def test_labels_and_answer_model_are_not_in_judge_payload(self):
        case = self.suite["splits"]["development"][0]
        self.assertEqual(set(judge_payload(case)), {"question", "sentence", "evidence"})

    def test_agreement_kappa_and_mismatches(self):
        cases = [{"case_id": str(i), "question_id": str(i), "reference_support": label,
                  "reference_relation": "supporting" if label else "neutral"}
                 for i, label in enumerate([True, True, False, False])]
        records = [{"case_id": str(i), "status": "ok", "supports_sentence": prediction, "reason": "test"}
                   for i, prediction in enumerate([True, False, False, False])]
        summary = summarize_predictions(records, cases)
        self.assertEqual(summary["agreement"], .75)
        self.assertEqual(summary["cohen_kappa"], .5)
        self.assertEqual(len(summary["mismatches"]), 1)

    def test_resume_does_not_repeat_completed_predictions(self):
        output = self.directory / "predictions.json"
        calls = []
        def fake(case, *, model):
            calls.append(case["case_id"])
            return {"supports_sentence": case["reference_support"], "reason": "test fixture", "evidence_quote": ""}
        run_suite(self.suite, output, model="test", limit=2, judge_fn=fake)
        result = run_suite(self.suite, output, model="test", limit=2, judge_fn=fake)
        self.assertEqual(len(calls), len(set(calls)))
        self.assertTrue(result["summary"]["complete"])
        with self.assertRaisesRegex(ValueError, "different suite/model/prompt"):
            run_suite(self.suite, output, model="changed", judge_fn=fake)

    def test_failed_prediction_retry_keeps_history_and_one_case_denominator(self):
        output = self.directory / "retry.json"
        def fail(case, *, model):
            raise ValueError("bad fixture response")
        run_suite(self.suite, output, model="test", limit=1, judge_fn=fail)
        def good(case, *, model):
            return {"supports_sentence": case["reference_support"], "reason": "test fixture", "evidence_quote": ""}
        state = run_suite(self.suite, output, model="test", limit=1, retry_errors=True, judge_fn=good)
        self.assertEqual(len(state["records"]), 2)
        self.assertEqual(state["summary"]["scored_cases"], 1)
        self.assertEqual(state["summary"]["attempted_cases"], 1)


if __name__ == "__main__":
    unittest.main()
