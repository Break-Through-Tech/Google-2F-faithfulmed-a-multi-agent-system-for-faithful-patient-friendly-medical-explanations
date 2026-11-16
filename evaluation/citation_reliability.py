"""Predeclared repeat of all 31 reviewed cases, with uniform technical retries."""
import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from . import citation_attribution as citation
from .original_judge_heldout import ROOT, RUN, SUITE, read
from .score_outputs import write_json
from .scoring import digest, safe_error

VERSION = 'citation-reliability-2026-11-15-v1'
PROTOCOL = ROOT / 'citation_reliability_2026-11-15_protocol.json'
OUTPUT = ROOT / 'citation_reliability_2026-11-15_run.json'
REPORT = Path('evaluation/CITATION_RELIABILITY.md')
ACCESS_CODES = {400, 401, 403, 404, 429}
TRANSIENT_CODES = {408, 500, 502, 503, 504}
RETRYABLE_FAILURES = {
    'quote_not_in_document', 'missing_support_witness', 'support_with_contradiction',
    'unexpected_support_witness', 'missing_contradiction_evidence',
    'unexpected_contradiction_evidence', 'missing_reason', 'schema_validation',
    'empty_response', 'incomplete_response',
}
TRANSIENT_TYPES = {
    'TimeoutError', 'ReadTimeout', 'WriteTimeout', 'ConnectTimeout', 'ConnectError',
    'ClientConnectorError', 'ClientConnectionError', 'ServerDisconnectedError',
    'RemoteProtocolError', 'ConnectionError', 'ConnectionResetError',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def specification():
    suite, old = read(SUITE), read(citation.PATH)
    cases = suite['splits']['heldout']
    if len(cases) != 31 or len({c['case_id'] for c in cases}) != 31:
        raise ValueError('Expected the same 31 unique reviewed pairs')
    if digest(citation.PROMPT) != digest(old['prompt']):
        raise ValueError('Citation prompt differs from the preserved experiment')
    if digest(suite) != old['suite_digest']:
        raise ValueError('Source suite differs from the preserved experiment')
    return dict(version=VERSION, cases=cases, prompt=citation.PROMPT,
        schema=citation.Attribution.model_json_schema(), model=citation.MODEL,
        temperature=0, sdk_version=version('google-genai'), timeout_ms=60000,
        sdk_attempts=1, exact_quote_validation=True,
        runner_sha256=sha(__file__), judge_sha256=sha(citation.__file__),
        preserved_files={str(p): sha(p) for p in [RUN, SUITE, citation.PATH,
            ROOT/'citation_attribution_v1_1_comparison.json',
            ROOT/'citation_quote_diagnostic_2026-11-12.json']},
        retry_policy=dict(max_attempts_per_case=2, phase_order='all_initial_then_eligible_retries',
            retryable_failure_codes=sorted(RETRYABLE_FAILURES),
            transient_http_codes=sorted(TRANSIENT_CODES), transient_types=sorted(TRANSIENT_TYPES),
            stop_http_codes=sorted(ACCESS_CODES), retry_correct_or_incorrect_valid_decisions=False,
            retry_prompt='identical; no correction feedback or reference label',
            final_selection='first valid attempt; otherwise last technical failure',
            interrupted_started_attempt='stop; never silently repeat an uncertain request'),
        interpretation='Reviewed-case reliability/development test, not fresh held-out validation')


def initialize():
    spec = specification()
    if PROTOCOL.exists():
        protocol = read(PROTOCOL)
        if protocol['specification'] != spec:
            raise ValueError('Frozen protocol differs; use a new version')
    else:
        if OUTPUT.exists():
            raise ValueError('Run exists without its frozen protocol')
        protocol = dict(frozen_utc=datetime.now(timezone.utc).isoformat(),
                        specification=spec, fingerprint=digest(spec))
        write_json(PROTOCOL, protocol)
    if OUTPUT.exists():
        state = read(OUTPUT)
        if state['protocol_fingerprint'] != protocol['fingerprint']:
            raise ValueError('Run uses a different protocol')
    else:
        state = dict(version=VERSION, protocol_fingerprint=protocol['fingerprint'],
                     started_utc=datetime.now(timezone.utc).isoformat(), records=[], phase='initial')
        write_json(OUTPUT, state)
    return protocol, state


def retryable(record):
    if record.get('status') != 'error' or record.get('service_code') in ACCESS_CODES:
        return False
    return (record.get('failure_code') in RETRYABLE_FAILURES
            or record.get('service_code') in TRANSIENT_CODES
            or record.get('error_type') in TRANSIENT_TYPES)


def live_call(case, capture):
    from google.genai import types
    from faithfulmed_demo.config import model_client
    with model_client() as client:
        response = client.models.generate_content(
            model=citation.MODEL, contents=json.dumps(citation.original.judge_payload(case)),
            config=types.GenerateContentConfig(system_instruction=citation.PROMPT, temperature=0,
                response_mime_type='application/json', response_schema=citation.Attribution,
                http_options=types.HttpOptions(timeout=60000,
                    retry_options=types.HttpRetryOptions(attempts=1))))
    text = response.text or ''
    finish = str(response.candidates[0].finish_reason).split('.')[-1] if response.candidates else 'NO_CANDIDATE'
    # Model text only, not request headers, API keys or raw provider exceptions.
    capture(text, finish)
    if finish != 'STOP':
        code = 'incomplete_response' if finish == 'MAX_TOKENS' else 'blocked_or_unfinished_response'
        raise citation.DecisionValidationError(code)
    if not text.strip():
        raise citation.DecisionValidationError('empty_response')
    return citation.validate_decision(citation.Attribution.model_validate_json(text), case)


def attempt_case(state, row, case, call=live_call):
    if row['attempts'] and row['attempts'][-1]['status'] == 'started':
        raise ValueError('Uncertain interrupted request; do not repeat it automatically')
    result = dict(number=len(row['attempts'])+1, status='started',
                  started_utc=datetime.now(timezone.utc).isoformat())
    row['attempts'].append(result)
    write_json(OUTPUT, state)
    started = time.perf_counter()
    def capture(text, finish):
        result.update(raw_response=text, finish_reason=finish)
        write_json(OUTPUT, state)
    try:
        result.update(call(case, capture), status='ok')
    except Exception as exc:
        result.update(status='error', **safe_error(exc),
            failure_code=getattr(exc, 'failure_code',
                'schema_validation' if type(exc).__name__ == 'ValidationError' else 'unclassified_failure'))
    result['seconds'] = round(time.perf_counter()-started, 3)
    result['retry_eligible'] = retryable(result)
    write_json(OUTPUT, state)
    print(f"{state['phase']} {case['question_id']}/{case['cited_pmid']} attempt {result['number']}: {result['status']}", flush=True)
    return result


def run_cases(state, cases, call=live_call):
    existing = {r['case_id']: r for r in state['records']}
    if any(a['status'] == 'started' for r in existing.values() for a in r['attempts']):
        raise ValueError('Uncertain interrupted request; do not repeat it automatically')
    state['phase'] = 'initial'
    for case in cases:
        row = existing.get(case['case_id'])
        if row is None:
            row = dict(case_id=case['case_id'], attempts=[])
            state['records'].append(row)
            existing[case['case_id']] = row
        if row['attempts']:
            continue
        result = attempt_case(state, row, case, call)
        if result.get('service_code') in ACCESS_CODES:
            state['phase'] = 'stopped_access_or_quota'
            write_json(OUTPUT, state)
            return
    state['phase'] = 'technical_retries'
    for case in cases:
        row = existing[case['case_id']]
        if len(row['attempts']) != 1 or not retryable(row['attempts'][0]):
            continue
        result = attempt_case(state, row, case, call)
        if result.get('service_code') in ACCESS_CODES:
            state['phase'] = 'stopped_access_or_quota'
            write_json(OUTPUT, state)
            return
    state['phase'] = 'finished'
    write_json(OUTPUT, state)


def summarize(state, cases):
    first, selected = [], []
    for row in state['records']:
        if not row['attempts']:
            continue
        attempts = row['attempts']
        first.append(dict(case_id=row['case_id'], **attempts[0]))
        chosen = next((a for a in attempts if a['status'] == 'ok'), attempts[-1])
        selected.append(dict(case_id=row['case_id'], **chosen))
    score = citation.original.summarize_predictions
    return dict(first_attempt=score(first, cases), post_retry=score(selected, cases),
        logical_calls=sum(len(r['attempts']) for r in state['records']),
        retried_cases=sum(len(r['attempts'])>1 for r in state['records']),
        recovered_cases=sum(len(r['attempts'])>1 and r['attempts'][0]['status']=='error'
                            and any(a['status']=='ok' for a in r['attempts'][1:]) for r in state['records']))


def report(protocol, state):
    cases = protocol['specification']['cases']
    result = summarize(state, cases)
    write_json(ROOT/'citation_reliability_2026-11-15_summary.json', result)
    lines = ['# Citation reliability repeat — November 15, 2026', '',
        'Predeclared full repeat of the 31 reviewed cases; not fresh held-out validation.',
        f"Protocol frozen at {protocol['frozen_utc']}; fingerprint `{protocol['fingerprint']}`.", '',
        '## Frozen policy', '',
        '- Same citation-only prompt, model, temperature zero, schema, cached source inputs, and exact-quote validation.',
        '- SDK transport retries explicitly disabled (one request per saved logical attempt); 60-second timeout. This transport control differs from the previous implicit SDK defaults.',
        '- First pass covers every case before any retry. At most one identical-call retry for invalid output or a predefined transient error; never for a valid disagreement.',
        '- No reference labels or correction feedback sent. Access/quota errors stop the run.',
        '- Every response/attempt retained; the first valid attempt is selected. Earlier runs and diagnostic responses are never spliced into this run.', '',
        '## Results', '',
        '| Pass | Valid assessments | Reference matches | Agreement on valid | Kappa on valid | Failed | Pending | Correct / all 31 |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for label, key in [('First attempt', 'first_attempt'), ('After bounded technical retries', 'post_retry')]:
        s = result[key]
        agreement = f"{s['agreement']:.1%}" if s['agreement'] is not None else 'unavailable'
        kappa = f"{s['cohen_kappa']:.3f}" if s['cohen_kappa'] is not None else 'unavailable'
        lines.append(f"| {label} | {s['scored_cases']}/31 | {s['correct']} | {agreement} | {kappa} | {s['failed_cases']} | {s['pending_cases']} | {s['correct']}/31 ({s['correct']/31:.1%}) |")
    lines += ['', f"Calls: {result['logical_calls']}; retried cases: {result['retried_cases']}; recovered technical failures: {result['recovered_cases']}.", '',
        'Historical frozen original: 23/31 (74.2%), kappa 0.498, no failures.',
        'Earlier citation-only experiment: 24/29 valid (82.8%), kappa 0.652, two failures; 24/31 correct across attempts.', '',
        '## Interpretation', '']
    final = result['post_retry']
    if final['complete']:
        lines.append('All 31 cases have valid assessments under the declared retry policy.')
        lines.append('The numerical targets are met on this reviewed cohort.' if final['targets_met_on_scored_cases'] else 'The numerical targets remain unmet on this reviewed cohort.')
    else:
        lines.append('Coverage is incomplete; valid-only metrics do not establish a complete-cohort target result.')
    lines += ['This tests repeat-run reliability on known cases. Fresh independent cases are still needed to confirm generalization. The live report Verifier is unchanged.', '',
              '## Retry and failure record', '']
    byid = {c['case_id']: c for c in cases}
    for row in state['records']:
        if len(row['attempts']) > 1 or any(a['status'] != 'ok' for a in row['attempts']):
            case = byid[row['case_id']]
            for attempt in row['attempts']:
                lines.append(f"- {case['question_id']} / PMID {case['cited_pmid']}, attempt {attempt['number']}: {attempt['status']}; {attempt.get('failure_code', 'valid decision')}; retry eligible {attempt.get('retry_eligible', False)}.")
    lines += ['', '## Remaining reference disagreements', '']
    for mismatch in final['mismatches']:
        case = byid[mismatch['case_id']]
        lines += [f"- {case['question_id']} / PMID {case['cited_pmid']}: reference {case['reference_relation']}; predicted {mismatch['prediction']}. {mismatch['reason']}"]
    REPORT.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['freeze', 'run', 'report'])
    args = parser.parse_args()
    protocol, state = initialize()
    if args.action == 'run':
        run_cases(state, protocol['specification']['cases'])
    for name, expected in protocol['specification']['preserved_files'].items():
        if sha(name) != expected:
            raise ValueError('Prior artifact changed: '+name)
    result = report(protocol, state)
    print(json.dumps({k:v for k,v in result.items() if k not in ['first_attempt','post_retry']}, indent=2))
    for key in ['first_attempt', 'post_retry']:
        print(key, {k: result[key][k] for k in ['correct','scored_cases','agreement','cohen_kappa','failed_cases','pending_cases']})


if __name__ == '__main__':
    main()
