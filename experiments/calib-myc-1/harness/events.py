"""Incremental native JSONL retention with a fail-closed init policy.

Copied from experiments/rvb-bh-1a/execution/events.py: public() (reasoning
removal with counting), has_tool(), the Trace line loop and run() (process
group, timer, killpg). Adapted: the init policy is three explicit sets —
EQUAL (compared to the expected init captured offline; 'model' is compared to
the requested model instead), PATTERN (shape checks) and RECORD_ONLY — and any
other new or missing field is an error. fast_mode_disabled_reason is in EQUAL
although the package brief did not list it: it is present in the observed
2.1.272 init, and an unlisted present field would otherwise fail every run.
Tools are expected here (rvb-bh-1a forbade them), so tool use is counted, not
invalidating. infrastructure_valid() follows PLAN.md revision 2: a timeout or a
non-zero exit after a normal result is not an environment failure; an
is_error result, a second init, an init policy error, or malformed lines (other
than one truncated final line after a kill) is.
"""
import json
import os
import re
import signal
import subprocess
import threading
from common import WORK

HIDDEN = {'thinking', 'redacted_thinking', 'reasoning', 'thinking_delta', 'signature_delta'}
STRUCTURAL = ('type', 'subtype')
EQUAL = ('model', 'claude_code_version', 'tools', 'mcp_servers', 'plugins', 'permissionMode', 'agents',
         'capabilities', 'analytics_disabled', 'product_feedback_disabled', 'fast_mode_state',
         'fast_mode_disabled_reason', 'skills', 'slash_commands')
# skills and slash_commands are also required to be EMPTY regardless of the
# expected capture: a non-empty list is a sign of foreign context (review B2).
MUST_BE_EMPTY = ('skills', 'slash_commands', 'mcp_servers', 'plugins')  # agents lists built-ins; EQUAL-compared only
PATTERN = ('cwd', 'session_id', 'uuid', 'apiKeySource', 'messaging_socket_path')
RECORD_ONLY = ('output_style',)
OPTIONAL = ('messaging_socket_path',)
API_KEY_SOURCES = ('none', 'ANTHROPIC_API_KEY')  # live Max login reports 'none'; the offline stub 'ANTHROPIC_API_KEY'
UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
SOCKET = re.compile(r'^/tmp/cc-socks/\d+\.sock$')
# tool_progress: CLI heartbeat for a tool call running longer than 30 s
# (tool_use_id suffix -heartbeat-N, elapsed_time_seconds, heartbeat: true).
# Observed in run e6b293fa slot 1, where it alone invalidated a trace whose
# grader outcome was PASS. It carries no model or user content.
KNOWN_TYPES = ('system', 'assistant', 'user', 'result', 'rate_limit_event', 'tool_progress')
# system subtypes seen live (2.1.272): init, api_retry, permission_denied,
# task_started, task_notification. Recorded, not policed beyond init.


def policy():
    return {'structural': list(STRUCTURAL), 'equal': list(EQUAL), 'must_be_empty': list(MUST_BE_EMPTY),
            'pattern': list(PATTERN), 'record_only': list(RECORD_ONLY),
            'optional': list(OPTIONAL), 'api_key_sources': list(API_KEY_SOURCES),
            'unknown_event_type': 'invalid', 'user_events': 'tool_result blocks only; the prompt echo once; any other text is foreign',
            'cwd_prefix': '~/' + WORK + '/receivers/', 'socket_regex': SOCKET.pattern,
            'model_accepts_1m_suffix': True, 'unknown_field': 'error'}


def cwd_prefix():
    return os.path.expanduser('~/' + WORK + '/receivers/')


def init_errors(event, expected, model):
    errors = []
    for name in EQUAL:
        if name not in event:
            errors.append('missing init field: ' + name)
        elif name == 'model':
            if event[name] != model:
                errors.append('requested model mismatch')
        elif name not in expected:
            errors.append('expected init lacks field: ' + name)
        # JSON serialization also distinguishes false from 0 and [] from null.
        elif json.dumps(event[name], sort_keys=True) != json.dumps(expected[name], sort_keys=True):
            errors.append('init field changed: ' + name)
    for name in MUST_BE_EMPTY:
        if name in event and event[name] != []:
            errors.append(name + ' must be []')
    for name in PATTERN + RECORD_ONLY:
        if name not in event and name not in OPTIONAL:
            errors.append('missing init field: ' + name)
    if 'cwd' in event and not (isinstance(event['cwd'], str) and event['cwd'].startswith(cwd_prefix())):
        errors.append('cwd outside receivers')
    for name in ('session_id', 'uuid'):
        if name in event and not (isinstance(event[name], str) and UUID.match(event[name])):
            errors.append(name + ' is not a UUID')
    if 'apiKeySource' in event and event['apiKeySource'] not in API_KEY_SOURCES:
        errors.append('apiKeySource unexpected')
    if 'messaging_socket_path' in event and not (isinstance(event['messaging_socket_path'], str)
                                                 and SOCKET.match(event['messaging_socket_path'])):
        errors.append('messaging_socket_path unexpected')
    if not (event.get('type') == 'system' and event.get('subtype') == 'init'):
        errors.append('not an init event')
    for name in sorted(set(event) - set(STRUCTURAL) - set(EQUAL) - set(PATTERN) - set(RECORD_ONLY)):
        errors.append('unexpected init field: ' + name)
    return errors


def probe_init(lines, model):
    rows = []
    for line in lines:
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    inits = [e for e in rows if isinstance(e, dict) and e.get('type') == 'system' and e.get('subtype') == 'init']
    if len(inits) != 1:
        raise ValueError('PROBE_INIT_COUNT')
    if init_errors(inits[0], inits[0], model):
        raise ValueError('PROBE_INIT_SURFACE: ' + '; '.join(init_errors(inits[0], inits[0], model)))
    return inits[0]


