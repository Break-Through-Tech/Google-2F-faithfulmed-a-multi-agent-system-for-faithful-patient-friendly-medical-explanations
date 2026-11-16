"""Portable final evaluator checks; no network or ignored evaluation data needed."""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from evaluation import citation_evaluator as final
from evaluation.citation_attribution import DecisionValidationError
from evaluation.scoring import digest


def test_published_results_recompute_from_case_decisions_without_calls(monkeypatch):
    from faithfulmed_demo import config
    monkeypatch.setattr(config,'model_client',lambda:pytest.fail('Verification must be offline'))
    results=final.verify_results()
    retro=results['cohorts']['retrospective_31']
    assert retro['runs']['original']['summary']['post_retry']['correct']==23
    assert retro['runs']['improved']['summary']['post_retry']['correct']==25
    assert len(retro['original_comparison']['gains'])==2
    assert not retro['original_comparison']['losses']
    assert results['cohorts']['development_32']['runs']['improved']['summary']['post_retry']['correct']==26


def test_editing_summary_cannot_change_the_measured_score(tmp_path,monkeypatch):
    artifact=json.loads(final.read(final.RESULTS))
    artifact['results']['cohorts']['retrospective_31']['runs']['improved']['summary']['post_retry']['correct']=31
    artifact['fingerprint']=digest(artifact['results'])
    path=tmp_path/'results.json';path.write_text(json.dumps(artifact),encoding='utf-8')
    monkeypatch.setattr(final,'RESULTS',path)
    with pytest.raises(ValueError,match='do not match decisions'):
        final.verify_results()


def test_prompt_edits_are_detected(tmp_path,monkeypatch):
    artifact=json.loads(final.read(final.CONFIGURATION))
    artifact['specification']['prompt']+=' changed rule'
    artifact['fingerprint']=digest(artifact['specification'])
    path=tmp_path/'configuration.json';path.write_text(json.dumps(artifact),encoding='utf-8')
    monkeypatch.setattr(final,'CONFIGURATION',path)
    with pytest.raises(ValueError,match='prompt fingerprint'):
        final.configuration()


@pytest.mark.parametrize('quote,accepted',[
    ('Device R detects smoke.',True),
    ('Device R detects smoke. [...] Device R records temperature.',False),
    ('Device R detects fire.',False),
])
def test_final_request_is_locked_and_source_validation_stays_strict(monkeypatch,quote,accepted):
    from faithfulmed_demo import config
    text=json.dumps(dict(relation='supports',supported_assertion='Device R detects smoke.',
        evidence_quote=quote,contradiction_quotes=[],reason='This is stated in the source.'))
    response=SimpleNamespace(text=text,candidates=[SimpleNamespace(finish_reason='STOP')])
    client=MagicMock();client.models.generate_content.return_value=response
    context=MagicMock();context.__enter__.return_value=client
    monkeypatch.setattr(config,'model_client',lambda:context)
    case=dict(question='What does device R do?',sentence='Device R detects smoke and records temperature.',
        evidence='Device R detects smoke. It has a blue housing. Device R records temperature.',
        reference_support=False,reference_relation='neutral',private_metadata='not model input')
    captured=[]
    if accepted:
        assert final.judge(case,captured.append)['supports_sentence']
    else:
        with pytest.raises(DecisionValidationError,match='quote_not_in_document'):
            final.judge(case,captured.append)
    assert captured==[text]
    request=client.models.generate_content.call_args.kwargs
    assert json.loads(request['contents'])=={k:case[k] for k in ['question','sentence','evidence']}
    spec=final.configuration()['specification']
    assert request['model']==spec['model']
    assert request['config'].system_instruction==spec['prompt']
    assert request['config'].temperature==0
    assert request['config'].http_options.timeout==60000
    assert request['config'].http_options.retry_options.attempts==1


def test_valid_disagreements_and_access_errors_are_never_retried():
    assert not final.retry_allowed(dict(status='ok',supports_sentence=False),1)
    assert not final.retry_allowed(dict(status='error',service_code=429,failure_code='empty_quote'),1)
    assert final.retry_allowed(dict(status='error',failure_code='quote_not_in_document'),1)
    assert not final.retry_allowed(dict(status='error',failure_code='quote_not_in_document'),2)
