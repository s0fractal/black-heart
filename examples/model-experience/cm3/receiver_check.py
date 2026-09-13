#!/usr/bin/env python3
"""Fixed CM-3 baseline/advice differential. Never execute record-supplied argv."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
MODULES = ['probe.py', 'test_empirical_settlement.py', 'warrant_kernel.py', 'glyph.py', 'crypto.py']


def git(cwd, *args):
    return subprocess.check_output(['git', '-C', str(cwd), *args]).decode('utf-8')


def checkout(cwd):
    return {'head': git(cwd, 'rev-parse', 'HEAD'), 'status_porcelain': git(cwd, 'status', '--porcelain')}


def run_case(name, apply_advice):
    cwd = ROOT / '.cm3-variants' / name
    cwd.mkdir(parents=True)
    for module in MODULES:
        (cwd / module).write_bytes((ROOT / module).read_bytes())
    git(cwd, '-c', 'init.templateDir=', 'init', '-q')
    git(cwd, 'add', '.')
    git(cwd, '-c', 'user.name=CM3 fixed check', '-c', 'user.email=cm3@example.invalid',
        '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'Fixed baseline source snapshot')
    if apply_advice:
        git(cwd, 'apply', '--check', str(ROOT / 'advice.patch'))
        git(cwd, 'apply', str(ROOT / 'advice.patch'))
    before = checkout(cwd)
    argv = [sys.executable, 'probe.py']
    result = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=60)
    return {'checkout_before': before, 'checkout_after': checkout(cwd), 'argv': argv, 'cwd': str(cwd),
            'warrant_kernel_sha256': hashlib.sha256((cwd / 'warrant_kernel.py').read_bytes()).hexdigest(),
            'exit_code': result.returncode, 'stdout': result.stdout.decode('utf-8'),
            'stderr': result.stderr.decode('utf-8'), 'measurement': json.loads(result.stdout.decode('utf-8'))}


def main():
    manifest_raw = (ROOT / 'source-manifest.json').read_bytes()
    manifest = json.loads(manifest_raw.decode('utf-8'))
    for name, expected in manifest['files'].items():
        if Path(name).name != name:
            raise ValueError('manifest only supports flat approved filenames')
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError('changed approved source: ' + name)
    before = checkout(ROOT)
    try:
        output = (ROOT / 'run.json').open('x', encoding='utf-8')
    except FileExistsError:
        print(json.dumps({'ok': False, 'refusal': 'OUTPUT_EXISTS', 'path': 'run.json'}))
        return 2
    with output:
        baseline = run_case('baseline', False)
        advice = run_case('advice', True)
        b, a = baseline['measurement'], advice['measurement']
        expected_failure = "test_an_unsettled_fixture_does_not_mask_a_settled_mismatch"
        observed = (baseline['exit_code'] == 0 and advice['exit_code'] == 1
                    and b['tests_run'] == a['tests_run'] == 3 and not b['failures']
                    and not b['errors'] and not a['errors'] and len(a['failures']) == 1
                    and expected_failure in a['failures'][0]
                    and [v['verdict'] for v in b['fixture_orders']] == ['fail', 'fail']
                    and [v['verdict'] for v in a['fixture_orders']] == ['unverified', 'fail'])
        report = {'profile': 'black-heart.cm3.local-check.v2',
                  'scope': 'Fixed baseline versus preregistered early-return advice patch; three tests and two explicit fixture orders. No repository patch or automatic advice adoption.',
                  'source_commit': manifest['source_commit'], 'checkout_before': before,
                  'checkout_after': checkout(ROOT),
                  'conditions': 'Fresh temporary variants; fixed patch and probe from the approved input commit; ATP 50; ephemeral test keys.',
                  'python': sys.version, 'platform': platform.platform(),
                  'patch_sha256': hashlib.sha256((ROOT / 'advice.patch').read_bytes()).hexdigest(),
                  'baseline': baseline, 'advice_applied': advice, 'expected_differential_observed': observed,
                  'source_manifest_sha256': hashlib.sha256(manifest_raw).hexdigest()}
        json.dump(report, output, ensure_ascii=False, indent=2)
        output.write('\n')
    print(json.dumps({'ok': observed, 'report': report,
                      'run_sha256': hashlib.sha256((ROOT / 'run.json').read_bytes()).hexdigest(),
                      'source_manifest_sha256': hashlib.sha256(manifest_raw).hexdigest()}, ensure_ascii=False))
    return 0 if observed else 1


if __name__ == '__main__':
    sys.exit(main())
