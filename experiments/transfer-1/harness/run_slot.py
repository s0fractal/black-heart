"""Launch one preregistered slot after exact package review; no automatic retries.

Not invoked by offline validation. Each completed slot needs an attributed
public-trace audit before the next slot, including the early-stop decision.
"""
import argparse
import datetime
import json
import os
import re
import signal
import shutil
import subprocess
import threading
import time
from pathlib import Path
from common import ROOT, git, sha, verify_inputs, write_json
from decision import SCHEDULE, decide
from grader import grade
from runtime import invocation, preflight, sandbox, settings


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def verify_package(package, reviewed_head):
    # The reviewed commit must contain the exact freeze, bundle and launcher bytes.
    if not re.fullmatch('[0-9a-f]{40}', reviewed_head) or git(ROOT,'cat-file','-t',reviewed_head) != 'commit':
        raise ValueError('INVALID_REVIEWED_HEAD')
    repo=Path(git(ROOT,'rev-parse','--show-toplevel'))
    frozen=json.loads((package/'freeze.json').read_text())
    files=[package/'freeze.json', *[package/a['bundle'] for a in frozen['arms'].values()],
           *Path(__file__).parent.glob('*.py')]
    for path in files:
        rel=path.resolve().relative_to(repo)
        committed=subprocess.check_output(['git','-C',str(repo),'show',reviewed_head+':'+str(rel)])
        if committed != path.read_bytes(): raise ValueError('UNREVIEWED_BYTES: '+str(rel))
    if (frozen['inputs'] != verify_inputs() or frozen['settings'] != settings() or
        frozen['schedule'] != list(SCHEDULE) or frozen['timeout_seconds'] != 300):
        raise ValueError('FREEZE_MISMATCH')
    for name,digest in frozen['harness'].items():
        if sha(Path(__file__).parent/name)!=digest: raise ValueError('HARNESS_CHANGED')
    for arm in frozen['arms'].values():
        if sha(package/arm['bundle'])!=arm['sha256']: raise ValueError('BUNDLE_CHANGED')
    return frozen


def audited_rows(root):
    rows=[]
    for i, arm in enumerate(SCHEDULE,1):
        slot=root/str(i)
        if not slot.exists(): break
        # Crash/interruption without an audit blocks further slots, never resumes it.
        report=json.loads((slot/'result.json').read_text())
        audit=json.loads((slot/'audit.json').read_text())
        if (audit['result_sha256']!=sha(slot/'result.json') or
            audit['events_sha256']!=sha(slot/'public-events.jsonl') or
            not audit['reviewer'] or not audit['evidence'] or type(audit['valid']) is not bool):
            raise ValueError('INVALID_TRACE_AUDIT')
        for field in ('supplied_witness_run','receiver_created_tag','tag_check_executed'):
            if audit[field] not in ('observed','not_observed','unknown'):
                raise ValueError('INVALID_SECONDARY_OBSERVATION')
        if report['slot']!=i or report['arm']!=arm:
            raise ValueError('WRONG_SLOT_REPORT')
        if report.get('ephemeral_snapshot') and os.path.lexists(report['ephemeral_snapshot']):
            raise ValueError('PREVIOUS_SNAPSHOT_NOT_ARCHIVED')
        valid=report['valid'] and audit['valid']
        rows.append({'arm':arm,'pass':report['pass'] and valid,'valid':valid})
    return rows


