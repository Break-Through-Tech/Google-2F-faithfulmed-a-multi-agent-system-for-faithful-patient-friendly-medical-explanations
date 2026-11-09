"""Presentation behavior and real offline ADK integration; no external calls."""

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from faithfulmed_demo import fixtures
from faithfulmed_ui.examples import BUILTIN, load_examples
from faithfulmed_ui.pipeline import LIVE, OFFLINE, REPAIR, Snapshot, request_message, stream_run
from faithfulmed_ui.presentation import answer_markdown, result_status, sources_html, trace_state


class PresentationTests(unittest.TestCase):
    def test_custom_report_and_scripted_modes_cannot_be_confused(self):
        self.assertEqual(request_message('Custom medical note.', LIVE), 'Custom medical note.')
        self.assertEqual(request_message(fixtures.SOURCE, LIVE), '/demo')
        self.assertEqual(request_message('Unrelated note.', REPAIR), '/offline-error')
        for report in ('', '  ', '/offline', 'x' * 30001):
            with self.assertRaises(ValueError):
                request_message(report, LIVE)

    def test_unresolved_or_failed_outputs_never_look_final(self):
        for status in ('needs_review', 'needs_simplification', 'failed'):
            view = Snapshot(state={'run_status': status, 'final_answer': 'stale final',
                                   'draft': 'current draft'}, finished=True)
            self.assertNotEqual(result_status(view)[0], 'complete')
            self.assertNotIn('stale final', answer_markdown(view))
        view = Snapshot(state={'run_status': 'complete', 'final_answer': 'unsafe',
                               'final_verdict': {'issues': [{'category': 'omission'}]}}, finished=True)
        self.assertEqual(result_status(view)[0], 'review')

    def test_sources_are_escaped_and_only_medlineplus_links_are_clickable(self):
        html = sources_html({'retrieved_context': [{'text': '<script>attack</script>',
            'metadata': {'title': '<img onerror=attack>', 'source_url': 'javascript:alert(1)'}}]})
        self.assertNotIn('<script>', html)
        self.assertNotIn('<img ', html)
        self.assertNotIn('href=', html)
        self.assertIn('&lt;script&gt;', html)

    def test_absent_dataset_keeps_synthetic_demo_available(self):
        with tempfile.TemporaryDirectory() as directory:
            examples, message = load_examples(Path(directory))
        self.assertEqual(list(examples), [BUILTIN])
        self.assertEqual(examples[BUILTIN]['text'], fixtures.SOURCE)
        self.assertIn('not installed', message)

    def test_trace_excludes_unknown_metadata(self):
        self.assertEqual(trace_state({'final_answer': 'answer', 'secret': 'hidden'}), {'final_answer': 'answer'})


class UIWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def collect(self, report=fixtures.SOURCE, mode=OFFLINE):
        return [view async for view in stream_run(report, mode)]

    async def test_offline_repair_runs_existing_pipeline_and_shows_recheck(self):
        views = await self.collect(mode=REPAIR)
        final = views[-1]
        self.assertTrue(final.finished)
        self.assertEqual(len(final.completed), 7)
        self.assertEqual(final.state['run_status'], 'complete')
        self.assertEqual(len(final.state['refinement_history']), 1)
        self.assertNotIn(fixtures.BAD_CLAIM, answer_markdown(final))
        self.assertIn('Scripted', result_status(final)[1])
        self.assertEqual(views[0].state['run_status'], 'running')
        self.assertNotIn('final_answer', views[0].state)

    async def test_concurrent_requests_keep_state_isolated(self):
        repaired, clean = await asyncio.gather(self.collect(mode=REPAIR), self.collect(mode=OFFLINE))
        self.assertEqual(len(repaired[-1].state['refinement_history']), 1)
        self.assertEqual(clean[-1].state['refinement_history'], [])
        self.assertEqual(clean[-1].state['verdict']['issues'], [])

    async def test_quote_failure_clears_final_and_stops_progress(self):
        with patch('faithfulmed_demo.agent.validate_source_quotes', side_effect=ValueError('bad quote')):
            views = await self.collect()
        self.assertEqual(views[-1].state['run_status'], 'failed')
        self.assertEqual(views[-1].state['final_answer'], '')
        self.assertNotIn('Simplifier', views[-1].completed)
        self.assertNotIn('bad quote', views[-1].error)

    async def test_omission_keeps_review_draft_and_blocker(self):
        verdict = {'issues': [{'category': 'omission', 'claim': '', 'replacement': 'Missing fact.',
                               'reason': 'Missing fact', 'source_quote': ''}], 'supported_examples': [], 'scope': 'test'}
        with patch('faithfulmed_demo.agent.judge', new=AsyncMock(return_value=verdict)):
            views = await self.collect()
        final = views[-1]
        self.assertEqual(final.state['run_status'], 'needs_review')
        self.assertTrue(final.state['repair_blocker'])
        self.assertTrue(answer_markdown(final).startswith('### Draft for review'))
        self.assertEqual(final.state['final_answer'], '')

    async def test_blank_input_finishes_without_starting_agent(self):
        with patch('faithfulmed_ui.pipeline.build_agent') as build:
            views = await self.collect('', LIVE)
        build.assert_not_called()
        self.assertEqual(len(views), 1)
        self.assertTrue(views[0].finished)
        self.assertIn('Paste a report', views[0].error)


if __name__ == '__main__':
    unittest.main()
