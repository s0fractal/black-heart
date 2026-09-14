#!/usr/bin/env python3
"""Check tracked UTF-8 source for machine-local paths, not document truth.

Stage new files first. By default scan all tracked files; --base REF checks only
line occurrences added since REF, preserving historical bytes. Binary files are
outside scope. Allowlist entries apply to a particular path occurrence, not a line.
Git/config/read failures refuse the check. Run --selftest for mutation controls.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
PATTERN = re.compile(r'''(?:/(?:Users|home|private/var)/|[A-Za-z]:[/\\](?:Users|Documents)[/\\])[^\s"'<>`),;}\]]+''')
SELF = {'tools/absolute_path_check.py', 'tools/path_allowlist.json'}


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])


def check(root, config, base=None):
    cfg = json.loads(config.read_text())
    # Exclusions are explicit file paths. Do not blanket-exclude review directories.
    ignored = cfg.get('ignore_globs', [])
    import fnmatch
    entries = cfg.get('allowed_entries', [])
    assert isinstance(ignored, list) and all(isinstance(x, str) for x in ignored)
    allow = {}
    for entry in entries:
        assert entry['reason'].strip() and entry['file']
        values = entry['allowed_substrings']
        assert isinstance(values, list) and all(isinstance(v, str) and v for v in values)
        allow.setdefault(entry['file'], []).extend(values)
    if base:
        git(root, 'rev-parse', '--verify', base + '^{commit}')
    errors, scanned, allowed, binary = [], 0, 0, 0
    for name in git(root, 'ls-files', '-z').decode().split('\0'):
        if not name or name in SELF or any(fnmatch.fnmatchcase(name, g) for g in ignored):
            continue
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f'outside-root source: {name}')
        data = path.read_bytes()  # A missing/unreadable tracked file is not success.
        if b'\0' in data:
            binary += 1
            continue
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            binary += 1
            continue
        old = Counter()
        if base:
            # A missing base path denotes a new file. Other git errors must escape.
            names = git(root, 'ls-tree', '-r', '--name-only', '-z', base, '--', name).decode().split('\0')
            if name in names:
                previous = git(root, 'show', f'{base}:{name}')
                if b'\0' not in previous:
                    old = Counter(previous.decode('utf-8').splitlines())
        scanned += 1
        for line_no, line in enumerate(text.splitlines(), 1):
            if old[line]:
                old[line] -= 1
                continue
            for match in PATTERN.finditer(line):
                # Only permit a match contained in an exact documented substring.
                permitted = False
                for value in allow.get(name, []):
                    start = line.find(value)
                    while start >= 0:
                        if start <= match.start() and match.end() <= start + len(value):
                            permitted = True
                        start = line.find(value, start + 1)
                if permitted:
                    allowed += 1
                else:
                    errors.append(f'{name}:{line_no}: {match.group()}')
    return {'violations': errors, 'scanned': scanned, 'allowed': allowed,
            'binary_skipped': binary, 'scope': 'added line occurrences' if base else 'tracked text'}


def selftest():
    import tempfile
    from unittest.mock import patch
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        git(root, 'init', '-q')
        path = root / 'example.py'
        config = root / 'config.json'
        config.write_text(json.dumps({'allowed_entries': [{'file': 'example.py',
            'reason': 'fixture', 'allowed_substrings': ['/Users/alice/example']}]}))
        path.write_text('old="/Users/alice/example"; new="/Users/bob/private"\n')
        git(root, 'add', 'example.py')
        assert len(check(root, config)['violations']) == 1
        path.write_text('old="/Users/alice/example/extra"\n')
        assert len(check(root, config)['violations']) == 1
        path.write_text('x="relative/path"\n')
        assert not check(root, config)['violations']
        original = Path.read_bytes
        def unreadable(p):
            if p == path:
                raise PermissionError('fixture')
            return original(p)
        with patch.object(Path, 'read_bytes', unreadable):
            try:
                check(root, config)
            except PermissionError:
                pass
            else:
                raise AssertionError('unreadable file passed')
        git(root, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
            'commit', '-qm', 'fixture')
        # HEAD contains the initially staged path pair; unchanged history is exempt.
        path.write_text('old="/Users/alice/example"; new="/Users/bob/private"\n')
        assert not check(root, config, 'HEAD')['violations']
        path.write_text(path.read_text() + 'fresh="/home/charlie/private"\n')
        assert len(check(root, config, 'HEAD')['violations']) == 1
        try:
            check(root, root / 'missing.json')
        except FileNotFoundError:
            pass
        else:
            raise AssertionError('missing config passed')
    print('PASS: occurrence scope, path suffix, relative path, unreadable file, baseline, new path, missing config')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'tools/path_allowlist.json')
    parser.add_argument('--base')
    parser.add_argument('--selftest', action='store_true')
    args = parser.parse_args()
    try:
        if args.selftest:
            selftest()
            return 0
        result = check(ROOT, args.config, args.base)
        print(json.dumps(result, indent=2))
        return bool(result['violations'])
    except (OSError, ValueError, AssertionError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f'REFUSED: incomplete check: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