def execute(package, reviewed_head):
    frozen=verify_package(package,reviewed_head)
    root=Path(frozen['run_root'])
    if root.parent != Path.home()/'.codex'/'transfer1-runs' or not re.fullmatch('[0-9a-f]{32}', root.name):
        raise ValueError('INVALID_RUN_ROOT')
    if root.is_symlink(): raise ValueError('SYMLINK_RUN_ROOT')
    root.mkdir(parents=True, exist_ok=True)
    if root.resolve() != root: raise ValueError('SYMLINK_RUN_PARENT')
    # One host runner at a time; a crash leaves this marker and refuses a retry.
    with (root/'runner.claim').open('x') as f: f.write(utc())
    try:
        rows=audited_rows(root)
        decision=decide(rows)
        if decision['status']!='CONTINUE':
            return decision
        number=len(rows)+1; arm=SCHEDULE[number-1]
        slot=root/str(number);slot.mkdir()
        write_json(slot/'claim.json',{'claimed_at':utc(),'slot':number,'arm':arm,
                   'reviewed_head':reviewed_head,'freeze_sha256':sha(package/'freeze.json')})
        # Neutral random path; no arm labels or preceding session outputs inside it.
        import tempfile
        snapshot=Path(tempfile.mkdtemp(prefix='receiver-',dir='/private/tmp'))
        git(snapshot,'-c','init.templateDir=','init','-q','--object-format=sha1')
        git(snapshot,'bundle','unbundle',str((package/frozen['arms'][arm]['bundle']).resolve()))
        git(snapshot,'checkout','--detach',frozen['arms'][arm]['head'])
        expected=frozen['arms'][arm]
        if git(snapshot,'rev-parse','HEAD')!=expected['head']: raise ValueError('SNAPSHOT_HEAD')
        for name,digest in expected['files'].items():
            if sha(snapshot/name)!=digest: raise ValueError('SNAPSHOT_BYTES')
        check=preflight(snapshot, root)
        write_json(slot/'preflight.json',check)
        if not check['pass']: raise ValueError('PREFLIGHT_FAILED; NO_MODEL_CALL')
        argv=invocation(snapshot)
        write_json(slot/'invocation.json',{'argv':argv,'started_at':utc(),
                   'head_before':expected['head'],'status_before':git(snapshot,'status','--porcelain'),
                   'prompt_sha256':sha(snapshot/'task.txt')})
        env={key:value for key,value in os.environ.items()
             if key in ('HOME','CODEX_HOME','PATH','USER','LOGNAME','SHELL','LANG','LC_ALL')}
        started=time.monotonic(); omitted=0; malformed=0; timed_out=[]
        with (slot/'stderr.txt').open('xb') as err, (slot/'public-events.jsonl').open('xb') as out:
            process=subprocess.Popen(argv,cwd=snapshot,env=env,stdin=subprocess.PIPE,
                      stdout=subprocess.PIPE,stderr=err,start_new_session=True)
            def kill():
                timed_out.append(True)
                try: os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError: pass
            timer=threading.Timer(300,kill);timer.start()
            try:
                process.stdin.write((snapshot/'task.txt').read_bytes());process.stdin.close()
                for line in process.stdout:
                    try: event=json.loads(line)
                    except ValueError:
                        malformed+=1; continue
                    if event.get('item',{}).get('type') in ('reasoning','thinking','redacted_thinking'):
                        omitted+=1;continue
                    out.write(line);out.flush()
                code=process.wait()
            finally:
                timer.cancel()
                try: os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError: pass
        protected={name:(not (snapshot/name).is_symlink() and (snapshot/name).is_file()
                           and sha(snapshot/name)==digest)
                   for name,digest in expected['files'].items() if name!='reader.py'}
        source=snapshot/'reader.py'
        if source.is_file() and not source.is_symlink():
            (slot/'reader.py').write_bytes(source.read_bytes())
        session_elapsed=time.monotonic()-started
        archived = slot/'snapshot'
        shutil.move(str(snapshot), str(archived))
        grading=grade(slot/'reader.py',sandbox)
        write_json(slot/'grade.json',grading)
        valid=(all(protected.values()) and malformed==0 and grading.get('valid',True)
               and (code==0 or bool(timed_out)))
        result={'slot':number,'arm':arm,'finished_at':utc(),'exit_code':code,
                'elapsed_seconds':session_elapsed,'timed_out':bool(timed_out),
                'protected_inputs':protected,'valid':valid,
                'pass':valid and code==0 and not timed_out and grading['pass'],
                'omitted_reasoning_events':omitted,'malformed_events':malformed,
                'head_after':git(archived,'rev-parse','HEAD'),'status_after':git(archived,'status','--porcelain'),
                'snapshot':str(archived),'ephemeral_snapshot':str(snapshot),'trace_audit':'REQUIRED_BEFORE_NEXT_SLOT'}
        write_json(slot/'result.json',result)
        return result
    except Exception as error:
        # Leave the slot claimed and a visible failure; the next invocation
        # requires its audit and will stop rather than replace the slot.
        if 'slot' in locals() and slot.exists() and not (slot/'result.json').exists():
            (slot/'public-events.jsonl').touch(exist_ok=True)
            failure={'slot':number,'arm':arm,'valid':False,'pass':False,
                     'error':type(error).__name__+': '+str(error),'finished_at':utc(),
                     'trace_audit':'REQUIRED; environment failure stops remaining slots'}
            write_json(slot/'result.json',failure)
        raise
    finally:
        if 'snapshot' in locals() and snapshot.exists():
            shutil.move(str(snapshot), str(slot/'snapshot'))
        (root/'runner.claim').unlink()

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('package',type=Path)
    parser.add_argument('--reviewed-head',required=True,help='Exact execution-package commit accepted before the first receiver call')
    args=parser.parse_args()
    print(json.dumps(execute(args.package.resolve(),args.reviewed_head),indent=2))
