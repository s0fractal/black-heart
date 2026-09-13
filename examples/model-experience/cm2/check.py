#!/usr/bin/env python3
"""Fixed local CM-2 check, not an input-driven replay runner. Output: new JSON file."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8')


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: python3 examples/model-experience/cm2/check.py NEW_REPORT.json')
    # Reserve the caller-selected report without replacing existing bytes.
    with open(sys.argv[1], 'x', encoding='utf-8') as out:
        before = {'head': git('rev-parse', 'HEAD'), 'status_porcelain': git('status', '--porcelain')}
        argv = [sys.executable, '-m', 'unittest', '-v', 'test_experience']
        result = subprocess.run(argv, cwd=ROOT, capture_output=True)
        after = {'head': git('rev-parse', 'HEAD'), 'status_porcelain': git('status', '--porcelain')}
        report = {
            'scope': 'CM-2 behavioral tests, real DOC-F1 storage/read/search and synthetic disagreement control. No actual independent model exchange, no advice acceptance or authentication.',
            'conditions': 'Caller explicitly chooses this fixed local test module. Full local Git history required. Test stores are temporary. No argv read from experience JSON.',
            'checkout_before': before, 'checkout_after': after, 'argv': argv, 'cwd': str(ROOT),
            'python': sys.version, 'platform': platform.platform(), 'exit_code': result.returncode,
            'stdout': result.stdout.decode('utf-8'), 'stderr': result.stderr.decode('utf-8'),
            'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                              for name in ['experience.py', 'test_experience.py',
                                           'examples/model-experience/doc-f1/experience.json',
                                           'examples/model-experience/doc-f1/replay.json']}}
        json.dump(report, out, ensure_ascii=False, indent=2)
        out.write('\n')
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
