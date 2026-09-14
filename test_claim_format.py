"""Real generated documents: one claim must not disappear behind whitespace."""
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from polyglot import PolyglotDocument, audit_polyglot_claims


class ClaimFormatTest(unittest.TestCase):
    def check_document(self, expected, transform=lambda raw: raw, false_claim=False):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'claim.pdf'
            doc = PolyglotDocument('Claim recognition')
            doc.add_claim('good', 'identity', '🤍 x', 'x', max_atp=10)
            if false_claim:
                doc.add_claim('bad', 'mismatch', '🤍 x', 'y', max_atp=10)
            doc.compile(str(target))
            # Mutate only metadata lines, never parser text or displayed prose.
            target.write_bytes(b'\n'.join(transform(line) if line.startswith('%🖤 CLAIM:'.encode()) else line
                                           for line in target.read_bytes().split(b'\n')))
            self.assertEqual(audit_polyglot_claims(str(target)), expected)
            run = subprocess.run([sys.executable, '-I', str(target)], cwd=tmp,
                                 capture_output=True, text=True, timeout=15)
            self.assertEqual(run.returncode, 0 if expected else 1, run.stdout + run.stderr)
            self.assertNotIn('100% SOUND', run.stdout)
            self.assertNotIn('Traceback', run.stderr)
            if expected:
                self.assertIn('recognized combinator claims only', run.stdout)

    def test_valid_spacing_and_description(self):
        for whitespace in (b'', b' ', b'  ', b'\t'):
            with self.subTest(whitespace=whitespace):
                self.check_document(True, lambda l: l.replace(b'CLAIM: ', b'CLAIM:'+whitespace))
        self.check_document(True, lambda l: l + b' | explanatory text')

    def test_whitespace_does_not_hide_a_false_claim(self):
        self.check_document(False, lambda l: l.replace(b'CLAIM: ', b'CLAIM:  ') if b'id=bad' in l else l,
                            false_claim=True)

    def test_missing_claims_are_not_success(self):
        self.check_document(False, lambda l: b'')

    def test_malformed_claim_beside_valid_claim_refuses(self):
        mutations = [lambda l: b'%'+ '🖤'.encode()+b' CLAIM: broken',
                     lambda l: l.replace(b'max_atp=10', b'max_atp=100001'),
                     lambda l: l.replace(b'max_atp=10', b'max_atp=-1'),
                     lambda l: l.replace(b'max_atp=10', b'max_atp=99999999999999999999'),
                     lambda l: l.replace(b'expected=y', b'expr=y'),
                     lambda l: l.replace(b'expected=y', b'expected='),
                     lambda l: l + b'\xff']
        for mutate in mutations:
            with self.subTest(mutation=mutations.index(mutate)):
                self.check_document(False, lambda l: mutate(l) if b'id=bad' in l else l, false_claim=True)


if __name__ == '__main__':
    unittest.main()
