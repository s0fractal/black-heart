#!/usr/bin/env python3
"""One fixed CM-3 local check. No command or operands are taken from records."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
TESTS = [
    'test_empirical_settlement.EmpiricalSettlementTest.test_an_unsettled_fixture_does_not_mask_a_settled_mismatch',
    'test_empirical_settlement.EmpiricalSettlementTest.test_both_suspended_on_the_same_term_is_not_a_pass',
    'test_empirical_settlement.EmpiricalSettlementTest.test_both_suspended_on_different_terms_is_not_a_fail',
]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8')


def main():
    manifest_raw = (ROOT / 'source-manifest.json').read_bytes()
    manifest = json.loads(manifest_raw.decode('utf-8'))
    for name, expected in manifest['files'].items():
        # The manifest is prepared by the caller and committed before delivery.
        if Path(name).name != name:
            raise ValueError('manifest only supports flat approved filenames')
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError('changed approved source: ' + name)
    before = {'head': git('rev-parse', 'HEAD'), 'status_porcelain': git('status', '--porcelain')}
    try:
        output = (ROOT / 'run.json').open('x', encoding='utf-8')
    except FileExistsError:
        print(json.dumps({'ok': False, 'refusal': 'OUTPUT_EXISTS', 'path': 'run.json'}))
        return 2
    argv = [sys.executable, '-m', 'unittest', '-v', *TESTS]
    with output:
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
        report = {
            'profile': 'black-heart.cm3.local-check.v1',
            'scope': 'Three fixed DOC-F1 regressions. No patch, historical checkout, mutation, identity check or advice acceptance.',
            'source_commit': manifest['source_commit'],
            'checkout_before': before,
            'checkout_after': {'head': git('rev-parse', 'HEAD'), 'status_porcelain': git('status', '--porcelain')},
            'conditions': 'Receiver snapshot contains only the approved files; test keys are ephemeral; ATP budget is the existing test constant 50.',
            'argv': argv, 'cwd': str(ROOT), 'python': sys.version, 'platform': platform.platform(),
            'exit_code': result.returncode, 'stdout': result.stdout.decode('utf-8'),
            'stderr': result.stderr.decode('utf-8'),
            'source_manifest_sha256': hashlib.sha256(manifest_raw).hexdigest(),
        }
        json.dump(report, output, ensure_ascii=False, indent=2)
        output.write('\n')
    print(json.dumps({'ok': result.returncode == 0, 'report': report,
                      'run_sha256': hashlib.sha256((ROOT / 'run.json').read_bytes()).hexdigest(),
                      'source_manifest_sha256': hashlib.sha256(manifest_raw).hexdigest()}, ensure_ascii=False))
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
