"""Deterministic case fixture and host comparison, with one fresh process per case."""
import json
import sys
import tempfile
from pathlib import Path
from common import ROOT, git, run, sha, verify_inputs

PAYLOAD = b'\x00\xff\xfe\x80\r\nTRANSFER-1\x00end\n'


def fixture(root):
    root.mkdir()
    git(root, '-c', 'init.templateDir=', 'init', '-q', '--object-format=sha1')
    (root / 'folder').mkdir()
    (root / 'folder/source.bin').write_bytes(PAYLOAD)
    git(root, 'add', '.')
    git(root, 'commit', '-qm', 'first')
    a = git(root, 'rev-parse', 'HEAD')
    git(root, 'commit', '--allow-empty', '-qm', 'second')
    b = git(root, 'rev-parse', 'HEAD')
    git(root, 'tag', '-a', 'one', '-m', 'one', a)
    tag = git(root, 'rev-parse', 'refs/tags/one')
    git(root, 'tag', '-a', 'two', '-m', 'two', tag)
    nested = git(root, 'rev-parse', 'refs/tags/two')
    missing = '0' * 40
    assert run(['git', 'cat-file', '-e', missing], cwd=root)['exit_code'] != 0
    assert git(root, 'rev-parse', a + '^{tree}') == git(root, 'rev-parse', b + '^{tree}')
    assert a != b and a.upper() != a
    path = 'folder/source.bin'
    cases = [
        ('commit_a', a, path, {'bytes_hex': PAYLOAD.hex()}),
        ('commit_b_same_tree', b, path, {'bytes_hex': PAYLOAD.hex()}),
        ('annotated_tag_commit', tag, path, {'refusal': 'INVALID_COMMIT'}),
        ('nested_annotated_tag', nested, path, {'refusal': 'INVALID_COMMIT'}),
        ('tree', git(root, 'rev-parse', a + '^{tree}'), path, {'refusal': 'INVALID_COMMIT'}),
        ('blob', git(root, 'rev-parse', a + ':' + path), path, {'refusal': 'INVALID_COMMIT'}),
        ('missing_object', missing, path, {'refusal': 'MISSING_SOURCE'}),
        ('missing_path', a, 'absent', {'refusal': 'MISSING_SOURCE'}),
        ('directory_path', a, 'folder', {'refusal': 'MISSING_SOURCE'}),
    ]
    for label, rev in [('HEAD', 'HEAD'), ('uppercase', a.upper()), ('short', a[:12]),
                       ('null', None), ('integer', 1), ('list', [a])]:
        cases.append(('malformed_revision/' + label, rev, path, {'refusal': 'INVALID_COMMIT'}))
    return cases

# Subprocess emits observations only; expected values and comparisons stay in host.
WORKER = '''import contextlib, importlib.util, io, json, sys
request=json.loads(sys.stdin.read())
captured=io.StringIO()
try:
 with contextlib.redirect_stdout(captured):
  spec=importlib.util.spec_from_file_location('submission', request['source'])
  module=importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  try:
   result=module.read_source(request['repo'], request['revision'], request['path'])
   observed={'bytes_hex': result.hex()} if type(result) is bytes else {'wrong_type':type(result).__name__}
  except module.Refusal as error:
   observed={'refusal':error.code}
except BaseException as error:
 observed={'exception':type(error).__name__, 'message':str(error)}
print(json.dumps(observed))
'''


def grade(source, command_prefix=()):
    verify_inputs()
    source = Path(source)
    if source.is_symlink() or not source.is_file():
        return {'pass': False, 'submission_error': 'MISSING_OR_SYMLINK_SUBMISSION', 'cases': []}
    source_bytes = source.read_bytes()
    results = []
    # Each case gets an independent repo and source copy; no cross-case mutation.
    for index in range(15):
        with tempfile.TemporaryDirectory(prefix='transfer-grade-') as td:
            root = Path(td).resolve()
            cases = fixture(root / 'repo')
            case_id, revision, path, expected = cases[index]
            frozen = root / 'reader.py'
            frozen.write_bytes(source_bytes)
            request = {'source': str(frozen), 'repo': str(root / 'repo'),
                       'revision': revision, 'path': path}
            prefix = command_prefix(root) if callable(command_prefix) else command_prefix
            result = run([*prefix, sys.executable, '-I', '-c', WORKER], cwd=root,
                         stdin=json.dumps(request).encode(), timeout=10)
            try:
                observed = json.loads(result['stdout'])
            except (ValueError, TypeError):
                observed = {'invalid_worker_output': True}
            passed = (not result['timed_out'] and result['exit_code'] == 0 and observed == expected)
            results.append({'id': case_id, 'expected': expected, 'observed': observed,
                            'pass': passed, 'worker': result})
    specified = {c['id'] for c in json.loads((ROOT / 'scoring/cases.json').read_text())['cases']}
    assert {c['id'].split('/')[0] for c in results} == specified
    return {'valid': all(c['worker']['exit_code'] == 0 or c['worker']['timed_out'] for c in results),
            'pass': all(c['pass'] for c in results), 'source_sha256': sha(source), 'cases': results}

if __name__ == '__main__':
    print(json.dumps(grade(sys.argv[1]), indent=2))
