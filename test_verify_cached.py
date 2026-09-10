import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools import verify_cached as C


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cache = self.root / 'cache.json'
        self.ledger = C.ROOT / 'examples/living_ledger.pdf'

    def test_real_reuse_changed_operand_and_fresh(self):
        with patch.object(C, 'execute', wraps=C.execute) as execute:
            first = C.run([self.ledger], self.cache)
            self.assertEqual(first['items'][0]['result']['exit_code'], 0)
            warm = C.run([self.ledger], self.cache)
            self.assertEqual(warm['items'][0]['origin'], 'REUSED')
            self.assertEqual(warm['items'][0]['result'], first['items'][0]['result'])
            self.assertEqual(execute.call_count, 1)
            forced = C.run([self.ledger], self.cache, fresh=True)
            self.assertEqual(forced['items'][0]['origin'], 'EXECUTED_NOW')
            self.assertEqual(execute.call_count, 2)
            raw = self.ledger.read_bytes()
            prefix = '%🖤 LEDGER_MANIFEST: '.encode()
            lines = raw.splitlines(keepends=True)
            for i, line in enumerate(lines):
                if line.startswith(prefix):
                    obj = json.loads(line[len(prefix):])
                    obj['chain_tip'] = '0' * 64
                    lines[i] = prefix + json.dumps(obj).encode() + b'\n'
            changed = self.root / self.ledger.name
            changed.write_bytes(b''.join(lines))
            result = C.run([changed], self.cache)['items'][0]
            self.assertEqual(result['origin'], 'EXECUTED_NOW')
            self.assertEqual(result['result']['exit_code'], 1)
            self.assertIn('LEDGER_TIP', result['result']['stdout'])
            self.assertEqual(execute.call_count, 3)

    def test_same_basename_different_paths_preserved(self):
        other = self.root / self.ledger.name
        other.write_bytes(self.ledger.read_bytes())
        r = C.run([self.ledger, other], self.cache)
        self.assertEqual(len(r['items']), 2)
        self.assertNotEqual(r['items'][0]['path'], r['items'][1]['path'])
        self.assertEqual([i['origin'] for i in r['items']], ['EXECUTED_NOW', 'REUSED'])

    def test_corrupt_cache_no_execution_or_overwrite(self):
        for raw in (b'{', b'[]', b'{"schema":true,"entries":{}}'):
            self.cache.write_bytes(raw)
            with patch.object(C, 'execute') as execute:
                with self.assertRaises((ValueError, TypeError)):
                    C.run([self.ledger], self.cache)
                execute.assert_not_called()
            self.assertEqual(self.cache.read_bytes(), raw)

    def test_entry_checksum_and_shape(self):
        result = {'exit_code': 0, 'stdout': '', 'stderr': '', 'state': 'COMPLETED'}
        valid = {'schema': 1, 'entries': {'a'*64: {'result': result, 'sha256': C.digest(C.encode(result))}}}
        altered = copy.deepcopy(valid)
        altered['entries']['a'*64]['result']['exit_code'] = 1
        self.cache.write_bytes(C.encode(altered))
        with self.assertRaisesRegex(ValueError, 'CACHE_CHECKSUM'):
            C.read_cache(self.cache)
        altered = copy.deepcopy(valid)
        altered['entries']['a'*64]['result']['exit_code'] = True
        self.cache.write_bytes(C.encode(altered))
        with self.assertRaisesRegex(ValueError, 'CACHE_RESULT'):
            C.read_cache(self.cache)

    def test_source_profile_invalidates_and_captured_bytes_execute(self):
        C.run([self.ledger], self.cache)
        files, profile = C.snapshot()
        files['artifact_audit.py'] += b'\n# harmless local test\n'
        with patch.object(C, 'snapshot', return_value=(files, 'changed-profile')):
            with patch.object(C, 'execute', wraps=C.execute) as execute:
                r = C.run([self.ledger], self.cache)
                self.assertEqual(r['items'][0]['origin'], 'EXECUTED_NOW')
                self.assertEqual(execute.call_args.args[0]['artifact_audit.py'], files['artifact_audit.py'])

    def test_timeout_not_cached(self):
        timeout = {'exit_code': None, 'stdout': '', 'stderr': '', 'state': 'TIMEOUT'}
        with patch.object(C, 'execute', return_value=timeout) as execute:
            C.run([self.ledger], self.cache)
            C.run([self.ledger], self.cache)
            self.assertEqual(execute.call_count, 2)
        self.assertFalse(C.read_cache(self.cache)['entries'])

    def test_actual_source_bytes_change_profile(self):
        source = self.root / 'sample.py'
        source.write_bytes(b'x = 1\n')
        with patch.object(C, 'ROOT', self.root):
            _, before = C.snapshot()
            source.write_bytes(b'x = 2\n')
            files, after = C.snapshot()
        self.assertNotEqual(before, after)
        self.assertEqual(files['sample.py'], b'x = 2\n')

    def test_child_uses_captured_operand_after_original_changes(self):
        path = self.root / 'input.pdf'
        original = self.ledger.read_bytes()
        path.write_bytes(original)
        execute = C.execute
        def replace_original(source, raw, timeout):
            path.write_bytes(b'changed after capture')
            return execute(source, raw, timeout)
        with patch.object(C, 'execute', side_effect=replace_original):
            result = C.run([path], self.cache)['items'][0]
        self.assertEqual(result['operand_sha256'], C.digest(original))
        self.assertEqual(result['result']['exit_code'], 0)

    def test_empty_request_and_operand_cache_collision(self):
        with self.assertRaisesRegex(ValueError, 'NO_OPERANDS'):
            C.run([], self.cache)
        with self.assertRaisesRegex(ValueError, 'CACHE_PATH'):
            C.run([self.ledger], self.ledger)

    def test_failed_replace_preserves_cache(self):
        original = {'schema': 1, 'entries': {}}
        C.save_cache(self.cache, original)
        before = self.cache.read_bytes()
        with patch.object(C.os, 'replace', side_effect=OSError('injected')):
            with self.assertRaises(OSError):
                C.save_cache(self.cache, original)
        self.assertEqual(self.cache.read_bytes(), before)
        self.assertFalse(list(self.root.glob('.verify-cache-*')))

    def test_other_process_lock_refuses(self):
        path = self.cache.parent / (self.cache.name + '.lock')
        code = "import fcntl,sys; f=open(sys.argv[1],'a+b'); fcntl.flock(f,fcntl.LOCK_EX); print('ready',flush=True); sys.stdin.readline()"
        child = subprocess.Popen([sys.executable, '-c', code, str(path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'ready')
            with self.assertRaisesRegex(ValueError, 'BUSY'):
                C.run([self.ledger], self.cache)
            self.assertFalse(self.cache.exists())
        finally:
            child.communicate('\n', timeout=5)

    def test_unsupported_route_refuses_before_cache_creation(self):
        path = self.root / 'unknown.pdf'
        path.write_bytes(b'# %COLONY_MANIFEST: {}\n')
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_ROUTE'):
            C.run([path], self.cache)
        self.assertFalse(self.cache.exists())

    def test_json_cli_and_exit_status(self):
        result = subprocess.run([sys.executable, '-B', str(C.ROOT/'tools/verify_cached.py'),
                                 '--cache', str(self.cache), str(self.ledger)], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['items'][0]['origin'], 'EXECUTED_NOW')


if __name__ == '__main__':
    unittest.main()
