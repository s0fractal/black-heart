"""Check card evidence correspondence offline; no model calls or saved rewrites."""
import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path
import probe

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    for name, digest in json.loads((HERE/'sha256.json').read_text()).items():
        assert hashlib.sha256((HERE/name).read_bytes()).hexdigest() == digest, name
    cards = json.loads((HERE/'cards.json').read_text())
    assert len(cards) == 8 and len({c['id'] for c in cards}) == 8
    observed = json.loads((HERE/'offline.json').read_text())['observed']
    assert probe.collect() == observed
    cls = sys.modules['bh_static_inspector'].PolyglotAuditReport
    report = cls('synthetic-no-file',0,'0'*64,True,True,0,[],False,False,[])
    states = {}
    for label, seals, errors in [('is_sound_for_empty_report',0,0),
                                 ('is_sound_with_one_positive_seal',1,0),
                                 ('is_sound_with_positive_seal_and_error',1,1)]:
        report.verified_seal_count = seals
        report.audit_error_count = errors
        states[label] = (vars(report).copy(), report.is_sound())
    receipts = 0
    for card in cards:
        context = card['context']
        if 'source' in context:
            s = context['source']
            raw = subprocess.check_output(['git','-C',str(ROOT),'show',s['commit']+':'+s['path']])
            assert hashlib.sha256(raw).hexdigest() == s['file_sha256']
            assert '\n'.join(raw.decode().splitlines()[s['start_line']-1:s['end_line']]) == s['text']
        if 'receipt' not in context:
            continue
        receipts += 1
        if card['family'] == 'report':
            mapping = context['receipt_field_mapping']
            expected = observed['report_predicate'].copy()
            for old in ('empty','one_positive_seal','positive_with_error'):
                expected[mapping[old]] = expected.pop(old)
            assert context['receipt'] == expected
            assert set(context['synthetic_report_inputs']) == set(states)
            for label, inputs in context['synthetic_report_inputs'].items():
                actual, result = states[label]
                assert set(inputs) == {'is_valid_iso32000','binary_marker_present',
                    'passed_claim_count','unconfirmed_seal_count','seal_mismatch_count',
                    'failed_claim_count','verified_seal_count','audit_error_count'}
                assert all(actual[k] == v and type(actual[k]) is type(v) for k,v in inputs.items())
                assert result is context['receipt'][label]
        else:
            group = {'reduction':'evaluation','signature':'signature'}[card['family']]
            assert context['receipt'] == observed[group]
    schedule = json.loads((HERE/'schedule.json').read_text())
    for slot in schedule['slots']:
        ids = [c['id'] for c in cards]
        random.Random(914260+slot['slot']).shuffle(ids)
        assert ids == slot['order']
    key = json.loads((HERE/'review-key.json').read_text())['items']
    assert set(key) == {c['id'] for c in cards}
    assert all(v['rationale'].strip() for v in key.values())
    print(json.dumps({'ok':True,'cards':len(cards),'receipts':receipts,
                      'synthetic_report_states':len(states),'model_calls':0}))


if __name__ == '__main__':
    main()
