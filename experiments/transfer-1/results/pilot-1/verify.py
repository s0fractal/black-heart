"""Verify retained pilot receipts without model calls or rewriting evidence."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'harness'))
from common import sha
from decision import decide


def read(path):
    return json.loads(path.read_text())


def main():
    for name, digest in read(ROOT / 'retained-sha256.json').items():
        assert sha(ROOT / name) == digest, name
    ci = read(ROOT / 'ci-before-live.json')
    summary = read(ROOT / 'summary.json')
    assert ci['headRefOid'] == summary['reviewed_head']
    checks = ci['statusCheckRollup']
    assert len(checks) == 8 and all(c['conclusion'] == 'SUCCESS' for c in checks)
    rows = []
    previous_audit = None
    for i in (1, 2, 3):
        p = ROOT / str(i)
        result, audit, invocation, claim, grade = [read(p / (n + '.json')) for n in
                                                  ('result', 'audit', 'invocation', 'claim', 'grade')]
        assert audit['result_sha256'] == sha(p / 'result.json')
        assert audit['events_sha256'] == sha(p / 'public-events.jsonl')
        assert grade['source_sha256'] == sha(p / 'reader.py')
        assert grade['valid'] and grade['pass'] and all(c['pass'] for c in grade['cases'])
        assert result['valid'] and audit['valid'] and all(result['protected_inputs'].values())
        assert claim['reviewed_head'] == summary['reviewed_head']
        assert claim['claimed_at'] <= invocation['started_at'] <= result['finished_at'] <= audit['audited_at']
        assert all(c['completedAt'] <= invocation['started_at'] for c in checks)
        if previous_audit:
            assert previous_audit <= claim['claimed_at']
        previous_audit = audit['audited_at']
        assert read(p / 'preflight.json')['pass']
        rows.append({'arm': result['arm'], 'pass': result['pass'], 'valid': True})
    saved = read(ROOT / 'decision.json')
    assert saved['recorded_at'] >= previous_audit
    del saved['recorded_at']
    assert decide(rows) == saved
    assert saved['status'] == 'EARLY_UNIFORM_SUCCESS'
    print(json.dumps({'ok': True, 'decision': saved}, indent=2))


if __name__ == '__main__':
    main()
