"""Offline regression probes; never call a model.

Adapted from experiments/transfer-1/harness/regressions.py (named check
functions that assert and return receipts) and test_harness.py (the scan
split-boundary fixture, now with this experiment's marker). New: init-policy
cases, the 4^3 decision table, Trace validity cases, environment whitelist,
public() filter, argv/profile shape and the store-canary wrapper. FIXTURE_INIT
is the init event observed from Claude Code 2.1.272 at the loopback stub
(cwd, ids and model neutralised) so the fast tests need no capture file.
"""
import copy
import hashlib
import itertools
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock
from common import write_json
from decision import CLASSES, NEXT_STEP, SCHEDULE, classify, decide
import events
import runtime

FIXTURE_INIT = {'type': 'system', 'subtype': 'init', 'cwd': '~/calib1-work/receivers/receiver-fixture',
                'session_id': '00000000-0000-4000-8000-000000000001', 'tools': ['Bash', 'Edit', 'Glob', 'Grep', 'Read', 'Write'],
                'mcp_servers': [], 'model': 'stand-in-model', 'permissionMode': 'dontAsk', 'slash_commands': [],
                'apiKeySource': 'ANTHROPIC_API_KEY', 'claude_code_version': '2.1.272', 'output_style': 'default',
                'agents': ['claude', 'Explore', 'general-purpose', 'Plan'], 'skills': [], 'plugins': [],
                'capabilities': ['interrupt_receipt_v1', 'interrupt_cancel_queued_v1', 'msg_lifecycle_v1'],
                'analytics_disabled': True, 'product_feedback_disabled': True,
                'uuid': '00000000-0000-4000-8000-000000000002', 'messaging_socket_path': '/tmp/cc-socks/1.sock',
                'fast_mode_state': 'off', 'fast_mode_disabled_reason': 'sdk_opt_in_required'}


def live_init(expected, model):
    base = copy.deepcopy(expected)
    base['model'] = model
    base['cwd'] = events.cwd_prefix() + 'receiver-abc123'
    return base


def init_policy_check(expected, model):
    base = live_init(expected, model)
    e = lambda event: events.init_errors(event, expected, model)  # noqa: E731
    cases = {
        'identical_live_init': e(base) == [],
        'extra_unknown_field': 'unexpected init field: brand_new_field' in e(dict(base, brand_new_field=1)),
        'socket_matching_pattern': e(dict(base, messaging_socket_path='/tmp/cc-socks/12345.sock')) == [],
        'socket_not_matching': 'messaging_socket_path unexpected' in e(dict(base, messaging_socket_path='/var/run/x.sock')),
        'socket_optional': e({k: v for k, v in base.items() if k != 'messaging_socket_path'}) == [],
        'model_mismatch': 'requested model mismatch' in e(dict(base, model='other-model')),
        'cwd_outside_receivers': 'cwd outside receivers' in e(dict(base, cwd='/private/tmp/receiver-x')),
        'missing_equal_field': 'missing init field: tools' in e({k: v for k, v in base.items() if k != 'tools'}),
        'changed_equal_field': 'init field changed: tools' in e(dict(base, tools=['Bash'])),
        'changed_version': 'init field changed: claude_code_version' in e(dict(base, claude_code_version='0.0.0')),
        'api_key_source_unexpected': 'apiKeySource unexpected' in e(dict(base, apiKeySource='apiKeyHelper')),
        'api_key_sources_accepted': all(e(dict(base, apiKeySource=s)) == [] for s in events.API_KEY_SOURCES),
        'record_only_may_differ': e(dict(base, skills=['x'], slash_commands=['y'], output_style='z')) == [],
        'bad_uuid': 'session_id is not a UUID' in e(dict(base, session_id='nope')),
        'not_init': 'not an init event' in e(dict(base, subtype='other')),
        'false_vs_zero_distinguished': 'init field changed: analytics_disabled' in e(dict(base, analytics_disabled=0)),
    }
    assert all(cases.values()), cases
    return {'pass': True, 'cases': cases}


