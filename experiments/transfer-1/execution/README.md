# TRANSFER-1 execution package v3 — pilot results awaiting review

Current status: the package at `de36fe5` was accepted and all eight CI checks
passed before launch. The first N,T,P block returned three successes and the
frozen early-stop rule ended the pilot. See [raw results and limits](../results/pilot-1/README.md).
The preparation account below describes the prelaunch state; its no-run statements
are historical. Inputs, harness and bundles remain unchanged.

## Historical preparation account

Plan head `0e5d44f` was accepted in Claude's review relayed by the owner and
merged by PR #60 in `7a2e7d8`. All eight accepted input/scoring files and PLAN.md
remain byte-identical. This execution amendment closes the remaining content-leak finding from review of `545d125`,
while retaining the accepted B2 worker-crash fix. **No receiver or calibration session has run.** The amended package
requires review of its exact commit before any receiver call.

## What changed after review

### B1: scan readable tmp content, not filename prefixes

The pinned profile permits reads in `/private/tmp`. Moving the receiver workspace
under home and adding explicit tmp deny entries still allowed a local canary read.
This package therefore does not claim filesystem isolation of tmp.

Review found actual reference code and design notes left in readable tmp. The
new content scan reproduced that exposure: 33 matching files. The operator moved
21 files/directories (including both development-output directories) under
`~/transfer1-work/quarantine/`, preserving original paths as symlinks so other
host tools retain their references. The receiver cannot read those protected
targets. A subsequent scan found no matches or errors. The local relocation
manifest and before/after scan receipts are retained; [cleanup-note.json](v3/cleanup-note.json)
records their hashes and counts without publishing other tools' output contents.

Before **every** receiver call, preflight now scans readable content under
canonical `/tmp`, `/var/tmp` and the host's OS-default temporary directory:

- The scan itself runs in the exact `transfer` sandbox with the proposed receiver
  as workspace root. Only files readable under those permissions are inspected.
- It recursively follows accessible directories/symlinks, tracks visited inodes,
  hashes complete regular files and searches content for `TRANSFER-1`, `transfer1`
  (ASCII case-insensitive), the lesson bytes and exact control-source digests.
  Filenames are irrelevant. Chunk overlap preserves markers across read boundaries.
- A match, unexpected I/O error, file change, malformed report or sixty-second
  scan timeout refuses the call. Permission-denied paths are recorded as unreadable;
  they are not silently treated as successfully inspected files.
- No scan failure triggers automatic deletion or a model call. The operator must
  relocate the offending material and review a fresh preflight. Existing prefix
  guards remain only as an additional check, not the content-leak defense.

The retained regression writes the reference repair as `arbitrary.py` in an
`ordinary-*` tmp directory. It passes neither old prefix guard, but content
preflight refuses. Removing that owned canary restores a passing preflight.
A portable test also checks digest-only detection and a split-boundary marker.

Receivers, bundle-build/readback scratch and offline witness scratch now live
under `~/transfer1-work/`; results and prior snapshots live under
`~/transfer1-runs/<id>`, outside the Codex configuration directory. Bundles stay
in the repository. Offline/package writers reject output paths in temporary
storage. Snapshot archival, protected-root canaries and refused stale claims
remain in effect.

This is a content-based contamination gate, not a general secrecy guarantee:
encoded or transformed material without these markers/digests can evade it, and
a file may appear after a scan. Keep other operators from writing experiment
material into readable tmp during the pilot; the trace audit must still flag
any observed out-of-scope read. Do not interpret a clean scan as proof of zero
hidden context or immunity to concurrent writes.

### B2: distinguish submission crashes from worker startup failures

The worker flushes `TRANSFER_WORKER_STARTED` immediately before `exec_module`.
Host comparison records whether that marker arrived. Nonzero exits, missing
JSON and timeouts after the marker fail the submitted patch while leaving the
run valid. Failure before the marker remains infrastructure-indeterminate.
The marker is a lifecycle observation, not a semantic answer from the submission.

Regression receipts cover `os._exit(3)` during import and during read_source:
both yield `valid: true, pass: false` for all fifteen cases. A one-slot decision
continues normally. A trusted prefix that exits before the worker starts yields
`valid: false`; that remains an infrastructure failure. A startup timeout without
a marker likewise cannot be credited to a submitted patch.

## Current retained evidence

- [v3/offline/receipt.json](v3/offline/receipt.json): committed harness revision,
  source hashes, versions, timestamps, all input hashes and aggregate results.
