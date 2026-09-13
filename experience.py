#!/usr/bin/env python3
"""CM-2: local, data-only experience packets. No evaluator or command runner."""
import argparse
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

PROFILE = 'black-heart.model-experience.draft.v1'
PACKET = 'black-heart.experience-packet.v1'
MAX_RECORD = 1024 * 1024
MAX_SOURCE = 8 * MAX_RECORD
MAX_PACKET = 64 * MAX_RECORD


class Refusal(Exception):
    def __init__(self, code, detail):
        self.code, self.detail = code, detail
        super().__init__(detail)


def refuse(code, detail):
    raise Refusal(code, detail)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fields(value, required, where):
    if not isinstance(value, dict):
        refuse('FIELD_TYPE', where + ' must be an object')
    missing = set(required) - value.keys()
    if missing:
        refuse('FIELD_MISSING', where + ': ' + ', '.join(sorted(missing)))
    if value.keys() - set(required):
        refuse('UNSUPPORTED_FIELD', where)


def string(value, where, nullable=False):
    if nullable and value is None:
        return
    if not isinstance(value, str):
        refuse('FIELD_TYPE', where + ' must be a string')
    # JSON can encode lone surrogates, which are not Unicode scalar values.
    try:
        value.encode('utf-8')
    except UnicodeError:
        refuse('INVALID_UTF8', where)


def strings_object(value, keys, where, nullable=True):
    fields(value, keys, where)
    for key in keys:
        string(value[key], where + '.' + key, nullable)


def array(value, where):
    if not isinstance(value, list):
        refuse('FIELD_TYPE', where + ' must be an array')


def hex_value(value, length, where):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{%d}' % length, value):
        refuse('INVALID_DIGEST' if length == 64 else 'INVALID_COMMIT', where)


def relative(value):
    string(value, 'path')
    if not value or '\\' in value or '\x00' in value or any(
        p in ('', '.', '..') for p in value.split('/')
    ) or value.startswith('/'):
        refuse('UNSAFE_PATH', repr(value))
    return value.split('/')


def parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                refuse('DUPLICATE_KEY', key)
            result[key] = value
        return result
    def constant(value):
        refuse('INVALID_JSON', value)
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                          parse_constant=constant)
    except UnicodeError:
        refuse('INVALID_UTF8', 'JSON must be UTF-8')
    except (ValueError, RecursionError) as exc:
        refuse('INVALID_JSON', str(exc))


def validate(raw):
    if len(raw) > MAX_RECORD:
        refuse('TOO_LARGE', 'record')
    r = parse(raw)
    if not isinstance(r, dict):
        refuse('FIELD_TYPE', 'record must be an object')
    if 'profile' not in r:
        refuse('FIELD_MISSING', 'profile')
    if r['profile'] != PROFILE:
        refuse('UNSUPPORTED_PROFILE', repr(r['profile']))
    fields(r, ['profile', 'id', 'task', 'revision', 'attempt', 'observations',
               'evidence', 'interpretation', 'advice', 'limits', 'provenance', 'relations'], 'record')
    string(r['id'], 'id')
    if not r['id']:
        refuse('FIELD_TYPE', 'id must not be empty')
    strings_object(r['task'], ['summary', 'component', 'context', 'applicability'], 'task')
    strings_object(r['revision'], ['repository', 'commit'], 'revision')
    if r['revision']['commit'] is not None:
        hex_value(r['revision']['commit'], 40, 'revision.commit')
    fields(r['attempt'], ['operation', 'conditions', 'argv', 'cwd'], 'attempt')
    for key in ['operation', 'conditions', 'cwd']:
        string(r['attempt'][key], 'attempt.' + key, True)
    array(r['attempt']['argv'], 'argv')
    for value in r['attempt']['argv']:
        string(value, 'argv member')
    for key in ['interpretation', 'advice']:
        string(r[key], key, True)
    for key in ['evidence', 'observations', 'limits', 'relations']:
        array(r[key], key)
    for value in r['limits']:
        string(value, 'limits member')
    strings_object(r['provenance'], ['compiler', 'model', 'session', 'recorded_at',
                                    'signer_key', 'authentication'], 'provenance')
    ids = set()
    for e in r['evidence']:
        fields(e, ['id', 'kind', 'path', 'commit', 'sha256', 'locator'], 'evidence')
        string(e['id'], 'evidence.id')
        if not e['id'] or e['id'] in ids:
            refuse('DUPLICATE_EVIDENCE_ID', e['id'])
        ids.add(e['id'])
        relative(e['path'])
        hex_value(e['sha256'], 64, 'evidence.sha256')
        string(e['locator'], 'evidence.locator', True)
        if e['kind'] == 'git_blob':
            hex_value(e['commit'], 40, 'evidence.commit')
        elif e['kind'] == 'file':
            if e['commit'] is not None:
                refuse('FIELD_TYPE', 'file evidence commit must be null')
        else:
            refuse('UNSUPPORTED_KIND', repr(e['kind']))
    for o in r['observations']:
        fields(o, ['basis', 'statement', 'evidence_ids'], 'observation')
        if o['basis'] not in ('reported', 'replayed', 'source_read'):
            refuse('UNSUPPORTED_BASIS', repr(o['basis']))
        string(o['statement'], 'statement', True)
        array(o['evidence_ids'], 'evidence_ids')
        for value in o['evidence_ids']:
            string(value, 'evidence_ids member')
            if value not in ids:
                refuse('MISSING_SOURCE', value)
    for relation in r['relations']:
        fields(relation, ['relation', 'target', 'explanation'], 'relation')
        if relation['relation'] not in ('supports', 'contradicts', 'refines'):
            refuse('UNSUPPORTED_RELATION', repr(relation['relation']))
        string(relation['explanation'], 'explanation', True)
        t = relation['target']
        strings_object(t, ['repository', 'commit', 'path', 'sha256'], 'target', False)
        hex_value(t['commit'], 40, 'target.commit')
        hex_value(t['sha256'], 64, 'target.sha256')
        relative(t['path'])
    return r


