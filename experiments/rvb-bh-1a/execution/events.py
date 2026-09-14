"""Incremental native JSONL retention. Preserve public lines byte for byte."""
import json
import os
import signal
import subprocess
import threading

HIDDEN={'thinking','redacted_thinking','reasoning','thinking_delta','signature_delta'}
INIT_VARIABLE={'cwd','session_id','uuid','apiKeySource'}
INIT_EMPTY=('tools','mcp_servers','skills','slash_commands','plugins')


def init_errors(event,expected,model):
    errors=[name+' must be []' for name in INIT_EMPTY if event.get(name)!=[]]
    if event.get('model')!=model:errors.append('requested model mismatch')
    if set(event)!=set(expected):errors.append('init field set changed')
    for name in sorted((set(event)|set(expected))-INIT_VARIABLE):
        # JSON serialization also distinguishes false from 0 and [] from null.
        if json.dumps(event.get(name),sort_keys=True)!=json.dumps(expected.get(name),sort_keys=True):
            errors.append('init field changed: '+name)
    return errors


def probe_init(capture,model):
    rows=[json.loads(line) for line in capture['stdout'].splitlines()]
    inits=[e for e in rows if isinstance(e,dict) and e.get('type')=='system' and e.get('subtype')=='init']
    if len(inits)!=1:raise ValueError('PROBE_INIT_COUNT')
    if init_errors(inits[0],inits[0],model):raise ValueError('PROBE_INIT_SURFACE')
    return inits[0]


def public(value):
    """Remove only recognizable private reasoning blocks; count every removal."""
    if isinstance(value,dict):
        if value.get('type') in HIDDEN:return None,1
        out={};removed=0
        for k,v in value.items():
            if k in ('thinking','reasoning_content','signature'):
                removed+=1;continue
            child,n=public(v);removed+=n
            if child is not None or n==0:out[k]=child
        return out,removed
    if isinstance(value,list):
        out=[];removed=0
        for v in value:
            child,n=public(v);removed+=n
            if child is not None or n==0:out.append(child)
        return out,removed
    return value,0


def has_tool(value):
    if isinstance(value,dict):
        if value.get('type') in ('tool_use','tool_result','server_tool_use','mcp_tool_use'):return True
        return any(has_tool(v) for v in value.values())
    return isinstance(value,list) and any(has_tool(v) for v in value)


class Trace:
    def __init__(self,expected_init=None,requested_model=None):
        self.omitted=0;self.rewritten=0;self.malformed=0;self.tool=False
        self.result=None;self.failed=False;self.unknown=[];self.models=[];self.complete=False
        self.expected_init=expected_init;self.requested_model=requested_model
        self.init_count=0;self.init_errors=[]
    def line(self,line):
        try:event=json.loads(line)
        except (ValueError,UnicodeError):
            self.malformed+=1
            return line # retained as unparsed public transport output, audit required
        if not isinstance(event,dict):self.malformed+=1;return line
        self.tool |= has_tool(event)
        if event.get('type')=='system' and event.get('subtype')=='init':
            self.tool |= bool(event.get('tools'))
            self.init_count+=1
            if self.expected_init is not None:
                self.init_errors.extend(init_errors(event,self.expected_init,self.requested_model))
        t=event.get('type')
        if t not in ('system','assistant','user','result','rate_limit_event'):self.unknown.append(t)
        if t=='assistant':
            model=event.get('message',{}).get('model')
            if model and model not in self.models:self.models.append(model)
        if t=='result':
            if self.complete:self.failed=True
            self.complete=True;self.failed |= bool(event.get('is_error'))
            if not event.get('is_error') and isinstance(event.get('result'),str):self.result=event['result']
        cleaned,n=public(event);self.omitted+=n
        if not n:return line
        self.rewritten+=1
        return (json.dumps(cleaned,ensure_ascii=False)+'\n').encode() if cleaned is not None else b''

    def infrastructure_valid(self,code,timed_out):
        model_ok=bool(self.models) and all(m in (self.requested_model,str(self.requested_model)+'[1m]') for m in self.models)
        return (self.expected_init is not None and self.init_count==1 and not self.init_errors
                and model_ok and (code==0 or timed_out) and not self.tool and not self.failed
                and not self.unknown and (not self.malformed or timed_out) and (self.complete or timed_out))


def run(argv,prompt,cwd,env,output,timeout=180,expected_init=None,requested_model=None):
    trace=Trace(expected_init,requested_model);expired=[]
    with (output/'stderr.txt').open('xb') as err,(output/'public-events.jsonl').open('xb') as out:
        proc=subprocess.Popen(argv,cwd=cwd,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,start_new_session=True)
        def stop():
            expired.append(True)
            try:os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        timer=threading.Timer(timeout,stop);timer.start()
        try:
            try:proc.stdin.write(prompt);proc.stdin.close()
            except BrokenPipeError:pass
            for line in proc.stdout:
                out.write(trace.line(line));out.flush()
            code=proc.wait()
        finally:
            timer.cancel()
            try:os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            proc.wait()
            proc.stdout.close()
    return trace,code,bool(expired)
