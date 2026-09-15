# CALIB-MYC-1 — execution package

**PREPARED / NOT LAUNCHED / PACKAGE REVIEW REQUIRED.** No receiver session has
run. This package implements the accepted [plan](../PLAN.md) (revision 2,
merged `4ad65c8`). Plan acceptance does not authorise a session; the exact
commit of this package must be reviewed first, and `run_slot.py` refuses any
byte that is not in the reviewed commit.

## What is frozen

- [`package/freeze.json`](package/freeze.json): plan head and merge, source
  revision `198f9e2…` and its tree, run root, requested model, Claude Code
  version and binary digest, settings, argv template, 600 s timeout, schedule
  S1–S3, input digests, snapshot bundle head/digest/file digests, harness
  digests, controls summary digest, init policy.
- [`package/snapshot.bundle`](package/snapshot.bundle): one commit, the
  `git archive` tree of `198f9e2` plus `CONTRACT.md` and `task.txt` at the
  root. Deterministic (two independent builds gave the same head and digest;
  see the offline receipt). The full-history bundle was rejected on purpose:
  commit messages up to `198f9e2` (#81) name the triage and DOC-F1. The
  in-tree ledger hint (`docs/REMEDIATION-LEDGER.md` backlog names
  `mycelium.verify`) stays, as the plan discloses.
- [`../inputs/`](../inputs/): contract, task text, and the immutable H7
  baseline `test_mycelium.py` at `198f9e2` (sha256 `883b7c62…`).
- [`../controls/`](../controls/): C0–C5 grader outputs with **per-check**
  expected results (`expected_checks`), observed results and a per-check
  match, plus the applied diffs. All six match: C0 FAIL, C1 PARTIAL (verify
  fixed in both branches, minting untouched — H6 fails because a record is
  still created), C2/C3 PARTIAL, C4 PASS (bytes of #82), C5 FAIL.
- [`offline/`](offline/): receipt of the host-only validation run on this
  exact package (controls re-run byte-identical, bundle readback and
  determinism, sandbox store canary, remote-network denial under the stub
  profile, init-surface capture with a loopback stub and a dummy key, Bash
  tool probe under the receiver profile, regressions) and
  `expected-init.json`, the init surface the live session is compared to.

## Isolation (what the receiver cannot read)

The live `claude -p` process is wrapped in a `sandbox-exec` profile
(`harness/runtime.py`): reads denied for `~/Projects` (the repaired `main`
checkout, this package incl. grader and controls, the experience store and
records), `~/.claude` and `~/.claude.json`, `~/.codex`, `~/calib1-runs` (slot
archives and grade receipts), `~/calib1-work` except the receiver's own
snapshot, and earlier experiments' trace directories; writes allowed only in
the snapshot, `/private/tmp`, the OS temp dir and `/dev`; network allowed
(provider). The store canary in every preflight proves, under the same
profile, that all 16 protected paths are denied — including the grader file,
the controls directory, the run root and a sibling receiver directory — while
the workspace is writable and `python3`/`git` run. `/private/tmp` stays
readable, so preflight also scans readable temp storage for the markers and
for the digests of every patched `mycelium.py` (C1–C5 and the current
checkout; C0's digest is the snapshot's own file and is excluded).

## Operator steps before the first session

1. Host hygiene: at the time of the offline receipt the temp scan still
   matched two Claude Code `bash-edit-diff` cache files under
   `/private/tmp/claude-501/` (edit diffs of the repaired `mycelium.py` from
   the authoring session) and reported transient `DISAPPEARED_DURING_SCAN`
   errors for browser/Codex singleton files. Preflight refuses on either.
   Close those applications and quarantine the cache files (move, never
   delete; see [`quarantine-note.json`](quarantine-note.json) for the earlier
   move of leaked control trees).
2. `python3 harness/run_slot.py execution/package --reviewed-head <accepted sha>`,
   once per slot. Preflight runs **before** a slot is claimed: a refusal makes
   no model call, consumes no slot, and is retained under
   `<run_root>/preflight-refusals/`; the operator may repair hygiene and invoke
   again. Once a slot is claimed, any environment failure is INVALID and ends
   the block as INCOMPLETE, per the plan.
3. After each slot, write `audit.json` by hand (result and events digests,
   reviewer, evidence, `valid`, and the three secondary observations
   `ledger_read`, `false_fix_kind`, `ran_existing_tests`). The runner refuses
   the next slot without it. Do not combine audit and launch in one step.

## Amendments after package review (revision 2 of the package)

- **B1 — a hanging submission is a graded failure, not INVALID.** The grader
  now runs an import probe and one child per check, each with its own
  deadline (`CALIB_GRADER_CHECK_TIMEOUT`, default 120 s), and the H7 baseline
  run with `CALIB_GRADER_H7_TIMEOUT` (default 600 s); the sum stays below the
  launcher's 1800 s. A deadline hit is recorded as that check failing with a
  "timed out" detail; the grader never surfaces `TimeoutExpired`. Regression
  `grader_hang_check` (three synthetic submissions on the pinned tree, 2 s
  deadlines: hang at import, hang inside `verify()`, hang inside the H7 run)
  yields outcome FAIL each time, no grader error; it is part of the offline
  receipt and of `test_harness.py`.
- **B2 — signs of foreign context invalidate automatically.** `skills`,
  `slash_commands`, `mcp_servers` and `plugins` must be `[]` (and equal to the
  capture); any unknown stream event type invalidates the trace; a `user`
  event is accepted only when every content block is a `tool_result` (the
  task prompt may echo once; the live stream does not echo it), any other
  text or a string content is recorded as foreign and invalidates. `agents`
  lists Claude Code's built-in agents and is compared for equality only.
  Regressions cover non-empty skills/slash_commands, an unknown event type,
  a foreign `user` text block, string content, tool-result-only `user` events
  and the prompt-echo rule.

- **Revision 3 — dangling symlinks in temp storage.** The dry preflight on
  the accepted revision 2 refused on `DISAPPEARED_DURING_SCAN` for
  Chromium-style `SingletonCookie` entries of Codex and Chrome under the OS
  temp dir: symlinks to a random number that is not a path, some dating from
  2026-09-04 (instances long closed). `os.stat` follows the link and raises
  `FileNotFoundError`. A dangling symlink has no readable content and cannot
  leak anything, so the scanner now records such entries under
  `dangling_symlinks` instead of `errors`; a genuine disappearance during the
  scan is still an error. Regression: a dangling symlink next to marker files
  is recorded and the scan passes. This is the only change in revision 3.
- **Revision 4 — the exception is narrowed to the initial `stat`.** Review
  showed revision 3's handler also covered the read: a target that exists at
  `stat` time and vanishes before `open` was filed as dangling. Now only a
  `FileNotFoundError` from the initial `os.stat` of a dangling symlink is
  recorded; any `FileNotFoundError` after a successful `stat` stays
  `DISAPPEARED_DURING_SCAN`. Regression: the target is removed between the
  scanner's `stat` and its `open` (via a patched `open` in the scanner's
  namespace) and must be reported as an error, not dangling; the regression
  fails against the revision 3 scanner. Only change in revision 4.

- **Revision 5 — zero-token authentication preflight.** Slot 1 of run
  `6cbd7c38…` (package revision 4) was INVALID: the sandboxed session
  received `401 OAuth access token has expired` on its first request (model
  `<synthetic>`, `terminal_reason api_error`, 8.8 s, no tool use, no tokens);
  the host CLI token had expired at 2026-09-14T19:52Z and the in-session
  refresh failed. The preflight had no authentication check. It now reads the
  CLI's OAuth expiry from the login keychain (`security find-generic-password
  -s "Claude Code-credentials" -w`, piped through a parser that returns only
  the expiry, the seconds remaining and whether a refresh token is present)
  and refuses `AUTH_TOKEN_EXPIRED_OR_EXPIRING` when fewer than
  `TIMEOUT + 300` s remain, or `AUTH_STATE_UNREADABLE` when the entry is
  missing or malformed. No provider contact; no secret is stored or logged.
  Re-authentication is the operator's action, never the harness's. The slot 1
  record and its audit stay under the old run root; this revision freezes a
  new run root. Whether the sandbox blocks a mid-session refresh is not
  established; the margin makes a refresh during a slot unnecessary.

- **Revision 6 — `tool_progress` is a known stream event.** Run `e6b293fa…`
  slot 1 (revision 5): a fresh `claude-sonnet-5` session produced a full
  repair (grader PASS on H1–H7, no in-tree hint read, 73 tool uses, killed at
  600 s while running the full test suite) but was classified INVALID solely
  because six `tool_progress` events — CLI heartbeats for Bash calls longer
  than 30 s, no model or user content — were not in `KNOWN_TYPES`. That
  record and its audit stay under the old run root as INVALID; the block is
  INCOMPLETE by the plan and this revision freezes a new run root. Change:
  `tool_progress` added to `KNOWN_TYPES`; regression: heartbeat events keep a
  trace valid, an unknown type still invalidates. The observed `system`
  subtypes (`api_retry`, `permission_denied`, `task_started`,
  `task_notification`) are named, not policed beyond `init`. Not changed on
  purpose: the Bash allowlist pattern `Bash(python3 *)` does not match
  multi-line `python3 -c "…"` commands (two denials in slot 1; the receiver
  continued). Widening it would change receiver conditions between slots; it
  is a reviewer decision.

## Decision points for the package reviewer

- **Model id.** Frozen as `claude-sonnet-5` (a fresh Claude model that is not
  the plan's author session; cheaper per slot). Changing it means re-running
  `prepare.py` and `offline.py` and re-reviewing the new commit.
- **Pre-slot preflight.** The plan lists "preflight не пройшов" under INVALID.
  This package runs preflight before the slot exists, so a refusal without a
  model call is retained but does not consume a slot. INVALID keeps its
  meaning for every failure after the claim. If the reviewer prefers the
  plan's letter, the change is one block in `run_slot.execute`.
- **Bundle size.** 2.1 MB binary in the repository for one calibration.
- **Init policy.** `fast_mode_disabled_reason` (present in Claude Code
  2.1.272) is compared for equality; `messaging_socket_path` is optional and
  pattern-checked (the rvb-bh-1a drift); any other new or missing init field
  is INVALID.
- **Grading budget.** The grader replays at the record's fixed 2000 ATP
  (`verify(replay_counterexample=True)`), as the plan states; it does not
  touch the authenticity-only mode.

## What this package does not do

It runs no session, chooses no outcome, and changes nothing outside
`experiments/calib-myc-1/` except five entries in `tools/path_allowlist.json`
for generic OS temp roots. A calibration result, when it exists, is recorded
under `results/` with its own review.
