from copy import deepcopy
import json
from unittest.mock import MagicMock, patch

import pytest

from evaluation import citation_attribution as strict
from evaluation import citation_quote_validation as repaired


def decision(quote,**updates):
    value=dict(relation='supports',supported_assertion='A complete claim.',evidence_quote=quote,
               contradiction_quotes=[],reason='Original model reasoning.')
    value.update(updates)
    return value


@pytest.mark.parametrize('source,quote',[
    ('Result.\nCONCLUSION: The result was unchanged.','Result. CONCLUSION: The result was unchanged.'),
    ('The dose is\t5 mg\r\ndaily.','The dose is 5 mg daily.'),
    ('One\u00a0space.','One space.'),
    ('A report sentence.','  A report sentence.\n'),
])
def test_whitespace_recovery_restores_exact_source_offsets(source,quote):
    result=repaired.recover_quote(quote,source)
    assert result['source_quote']==source[result['start']:result['end']]
    assert result['match_kind']=='whitespace_only'
    assert result['supplied_quote']==quote


def test_unique_exact_quote_keeps_its_original_text():
    result=repaired.recover_quote('Dose: 5 mg.','Context. Dose: 5 mg. Follow-up.')
    assert result['match_kind']=='exact'
    assert result['start']==9


@pytest.mark.parametrize('source,quote',[
    ('The test found no cancer.','The test found cancer.'),
    ('The dose is 15 mg daily.','The dose is 5 mg daily.'),
    ('Possible cancer.','Definite cancer.'),
    ('Left kidney.','Right kidney.'),
    ('The intervention may help.','The intervention will help.'),
    ('No improvement occurred.','No improvement occured.'),
    ('A was measured. A different result. B was measured.','A was measured. ... B was measured.'),
    ('A\nqualifier B.','A B.'),
    ('Original result.','original result.'),
    ('Five-mg dose.','Five mg dose.'),
])
def test_content_changes_are_not_whitespace_repairs(source,quote):
    with pytest.raises(strict.DecisionValidationError):
        repaired.recover_quote(quote,source)


@pytest.mark.parametrize('source',[
    'A result.\nA result.',
    'A\nresult. A result.',
])
def test_ambiguous_locations_are_rejected_even_if_one_match_is_exact(source):
    with pytest.raises(strict.DecisionValidationError,match='ambiguous_quote_location'):
        repaired.recover_quote('A result.',source)


@pytest.mark.parametrize('source,quote',[
    ('Dose 15 mg daily.','5 mg daily.'),
    ('Dose 0.5 mg daily.','5 mg daily.'),
    ('Dose -5 mg daily.','5 mg daily.'),
    ('These cells changed.','cells change'),
])
def test_token_and_number_fragments_cannot_manufacture_a_match(source,quote):
    with pytest.raises(strict.DecisionValidationError):
        repaired.recover_quote(quote,source)


def test_original_decision_and_input_are_preserved():
    supplied=decision('The result. Conclusion: unchanged.')
    before=deepcopy(supplied)
    result=repaired.validate_decision(supplied,{'evidence':'The result.\nConclusion: unchanged.'})
    assert supplied==before
    assert result['relation']==supplied['relation']
    assert result['reason']==supplied['reason']
    assert result['supported_assertion']==supplied['supported_assertion']
    assert result['supports_sentence'] is True
    assert result['evidence_quote']=='The result.\nConclusion: unchanged.'
    assert result['quote_locations'][0]['supplied_quote']==supplied['evidence_quote']


def test_contradiction_quotes_are_restored_without_becoming_support():
    result=repaired.validate_decision(decision('',relation='contradicts',supported_assertion='',
        contradiction_quotes=['No effect. Conclusion: failed.']),
        {'evidence':'No effect.\nConclusion: failed.'})
    assert result['supports_sentence'] is False
    assert result['contradiction_quotes']==['No effect.\nConclusion: failed.']


def test_whitespace_repair_cannot_bypass_contradiction_consistency_check():
    with pytest.raises(strict.DecisionValidationError,match='support_with_contradiction'):
        repaired.validate_decision(decision('A helped. Conclusion: B failed.',
            contradiction_quotes=['B failed.']),{'evidence':'A helped.\nConclusion: B failed.'})


def test_old_validator_still_rejects_whitespace_mismatch():
    with pytest.raises(strict.DecisionValidationError,match='quote_not_in_document'):
        strict.validate_decision(decision('A result. Conclusion: unchanged.'),
                                 {'evidence':'A result.\nConclusion: unchanged.'})


def test_future_judge_uses_recovery_without_changing_the_model_prompt():
    raw=json.dumps(decision('A result. Conclusion: unchanged.'))
    captured=[]
    client=MagicMock()
    with patch('faithfulmed_demo.config.model_client',return_value=client), \
         patch('faithfulmed_demo.config.require_text',return_value=raw):
        result=repaired.judge({'question':'Question?', 'sentence':'A claim.',
                              'evidence':'A result.\nConclusion: unchanged.'},
                              record_response=captured.append)
    assert captured==[raw]
    assert result['evidence_quote']=='A result.\nConclusion: unchanged.'
    config=client.__enter__.return_value.models.generate_content.call_args.kwargs['config']
    assert config.system_instruction==strict.PROMPT
    assert config.temperature==0
    assert config.http_options.retry_options.attempts==1
