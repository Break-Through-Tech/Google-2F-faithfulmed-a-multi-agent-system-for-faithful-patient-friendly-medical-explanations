from copy import deepcopy
import pytest
from evaluation import original_judge_heldout as held
from evaluation.scoring import digest

def source_and_data():
    case=dict(case_id='case1',question_id='held',question='Question?',sentence='An assertion.',
        cited_pmid='123',evidence='Original snippet',reference_relation='supporting',reference_support=True)
    source=dict(dataset_sha256='fixture',question_groups=dict(development=['dev'],heldout=['held']),
        splits=dict(development=[],heldout=[case]))
    data=[dict(question_id='held',machine_generated_answers=dict(M=dict(answer_sentences=[dict(
        answer_sentence_id='s1',answer_sentence='An assertion.',citation_assessment=[dict(
            cited_pmid='123',evidence_relation='supporting',evidence_support='A source excerpt')])])))]
    return source,data

def test_reference_conflict_quarantined_before_any_prediction():
    source,data=source_and_data();before=deepcopy(source)
    extra=deepcopy(data[0]['machine_generated_answers']['M'])
    extra['answer_sentences'][0]['citation_assessment'][0]['evidence_relation']='neutral'
    data[0]['machine_generated_answers']['other']=extra
    result=held.select(source,data)
    assert result['records'][0]['reference_status']=='ambiguous'
    assert result['records'][0]['case']['reference_support'] is True
    assert source==before
    assert result['predictions_used_for_selection'] is False

def test_question_overlap_and_mismatched_reference_rejected():
    source,data=source_and_data()
    source['question_groups']['development']=['held']
    with pytest.raises(ValueError,match='overlap'):held.select(source,data)
    source['question_groups']['development']=['dev']
    data[0]['machine_generated_answers']['M']['answer_sentences'][0]['citation_assessment'][0]['evidence_relation']='neutral'
    with pytest.raises(ValueError,match='mapping'):held.select(source,data)

def test_no_snippet_fallback_on_missing_abstract(tmp_path,monkeypatch):
    source,data=source_and_data();selection=held.select(source,data)
    monkeypatch.setattr(held,'SUITE',tmp_path/'suite.json')
    cache=dict(selection_digest=digest(selection),records={'123':dict(pmid='123',title='Title',abstract='')})
    prepared=held.prepare(selection,cache)
    assert prepared['splits']['heldout']==[]
    assert prepared['source_unavailable_case_ids']==['case1']

def test_wrong_source_hash_is_rejected_before_output(tmp_path,monkeypatch):
    source,data=source_and_data();selection=held.select(source,data)
    monkeypatch.setattr(held,'SUITE',tmp_path/'suite.json')
    cache=dict(selection_digest=digest(selection),records={'123':dict(pmid='123',title='Title',abstract='Abstract',context_sha256='corrupt')})
    with pytest.raises(ValueError,match='hash'):held.prepare(selection,cache)
    assert not held.SUITE.exists()
