"""Opt-in, trusted-local cache for the ledger and continuum CLI auditors."""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 16 * 1024 * 1024
ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C', 'PYTHONHASHSEED': '0'}


def encode(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def entry_digest(key, result):
    return digest(encode({'key': key, 'result': result}))


def bounded(path):
    with Path(path).open('rb') as f:
        raw = f.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError('SIZE_LIMIT')
    return raw


def route(raw):
    allowed = {b'%\xf0\x9f\x96\xa4 LEDGER_MANIFEST:', b'%\xf0\x9f\x96\xa4 CONTINUUM_THUNK:'}
    found = set()
    for line in raw.splitlines():
        if line.startswith(b'# %'):
            raise ValueError('UNSUPPORTED_ROUTE')
        if line.startswith('%🖤 '.encode()) and b':' in line:
            prefix = line.split(b':', 1)[0] + b':'
            if prefix not in allowed:
                raise ValueError('UNSUPPORTED_ROUTE')
            found.add(prefix)
    if len(found) != 1:
        raise ValueError('AMBIGUOUS_OR_UNSUPPORTED_ROUTE')


def snapshot():
    paths = list(ROOT.glob('*.py'))
    for folder in ('tools', 'continuation'):
        paths += list((ROOT / folder).rglob('*.py'))
    files = {str(p.relative_to(ROOT)): bounded(p) for p in sorted(paths)}
    if sum(map(len, files.values())) > 64 * 1024 * 1024:
        raise ValueError('SOURCE_SIZE')
    profile = {'schema': 'black-heart-local-cache/1',
               'sources': {n: digest(b) for n, b in files.items()},
               'python': sys.version, 'executable': digest(Path(sys.executable).read_bytes()),
               'platform': platform.platform(), 'env': ENV, 'flags': ['-B', '-s', '-S'],
               'command': ['cli.py', 'verify'],
               'scope': 'trusted same-host stdlib and shared libraries; no external identity or freshness'}
    return files, digest(encode(profile))


def execute(source, raw, timeout):
    # Execute the exact captured source and operand; original paths cannot race
    # the child after their bytes have been hashed.
    with tempfile.TemporaryDirectory(prefix='black-heart-verify-') as tmp:
        root = Path(tmp)
        for name, data in source.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        operand = root / 'operand.pdf'
        operand.write_bytes(raw)
        try:
            p = subprocess.run([sys.executable, '-B', '-s', '-S', str(root / 'cli.py'),
                                'verify', str(operand)], cwd=root, env=ENV,
                               capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {'exit_code': None, 'stdout': '', 'stderr': '', 'state': 'TIMEOUT'}
    return {'exit_code': p.returncode, 'stdout': p.stdout.decode(errors='replace'),
            'stderr': p.stderr.decode(errors='replace'), 'state': 'COMPLETED'}


def read_cache(path):
    if not path.exists():
        return {'schema': 1, 'entries': {}}
    cache = json.loads(bounded(path))
    if not isinstance(cache, dict) or set(cache) != {'schema', 'entries'} or type(cache['schema']) is not int or cache['schema'] != 1 or not isinstance(cache['entries'], dict):
        raise ValueError('CACHE_SHAPE')
    for key, entry in cache['entries'].items():
        if not isinstance(key, str) or len(key) != 64 or any(c not in '0123456789abcdef' for c in key):
            raise ValueError('CACHE_KEY')
        if not isinstance(entry, dict) or set(entry) != {'result', 'sha256'}:
            raise ValueError('CACHE_ENTRY')
        result = entry['result']
        if not isinstance(result, dict) or set(result) != {'exit_code', 'stdout', 'stderr', 'state'} or type(result['exit_code']) is not int or result['exit_code'] not in (0, 1) or result['state'] != 'COMPLETED' or not all(isinstance(result[n], str) for n in ('stdout', 'stderr')):
            raise ValueError('CACHE_RESULT')
        if entry_digest(key, result) != entry['sha256']:
            raise ValueError('CACHE_CHECKSUM')
    return cache


def save_cache(path, cache):
    raw = encode(cache)
    if len(raw) > LIMIT:
        raise ValueError('CACHE_FULL')
    fd, name = tempfile.mkstemp(prefix='.verify-cache-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(name)


def run(paths, cache_path, fresh=False, timeout=30, batch=False):
    # Validate all operands before creating/updating the cache.
    if not paths:
        raise ValueError('NO_OPERANDS')
    operands = []
    for p in paths:
        path = str(Path(p).absolute())
        try:
            raw = bounded(p)
            route(raw)
        except (OSError, ValueError) as error:
            if not batch:
                raise
            operands.append((path, None, {'path': path, 'status': 'REFUSED',
                                         'origin': 'NOT_RUN', 'reason': str(error)}))
        else:
            operands.append((path, raw, None))
    if not any(error is None for _, _, error in operands):
        return {'schema': 1, 'authority': 'none', 'status': 'INCOMPLETE',
                'items': [error for _, _, error in operands]}
    source, profile = snapshot()
    cache_path = Path(cache_path).absolute()
    if cache_path.resolve() in {Path(p).resolve() for p, _, _ in operands} or cache_path.suffix == '.py':
        raise ValueError('CACHE_PATH')
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with (cache_path.parent / (cache_path.name + '.lock')).open('a+b') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as e:
            raise ValueError('BUSY') from e
        cache = read_cache(cache_path)
        items = []
        for path, raw, error in operands:
            if error is not None:
                items.append(error)
                continue
            key = digest(encode({'profile': profile, 'operand': digest(raw)}))
            if not fresh and key in cache['entries']:
                result = cache['entries'][key]['result']
                origin = 'REUSED'
            else:
                result = execute(source, raw, timeout)
                origin = 'EXECUTED_NOW'
                if result['state'] == 'COMPLETED' and result['exit_code'] in (0, 1):
                    cache['entries'][key] = {'result': result, 'sha256': entry_digest(key, result)}
            status = 'CHECKED' if result['state'] == 'COMPLETED' and result['exit_code'] in (0, 1) else 'UNRESOLVED'
            items.append({'path': path, 'status': status, 'operand_sha256': digest(raw), 'origin': origin,
                          'profile_sha256': profile, 'result': result})
        save_cache(cache_path, cache)
    return {'schema': 1, 'authority': 'none',
            'status': 'INCOMPLETE' if any(i['status'] != 'CHECKED' for i in items) else 'COMPLETE',
            'items': items}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+')
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--fresh', action='store_true')
    parser.add_argument('--batch', action='store_true',
                        help='report unsupported/unreadable inputs individually; overall exit remains nonzero')
    args = parser.parse_args()
    try:
        report = run(args.files, args.cache, args.fresh, batch=args.batch)
    except (OSError, ValueError, TypeError) as e:
        print(json.dumps({'status': 'REFUSED', 'reason': str(e)}))
        return 2
    print(json.dumps(report, ensure_ascii=False))
    if any(i['status'] == 'REFUSED' for i in report['items']):
        return 2
    return 0 if all(i['result']['exit_code'] == 0 for i in report['items']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
