"""Capture the native init surface at a loopback stub. OS denies remote networking.
No request forwarding, no model inference, no credential/header retention.

Adapted from experiments/rvb-bh-1a/execution/context_probe.py: same loopback
HTTP stub, dummy API-key transport, sandbox-exec remote-network denial,
neutral workspace, no header retention. Adapted: the workspace is a real
materialized snapshot (so the init reflects the tree, e.g. that the in-tree
.agents skill is not loaded); the stub answers a minimal SSE message instead
of a 400 so the CLI completes normally; an optional Bash tool turn exercises
the tool path under the receiver sandbox; request bodies are reduced to
model, tool names, message count, the system blocks, the user-message text
blocks and the native environment message (tool schemas are not retained).
Observed on 2.1.272: the first user message carries a native commit-attribution
system-reminder block before the prompt block; the pass rule is therefore
"prompt is the last text block" and every other block is retained verbatim.
"""
import hashlib
import http.server
import json
import os
import signal
import subprocess
import threading
import time
from pathlib import Path
import runtime

SSE_MODEL = 'stub'
PROBE_PROMPT = 'OFFLINE INIT PROBE. Return only probe-ok.'
TOOL_PROBE = ('python3 -c "import os\nfor p in %s:\n    p = os.path.expanduser(p)\n    try:\n        try: open(p, \'rb\').read(1)\n'
              '        except IsADirectoryError: os.listdir(p)\n        print(\'ALLOWED\', p)\n'
              '    except PermissionError: print(\'DENIED\', p)\n    except FileNotFoundError: print(\'MISSING\', p)\n'
              'open(\'probe-write.txt\', \'w\').write(\'x\'); os.remove(\'probe-write.txt\'); print(\'WROTE\')"' % list(runtime.PROTECTED))


def sse(events):
    return ''.join(f'event: {e["type"]}\ndata: {json.dumps(e)}\n\n' for e in events).encode()


def message(model, block, stop):
    return [{'type': 'message_start', 'message': {'id': 'msg_stub', 'type': 'message', 'role': 'assistant', 'model': model,
                                                 'content': [], 'stop_reason': None, 'stop_sequence': None,
                                                 'usage': {'input_tokens': 1, 'output_tokens': 1}}},
            *block,
            {'type': 'message_delta', 'delta': {'stop_reason': stop, 'stop_sequence': None}, 'usage': {'output_tokens': 1}},
            {'type': 'message_stop'}]


def text_turn(model, text):
    return message(model, [{'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}},
                           {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': text}},
                           {'type': 'content_block_stop', 'index': 0}], 'end_turn')


def tool_turn(model, command):
    return message(model, [{'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'tool_use', 'id': 'toolu_stub1', 'name': 'Bash', 'input': {}}},
                           {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'input_json_delta', 'partial_json': json.dumps({'command': command})}},
                           {'type': 'content_block_stop', 'index': 0}], 'tool_use')


def text_of(content):
    if isinstance(content, str):
        return content
    return ''.join(b.get('text', '') for b in content if isinstance(b, dict) and b.get('type') == 'text')


def reduce(data, prompt):
    messages = data.get('messages') or []
    first = messages[0] if messages else {}
    content = first.get('content')
    return {'model': data.get('model'), 'stream': data.get('stream'), 'top_level_keys': sorted(data),
            'tools': [t.get('name') for t in data.get('tools') or []], 'message_count': len(messages),
            # 2.1.272 prepends a native attribution system-reminder block; the prompt is the last text block.
            'first_user_message_is_prompt': first.get('role') == 'user' and (
                content == prompt or (isinstance(content, list) and bool(content) and text_of(content[-1:]) == prompt)),
            'first_user_content_shape': 'str' if isinstance(content, str) else
            ('blocks:' + ','.join(str(b.get('type')) for b in content) if isinstance(content, list) else type(content).__name__),
            'message_roles': [m.get('role') for m in messages],
            'first_user_blocks': [text_of([b]) if isinstance(b, dict) else str(b) for b in content] if isinstance(content, list) else None,
            'other_messages': [{'role': m.get('role'), 'text': text_of(m.get('content') or '')} for m in messages[1:]],
            'system': data.get('system'),
            'thinking': data.get('thinking'), 'max_tokens': data.get('max_tokens')}


def capture(snapshot, model, prompt=PROBE_PROMPT, tool_command=None, timeout=120):
    snapshot = Path(snapshot).resolve()
    requests = []; turns = []
    tool_model = model

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
            try:
                data = json.loads(body)
            except ValueError:
                data = {'unparsed_body_sha256': hashlib.sha256(body).hexdigest()}
            requests.append({'path': self.path, 'body_sha256': hashlib.sha256(body).hexdigest(), **reduce(data, prompt)})
            if tool_command and not turns:
                events = tool_turn(tool_model, tool_command); turns.append('tool')
            else:
                events = text_turn(tool_model, 'probe-ok'); turns.append('text')
            self.send_response(200); self.send_header('Content-Type', 'text/event-stream'); self.end_headers()
            self.wfile.write(sse(events)); self.wfile.flush()

        def do_GET(self):
            requests.append({'path': self.path, 'method': 'GET'})
            self.send_response(404); self.end_headers()

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
    env = runtime.environment()
    env.update(ANTHROPIC_BASE_URL=f'http://127.0.0.1:{server.server_port}', ANTHROPIC_API_KEY='offline-not-a-credential',
               ANTHROPIC_AUTH_TOKEN='', CLAUDE_CODE_MAX_RETRIES='0')
    argv = [*runtime.sandbox(snapshot, runtime.STUB_NETWORK), *runtime.invocation(snapshot, model)]
    started = time.monotonic()
    process = subprocess.Popen(argv, cwd=snapshot, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        out, err = process.communicate(prompt.encode(), timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True; os.killpg(process.pid, signal.SIGKILL); out, err = process.communicate()
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    server.shutdown(); server.server_close(); worker.join()
    lines = out.decode(errors='replace').splitlines()
    parsed = []
    for line in lines:
        try:
            parsed.append(json.loads(line))
        except ValueError:
            parsed.append({'unparsed': line})
    tool_results = [c for e in parsed if e.get('type') == 'user'
                    for c in (e.get('message') or {}).get('content') or [] if isinstance(c, dict) and c.get('type') == 'tool_result']
    result = next((e for e in parsed if e.get('type') == 'result'), None)
    return {'model': model, 'requests': requests, 'turns': turns, 'exit_code': process.returncode, 'timed_out': timed_out,
            'elapsed_seconds': time.monotonic() - started, 'stdout_lines': lines, 'stderr': err.decode(errors='replace'),
            'tool_results': tool_results, 'result': {k: result.get(k) for k in ('subtype', 'is_error', 'result', 'num_turns', 'permission_denials')} if result else None,
            'argv': argv[3:],  # the sandbox-exec prefix carries the profile; recorded via runtime.PROFILE
            'transport': 'loopback stub; sandbox-exec denies remote network; dummy API-key transport',
            'auth_difference': 'Dummy API-key transport for capture (apiKeySource ANTHROPIC_API_KEY); the live Max login reports none.',
            'projection': 'Only model/tool names/message count/system blocks/prompt-equality retained from request bodies; headers never retained.'}
