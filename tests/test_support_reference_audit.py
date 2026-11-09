"""Offline policy regressions: conflicts cannot disappear with missing snippets."""

from evaluation.audit_support_references import audit, identity
from evaluation.scoring import digest


def fixture(relations):
    citations = [dict(cited_pmid="123", evidence_relation=r, evidence_support=e) for r, e in relations]
    dataset = [dict(question_id=1, machine_generated_answers={"model": dict(answer_sentences=[
        dict(answer_sentence="A 1.5 cm lesion [1].", answer_sentence_id=1, citation_assessment=citations)])})]
    case = dict(case_id="a", question_id=1, cited_pmid="123", sentence="A 1.5 cm lesion [1].", reference_relation="supporting")
    suite = {"splits": {"development": [case], "heldout": []}}
    return dataset, suite


def test_missing_snippet_does_not_hide_opposite_document_reference():
    dataset, suite = fixture([("supporting", "evidence"), ("not relevant", "")])
    result = audit(dataset, suite, {})
    assert result["cases"][0]["binary_conflict"]
    assert result["cases"][0]["relation_counts"] == {"supporting": 1, "not relevant": 1}


def test_identity_preserves_decimal_and_negation():
    assert identity(1, 123, "A 1.5 cm lesion [1].") != identity(1, 123, "A 15 cm lesion.")
    assert identity(1, 123, "No lesion") != identity(1, 123, "Lesion")
    assert identity(1, 123, " A lesion [1] ") == identity(1, "123", "a lesion")


def test_duplicate_documents_are_flagged_and_invalid_cache_is_not_ready():
    dataset, suite = fixture([("supporting", "excerpt")])
    suite["splits"]["development"].append({**suite["splits"]["development"][0], "case_id": "b"})
    cache = {"records": {"123": dict(pmid="123", title="Title", abstract="Abstract", context_sha256="changed")}}
    result = audit(dataset, suite, cache)
    assert not result["cases"][0]["cached_context"]
    assert "duplicate_document_assertion" in result["cases"][1]["audit_flags"]
    cache["records"]["123"]["context_sha256"] = digest(["Title", "Abstract"])
    assert audit(dataset, suite, cache)["cases"][0]["cached_context"]


def test_false_relation_disagreement_is_not_binary_conflict():
    dataset, suite = fixture([("neutral", "e"), ("contradicting", "e")])
    result = audit(dataset, suite, {})["cases"][0]
    assert result["mixed_relations"] and not result["binary_conflict"]
    dataset, suite = fixture([("supporting", "e"), ("invalid citation", "")])
    assert "invalid_or_unmapped_reference" in audit(dataset, suite, {})["cases"][0]["audit_flags"]
