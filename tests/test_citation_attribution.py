from copy import deepcopy

import pytest

from evaluation import citation_attribution as experiment
from evaluation import calibrate_verifier as original


def decision(**updates):
    value = dict(relation='supports', supported_assertion='Process A reduced waiting time.',
                 evidence_quote='Process A reduced waiting time.', contradiction_quotes=[],
                 reason='Delay is supported; energy use is unestablished.')
    value.update(updates)
    return value


def test_partial_support_is_not_whole_sentence_coverage():
    case = experiment.fixtures()[0]
    assert experiment.validate_decision(decision(), case)['supports_sentence'] is True


def test_invalid_evidence_is_a_failure_not_a_negative_label():
    with pytest.raises(experiment.DecisionValidationError, match='quote_not_in_document'):
        experiment.validate_decision(decision(evidence_quote='Invented result.'), experiment.fixtures()[0])


def test_contradiction_cannot_coexist_with_support_label():
    case = experiment.fixtures()[1]
    with pytest.raises(experiment.DecisionValidationError, match='support_with_contradiction'):
        experiment.validate_decision(decision(evidence_quote='Process B reduced waiting time',
            contradiction_quotes=['energy use increased rather than decreased.']), case)


def test_contradiction_is_negative_even_when_another_claim_supported():
    case = experiment.fixtures()[1]
    result = decision(relation='contradicts', supported_assertion='', evidence_quote='',
        contradiction_quotes=['energy use increased rather than decreased.'])
    assert experiment.validate_decision(result, case)['supports_sentence'] is False


def test_payload_contains_no_reference_or_whole_support_sidecar():
    case = experiment.fixtures()[0]
    case.update(reference_support=True, whole_sentence_support=False)
    payload = original.judge_payload(case)
    assert set(payload) == {'question', 'sentence', 'evidence'}


def test_failed_response_keeps_sanitized_failure_code():
    def invalid(case, model):
        raise experiment.DecisionValidationError('missing_support_witness')
    result = experiment.attempt(invalid, {})
    assert result['status'] == 'error'
    assert result['failure_code'] == 'missing_support_witness'
    assert 'supports_sentence' not in result


def test_resume_does_not_repeat_completed_or_failed_arms(tmp_path, monkeypatch):
    case = experiment.fixtures()[0]
    monkeypatch.setattr(experiment, 'PATH', tmp_path/'run.json')
    state = dict(reviewed=[dict(case_id=case['case_id'], arms=dict(
        baseline={'status': 'error'}, revised={'status': 'ok', 'supports_sentence': True}))])
    before = deepcopy(state)
    def unwanted(*args, **kwargs):
        raise AssertionError('must not repeat a saved attempt')
    monkeypatch.setattr(original, 'judge', unwanted)
    monkeypatch.setattr(experiment, 'judge', unwanted)
    assert experiment.run_phase(state, [case], 'reviewed')
    assert state == before
