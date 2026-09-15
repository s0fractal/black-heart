"""Retain host-only control, readback, sandbox, init-surface and regression evidence. No model calls.

Adapted from experiments/transfer-1/harness/offline.py (temp-storage refusal,
receipt.json + sha256.json layout, control re-run, preflight on a materialized
snapshot) and experiments/rvb-bh-1a/execution/offline.py (loopback init
capture with a dummy API key, OS-level remote-network denial probe, binary
digest in the receipt). New: bundle determinism (prepare twice, compare),
the store canary, a stub-driven Bash tool probe under the receiver sandbox,
and the init-policy / decision / Trace / environment / argv regressions.

    python3 offline.py PACKAGE OUTPUT

expected-init.json is written to OUTPUT (cwd made portable) and is what
run_slot.py compares the live init against; it must be committed and reviewed
with the package. Re-run this after choosing the final CALIB_MODEL so the
capture carries the same requested model.
"""
import argparse
import datetime
import json
import os
import platform
import shutil
import sys
import tempfile
from pathlib import Path
from common import (HARNESS, REPO, ROOT, RUNS, WORK, git, inputs_digests, portable, portable_json, read_json, refuse_temp,
                    run, sha, sha_bytes, write_json)
from regressions import (argv_check, decision_check, environment_check, grader_hang_check, init_policy_check,
                         overwrite_check, public_filter_check, scan_boundary_check, trace_check)
from runtime import PROTECTED, STUB_NETWORK, TOOLS, client_identity, preflight, sandbox
from tmp_scan import MARKERS
from verify_prepared import materialize, verify
import context_probe
import events
import prepare
import run_controls

REMOTE_PROBE = ("import socket; s=socket.socket(); s.settimeout(2)\ntry:s.connect(('1.1.1.1',443))\n"
                "except PermissionError:print('REMOTE_DENIED');raise SystemExit(0)\n"
                "except OSError as e:print(type(e).__name__);raise SystemExit(2)\nraise SystemExit(3)")


def controls_check(work):
    # run_controls.py leaves its six extracted control trees in the temp dir (its
    # logic is pinned); point tempfile at a receiver-denied directory under
    # ~/calib1-work for the duration so no patched mycelium.py lands in readable tmp.
    with tempfile.TemporaryDirectory(prefix='controls-', dir=work) as td:
        previous = tempfile.tempdir
        tempfile.tempdir = td
        try:
            code = run_controls.main(str(REPO), str(Path(td) / 'out'))
        finally:
            tempfile.tempdir = previous
        regenerated = (Path(td) / 'out' / 'SUMMARY.json').read_bytes()
        leaked = sorted(p.name for p in Path(td).glob('calib-C*'))
    committed = (ROOT / 'controls' / 'SUMMARY.json').read_bytes()
    summary = json.loads(regenerated)
    return {'pass': code == 0 and summary['all_as_predicted'] and regenerated == committed,
            'all_as_predicted': summary['all_as_predicted'], 'byte_identical_to_committed': regenerated == committed,
            'regenerated_sha256': sha_bytes(regenerated), 'committed_sha256': sha_bytes(committed),
            'outcomes': {k: v['outcome'] for k, v in summary['controls'].items()},
            'grader_sha256': summary['grader_sha256'], 'baseline_test_sha256': summary['baseline_test_sha256'],
            'control_trees_redirected_from_tmp': leaked}


def remote_denied(snapshot):
    probe = run([*sandbox(snapshot, STUB_NETWORK), sys.executable, '-c', REMOTE_PROBE], cwd=snapshot, timeout=15)
    return {'pass': probe['exit_code'] == 0 and probe['stdout'].strip() == 'REMOTE_DENIED', **probe}