def decision_check():
    counts = {}
    for triple in itertools.product(CLASSES, repeat=3):
        rows = [{'slot': i + 1, 'classification': c} for i, c in enumerate(triple)]
        for n in range(4):
            prefix = triple[:n]; d = decide(rows[:n])
            if 'INVALID' in prefix:
                assert d['status'] == 'INCOMPLETE' and d['next_step'].startswith('INVALID slot present')
            elif n < 3:
                assert d['status'] == 'CONTINUE' and d['next_step'] is None
            else:
                assert d['status'] == 'COMPLETE' and d['next_step'] == NEXT_STEP[prefix.count('PASS')]
                assert d['valid'] == 3
        counts[d['status']] = counts.get(d['status'], 0) + 1
    assert decide([])['status'] == 'CONTINUE'
    for bad in ([{'slot': 1, 'classification': 'PASS'}] * 4, [{'slot': 2, 'classification': 'PASS'}],
                [{'slot': 1, 'classification': 'BOGUS'}]):
        try:
            decide(bad)
        except ValueError:
            pass
        else:
            raise AssertionError('accepted ' + json.dumps(bad))
    assert classify(False, 'PASS') == 'INVALID' and classify(True, 'PARTIAL') == 'PARTIAL'
    for bad in ((True, 'BOGUS'), (True, 'INVALID'), ('yes', 'PASS')):
        try:
            classify(*bad)
        except ValueError:
            pass
        else:
            raise AssertionError('classified ' + repr(bad))
    assert len(SCHEDULE) == 3
    return {'pass': True, 'triples': 64, 'status_counts': counts, 'order': 'INVALID > PASS > FAIL > PARTIAL'}


def stream(expected, model, *, thinking=True, error=False, second_init=False, model_seen=None, truncate=False, junk=False):
    init = live_init(expected, model)
    assistant = {'type': 'assistant', 'message': {'model': model_seen or model, 'content': [
        {'type': 'thinking', 'thinking': 'private', 'signature': 'sig'}, {'type': 'text', 'text': 'answer'}]}}
    if not thinking:
        assistant['message']['content'] = assistant['message']['content'][1:]
    result = {'type': 'result', 'subtype': 'error' if error else 'success', 'is_error': error, 'result': 'final text'}
    lines = [init, assistant] + ([init] if second_init else []) + [result]
    raw = [(json.dumps(x) + '\n').encode() for x in lines]
    if junk:
        raw.insert(1, b'not json\n')
    if truncate:
        raw.append(b'{"type":"assistant","message":{"mo')
    return raw


def feed(expected, model, lines):
    trace = events.Trace(expected, model)
    out = b''.join(trace.line(line) for line in lines)
    return trace, out


def trace_check(expected, model):
    cases = {}
    t, out = feed(expected, model, stream(expected, model))
    cases['normal_valid'] = t.infrastructure_valid(0, False) and t.result == 'final text' and t.omitted == 1 and t.rewritten == 1
    cases['thinking_removed_from_public'] = b'private' not in out and b'"signature"' not in out and b'answer' in out
    t, _ = feed(expected, model, stream(expected, model, truncate=True))
    cases['kill_truncated_last_line_valid'] = t.infrastructure_valid(-9, True) and t.malformed == 1
    cases['truncated_without_timeout_invalid'] = not t.infrastructure_valid(0, False)
    t, _ = feed(expected, model, stream(expected, model, junk=True))
    cases['malformed_middle_invalid_even_on_timeout'] = not t.infrastructure_valid(-9, True)
    t, _ = feed(expected, model, stream(expected, model, error=True))
    cases['is_error_result_invalid'] = not t.infrastructure_valid(0, False)
    t, _ = feed(expected, model, stream(expected, model, second_init=True))
    cases['second_init_invalid'] = not t.infrastructure_valid(0, False) and t.init_count == 2
    t, _ = feed(expected, model, stream(expected, model, model_seen=model + '[1m]'))
    cases['1m_suffix_accepted'] = t.infrastructure_valid(0, False)
    t, _ = feed(expected, model, stream(expected, model, model_seen='other'))
    cases['other_model_invalid'] = not t.infrastructure_valid(0, False)
    t, _ = feed(expected, model, stream(expected, model)[:2])
    cases['no_result_without_timeout_invalid'] = not t.infrastructure_valid(0, False)
    cases['no_result_with_timeout_valid'] = t.infrastructure_valid(-9, True)
    cases['nonzero_exit_without_timeout_invalid'] = not feed(expected, model, stream(expected, model))[0].infrastructure_valid(1, False)
    t, _ = feed(expected, model, [json.dumps(dict(live_init(expected, model), extra=1)).encode() + b'\n'])
    cases['init_policy_error_invalid'] = bool(t.init_errors) and not t.infrastructure_valid(0, True)
    assert all(cases.values()), cases
    return {'pass': True, 'cases': cases}