def public(value):
    """Remove only recognizable private reasoning blocks; count every removal."""
    if isinstance(value, dict):
        if value.get('type') in HIDDEN:
            return None, 1
        out = {}; removed = 0
        for k, v in value.items():
            if k in ('thinking', 'reasoning_content', 'signature'):
                removed += 1; continue
            child, n = public(v); removed += n
            if child is not None or n == 0:
                out[k] = child
        return out, removed
    if isinstance(value, list):
        out = []; removed = 0
        for v in value:
            child, n = public(v); removed += n
            if child is not None or n == 0:
                out.append(child)
        return out, removed
    return value, 0


def tool_uses(value, found):
    if isinstance(value, dict):
        if value.get('type') == 'tool_use':
            found.append(value.get('name'))
        for v in value.values():
            tool_uses(v, found)
    elif isinstance(value, list):
        for v in value:
            tool_uses(v, found)
    return found


def foreign_user_blocks(event, prompt_text, prompt_seen):
    """Blocks of a `user` event that are not tool results. The task prompt may echo once."""
    message = event.get('message')
    content = message.get('content') if isinstance(message, dict) else None
    if isinstance(content, str):
        content = [{'type': 'text', 'text': content}]
    if not isinstance(content, list):
        return ['user event without a content list']
    foreign = []
    for block in content:
        kind = block.get('type') if isinstance(block, dict) else None
        if kind == 'tool_result':
            continue
        if (kind == 'text' and prompt_text is not None and not prompt_seen[0]
                and isinstance(block.get('text'), str) and block['text'].strip() == prompt_text.strip()):
            prompt_seen[0] = True
            continue
        foreign.append(kind or 'non-dict block')
    return foreign


class Trace:
    def __init__(self, expected_init, requested_model, prompt=None):
        self.omitted = 0; self.rewritten = 0; self.malformed = 0; self.lines = 0; self.last_malformed = False
        self.result = None; self.result_event = None; self.failed = False; self.unknown = []; self.models = []
        self.complete = False; self.tools = []; self.foreign_user = []
        self.prompt_text = prompt.decode('utf-8', 'replace') if isinstance(prompt, bytes) else prompt
        self.prompt_seen = [False]
        self.expected_init = expected_init; self.requested_model = requested_model
        self.init_count = 0; self.init_errors = []; self.init_event = None

    def line(self, line):
        self.lines += 1
        try:
            event = json.loads(line)
        except (ValueError, UnicodeError):
            self.malformed += 1; self.last_malformed = True
            return line  # retained as unparsed public transport output, audit required
        self.last_malformed = False
        if not isinstance(event, dict):
            self.malformed += 1; self.last_malformed = True
            return line
        tool_uses(event, self.tools)
        if event.get('type') == 'system' and event.get('subtype') == 'init':
            self.init_count += 1
            if self.init_event is None:
                self.init_event = event
                self.init_errors.extend(init_errors(event, self.expected_init, self.requested_model))
        t = event.get('type')
        if t not in KNOWN_TYPES:
            self.unknown.append(t)
        if t == 'user':
            self.foreign_user.extend(foreign_user_blocks(event, self.prompt_text, self.prompt_seen))
        if t == 'assistant':
            model = event.get('message', {}).get('model')
            if model and model not in self.models:
                self.models.append(model)
        if t == 'result':
            if self.complete:
                self.failed = True
            self.complete = True; self.failed |= bool(event.get('is_error'))
            self.result_event = event
            if isinstance(event.get('result'), str):
                self.result = event['result']
        cleaned, n = public(event); self.omitted += n
        if not n:
            return line
        self.rewritten += 1
        return (json.dumps(cleaned, ensure_ascii=False) + '\n').encode() if cleaned is not None else b''

    def models_ok(self):
        return all(m in (self.requested_model, str(self.requested_model) + '[1m]') for m in self.models)

    def infrastructure_valid(self, code, timed_out):
        malformed_ok = self.malformed == 0 or (timed_out and self.malformed == 1 and self.last_malformed)
        return (self.expected_init is not None and self.init_count == 1 and not self.init_errors
                and self.models_ok() and (code == 0 or timed_out) and not self.failed
                and malformed_ok and (self.complete or timed_out)
                and not self.unknown and not self.foreign_user)

    def summary(self):
        return {'init_count': self.init_count, 'init_errors': self.init_errors, 'observed_models': self.models,
                'omitted_reasoning_events': self.omitted, 'rewritten_lines': self.rewritten,
                'malformed_events': self.malformed, 'lines': self.lines, 'unknown_event_types': self.unknown,
                'tool_uses': self.tools, 'result_event_seen': self.complete, 'result_is_error': self.failed,
                'foreign_user_blocks': self.foreign_user}


def run(argv, prompt, cwd, env, output, timeout, expected_init, requested_model):
    trace = Trace(expected_init, requested_model, prompt); expired = []
    with (output / 'stderr.txt').open('xb') as err, (output / 'public-events.jsonl').open('xb') as out:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=err, start_new_session=True)

        def stop():
            expired.append(True)
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        timer = threading.Timer(timeout, stop); timer.start()
        try:
            try:
                proc.stdin.write(prompt); proc.stdin.close()
            except BrokenPipeError:
                pass
            for line in proc.stdout:
                out.write(trace.line(line)); out.flush()
            code = proc.wait()
        finally:
            timer.cancel()
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
            proc.stdout.close()
    return trace, code, bool(expired)
