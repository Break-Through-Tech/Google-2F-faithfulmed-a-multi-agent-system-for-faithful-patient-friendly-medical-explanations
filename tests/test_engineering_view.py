import asyncio
import json
from unittest.mock import patch
import pytest
from faithfulmed_demo import fixtures
from faithfulmed_demo.execution_trace import interrupt
from faithfulmed_ui.pipeline import stream_run, OFFLINE, REPAIR
from faithfulmed_ui.presentation import engineering_html

async def collect(mode=OFFLINE):
    return [v async for v in stream_run(fixtures.SOURCE,mode)]

def test_scripted_run_has_real_local_calls_but_no_claimed_model_calls():
    views=asyncio.run(collect());rows=views[-1].state['execution_trace']
    assert len([r for r in rows if r['kind']=='stage'])==7
    assert all(r['status']=='completed' for r in rows if r['kind']=='stage')
    assert not any(r['kind']=='model' and r['status']=='completed' for r in rows)
    assert any(r['name']=='validate_source_quotes' and r['status']=='completed' for r in rows)
    assert any(r['name']=='apply_verified_edits' and r['status']=='skipped' for r in rows)
    assert any(r['kind']=='local' and r['status']=='running' for v in views for r in v.state.get('execution_trace',[]))
    assert all(isinstance(r['duration_ms'],(int,float)) and r['duration_ms']>=0 for r in rows)

def test_repair_edits_and_recheck_are_separate_entries():
    with patch('faithfulmed_demo.agent.apply_verified_edits',wraps=__import__('faithfulmed_demo.agent',fromlist=['apply_verified_edits']).apply_verified_edits) as edit:
        views=asyncio.run(collect(REPAIR))
    rows=views[-1].state['execution_trace']
    assert edit.call_count==1
    assert any(r['name']=='apply_verified_edits / round 1' and r['status']=='completed' for r in rows)
    recheck=next(r for r in rows if r['name']=='Verifier recheck / repair 1')
    assert recheck['kind']=='scripted' and recheck['output']['issues']==[]
    assert fixtures.BAD_CLAIM not in views[-1].state['final_answer']

def test_failure_is_sanitized_and_downstream_stages_are_skipped():
    with patch('faithfulmed_demo.agent.validate_source_quotes',side_effect=ValueError('API_KEY=do-not-display')):
        views=asyncio.run(collect())
    rows=views[-1].state['execution_trace']
    assert next(r for r in rows if r['name']=='validate_source_quotes')['status']=='failed'
    assert next(r for r in rows if r['kind']=='stage' and r['stage']=='Simplifier')['status']=='skipped'
    assert not any(r['status']=='running' for r in rows)
    assert 'do-not-display' not in json.dumps(rows)
    assert views[-1].state['final_answer']==''

def test_timeline_escapes_report_text_and_marks_truncation():
    html=engineering_html({'execution_trace':[dict(name='<script>x</script>',stage='X',kind='local',status='completed',
        duration_ms=12,inputs={'text':'<img onerror=oops>'},output='safe')]})
    assert '<script>' not in html and '<img ' not in html
    assert '&lt;script&gt;' in html and '&lt;img' in html

def test_interrupted_operations_do_not_remain_running():
    state={'execution_trace':[dict(status='running',started_utc='2026-01-01T00:00:00+00:00')]}
    interrupt(state)
    assert state['execution_trace'][0]['status']=='interrupted'

def test_trace_is_per_run_and_view_tabs_share_one_pipeline():
    async def run_both():return await asyncio.gather(collect(),collect(REPAIR))
    clean,repair=asyncio.run(run_both())
    assert not any('repair 1' in r['name'] for r in clean[-1].state['execution_trace'])
    assert any('repair 1' in r['name'] for r in repair[-1].state['execution_trace'])
    from faithfulmed_ui.app import build_ui
    app=build_ui()
    labels=[c['props'].get('label') for c in app.config['components'] if c['type']=='tabitem']
    assert labels==['User view','Engineering view']
    assert sum(d.get('api_name')=='simplify' for d in app.config['dependencies'])==1
