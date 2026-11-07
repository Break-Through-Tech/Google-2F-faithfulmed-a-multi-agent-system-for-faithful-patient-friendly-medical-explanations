"""Run the offline Refiner checks through the ADK workflow.

Only the synthetic draft and Verifier judgments are scripted. The production
adapter, strict helper, repair loop, session events and readability stage run.
No model calls, retrieval, API key or vector database are needed.
"""

import argparse
import asyncio
from copy import deepcopy
from importlib.metadata import version
import json
from pathlib import Path
import platform
from unittest.mock import patch

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from . import agent, fixtures


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def issue(claim, category='unsupported', replacement='', source_quote=''):
    return {'category': category, 'claim': claim, 'replacement': replacement,
            'source_quote': source_quote, 'reason': 'Scripted Refiner behavior check.'}


def verdict(*issues):
    return {'issues': list(issues), 'supported_examples': [],
            'scope': 'Scripted behavior check; not a clinical judgment.'}


async def run_case(case_id, draft, judgments, expected_draft, expected_repairs,
                   expected_status, blocker=''):
    sessions = InMemorySessionService()
    await sessions.create_session(app_name='faithfulmed_demo', user_id='check',
                                  session_id=case_id)
    runner = Runner(agent=agent.build_agent(), app_name='faithfulmed_demo',
                    session_service=sessions)
    calls = []

    async def scripted_judge(state, text):
        require(state['mode'] == 'offline-scripted', 'Expected offline mode')
        require(len(calls) < len(judgments), 'Unexpected extra Verifier call')
        result = deepcopy(judgments[len(calls)])
        calls.append({'draft': text, 'verdict': deepcopy(result)})
        return result

    # Keep the real orchestration and repair implementation; substitute only
    # deterministic inputs at the existing offline draft / judgment seams.
    with patch.object(fixtures, 'DRAFT', draft), \
            patch.object(agent, 'judge', new=scripted_judge), \
            patch.object(agent, 'apply_verified_edits',
                         wraps=agent.apply_verified_edits) as edits:
        events = [event async for event in runner.run_async(
            user_id='check', session_id=case_id,
            new_message=types.Content(role='user', parts=[types.Part(text='/offline')]))]
    session = await sessions.get_session(app_name='faithfulmed_demo', user_id='check',
                                         session_id=case_id)
    state = session.state
    history = state['refinement_history']
    require(state['source_report'] == fixtures.SOURCE, 'Source report changed')
    require(state['draft'] == draft, 'Original draft trace changed')
    require(state['verdict'] == judgments[0], 'Initial verdict trace changed')
    require(state['revised_draft'] == expected_draft, 'Unexpected revised text')
    require(state['run_status'] == expected_status,
            f"{case_id}: expected {expected_status}, got {state['run_status']}; "
            f"{state.get('error', '')}")
    require(len(history) == expected_repairs, 'Unexpected repair count')
    require(len(calls) == len(judgments) == expected_repairs + 1,
            'Must verify initially and after every applied repair')
    require(edits.call_count == expected_repairs + bool(blocker),
            'Unexpected adapter attempts (two-round cap / blocked edit)')
    require(blocker in state['repair_blocker'] if blocker else not state['repair_blocker'],
            'Unexpected repair blocker')
    for i, entry in enumerate(history, start=1):
        require(entry['round'] == i, 'Non-sequential repair trace')
        require(entry['revised_draft'] == calls[i]['draft'], 'Recheck used stale text')
        require(entry['verdict'] == calls[i]['verdict'], 'Recheck verdict not saved')
    require(state['final_verdict'] == calls[-1]['verdict'], 'Final verdict not saved')
    authors = list(dict.fromkeys(event.author for event in events if event.content))
    require(authors == ['Intake', 'Extractor', 'QuoteCheck', 'Simplifier',
                        'Verifier', 'Refiner', 'Readability'], 'Workflow did not finish all stages')
    if expected_status == 'needs_review':
        require(state['final_answer'] == '', 'Unresolved draft was released')
    else:
        require(state['final_answer'] == expected_draft, 'Clean answer not released unchanged')
    return {'case_id': case_id, 'result': 'PASS', 'source_report': state['source_report'],
            'original_draft': state['draft'], 'initial_verdict': state['verdict'],
            'revised_draft': state['revised_draft'], 'verifier_calls': calls,
            'adapter_attempts': edits.call_count, 'refinement_history': history,
            'final_verdict': state['final_verdict'], 'repair_blocker': state['repair_blocker'],
            'run_status': state['run_status'], 'final_answer': state['final_answer'],
            'readability_score': state['readability_score'], 'stages': authors}


async def run_checks():
    clean = fixtures.DRAFT
    bad = 'Your stress test result was normal.'
    pending = next(q for q in fixtures.QUOTES if 'pending' in q.lower())
    # The clean case deliberately includes extra whitespace/newlines.
    preserved = clean + '\n\n  '
    replacement_input = clean + '\n' + bad + '\n'
    ambiguous = clean + ' ' + fixtures.BAD_CLAIM + ' ' + fixtures.BAD_CLAIM
    # Reveal one scripted finding per round to exercise both boundaries:
    # clean after repair two vs. still unresolved after repair two.
    first, second, third = ('Unsupported first.', 'Unsupported second.', 'Unsupported third.')
    cases = [
        ('clean', preserved, [verdict()], preserved, 0, 'complete', ''),
        ('deletion', clean + ' ' + fixtures.BAD_CLAIM,
         [verdict(issue(fixtures.BAD_CLAIM)), verdict()], clean + ' ', 1, 'complete', ''),
        ('replacement', replacement_input,
         [verdict(issue(bad, 'contradiction', pending, pending)), verdict()],
         clean + '\n' + pending + '\n', 1, 'complete', ''),
        ('omission', clean, [verdict(issue('', 'omission', pending, pending))],
         clean, 0, 'needs_review', 'Omission requires human review'),
        ('ambiguous', ambiguous, [verdict(issue(fixtures.BAD_CLAIM))],
         ambiguous, 0, 'needs_review', 'one exact draft span'),
        ('cap_unresolved', clean + ' ' + first + ' ' + second + ' ' + third,
         [verdict(issue(first)), verdict(issue(second)), verdict(issue(third))],
         clean + '   ' + third, 2, 'needs_review', ''),
        ('cap_clean', clean + ' ' + first + ' ' + second,
         [verdict(issue(first)), verdict(issue(second)), verdict()],
         clean + '  ', 2, 'complete', ''),
    ]
    records = []
    for case in cases:
        records.append(await run_case(*case))
    return {'scope': 'Offline scripted ADK behavior checks; no clinical/model accuracy claim.',
            'python': platform.python_version(),
            'packages': {name: version(name) for name in
                         ('google-adk', 'google-genai', 'pydantic', 'textstat', 'pandas', 'nltk')},
            'cases': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Save synthetic session traces as JSON')
    args = parser.parse_args()
    result = asyncio.run(run_checks())
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    for record in result['cases']:
        print(f"PASS {record['case_id']}: {len(record['refinement_history'])} repairs, "
              f"{len(record['verifier_calls'])} verifier calls, {record['run_status']}")
    print(f"All {len(result['cases'])} checks passed.")


if __name__ == '__main__':
    main()
