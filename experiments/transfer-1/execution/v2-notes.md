> **SUPERSEDED:** Historical v2 notes. Review found readable reference code under other tmp filenames; prefix checks were insufficient. Do not use these launch instructions. See [current package](README.md).

# TRANSFER-1 execution package v2 — review required, no receiver run

Plan head `0e5d44f` was accepted in Claude's review relayed by the owner and
merged by PR #60 in `7a2e7d8`. All eight accepted input/scoring files and PLAN.md
remain byte-identical. This execution amendment addresses B1/B2 from the review
of `7684f39`. **No receiver or calibration session has run.** The amended package
requires review of its exact commit before any receiver call.

## What changed after review

### B1: keep protected material outside readable temporary storage

The pinned Codex profile permits reads in `/private/tmp`. The earlier canary in
the OS-default `$TMPDIR` did not test that boundary; the old positive receipt
must not be interpreted as proof of sibling isolation. Adding a parent deny in
a local development probe did not remove that access. This revision therefore
changes placement and lifecycle instead of claiming a stronger sandbox.

- Bundles stay in the repository, outside the receiver's readable area.
- The frozen run root is under `~/.codex/transfer1-runs/<id>`, not `/private/tmp`.
  Receipts, submitted reader.py and prior snapshots are kept there.
- After the receiver process group stops, its submitted bytes are frozen and its
  whole snapshot is moved to the slot's protected archive before grading. Normal
  exception cleanup also archives a remaining snapshot.
- Before a call, preflight refuses stale `/private/tmp/receiver-*` or
  `/private/tmp/transfer1-run-*` paths other than the current snapshot. It does
  not delete another operator's material. Auditing a previous slot also checks
  that its old ephemeral path no longer exists.
- Preflight creates real prior-snapshot and grade.json canaries under the actual
  run root and requires denied reads, including through a symlink. A separate
  canary beside the current snapshot explicitly records that temporary neighbors
  remain readable. A readable tmp diagnostic is not labeled “outside denied”.

The regression first leaves a real previous snapshot in `/private/tmp` and
verifies preflight refuses. It then archives it under home and verifies that a
new snapshot cannot read the actual archived witness or actual grade.json.
This protects the harness's allocated material, not arbitrary files another
process might put in `/private/tmp` under unrelated names. Other operators must
not stage experiment material there during the pilot. A process killed before
cleanup needs the recovery procedure below; it cannot silently advance.

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

- [v2/offline/receipt.json](v2/offline/receipt.json): committed harness revision,
  source hashes, versions, timestamps, all input hashes and aggregate results.
- [v2/package/freeze.json](v2/package/freeze.json): new protected run root, three
  input bundles, settings, fixed schedule, heads and file hashes.
- [v2/prepared-check.json](v2/prepared-check.json): exact bundle readback,
  single-commit histories, identical T/P log bytes and no leaked FETCH_HEAD.

The reference passes 15/15 concrete checks. All five original negative controls
still fail their expected cases. Refuse-all has the documented three additional
MISSING_SOURCE failures. Crash diagnostics are additional host controls, not new
receiver tasks. All 512 binary schedules are checked against the fixed decision
rule; the five portable unit tests include crash classification.

Each graded case uses a fresh fixture, fresh source copy and a ten-second process
group limit. Expected answers stay in the host process. This is a bounded grader,
not a proof against malicious code deliberately attacking its evaluator.

The original `offline/`, `package/`, `prepared-check.json` and development receipts
are preserved without rewriting. [v1-notes.md](v1-notes.md) retains the superseded
description, explicitly marked invalid for launch. Do not launch the old package.
The new harness rejects its mismatched frozen source hashes.

## Reproduction and launch gate

These commands perform no model calls and require new output paths:

```sh
python3 experiments/transfer-1/harness/test_harness.py
python3 experiments/transfer-1/harness/offline.py /private/tmp/transfer1-v2-offline-review
python3 experiments/transfer-1/harness/verify_prepared.py experiments/transfer-1/execution/v2/package /private/tmp/transfer1-v2-prepared-review.json
```

Offline sandbox checks require the pinned macOS CLI `0.154.0`; portable unit tests
run in the existing CI matrix. The requested receiver is still `gpt-6-astra`,
medium effort, 300 seconds per slot, no substitution or API purchase. The original
Latin-square schedule and stopping rules are unchanged.

Only after review of the exact amended execution-package commit:

```sh
python3 experiments/transfer-1/harness/run_slot.py experiments/transfer-1/execution/v2/package --reviewed-head FULL_ACCEPTED_PACKAGE_COMMIT
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
