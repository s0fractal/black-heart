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
            report = C.run([self.ledger], self.cache)
            self.assertEqual(report['status'], 'INCOMPLETE')
            self.assertEqual(report['items'][0]['status'], 'UNRESOLVED')
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

    def test_mixed_batch_preserves_order_and_refusals(self):
        unknown = self.root / 'unknown.pdf'
        unknown.write_bytes(b'unsupported')
        missing = self.root / 'missing.pdf'
        with patch.object(C, 'execute', wraps=C.execute) as execute:
            report = C.run([unknown, self.ledger, missing], self.cache, batch=True)
            self.assertEqual(execute.call_count, 1)
            self.assertEqual(report['status'], 'INCOMPLETE')
            self.assertEqual([i['path'] for i in report['items']], list(map(str, [unknown, self.ledger, missing])))
            self.assertEqual([i['origin'] for i in report['items']], ['NOT_RUN', 'EXECUTED_NOW', 'NOT_RUN'])
            again = C.run([unknown, self.ledger, missing], self.cache, batch=True)
            self.assertEqual(again['items'][1]['origin'], 'REUSED')
            self.assertEqual(execute.call_count, 1)
            self.assertTrue(all('result' not in again['items'][i] for i in (0, 2)))

    def test_all_unsupported_batch_does_not_touch_cache(self):
        with patch.object(C, 'snapshot') as snapshot:
            r = C.run([self.root/'missing.pdf'], self.cache, batch=True)
            self.assertEqual(r['status'], 'INCOMPLETE')
            snapshot.assert_not_called()
        self.assertFalse(self.cache.exists())

    def test_strict_mixed_request_still_refuses_before_execution(self):
        with patch.object(C, 'execute') as execute:
            with self.assertRaises(OSError):
                C.run([self.ledger, self.root/'missing.pdf'], self.cache)
            execute.assert_not_called()
        self.assertFalse(self.cache.exists())

    def test_batch_cli_nonzero_despite_supported_success(self):
        unknown = self.root/'unknown.pdf'
        unknown.write_bytes(b'unknown')
        p = subprocess.run([sys.executable, '-B', str(C.ROOT/'tools/verify_cached.py'),
                            '--batch', '--cache', str(self.cache), str(self.ledger), str(unknown)],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 2, p.stderr)
        report = json.loads(p.stdout)
        self.assertEqual(report['status'], 'INCOMPLETE')
        self.assertEqual(report['items'][0]['result']['exit_code'], 0)
        self.assertEqual(report['items'][1]['origin'], 'NOT_RUN')

    def test_fresh_process_restart_repair_and_cache_loss(self):
        path = self.root / 'subject.pdf'
        original = self.ledger.read_bytes()
        path.write_bytes(original)
        def invoke(code, origin=None, cache=None):
            p = subprocess.run([sys.executable, '-B', str(C.ROOT/'tools/verify_cached.py'),
                                '--cache', str(cache or self.cache), str(path)],
                               capture_output=True, text=True, timeout=30)
            self.assertEqual(p.returncode, code, p.stderr + p.stdout)
            report = json.loads(p.stdout)
            if origin:
                self.assertEqual(report['items'][0]['origin'], origin)
            else:
                self.assertEqual(report['status'], 'REFUSED')
                self.assertNotIn('items', report)
            return report
        invoke(0, 'EXECUTED_NOW')
        invoke(0, 'REUSED')
        prefix = '%🖤 LEDGER_MANIFEST: '.encode()
        rows = original.splitlines(keepends=True)
        for i, row in enumerate(rows):
            if row.startswith(prefix):
                obj = json.loads(row[len(prefix):])
                obj['chain_tip'] = '0' * 64
                rows[i] = prefix + json.dumps(obj).encode() + b'\n'
        path.write_bytes(b''.join(rows))
        rejected = invoke(1, 'EXECUTED_NOW')
        self.assertIn('LEDGER_TIP', rejected['items'][0]['result']['stdout'])
        invoke(1, 'REUSED')
        path.write_bytes(original + b'\n% repair control\n')
        invoke(0, 'EXECUTED_NOW')
        invoke(0, 'REUSED')
        entries = C.read_cache(self.cache)['entries']
        self.assertEqual(sorted(e['result']['exit_code'] for e in entries.values()), [0, 0, 1])
        self.cache.unlink()
        invoke(0, 'EXECUTED_NOW')
        self.cache.write_bytes(b'{broken')
        invoke(2)
        self.assertEqual(self.cache.read_bytes(), b'{broken')
        invoke(0, 'EXECUTED_NOW', self.root/'replacement.json')


if __name__ == '__main__':
    unittest.main()