def read_file(root, name, limit):
    """Traverse untrusted relative components without following symlinks."""
    parts = relative(name)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        source = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(source, 'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                refuse('UNSAFE_PATH', name + ' is not a regular file')
            raw = stream.read(limit + 1)
            if len(raw) > limit:
                refuse('TOO_LARGE', name)
            return raw
    except FileNotFoundError:
        refuse('MISSING_SOURCE', name)
    finally:
        os.close(fd)


def git_blob(repo, commit, path):
    # Shape alone is insufficient: Git also accepts TREE:path. Both evidence
    # and relation targets must name an actual commit before resolving a path.
    object_type = subprocess.run(['git', '-C', str(repo), 'cat-file', '-t', commit],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if object_type.returncode:
        refuse('MISSING_SOURCE', commit)
    if object_type.stdout.strip() != b'commit':
        refuse('INVALID_COMMIT', commit + ' does not name a Git commit object')
    size = subprocess.run(['git', '-C', str(repo), 'cat-file', '-s', commit + ':' + path],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if size.returncode:
        refuse('MISSING_SOURCE', commit + ':' + path)
    if int(size.stdout) > MAX_SOURCE:
        refuse('TOO_LARGE', path)
    result = subprocess.run(['git', '-C', str(repo), 'cat-file', 'blob', commit + ':' + path],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        refuse('MISSING_SOURCE', commit + ':' + path)
    if len(result.stdout) > MAX_SOURCE:
        refuse('TOO_LARGE', path)
    return result.stdout


def encode(raw):
    return base64.b64encode(raw).decode('ascii')


def decode(value):
    string(value, 'base64')
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        refuse('INVALID_BASE64', 'packet bytes')


def check_digest(raw, expected, where):
    if digest(raw) != expected:
        refuse('DIGEST_MISMATCH', where)


def load(store, address):
    hex_value(address, 64, 'address')
    p = parse(read_file(store, address + '.json', MAX_PACKET))
    fields(p, ['profile', 'record', 'sources'], 'packet')
    if p['profile'] != PACKET:
        refuse('UNSUPPORTED_PROFILE', 'packet')
    raw = decode(p['record'])
    check_digest(raw, address, 'record')
    r = validate(raw)
    if not isinstance(p['sources'], dict):
        refuse('FIELD_TYPE', 'sources')
    expected = {e['id'] for e in r['evidence']}
    if p['sources'].keys() != expected:
        refuse('MISSING_SOURCE', 'packet source set differs from record')
    for e in r['evidence']:
        source = decode(p['sources'][e['id']])
        if len(source) > MAX_SOURCE:
            refuse('TOO_LARGE', e['id'])
        check_digest(source, e['sha256'], e['id'])
    return raw, r


def read(store, address):
    raw, r = load(store, address)
    # Only the immediate relation target is checked: no recursive advice traversal.
    for rel in r['relations']:
        load(store, rel['target']['sha256'])
    return raw, r


def save(record, store, repo):
    record, store = Path(record), Path(store)
    raw = read_file(record.parent, record.name, MAX_RECORD)
    r = validate(raw)
    sources = {}
    total = len(raw)
    for e in r['evidence']:
        source = (read_file(record.parent, e['path'], MAX_SOURCE) if e['kind'] == 'file'
                  else git_blob(repo, e['commit'], e['path']))
        check_digest(source, e['sha256'], e['id'])
        total += len(source)
        if total > MAX_PACKET // 2:
            refuse('TOO_LARGE', 'aggregate source bytes')
        sources[e['id']] = encode(source)
    for rel in r['relations']:
        t = rel['target']
        previous, _ = load(store, t['sha256'])
        check_digest(git_blob(repo, t['commit'], t['path']), t['sha256'], 'relation target')
        check_digest(previous, t['sha256'], 'stored predecessor')
    payload = json.dumps({'profile': PACKET, 'record': encode(raw), 'sources': sources},
                         ensure_ascii=True, sort_keys=True).encode('utf-8') + b'\n'
    if len(payload) > MAX_PACKET:
        refuse('TOO_LARGE', 'packet')
    store.mkdir(parents=True, exist_ok=True)
    if store.is_symlink():
        refuse('UNSAFE_PATH', 'store is a symlink')
    address = digest(raw)
    target = store / (address + '.json')
    # Publish a complete single file with filesystem-enforced no-clobber.
    fd, staging = tempfile.mkstemp(prefix='.experience-', dir=store)
    published = False
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
        try:
            os.link(staging, target)
        except FileExistsError:
            refuse('OUTPUT_EXISTS', str(target))
        published = True
    finally:
        try:
            os.unlink(staging)
        except OSError:
            if not published:
                raise
    return {**status('SAVED'), 'address': address, 'path': str(target),
            'cleanup_complete': not os.path.lexists(staging),
            'leftover_staging_path': staging if os.path.lexists(staging) else None}


def status(operation):
    return {'ok': True, 'operation': operation, 'bytes_verified': True,
            'authentication': 'NOT_PERFORMED', 'evidence_replayed': False,
            'advice_accepted': False}


def search(store, task='', component=''):
    store = Path(store)
    if store.is_symlink():
        refuse('UNSAFE_PATH', 'store is a symlink')
    if not store.is_dir():
        refuse('MISSING_STORE', str(store))
    matches, errors = [], []
    for path in sorted(store.iterdir()):
        if path.name.startswith('.experience-'):
            errors.append({'path': str(path), 'refusal': 'INCOMPLETE_STAGING'})
            continue
        try:
            if not re.fullmatch(r'[0-9a-f]{64}\.json', path.name):
                refuse('UNSUPPORTED_STORE_ENTRY', path.name)
            address = path.stem
            _, r = read(store, address)
            if (task.casefold() in (r['task']['summary'] or '').casefold() and
                    component.casefold() in (r['task']['component'] or '').casefold()):
                matches.append({'address': address, 'id': r['id'], 'task': r['task'],
                                'relations': r['relations']})
        except (Refusal, OSError) as exc:
            errors.append({'path': str(path), 'refusal': getattr(exc, 'code', 'IO_ERROR'),
                           'detail': str(exc)})
    return {**status('SEARCH'), 'ok': not errors, 'bytes_verified': not errors, 'matches': matches, 'errors': errors}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    s = sub.add_parser('save')
    s.add_argument('record')
    s.add_argument('--repo', required=True, help='local Git repository; no fetch')
    for name in ['read', 'verify']:
        p = sub.add_parser(name)
        p.add_argument('address', help='SHA-256 of original record bytes')
        if name == 'read':
            p.add_argument('--raw', action='store_true', help='exact record bytes on stdout')
    p = sub.add_parser('search')
    p.add_argument('--task', default='')
    p.add_argument('--component', default='')
    for p in sub.choices.values():
        p.add_argument('--store', required=True, help='caller-owned local directory')
    args = parser.parse_args(argv)
    try:
        if args.operation == 'save':
            result = save(args.record, args.store, args.repo)
        elif args.operation == 'search':
            result = search(args.store, args.task, args.component)
        else:
            raw, record = read(args.store, args.address)
            if args.operation == 'read' and args.raw:
                sys.stdout.buffer.write(raw)
                return 0
            result = {**status(args.operation.upper()), 'address': args.address}
            if args.operation == 'read':
                result['record'] = record
                result['raw_utf8'] = raw.decode('utf-8')
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 0 if result['ok'] else 2
    except (Refusal, OSError, RecursionError) as exc:
        result = {'ok': False, 'refusal': getattr(exc, 'code', 'IO_ERROR'), 'detail': str(exc)}
        print(json.dumps(result, ensure_ascii=True), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
