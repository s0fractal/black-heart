# read_source contract

`read_source(repo, revision, path)` returns the exact Git blob bytes at `path`
from the supplied full lowercase 40-hex Git commit identifier.
The repository is local and trusted; no fetch
or network access is permitted. This is a byte reader, not advice acceptance.

Refuse by raising `Refusal(code)`:

- Malformed revision or an existing revision that is not a valid commit identifier: `INVALID_COMMIT`.
- Missing revision object, absent path, or a path that is not a blob:
  `MISSING_SOURCE`.

Valid commits must keep working, including two different commits with the same
tree. Exact bytes matter; no text decoding, normalization or HEAD substitution.
`path` is a caller-validated nonempty relative path, without traversal or revision
syntax. Do not broaden this task into path validation or repository ownership.
Only reader.py is the submitted patch; test code is scratch material.
