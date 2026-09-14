"""Local Git source reader used as a synthetic TRANSFER-1 task."""
import re
import subprocess

class Refusal(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)

def read_source(repo, revision, path):
    if not isinstance(revision, str) or not re.fullmatch('[0-9a-f]{40}', revision):
        raise Refusal('INVALID_COMMIT')
    def git(*args):
        return subprocess.run(
            ['git', '--no-replace-objects', '-C', str(repo), *args],
            capture_output=True,
        )
    kind = git('cat-file', '-t', revision)
    if kind.returncode:
        raise Refusal('MISSING_SOURCE')
    if kind.stdout != b'commit\n':
        raise Refusal('INVALID_COMMIT')
    source = revision + ':' + path
    source_kind = git('cat-file', '-t', source)
    if source_kind.returncode or source_kind.stdout != b'blob\n':
        raise Refusal('MISSING_SOURCE')
    result = git('cat-file', 'blob', source)
    if result.returncode:
        raise Refusal('MISSING_SOURCE')
    return result.stdout
