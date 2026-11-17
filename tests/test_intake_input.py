"""Input boundaries: prior session state is not a new medical report."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from google.genai import types

from faithfulmed_demo.agent import prepare


def context(message, state):
    return SimpleNamespace(user_content=types.Content(parts=[types.Part(text=message)]), state=state)


@pytest.mark.parametrize('field', ['source_report', 'note', 'source_text'])
def test_blank_message_cannot_reprocess_prior_report(field):
    state = {field: 'An earlier report.', 'final_answer': 'An earlier answer.'}
    before = deepcopy(state)
    response = prepare(context('  \n\t ', state))
    assert response is not None
    assert 'Enter /demo or paste' in response.parts[0].text
    assert state == before  # Validation stops this invocation before stages run.


def test_explicit_report_replaces_every_prior_note_result():
    state = dict(source_report='Old report', note='Old alias', source_text='Old alias',
                 final_answer='Old answer', atoms=[{'text': 'Old fact'}], execution_trace=[{}])
    assert prepare(context('New report text.', state)) is None
    assert state['source_report'] == state['retrieval_query'] == 'New report text.'
    assert state['final_answer'] == ''
    assert state['atoms'] == state['execution_trace'] == []
    assert state['run_status'] == 'running'


def test_comparison_runner_supplies_report_as_current_message():
    from evaluation.run_comparison import run_adk_attempt

    received = []

    async def invoke(message, session_id, events, scripted=False, variant='full'):
        received.append(message)
        state = {}
        assert prepare(context(message, state)) is None
        assert state['source_report'] == 'The current comparison report.'
        return state

    # Match the public runner invocation contract without any generation calls.
    with patch('evaluation.run_comparison.invoke_adk', new=invoke):
        _, trace = run_adk_attempt(SimpleNamespace(mode='live', check_model=False, variant='full'),
                                  'The current comparison report.', 'isolated-test')
    assert trace['state']['source_report'] == 'The current comparison report.'
    assert received == ['The current comparison report.']