def collect(package, output):
    package = Path(package).resolve()
    output = refuse_temp(output, 'OFFLINE_OUTPUT_MUST_BE_OUTSIDE_TEMP_STORAGE')
    output.mkdir(parents=True, exist_ok=False)
    frozen = read_json(package / 'freeze.json'); model = frozen['model']
    work = Path.home() / WORK / 'offline'; work.mkdir(parents=True, exist_ok=True)
    runs = Path.home() / RUNS; runs.mkdir(exist_ok=True)
    report = {'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'head': git(ROOT, 'rev-parse', 'HEAD'), 'status': git(ROOT, 'status', '--porcelain'),
              'python': sys.version, 'platform': platform.platform(),
              'git': run(['git', '--version'], cwd=ROOT)['stdout'].strip(), 'inputs': inputs_digests(),
              'harness': {p.name: sha(p) for p in sorted(HARNESS.glob('*.py'))},
              'package': portable(package), 'freeze_sha256': sha(package / 'freeze.json'),
              'snapshot': frozen['snapshot'], 'model': model, 'client': client_identity(),
              'model_note': 'requested model id as frozen in the package (CALIB_MODEL at prepare time); this receipt does not choose it',
              'scope': 'Offline host verification only. No receiver or calibration session; zero provider calls.'}
    print('controls ...', flush=True)
    controls = controls_check(work)
    print('readback + determinism ...', flush=True)
    readback = verify(package)
    with tempfile.TemporaryDirectory(prefix='determinism-', dir=work) as td:
        second = prepare.prepare(Path(td) / 'package', model=model)
    determinism = {'pass': second['snapshot'] == frozen['snapshot'], 'first_bundle_sha256': frozen['snapshot']['sha256'],
                   'second_bundle_sha256': second['snapshot']['sha256'], 'head': frozen['snapshot']['head']}
    print('sandbox preflight + init capture ...', flush=True)
    snapshot = materialize(package, frozen)
    try:
        with tempfile.TemporaryDirectory(prefix='offline-canary-', dir=runs) as run_root:
            (Path(run_root) / 'runner.claim').write_text('offline canary')
            pre = preflight(snapshot, run_root, frozen)
        remote = remote_denied(snapshot)
        capture = context_probe.capture(snapshot, model)
        tool = context_probe.capture(snapshot, model, tool_command=context_probe.TOOL_PROBE)
    finally:
        shutil.rmtree(snapshot, ignore_errors=True)
    init = events.probe_init(capture['stdout_lines'], model)
    write_json(output / 'expected-init.json', portable_json(init))
    write_json(output / 'context.json', portable_json(capture))
    write_json(output / 'tool-probe.json', portable_json(tool))
    request = capture['requests'][0] if capture['requests'] else {}
    extra_blocks = (request.get('first_user_blocks') or [])[:-1]
    visible = [*extra_blocks, *[b.get('text', '') for b in request.get('system') or []],
               *[m['text'] for m in request.get('other_messages') or []]]
    markers_seen = sorted({m.decode() for m in MARKERS for t in visible if m in t.lower().encode()})
    init_capture = {'pass': (capture['exit_code'] == 0 and not capture['timed_out'] and (capture['result'] or {}).get('result') == 'probe-ok'
                             and not markers_seen
                             and init['skills'] == [] and init['slash_commands'] == [] and init['mcp_servers'] == []
                             and init['plugins'] == [] and init['permissionMode'] == 'dontAsk'
                             and init['tools'] == sorted(TOOLS.split(',')) and init['model'] == model
                             and len(capture['requests']) == 1 and capture['requests'][0]['first_user_message_is_prompt']
                             and capture['requests'][0]['tools'] == sorted(TOOLS.split(','))
                             and capture['requests'][0]['model'] == model),
                    'requests': len(capture['requests']), 'skills': init['skills'], 'slash_commands': init['slash_commands'],
                    'tools': init['tools'], 'apiKeySource': init['apiKeySource'], 'claude_code_version': init['claude_code_version'],
                    'in_tree_skill_present_but_not_loaded': '.agents/skills/black-heart-experience/SKILL.md',
                    'system_blocks': [b.get('text', '') for b in request.get('system') or []],
                    'extra_user_blocks_before_prompt': portable_json(extra_blocks),
                    'native_messages_after_prompt': portable_json(request.get('other_messages')),
                    'markers_in_model_visible_context': markers_seen,
                    'note': 'Everything the model sees besides the snapshot: three system blocks (billing header, SDK preamble, '
                            'pinned SYSTEM), the native attribution reminder, the prompt, and the native environment message.'}
    text = tool['tool_results'][0]['content'] if tool['tool_results'] else ''
    text = text if isinstance(text, str) else json.dumps(text)
    tool_probe = {'pass': (tool['exit_code'] == 0 and not tool['timed_out'] and 'WROTE' in text and 'ALLOWED' not in text
                           and all(f'DENIED {os.path.expanduser(p)}' in text for p in PROTECTED)
                           and (tool['result'] or {}).get('result') == 'probe-ok' and tool['turns'] == ['tool', 'text']
                           and not tool['tool_results'][0].get('is_error')),
                  'tool_result': portable_json(text), 'turns': tool['turns'], 'permission_denials': (tool['result'] or {}).get('permission_denials')}
    print('regressions ...', flush=True)
    regressions = {'init_policy': init_policy_check(init, model), 'decision': decision_check(), 'trace': trace_check(init, model),
                   'overwrite': overwrite_check(), 'scan_boundary': scan_boundary_check(), 'public_filter': public_filter_check(),
                   'environment': environment_check(), 'argv': argv_check(model),
                   'grader_hang': grader_hang_check(REPO, work)}
    scan = pre['tmp_content_scan']
    report.update(controls=controls, readback=readback, determinism=determinism,
                  store_canary={'pass': pre['store_canary']['pass'], 'observed': pre['store_canary']['observed'],
                                'protected': portable_json(pre['store_canary']['protected'])},
                  client_pins_match='CLIENT_CHANGED' not in pre['refusals'],
                  stale_inputs={'tmp': pre['stale_tmp_inputs'], 'receivers': portable_json(pre['stale_receiver_snapshots'])},
                  tmp_content_scan={'pass': scan['pass'], 'roots': scan['roots'], 'files_read': scan['scan'].get('files_read'),
                                    'denied': scan['scan'].get('denied'), 'matches': scan['scan'].get('matches'),
                                    'errors': scan['scan'].get('errors'), 'markers': scan['markers'],
                                    'digests': scan['digests'], 'excluded_c0_digest': scan['excluded_c0_digest']},
                  launch_preflight_now={'pass': pre['pass'], 'refusals': pre['refusals'],
                                        'note': 'Host hygiene at this moment; preflight gates again before every receiver call.'},
                  remote_network_denied_under_stub_profile=remote, init_capture=init_capture, tool_probe=tool_probe,
                  regressions=regressions,
                  sandbox_notes={'claude_home_paths_allowed': [], 'why': 'CLI started, ran the Bash tool and finished with the whole of ~/.claude and ~/.claude.json read-denied and all writes outside the snapshot, /private/tmp, /private/var/folders and /dev denied.'})
    report['pass'] = all([controls['pass'], readback['pass'], determinism['pass'], pre['store_canary']['pass'],
                          report['client_pins_match'], remote['pass'], init_capture['pass'], tool_probe['pass'],
                          all(r['pass'] for r in regressions.values())])
    report['finished_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    write_json(output / 'receipt.json', portable_json(report))
    write_json(output / 'sha256.json', {p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()})
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('package', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); report = collect(args.package, args.output)
    print(json.dumps({'pass': report['pass'], 'launch_preflight_now': report['launch_preflight_now'],
                      'receipt': portable(args.output.resolve() / 'receipt.json')}, indent=2))
    sys.exit(0 if report['pass'] else 1)
