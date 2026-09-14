"""Verify retained package bytes and offline context receipts; no client launch."""
import hashlib
import json
import subprocess
from pathlib import Path
import context_check
import events
import runtime

HERE=Path(__file__).resolve().parent
CAPTURE_SOURCE_HEAD='3e42c3f00eefd22706faef46196855122bb97dbc'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    freeze=json.loads((HERE/'freeze.json').read_text())
    for name,expected in freeze['files'].items():
        if digest(HERE/name)!=expected:raise ValueError('FREEZE_HASH: '+name)
    receipt=json.loads((HERE/'context'/'receipt.json').read_text())
    for name,expected in receipt['files'].items():
        if digest(HERE/'context'/name)!=expected:raise ValueError('CAPTURE_HASH: '+name)
    for name,expected in receipt['sources'].items():
        raw=subprocess.check_output(['git','-C',str(HERE),'show',CAPTURE_SOURCE_HEAD+':experiments/rvb-bh-1a/execution/'+name])
        if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('CAPTURE_SOURCE_CHANGED: '+name)
    for slot in range(1,5):
        capture=json.loads((HERE/'context'/f'{slot}.json').read_text())
        context_check.check(capture,(HERE/'stimuli'/f'{slot}.txt').read_text())
        events.probe_init(capture,runtime.MODELS[capture['annotator']])
    print(json.dumps({'ok':True,'frozen_files':len(freeze['files']),'checked_stimuli':4,'model_calls':0}))

if __name__=='__main__':main()