- [v3/package/freeze.json](v3/package/freeze.json): new protected run root, three
  input bundles, settings, fixed schedule, heads and file hashes.
- [v3/prepared-check.json](v3/prepared-check.json): exact bundle readback,
  single-commit histories, identical T/P log bytes and no leaked FETCH_HEAD.

The reference passes 15/15 concrete checks. All five original negative controls
still fail their expected cases. Refuse-all has the documented three additional
MISSING_SOURCE failures. Crash diagnostics are additional host controls, not new
receiver tasks. All 512 binary schedules are checked against the fixed decision
rule; the six portable unit tests include crash classification.

Each graded case uses a fresh fixture, fresh source copy and a ten-second process
group limit. Expected answers stay in the host process. This is a bounded grader,
not a proof against malicious code deliberately attacking its evaluator.

The original and v2 bundles/receipts remain unchanged. [v1-notes.md](v1-notes.md)
and [v2-notes.md](v2-notes.md) retain superseded descriptions, marked invalid for
launch. The current harness rejects both old packages by source/settings hashes.

## Reproduction and launch gate

These commands perform no model calls and require new output paths:

```sh
mkdir -p "$HOME/transfer1-work/review"
python3 experiments/transfer-1/harness/test_harness.py
python3 experiments/transfer-1/harness/offline.py "$HOME/transfer1-work/review/offline"
python3 experiments/transfer-1/harness/verify_prepared.py experiments/transfer-1/execution/v3/package "$HOME/transfer1-work/review/prepared.json"
```

Offline sandbox checks require the pinned macOS CLI `0.154.0`; portable unit tests
run in the existing CI matrix. The requested receiver is still `gpt-6-astra`,
medium effort, 300 seconds per slot, no substitution or API purchase. The original
Latin-square schedule and stopping rules are unchanged.

Only after review of the exact amended execution-package commit:

```sh
python3 experiments/transfer-1/harness/run_slot.py experiments/transfer-1/execution/v3/package --reviewed-head FULL_ACCEPTED_PACKAGE_COMMIT
```

The argument records the operator's accepted review; the script verifies committed
bytes, not a review's existence or independence. Each slot is claimed before the
call; incomplete slots cannot be replaced. Public events and stderr are retained,
hidden reasoning events are omitted and counted. The session's elapsed time
excludes host grading. All terminal decisions retain unlaunched slots as NOT_RUN.

Before the next slot, save audit.json in the completed slot's protected output:

- `reviewer`, `result_sha256`, `events_sha256`, boolean `valid` and `evidence`
  identifying public event lines and commands for scope/context validity. Include
  prohibited edits even if reverted; final hashes cannot detect those alone.
- `supplied_witness_run`, `receiver_created_tag`, `tag_check_executed`, each
  `observed`, `not_observed` or `unknown`, supported by that evidence.

No grading feedback is sent to a receiver. Invalid or incomplete audits stop or
block continuation. After a complete valid first block, the fixed early-stop
rule determines whether the remaining six slots are NOT_RUN.

## Interrupted runner and remaining limits

If SIGKILL leaves runner.claim, do not unlink it to resume. Verify the old process
group is gone, preserve the claim, traces and timestamps, and document the crash
with attribution. Archive any remaining snapshot under the protected slot path,
retaining its original path and available hashes. Record the claimed slot as
`valid: false, pass: false`, add its audit, and record remaining slots NOT_RUN with
ENVIRONMENT_INDETERMINATE. Preserve the stale claim as evidence; this pilot does
not resume after that infrastructure failure. Any later attempt needs a separately
reviewed plan/run identity and must not be pooled with this one.

The network probe tests only a listener on `127.0.0.1`; it is not a survey of
external destinations. Provider traffic from the host CLI remains distinct from
tool network access. No OAuth request rewriting is used. Home/Projects denial and
specific canary observations are not a proof against all OS escape techniques.

User configuration/rules and project documentation loading are disabled; memory,
plugins, apps, additional agents and browser/computer tools are disabled explicitly.
The profile still grants reads of OS/Homebrew/Apple toolchain resources. See the
[OpenAI configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).
`skip_host_skill_discovery` remains experimental: retain its warnings and inspect
the actual tool surface in the trace audit. Fresh processes do not establish zero
provider-side context or model independence. Packet advantage and completion of
TRANSFER-1 remain unclaimed.
