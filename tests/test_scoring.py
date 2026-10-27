"""Advisor examples and protections against misleading scoring denominators."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from evaluation.scoring import Assessment, compute_metrics, generation_schema, safe_error, summarize, validate_assessment
from evaluation.score_outputs import advisor_jobs, public_job, run

FIXTURES = Path(__file__).resolve().parents[1] / "evaluation/examples/advisor_scoring_examples.json"


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(FIXTURES.read_text(encoding="utf-8"))

    def validate(self, case, assessment=None):
        return validate_assessment(self.data["source_report"], case["output"], self.data["key_facts"],
                                   self.data["retrieved_context"], assessment or case["reference_assessment"])

    def test_all_four_advisor_examples(self):
        for case in self.data["examples"]:
            with self.subTest(case=case["id"]):
                metrics = compute_metrics(self.validate(case))
                for key, expected in case["expected_counts"].items():
                    self.assertEqual(metrics[key], expected)

    def test_supported_background_addition_is_not_hallucination(self):
        metrics = compute_metrics(self.validate(self.data["examples"][0]))
        self.assertEqual(metrics["supported_additions"], 1)
        self.assertFalse(metrics["hallucination"])

    def test_omission_can_coexist_with_perfect_faithfulness(self):
        metrics = compute_metrics(self.validate(self.data["examples"][1]))
        self.assertEqual(metrics["faithfulness"], 1)
        self.assertEqual(metrics["omissions"], 1)
        self.assertFalse(metrics["hallucination"])

    def test_distortion_is_neither_addition_nor_missing_fact(self):
        metrics = compute_metrics(self.validate(self.data["examples"][3]))
        self.assertEqual(metrics["faithfulness"], .6)
        self.assertEqual(metrics["distorted_key_facts"], 2)
        self.assertEqual(metrics["omissions"], 1)  # The missing follow-up only.
        self.assertEqual(metrics["additions"], 0)

    def test_fabricated_evidence_quote_is_rejected(self):
        case = self.data["examples"][0]
        assessment = copy.deepcopy(case["reference_assessment"])
        assessment["claims"][0]["evidence"][0]["quote"] = "The patient has cancer."
        with self.assertRaisesRegex(ValueError, "quotes evidence absent"):
            self.validate(case, assessment)

    def test_background_cannot_prove_patient_diagnosis(self):
        case = self.data["examples"][0]
        assessment = copy.deepcopy(case["reference_assessment"])
        assessment["claims"][-1]["scope"] = "patient"
        with self.assertRaisesRegex(ValueError, "Context alone cannot support"):
            self.validate(case, assessment)

    def test_missing_coverage_is_not_implicitly_success(self):
        case = self.data["examples"][0]
        assessment = copy.deepcopy(case["reference_assessment"])
        assessment["key_fact_coverage"].pop()
        with self.assertRaisesRegex(ValueError, "every fixed key fact"):
            self.validate(case, assessment)

    def test_empty_claim_inventory_does_not_get_100_percent(self):
        metrics = compute_metrics({"claims": [], "key_fact_coverage": []})
        self.assertIsNone(metrics["faithfulness"])
        self.assertIsNone(metrics["hallucination"])

    def test_drafts_and_failed_runs_are_not_released_output_performance(self):
        metrics = compute_metrics(self.validate(self.data["examples"][1]))
        records = [{"status": "scored", "metrics": metrics, "output_kind": "final"},
                   {"status": "scored", "metrics": metrics, "output_kind": "draft"},
                   {"status": "generation_failed"}]
        summary = summarize(records)
        self.assertEqual(summary["attempted_outputs"], 3)
        self.assertEqual(summary["scored_final_outputs"], 1)
        self.assertEqual(summary["scored_drafts"], 1)
        self.assertEqual(summary["unscored_outputs"], 1)

    def test_claim_weighted_and_output_averaged_scores_are_separate(self):
        records = [{"status": "scored", "metrics": compute_metrics(self.validate(self.data["examples"][i]))}
                   for i in [0, 3]]
        summary = summarize(records)
        self.assertAlmostEqual(summary["faithfulness_micro"], 10 / 12)
        self.assertAlmostEqual(summary["faithfulness_macro"], .8)
        self.assertEqual(summary["hallucinated_outputs"], 1)
        self.assertEqual(summary["hallucination_rate"], .5)

    def test_reference_assessment_is_never_sent_to_judge(self):
        job = {"source_report": "report", "output": "answer", "key_facts": [],
               "retrieved_context": [], "reference_assessment": {"expected": "secret"}}
        self.assertEqual(set(public_job(job)), {"source_report", "output", "key_facts", "retrieved_context"})

    def test_google_request_schema_omits_unsupported_keyword_but_local_schema_is_strict(self):
        self.assertIn("additionalProperties", json.dumps(Assessment.model_json_schema()))
        self.assertNotIn("additionalProperties", json.dumps(generation_schema(Assessment)))

    def test_service_error_does_not_expose_credentials_or_response_details(self):
        error = RuntimeError("secret key and URL")
        error.code = 400
        error.details = {"error": {"details": [{"reason": "API_KEY_INVALID", "metadata": {"api_key": "secret"}}]}}
        saved = safe_error(error)
        self.assertEqual(saved["service_reason"], "API_KEY_INVALID")
        self.assertNotIn("secret", json.dumps(saved))

    def test_refusal_stays_in_readability_denominator(self):
        records = [{"status": "refusal", "readability": {"status": "ok", "passes_readability": False}}]
        result = summarize(records)
        self.assertEqual(result["readability_scored_outputs"], 1)
        self.assertEqual(result["readability_pass_rate"], 0)
        self.assertIsNone(result["faithfulness_micro"])

    def test_same_case_cannot_change_key_facts_between_systems(self):
        first = advisor_jobs()[0]
        second = copy.deepcopy(first)
        second["system"] = "other"
        second["key_facts"][0]["text"] = "A different scoring requirement."
        with tempfile.TemporaryDirectory() as temp, self.assertRaisesRegex(ValueError, "identical source text and key facts"):
            run([first, second], Path(temp) / "out.json", model="fixture", reference=True)

    def test_duplicate_output_cannot_inflate_denominator(self):
        first = advisor_jobs()[0]
        with tempfile.TemporaryDirectory() as temp, self.assertRaisesRegex(ValueError, "duplicate the denominator"):
            run([first, copy.deepcopy(first)], Path(temp) / "out.json", model="fixture", reference=True)


if __name__ == "__main__":
    unittest.main()
