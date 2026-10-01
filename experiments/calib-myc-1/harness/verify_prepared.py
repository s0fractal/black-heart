"""Offline bundle readback: exact tree, one-commit history, no remotes. Also materialize().

Adapted from experiments/transfer-1/harness/verify_prepared.py for one bundle;
the tracked-file check compares the full `ls-tree -r` entry set (mode, blob,
path) with the source tree plus the two inputs. materialize() is the shared
unbundle-into-a-neutral-receiver-directory step used by run_slot.py and
offline.py.
"""
import argparse
import tempfile
from pathlib import Path
from common import git, read_json, sha, write_json
from prepare import expected_tree
from runtime import receivers


def materialize(package, frozen, prefix='receiver-'):
    """Neutral random path; no condition labels or preceding session outputs inside it."""
    parent = receivers(); parent.mkdir(parents=True, exist_ok=True)
    snapshot = Path(tempfile.mkdtemp(prefix=prefix, dir=parent))
    expected = frozen['snapshot']
    bundle = (Path(package) / expected['bundle']).resolve()
    if sha(bundle) != expected['sha256']:
        raise ValueError('BUNDLE_CHANGED')
    git(snapshot, '-c', 'init.templateDir=', 'init', '-q', '--object-format=sha1')
    git(snapshot, 'bundle', 'unbundle', str(bundle), timeout=120)
    git(snapshot, 'checkout', '--detach', expected['head'], timeout=120)
    if git(snapshot, 'rev-parse', 'HEAD') != expected['head']:
        raise ValueError('SNAPSHOT_HEAD')
    for name, digest in expected['files'].items():
        if (snapshot / name).is_symlink() or sha(snapshot / name) != digest:
            raise ValueError('SNAPSHOT_BYTES')
    return snapshot


def verify(package):
    package = Path(package)
    frozen = read_json(package / 'freeze.json')
    data = frozen['snapshot']
    bundle = (package / data['bundle']).resolve()
    assert sha(bundle) == data['sha256']
    work = Path.home() / 'calib1-work' / 'readback'; work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='snapshot-', dir=work) as td:
        root = Path(td)
        git(root, '-c', 'init.templateDir=', 'init', '-q', '--object-format=sha1')
        git(root, 'bundle', 'verify', str(bundle), timeout=120)
        git(root, 'bundle', 'unbundle', str(bundle), timeout=120)
        git(root, 'checkout', '--detach', data['head'], timeout=120)
        assert git(root, 'rev-list', '--count', 'HEAD') == '1'
        assert git(root, 'log', '-1', '--format=%an <%ae> %s') == 'CALIB fixture <calib@example.invalid> receiver input'
        entries = set(git(root, 'ls-tree', '-r', 'HEAD', timeout=60).splitlines())
        assert entries == expected_tree()
        assert all(sha(root / name) == digest for name, digest in data['files'].items())
        assert not (root / '.git/FETCH_HEAD').exists()
        assert not git(root, 'remote')
        assert not git(root, 'status', '--porcelain', timeout=60)
        tracked = len(entries)
    return {'pass': True, 'freeze_sha256': sha(package / 'freeze.json'), 'bundle_sha256': data['sha256'],
            'head': data['head'], 'tracked_entries': tracked, 'history_commits': 1}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('package', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); write_json(args.output, verify(args.package))
    print('Prepared bundle readback passed; no receiver called.')
