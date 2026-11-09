import copy

import pytest

from evaluation.clinical_scoring_v2 import (ScoringFailure, blocks, metrics, prepare, resolve)
from evaluation.score_outputs import advisor_jobs


def anchored_reference(job):
    _, registry, output=prepare(job)
    def ids_for_quote(quote, text, spans):
        start=text.index(quote);end=start+len(quote)
        return [b['id'] for b in spans if b['end']>start and b['start']<end]
    claims=[];used=set()
    for original in job['reference_assessment']['claims']:
        c={k:v for k,v in original.items() if k not in ('output_quote','evidence')}
        c['output_span_ids']=ids_for_quote(original['output_quote'],job['output'],output.values())
        used.update(c['output_span_ids']);c['evidence_span_ids']=[]
        for e in original['evidence']:
            text=job['source_report'] if e['origin']=='report' else next(p['text'] for p in job['retrieved_context'] if p['id']==e['context_id'])
            spans=[b for b in registry.values() if b['origin']==e['origin'] and b['context_id']==e['context_id']]
            c['evidence_span_ids'].extend(ids_for_quote(e['quote'],text,spans))
        c['evidence_span_ids']=list(dict.fromkeys(c['evidence_span_ids']))
        claims.append(c)
    coverage=[{**f,'missing_detail':f['reason'] if f['status']=='missing' else ''}
              for f in job['reference_assessment']['key_fact_coverage']]
    return dict(claims=claims,key_fact_coverage=coverage,
                ignored_output_span_ids=list(set(output)-used))


@pytest.mark.parametrize('index',range(4))
def test_advisor_counts_and_exact_restored_quotes(index):
    job=advisor_jobs()[index];decision=resolve(job,anchored_reference(job));result=metrics(decision)
    from evaluation.score_outputs import EXAMPLES
    import json
    expected=json.loads(EXAMPLES.read_text(encoding='utf-8'))['examples'][index]['expected_counts']
    for k,v in expected.items():assert result[k]==v
    for claim in decision['claims']:
        assert claim['output_quote'] in job['output']
        for e in claim['evidence']:
            text=job['source_report'] if e['origin']=='report' else next(p['text'] for p in job['retrieved_context'] if p['id']==e['context_id'])
            assert e['quote'] in text


@pytest.mark.parametrize('text',['Dose 1.5 mg. Next sentence.','**Dose:** 5 mg\n\nNew line.','Unicode \u03ba, \u00b1, \u00a0text.\r\nNext.','No punctuation'])
def test_blocks_are_lossless_with_exact_offsets(text):
    spans=blocks(text,'R')
    assert ''.join(b['text'] for b in spans)==text
    assert all(text[b['start']:b['end']]==b['text'] for b in spans)


def test_unknown_anchor_cannot_become_supported_evidence():
    job=advisor_jobs()[0];decision=anchored_reference(job)
    decision['claims'][0]['evidence_span_ids']=['R99999']
    with pytest.raises(ScoringFailure,match='evidence_anchor_invalid'):resolve(job,decision)


def test_invented_quote_field_is_rejected_by_schema():
    job=advisor_jobs()[0];decision=anchored_reference(job)
    decision['claims'][0]['output_quote']='Invented paraphrase.'
    with pytest.raises(ScoringFailure,match='schema_invalid'):resolve(job,decision)


def test_unaccounted_output_block_is_not_silently_dropped():
    job=advisor_jobs()[0];job['output']+='\nAn invented additional plan.'
    decision=anchored_reference(job)
    decision['ignored_output_span_ids']=[]
    with pytest.raises(ScoringFailure,match='output_blocks_unaccounted'):resolve(job,decision)


def test_partial_fact_is_distinct_from_whole_omission():
    job=advisor_jobs()[1];decision=anchored_reference(job)
    f=decision['key_fact_coverage'][0];f.update(status='partial',missing_detail='One required qualification is absent.')
    result=metrics(resolve(job,decision))
    assert result['partial_key_facts']==1
    assert result['omissions']==1  # Existing missing follow-up remains a separate fact.
    assert result['incomplete_key_facts']==2
    f['missing_detail']=''
    with pytest.raises(ScoringFailure,match='partial_fact_needs_missing_detail'):resolve(job,decision)


def test_context_only_evidence_cannot_establish_patient_claim():
    job=advisor_jobs()[0];decision=anchored_reference(job)
    decision['claims'][-1]['scope']='patient'
    with pytest.raises(ScoringFailure,match='patient_support_requires_report'):resolve(job,decision)


