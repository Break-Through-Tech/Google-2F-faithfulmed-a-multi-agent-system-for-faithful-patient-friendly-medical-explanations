"""Document context must be source-matched, label-blind and development-only."""

import copy
import io
import unittest
from pathlib import Path
from unittest.mock import patch

from evaluation.calibrate_verifier import judge_payload, run_suite
from evaluation.investigate_calibration import (audit_document_labels, compare_runs,
    enrich_pilot, fetch_context, parse_pubmed, pilot_cases)
from evaluation.scoring import digest

XML = b'''<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID>
<Article><ArticleTitle>A <i>test</i> study.</ArticleTitle><Abstract>
<AbstractText Label="BACKGROUND">We investigated a treatment.</AbstractText>
<AbstractText Label="RESULTS">The trial found a benefit.</AbstractText>
</Abstract></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>'''


class CalibrationContextTests(unittest.TestCase):
    def setUp(self):
        self.case = {"case_id": "original-case-id", "question_id": "q1", "question": "Does it help?",
                     "sentence": "The treatment helps.", "evidence": "We investigated a treatment.",
                     "cited_pmid": "123", "reference_support": True, "reference_relation": "supporting"}
        self.suite = {"dataset_sha256": "original-dataset", "question_groups": {"heldout": ["q2"]},
                      "splits": {"development": [self.case], "heldout": [{"case_id": "never-used"}]}}
        self.run = {"run_digest": "original-run", "split": "development",
                    "records": [{"case_id": self.case["case_id"], "question_id": "q1", "status": "ok", "supports_sentence": False}]}
        self.cache = {"records": parse_pubmed(XML)}

    def test_parser_keeps_title_and_results_from_correct_pmid(self):
        parsed = parse_pubmed(XML)["123"]
        self.assertEqual(parsed["title"], "A test study.")
        self.assertIn("RESULTS: The trial found a benefit.", parsed["abstract"])

    def test_fetch_only_sends_numeric_document_ids(self):
        with patch("urllib.request.urlopen", return_value=io.BytesIO(XML)) as mock:
            result = fetch_context([self.case])
        url = mock.call_args.args[0].full_url
        self.assertIn("id=123", url)
        self.assertNotIn("Does", url)
        self.assertNotIn("reference_support", url)
        self.assertEqual(set(result["records"]), {"123"})

    def test_invalid_id_never_reaches_network(self):
        case = {**self.case, "cited_pmid": "123&question=export"}
        with patch("urllib.request.urlopen") as mock, self.assertRaises(ValueError):
            fetch_context([case])
        mock.assert_not_called()

    def test_missing_returned_document_is_not_silently_skipped(self):
        with patch("urllib.request.urlopen", return_value=io.BytesIO(XML)), self.assertRaisesRegex(ValueError, "missing or unexpected"):
            fetch_context([{**self.case, "cited_pmid": "456"}])

    def test_enrichment_preserves_case_id_reference_and_original_suite(self):
        original = copy.deepcopy(self.suite)
        enriched = enrich_pilot(self.suite, self.run, self.cache)
        case = enriched["splits"]["development"][0]
        self.assertEqual(case["case_id"], self.case["case_id"])
        self.assertEqual(case["reference_support"], self.case["reference_support"])
        self.assertIn("The trial found a benefit.", case["evidence"])
        self.assertEqual(self.suite, original)
        self.assertEqual(enriched["splits"]["heldout"], [])

    def test_enriched_payload_does_not_include_labels_or_selected_snippet(self):
        enriched = enrich_pilot(self.suite, self.run, self.cache)
        payload = judge_payload(enriched["splits"]["development"][0])
        self.assertEqual(set(payload), {"question", "sentence", "evidence"})
        self.assertNotIn("original_evidence", payload)

    def test_changed_cache_is_rejected(self):
        self.cache["records"]["123"]["abstract"] = "Changed source."
        with self.assertRaisesRegex(ValueError, "changed after collection"):
            enrich_pilot(self.suite, self.run, self.cache)

    def test_missing_abstract_cannot_fall_back_to_snippet(self):
        record = self.cache["records"]["123"]
        record["abstract"] = ""
        record["context_sha256"] = digest([record["title"], ""])
        with self.assertRaisesRegex(ValueError, "title and abstract"):
            enrich_pilot(self.suite, self.run, self.cache)

    def test_heldout_run_cannot_be_used_for_tuning(self):
        self.run["split"] = "heldout"
        with self.assertRaisesRegex(ValueError, "restricted to development"):
            pilot_cases(self.suite, self.run)

    def test_document_label_conflict_is_reported_not_relabelled(self):
        data = [{"question_id": "q1", "machine_generated_answers": {
            "M1": {"answer_sentences": [{"answer_sentence_id": "1", "answer_sentence": "The treatment helps. [123]",
                "citation_assessment": [{"cited_pmid": "123", "evidence_relation": "supporting", "evidence_support": "One excerpt."}]}]},
            "M2": {"answer_sentences": [{"answer_sentence_id": "2", "answer_sentence": "The treatment helps [123].",
                "citation_assessment": [{"cited_pmid": "123", "evidence_relation": "neutral", "evidence_support": "Another excerpt."}]}]}}}]
        result = audit_document_labels(data, [self.case])[0]
        self.assertTrue(result["binary_conflict_with_nonblank_excerpts"])
        self.assertEqual(result["relation_counts"], {"supporting": 1, "neutral": 1})
        self.assertTrue(self.case["reference_support"])

    def test_comparison_requires_same_cases(self):
        after = {"records": [{"case_id": "different", "question_id": "q1", "status": "ok"}]}
        with self.assertRaisesRegex(ValueError, "exact same case IDs"):
            compare_runs(self.run, after)

    def test_diagnostic_has_no_heldout_execution_path(self):
        enriched = enrich_pilot(self.suite, self.run, self.cache)
        with patch("evaluation.calibrate_verifier.judge") as mock, self.assertRaisesRegex(ValueError, "No cases in this split"):
            run_suite(enriched, Path("unused.json"), split="heldout", model="test", judge_fn=mock)
        mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
