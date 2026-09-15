"""Host utilities for CALIB-MYC-1; never copied into receiver snapshots.

Copied from experiments/transfer-1/harness/common.py (sha, write_json,
environment, run, git). Adapted: PLAN_HEAD is the commit of the accepted plan
file and PLAN_MERGE the merge that made it reachable from main; fixture
identity 'CALIB fixture' / calib@example.invalid; RUNS/WORK roots are
~/calib1-runs and ~/calib1-work. New: SOURCE_* pins from PLAN.md,
inputs_digests() (there is no input-sha256.json; the three inputs are digested
directly), portable()/expand() so tracked receipts never carry the host home
path, and refuse_temp() shared by prepare.py and offline.py.
"""
import hashlib
import json
import os
import signal
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]  # git archive / ls-tree are cwd-relative: always run them at the top level
HARNESS = Path(__file__).resolve().parent
PLAN_HEAD = 'a628bc5c6a09da36d9d75dc97b7c13e7bf317e95'   # plan(calib-myc-1): revision 2
PLAN_MERGE = '4ad65c8a7018a5e76894cdd7dd3e7456467f1b92'  # Merge pull request #86
SOURCE_REVISION = '198f9e2b64934f2e67b01df9128d1e57c2079407'
SOURCE_MYCELIUM = 'deb9928e31d3219c59e55edbdacb7223bb4028b1de482bd02dad0c9f0b31d29a'
INPUTS = ('CONTRACT.md', 'task.txt', 'test_mycelium.baseline-198f9e2.py')
RUNS = 'calib1-runs'
WORK = 'calib1-work'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    with Path(path).open('x') as f:
        f.write(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def read_json(path):
    return json.loads(Path(path).read_text())


def inputs_digests():
    return {name: sha(ROOT / 'inputs' / name) for name in INPUTS}


def portable(path):
    """Tracked receipts carry '~/...' instead of the host home path."""
    text = str(path)
    home = str(Path.home())
    return '~' + text[len(home):] if text == home or text.startswith(home + '/') else text


def portable_json(value):
    """Apply portable() to every string in a JSON-like value; the OS temp dir becomes <TMPDIR>."""
    if isinstance(value, dict):
        return {k: portable_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [portable_json(v) for v in value]
    if isinstance(value, str):
        home = str(Path.home()); tmp = str(Path(tempfile.gettempdir()).resolve())
        if tmp in value:
            value = value.replace(tmp, '<TMPDIR>')
        return value.replace(home + '/', '~/').replace(home, '~') if home in value else value
    return value


def expand(text):
    return Path(os.path.expanduser(text)) if str(text).startswith('~/') else Path(text)


def refuse_temp(path, name):
    path = Path(path).resolve()
    if any(path.is_relative_to(Path(p).resolve()) for p in ('/private/tmp', '/private/var/tmp', tempfile.gettempdir())):
        raise ValueError(name)
    return path


def environment():
    """Deterministic host-side git environment for snapshot building."""
    return dict(PATH='/opt/homebrew/bin:/Library/Developer/CommandLineTools/usr/bin:/usr/bin:/bin:/usr/sbin:/sbin',
                HOME=str(Path.home()), LANG='C', LC_ALL='C',
                GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                GIT_AUTHOR_NAME='CALIB fixture', GIT_AUTHOR_EMAIL='calib@example.invalid',
                GIT_COMMITTER_NAME='CALIB fixture', GIT_COMMITTER_EMAIL='calib@example.invalid',
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


def git(repo, *args, timeout=10):
    p = subprocess.run(['git', '-C', str(repo), '-c', 'core.hooksPath=/dev/null',
                        '-c', 'commit.gpgsign=false', '-c', 'tag.gpgSign=false',
                        '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-c', 'core.fsmonitor=false', *args],
                       env=environment(), capture_output=True, check=True, timeout=timeout)
    return p.stdout.decode().strip()


def git_bytes(repo, *args, timeout=30):
    return subprocess.run(['git', '-C', str(repo), *args], env=environment(),
                          capture_output=True, check=True, timeout=timeout).stdout
