"""Exercise an already-running ADK Web server and save its session/trace."""

import argparse
import json
from pathlib import Path
import urllib.request
import uuid


def request(base, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(base + path, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='http://127.0.0.1:8000')
    parser.add_argument('--message', default='/offline-error')
    parser.add_argument('--sse', action='store_true', help='Use the streaming endpoint used by the browser.')
    parser.add_argument('--output', type=Path, default=Path('data/adk_demo_results/web_offline.json'))
    args = parser.parse_args()
    assert 'faithfulmed_demo' in request(args.base, '/list-apps')
    session_id = 'smoke-' + uuid.uuid4().hex[:12]
    path = f'/apps/faithfulmed_demo/users/demo_smoke/sessions/{session_id}'
    request(args.base, path, {})
    print('Running', args.message, 'through ADK Web session', session_id, flush=True)
    payload = {'appName': 'faithfulmed_demo',
        'userId': 'demo_smoke', 'sessionId': session_id,
        'newMessage': {'role': 'user', 'parts': [{'text': args.message}]}}
    if args.sse:
        req = urllib.request.Request(args.base + '/run_sse', data=json.dumps(payload).encode(),
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=300) as response:
            events = [json.loads(line[6:]) for raw in response
                      if (line := raw.decode().strip()).startswith('data: ')]
    else:
        events = request(args.base, '/run', payload)
    session = request(args.base, path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'message': args.message, 'events': events,
                                      'state': session['state']}, indent=2), encoding='utf-8')
    state = session['state']
    print('Stage authors:', list(dict.fromkeys(e['author'] for e in events if e.get('content'))))
    print('Status:', state.get('run_status'), '; mode:', state.get('mode'))
    print('Error:', state.get('error'))
    print('Readability:', state.get('readability'))
    print('Saved:', args.output)
    if state.get('run_status') not in ('complete', 'needs_review'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
