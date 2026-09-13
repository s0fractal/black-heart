# CM-2 local experience path

`experience.py` is a standalone standard-library CLI/API. The existing
`cli.py library` accepts warrant PDF / EdgeClaim and evaluates GROUNDED claims;
reusing that parser would misrepresent narrative experience. This small path
keeps LI's data-only reading, explicit refusals and no-clobber publication,
without invoking its authentication, evaluator, admission or PDF renderer.

From a full local clone, choose a caller-owned store outside the source tree:

```sh
python3 experience.py save examples/model-experience/doc-f1/experience.json --repo . --store /tmp/cm2-store
python3 experience.py search --component EMPIRICAL --store /tmp/cm2-store
python3 experience.py search --task suspended --store /tmp/cm2-store
# Use the address returned by save/search:
python3 experience.py read ADDRESS --store /tmp/cm2-store
python3 experience.py read ADDRESS --raw --store /tmp/cm2-store
python3 experience.py verify ADDRESS --store /tmp/cm2-store
```

Replace `ADDRESS` with the returned SHA-256. `read --raw` emits the exact
original record bytes, including formatting; default JSON additionally shows
parsed fields. All these commands verify stored byte digests before returning
success. `verify` emits only the bounded check result. None replays evidence,
authenticates a signer/model/session, or accepts advice. Received argv and
text remain data. Review commands before executing them.

The record address is SHA-256 of its original UTF-8 bytes, **not** its local id.
`<address>.json` is a single `black-heart.experience-packet.v1` object with
`profile`, `record` (base64 original bytes), and `sources` (evidence id → base64
original bytes). This transport encoding does not canonicalize the record.
`save` reads file evidence relative to the input record and Git blobs from the
explicit local `--repo`; it never fetches or follows repository URLs. The packet
captures each complete source, including the unchanged historical replay.
Moving the store preserves reading without Git or the original input files.
Source drift on a later import is a refusal; later edits to the old source tree
do not change this retained snapshot. Editing saved source bytes is detected.
SHA-256 correspondence establishes neither truth nor repository ownership.

`relations` uses the CM-1 exact Git target (`repository`, full `commit`, relative
`path`, `sha256`). Save requires the predecessor already in the store and checks
its target Git blob against the digest in the supplied local repository.
For both evidence and relation targets, `save` checks that the object named by
`commit` has Git type `commit`; a tree/blob/tag object is `INVALID_COMMIT`
even if Git could resolve its path to matching source bytes. The URL
is descriptive, not authenticated. This minimal slice supports **Git-anchored
relation targets**; commit a new predecessor before citing it. It does not
invent a commit for an uncommitted local record. On read, the immediate
predecessor packet must still exist and pass its byte checks; no recursive
relation traversal or endorsement is performed. Copy those packets when moving
related records. Different advice gets a different record, never an update.

Search is a case-insensitive substring scan of task summary / component, with
AND when both filters are supplied. It returns applicability and exact addresses;
there is no ranking, inferred equivalence or latest-wins rule. Empty search
returns all valid records. It checks every packet: corrupt/non-supported entries
and unfinished staging files produce an `errors` array and exit 2 even when
outside the filter, alongside any valid matches. No directory means
`MISSING_STORE`; an empty directory succeeds with an empty result.

JSON is explicitly UTF-8; duplicate keys at any level, missing fields, unknown
fields/profiles/kinds, dangling evidence ids, invalid digests, missing sources,
unsafe relative paths and incorrect field types are refused, never repaired.
Narrative/provenance scalars may be null as in CM-1; operational identifiers,
source addresses and relation pins must be usable. Limits: record 1 MiB,
source 8 MiB, aggregate raw input 32 MiB, encoded packet 64 MiB. This path targets
POSIX local filesystems with hard links and `O_NOFOLLOW` (Linux/macOS).
File evidence and store entries cannot follow symlinks, traverse `..`, use
absolute paths, or read non-regular files. Caller-selected roots and their
ancestors, local Git object database and local operator are trusted; this is
not isolation from a process that can concurrently rewrite those directories.

Publication stages one complete file, flushes/fsyncs it, then hard-links it
without replacing a destination. Retry refuses `OUTPUT_EXISTS`, including a
concurrent writer's destination. A crash before publication may leave a hidden
`.experience-*` staging file; search names it and the operator handles cleanup.
After publication, failed staging cleanup reports `cleanup_complete: false`
with its path; the packet remains readable. This does not claim power-loss
crash durability, multi-record transactions or protection from deletion by the
store owner. No automatic repair/deletion is provided.

Successful CLI results are JSON on stdout, exit 0; named refusals are JSON on
stderr, exit 2. Search with partial errors returns JSON on stdout, exit 2.
`read --raw` success emits only bytes. Argument syntax errors use argparse's
usage/exit 2; unexpected programming errors retain a traceback/exit 1. The small
Python API raises `Refusal` (with `code`/`detail`) or `OSError`; the CLI maps them.

## Reproduce the bounded check

```sh
python3 examples/model-experience/cm2/check.py /tmp/cm2-new-report.json
python3 test_all.py
```

The first command runs only the fixed `test_experience` module and records actual
`git rev-parse HEAD`, `git status --porcelain` before/after, command, conditions,
output, runtime and source digests. It refuses an existing output path. It does
not execute an experience's argv. The saved [check.json](check.json) is one such
run; dirty status is preserved honestly. The old DOC-F1 replay lacks checkout
measurements and remains byte-identical, with no historical reconstruction.

The disagreement behavior in `test_experience` is explicitly a **synthetic
functional control**, not a second-model response: save DOC-F1; save a distinct
contradiction with the exact original Git path/commit/digest; read both; find
both; reject an incorrect target and a missing predecessor. The test also
checks missing fields/sources, duplicates, UTF-8, tampering, unsafe paths,
no-clobber races, publication/cleanup failure and non-execution of input argv.
CI includes this module in `test_all.py`, using full checkout history so the
real DOC-F1 tests cannot silently skip.

## B1 amendment

[check-b1.json](check-b1.json) records the amended focused run and source digests;
[check.json](check.json) remains the historical pre-amendment run unchanged.
Two regression controls substitute the real tree OID for an evidence commit
and a relation-target commit while retaining matching blob bytes. Both were
accepted before the amendment; both now refuse with `INVALID_COMMIT`, exit 2,
without saving a successor or changing the retained predecessor.

Packets inherit `mkstemp` owner-only permissions (`0600`); a shared CM-3 store
will need an explicit access decision. CM-2 status must be updated after verified
merge, at the start of CM-3; readiness is not acceptance. The non-blocking review
notes about generic I/O refusal codes and cleanup masking remain outside B1.
