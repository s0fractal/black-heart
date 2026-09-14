"""One reviewed native session; no retry; separate attributed audit gate."""
import argparse
import datetime
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
import context_check
import context_probe
import events
import runtime
from score import answer,score
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
REPO=BASE.parents[1]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(path,obj):
    with path.open('x') as f:json.dump(obj,f,indent=2);f.write('\n')
def read(path):return json.loads(path.read_text())

def verify(head):
    if len(head)!=40 or any(c not in '0123456789abcdef' for c in head):raise ValueError('BAD_HEAD')
    if subprocess.check_output(['git','-C',str(REPO),'cat-file','-t',head]).strip()!=b'commit':raise ValueError('NOT_COMMIT')
    freeze=read(HERE/'freeze.json')
    for name in [*freeze['files'],'freeze.json']:
        p=(HERE/name).resolve()
        if name!='freeze.json' and sha(p)!=freeze['files'][name]:raise ValueError('HASH_CHANGED')
        raw=subprocess.check_output(['git','-C',str(REPO),'show',head+':'+str(p.relative_to(REPO))])
        if raw!=p.read_bytes():raise ValueError('UNREVIEWED_BYTES')
    return freeze

def final(root,status,slots,raws=None,validity=None):
    result=score(raws,validity) if raws is not None else {'status':status}
    result['remaining']=[dict(slot=s['slot'],status='NOT_RUN') for s in slots if not (root/str(s['slot'])).exists()]
    target=root/'decision.json'
    if target.exists():
        if read(target)!=result:raise ValueError('DECISION_CHANGED')
    else:write(target,result)
    return result

def prior(root,slots):
    raws=[];validity=[]
    for slot in slots:
        folder=root/str(slot['slot'])
        if not folder.exists():return slot,raws,validity
        result=read(folder/'result.json');audit=read(folder/'audit.json')
        if result['slot']!=slot or type(result['infrastructure_valid']) is not bool:raise ValueError('RESULT_SLOT')
        if type(audit.get('valid')) is not bool or not isinstance(audit.get('reviewer'),str) or not audit['reviewer'].strip() or not audit.get('evidence'):raise ValueError('AUDIT_INVALID')
        for name in ('result.json','public-events.jsonl','response.txt','context.json'):
            path=folder/name
            if audit.get('hashes',{}).get(name)!=(sha(path) if path.exists() else None):raise ValueError('AUDIT_HASH')
        stamp=datetime.datetime.fromisoformat(audit['audited_at'])
        if not datetime.datetime.fromisoformat(result['finished_at'])<=stamp<=datetime.datetime.now(datetime.timezone.utc):raise ValueError('AUDIT_CHRONOLOGY')
        if not audit['valid'] or not result['infrastructure_valid']:
            return None,None,None
        validity.append(True)
        raws.append((folder/'response.txt').read_text() if result['format_valid'] else None)
    return None,raws,validity

def execute(head):
    freeze=verify(head)
    if freeze.get('launch_ready') is not True:raise ValueError('PACKAGE_NOT_READY; NO_MODEL_CALL')
    root=Path.home()/'rvb-bh-1a-runs'/freeze['run_id']
    if root.resolve()!=root or (Path.home()/'Projects') in root.parents:raise ValueError('UNSAFE_RUN_ROOT')
    root.mkdir(parents=True,exist_ok=True)
    with (root/'runner.claim').open('x') as f:f.write(now())
    try:
        slots=read(BASE/'schedule.json')['slots']
        slot,raws,validity=prior(root,slots)
        if slot is None:
            return final(root,'INVALID',slots) if raws is None else final(root,None,slots,raws,validity)
        folder=root/str(slot['slot']);folder.mkdir()
        write(folder/'claim.json',{'claimed_at':now(),'slot':slot,'reviewed_head':head})
        try:
            version=subprocess.check_output(['claude','--version'],text=True).strip()
            binary=Path(shutil.which('claude')).resolve()
            if version!=runtime.VERSIONS[slot['annotator']] or sha(binary)!=freeze['claude_binary_sha256']:raise ValueError('CLIENT_CHANGED')
            workspace=folder/'workspace';workspace.mkdir()
            prompt=(HERE/'stimuli'/f"{slot['slot']}.txt").read_bytes()
            # Local rejection endpoint, OS blocks all remote traffic, no inference.
            capture=context_probe.capture(slot['annotator'],prompt.decode(),Path.home()/'rvb-bh-1a-work')
            write(folder/'context.json',capture)
            checked=context_check.check(capture,prompt.decode());write(folder/'preflight.json',checked)
            argv=runtime.command(slot['annotator'],workspace);env=runtime.environment()
            write(folder/'invocation.json',{'argv':argv,'prompt_sha256':hashlib.sha256(prompt).hexdigest(),
                'started_at':now(),'version':version,'binary_sha256':sha(binary),
                'requested_model':runtime.MODELS[slot['annotator']],
                'explicit_environment':{k:v for k,v in env.items() if k.startswith('CLAUDE_') or k=='DISABLE_AUTOUPDATER'}})
            trace,code,timed_out=events.run(argv,prompt,workspace,env,folder)
            if trace.result is not None:
                with (folder/'response.txt').open('x') as f:f.write(trace.result)
            format_ok=False
            try:answer(trace.result);format_ok=True
            except (ValueError,TypeError):pass
            model_ok=all(m==runtime.MODELS[slot['annotator']] or m==runtime.MODELS[slot['annotator']]+'[1m]' for m in trace.models)
            valid=(code==0 or timed_out) and not trace.tool and not trace.failed and not trace.unknown and model_ok and (not trace.malformed or timed_out) and (trace.complete or timed_out)
            write(folder/'result.json',{'finished_at':now(),'slot':slot,'exit_code':code,'timed_out':timed_out,
                'infrastructure_valid':valid,'format_valid':format_ok and not timed_out,
                'omitted_reasoning_blocks':trace.omitted,'rewritten_lines':trace.rewritten,
                'malformed_lines':trace.malformed,'tool_event_seen':trace.tool,'unknown_events':trace.unknown,
                'observed_models':trace.models,'trace_audit':'REQUIRED_BEFORE_NEXT_SLOT'})
        except Exception as error:
            (folder/'public-events.jsonl').touch(exist_ok=True)
            if not (folder/'result.json').exists():write(folder/'result.json',{'finished_at':now(),
                'slot':slot,'infrastructure_valid':False,'format_valid':False,'error':str(error)})
            raise
        return read(folder/'result.json')
    finally:(root/'runner.claim').unlink()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--reviewed-head',required=True);a=p.parse_args()
    print(json.dumps(execute(a.reviewed_head),indent=2))
