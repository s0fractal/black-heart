# Optional local verification cache

`verify_cached.py` wraps the existing host-side CLI auditors for **ledger** and
**continuum** artifacts. Other routes deliberately refuse. It is opt-in: ordinary
`cli.py verify` and existing verification policies retain their behavior.

From the repository root:

```sh
python3 tools/verify_cached.py --cache /tmp/black-heart-local-cache.json \
  examples/living_ledger.pdf examples/resumable_computation.pdf

# Always execute the selected auditors again, even when entries match:
python3 tools/verify_cached.py --fresh --cache /tmp/black-heart-local-cache.json \
  examples/living_ledger.pdf
```

Output is one JSON object with an ordered `items` list. Each item contains the
original input path, captured operand digest, profile digest, `origin` equal to
`REUSED` or `EXECUTED_NOW`, and the CLI's exit code/stdout/stderr. Child output uses
the normalized name `operand.pdf`; the original path is a separate field.
Duplicate basenames cannot overwrite report items. Identical bytes may reuse an
entry even when supplied under different paths.

Exit 0 means all selected CLI outcomes have exit 0. Exit 1 means at least one
auditor failed or timed out. Exit 2 means the wrapper refused, for example
`CACHE_CHECKSUM`, `CACHE_SHAPE`, `BUSY`, unsupported metadata or an I/O error.
Malformed-cache refusals preserve the existing file. `--fresh` does not silently
discard corrupt cache bytes: remove the disposable cache explicitly or select a
new path. A timeout is returned but never cached.

For a mixed collection, opt into per-file handling:

```sh
python3 tools/verify_cached.py --batch --cache /tmp/black-heart-local-cache.json examples/*.pdf
```

Unsupported or unreadable files become `status: REFUSED`, `origin: NOT_RUN`
items with a reason, in their original order. Supported files are still checked
or reused. Any such refusal makes the overall status `INCOMPLETE` and exit code
2, even if every supported file passes. Unsupported files receive no cached
verdict. With no supported inputs, no cache is created or read. Without `--batch`,
the original strict behavior remains: reject the entire request before execution.

Top-level `COMPLETE` means all input checks yielded a completed CLI outcome;
it does **not** mean they all passed. Each completed item is `CHECKED`, including
exit-1 refusals. A timeout or abnormal process exit is `UNRESOLVED`, makes the
report `INCOMPLETE`, and returns exit 1 (unless a per-file refusal requires exit
2). Always inspect CLI outcomes as well as coverage and origin. Cache corruption
or a global locking/storage failure still refuses the whole call.

Passing and failing CLI outcomes can both be reused across process restarts.
A stored refusal applies to its captured bytes and profile, not permanently to
the filename. Repairing a document produces a different key and a fresh check;
the old refusal may remain as a separate cache entry. Deleting the cache causes
fresh execution, not loss of an authoritative decision history: this cache is
disposable and is not a historical ledger or retirement protocol.

## What is bound

Each entry binds captured PDF bytes and a conservative profile of root Python
files, Python files under `tools/` and `continuation/`, interpreter binary/version,
platform, fixed environment and command. Source/input bytes are copied to a
temporary directory; the child runs those captured bytes. A later change to an
original input path cannot change the child's operand. The capture is not an
atomic Git snapshot across concurrently edited source files.

The child runs `cli.py verify` with `-B -s -S`, a fixed environment and a
30-second timeout. These two routes read artifact metadata and invoke local
auditors, not embedded PDF code. The wrapper does not alter their predicate or
establish external signer identity, global freshness, normative adoption or
complete PDF validity. A cached passing outcome is not a fresh execution.

## Trust and storage

This is a **trusted-local** cache. Entry checksums bind both the lookup key and
the result, detecting accidental corruption or intact entries swapped between
keys. Earlier experimental value-only checksums refuse with `CACHE_CHECKSUM`;
discard that disposable cache or choose a new path. This does not protect against
a malicious writer who can replace both data and checksum. Do not import
cache files from an untrusted producer or use this as a substitute for a fresh
release/security gate. Stdlib and shared-library bytes are not individually
hashed; this is a same-host profile, not a hermetic cross-machine proof.

A sibling `.lock` file serializes cooperating callers with nonblocking `flock`.
`BUSY` performs no auditor work or cache update. Writes use a mode-0600 temporary
file, fsync and atomic replacement; failed replacement preserves the previous
cache. No protection against hostile filesystem writers or platform-wide power
failure is claimed. The cache has a 16 MiB limit and no automatic eviction. It can
always be deleted: authoritative inputs and existing verifiers remain elsewhere.
The lock file may remain after use; its existence alone does not mean it is held.

## Validation and status

```sh
python3 -B -m unittest test_verify_cached test_cli_verify -v
```

Tests cover actual CLI reuse/fresh execution, changed ledger refusal, duplicate
basenames, captured operands, source-profile invalidation, cache corruption,
timeouts, failed replacement and a lock held by another process. They also
exercise nine fresh CLI processes through reuse, rejection, repair, cache
loss, corrupt-cache refusal and recovery using a new cache path. The test module
is included in `test_all.py`. This is a small experimental repository tool, not a
general cache for every Black-heart engine or a change to Warrant semantics.
