"""Verify the retained block-1 receipts without model calls or rewriting evidence.

Adapted from experiments/transfer-1/results/pilot-1/verify.py: retained
digests, audit digests, chronological order (claim <= start <= finish <=
audit, previous audit <= next claim), preflight pass, and the frozen decision
rule recomputed from the retained rows. The reviewed head in summary.json
must be the accepted package commit whose freeze.json is committed beside
this directory.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'harness'))
from common import sha  # noqa: E402
from decision import decide  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def main():
    for name, digest in read(ROOT / 'retained-sha256.json').items():
        assert sha(ROOT / name) == digest, name
    summary = read(ROOT / 'summary.json')
    freeze = read(ROOT.parents[1] / 'execution' / 'package' / 'freeze.json')
    assert summary['snapshot_head'] == freeze['snapshot']['head'] and summary['model'] == freeze['model']
    rows = []
    previous_audit = None
    for i in (1, 2, 3):
        p = ROOT / str(i)
        result, audit, invocation, claim, grade, preflight = [read(p / (n + '.json')) for n in
                                                              ('result', 'audit', 'invocation', 'claim', 'grade', 'preflight')]
        assert audit['result_sha256'] == sha(p / 'result.json'), i
        assert audit['events_sha256'] == sha(p / 'public-events.jsonl'), i
        assert claim['reviewed_head'] == summary['reviewed_head'] and claim['slot'] == i
        assert claim['claimed_at'] <= invocation['started_at'] <= result['finished_at'] <= audit['audited_at'], i
        if previous_audit:
            assert previous_audit <= claim['claimed_at'], i
        previous_audit = audit['audited_at']
        assert preflight['pass'] and preflight['auth']['seconds_remaining'] >= preflight['auth']['margin_seconds'], i
        assert result['infrastructure_valid'] and audit['valid'] and all(result['protected_inputs'].values()), i
        assert grade['outcome'] == result['grader_outcome'] == result['classification'], i
        assert grade['baseline_sha256'] == sha(ROOT.parents[1] / 'inputs' / 'test_mycelium.baseline-198f9e2.py'), i
        assert result['model_reported'] == [summary['model']], i
        assert not result['unknown_event_types'] and result['malformed_events'] == 0 and not result['init_errors'], i
        rows.append({'slot': i, 'classification': result['classification']})
    saved = read(ROOT / 'decision.json')
    assert saved['recorded_at'] >= previous_audit
    del saved['recorded_at']
    assert decide(rows) == saved
    assert saved['status'] == 'COMPLETE' and saved['counts'] == {'INVALID': 0, 'PASS': 2, 'FAIL': 1, 'PARTIAL': 0}
    print(json.dumps({'ok': True, 'decision': saved}, indent=2))


if __name__ == '__main__':
    main()
