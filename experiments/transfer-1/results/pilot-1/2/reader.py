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
        return subprocess.run(['git', '-C', str(repo), *args], capture_output=True)
    object_type = git('cat-file', '-t', revision)
    if object_type.returncode:
        raise Refusal('MISSING_SOURCE')
    if object_type.stdout != b'commit\n':
        raise Refusal('INVALID_COMMIT')
    result = git('cat-file', 'blob', revision + ':' + path)
    if result.returncode:
        raise Refusal('MISSING_SOURCE')
    return result.stdout
