from copy import deepcopy

import pytest

from evaluation import citation_reliability as repeat


def cases():
    return [dict(case_id=str(i),question_id='q',cited_pmid=str(i),reference_support=True,
                 reference_relation='supporting') for i in range(3)]


def test_all_first_attempts_precede_uniform_technical_retries(tmp_path,monkeypatch):
    monkeypatch.setattr(repeat,'OUTPUT',tmp_path/'run.json')
    state=dict(records=[],phase='initial'); calls=[]
    def call(case,capture):
        calls.append(case['case_id']);capture('model text','STOP')
        if calls.count(case['case_id'])==1 and case['case_id']=='0':
            raise repeat.citation.DecisionValidationError('quote_not_in_document')
        return dict(supports_sentence=True,reason='reason')
    repeat.run_cases(state,cases(),call)
    assert calls==['0','1','2','0']
    assert state['records'][0]['attempts'][0]['raw_response']=='model text'
    scores=repeat.summarize(state,cases())
    assert scores['first_attempt']['failed_cases']==1
    assert scores['post_retry']['scored_cases']==3
    assert scores['recovered_cases']==1


def test_valid_wrong_decision_is_never_retried(tmp_path,monkeypatch):
    monkeypatch.setattr(repeat,'OUTPUT',tmp_path/'run.json')
    state=dict(records=[],phase='initial');calls=[]
    def call(case,capture):
        calls.append(case['case_id'])
        return dict(supports_sentence=False,reason='valid disagreement')
    repeat.run_cases(state,cases(),call)
    assert calls==['0','1','2']
    assert repeat.summarize(state,cases())['post_retry']['correct']==0


def test_failed_retry_is_not_repeated_on_resume(tmp_path,monkeypatch):
    monkeypatch.setattr(repeat,'OUTPUT',tmp_path/'run.json')
    state=dict(records=[],phase='initial');calls=[]
    def call(case,capture):
        calls.append(case['case_id'])
        raise repeat.citation.DecisionValidationError('schema_validation')
    repeat.run_cases(state,cases(),call)
    before=deepcopy(state)
    repeat.run_cases(state,cases(),call)
    assert calls==['0','1','2','0','1','2']
    assert state==before


def test_access_error_stops_run_without_retries(tmp_path,monkeypatch):
    monkeypatch.setattr(repeat,'OUTPUT',tmp_path/'run.json')
    state=dict(records=[],phase='initial')
    class AccessError(Exception):
        code=429
    def call(case,capture):raise AccessError()
    repeat.run_cases(state,cases(),call)
    assert len(state['records'])==1
    assert state['phase']=='stopped_access_or_quota'
    assert not repeat.retryable(state['records'][0]['attempts'][0])


def test_uncertain_interrupted_request_is_not_silently_repeated(tmp_path,monkeypatch):
    monkeypatch.setattr(repeat,'OUTPUT',tmp_path/'run.json')
    state=dict(records=[dict(case_id='0',attempts=[dict(status='started')])])
    with pytest.raises(ValueError,match='Uncertain interrupted'):
        repeat.run_cases(state,cases(),lambda *a:pytest.fail('no request expected'))


@pytest.mark.parametrize('record,expected',[
    ({'status':'ok','supports_sentence':False},False),
    ({'status':'error','service_code':503},True),
    ({'status':'error','service_code':403,'failure_code':'schema_validation'},False),
    ({'status':'error','failure_code':'schema_validation'},True),
    ({'status':'error','error_type':'ReadTimeout'},True),
    ({'status':'error','failure_code':'blocked_or_unfinished_response'},False),
    ({'status':'error','error_type':'UnexpectedFailure'},False),
])
def test_retry_policy_is_independent_of_reference_labels(record,expected):
    assert repeat.retryable(record) is expected
