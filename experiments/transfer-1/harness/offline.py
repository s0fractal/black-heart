"""Retain host-only reference, mutant, witness and sandbox evidence. No model calls."""
import argparse
import datetime
import hashlib
import itertools
import json
import platform
import sys
import tempfile
from pathlib import Path
from common import ROOT, git, run, sha, verify_inputs, write_json
from controls import sources
from decision import SCHEDULE, decide
from grader import grade
from runtime import preflight, sandbox
from regressions import crash_checks, isolation_check, content_scan_check


def decision_checks():
    counts = {}
    for bits in itertools.product((False, True), repeat=9):
        rows = [{'arm': arm, 'pass': bit, 'valid': True} for arm, bit in zip(SCHEDULE, bits)]
        if bits[0] == bits[1] == bits[2]:
            result = decide(rows[:3])
            expected = 'EARLY_UNIFORM_SUCCESS' if bits[0] else 'EARLY_UNIFORM_FAILURE'
            assert result['status'] == expected
            try:
                decide(rows)
            except ValueError:
                pass
            else:
                raise AssertionError('accepted slots after stop')
        else:
            p = sum(bits[i] for i, arm in enumerate(SCHEDULE) if arm == 'P')
            t = sum(bits[i] for i, arm in enumerate(SCHEDULE) if arm == 'T')
            expected = 'FOLLOWUP_CANDIDATE' if p-t >= 2 else 'NEGATIVE_PILOT_SIGNAL' if p < t else 'INDETERMINATE'
            assert decide(rows)['status'] == expected
        counts[expected] = counts.get(expected, 0) + 1
    assert decide([{'arm': 'N', 'pass': False, 'valid': False}])['status'] == 'ENVIRONMENT_INDETERMINATE'
    assert decide([])['status'] == 'CONTINUE'
    assert list(SCHEDULE) == sum(json.loads((ROOT/'scoring/decision.json').read_text())['schedule'], [])
    return {'pass': True, 'all_512_binary_sequences': counts, 'infrastructure_priority': True}


def collect(output):
    output=output.resolve()
    if any(output.is_relative_to(Path(p).resolve()) for p in ('/private/tmp','/private/var/tmp',tempfile.gettempdir())):
        raise ValueError('OFFLINE_OUTPUT_MUST_BE_OUTSIDE_TEMP_STORAGE')
    output.mkdir(parents=True, exist_ok=False)
    inputs = verify_inputs()
    report = {'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'head': git(ROOT, 'rev-parse', 'HEAD'), 'status': git(ROOT, 'status', '--porcelain'),
              'python': sys.version, 'platform': platform.platform(),
              'git': run(['git','--version'], cwd=ROOT), 'inputs': inputs,
              'harness': {p.name: sha(p) for p in sorted(Path(__file__).parent.glob('*.py'))},
              'scope': 'Offline host verification only. No receiver or calibration session.'}
    spec = json.loads((ROOT/'scoring/cases.json').read_text())
    expectations = {c['variant']: set(c['must_fail']) for c in spec['required_negative_controls']}
    results = {}
    for number, (name, source) in enumerate(sources().items()):
        path = output/f'control-{number}.py'
        path.write_text(source)
        result = grade(path, sandbox)
        actual = {c['id'] for c in result['cases'] if not c['pass']}
        expected = set(expectations.get(name, set()))
        if name == 'refuse all revisions':
            expected |= {'missing_object', 'missing_path', 'directory_path'}
        # Exact failed sets, plus named semantic observations rather than worker crashes.
        correct = actual == expected and all(c['worker']['exit_code'] == 0 and
                    not c['worker']['timed_out'] and 'exception' not in c['observed'] and
                    'invalid_worker_output' not in c['observed'] for c in result['cases'])
        result['control_verified'] = correct
        result['expected_failed'] = sorted(expected)
        write_json(output/f'control-{number}.json', result)
        results[name] = {'pass': correct, 'failures': sorted(actual), 'receipt': f'control-{number}.json'}
        print(name, correct, sorted(actual), flush=True)
    work=Path.home()/'transfer1-work'/'offline';work.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='witness-',dir=work) as td:
        root = Path(td)
        (root/'witness.py').write_bytes((ROOT/'inputs/packet/witness.py').read_bytes())
        witness = run([*sandbox(root), sys.executable, '-I', 'witness.py'], cwd=root)
        expected = json.loads((ROOT/'inputs/packet/manifest.json').read_text())['expected_witness_output']
        witness['pass'] = witness['exit_code'] == 0 and json.loads(witness['stdout'] or 'null') == expected
        witness['temporary_directory_removed'] = sorted(p.name for p in root.iterdir()) == ['witness.py']
        isolation = preflight(root)
    crash_reports=crash_checks(output,sandbox)
    for name,result in crash_reports.items(): write_json(output/(name+'.json'),result)
    boundary=isolation_check()
    report['regressions']={'crash_receipts':{name:name+'.json' for name in crash_reports},
                           'worker_crashes_are_valid_failures':True,'isolation':boundary,'tmp_content':content_scan_check()}
    report.update(controls=results, witness=witness, isolation=isolation, decisions=decision_checks())
    report['pass'] = all(r['pass'] for r in results.values()) and witness['pass'] and witness['temporary_directory_removed'] and isolation['pass'] and boundary['pass']
    report['finished_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    write_json(output/'receipt.json', report)
    write_json(output/'sha256.json', {p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file()})
    return report

if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('output',type=Path)
    args=parser.parse_args(); report=collect(args.output)
    print(json.dumps({'pass':report['pass'], 'receipt':str(args.output/'receipt.json')}))
    sys.exit(0 if report['pass'] else 1)
