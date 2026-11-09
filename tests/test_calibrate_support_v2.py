"""The new development judge keeps reference agreement and coverage distinct."""

import copy
import json

import pytest
from unittest.mock import patch

from evaluation.audit_support_references import POLICY
from evaluation.calibrate_support_v2 import (VERSION, DiagnosticError, SupportDecisionV2, judge, judge_payload, prepare_suite,
    run_suite, summarize, validate_decision)
from evaluation.scoring import digest, generation_schema


def setup_suite():
    source = {"dataset_sha256": "source-hash", "question_groups": {"development": ["dev"], "heldout": ["held"]},
              "splits": {"development": [
                  {"case_id": "a", "question_id": "dev", "question": "Question?", "sentence": "A and B.",
                   "cited_pmid": "123", "reference_relation": "supporting", "reference_support": True},
                  {"case_id": "b", "question_id": "dev", "question": "Question?", "sentence": "C.",
                   "cited_pmid": "456", "reference_relation": "neutral", "reference_support": False},
                  {"case_id": "c", "question_id": "dev", "question": "Question?", "sentence": "D.",
                   "cited_pmid": "789", "reference_relation": "neutral", "reference_support": False}],
                  "heldout": [{"case_id": "hidden", "sentence": "Heldout must not be copied."}]}}
    doc = {"pmid": "123", "title": "Title", "abstract": "Evidence A.",
           "context_sha256": digest(["Title", "Evidence A."]), "source_url": "https://pubmed.ncbi.nlm.nih.gov/123/"}
    cache = {"records": {"123": doc}}
    rows = []
    for case, flags, context in zip(source["splits"]["development"], [[], ["conflicting_binary_references", "title_abstract_not_cached"], ["title_abstract_not_cached"]], [True, False, False]):
        rows.append({"case_id": case["case_id"], "split": "development", "question_id": "dev", "pmid": case["cited_pmid"],
                     "cached_context": context, "audit_flags": flags, "relation_counts": {case["reference_relation"]: 1}, "reference_records": []})
    audit = {"policy_version": POLICY, "suite_digest": digest(source), "context_cache_digest": digest(cache), "cases": rows}
    return source, audit, cache


def decision():
    return {"propositions": [
        {"proposition": "A", "sentence_quote": "A", "status": "supported", "evidence_quote": "Evidence A.", "reason": "Shown."},
        {"proposition": "B", "sentence_quote": "B", "status": "not_established", "evidence_quote": "", "reason": "Absent."}],
        "complete_sentence_supported": False, "citation_support": True, "citation_reason": "A is supported."}


def test_service_schema_excludes_unsupported_keys_but_local_parser_is_strict():
    schema = generation_schema(SupportDecisionV2)
    assert "additionalProperties" not in json.dumps(schema)
    bad = decision()
    bad["unexpected"] = "not allowed"
    case = prepare_suite(*setup_suite())["cases"][0]
    with pytest.raises(ValueError):
        validate_decision(case, bad)


def test_development_only_eligibility_and_label_blind_payload():
    suite = prepare_suite(*setup_suite())
    assert suite["counts"]["selected"] == 3
    assert suite["counts"]["ready_eligible"] == 1
    assert suite["cases"][1]["reference_status"] == "ambiguous"
    assert suite["cases"][1]["reference_support"] is None
    assert suite["cases"][2]["context_status"] == "pending"
    assert "Heldout must not be copied" not in json.dumps(suite)
    assert set(judge_payload(suite["cases"][0])) == {"question", "sentence", "evidence"}
    with pytest.raises(ValueError, match="full cached"):
        judge_payload(suite["cases"][2])


def test_partial_support_and_literal_anchors_are_enforced():
    case = prepare_suite(*setup_suite())["cases"][0]
    assert not validate_decision(case, decision())["complete_sentence_supported"]
    for field, value in [("sentence_quote", "invented"), ("evidence_quote", "invented")]:
        bad = decision()
        bad["propositions"][0][field] = value
        with pytest.raises(ValueError): validate_decision(case, bad)
    bad = decision()
    bad["complete_sentence_supported"] = True
    with pytest.raises(ValueError): validate_decision(case, bad)
    bad = decision()
    bad["propositions"][0]["evidence_quote"] = ""
    with pytest.raises(ValueError): validate_decision(case, bad)


def test_cache_mismatch_and_heldout_injection_are_rejected(tmp_path):
    source, audit, cache = setup_suite()
    cache["records"]["123"]["abstract"] = "Changed."
    with pytest.raises(ValueError, match="audit|Audit"):
        prepare_suite(source, audit, cache)
    suite = prepare_suite(*setup_suite())
    suite["cases"][0]["question_id"] = "held"
    with pytest.raises(ValueError, match="development questions"):
        run_suite(suite, tmp_path / "never.json", model="test", judge_fn=lambda *_args, **_kwargs: decision())