def test_supported_background_is_still_an_addition():
    job=advisor_jobs()[0];decision=anchored_reference(job)
    decision['claims'][-1]['is_addition']=False
    with pytest.raises(ScoringFailure,match='background_must_be_addition'):resolve(job,decision)


def test_reference_labels_are_not_model_inputs():
    job=advisor_jobs()[0];payload,_,_=prepare(job)
    assert set(payload)=={'source_blocks','output_blocks','context_blocks','key_facts'}
    assert 'reference_assessment' not in payload


def test_duplicate_proposition_cannot_inflate_claim_count():
    job=advisor_jobs()[0];decision=anchored_reference(job)
    duplicate=copy.deepcopy(decision['claims'][0]);duplicate['id']='extra';decision['claims'].append(duplicate)
    with pytest.raises(ScoringFailure,match='duplicate_or_empty_claim'):resolve(job,decision)


def test_one_consistency_correction_preserves_initial_attempt_without_reference_labels():
    import json
    from unittest.mock import patch
    from evaluation.clinical_scoring_v2 import assess
    job=advisor_jobs()[0];good=anchored_reference(job);bad=copy.deepcopy(good)
    bad['claims'][-1]['is_addition']=False
    fix={'corrections':[{'claim_id':bad['claims'][-1]['id'],'is_addition':True,'report_span_ids':[],
                         'reason':'The specific background fact is absent from the report.'}]}
    with patch('faithfulmed_demo.config.model_client'), patch('evaluation.clinical_scoring_v2.generate_text',side_effect=[json.dumps(bad),json.dumps(fix)]) as request:
        result=assess(job,'fixture')
    assert len(result['attempts'])==2
    assert result['attempts'][0]['error_category']=='context_only_background_must_be_addition'
    assert result['attempts'][1]['status']=='valid'
    sent=request.call_args_list[1].args[2]
    assert 'reference_assessment' not in sent
    assert sent['claims_to_check'][0]['id']==bad['claims'][-1]['id']
    assert result['attempts'][1]['addition_corrections'][0]['is_addition'] is True


def test_two_invalid_attempts_stop_and_keep_safe_diagnostics():
    import json
    from unittest.mock import patch
    from evaluation.clinical_scoring_v2 import assess
    job=advisor_jobs()[0];bad=anchored_reference(job);bad['claims'][0]['evidence_span_ids']=['not-real']
    with patch('faithfulmed_demo.config.model_client'),patch('evaluation.clinical_scoring_v2.generate_text',return_value=json.dumps(bad)) as request:
        with pytest.raises(ScoringFailure) as caught:assess(job,'fixture')
    assert request.call_count==2
    assert len(caught.value.attempts)==2


def test_transient_disconnect_retries_once_without_pretending_it_is_a_judgment():
    import json
    import httpx
    from unittest.mock import patch
    from evaluation.clinical_scoring_v2 import assess
    job=advisor_jobs()[0]
    with patch('faithfulmed_demo.config.model_client'),patch('evaluation.clinical_scoring_v2.generate_text',side_effect=[httpx.RemoteProtocolError('private request'),json.dumps(anchored_reference(job))]) as request:
        result=assess(job,'fixture')
    assert result['attempts'][0]['status']=='service_error'
    assert 'private request' not in json.dumps(result)
    sent=request.call_args_list[1].args[2]
    assert 'validation_feedback' not in sent


def test_streaming_preserves_text_ignores_thoughts_and_requires_complete_finish():
    from types import SimpleNamespace as N
    from unittest.mock import MagicMock
    from evaluation.clinical_scoring_v2 import generate_text
    def chunk(text,finish=None,thought=False):
        return N(candidates=[N(content=N(parts=[N(text=text,thought=thought)]),finish_reason=finish)])
    client=MagicMock();client.models.generate_content_stream.return_value=[chunk('private reasoning',thought=True),chunk('{"claims":'),chunk('[]}',finish='STOP')]
    assert generate_text(client,'fixture',{})=='{"claims":[]}'
    assert client.models.generate_content_stream.call_args.kwargs['config'].http_options.timeout==180000
    client.models.generate_content_stream.return_value=[chunk('partial',finish='MAX_TOKENS')]
    with pytest.raises(ScoringFailure,match='response_incomplete'):generate_text(client,'fixture',{})


