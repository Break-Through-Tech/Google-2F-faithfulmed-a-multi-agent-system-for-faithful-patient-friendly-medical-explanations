"""Offline ADK orchestration and targeted-edit regression checks; no API calls."""

import unittest
from unittest.mock import patch

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from faithfulmed_demo.agent import build_agent
from faithfulmed_demo import fixtures
from faithfulmed_demo.refiner_adapter import apply_verified_edits


class RefinerTests(unittest.TestCase):
    def test_clean_verdict_preserves_draft_exactly(self):
        self.assertEqual(apply_verified_edits('A.  B.', {'issues': []}, fixtures.SOURCE), 'A.  B.')

    def test_only_flagged_span_is_changed(self):
        draft = fixtures.DRAFT + ' ' + fixtures.BAD_CLAIM
        self.assertEqual(apply_verified_edits(draft, fixtures.fixture_verdict(draft), fixtures.SOURCE), fixtures.DRAFT + ' ')

    def test_ambiguous_edit_rejected(self):
        with self.assertRaises(ValueError):
            apply_verified_edits('X X', {'issues': [{'category': 'unsupported', 'claim': 'X', 'replacement': ''}]}, fixtures.SOURCE)

    def test_paraphrase_and_omission_require_review(self):
        for issue in [
            {'category': 'unsupported', 'claim': 'Wrong.', 'replacement': 'Paraphrase.', 'source_quote': fixtures.QUOTES[0], 'reason': 'unsupported'},
            {'category': 'omission', 'claim': '', 'replacement': fixtures.QUOTES[0], 'source_quote': fixtures.QUOTES[0], 'reason': 'missing'},
        ]:
            with self.subTest(issue=issue['category']), self.assertRaises(ValueError):
                apply_verified_edits('Wrong.', {'issues': [issue]}, fixtures.SOURCE)

    def test_exact_source_quote_replacement(self):
        quote = fixtures.QUOTES[1]
        issue = {'category': 'contradiction', 'claim': 'You did not have a heart attack.',
                 'replacement': quote, 'source_quote': quote, 'reason': 'Overstates the test result'}
        self.assertEqual(apply_verified_edits(issue['claim'], {'issues': [issue]}, fixtures.SOURCE), quote)

    def test_repair_cannot_erase_entire_explanation(self):
        issue = {'category': 'unsupported', 'claim': 'Wrong.',
                 'replacement': '', 'source_quote': '', 'reason': 'Unsupported'}
        with self.assertRaises(ValueError):
            apply_verified_edits('Wrong.', {'issues': [issue]}, fixtures.SOURCE)


class WorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.sessions = InMemorySessionService()
        await self.sessions.create_session(app_name='faithfulmed_demo', user_id='test', session_id='test')
        self.runner = Runner(agent=build_agent(), app_name='faithfulmed_demo', session_service=self.sessions)

    async def invoke(self, message):
        events = [event async for event in self.runner.run_async(user_id='test', session_id='test',
            new_message=types.Content(role='user', parts=[types.Part(text=message)]))]
        session = await self.sessions.get_session(app_name='faithfulmed_demo', user_id='test', session_id='test')
        return events, session.state

    async def test_seven_stages_and_repair_then_clean_second_turn(self):
        events, state = await self.invoke('/offline-error')
        authors = list(dict.fromkeys(event.author for event in events if event.content))
        self.assertEqual(authors, ['Intake', 'Extractor', 'QuoteCheck', 'Simplifier', 'Verifier', 'Refiner', 'Readability'])
        self.assertEqual(state['source_report'], fixtures.SOURCE)
        self.assertEqual(state['verdict']['issues'][0]['category'], 'unsupported')
        self.assertNotIn(fixtures.BAD_CLAIM, state['final_answer'])
        self.assertEqual(len(state['refinement_history']), 1)
        self.assertEqual(state['final_verdict']['issues'], [])
        self.assertEqual(state['run_status'], 'complete')
        _, clean = await self.invoke('/offline')
        self.assertEqual(clean['refinement_history'], [])
        self.assertEqual(clean['draft'], clean['revised_draft'])

    async def test_failure_does_not_reuse_previous_answer(self):
        await self.invoke('/offline')
        with patch('faithfulmed_demo.agent.validate_source_quotes', side_effect=ValueError('bad quote')):
            events, state = await self.invoke('/offline-error')
        self.assertEqual(state['run_status'], 'failed')
        self.assertEqual(state['final_answer'], '')
        self.assertNotIn('Readability', [event.author for event in events])

    async def test_empty_extraction_fails_before_generation(self):
        with patch('faithfulmed_demo.fixtures.ATOMS', []):
            _, state = await self.invoke('/offline')
        self.assertEqual(state['run_status'], 'failed')

    async def test_omission_requires_review_without_unverified_insertion(self):
        from unittest.mock import AsyncMock
        verdict = {'issues': [{'category': 'omission', 'claim': '', 'replacement': 'Missing fact.',
                               'reason': 'Test fixture', 'source_quote': ''}],
                   'supported_examples': [], 'scope': 'test'}
        with patch('faithfulmed_demo.agent.judge', new=AsyncMock(return_value=verdict)) as judge:
            _, state = await self.invoke('/offline')
        self.assertEqual(len(state['refinement_history']), 0)
        self.assertEqual(judge.await_count, 1)
        self.assertEqual(state['run_status'], 'needs_review')
        self.assertEqual(state['final_answer'], '')
        self.assertIn('Omission', state['repair_blocker'])

    async def test_invalid_source_quote_stops_before_simplifier(self):
        invalid = [dict(fixtures.ATOMS[0], source_quote='Not in the original source.')]
        with patch('faithfulmed_demo.fixtures.ATOMS', invalid):
            events, state = await self.invoke('/offline')
        self.assertEqual(state['run_status'], 'failed')
        self.assertNotIn('Simplifier', [event.author for event in events])


if __name__ == '__main__':
    unittest.main()
