> **SUPERSEDED:** Historical notes for 7684f39. Its isolation and worker-validity claims were refuted in review. Do not use these launch instructions. See [current package](README.md).

# TRANSFER-1 execution package — review required, no receiver run

Claude's ACCEPT review of plan head `0e5d44f22079a6f4f2543b718b18b3968253c2f1`
was relayed by the owner. PR #60 merged with eight green checks in
`7a2e7d807fc5640c9c0920d2121ca72967ed4940`. The accepted PLAN.md and all eight
pinned input/scoring files remain unchanged. Its draft/preparation labels are
historical; this README records the current stage.

**This package needs review before the first receiver call.** No calibration
or receiver session has run. Preparing and verifying a witness is a host-only
operation, not a receiver outcome. Do not merge or execute this package merely
because the plan was accepted.

## Retained offline evidence

[offline/receipt.json](offline/receipt.json) records the exact committed harness
source at `49db352`, all source digests, Python/Git versions, input digests,
start/end times and the individual observations. Each worker has a ten-second
limit and its own copy of the submission plus an independently rebuilt fixture.
Expected answers and pass/fail comparisons remain in the parent process.
This is a bounded grader for these cases, not a proof against a malicious Python
program deliberately attacking its evaluator.

| Implementation | Failed concrete cases |
| --- | --- |
| Reference repair | None: 15/15 pass |
| Type check after peeling | Annotated tag and nested annotated tag |
| Refuse all with INVALID_COMMIT | Both valid commits, plus missing object, missing path and directory path |
| Accept peelable objects (baseline) | Annotated tag and nested annotated tag |
| Missing object classified as INVALID_COMMIT | Missing object |
| Decode/re-encode with replacement | Both valid commits |

The extra three refuse-all failures follow from its fixed refusal code; the
frozen specification's `must_fail` list is a minimum requirement. All expected
failed sets are checked exactly in the offline verifier, and worker exceptions
or startup failures cannot satisfy these negative controls. Six malformed-value
checks expand the ten case families to fifteen concrete checks; the primary
unit remains one binary outcome per receiver, not fifteen independent samples.

The same receipt retains successful witness output, removal of its temporary
directory, sandbox probes and all 512 binary decision sequences. The first
uniform block truncates the schedule; attempts to append slots after that stop
are rejected. An infrastructure failure takes priority over success counts.

Development attempts are retained separately in `development/attempt-1/` and
`development/attempt-2/`. Attempt 1 marked the offline suite failed because its
validator incorrectly demanded only two failures for refuse-all. Attempt 2
accepted the correct additional failures. These are development runs of trusted
host controls, not model retries, and are not pooled with receiver results.
The final receipt comes from the committed harness revision named above.

## Prepared inputs and isolation

[package/freeze.json](package/freeze.json) binds three Git bundles, their heads
and every receiver-visible file, the fixed nine-slot schedule, CLI settings,
harness hashes and a single prospective run directory. It does not claim that
a receiver has been launched. The [readback receipt](prepared-check.json)
verifies all bundles, exact file sets, one-commit histories and identical T/P
lesson bytes. The snapshots have no upstream history, remotes, arm names or
FETCH_HEAD containing the bundle's host path.

The platform is this macOS host, Codex CLI `0.154.0`, requested model
`gpt-6-astra`, medium reasoning effort, 300 seconds per receiver. No model
substitution or API purchase is provided. Runtime-reported model/usage data are
retained if emitted; requested model identity is not independent attestation.

The named `transfer` permission profile allows the current snapshot and reads
of minimal OS resources, Homebrew installations and Apple command-line tools.
These runtime directories must not contain experiment material. It denies tool
network access and grants no access to Projects, the home directory, other
snapshots or host receipts. The offline probe verifies a real external canary
cannot be read directly or through a symlink, a local listener cannot be reached,
and Python/Git plus local writes work. A fresh preflight precedes every call.
These probes test named boundaries, not all possible OS escape techniques.

This uses [OpenAI's documented named permission profiles](https://learn.chatgpt.com/docs/config-file/config-reference),
not the broader default workspace-write read access. The provider connection
remains available to the host CLI; no request rewriting is used. Tool network
restrictions do not by themselves disable remote tools, so memory, apps, plugins,
additional agents, browser and computer tools are disabled explicitly. User
configuration and rules are ignored, project documentation loading is zero,
and shell tools inherit only the explicit environment in runtime.py.
`skip_host_skill_discovery` remains experimental; warnings must be retained.
This is a new CLI process with observed tool boundaries, not an audit of every
provider-side context source. Review the actual emitted tool surface and context
warnings before accepting a slot's validity.

## Review and run procedure

Reproduce offline checks to a **new** output directory; outputs never overwrite:

```sh
python3 experiments/transfer-1/harness/test_harness.py
python3 experiments/transfer-1/harness/offline.py /private/tmp/transfer1-offline-review
python3 experiments/transfer-1/harness/verify_prepared.py experiments/transfer-1/execution/package /private/tmp/transfer1-prepared-review.json
```

Offline grading and preflight require the pinned macOS CLI environment. The
four scheduling/receipt unit tests also run in the existing CI matrix without
Codex or model authentication. To regenerate bundles after a reviewed amendment,
use prepare.py with a new directory, preserve the prior freeze and review the
replacement before calls. Never regenerate to replace launched slots.

After explicit review of the exact execution-package commit, run one slot:

```sh
python3 experiments/transfer-1/harness/run_slot.py experiments/transfer-1/execution/package --reviewed-head FULL_ACCEPTED_PACKAGE_COMMIT
```

The argument is the operator's record of accepted review; the script checks
committed bytes, not the existence or independence of a human review. It claims
the fixed slot before launch, creates a neutral snapshot, runs preflight,
retains public events and stderr, freezes reader.py, then grades it in sandboxed
workers. Hidden reasoning events are omitted and counted. Session elapsed time
excludes subsequent host grading. Timeouts fail the slot; missing output is not
silently retried. A crash or interrupted claimed slot blocks further progress.

Before the same command may launch the next slot, retain `audit.json` inside the
completed slot's host output directory with:

- `reviewer`: attribution of the operator/reviewer.
- `result_sha256`, `events_sha256`: hashes of result.json and public-events.jsonl.
- `valid`: boolean assessment of scope/context/trace validity, with `evidence`
  naming public event lines, commands and the basis of the decision. Include
  prohibited edits even if reverted; a final hash comparison cannot see them.
- `supplied_witness_run`, `receiver_created_tag`, `tag_check_executed`: each
  `observed`, `not_observed` or `unknown`, supported by that evidence. Distinguish
  supplied witness execution from a receiver-authored tag check.

This audit never sends grading feedback into a receiver. It is needed because
shell commands cannot reliably be classified by keyword search. An invalid
slot stops the pilot as environment-indeterminate; incomplete audits block the
next call. After slot three, the frozen early-stop rule determines whether six
slots remain NOT_RUN. Subsequent invocations only report a terminal decision;
they do not start replacement calls. Report exposed usage and warnings from the
retained events, including unknown values, without inventing missing metadata.

The profile, harness, bundles and receipts are offered for review together.
Automatic live execution, general packet superiority and completion of
TRANSFER-1 are not claimed.
