"""Replay retained checks and scoring only; never launch a client."""
import datetime
import hashlib
import json
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=HERE.parent.parent
sys.path.insert(0,str(BASE/'execution'))
import context_check,events,run_slot,runtime,score

def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    for name,digest in read(HERE/'retained-sha256.json').items():
        if sha(HERE/name)!=digest:raise ValueError('RETAINED_HASH '+name)
    root=HERE/'run';slots=read(BASE/'schedule.json')['slots']
    ready=read(HERE/'prelaunch.json')
    run_slot.verify(ready['github']['headRefOid'])
    if len(ready['github']['statusCheckRollup'])!=8 or any(c['conclusion']!='SUCCESS' for c in ready['github']['statusCheckRollup']):raise ValueError('CI_GATE')
    last=datetime.datetime.fromisoformat(ready['observed_at'])
    for slot in slots:
        folder=root/str(slot['slot'])
        if not folder.exists():continue
        claim=read(folder/'claim.json')
        if claim['reviewed_head']!=ready['github']['headRefOid']:raise ValueError('REVIEWED_HEAD')
        claimed=datetime.datetime.fromisoformat(claim['claimed_at'])
        if claimed<last:raise ValueError('CLAIM_CHRONOLOGY')
        result=read(folder/'result.json');audit=read(folder/'audit.json')
        capture=read(folder/'context.json');model=runtime.MODELS[slot['annotator']]
        prompt=(BASE/'execution'/'stimuli'/f"{slot['slot']}.txt").read_text()
        context_check.check(capture,prompt)
        trace=events.Trace(events.probe_init(capture,model),model)
        retries=0
        for line in (folder/'public-events.jsonl').read_bytes().splitlines(keepends=True):
            trace.line(line)
            row=json.loads(line)
            retries+=row.get('type')=='system' and row.get('subtype')=='api_retry'
        if trace.infrastructure_valid(result['exit_code'],result['timed_out'])!=result['infrastructure_valid']:raise ValueError('TRACE_VALIDITY')
        if retries!=audit['api_retry_count']:raise ValueError('RETRY_COUNT')
        if (folder/'response.txt').exists() and (folder/'response.txt').read_bytes()!=trace.result.encode():raise ValueError('RESPONSE_BYTES')
        for k,v in [('init_count',trace.init_count),('init_errors',trace.init_errors),('observed_models',trace.models),('tool_event_seen',trace.tool),('unknown_events',trace.unknown)]:
            if result[k]!=v:raise ValueError('TRACE_SUMMARY '+k)
        last=datetime.datetime.fromisoformat(audit['audited_at'])
    slot,raws,validity=run_slot.prior(root,slots)
    if slot is not None:raise ValueError('INCOMPLETE_RUN')
    expected=score.score(raws,validity) if raws is not None else {'status':'INVALID'}
    expected['remaining']=[dict(slot=s['slot'],status='NOT_RUN') for s in slots if not (root/str(s['slot'])).exists()]
    if expected!=read(root/'decision.json'):raise ValueError('DECISION')
    print(json.dumps({'ok':True,'status':expected['status'],'model_calls':0}))

if __name__=='__main__':main()
