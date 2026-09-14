"""Offline fixture checks only: no model calls, no study launcher."""
import argparse
import hashlib
import importlib.util
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from glyph import evaluate, parse
from crypto import public_key_from_secret, sign_bytes, verify_bytes


def collect():
    spec = importlib.util.spec_from_file_location('bh_static_inspector', ROOT/'tools/sandbox.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    def evaluation(budget):
        result = evaluate(parse('S K K I'), max_atp=budget)
        return {'status':result.status.value,'term':str(result.term),'equals_I':result.term == parse('I'),'steps':result.steps}
    # Public deterministic TEST seed, never an identity or production key.
    seed=bytes(range(32)); payload=b'fixture: claim bytes, not an identity assertion'
    pk=public_key_from_secret(seed); signature=sign_bytes(seed,payload)
    report=module.PolyglotAuditReport('synthetic-no-file',0,'0'*64,True,True,0,[],False,False,[])
    empty=report.is_sound()
    report.verified_seal_count=1
    positive=report.is_sound()
    report.audit_error_count=1
    error=report.is_sound()
    return {'evaluation':{'budget_0':evaluation(0),'budget_2':evaluation(2)},
            'signature':{'valid_payload':verify_bytes(pk,payload,signature),
                         'changed_payload':verify_bytes(pk,payload+b'!',signature),
                         'public_key_hex':pk.hex(),'identity_mapping_supplied':False},
            'report_predicate':{'empty':empty,'one_positive_seal':positive,'positive_with_error':error,
                                'scope':report.scope_summary(),
                                'scope_limit':'Synthetic dataclass predicate only; no PDF parsed or audited.'}}


def checks(data):
    return {'budget_zero_suspended':data['evaluation']['budget_0']['status']=='SUSPENDED',
            'budget_two_settled':(data['evaluation']['budget_2']['status']=='SETTLED' and data['evaluation']['budget_2']['equals_I'] and data['evaluation']['budget_2']['steps']==2),
            'valid_signature_accepted':data['signature']['valid_payload'] is True,
            'changed_payload_refused':data['signature']['changed_payload'] is False,
            'empty_not_sound':data['report_predicate']['empty'] is False,
            'positive_sound':data['report_predicate']['one_positive_seal'] is True,
            'error_not_sound':data['report_predicate']['positive_with_error'] is False}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);args=parser.parse_args()
    if args.output.exists(): raise SystemExit('OUTPUT_EXISTS')
    data=collect(); passed=checks(data)
    import copy
    mutations={}
    for name,path,value in [('suspension_as_success',('evaluation','budget_0','status'),'SETTLED'),
                            ('accept_changed_bytes',('signature','changed_payload'),True),
                            ('empty_report_as_sound',('report_predicate','empty'),True),
                            ('error_as_sound',('report_predicate','positive_with_error'),True)]:
        m=copy.deepcopy(data); target=m
        for key in path[:-1]: target=target[key]
        target[path[-1]]=value
        mutations[name]=[k for k,v in checks(m).items() if not v]
    sources={}
    for name in ('glyph.py','crypto.py','tools/sandbox.py','dialectic_kernel.py'):
        raw=(ROOT/name).read_bytes();sources[name]=hashlib.sha256(raw).hexdigest()
    result={'kind':'OFFLINE_FIXTURE_CHECK_NOT_ANNOTATOR_STUDY','recorded_at':datetime.now(timezone.utc).isoformat(),
            'repository_head':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
            'python':platform.python_version(),'probe_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'sources':sources,'observed':data,'checks':passed,'receipt_mutation_checks':mutations,
            'limits':['Receipt mutations check oracle sensitivity, not implementation mutation coverage.',
                      'No person identity, semantic binding or whole-document correctness was verified.']}
    with args.output.open('x') as f: json.dump(result,f,indent=2);f.write('\n')
    assert all(passed.values()) and all(mutations.values()),'OFFLINE_CHECK_FAILED'
    print(json.dumps({'ok':True,'checks':len(passed),'receipt_mutations_detected':len(mutations)}))

if __name__=='__main__': main()
