"""Run the same ADK agent as Web and save a local trace. Defaults to offline."""

import argparse
import asyncio
import json
from pathlib import Path

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .agent import build_agent


async def run(message, output):
    sessions = InMemorySessionService()
    await sessions.create_session(app_name='faithfulmed_demo', user_id='smoke', session_id='demo')
    runner = Runner(agent=build_agent(), app_name='faithfulmed_demo', session_service=sessions)
    events = []
    async for event in runner.run_async(user_id='smoke', session_id='demo',
            new_message=types.Content(role='user', parts=[types.Part(text=message)])):
        events.append(event.model_dump(mode='json', exclude_none=True))
        if event.content:
            print(event.author + ': ' + ''.join(p.text or '' for p in event.content.parts)[:250], flush=True)
    session = await sessions.get_session(app_name='faithfulmed_demo', user_id='smoke', session_id='demo')
    payload = {'message': message, 'state': session.state, 'events': events}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print('Saved trace:', output)
    if session.state.get('run_status') not in ('complete', 'needs_review'):
        raise SystemExit('Demo did not complete. Read the stage error in the trace.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--message', default='/offline-error')
    parser.add_argument('--output', type=Path, default=Path('data/adk_demo_results/offline.json'))
    args = parser.parse_args()
    asyncio.run(run(args.message, args.output))
