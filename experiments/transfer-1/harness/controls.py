"""Host-only reference and the five preregistered negative controls."""
from common import ROOT

def sources():
    baseline = (ROOT / 'inputs/common/reader.py').read_text()
    start = baseline.index('    resolved =')
    end = baseline.index('    result =', start)
    reference = baseline[:start] + "    if git('cat-file', '-t', revision).stdout != b'commit\\n':\n        raise Refusal('INVALID_COMMIT')\n    commit = revision\n" + baseline[end:]
    post_peel = baseline.replace('    result =', "    if git('cat-file', '-t', commit).stdout != b'commit\\n':\n        raise Refusal('INVALID_COMMIT')\n    result =")
    return {
        'reference': reference,
        'type check only after peeling': post_peel,
        'refuse all revisions': reference.replace('    if not isinstance', "    raise Refusal('INVALID_COMMIT')\n    if not isinstance"),
        'accept any object peelable to commit (flawed baseline)': baseline,
        'missing object classified as INVALID_COMMIT': reference.replace("if git('cat-file', '-e', revision).returncode:\n        raise Refusal('MISSING_SOURCE')", "if git('cat-file', '-e', revision).returncode:\n        raise Refusal('INVALID_COMMIT')"),
        'decode blob to text or decode and re-encode with replacement': reference.replace('return result.stdout', "return result.stdout.decode('utf-8', 'replace').encode('utf-8')"),
    }
