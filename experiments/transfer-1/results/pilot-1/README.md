# TRANSFER-1 pilot: early uniform success — accepted as a bounded record

The accepted execution package at `de36fe5c0d7c446fb40c4c03fadf07da87665e9c`
was launched after all eight CI checks passed (see `ci-before-live.json`).
Exactly three receiver sessions ran, in the frozen N,T,P order, with no retries.
The operator audited each public trace before the next launch; after slot 3,
the unchanged decision rule returned **EARLY_UNIFORM_SUCCESS**. Slots 4–9 are
**NOT_RUN**, not failures or additional successes. No further model call was made.

| Slot | Condition | Primary outcome | Host checks | Session seconds |
| --- | --- | --- | --- | --- |
| 1 | N: no lesson | PASS | 15/15 | 162.36 |
| 2 | T: plain misleading lesson | PASS | 15/15 | 65.44 |
| 3 | P: same lesson plus witness | PASS | 15/15 | 71.71 |

These are **one success out of one observed session per condition**, on one
synthetic task. Fifteen host checks diagnose each patch, not fifteen samples.
This pilot demonstrates no packet advantage. Uniform success triggered the
preregistered resource stop; it does not establish a population ceiling or
that evidence is useless. Any redesign or calibration requires a separate
reviewed plan and must not pool these sessions. FEEDBACK-1 has not started.

## Observations and limits

All three receivers authored and executed annotated-tag checks. T read the
lesson and repaired the code according to the contract. The public trace shows
no explicit engagement with the lesson; it does not show whether the receiver
weighed, rejected or ignored the advice. P read the
packet and ran the supplied witness once, obtaining the expected output; no
receiver command explicitly verifying manifest digests was observed. The host
verified protected bytes independently. P also authored a separate tag check.
The trace shows P editing the source before running the witness, so successful
witness execution alone cannot establish that replay caused its repair.

N had two failed auxiliary test commands (same-commit graft and malformed-tree
repack) before a corrected local check succeeded. T and P had no nonzero completed
commands. All three traces retain the experimental skill-discovery warning and
Git warnings about denied external cache/ignore access. No successful foreign
experiment-content read, network operation or protected input edit was observed.
The operator audits are from Codex, not independent review or proof of hidden
provider context. Requested model/settings are in each invocation; the retained
public events do not independently attest the actual served model.

Each preflight passed with zero content matches and zero scan errors. Tmp remains
readable. `/opt/homebrew` is explicitly readable and is **not scanned**; transformed
material and concurrent writes remain limitations. The loopback network probe
is not a survey of external destinations. These bounded observations do not
establish perfect isolation.

`2/audit.json` contains a transcription error: 18 events instead of 17. The
original remains intact; `2/audit-correction.json` records the correction after
slot 3 started. The entire trace had been inspected before that launch; validity
and event-identifier evidence are unchanged.

## Retained evidence and verification

Directories `1/`, `2/`, `3/` contain byte-identical copies of host claim,
preflight, invocation, public JSONL events, stderr, submitted reader.py, grade,
result and attributed audit files. `summary.json` retains elapsed times and
exposed usage; `decision.json` includes every unlaunched slot. Numeric reasoning
usage is metadata; no hidden reasoning content is requested or retained.

The original archived Git snapshots remain in the protected run root recorded
in `summary.json`; they are not copied into this repository. The committed v3
input bundles plus each submitted reader.py suffice to reconstruct the graded
source. `retained-sha256.json` binds the copied evidence and generated summary.
Documentation and verifier are outside that evidence manifest.

Run from the repository root (no model calls):

```sh
python3 experiments/transfer-1/results/pilot-1/verify.py
```

The verifier checks retained hashes, audit/source bindings, launch chronology,
CI head/results and the unchanged stopping rule. It does not repeat human trace
review or claim to authenticate the unsigned operator audits. Original plan,
inputs, harness and execution bundles were not rewritten after launch.

## Post-result review

Claude’s ACCEPT review of `712d42c`, relayed by the owner, accepts this as an
honest record, not evidence of packet benefit or demonstrated resistance to
misleading advice. See `2/audit-interpretation-note.json` for the correction to
the original audit’s “despite the lesson” wording. Historical audits and traces
remain byte-identical. The new note is outside the original retained manifest.

For the next reviewed design, record and inspect the completed audit in a
separate operator step before invoking the next slot. Do not combine audit
creation and launch in one tool-call chain. Mere elapsed time would not itself
prove review quality; explicit evidence and correct event references still matter.

A successor needs a fair visible contract plus an empirical uncertainty that the
lesson and witness can meaningfully resolve, or a larger search problem where
they identify relevant code. This is a design direction, not a validated task or
launch authorization. Preserve a plain-text control, review the new plan before
launch, and do not pool its outcomes with this pilot. FEEDBACK-1 remains deferred.

PR #62 was merged with all eight checks green in ordinary merge
`467a7c6d341ffbe9e01f74dcdb294b94cee5f026`, whose second parent is the
accepted `712d42ca4e80fcc9008e3003f2711e76402a5430`. The accepted package
`de36fe5c0d7c446fb40c4c03fadf07da87665e9c` remains reachable from main.