def test_valid_initial_result_is_revalidated_and_reused(tmp_path):
    from unittest.mock import patch
    from evaluation.clinical_scoring_v2 import run
    job=advisor_jobs()[0];answer=resolve(job,anchored_reference(job))
    with patch('evaluation.clinical_scoring_v2.assess',return_value=answer):
        initial=run([job],tmp_path/'first.json','fixture')
    with patch('evaluation.clinical_scoring_v2.assess') as model:
        result=run([job],tmp_path/'next.json','fixture',initial)
        model.assert_not_called()
    assert result['records'][0]['reused_previous_valid_assessment'] is True


def test_report_presence_correction_can_preserve_nonaddition_with_real_report_evidence():
    import json
    from unittest.mock import patch
    from evaluation.clinical_scoring_v2 import correct_addition_links
    job=advisor_jobs()[0];background=job['retrieved_context'][0]['text']
    job['source_report']+=' '+background
    raw=anchored_reference(job);raw['claims'][-1]['is_addition']=False
    _,registry,_=prepare(job)
    ids=[i for i,b in registry.items() if b['origin']=='report' and background in b['text']]
    assert ids
    fix={'corrections':[{'claim_id':raw['claims'][-1]['id'],'is_addition':False,'report_span_ids':ids,'reason':'This fact is explicitly in the report too.'}]}
    with patch('evaluation.clinical_scoring_v2.generate_text',return_value=json.dumps(fix)):
        updated,_=correct_addition_links(None,'fixture',job,raw)
    result=resolve(job,updated)
    assert result['claims'][-1]['is_addition'] is False
    assert any(e['origin']=='report' for e in result['claims'][-1]['evidence'])


def test_compact_correction_cannot_change_unrequested_claims_or_use_fake_report_ids():
    import json
    from unittest.mock import patch
    from evaluation.clinical_scoring_v2 import correct_addition_links
    job=advisor_jobs()[0];raw=anchored_reference(job);raw['claims'][-1]['is_addition']=False
    fix={'corrections':[{'claim_id':'not-requested','is_addition':True,'report_span_ids':[],'reason':'Wrong claim.'}]}
    with patch('evaluation.clinical_scoring_v2.generate_text',return_value=json.dumps(fix)),pytest.raises(ScoringFailure,match='inventory_invalid'):
        correct_addition_links(None,'fixture',job,raw)
    fix['corrections'][0].update(claim_id=raw['claims'][-1]['id'],is_addition=False,report_span_ids=['R99999'])
    with patch('evaluation.clinical_scoring_v2.generate_text',return_value=json.dumps(fix)),pytest.raises(ScoringFailure,match='report_anchor_invalid'):
        correct_addition_links(None,'fixture',job,raw)


def test_saved_run_resumes_without_repeating_calls_and_rejects_changed_inputs(tmp_path):
    from unittest.mock import patch
    from evaluation.clinical_scoring_v2 import run
    job=advisor_jobs()[0];answer=resolve(job,anchored_reference(job));path=tmp_path/'scores.json'
    with patch('evaluation.clinical_scoring_v2.assess',return_value=answer) as model:
        run([job],path,'fixture');run([job],path,'fixture')
        assert model.call_count==1
        changed=copy.deepcopy(job);changed['output']+=' Changed.'
        with pytest.raises(ValueError,match='Changed scorer or inputs'):run([changed],path,'fixture')


def test_failed_assessment_is_saved_without_faithfulness_score(tmp_path):
    from unittest.mock import patch
    from evaluation.clinical_scoring_v2 import run
    with patch('evaluation.clinical_scoring_v2.assess',side_effect=ScoringFailure('evidence_anchor_invalid')):
        result=run([advisor_jobs()[0]],tmp_path/'failed.json','fixture')
    assert result['records'][0]['status']=='evaluation_failed'
    assert result['records'][0]['error_category']=='evidence_anchor_invalid'
    assert 'metrics' not in result['records'][0]
    assert result['summary_by_system'][0]['faithfulness_micro'] is None


def test_drafts_and_failed_generations_stay_outside_released_summary(tmp_path):
    from unittest.mock import patch
    from evaluation.clinical_scoring_v2 import run
    draft=advisor_jobs()[0];answer=resolve(draft,anchored_reference(draft));draft['output_kind']='draft'
    failed=copy.deepcopy(draft);failed.update(system='failed_system',output_kind='final',run_status='failed',output='')
    with patch('evaluation.clinical_scoring_v2.assess',return_value=answer) as model:
        result=run([draft,failed],tmp_path/'mixed.json','fixture')
        assert model.call_count==1
    assert result['records'][1]['status']=='generation_failed'
    assert result['summary_by_system'][0]['scored_drafts']==1
    assert all(s['scored_final_outputs']==0 for s in result['summary_by_system'])