def test_run_uses_only_ready_eligible_cases_and_resumes(tmp_path):
    suite = prepare_suite(*setup_suite())
    calls = []
    def fake(case, *, model):
        calls.append(case["case_id"])
        return decision()
    output = tmp_path / "results.json"
    result = run_suite(suite, output, model="test", judge_fn=fake)
    run_suite(suite, output, model="test", judge_fn=fake)
    assert calls == ["a"]
    assert result["summary"]["citation_agreement"]["scored"] == 1
    assert result["summary"]["coverage_diagnostic"]["complete_supported"] == 0
    assert result["summary"]["citation_agreement"]["cohen_kappa"] is None
    with pytest.raises(ValueError, match="different settings"):
        run_suite(suite, output, model="changed", judge_fn=fake)


def test_ambiguous_and_abstained_predictions_never_enter_agreement():
    suite = prepare_suite(*setup_suite())
    ambiguous = {"case_id": "b", "status": "ok", **decision()}
    abstained = {"case_id": "a", "status": "ok", **decision(), "citation_support": None}
    summary = summarize(suite["cases"], [ambiguous, abstained])
    assert summary["citation_agreement"]["scored"] == 0
    assert summary["abstained_cases"] == 1
    assert summary["coverage_diagnostic"]["successful_outputs"] == 2


def test_tampered_evidence_is_rejected_before_call(tmp_path):
    suite = prepare_suite(*setup_suite())
    suite["cases"][0]["evidence"] = "Altered"
    calls = []
    result = run_suite(suite, tmp_path / "out.json", model="test", judge_fn=lambda *a, **k: calls.append(1))
    assert not calls
    assert result["records"][0]["status"] == "error"
    assert result["records"][0]["error_category"] == "input_invalid"


@pytest.mark.parametrize("mutate,expected", [
    (lambda d: d["propositions"][0].update(sentence_quote="not present"), "sentence_quote_missing_or_not_verbatim"),
    (lambda d: d["propositions"][0].update(evidence_quote="not present"), "evidence_quote_not_verbatim"),
    (lambda d: d["propositions"][0].update(evidence_quote=""), "evidence_quote_missing"),
    (lambda d: d.update(complete_sentence_supported=True), "coverage_inconsistent"),
    (lambda d: d.update(propositions=[], citation_support=True), "response_schema_invalid"),
    (lambda d: d["propositions"][0].update(status="not_established"), "citation_without_supported_claim"),
])
def test_failures_save_specific_safe_categories_and_retry_history(tmp_path, mutate, expected):
    suite = prepare_suite(*setup_suite())
    bad = decision()
    mutate(bad)
    output = tmp_path / "out.json"
    first = run_suite(suite, output, model="test", judge_fn=lambda *a, **k: bad)
    assert first["records"][0]["error_category"] == expected
    assert first["records"][0]["error_stage"] == "response_validation"
    result = run_suite(suite, output, model="test", retry_errors=True, judge_fn=lambda *a, **k: decision())
    assert len(result["records"]) == 2
    assert result["records"][0]["error_category"] == expected
    assert result["records"][1]["status"] == "ok"
    assert result["summary"]["citation_agreement"]["scored"] == 1


def test_provider_error_does_not_save_secret_or_raw_error(tmp_path):
    suite = prepare_suite(*setup_suite())
    def fail(*args, **kwargs):
        raise RuntimeError("private-key-and-raw-provider-message")
    output = tmp_path / "out.json"
    result = run_suite(suite, output, model="test", judge_fn=fail)
    assert result["records"][0]["error_stage"] == "service_call_or_response"
    assert result["records"][0]["error_category"] == "service_or_unclassified_error"
    assert "private-key-and-raw-provider-message" not in output.read_text()


def test_response_parsing_error_has_safe_diagnostic():
    class Client:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        @property
        def models(self): return self
        def generate_content(self, **kwargs): return object()
    case = prepare_suite(*setup_suite())["cases"][0]
    with patch("faithfulmed_demo.config.model_client", return_value=Client()), \
         patch("faithfulmed_demo.config.require_text", return_value="not-json-secret"), \
         pytest.raises(DiagnosticError) as error:
        judge(case, model="test")
    assert error.value.category == "response_invalid_json"
    assert "not-json-secret" not in str(error.value)


def test_incomplete_response_has_safe_diagnostic():
    class Client:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        @property
        def models(self): return self
        def generate_content(self, **kwargs): return object()
    case = prepare_suite(*setup_suite())["cases"][0]
    with patch("faithfulmed_demo.config.model_client", return_value=Client()), \
         patch("faithfulmed_demo.config.require_text", side_effect=ValueError("private response")), \
         pytest.raises(DiagnosticError) as error:
        judge(case, model="test")
    assert error.value.category == "response_incomplete_or_empty"
    assert "private response" not in str(error.value)
