"""Release-gate tests for readability rewrites; no external calls."""

import asyncio
from functools import wraps
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from faithfulmed_demo.agent import ReadabilityStage


def run_async(test):
    @wraps(test)
    def run():
        return asyncio.run(test())
    return run


def context(**updates):
    state = dict(source_report='Dose is 5 mg. Result is pending.', atoms=[],
                 retrieved_context=[], revised_draft='Original verified draft.',
                 final_verdict={'issues': []}, repair_blocker='', mode='live',
                 model='test-model', stage_modes={}, final_answer='', run_status='running')
    state.update(updates)
    return SimpleNamespace(invocation_id='rewrite-test', session=SimpleNamespace(state=state))


def score(grade):
    passes = grade <= 8
    return dict(readability_score={'status': 'ok', 'flesch_kincaid_grade': grade},
                readability_pass=passes, readability_status='passed' if passes else 'needs_simplification',
                final_answer='Simpler verified draft.' if passes else None,
                suggestion=None if passes else 'Use simpler words.')


async def consume(ctx):
    events = []
    async for event in ReadabilityStage(name='Readability')._run_async_impl(ctx):
        ctx.session.state.update(event.actions.state_delta)
        events.append(event)
    return events


@run_async
async def test_already_readable_text_needs_no_rewrite_or_recheck():
    ctx = context()
    with patch('faithfulmed_demo.agent.run_readability', return_value=score(7)), \
         patch('faithfulmed_demo.agent.rewrite_for_readability') as rewrite, \
         patch('faithfulmed_demo.agent.judge', new_callable=AsyncMock) as judge:
        await consume(ctx)
    rewrite.assert_not_called()
    judge.assert_not_awaited()
    assert ctx.session.state['run_status'] == 'complete'


@run_async
async def test_rewrite_cannot_be_released_until_reverified():
    ctx = context()
    order = []

    def rewrite(*args, **kwargs):
        order.append('rewrite')
        return 'Simpler verified draft.'

    async def judge(state, candidate):
        order.append('verify')
        assert state['final_answer'] == ''
        assert state['faithfulness_recheck_required'] is True
        return {'issues': []}

    with patch('faithfulmed_demo.agent.run_readability', side_effect=[score(10), score(7)]), \
         patch('faithfulmed_demo.agent.rewrite_for_readability', side_effect=rewrite), \
         patch('faithfulmed_demo.agent.judge', side_effect=judge):
        await consume(ctx)
    assert order == ['rewrite', 'verify']
    assert ctx.session.state['run_status'] == 'complete'
    assert ctx.session.state['final_answer'] == ctx.session.state['revised_draft'] == 'Simpler verified draft.'
    assert ctx.session.state['readability_history'][0]['accepted'] is True
    assert ctx.session.state['faithfulness_recheck_required'] is False


@run_async
async def test_changed_dose_finding_blocks_release_even_if_grade_passes():
    ctx = context()
    issue = {'category': 'contradiction', 'claim': '50 mg', 'reason': 'Dose was changed.'}
    with patch('faithfulmed_demo.agent.run_readability', side_effect=[score(10), score(6)]), \
         patch('faithfulmed_demo.agent.rewrite_for_readability', return_value='Take 50 mg.'), \
         patch('faithfulmed_demo.agent.judge', new=AsyncMock(return_value={'issues': [issue]})):
        await consume(ctx)
    state = ctx.session.state
    assert state['run_status'] == 'needs_review'
    assert state['final_answer'] == ''
    assert state['revised_draft'] == 'Original verified draft.'
    assert state['readability_history'][0]['verdict']['issues'] == [issue]
    assert state['readability_history'][0]['accepted'] is False


@run_async
async def test_existing_clinical_blocker_is_not_bypassed():
    ctx = context(repair_blocker='Omission needs review.')
    with patch('faithfulmed_demo.agent.run_readability', return_value=score(10)), \
         patch('faithfulmed_demo.agent.rewrite_for_readability') as rewrite:
        await consume(ctx)
    rewrite.assert_not_called()
    assert ctx.session.state['run_status'] == 'needs_review'
    assert ctx.session.state['final_answer'] == ''


@run_async
async def test_two_rewrite_cap_keeps_verified_but_difficult_draft_unreleased():
    ctx = context()
    with patch('faithfulmed_demo.agent.run_readability', side_effect=[score(11), score(10), score(9)]), \
         patch('faithfulmed_demo.agent.rewrite_for_readability', side_effect=['First rewrite.', 'Second rewrite.']) as rewrite, \
         patch('faithfulmed_demo.agent.judge', new=AsyncMock(return_value={'issues': []})) as judge:
        await consume(ctx)
    assert rewrite.call_count == judge.await_count == 2
    assert ctx.session.state['run_status'] == 'needs_simplification'
    assert ctx.session.state['revised_draft'] == 'Second rewrite.'
    assert ctx.session.state['final_answer'] == ''


@run_async
async def test_non_improving_rewrite_stops_early():
    ctx = context()
    with patch('faithfulmed_demo.agent.run_readability', side_effect=[score(10), score(11)]), \
         patch('faithfulmed_demo.agent.rewrite_for_readability', return_value='Harder text.') as rewrite, \
         patch('faithfulmed_demo.agent.judge', new=AsyncMock(return_value={'issues': []})):
        await consume(ctx)
    assert rewrite.call_count == 1
    assert ctx.session.state['revised_draft'] == 'Original verified draft.'
    assert ctx.session.state['final_answer'] == ''


@run_async
async def test_recheck_service_failure_never_releases_candidate():
    ctx = context()
    with patch('faithfulmed_demo.agent.run_readability', return_value=score(10)), \
         patch('faithfulmed_demo.agent.rewrite_for_readability', return_value='Unchecked rewrite.'), \
         patch('faithfulmed_demo.agent.judge', new=AsyncMock(side_effect=RuntimeError('private response'))):
        await consume(ctx)
    assert ctx.session.state['run_status'] == 'failed'
    assert ctx.session.state['final_answer'] == ''
    assert ctx.session.state['readability_history'][0]['verdict'] is None
    assert 'private response' not in ctx.session.state['error']
