"""Evidence IDs must resolve to unchanged source text, never invented quotations."""

import copy
import json

import pytest

from evaluation import calibrate_support_spans as spans
from evaluation.calibrate_support_v2 import DiagnosticError
from evaluation.scoring import digest


def suite():
    text = "Title.\n\nTreatment A helped. Treatment B was not tested."
    title, abstract = text.split("\n\n")
    case = dict(case_id="case", question_id="dev", question="What helped?", sentence="A and B helped.",
                evidence=text, context_title=title, context_abstract=abstract,
                context_sha256=digest([title, abstract]), context_status="ready",
                reference_status="eligible", reference_support=True, reference_relation="supporting")
    return spans.prepare_suite(dict(suite_version=spans.previous.VERSION, run_kind="development_only",
        question_groups={"development": ["dev"], "heldout": ["held"]}, cases=[case], counts={"selected": 1}))


def decision(case):
    ident = next(s["id"] for s in case["source_spans"] if "Treatment A helped" in s["text"])
    return dict(propositions=[dict(proposition="A helped", sentence_quote="A", status="supported",
                evidence_span_ids=[ident], reason="Reported outcome"),
                dict(proposition="B helped", sentence_quote="B helped", status="not_established",
                evidence_span_ids=[], reason="Not tested")],
                complete_sentence_supported=False, citation_support=True, citation_reason="Supports A only")


@pytest.mark.parametrize("text", [
    "Title\n\nA 1.5 cm result. Another result.", " Dr. X used 0.1 mg.\r\nNext paragraph.  ",
    "Unicode: \u03ba, \u00b1 and \u00a0space. Next sentence!", "No punctuation", "Title\n\nSingle paragraph\n"])
def test_spans_preserve_every_character_and_offset(text):
    result = spans.source_spans(text)
    assert "".join(s["text"] for s in result) == text
    assert result == spans.source_spans(text)
    assert len({s["id"] for s in result}) == len(result)
    for s in result:
        assert text[s["start"]:s["end"]] == s["text"]


def test_restoration_copies_exact_source_and_payload_hides_labels():
    case = suite()["cases"][0]
    payload = spans.judge_payload(case)
    assert set(payload) == {"question", "sentence", "evidence_spans"}
    result = spans.validate_decision(case, decision(case))
    anchor = result["propositions"][0]["evidence_spans"][0]
    assert case["evidence"][anchor["start"]:anchor["end"]] == anchor["text"]
    assert not result["complete_sentence_supported"]
    assert result["citation_support"]


@pytest.mark.parametrize("ids,category", [([], "evidence_span_ids_missing"), (["fake"], "evidence_span_id_unknown"),
                                        (["E001", "E001"], "evidence_span_ids_repeated")])
def test_missing_unknown_and_repeated_ids_are_rejected(ids, category):
    case = suite()["cases"][0]
    value = decision(case)
    value["propositions"][0]["evidence_span_ids"] = ids
    with pytest.raises(DiagnosticError) as error:
        spans.validate_decision(case, value)
    assert error.value.category == category


def test_multi_span_selection_is_restored_in_source_order():
    case = suite()["cases"][0]
    value = decision(case)
    ids = [s["id"] for s in case["source_spans"]]
    value["propositions"][0]["evidence_span_ids"] = ids[::-1]
    restored = spans.validate_decision(case, value)["propositions"][0]["evidence_spans"]
    assert [s["id"] for s in restored] == ids


def test_tampered_spans_fail_before_service_and_failed_attempt_is_retained(tmp_path):
    data = suite()
    data["cases"][0]["source_spans"][0]["text"] = "invented"
    calls = []
    result = spans.run_suite(data, tmp_path / "failed.json", model="test", judge_fn=lambda *a, **k: calls.append(1))
    assert not calls
    assert result["records"][0]["error_category"] == "source_spans_invalid"


def test_resume_retry_and_changed_signature(tmp_path):
    data = suite()
    output = tmp_path / "results.json"
    def bad(case, *, model):
        value = decision(case)
        value["propositions"][0]["evidence_span_ids"] = ["fake"]
        return value
    spans.run_suite(data, output, model="test", judge_fn=bad)
    result = spans.run_suite(data, output, model="test", retry_errors=True, judge_fn=lambda c, **k: decision(c))
    assert len(result["records"]) == 2
    assert result["summary"]["citation_agreement"]["scored"] == 1
    spans.run_suite(data, output, model="test", judge_fn=lambda *a, **k: pytest.fail("Repeated call"))
    with pytest.raises(ValueError, match="different"):
        spans.run_suite(data, output, model="changed")


def test_ambiguous_and_heldout_cases_cannot_be_run(tmp_path):
    data = suite()
    data["cases"][0]["reference_status"] = "ambiguous"
    result = spans.run_suite(data, tmp_path / "out.json", model="test", judge_fn=lambda *a, **k: pytest.fail("Ambiguous call"))
    assert not result["records"]
    data["cases"][0]["question_id"] = "held"
    with pytest.raises(ValueError, match="development"):
        spans.run_suite(data, tmp_path / "held.json", model="test")
