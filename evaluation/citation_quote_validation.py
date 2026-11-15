"""Versioned whitespace-only quote recovery; frozen strict judges stay intact."""
import argparse
import hashlib
import json
from pathlib import Path

from . import citation_attribution as strict
from . import citation_reliability as reliability
from .score_outputs import write_json
from .scoring import digest, safe_error

VERSION = 'citation-quote-whitespace-2026-11-15-v1'
OUTPUT = reliability.ROOT / 'citation_whitespace_replay_2026-11-15_v1_1.json'


def normalized_positions(text):
    """Collapse whitespace runs, mapping retained characters to source offsets."""
    characters, positions = [], []
    for index, char in enumerate(text):
        if char.isspace():
            if characters and characters[-1] != ' ':
                characters.append(' ')
                positions.append(index)
        else:
            characters.append(char)
            positions.append(index)
    if characters and characters[-1] == ' ':
        characters.pop()
        positions.pop()
    return ''.join(characters), positions


def splits_token(source, start, end):
    """Never recover '5 mg' from '15 mg', or a word suffix from another word."""
    first, last = source[start], source[end-1]
    left = source[start-1] if start else ''
    right = source[end] if end < len(source) else ''
    if first.isalnum() and left and (left.isalnum() or left == '_'):
        return True
    if last.isalnum() and right and (right.isalnum() or right == '_'):
        return True
    # Protect decimal, signed, fractional and comma-separated numbers as well.
    if first.isdigit() and left in '.,+-/%' and left:
        return True
    if last.isdigit() and right in '.,/%' and right:
        # A sentence-ending period is not part of a number.
        if right != '.' or (end+1 < len(source) and source[end+1].isdigit()):
            return True
    return False


def recover_quote(quote, source):
    """Recover one unique contiguous span; never fuzzy-match or edit words."""
    needle, _ = normalized_positions(quote)
    if not needle:
        raise strict.DecisionValidationError('empty_quote')
    haystack, positions = normalized_positions(source)
    locations = []
    cursor = 0
    while True:
        index = haystack.find(needle, cursor)
        if index < 0:
            break
        locations.append((positions[index], positions[index+len(needle)-1]+1))
        cursor = index+1
    if not locations:
        raise strict.DecisionValidationError('quote_not_in_document')
    if len(locations) != 1:
        raise strict.DecisionValidationError('ambiguous_quote_location')
    start, end = locations[0]
    if splits_token(source, start, end):
        raise strict.DecisionValidationError('quote_splits_token')
    restored = source[start:end]
    assert normalized_positions(restored)[0] == needle
    return dict(supplied_quote=quote, source_quote=restored, start=start, end=end,
                match_kind='exact' if restored == quote else 'whitespace_only')


def validate_decision(decision, case):
    """Restore source quotes, then apply the unchanged consistency checks."""
    parsed = strict.Attribution.model_validate(decision).model_copy(deep=True)
    source = case['evidence']
    locations = []
    if parsed.evidence_quote:
        match = recover_quote(parsed.evidence_quote, source)
        parsed.evidence_quote = match['source_quote']
        locations.append(dict(field='evidence_quote', **match))
    for index, quote in enumerate(parsed.contradiction_quotes):
        if quote:
            match = recover_quote(quote, source)
            parsed.contradiction_quotes[index] = match['source_quote']
            locations.append(dict(field=f'contradiction_quotes[{index}]', **match))
    result = strict.validate_decision(parsed, case)
    return dict(**result, quote_validation_version=VERSION, quote_locations=locations,
                evidence_sha256=hashlib.sha256(source.encode('utf-8')).hexdigest())


def judge(case, model=strict.MODEL, record_response=None):
    """Entry point for a future frozen run; prompt/schema are unchanged."""
    from google.genai import types
    from faithfulmed_demo.config import model_client, require_text
    with model_client() as client:
        response = client.models.generate_content(
            model=model, contents=json.dumps(strict.original.judge_payload(case)),
            config=types.GenerateContentConfig(system_instruction=strict.PROMPT, temperature=0,
                response_mime_type='application/json', response_schema=strict.Attribution,
                http_options=types.HttpOptions(timeout=60000,
                    retry_options=types.HttpRetryOptions(attempts=1))))
    text = require_text(response)
    if record_response is not None:
        record_response(text)
    try:
        return validate_decision(strict.Attribution.model_validate_json(text), case)
    except ValueError as exc:
        exc.rejected_response = text
        raise


def replay():
    """Revalidate ALL saved first responses. No model calls, retries or label edits."""
    protocol, run = reliability.read(reliability.PROTOCOL), reliability.read(reliability.OUTPUT)
    spec = protocol['specification']
    if digest(spec['prompt']) != digest(strict.PROMPT):
        raise ValueError('Prompt differs from saved run')
    if spec['schema'] != strict.Attribution.model_json_schema():
        raise ValueError('Schema differs from saved run')
    cases = spec['cases']
    rows = {r['case_id']: r for r in run['records']}
    if len(rows) != 31 or set(rows) != {c['case_id'] for c in cases}:
        raise ValueError('Expected all 31 captured cases')
    preserved = dict(spec['preserved_files'])
    for path in [reliability.PROTOCOL, reliability.OUTPUT,
                 reliability.ROOT/'citation_reliability_2026-11-15_summary.json']:
        preserved[str(path)] = reliability.sha(path)
    for path, expected in preserved.items():
        if reliability.sha(path) != expected:
            raise ValueError('Prior artifact changed: '+path)
    signature = digest(dict(version=VERSION, preserved=preserved,
                            validator_sha256=reliability.sha(__file__)))
    if OUTPUT.exists():
        existing = reliability.read(OUTPUT)
        if existing['signature'] != signature:
            raise ValueError('Existing replay differs; use a new version')
        print('Saved replay already exists; no earlier result overwritten.')
        print(json.dumps(existing['summary'], indent=2))
        return existing
    records = []
    for case in cases:
        first = rows[case['case_id']]['attempts'][0]
        record = dict(case_id=case['case_id'], original_status=first['status'])
        try:
            if first.get('finish_reason') != 'STOP' or not first.get('raw_response'):
                raise strict.DecisionValidationError('missing_complete_captured_response')
            parsed = strict.Attribution.model_validate_json(first['raw_response'])
            checked = validate_decision(parsed, case)
            if checked['relation'] != parsed.relation or checked['reason'] != parsed.reason:
                raise ValueError('Model decision or reason was altered')
            record.update(checked, status='ok')
        except Exception as exc:
            record.update(status='error', **safe_error(exc),
                          failure_code=getattr(exc,'failure_code','validation_failure'))
        records.append(record)
    for path, expected in preserved.items():
        if reliability.sha(path) != expected:
            raise ValueError('Prior artifact changed: '+path)
    summary = strict.original.summarize_predictions(records,cases)
    # The generic summarizer calls its input-record count api_attempts. Here
    # those are previously captured responses, not new external requests.
    source_responses = summary.pop('api_attempts')
    result = dict(version=VERSION, signature=signature, preserved_files=preserved,
        source='all 31 original first-attempt responses; no diagnostic substitutions',
        run_kind='retrospective offline validation replay, not a new model run',
        source_response_count=source_responses, new_model_calls=0,
        records=records, summary=summary)
    write_json(OUTPUT,result)
    print(json.dumps(result['summary'],indent=2))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['replay'])
    parser.parse_args()
    replay()


if __name__=='__main__':
    main()
