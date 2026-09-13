"""Offline controls for CM-3 preparation. Never launch a model or provider call."""
import copy
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent / 'examples/model-experience/cm3'


def module(name):
    spec = importlib.util.spec_from_file_location('cm3_' + name, HERE / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class ContextBoundaryTest(unittest.TestCase):
    def setUp(self):
        self.client = module('claude_session')
        self.body = {'system': [{'type': 'text', 'text': self.client.SYSTEM}],
                     'messages': [{'role': 'user', 'content': [{'type': 'text', 'text': 'approved prompt'}]}],
                     'tools': [{'name': 'Bash'}], 'thinking': {'type': 'disabled'}}

    def check(self, body):
        return self.client.check_context(body, 'approved prompt', ['python3 receiver_check.py'])

    def test_client_memory_text_is_removed_from_actual_forwarded_body(self):
        self.body['messages'][0]['content'].insert(0, {'type': 'text', 'text': 'PRIVATE prior project memory'})
        self.body['messages'].extend([
            {'role': 'assistant', 'content': [{'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'python3 receiver_check.py'}}]},
            {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': 'x', 'content': 'approved output'},
                                         {'type': 'text', 'text': 'PRIVATE later memory'}]},
        ])
        audit = self.check(self.body)
        self.assertNotIn('PRIVATE', json.dumps(self.body))
        self.assertNotIn('PRIVATE', json.dumps(audit))
        self.assertEqual(len(audit['removed_client_text_sha256']), 2)
        self.assertEqual(self.body['messages'][-1]['content'][0]['content'], 'approved output')

    def test_unexpected_system_tool_command_and_thinking_refuse(self):
        cases = []
        b = copy.deepcopy(self.body); b['system'].append({'type': 'text', 'text': 'private memory'}); cases.append(b)
        b = copy.deepcopy(self.body); b['tools'].append({'name': 'Read'}); cases.append(b)
        b = copy.deepcopy(self.body); b['thinking'] = {'type': 'enabled'}; cases.append(b)
        b = copy.deepcopy(self.body); b['messages'].append({'role': 'assistant', 'content': [{'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'cat ~/.claude/CLAUDE.md'}}]}); cases.append(b)
        for b in cases:
            with self.subTest(body=b):
                with self.assertRaises(ValueError):
                    self.check(b)


class DifferentialTest(unittest.TestCase):
    def test_advice_patch_has_measured_order_specific_failure_and_no_overwrite(self):
        self.exercise(False)

    def test_noncausal_patch_cannot_pass_the_differential(self):
        self.exercise(True)

    def exercise(self, neutral_patch):
        with tempfile.TemporaryDirectory() as parent:
            root = Path(parent) / 'receiver'
            module('prepare_receiver').prepare(root)
            if neutral_patch:
                original = (root / 'warrant_kernel.py').read_text(encoding='utf-8')
                changed = original.replace('unsettled = []', 'unsettled = list()')
                patch = ''.join(difflib.unified_diff(original.splitlines(True), changed.splitlines(True), fromfile='a/warrant_kernel.py', tofile='b/warrant_kernel.py'))
                (root / 'advice.patch').write_text(patch, encoding='utf-8')
                m = json.loads((root / 'source-manifest.json').read_text(encoding='utf-8'))
                m['files']['advice.patch'] = hashlib.sha256(patch.encode()).hexdigest()
                (root / 'source-manifest.json').write_text(json.dumps(m), encoding='utf-8')
            before = (root / 'warrant_kernel.py').read_bytes()
            r = subprocess.run([sys.executable, 'receiver_check.py'], cwd=root, capture_output=True)
            self.assertEqual(r.returncode, 1 if neutral_patch else 0, r.stderr)
            report = json.loads((root / 'run.json').read_text(encoding='utf-8'))
            self.assertEqual(report['expected_differential_observed'], not neutral_patch)
            self.assertEqual(report['baseline']['measurement']['failures'], [])
            self.assertEqual(len(report['advice_applied']['measurement']['failures']), 0 if neutral_patch else 1)
            self.assertEqual((root / 'warrant_kernel.py').read_bytes(), before)
            saved = (root / 'run.json').read_bytes()
            repeat = subprocess.run([sys.executable, 'receiver_check.py'], cwd=root, capture_output=True)
            self.assertEqual(repeat.returncode, 2)
            self.assertEqual((root / 'run.json').read_bytes(), saved)


class SavedExchangeTest(unittest.TestCase):
    def test_response_roundtrip_context_and_original_packets(self):
        result = module('verify_saved').verify()
        self.assertTrue(result['ok'])
        self.assertEqual(result['records_found'], 3)
        self.assertFalse(result['model_invoked'])


if __name__ == '__main__':
    unittest.main()
