# CALIB-MYC-1 — execution package

**BLOCK 1 RUN COMPLETE — [results](../results/README.md). Calibration closed by
owner decision on 2026-09-15; no further session, no comparison on `mycelium`.**
This file describes the accepted package (revision 6, head
`6ea19678d9d85647ec6d0d0a75a25cfb2007d408`, merged `4fd568a`) that the block was
run with. The [plan](../PLAN.md) is retained as accepted; its "NOT RUN" header is
historical. Revisions 2–6 and their review threads are in PRs #87–#89.

## What is frozen

- [`package/freeze.json`](package/freeze.json): plan head and merge, source
  revision `198f9e2…` and its tree, run root, requested model
  `claude-sonnet-5`, Claude Code version and binary digest, settings, argv
  template, 600 s timeout, schedule S1–S3, input digests, snapshot bundle
  head/digest/file digests, harness digests, controls summary digest, init
  policy.
- [`package/snapshot.bundle`](package/snapshot.bundle): one commit — the
  `git archive` tree of `198f9e2` plus `CONTRACT.md` and `task.txt`. A history
  bundle was rejected: commit messages up to `198f9e2` name the triage and
  DOC-F1. The in-tree ledger hint stays, as the plan discloses.
- [`../inputs/`](../inputs/): contract, task text, immutable H7 baseline
  `test_mycelium.py` at `198f9e2` (sha256 `883b7c62…`).
- [`../controls/`](../controls/): C0–C5 with per-check expected and observed
  results and the applied diffs; all six match (C1, verify fixed but minting
  untouched, is PARTIAL on H6).
- [`offline/`](offline/): host-only receipt on this exact package (controls
  byte-identical, bundle readback and determinism, sandbox canary, remote
  denial under the stub profile, init capture, tool probe, regressions) and
  `expected-init.json`.

## Isolation

The live `claude -p` process runs under a `sandbox-exec` profile
(`harness/runtime.py`): reads denied for `~/Projects` (the repaired `main`,
this package incl. grader and controls, the experience store and records),
`~/.claude`, `~/.codex`, `~/calib1-runs`, `~/calib1-work` except the receiver's
own snapshot, and earlier experiments' trace directories; writes only in the
snapshot, `/private/tmp`, the OS temp dir and `/dev`; network allowed. Every
preflight proves, under the same profile, that all 16 protected paths are
denied while the workspace is writable and `python3`/`git` run; scans
readable temp storage for markers and the digests of every patched
`mycelium.py`; checks the Claude Code binary, stale snapshots, and the CLI's
OAuth expiry (≥ `TIMEOUT + 300` s, read from the login keychain, expiry only).

## Decisions taken during package review

- Grader deadlines per check: a hanging submission is a graded failure, never
  INVALID; INVALID is reserved for environment failures after a slot is
  claimed. Preflight runs before the slot is claimed; a refusal consumes no
  slot and is retained under `preflight-refusals/`.
- Trace policy: `skills`, `slash_commands`, `mcp_servers`, `plugins` must be
  empty; unknown event types invalidate (`tool_progress` heartbeats are
  known); `user` events must be tool-result-only; the final message is
  stored verbatim, never parsed.
- Temp scan: a dangling symlink is recorded, not an error; a target that
  vanishes after a successful `stat` is still `DISAPPEARED_DURING_SCAN`.
- Bash allowlist left as accepted (multi-line `python3 -c` denials observed;
  cause not established).
- `tools/path_allowlist.json` names generic OS temp roots for the harness and
  the retained trace files of the results, byte-exact.

## What this package does not do

It chooses no outcome and changes nothing outside `experiments/calib-myc-1/`
beyond the allowlist entries. The grader replays at the record's fixed 2000
ATP (`verify(replay_counterexample=True)`); the authenticity-only mode is not
graded. ATP is the toy unit of this repository, not a real payer.
