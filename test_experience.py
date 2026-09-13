"""Behavioral CM-2 checks over real DOC-F1 bytes; disagreement is a control."""
import base64
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import experience as ex

ROOT = Path(__file__).resolve().parent
DOC = ROOT / 'examples/model-experience/doc-f1'
CM1 = '91e1fd393a36bac73edc305b17ddf55a8254b8c8'


class ExperienceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Real integration requires the pinned historical Git objects; never fetch.
        cls.history_available = subprocess.run(
            ['git', 'cat-file', '-e', CM1 + '^{commit}'], cwd=ROOT,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.store = self.base / 'store'
        self.packet = self.base / 'input'
        shutil.copytree(DOC, self.packet)
        self.record = self.packet / 'experience.json'
        self.raw = self.record.read_bytes()
        self.r = json.loads(self.raw)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'experience.py'), *map(str, args),
                               '--store', str(self.store)], capture_output=True, cwd=ROOT)

    def save(self):
        return ex.save(self.record, self.store, ROOT)

    def write(self, record):
        self.record.write_text(json.dumps(record, ensure_ascii=False), encoding='utf-8')

    def require_history(self):
        if not self.history_available:
            self.fail('real historical Git objects unavailable; use a full clone (CI fetch-depth: 0)')

    def test_real_save_read_search_portable_snapshot(self):
        self.require_history()
        saved = self.cli('save', self.record, '--repo', ROOT)
        self.assertEqual(saved.returncode, 0, saved.stderr)
        address = json.loads(saved.stdout)['address']
        self.assertEqual(address, ex.digest(self.raw))
        self.assertEqual(self.cli('read', address, '--raw').stdout, self.raw)
        self.assertEqual(self.cli('verify', address).returncode, 0)
        for query in [('search', '--task', 'suspended'), ('search', '--component', 'EMPIRICAL')]:
            result = self.cli(*query)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)['matches'][0]['address'], address)
        self.assertEqual(json.loads(self.cli('search', '--task', 'nonexistent').stdout)['matches'], [])
        # Retrieval uses the saved evidence, even when the input disappears.
        shutil.rmtree(self.packet)
        with mock.patch.object(subprocess, 'run', side_effect=AssertionError('no Git or runner on read')):
            self.assertEqual(ex.read(self.store, address)[0], self.raw)
        packet = json.loads((self.store / (address + '.json')).read_text(encoding='utf-8'))
        self.assertEqual(base64.b64decode(packet['sources']['replay']), (DOC / 'replay.json').read_bytes())

    def test_refusals_before_writes(self):
        cases = []
        r = copy.deepcopy(self.r); r['profile'] = 'other'; cases.append((r, 'UNSUPPORTED_PROFILE'))
        r = copy.deepcopy(self.r); del r['task']['applicability']; cases.append((r, 'FIELD_MISSING'))
        r = copy.deepcopy(self.r); r['observations'][0]['evidence_ids'] = ['absent']; cases.append((r, 'MISSING_SOURCE'))
        r = copy.deepcopy(self.r); r['evidence'][-1]['path'] = '../secret'; cases.append((r, 'UNSAFE_PATH'))
        r = copy.deepcopy(self.r); r['evidence'][0]['commit'] = '--help'; cases.append((r, 'INVALID_COMMIT'))
        r = copy.deepcopy(self.r); r['relations'] = [{}]; cases.append((r, 'FIELD_MISSING'))
        r = copy.deepcopy(self.r); r['attempt']['argv'] = [3]; cases.append((r, 'FIELD_TYPE'))
        r = copy.deepcopy(self.r); r['evidence'][0]['kind'] = []; cases.append((r, 'UNSUPPORTED_KIND'))
        for record, code in cases:
            with self.subTest(code=code):
                self.write(record)
                result = self.cli('save', self.record, '--repo', ROOT)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(json.loads(result.stderr)['refusal'], code)
                self.assertFalse(self.store.exists())

    def test_duplicate_keys_and_invalid_utf8(self):
        for raw, code in [(b'{"profile": "x", "profile": "y"}', 'DUPLICATE_KEY'),
                          (b'{"x": {"k": 1, "k": 2}}', 'DUPLICATE_KEY'),
                          (b'\xff', 'INVALID_UTF8'), (b'{"x": NaN}', 'INVALID_JSON')]:
            self.record.write_bytes(raw)
            result = self.cli('save', self.record, '--repo', ROOT)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stderr)['refusal'], code)
            self.assertEqual(self.record.read_bytes(), raw)

    def file_only(self):
        self.r['evidence'] = [self.r['evidence'][-1]]
        self.r['observations'] = [self.r['observations'][2]]
        self.write(self.r)

    def test_missing_tampered_and_symlink_source(self):
        self.file_only()
        source = self.packet / 'replay.json'
        source.unlink()
        result = self.cli('save', self.record, '--repo', ROOT)
        self.assertEqual(json.loads(result.stderr)['refusal'], 'MISSING_SOURCE')
        source.write_bytes(b'changed')
        result = self.cli('save', self.record, '--repo', ROOT)
        self.assertEqual(json.loads(result.stderr)['refusal'], 'DIGEST_MISMATCH')
        source.unlink(); source.symlink_to(DOC / 'replay.json')
        result = self.cli('save', self.record, '--repo', ROOT)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.store.exists())
        source.unlink()
        (self.packet / 'link').symlink_to(DOC, target_is_directory=True)
        self.r['evidence'][0]['path'] = 'link/replay.json'
        self.write(self.r)
        self.assertEqual(self.cli('save', self.record, '--repo', ROOT).returncode, 2)

    def test_saved_corruption_visible_to_read_and_search(self):
        self.file_only()
        address = self.save()['address']
        path = self.store / (address + '.json')
        original = path.read_bytes()
        p = json.loads(original)
        p['sources']['replay'] = ex.encode(b'changed')
        path.write_text(json.dumps(p), encoding='utf-8')
        for operation in ['read', 'verify']:
            result = self.cli(operation, address)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stderr)['refusal'], 'DIGEST_MISMATCH')
        result = self.cli('search', '--task', 'irrelevant')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(len(json.loads(result.stdout)['errors']), 1)
        p['record'] = ex.encode(b'{}')
        path.write_text(json.dumps(p), encoding='utf-8')
        self.assertEqual(json.loads(self.cli('read', address).stderr)['refusal'], 'DIGEST_MISMATCH')
        path.write_bytes(original)
        (self.store / '.experience-interrupted').write_bytes(b'partial')
        self.assertEqual(self.cli('search').returncode, 2)

    def test_no_clobber_retry_and_publication_race(self):
        self.file_only()
        address = self.save()['address']
        target = self.store / (address + '.json')
        original = target.read_bytes()
        self.assertEqual(json.loads(self.cli('save', self.record, '--repo', ROOT).stderr)['refusal'], 'OUTPUT_EXISTS')
        self.assertEqual(target.read_bytes(), original)
        target.unlink()
        link = ex.os.link
        def race(source, destination):
            Path(destination).write_bytes(b'other writer')
            return link(source, destination)
        with mock.patch.object(ex.os, 'link', side_effect=race):
            with self.assertRaisesRegex(ex.Refusal, str(target)):
                self.save()
        self.assertEqual(target.read_bytes(), b'other writer')

    def test_publication_failure_and_cleanup_outcome(self):
        self.file_only()
        with mock.patch.object(ex.os, 'link', side_effect=OSError('injected publication failure')):
            with self.assertRaises(OSError):
                self.save()
        self.assertEqual(list(self.store.iterdir()), [])
        with mock.patch.object(ex.os, 'unlink', side_effect=OSError('injected cleanup failure')):
            result = self.save()
        self.assertTrue(result['ok'])
        self.assertFalse(result['cleanup_complete'])
        self.assertEqual(ex.read(self.store, result['address'])[0], self.record.read_bytes())
        self.assertEqual(self.cli('search').returncode, 2)

    def test_size_limits_and_wrong_source_type(self):
        self.file_only()
        source = self.packet / 'replay.json'
        with mock.patch.object(ex, 'MAX_SOURCE', 1):
            with self.assertRaises(ex.Refusal) as error:
                self.save()
        self.assertEqual(error.exception.code, 'TOO_LARGE')
        source.unlink()
        source.mkdir()
        self.assertEqual(self.cli('save', self.record, '--repo', ROOT).returncode, 2)
        self.assertFalse(self.store.exists())

    def test_missing_packet_source_and_symlink_destination(self):
        self.file_only()
        address = self.save()['address']
        path = self.store / (address + '.json')
        packet = json.loads(path.read_bytes())
        del packet['sources']['replay']
        path.write_text(json.dumps(packet), encoding='utf-8')
        self.assertEqual(json.loads(self.cli('read', address).stderr)['refusal'], 'MISSING_SOURCE')
        path.unlink()
        sentinel = self.base / 'sentinel'
        sentinel.write_bytes(b'existing bytes')
        path.symlink_to(sentinel)
        self.assertEqual(self.cli('save', self.record, '--repo', ROOT).returncode, 2)
        self.assertEqual(sentinel.read_bytes(), b'existing bytes')
        self.assertEqual(self.cli('read', address).returncode, 2)

    def test_untrusted_argv_is_data(self):
        self.file_only()
        sentinel = self.base / 'executed'
        self.r['attempt']['argv'] = [sys.executable, '-c', f'open({str(sentinel)!r}, "w").close()']
        self.write(self.r)
        with mock.patch.object(subprocess, 'run', side_effect=AssertionError('no execution')):
            address = self.save()['address']
            ex.read(self.store, address)
            ex.search(self.store)
        self.assertFalse(sentinel.exists())

    def test_tree_oid_is_not_an_evidence_commit(self):
        self.require_history()
        commit = self.r['evidence'][0]['commit']
        tree = subprocess.check_output(
            ['git', 'rev-parse', commit + '^{tree}'], cwd=ROOT).decode('ascii').strip()
        # Same path and source bytes: a digest check alone cannot catch this.
        self.r['evidence'][0]['commit'] = tree
        self.write(self.r)
        before = self.record.read_bytes()
        result = self.cli('save', self.record, '--repo', ROOT)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertEqual(json.loads(result.stderr)['refusal'], 'INVALID_COMMIT')
        self.assertEqual(self.record.read_bytes(), before)
        self.assertFalse(self.store.exists())

    def test_tree_oid_is_not_a_relation_commit(self):
        self.require_history()
        first = self.save()['address']
        predecessor = self.store / (first + '.json')
        before = predecessor.read_bytes()
        tree = subprocess.check_output(
            ['git', 'rev-parse', CM1 + '^{tree}'], cwd=ROOT).decode('ascii').strip()
        self.r['id'] = 'synthetic-tree-relation-control'
        self.r['relations'] = [{'relation': 'contradicts', 'target': {
            'repository': self.r['revision']['repository'], 'commit': tree,
            'path': 'examples/model-experience/doc-f1/experience.json', 'sha256': first},
            'explanation': 'Synthetic invalid object-type control, not a model exchange.'}]
        self.write(self.r)
        result = self.cli('save', self.record, '--repo', ROOT)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertEqual(json.loads(result.stderr)['refusal'], 'INVALID_COMMIT')
        self.assertEqual(predecessor.read_bytes(), before)
        self.assertEqual(list(self.store.iterdir()), [predecessor])
        self.assertEqual(ex.read(self.store, first)[0], self.raw)

    def test_disagreement_control_preserves_exact_predecessor(self):
        self.require_history()
        first = self.save()['address']
        first_packet = (self.store / (first + '.json')).read_bytes()
        self.r['id'] = 'synthetic-disagreement-control'
        self.r['interpretation'] = 'Synthetic control: withhold advice pending exception testing. No independent model exchange.'
        self.r['provenance']['compiler'] = 'CM-2 functional test control'
        self.r['relations'] = [{'relation': 'contradicts', 'target': {
            'repository': self.r['revision']['repository'], 'commit': CM1,
            'path': 'examples/model-experience/doc-f1/experience.json', 'sha256': first},
            'explanation': 'Synthetic control of disagreement storage only.'}]
        self.write(self.r)
        second = self.save()['address']
        self.assertNotEqual(first, second)
        self.assertEqual(ex.read(self.store, first)[0], self.raw)
        self.assertEqual((self.store / (first + '.json')).read_bytes(), first_packet)
        self.assertEqual(ex.read(self.store, second)[1]['relations'][0]['target']['sha256'], first)
        self.assertEqual(len(ex.search(self.store, component='EMPIRICAL')['matches']), 2)
        self.r['relations'][0]['target']['path'] = 'README.md'
        self.write(self.r)
        with self.assertRaises(ex.Refusal) as error:
            self.save()
        self.assertEqual(error.exception.code, 'DIGEST_MISMATCH')
        (self.store / (first + '.json')).unlink()
        self.assertEqual(self.cli('read', second).returncode, 2)


if __name__ == '__main__':
    unittest.main()
