"""Host utilities; never copied into receiver snapshots."""
import hashlib
import json
import os
import signal
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN_HEAD = '0e5d44f22079a6f4f2543b718b18b3968253c2f1'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write_json(path, value):
    with Path(path).open('x') as f:
        f.write(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def verify_inputs():
    hashes = json.loads((ROOT / 'input-sha256.json').read_text())
    for name, digest in hashes.items():
        if sha(ROOT / name) != digest:
            raise ValueError('INPUT_DIGEST_MISMATCH: ' + name)
    return hashes

def environment():
    return dict(PATH='/opt/homebrew/bin:/Library/Developer/CommandLineTools/usr/bin:/usr/bin:/bin:/usr/sbin:/sbin', LANG='C', LC_ALL='C',
                GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                GIT_AUTHOR_NAME='TRANSFER fixture', GIT_AUTHOR_EMAIL='transfer@example.invalid',
                GIT_COMMITTER_NAME='TRANSFER fixture', GIT_COMMITTER_EMAIL='transfer@example.invalid',
                GIT_AUTHOR_DATE='2000-01-01T00:00:00+00:00',
                GIT_COMMITTER_DATE='2000-01-01T00:00:00+00:00')

def run(argv, *, cwd, timeout=10, env=None, stdin=None):
    """Bound the whole process group, including children retaining pipes."""
    p = subprocess.Popen(argv, cwd=cwd, env=env or environment(), stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        out, err = p.communicate(stdin, timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(p.pid, signal.SIGKILL)
        out, err = p.communicate()
    finally:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    return {'exit_code': p.returncode, 'timed_out': timed_out,
            'stdout': out.decode('utf-8', 'replace'), 'stderr': err.decode('utf-8', 'replace')}

def git(repo, *args):
    p = subprocess.run(['git', '-C', str(repo), '-c', 'core.hooksPath=/dev/null',
                        '-c', 'commit.gpgsign=false', '-c', 'tag.gpgSign=false', *args],
                       env=environment(), capture_output=True, check=True, timeout=10)
    return p.stdout.decode().strip()
