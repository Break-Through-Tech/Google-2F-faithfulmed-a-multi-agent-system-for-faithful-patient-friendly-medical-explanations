"""Portable final citation evaluator and offline verification of published results."""
import argparse
import hashlib
import json
from pathlib import Path

from . import citation_attribution as base
from . import citation_quote_validation as validation
from .citation_reliability import summarize
from .freeze_citation_judge import retry_allowed as policy_retry_allowed
from .scoring import digest

ROOT=Path(__file__).resolve().parents[1]
CONFIGURATION=ROOT/'evaluation/frozen/citation_evaluator_final_2026-11-16.json'
RESULTS=ROOT/'evaluation/results/citation_evaluator_final_2026-11-16.json'
METRICS=('selected_cases','attempted_cases','scored_cases','failed_cases','pending_cases',
         'correct','agreement','cohen_kappa','reference_support_counts','confusion_counts',
         'agreement_wilson_95','complete','targets_met_on_scored_cases')


def read(path):
    return Path(path).read_text(encoding='utf-8')


def configuration():
    artifact=json.loads(read(CONFIGURATION))
    spec=artifact['specification']
    if digest(spec)!=artifact['fingerprint']:
        raise ValueError('Final evaluator manifest fingerprint mismatch')
    if spec['schema']!=base.Attribution.model_json_schema():
        raise ValueError('Final evaluator schema drift')
    if spec['prompt_sha256']!=digest(spec['prompt']):
        raise ValueError('Final evaluator prompt fingerprint mismatch')
    for name,expected in spec['source_sha256'].items():
        actual=hashlib.sha256(read(ROOT/name).encode('utf-8')).hexdigest()
        if actual!=expected:
            raise ValueError('Final evaluator dependency drift: '+name)
    return artifact


def judge(case,record_response=None):
    """One request, no automatic retry. Only question/sentence/evidence reach Gemini.

    Callers should freeze their batch, save every attempt, and use retry_allowed
    after all first attempts. This function does not change the live Verifier.
    """
    from google.genai import types
    from faithfulmed_demo.config import model_client,require_text
    spec=configuration()['specification']
    with model_client() as client:
        response=client.models.generate_content(model=spec['model'],
            contents=json.dumps(base.original.judge_payload(case)),
            config=types.GenerateContentConfig(system_instruction=spec['prompt'],
                temperature=spec['temperature'],response_mime_type='application/json',
                response_schema=base.Attribution,
                http_options=types.HttpOptions(timeout=spec['timeout_ms'],
                    retry_options=types.HttpRetryOptions(attempts=spec['sdk_attempts']))))
    if record_response is not None:
        record_response(response.text or '')
    text=require_text(response)
    return validation.validate_decision(base.Attribution.model_validate_json(text),case)


def retry_allowed(attempt,attempts_used):
    return policy_retry_allowed(attempt,attempts_used,configuration()['specification']['retry_policy'])


def compact_summary(state,cases):
    full=summarize(state,cases)
    return {**{key:{k:full[key][k] for k in METRICS} for key in ['first_attempt','post_retry']},
            **{k:full[k] for k in ['logical_calls','retried_cases','recovered_cases']}}


def changes(left,right,cases):
    def selected(state):
        return {r['case_id']:next((a for a in r['attempts'] if a['status']=='ok'),r['attempts'][-1])
                for r in state['records']}
    a,b=selected(left),selected(right)
    gains=[];losses=[];shared=[]
    for c in cases:
        key=c['case_id']
        if a.get(key,{}).get('status')!='ok' or b.get(key,{}).get('status')!='ok': continue
        shared.append(key)
        old=a[key]['supports_sentence']==c['reference_support']
        new=b[key]['supports_sentence']==c['reference_support']
        if new and not old: gains.append(key)
        if old and not new: losses.append(key)
    return dict(shared_valid_case_ids=shared,gains=gains,losses=losses)


def verify_results():
    config=configuration()
    artifact=json.loads(read(RESULTS));results=artifact['results']
    if artifact['fingerprint']!=digest(results):
        raise ValueError('Published results fingerprint mismatch')
    if results['configuration_fingerprint']!=config['fingerprint']:
        raise ValueError('Results use another final evaluator')
    for cohort in results['cohorts'].values():
        cases=cohort['cases'];ids={c['case_id'] for c in cases}
        if len(ids)!=len(cases): raise ValueError('Duplicate published case ID')
        for run in cohort['runs'].values():
            rows=run['records']
            if len(rows)!=len(ids) or {r['case_id'] for r in rows}!=ids:
                raise ValueError('Published run is missing cases or contains duplicates')
            if compact_summary(run,cases)!=run['summary']:
                raise ValueError('Published counts/agreement/kappa do not match decisions')
        expected=changes(cohort['runs']['original'],cohort['runs']['improved'],cases)
        if expected!=cohort['original_comparison']:
            raise ValueError('Published gains/losses do not match decisions')
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['verify'])
    parser.parse_args()
    results=verify_results()
    for name,cohort in results['cohorts'].items():
        s=cohort['runs']['improved']['summary']['post_retry']
        print(name,f"{s['correct']}/{s['scored_cases']}",
              f"agreement={s['agreement']:.4%}",f"kappa={s['cohen_kappa']:.6f}",
              f"failures={s['failed_cases']}")
    print('Final configuration and all published case-level metrics verified. No API calls.')


if __name__=='__main__': main()
