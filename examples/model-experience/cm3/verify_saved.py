#!/usr/bin/env python3
"""Verify saved CM-3 artifacts and CM-2 roundtrip offline. No model or replay."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import experience


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify():
    out = HERE / 'exchange'
    prep = experience.parse((out / 'preparation.json').read_bytes())
    for name, digest in experience.parse((out / 'prelaunch-sha256.json').read_bytes()).items():
        assert Path(name).name == name and sha((out / name).read_bytes()) == digest, name
    events = [experience.parse(line) for line in (out / 'stdout.jsonl').read_bytes().splitlines()]
    result, = [e for e in events if e['type'] == 'result']
    assert result['subtype'] == 'success' and not result['is_error'] and not result['permission_denials']
    raw = (out / 'response.json').read_bytes()
    assert raw == result['result'].encode('utf-8')
    experience.validate(raw)
    audit = experience.parse((out / 'session-audit.json').read_bytes())
    assert audit['live'] and audit['exit_code'] == 0 and not audit['context_refusals']
    assert audit['stdout_byte_identical'] and audit['hidden_reasoning_lines_omitted'] == 0
    contexts = experience.parse((out / 'request-context.json').read_bytes())
    spec = importlib.util.spec_from_file_location('cm3_context_boundary', HERE / 'claude_session.py')
    boundary = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(boundary)
    assert len(contexts) == audit['provider_requests'] == audit['observed_requests']
    with tempfile.TemporaryDirectory() as td:
        objects = Path(td) / 'snapshot'
        objects.mkdir()
        def git(*args):
            return subprocess.check_output(['git', '-C', str(objects), *args], stderr=subprocess.PIPE)
        git('-c', 'init.templateDir=', 'init', '-q')
        git('fetch', '-q', str(out / 'receiver-snapshot.bundle'), 'HEAD')
        assert git('rev-parse', 'FETCH_HEAD').decode().strip() == prep['snapshot_head']
        def blob(name):
            return git('show', prep['snapshot_head'] + ':' + name)
        prompt = blob('receiver-prompt.txt').decode('utf-8')
        assert sha(prompt.encode()) == prep['prompt_sha256']
        manifest_raw = (out / 'source-manifest.json').read_bytes()
        assert manifest_raw == blob('source-manifest.json')
        assert sha(manifest_raw) == prep['source_manifest_sha256']
        manifest = experience.parse(manifest_raw)
        for name, digest in manifest['files'].items():
            assert Path(name).name == name and sha(blob(name)) == digest, name
        commands = [line for line in prompt.splitlines() if line.startswith(('python3 ', 'cat '))]
        for context in contexts:
            boundary.check_context({'system': context['system'],
                                    'messages': [{'role': 'user', 'content': context['initial_user_content']}],
                                    'tools': context['tools']}, prompt, commands)
            assert context['initial_user_content'] == [{'type': 'text', 'text': prompt}]
            assert [t['name'] for t in context['tools']] == ['Bash']
        commands = [line for line in prompt.splitlines() if line.startswith(('python3 ', 'cat '))]
        observed = []
        for event in events:
            for block in event.get('message', {}).get('content', []):
                assert block.get('type') not in ('thinking', 'redacted_thinking')
                if block.get('type') == 'tool_use':
                    assert block['name'] == 'Bash'
                    observed.append(block['input']['command'])
        assert sorted(observed) == sorted(commands)
        store = Path(td) / 'store'
        store.mkdir()
        for address in prep['record_addresses']:
            experience.hex_value(address, 64, 'address')
            (store / (address + '.json')).write_bytes(blob('store/' + address + '.json'))
            experience.read(store, address)
        before = {p.name: p.read_bytes() for p in store.iterdir()}
        saved = experience.save(out / 'response.json', store, ROOT)
        assert experience.read(store, saved['address'])[0] == raw
        assert all((store / name).read_bytes() == original for name, original in before.items())
        found = experience.search(store, component='EMPIRICAL')
        assert found['ok'] and len(found['matches']) == 3
    run = experience.parse((out / 'run.json').read_bytes())
    assert run['checkout_before']['head'].strip() == prep['snapshot_head']
    assert run['checkout_before']['status_porcelain'] == ''
    baseline, advice = run['baseline'], run['advice_applied']
    assert baseline['exit_code'] == 0 and advice['exit_code'] == 1
    assert baseline['measurement']['tests_run'] == advice['measurement']['tests_run'] == 3
    assert not baseline['measurement']['failures'] and not baseline['measurement']['errors']
    assert len(advice['measurement']['failures']) == 1 and not advice['measurement']['errors']
    assert [v['verdict'] for v in baseline['measurement']['fixture_orders']] == ['fail', 'fail']
    assert [v['verdict'] for v in advice['measurement']['fixture_orders']] == ['unverified', 'fail']
    return {'ok': True, 'operation': 'VERIFY_SAVED_EXCHANGE', 'response_sha256': sha(raw),
            'records_found': 3, 'predecessors_preserved': True, 'model_invoked': False,
            'evidence_replayed_by_this_reader': False,
            'scope': 'Artifact correspondence and scoped report consistency, not authenticated model identity or general advice truth.'}


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
