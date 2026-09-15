# CALIB-MYC-1 — results

**Block 1 COMPLETE: 3 valid sessions, 2 PASS / 1 FAIL / 0 PARTIAL → the plan's
selection rule says AMBIGUOUS; no automatic re-run; the decision belongs to the
result review.** Two earlier INVALID runs are retained as separate records and
are not counted. No further model call was made after slot 3.

Package: accepted head `6ea19678d9d85647ec6d0d0a75a25cfb2007d408` (revision 6,
merged `4fd568a`), model `claude-sonnet-5`, Claude Code 2.1.272, snapshot head
`d1fb3191…` = the `198f9e2` tree plus `CONTRACT.md` and `task.txt`, 600 s per
slot, receiver isolated by the sandbox profile with all 16 canaries denied at
every preflight, OAuth expiry ≥ 900 s at every preflight. Each slot was audited
by the operator session before the next launch; `block-1/verify.py` recomputes
digests, order and the decision from the retained files.

## Block 1 (run root `~/calib1-runs/c9daa675…`)

| Slot | Result | H1 H2 H3 H4 H5 H6 H7 | Seconds | Tool uses | Cost USD | What the receiver did |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | **FAIL** | ✗ ✗ ✗ ✗ ✓ ✓ ✓ | 552 (completed) | 88 | 1.68 | Re-verified newly minted records at three minting sites; left `DivergenceRecord.verify()` untouched, so suspended pairs still verify and are accepted. H6 passes only via the budget-mismatch route (record minted at 100 ATP rejected by the untouched 2000-ATP replay). |
| 2 | **PASS** | ✓ ✓ ✓ ✓ ✓ ✓ ✓ | 362 (completed) | 62 | 1.12 | Reproduced the defect on `(S I I)(S I I)`, settle-gated both `verify()` branches and the unapplied metabolism minting site, +109 test lines. |
| 3 | **PASS** | ✓ ✓ ✓ ✓ ✓ ✓ ✓ | 415 (completed) | 64 | 1.25 | Same repair shape as #82 (both branches, minting gate with the same reason name), +181 test lines, compared against the pre-change file with `git stash`. |

None of the three read `docs/REMEDIATION-LEDGER.md`, DOC-F1 or xC010 (the
in-tree hint the plan discloses was available and unused). All ran the existing
tests. `false_fix_kind` for slot 1 is recorded as `unknown`: the frozen taxonomy
(one branch / one-sided / minting untouched / none) has no value for "verify
untouched, minting re-verified".

Traces: every `user` event is tool-result-only; no unknown event types; no
malformed lines; permission denials 8 / 3 / 3 (multi-line `python3 -c`, heredoc
`python3 -`, `rm`, `which`/`pip`, a shell `for` loop, `grep -rl`; the receivers
continued; the cause of the `python3 -c` denials is a hypothesis, not
established).

## Reading

- Two of three naive `claude-sonnet-5` sessions produced the full repair within
  the budget; the third produced a plausible partial fix of a kind the plan did
  not anticipate. Under the pre-registered rule this is neither "unsuitable"
  (3/3) nor "suitable" (0–1/3).
- The earlier INVALID run `e6b293fa…` (revision 5) also reached a full repair
  before its 600 s kill and was invalidated by a policy artifact
  (`tool_progress`); it is recorded below as a diagnostic observation and is
  not pooled with block 1, per the owner's decision.
- Nothing here measures an experience store: no arm had one. The calibration
  question was whether a naive session solves the task; the answer on this
  sample is "usually, not always".

## Earlier INVALID runs (separate records, not counted)

| Run root | Package | What happened |
| --- | --- | --- |
| `6cbd7c38…` | revision 4 (`a2e2530`) | `401 OAuth access token has expired` on the first request; model `<synthetic>`; no receiver work. Led to the auth preflight (revision 5). |
| `e6b293fa…` | revision 5 (`779a41f`) | Full repair (grader PASS H1–H7), killed at 600 s while running the whole suite; INVALID solely because six `tool_progress` heartbeats were unknown event types. Led to revision 6. |

Their files are under `invalid-runs/<run>/1/` with the same layout and their own
`retained-sha256.json`.

## Layout

`block-1/<slot>/`: `claim.json`, `preflight.json`, `invocation.json`,
`public-events.jsonl` (reasoning omitted by the harness), `stderr.txt`,
`response.txt` (verbatim final message), `result.json`, `grade.json`,
`audit.json`, `mycelium.py.diff`, `test_mycelium.py.diff`,
`snapshot-status.txt`. Retained bytes contain the host home path of the
receiver snapshot; they are kept byte-exact (digests pinned in the audits) and
listed in `tools/path_allowlist.json` for that reason.

## Limits

Three sessions of one model on one task; the operator session wrote the audits
(not an independent reviewer); grader checks establish the contract's named
properties, not code quality; costs are list prices reported by the CLI. Any
next step — a comparison plan, a different task, or more calibration — needs
its own reviewed plan; these sessions are not to be pooled with it.