def overwrite_check():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / 'receipt.json'; write_json(path, {'first': True})
        try:
            write_json(path, {'first': False})
        except FileExistsError:
            pass
        else:
            raise AssertionError('receipt overwritten')
        assert json.loads(path.read_text())['first']
    return {'pass': True}


def scan_boundary_check():
    from tmp_scan import SCANNER, MARKERS
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / 'one').write_bytes(b'a' * (1024 * 1024 - 4) + b'CALIB-MYC-1')
        (root / 'two').write_bytes(b'no marker here')
        (root / 'three').write_bytes(b'S-VERIF-7 mentioned')
        (root / 'four').write_bytes(b'nothing of interest')
        request = {'roots': [td], 'markers_hex': [m.hex() for m in MARKERS],
                   'digests': [hashlib.sha256(b'no marker here').hexdigest()]}
        result = subprocess.run([sys.executable, '-I', '-c', SCANNER], input=json.dumps(request),
                                text=True, capture_output=True, check=True, timeout=30)
        report = json.loads(result.stdout)
        assert {Path(x['path']).name for x in report['matches']} == {'one', 'two', 'three'}, report
        assert report['errors'] == [] and report['files_read'] == 4
    return {'pass': True, 'split_boundary_marker': True, 'digest_only_match': True, 'case_insensitive': True}


def public_filter_check():
    event = {'type': 'assistant', 'message': {'content': [{'type': 'thinking', 'thinking': 'x'}, {'type': 'text', 'text': 'y', 'signature': 's'}]}}
    cleaned, n = events.public(event)
    assert n == 2 and cleaned == {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'y'}]}}
    assert events.public({'type': 'result', 'result': 'ok'}) == ({'type': 'result', 'result': 'ok'}, 0)
    return {'pass': True}


def environment_check():
    poisoned = dict(os.environ, ANTHROPIC_API_KEY='leak', ANTHROPIC_BASE_URL='leak', CLAUDE_CODE_FOO='leak',
                    CLAUDE_CONFIG_DIR='leak', TMPDIR='/leak', GIT_CONFIG_GLOBAL='/leak')
    with mock.patch.dict(os.environ, poisoned, clear=True):
        env = runtime.environment()
    assert not any(k.startswith('ANTHROPIC_') for k in env)
    assert {k for k in env if k.startswith('CLAUDE_')} == {k for k in runtime.FLAGS if k.startswith('CLAUDE_')}
    assert 'TMPDIR' not in env and env['GIT_CONFIG_GLOBAL'] == os.devnull and env['GIT_AUTHOR_NAME'] == 'CALIB fixture'
    assert env['MAX_THINKING_TOKENS'] == '0' and env['DISABLE_AUTOUPDATER'] == '1'
    assert set(env) <= set(runtime.KEEP) | set(runtime.FLAGS) | {k for k in env if k.startswith('GIT_')}
    return {'pass': True, 'keys': sorted(env)}


def argv_check(model):
    argv = runtime.invocation('/x', model)
    for flag in ('-p', '--safe-mode', '--no-session-persistence', '--disable-slash-commands', '--strict-mcp-config', '--verbose'):
        assert flag in argv
    assert argv[argv.index('--setting-sources') + 1] == '' and argv[argv.index('--permission-mode') + 1] == 'dontAsk'
    assert argv[argv.index('--settings') + 1] == runtime.SETTINGS and argv[argv.index('--model') + 1] == model
    assert argv[argv.index('--tools') + 1] == runtime.TOOLS and argv[argv.index('--output-format') + 1] == 'stream-json'
    assert argv[argv.index('--system-prompt') + 1] == runtime.SYSTEM and 'Black' not in runtime.SYSTEM
    assert runtime.UUID.match(argv[argv.index('--session-id') + 1])
    assert runtime.argv_template(model) == runtime.argv_template(model) and '<UUID4>' in runtime.argv_template(model)
    for bad in ('', ' ', None):
        try:
            runtime.invocation('/x', bad)
        except ValueError:
            pass
        else:
            raise AssertionError('accepted empty model')
    try:
        runtime.profile('/private/tmp/receiver-outside')
    except ValueError:
        pass
    else:
        raise AssertionError('profile accepted a root outside receivers')
    return {'pass': True}


def sandbox_canary_check(snapshot, run_root):
    canary = runtime.store_canary(snapshot, run_root)
    assert canary['pass'], canary['observed']
    return canary
