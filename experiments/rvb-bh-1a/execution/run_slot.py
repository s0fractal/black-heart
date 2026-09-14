"""One native CLI session; explicit reviewed head; separate human audit gate."""
import argparse
import datetime
import hashlib
import json
import os
import signal
import subprocess
import tempfile
from pathlib import Path
import runtime
from score import answer
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
    freeze=read(HERE/'freeze.json')
    for name in [*freeze['files'],'freeze.json']:
        p=(HERE/name).resolve()
        if name!='freeze.json' and sha(p)!=freeze['files'][name]:raise ValueError('HASH_CHANGED')
        raw=subprocess.check_output(['git','-C',str(REPO),'show',head+':'+str(p.relative_to(REPO))])
        if raw!=p.read_bytes():raise ValueError('UNREVIEWED_BYTES')
    return freeze

def execute(head):
    freeze=verify(head)
    if freeze.get('launch_ready') is not True:
        raise ValueError('ISOLATION_PREFLIGHT_NOT_REVIEWED; NO_MODEL_CALL')
    root=Path.home()/'rvb-bh-1a-runs'/freeze['run_id']
    root.mkdir(parents=True,exist_ok=True)
    if root.resolve()!=root:raise ValueError('SYMLINK_RUN_ROOT')
    # SIGKILL leaves this claim. Never remove it to resume a crashed study.
    with (root/'runner.claim').open('x') as f:f.write(now())
    try:
        slots=read(BASE/'schedule.json')['slots']
        for slot in slots:
            folder=root/str(slot['slot'])
            if not folder.exists():break
            result=read(folder/'result.json');audit=read(folder/'audit.json')
            for kind in ('result','public-events'):
                path=folder/(kind+('.jsonl' if kind=='public-events' else '.json'))
                if audit[kind+'_sha256']!=sha(path):raise ValueError('AUDIT_HASH')
            if audit.get('valid') is not True or not audit.get('reviewer') or not audit.get('evidence'):
                raise ValueError('AUDIT_INVALID')
            if not result['infrastructure_valid']:raise ValueError('STUDY_INVALID_STOP')
        else:return {'status':'ALL_FOUR_RETAINED; SCORE_AFTER_FINAL_AUDIT'}
        folder.mkdir();write(folder/'claim.json',{'claimed_at':now(),'slot':slot,'reviewed_head':head})
        annotator=slot['annotator'];client='codex' if annotator=='A' else 'claude'
        try:
            version=subprocess.check_output([client,'--version'],text=True).strip()
            if version!=runtime.VERSIONS[annotator]:raise ValueError('CLIENT_VERSION_CHANGED')
            workspace=folder/'workspace';workspace.mkdir()
            argv=runtime.command(annotator,workspace)
            prompt=(HERE/'stimuli'/f"{slot['slot']}.txt").read_bytes()
            env={k:v for k,v in os.environ.items() if k in ('HOME','PATH','USER','LOGNAME','SHELL','LANG','LC_ALL')}
            # Native login stores remain available, host API/proxy overrides do not.
            write(folder/'invocation.json',{'argv':argv,'prompt_sha256':hashlib.sha256(prompt).hexdigest(),
                'started_at':now(),'version':version,'requested_model':runtime.MODELS[annotator]})
            with (folder/'stderr.txt').open('xb') as err:
                proc=subprocess.Popen(argv,cwd=workspace,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                      stderr=err,start_new_session=True)
                timed_out=False
                try: raw,_=proc.communicate(prompt,timeout=180)
                except subprocess.TimeoutExpired:
                    timed_out=True;os.killpg(proc.pid,signal.SIGKILL);raw,_=proc.communicate()
            events=[];omitted=0;malformed=False;response=None;tools=False
            try:
                if annotator=='A':
                    for line in raw.splitlines():
                        e=json.loads(line);item=e.get('item',{})
                        if item.get('type') in ('reasoning','thinking','redacted_thinking'):omitted+=1;continue
                        events.append(e)
                        if item.get('type') in ('command_execution','file_change','mcp_tool_call','web_search'):tools=True
                        if e.get('type')=='item.completed' and item.get('type')=='agent_message':response=item['text']
                else:
                    e=json.loads(raw);events=[e];response=e.get('result')
                    if e.get('is_error'):raise ValueError('CLAUDE_CLIENT_ERROR')
            except (ValueError,KeyError):malformed=True
            with (folder/'public-events.jsonl').open('x') as f:
                for e in events:f.write(json.dumps(e,ensure_ascii=False)+'\n')
            if response is not None:
                with (folder/'response.txt').open('x') as f:f.write(response)
            format_ok=False
            try:answer(response);format_ok=True
            except (ValueError,TypeError):pass
            valid=(proc.returncode==0 or timed_out) and not tools and (not malformed or timed_out)
            write(folder/'result.json',{'finished_at':now(),'slot':slot,'exit_code':proc.returncode,
                'timed_out':timed_out,'infrastructure_valid':valid,'format_valid':format_ok and not timed_out,
                'omitted_reasoning_events':omitted,'malformed_events':malformed,'tool_event_seen':tools,
                'trace_audit':'REQUIRED_BEFORE_NEXT_SLOT'})
        except Exception as error:
            (folder/'public-events.jsonl').touch(exist_ok=True)
            if not (folder/'result.json').exists():write(folder/'result.json',{'finished_at':now(),
                'slot':slot,'infrastructure_valid':False,'format_valid':False,'error':str(error)})
            raise
        return read(folder/'result.json')
    finally:(root/'runner.claim').unlink()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--reviewed-head',required=True);args=p.parse_args()
    print(json.dumps(execute(args.reviewed_head),indent=2))
