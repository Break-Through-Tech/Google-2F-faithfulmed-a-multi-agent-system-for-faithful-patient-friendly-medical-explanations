"""Freeze and verify the citation-only evaluator; never starts an API run."""
import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from . import citation_quote_validation as evaluator
from . import citation_reliability as reliability
from .scoring import digest

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'citation-judge-frozen-2026-11-15-v1'
MANIFEST = ROOT/'evaluation/frozen/citation_judge_2026-11-15_v1.json'
SOURCE_FILES = (
    'evaluation/citation_quote_validation.py',
    'evaluation/citation_attribution.py',
    'evaluation/calibrate_verifier.py',
    'evaluation/original_judge_heldout.py',
    'evaluation/citation_reliability.py',
    'evaluation/scoring.py',
    'evaluation/score_outputs.py',
    'faithfulmed_demo/config.py',
    'evaluation/freeze_citation_judge.py',
)


def source_snapshot(root=ROOT):
    result = {}
    for name in SOURCE_FILES:
        # Canonical line endings make the source check portable across Git's
        # Windows CRLF / Unix LF checkouts without ignoring code changes.
        text = (root/name).read_text(encoding='utf-8')
        result[name] = dict(sha256=hashlib.sha256(text.encode('utf-8')).hexdigest(),
                            utf8_source=text)
    return result


def current_specification():
    return dict(version=VERSION, scope='single-document citation support only',
        entry_point='evaluation.freeze_citation_judge.judge',
        model=evaluator.strict.MODEL, temperature=0, response_mime_type='application/json',
        prompt=evaluator.strict.PROMPT, prompt_sha256=digest(evaluator.strict.PROMPT),
        response_schema=evaluator.strict.Attribution.model_json_schema(),
        payload_fields=['question','sentence','evidence'],
        evidence_input='PMID-matched cached title and full available abstract; no snippet fallback',
        reference_labels_sent_to_model=False,
        positive_relation='supports', negative_relations=['contradicts','neutral','not_relevant'],
        citation_policy='One complete substantive supported claim is sufficient unless an asserted claim is contradicted; no whole-sentence coverage requirement.',
        quote_validation=dict(version=evaluator.VERSION, unique_contiguous_span=True,
            whitespace_only_recovery=True, restore_exact_source_text=True, record_offsets=True,
            reject_content_changes=True, reject_token_fragments=True, reject_ambiguous_locations=True),
        retry_policy=dict(max_attempts_per_case=2, sdk_attempts=1, timeout_ms=60000,
            phase_order='all first attempts before eligible second attempts',
            retryable_failure_codes=sorted(reliability.RETRYABLE_FAILURES |
                {'empty_quote','ambiguous_quote_location','quote_splits_token'}),
            transient_http_codes=sorted(reliability.TRANSIENT_CODES),
            transient_error_types=sorted(reliability.TRANSIENT_TYPES),
            stop_http_codes=sorted(reliability.ACCESS_CODES),
            retry_valid_disagreements=False, retry_prompt='identical, no correction feedback',
            selection='first valid attempt; otherwise retain the technical failure',
            interrupted_attempt='stop; no automatic repeat of an uncertain in-flight request'),
        reporting=dict(agreement_target=.8,kappa_target=.6,
            report_first_and_post_retry_separately=True, report_valid_and_all_attempt_denominators=True,
            retain_every_response_and_failure=True, do_not_impute_failed_predictions=True),
        dataset_binding=dict(status='not_selected', required_before_calls=True,
            freeze_case_ids_sources_labels_exclusions_and_hashes=True,
            exclude_development_exposure_and_duplicates_before_predictions=True,
            never_replace_cases_based_on_model_outputs=True),
        runtime=dict(python=platform.python_version(),google_genai=version('google-genai'),
                     pydantic=version('pydantic')),
        source_hash_normalization='UTF-8 text with universal newlines', sources=source_snapshot())


def verify_manifest(manifest, current):
    if manifest['fingerprint'] != digest(manifest['specification']):
        raise ValueError('Frozen manifest was edited or corrupted')
    if digest(current) != manifest['fingerprint']:
        raise ValueError('Evaluator configuration/code/runtime drift; use a new freeze version')
    return manifest


def freeze():
    current = current_specification()
    if MANIFEST.exists():
        return verify_manifest(json.loads(MANIFEST.read_text(encoding='utf-8')),current)
    manifest = dict(frozen_utc=datetime.now(timezone.utc).isoformat(),
                    fingerprint=digest(current),specification=current)
    MANIFEST.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive creation prevents silently replacing a previous freeze.
    with MANIFEST.open('x',encoding='utf-8',newline='\n') as handle:
        json.dump(manifest,handle,ensure_ascii=False,indent=2)
        handle.write('\n')
    return manifest


def verify():
    if not MANIFEST.exists():
        raise ValueError('Freeze the configuration before using this entry point')
    return verify_manifest(json.loads(MANIFEST.read_text(encoding='utf-8')),
                           current_specification())


def retry_allowed(attempt, attempts_used, policy):
    """Reference labels and agreement never enter a retry decision."""
    if attempts_used >= policy['max_attempts_per_case'] or attempts_used < 1:
        return False
    if attempt.get('status') != 'error' or attempt.get('service_code') in policy['stop_http_codes']:
        return False
    return (attempt.get('failure_code') in policy['retryable_failure_codes']
            or attempt.get('service_code') in policy['transient_http_codes']
            or attempt.get('error_type') in policy['transient_error_types'])


def verify_cohort(case, cohort, configuration_fingerprint):
    """Bind a future sample before calls; sampling independence still needs audit."""
    if not cohort or not isinstance(cohort.get('specification'),dict):
        raise ValueError('Freeze the evaluation cohort before making model calls')
    spec=cohort['specification']
    if cohort.get('fingerprint') != digest(spec):
        raise ValueError('Cohort manifest was edited or corrupted')
    if spec.get('configuration_fingerprint') != configuration_fingerprint:
        raise ValueError('Cohort is bound to another evaluator configuration')
    if not spec.get('sampling_policy') or not spec.get('exclusions_sha256'):
        raise ValueError('Cohort needs its sampling policy and exclusions audit')
    expected=spec.get('case_records',{}).get(case.get('case_id'))
    actual=dict(payload_sha256=digest(evaluator.strict.original.judge_payload(case)),
        reference_sha256=digest({key:case[key] for key in ['reference_relation','reference_support']}))
    if expected != actual:
        raise ValueError('Case inputs or reference labels differ from the frozen cohort')


def judge(case, record_response=None, cohort_manifest=None):
    manifest = verify()
    verify_cohort(case,cohort_manifest,manifest['fingerprint'])
    return evaluator.judge(case,model=manifest['specification']['model'],
                           record_response=record_response)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['freeze','verify'])
    args=parser.parse_args()
    result=freeze() if args.action=='freeze' else verify()
    print(result['specification']['version'])
    print('Fingerprint:',result['fingerprint'])
    print('Manifest:',MANIFEST.relative_to(ROOT))
    print('Configuration frozen and verified; evaluation dataset is not selected. No API calls made.')


if __name__=='__main__':
    main()
