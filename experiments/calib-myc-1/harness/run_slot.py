"""Launch one preregistered slot after exact package review; no automatic retries.

Not invoked by offline validation. Each completed slot needs an attributed
public-trace audit (audit.json) before the next slot.

Adapted from experiments/transfer-1/harness/run_slot.py (verify_package,
audited_rows, runner.claim, neutral snapshot, preflight, whitelist env, timer,
stream filtering, protected-input check, exception path) with the native
stream handling of rvb-bh-1a/execution/run_slot.py (events.run, init policy,
verbatim response.txt). Adapted for PLAN.md revision 2: the snapshot state at
stop is always graded by grade_checks.py; INVALID is reserved for environment
failures (preflight, pins, launch, init policy, a modified protected input,
malformed events, grader crash). Model timeout, no patch or a broken patch are
graded outcomes.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from common import (HARNESS, PLAN_HEAD, PLAN_MERGE, ROOT, RUNS, SOURCE_REVISION, expand, git, git_bytes,
                    inputs_digests, portable, read_json, sha, sha_bytes, write_json)
from decision import CLASSES, OUTCOMES, SCHEDULE, classify, decide
from runtime import KEEP, SETTINGS, TIMEOUT, argv_template, environment, invocation, preflight, profile, sandbox
from verify_prepared import materialize
import events

SECONDARY = {'ledger_read': ('observed', 'not_observed', 'unknown'),
             'false_fix_kind': ('one_branch', 'one_sided', 'minting_untouched', 'none', 'unknown'),
             'ran_existing_tests': ('observed', 'not_observed', 'unknown')}
PROTECTED = ('CONTRACT.md', 'task.txt')
BASELINE = ROOT / 'inputs' / 'test_mycelium.baseline-198f9e2.py'
EXPECTED_INIT = ROOT / 'execution' / 'offline' / 'expected-init.json'


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def reviewed_bytes(reviewed_head, path):
    repo = Path(git(ROOT, 'rev-parse', '--show-toplevel'))
    return git_bytes(ROOT, 'show', reviewed_head + ':' + str(Path(path).resolve().relative_to(repo)))


def verify_package(package, reviewed_head, expected_init=EXPECTED_INIT):
    """The reviewed commit must contain the exact freeze, bundle, harness, inputs, controls and init bytes."""
    if not re.fullmatch('[0-9a-f]{40}', reviewed_head) or git(ROOT, 'cat-file', '-t', reviewed_head) != 'commit':
        raise ValueError('INVALID_REVIEWED_HEAD')
    package = Path(package)
    frozen = read_json(package / 'freeze.json')
    files = [package / 'freeze.json', package / frozen['snapshot']['bundle'], *sorted(HARNESS.glob('*.py')),
             *[ROOT / 'inputs' / n for n in frozen['inputs']], ROOT / 'controls' / 'SUMMARY.json',
             *sorted((ROOT / 'controls').glob('C*.json')), ROOT / 'PLAN.md', Path(expected_init)]
    for path in files:
        if reviewed_bytes(reviewed_head, path) != path.read_bytes():
            raise ValueError('UNREVIEWED_BYTES: ' + path.name)
    if git_bytes(ROOT, 'show', PLAN_HEAD + ':experiments/calib-myc-1/PLAN.md') != (ROOT / 'PLAN.md').read_bytes():
        raise ValueError('PLAN_CHANGED_SINCE_ACCEPTANCE')
    if (frozen['plan_head'] != PLAN_HEAD or frozen['plan_merge'] != PLAN_MERGE
            or frozen['source_revision'] != SOURCE_REVISION
            or frozen['source_tree'] != git(ROOT, 'rev-parse', SOURCE_REVISION + '^{tree}')
            or frozen['inputs'] != inputs_digests() or frozen['settings'] != SETTINGS
            or frozen['argv_template'] != argv_template(frozen['model']) or frozen['schedule'] != list(SCHEDULE)
            or frozen['timeout_seconds'] != TIMEOUT or frozen['init_policy'] != events.policy()
            or frozen['controls_summary_sha256'] != sha(ROOT / 'controls' / 'SUMMARY.json')
            or not isinstance(frozen['model'], str) or not frozen['model'].strip()):
        raise ValueError('FREEZE_MISMATCH')
    if set(frozen['harness']) != {p.name for p in HARNESS.glob('*.py')}:
        raise ValueError('HARNESS_CHANGED')
    for name, digest in frozen['harness'].items():
        if sha(HARNESS / name) != digest:
            raise ValueError('HARNESS_CHANGED')
    if sha(package / frozen['snapshot']['bundle']) != frozen['snapshot']['sha256']:
        raise ValueError('BUNDLE_CHANGED')
    return frozen


def audited_rows(root):
    rows = []
    for i, _condition in enumerate(SCHEDULE, 1):
        slot = root / str(i)
        if not slot.exists():
            break
        # Crash/interruption without an audit blocks further slots, never resumes it.
        report = read_json(slot / 'result.json')
        audit = read_json(slot / 'audit.json')
        if (audit['result_sha256'] != sha(slot / 'result.json') or
                audit['events_sha256'] != sha(slot / 'public-events.jsonl') or
                not audit['reviewer'] or not audit['evidence'] or type(audit['valid']) is not bool):
            raise ValueError('INVALID_TRACE_AUDIT')
        for field, values in SECONDARY.items():
            if audit[field] not in values:
                raise ValueError('INVALID_SECONDARY_OBSERVATION')
        if report['slot'] != i or report['classification'] not in CLASSES or type(report['infrastructure_valid']) is not bool:
            raise ValueError('WRONG_SLOT_REPORT')
        if report.get('ephemeral_snapshot') and os.path.lexists(expand(report['ephemeral_snapshot'])):
            raise ValueError('PREVIOUS_SNAPSHOT_NOT_ARCHIVED')
        valid = report['infrastructure_valid'] and audit['valid']
        rows.append({'slot': i, 'classification': report['classification'] if valid else 'INVALID'})
    return rows


def grade(archived):
    out = subprocess.run([sys.executable, str(HARNESS / 'grade_checks.py'), str(archived), str(BASELINE)],
                         capture_output=True, text=True, timeout=1800)
    try:
        result = json.loads(out.stdout)
    except ValueError:
        result = {'outcome': 'GRADER_ERROR', 'exit_code': out.returncode,
                  'stdout_tail': out.stdout[-2000:], 'stderr_tail': out.stderr[-2000:]}
    result.update(baseline_sha256=sha(BASELINE), grader_sha256=sha(HARNESS / 'grade_checks.py'))
    return result


def execute(package, reviewed_head, expected_init_path=EXPECTED_INIT):
    package = Path(package).resolve()
    frozen = verify_package(package, reviewed_head, expected_init_path)
    expected_init = read_json(expected_init_path)
    root = expand(frozen['run_root'])
    if root.parent != Path.home() / RUNS or not re.fullmatch('[0-9a-f]{32}', root.name):
        raise ValueError('INVALID_RUN_ROOT')
    if root.is_symlink():
        raise ValueError('SYMLINK_RUN_ROOT')
    root.mkdir(parents=True, exist_ok=True)
    if root.resolve() != root:
        raise ValueError('SYMLINK_RUN_PARENT')
    # One host runner at a time; a crash leaves this marker and refuses a retry.
    with (root / 'runner.claim').open('x') as f:
        f.write(utc())
    try:
        rows = audited_rows(root)
        decision = decide(rows)
        if decision['status'] != 'CONTINUE':
            return decision
        number = len(rows) + 1; condition = SCHEDULE[number - 1]
        # Preflight runs BEFORE the slot exists. A refusal here makes no model
        # call and produces no receiver result, so it consumes no slot: the
        # refusal is retained under preflight-refusals/ and the operator may
        # repair host hygiene and invoke the runner again. INVALID (a consumed
        # slot) is reserved for failures after the slot is claimed.
        snapshot = materialize(package, frozen)
        check = preflight(snapshot, root, frozen)
        if not check['pass']:
            refusals = root / 'preflight-refusals'; refusals.mkdir(exist_ok=True)
            write_json(refusals / (utc().replace(':', '-') + '.json'),
                       {'intended_slot': number, 'refusals': check['refusals'], 'preflight': check})
            shutil.rmtree(snapshot)
            raise ValueError('PREFLIGHT_FAILED; NO_MODEL_CALL; SLOT_NOT_CONSUMED; ' + ', '.join(check['refusals']))
        slot = root / str(number); slot.mkdir()
        write_json(slot / 'claim.json', {'claimed_at': utc(), 'slot': number, 'condition': condition,
                   'reviewed_head': reviewed_head, 'freeze_sha256': sha(package / 'freeze.json'),
                   'expected_init_sha256': sha(expected_init_path)})
        write_json(slot / 'preflight.json', check)
        prompt = (snapshot / 'task.txt').read_bytes()
        if sha_bytes(prompt) != frozen['inputs']['task.txt']:
            raise ValueError('PROMPT_MISMATCH')
        argv = invocation(snapshot, frozen['model']); env = environment()
        write_json(slot / 'invocation.json', {
            'argv': argv, 'sandbox': sandbox(snapshot)[:2] + ['<profile>'], 'sandbox_profile': profile(snapshot),
            'started_at': utc(), 'head_before': frozen['snapshot']['head'],
            'status_before': git(snapshot, 'status', '--porcelain', timeout=60), 'prompt_sha256': sha_bytes(prompt),
            'requested_model': frozen['model'], 'client': check['client'], 'timeout_seconds': TIMEOUT,
            'explicit_environment': {k: v for k, v in env.items() if k not in KEEP},
            'inherited_keys': sorted(k for k in env if k in KEEP), 'inherited_path': env.get('PATH')})
        started = time.monotonic()
        trace, code, timed_out = events.run([*sandbox(snapshot), *argv], prompt, snapshot, env, slot,
                                            TIMEOUT, expected_init, frozen['model'])
        elapsed = time.monotonic() - started
        if trace.result is not None:
            with (slot / 'response.txt').open('x') as f:
                f.write(trace.result)
        protected = {name: (not (snapshot / name).is_symlink() and (snapshot / name).is_file()
                            and sha(snapshot / name) == frozen['inputs'][name]) for name in PROTECTED}
        head_after = git(snapshot, 'rev-parse', 'HEAD')
        status_after = git(snapshot, 'status', '--porcelain', timeout=60)
        archived = slot / 'snapshot'
        shutil.move(str(snapshot), str(archived))
        grading = grade(archived)
        write_json(slot / 'grade.json', grading)
        infrastructure_valid = (all(protected.values()) and trace.infrastructure_valid(code, timed_out)
                                and grading.get('outcome') in OUTCOMES)
        classification = classify(infrastructure_valid, grading.get('outcome')) if infrastructure_valid else 'INVALID'
        usage = (trace.result_event or {})
        result = {'slot': number, 'condition': condition, 'finished_at': utc(), 'exit_code': code,
                  'elapsed_seconds': elapsed, 'timed_out': timed_out, 'protected_inputs': protected,
                  'infrastructure_valid': infrastructure_valid, 'init_errors': trace.init_errors,
                  'classification': classification, 'grader_outcome': grading.get('outcome'),
                  'checks': {h: v.get('pass') for h, v in grading.get('checks', {}).items()},
                  'omitted_reasoning_events': trace.omitted, 'malformed_events': trace.malformed,
                  'unknown_event_types': trace.unknown, 'tool_uses': len(trace.tools),
                  'tool_use_names': sorted(set(trace.tools)),
                  'head_after': head_after, 'status_after': status_after, 'model_reported': trace.models,
                  'api_key_source': (trace.init_event or {}).get('apiKeySource'),
                  'usage': {k: usage.get(k) for k in ('usage', 'modelUsage', 'num_turns', 'duration_ms', 'duration_api_ms',
                                                       'total_cost_usd', 'stop_reason', 'subtype', 'is_error',
                                                       'permission_denials', 'terminal_reason')},
                  'snapshot': portable(archived), 'ephemeral_snapshot': portable(snapshot),
                  'trace_audit': 'REQUIRED_BEFORE_NEXT_SLOT'}
        write_json(slot / 'result.json', result)
        return result
    except Exception as error:
        # Leave the slot claimed and a visible failure; the next invocation
        # requires its audit and will stop rather than replace the slot.
        if 'slot' in locals() and slot.exists() and not (slot / 'result.json').exists():
            (slot / 'public-events.jsonl').touch(exist_ok=True)
            write_json(slot / 'result.json', {'slot': number, 'condition': condition, 'infrastructure_valid': False,
                       'classification': 'INVALID', 'error': type(error).__name__ + ': ' + str(error),
                       'finished_at': utc(), 'trace_audit': 'REQUIRED; environment failure stops remaining slots'})
        raise
    finally:
        if 'snapshot' in locals() and snapshot.exists():
            # A snapshot that never reached a claimed slot (preflight raised
            # unexpectedly) is parked under the run root, never left readable.
            target = (slot / 'snapshot') if 'slot' in locals() else (root / 'preflight-refusals' / ('orphan-' + snapshot.name))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(snapshot), str(target))
        (root / 'runner.claim').unlink()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('package', type=Path)
    parser.add_argument('--reviewed-head', required=True, help='Exact execution-package commit accepted before the first receiver call')
    parser.add_argument('--expected-init', type=Path, default=EXPECTED_INIT, help='Reviewed init capture from offline.py')
    args = parser.parse_args()
    print(json.dumps(execute(args.package.resolve(), args.reviewed_head, args.expected_init.resolve()), indent=2))
