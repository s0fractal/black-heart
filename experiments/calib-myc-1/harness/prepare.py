"""Freeze ONE snapshot bundle and a single run directory before review.

Adapted from experiments/transfer-1/harness/prepare.py (temp-storage refusal,
build-under-home, one commit 'receiver input', bundle + freeze.json layout).
Adapted: one condition, one bundle; the snapshot tree is `git archive` of the
pinned revision 198f9e2 read from this repository's object store, plus
inputs/CONTRACT.md and inputs/task.txt at the root. The model id comes from the
CALIB_MODEL environment variable (or the model= argument used by offline.py for
the determinism check) and preparation refuses without it.

Why a single-commit snapshot rather than a history bundle of 198f9e2: the full
history bundle (2.6 MB) would carry commit messages (#81) naming the triage and
DOC-F1; the tree alone keeps only the in-tree ledger hint that PLAN.md already
discloses. The snapshot's tree is checked to equal the source tree plus the two
input files, entry by entry (mode, blob id, path).
"""
import argparse
import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from common import (HARNESS, PLAN_HEAD, PLAN_MERGE, REPO, ROOT, RUNS, SOURCE_MYCELIUM, SOURCE_REVISION, WORK,
                    git, git_bytes, inputs_digests, refuse_temp, sha, sha_bytes, write_json)
from decision import SCHEDULE
from runtime import SETTINGS, TIMEOUT, argv_template, client_identity
import events

SNAPSHOT_FILES = ('mycelium.py', 'test_mycelium.py', 'CONTRACT.md', 'task.txt', 'docs/REMEDIATION-LEDGER.md')


def check_pins():
    if git(ROOT, 'cat-file', '-t', SOURCE_REVISION) != 'commit':
        raise ValueError('SOURCE_REVISION_NOT_A_COMMIT')
    if sha_bytes(git_bytes(ROOT, 'show', SOURCE_REVISION + ':mycelium.py')) != SOURCE_MYCELIUM:
        raise ValueError('SOURCE_MYCELIUM_MISMATCH')
    if sha_bytes(git_bytes(ROOT, 'show', SOURCE_REVISION + ':test_mycelium.py')) != sha(ROOT / 'inputs/test_mycelium.baseline-198f9e2.py'):
        raise ValueError('BASELINE_TEST_MISMATCH')
    for head in (PLAN_HEAD, PLAN_MERGE):
        if git(ROOT, 'cat-file', '-t', head) != 'commit':
            raise ValueError('PLAN_HEAD_NOT_A_COMMIT')
    if git_bytes(ROOT, 'show', PLAN_HEAD + ':experiments/calib-myc-1/PLAN.md') != (ROOT / 'PLAN.md').read_bytes():
        raise ValueError('PLAN_CHANGED_SINCE_ACCEPTANCE')
    return {'source_tree': git(ROOT, 'rev-parse', SOURCE_REVISION + '^{tree}')}


def expected_tree():
    if git(REPO, 'rev-parse', '--show-toplevel') != str(REPO):
        raise ValueError('REPO_TOPLEVEL_MISMATCH')
    entries = set(git(REPO, 'ls-tree', '-r', SOURCE_REVISION, timeout=60).splitlines())
    if not any(e.endswith('\tmycelium.py') for e in entries) or len(entries) < 500:
        raise ValueError('SOURCE_TREE_NOT_LISTED')
    for name in ('CONTRACT.md', 'task.txt'):
        blob = git(ROOT, 'hash-object', str(ROOT / 'inputs' / name))
        entries.add(f'100644 blob {blob}\t{name}')
    return entries


def build_snapshot(snapshot):
    """Extract the pinned tree, add the two inputs, commit once. Returns HEAD."""
    snapshot = Path(snapshot)
    tar = subprocess.Popen(['git', '-C', str(REPO), 'archive', '--format=tar', SOURCE_REVISION], stdout=subprocess.PIPE)
    subprocess.check_call(['tar', '-x', '-C', str(snapshot)], stdin=tar.stdout)
    code = tar.wait(); tar.stdout.close()
    if code != 0 or not (snapshot / 'mycelium.py').is_file():
        raise ValueError('ARCHIVE_FAILED')
    for name in ('CONTRACT.md', 'task.txt'):
        (snapshot / name).write_bytes((ROOT / 'inputs' / name).read_bytes())
    git(snapshot, '-c', 'init.templateDir=', 'init', '-q', '--object-format=sha1')
    git(snapshot, 'add', '-A', '-f', '.', timeout=60)
    git(snapshot, 'commit', '-qm', 'receiver input', timeout=60)
    if set(git(snapshot, 'ls-tree', '-r', 'HEAD', timeout=60).splitlines()) != expected_tree():
        raise ValueError('SNAPSHOT_TREE_MISMATCH')
    if git(snapshot, 'rev-list', '--count', 'HEAD') != '1':
        raise ValueError('SNAPSHOT_HISTORY')
    return git(snapshot, 'rev-parse', 'HEAD')


def prepare(output, model=None):
    output = refuse_temp(output, 'PACKAGE_OUTPUT_MUST_BE_OUTSIDE_TEMP_STORAGE')
    model = model or os.environ.get('CALIB_MODEL', '')
    if not model.strip():
        raise ValueError('CALIB_MODEL_UNSET')
    pins = check_pins()
    inputs = inputs_digests()
    client = client_identity()
    output.mkdir(parents=True, exist_ok=False)
    build_root = Path.home() / WORK / 'build'; build_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='snapshot-', dir=build_root) as td:
        snapshot = Path(td)
        head = build_snapshot(snapshot)
        bundle = output / 'snapshot.bundle'
        git(snapshot, 'bundle', 'create', str(bundle), 'HEAD', timeout=120)
        files = {name: sha(snapshot / name) for name in SNAPSHOT_FILES}
    frozen = {'plan_head': PLAN_HEAD, 'plan_merge': PLAN_MERGE, 'preparation_head': git(ROOT, 'rev-parse', 'HEAD'),
              'source_revision': SOURCE_REVISION, 'source_tree': pins['source_tree'],
              'run_root': '~/' + RUNS + '/' + uuid.uuid4().hex,
              'model': model, 'client_version': client['client_version'],
              'claude_binary_sha256': client['claude_binary_sha256'],
              'claude_binary': {'which': client['which'], 'resolved': client['resolved'],
                                'is_shell_wrapper': client['is_shell_wrapper']},
              'settings': SETTINGS, 'argv_template': argv_template(model), 'timeout_seconds': TIMEOUT,
              'schedule': list(SCHEDULE), 'inputs': inputs,
              'snapshot': {'bundle': bundle.name, 'sha256': sha(bundle), 'head': head, 'files': files},
              'harness': {p.name: sha(p) for p in sorted(HARNESS.glob('*.py'))},
              'controls_summary_sha256': sha(ROOT / 'controls' / 'SUMMARY.json'),
              'init_policy': events.policy(),
              'status': 'PREPARED_NOT_LAUNCHED; exact package commit requires review'}
    write_json(output / 'freeze.json', frozen)
    return frozen


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('output', type=Path)
    print(json.dumps({k: v for k, v in prepare(parser.parse_args().output).items() if k != 'argv_template'}, indent=2))
