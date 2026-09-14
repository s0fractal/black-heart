"""No inference: native request capture and mechanical regressions. macOS only."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import context_check
import context_probe
import runtime

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
REPO=BASE.parents[1]

def main(output):
    output=output.resolve()
    if Path.home() not in output.parents or (Path.home()/'Projects') in output.parents:
        raise ValueError('OUTPUT_MUST_BE_UNDER_HOME_OUTSIDE_PROJECTS')
    output.mkdir(parents=True,exist_ok=False)
    parent=Path.home()/'rvb-bh-1a-work';parent.mkdir(exist_ok=True)
    checks=[]
    for slot in json.loads((BASE/'schedule.json').read_text())['slots']:
        prompt=(HERE/'stimuli'/f"{slot['slot']}.txt").read_text()
        captured=context_probe.capture(slot['annotator'],prompt,parent)
        (output/f"{slot['slot']}.json").write_text(json.dumps(captured,indent=2)+'\n')
        checks.append({'slot':slot['slot'],**context_check.check(captured,prompt)})
    prompt='OFFLINE CONTEXT PROBE. Return only probe-ok.'
    for name,unhardened in [('canary-hardened',False),('canary-positive-control',True)]:
        with tempfile.TemporaryDirectory(prefix='synthetic-home-',dir=parent) as home:
            captured=context_probe.capture('B',prompt,parent,home,unhardened)
        (output/f'{name}.json').write_text(json.dumps(captured,indent=2)+'\n')
        visible=any(captured['canary'] in json.dumps(q) for q in captured['requests'])
        if visible!=unhardened:raise ValueError('CANARY_CONTROL_FAILED')
        if not unhardened:context_check.check(captured,prompt)
        else:
            try:context_check.check(captured,prompt)
            except ValueError:pass
            else:raise ValueError('CONTEXT_CHECK_ACCEPTED_CANARY')
        checks.append({'control':name,'marker_visible':visible,'ok':True})
    # This probe must fail at the OS permission boundary, not at an Internet timeout.
    network_code="import socket; s=socket.socket(); s.settimeout(2)\ntry:s.connect(('1.1.1.1',443))\nexcept PermissionError:print('REMOTE_DENIED');raise SystemExit(0)\nexcept OSError as e:print(type(e).__name__);raise SystemExit(2)\nraise SystemExit(3)"
    probe=subprocess.run(['/usr/bin/sandbox-exec','-p',context_probe.PROFILE,sys.executable,'-c',network_code],capture_output=True,text=True,timeout=5)
    if probe.returncode!=0 or probe.stdout.strip()!='REMOTE_DENIED':raise ValueError('REMOTE_NETWORK_NOT_DENIED')
    checks.append({'control':'remote numeric TCP endpoint denied by OS','exit_code':probe.returncode,'stdout':probe.stdout,'stderr':probe.stderr,'ok':True})
    binary=Path(shutil.which('claude')).resolve()
    receipt={'status':'OFFLINE_CONTEXT_CAPTURE_ONLY','model_calls':0,'checks':checks,
             'version':subprocess.check_output(['claude','--version'],text=True).strip(),
             'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
             'models_requested':runtime.MODELS,
             'auth_limit':'Dummy API-key local transport; native Max auth path is not captured or asserted equivalent.',
             'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.glob('*.json'))},
             'sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.glob('*.py'))}}
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'ok':True,'model_calls':0,'checks':len(checks),'output':str(output)}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);args=parser.parse_args();main(args.output)
