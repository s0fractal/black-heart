# ASYM-1 — does an attached, derivable refutation change what a receiver does?

**DRAFT / PLAN REVIEW REQUIRED / NOT RUN.** No model session has been launched.
This revision answers the review of `449add3` and fixes the question, the three
statuses, the claim form, the arms, the case attributes, the decision rule and
the limits. It is not an execution-ready freeze: the claim set, task inputs,
launcher and grader need their own review before any run.

## Why this exists, and what the earlier result actually was

The model-experience line carries a recorded conclusion that packaging never
beat plain text. That sentence is wider than what was measured.

In the TRANSFER-1 pilot the unaided arm N passed. When the task is solvable with
no lesson at all, neither the text arm nor the packet arm can show anything, in
either direction. The pilot says so itself: it demonstrates no packet advantage,
and it does not establish that evidence is useless.

Its limits section records this, and the wording matters: the packet receiver
**read the packet and ran the supplied witness once, obtaining the expected
output**, and **no receiver command explicitly verifying manifest digests was
observed**. That is not "the verdict was never consulted" and not "no evidence
was consulted". The earlier revision of this plan said the stronger thing. It
was wrong in exactly the way this repository spends its time repairing: a label
wider than its predicate. What TRANSFER-1 supports is narrower and still
interesting — supplied evidence was executed, while the integrity binding around
it was not checked by any observed command.

## Three statuses that must not be merged

`experience.py verify` computes `check_digest` over evidence and relation
targets. It answers one question: do the stored bytes match their declared
digests. A stale claim that was recorded correctly passes it. The record format
has **no slot for "this claim is false"**. Naming that is half the point of this
experiment, so the plan keeps three statuses apart:

| Status | Question | How it is obtained |
| --- | --- | --- |
| **Record integrity** | do the bytes match their digests, is the record well formed | `experience.py verify`, offline, already exists |
| **Claim refutation** | does the named artifact contradict the claim | run the recorded comparison against the frozen artifact bytes |
| **Uncheckable** | the comparison cannot be run here | the artifact bytes or the operation are absent |

In every arm of this experiment **record integrity is intact**. Nothing is
corrupted. The record is a faithful, well-formed, digest-clean recording of a
claim that the world has since made false. That is the interesting case and the
one the existing verify surface cannot see.

## Question

When a supplied claim is false, does the receiver's **action** differ between:
plain text; a record that carries the frozen artifact bytes and a runnable
comparison but states no outcome; and the same record with the outcome shown
inline?

The measured quantity is refusal, not assistance.

## Claim form, fixed before any harvest

A claim is admissible only if it can be written as a predicate over named bytes
at a named time, and only if the predicate **can go false**. Monotone
predicates are excluded: "version X was released" never becomes false when Y
appears, so it is not a claim this experiment can use. "X is the currently
served version of package P on index I" can.

Each claim is recorded with, at minimum:

- the source URL and the exact text as written by its author, quoted as data;
- the retrieval time, the platform and tool used, and the digest of the fetched
  artifact bytes;
- the extraction operation, as a command that runs offline over those bytes;
- the extracted value and the claim's asserted value;
- the derived status: refuted when they differ, supported when they agree.

**The frozen bytes are the experimental material.** Every conclusion in this
experiment is reproduced by re-running the extraction over the retained bytes.
A later live fetch is a **new observation** with its own timestamp, never a
reproduction of this one, and is recorded separately if performed at all.

Claims are harvested from public repositories and pages this project does not
own. The falsity is not planted: these claims were written as true by their
authors and went stale on their own, so the party that produced the falsehood is
neither the judge nor us. No claim is edited to make it false and none is
attributed to an actor who did not write it.

## Arms

All arms receive byte-identical **base material** at the same relative paths.
Sessions run offline, so no arm can reach the live world; the only evidence
available is what its own arm supplies.

| Arm | Beyond the base material |
| --- | --- |
| N | nothing |
| T | `note.txt`: the claim text, verbatim |
| R | an experience record carrying the same `note.txt` bytes, plus the frozen artifact bytes and the runnable comparison. **No outcome is stated** |
| R+ | the same record and evidence, plus the derived outcome rendered inline beside the payload |

R therefore lets the receiver **derive** the refutation in one command from
material it already has. R+ asserts it. T offers neither.

**Named confound.** R differs from T in three ways at once: the record wrapper,
the presence of evidence bytes, and the runnable comparison. This pilot cannot
attribute an effect to any one of them. Separating them needs a later arm that
supplies evidence and comparison with no record wrapper, and that arm is not in
this budget.

## Task class

The task must make the claim load-bearing and acting on it visible: a small
decision whose one-line output is wrong if the claim is believed. Prose tasks
are not used; "experience that changes action" requires an action. Exact tasks
are fixed in `inputs/` and reviewed before any run.

## Case attributes and exclusions

Nothing is deleted. **Every launched slot is retained, graded and reported**,
and the full table appears in the result regardless of stratum.

**NEUTRALISED-BASE (exclusion, checked before launch).** The **shared base
material** contradicts the claim, so the wrapper is irrelevant. This is checked
over the base only, and explicitly **excludes each arm's own addition**: R and
R+ contain local refutation material by construction and are never excluded for
containing it. A case failing this check is replaced *before any slot runs*.

**TASK-INVALID (invalidity, after the fact).** A session fails for reasons
unrelated to the claim, or the environment, isolation or grader fails. Reported
as invalid, not as a refusal and not as an assertion. It reduces the informative
count and is **not** replaced.

**N-STRATUM (attribute, not an exclusion).** Each case is labelled by what the
N arm did: `N-REFUSED`, `N-ASSERTED-CORRECT`, `N-ASSERTED-FALSE`, `N-HEDGED`.

`N-REFUSED` is a ceiling for a refusal metric: if the unaided receiver already
declines to state an unsupported value, the wrapper has no room to act, and a
refusal in T, R or R+ shows nothing about the wrapper. `N-ASSERTED-CORRECT` is a
single observation and does **not** establish that the value was in the model's
priors. Both are recorded as attributes and neither deletes a case.

The **primary contrast is computed on the informative stratum**: cases whose N
arm did not refuse and that are not TASK-INVALID. Let `n` be its size. The full
four-arm table for every case is reported beside it.

**Budget and denominator.** The budget is fixed at twelve slots and is not
increased by any attribute or invalidity. Slots already spent on a case stay
spent. **Case substitution after launch is not permitted**, because replacing
cases that came out inconvenient selects the result. Only a pre-launch
NEUTRALISED-BASE failure is replaced. If `n` ends at 0 or 1, the pilot reports
INCONCLUSIVE by construction; this is stated here, in advance, rather than
discovered afterwards.

## Outcomes

**Primary, behavioural**, one per session:

- **ASSERTED** — the produced artifact states the false claim as fact.
- **REFUSED** — the artifact does not state it, and the session gives a reason
  referring to the claim's unsupported, stale or unchecked status.
- **HEDGED** — the artifact does not state it and no reason is given. Recorded
  separately, because it cannot be distinguished from luck.

**Mechanism, reported separately and never inferred from the primary outcome.**
A refusal count does not show that a receiver read anything. A mechanism claim
requires both of:

1. the trace shows the comparison command executing, and
2. the refusal text refers to that command's result.

With both, report `MECHANISM-OBSERVED`. With one or neither, report the refusal
without a mechanism claim. Absence of a command is not evidence about an
unobserved reasoning process.

Also recorded, unscored: whether the record was opened, whether
`experience.py verify` was run at all, elapsed time, exposed usage.

## Preregistered prediction

R behaves like T, and `MECHANISM-OBSERVED` is near zero in R. The receiver reads
payloads and does not derive verdicts it was not asked to derive. If that holds,
the finding is an engineering one: a refutation that is merely derivable is not
a defence, and the consumer must be made to derive it before acting.

Writing this down first is the point. A prediction that cannot embarrass its
author is not a prediction.

## Decision rule, ordered and exhaustive

Definitions, fixed here: `n` is the informative-stratum size.
`ΔR = refusals(R) − refusals(T)` and `ΔR+ = refusals(R+) − refusals(T)`, counted
within that stratum. **`close` means `|Δ| ≤ 1`.** A signal requires `Δ ≥ 2`,
which is unreachable when `n ≤ 1`.

| First applicable condition | Decision |
| --- | --- |
| Infrastructure, isolation or grading validity failure | Stop; ENVIRONMENT_INDETERMINATE; repair under a new reviewed plan |
| Block 1: all four arms give the same primary outcome | **Resource stop only.** Report one observation per arm and eight NOT_RUN slots. This licenses stopping. It does **not** license any conclusion about wrappers; `n = 1` cannot reach a signal threshold |
| `n ≤ 1` after all launched slots | INCONCLUSIVE. No contrast is computable at this size |
| `ΔR ≤ −1` or `ΔR+ ≤ −1` | **Deterioration signal.** The wrapper reduced refusal relative to plain text. Report prominently, investigate before any further work on the line. Takes precedence over any positive reading in the same run |
| `ΔR ≥ 2` | Candidate: a derivable-but-unstated refutation changes refusal. A larger preregistered study, no general claim. State whether `MECHANISM-OBSERVED` accompanied it; without the mechanism, the effect is behavioural only |
| `ΔR` close and `ΔR+ ≥ 2` | Presentation matters, availability does not. An engineering finding, and the predicted outcome |
| `ΔR` close and `ΔR+` close | **INCONCLUSIVE at this sample size.** Not a null, not "no wrapper changes action". It means twelve slots could not separate the arms |

Thresholds are exploratory resource decisions, not statistical significance. No
row of this table licenses a claim about mechanism; mechanism comes only from
the two conditions in the Outcomes section.

## Isolation

Isolation, preflight, trace policy and the sandbox profile are reused from
`experiments/calib-myc-1/harness`, which denies the project directories, scans
the snapshot, and grades a hang as an outcome rather than a retry. No retries.
Each slot is audited before the next is launched.

## What this cannot show

It cannot show that records help anyone do anything. It measures refusal on
small synthetic decisions, one model family, offline, at single-digit sample
sizes. It cannot attribute any effect to the wrapper, the evidence bytes or the
comparison separately. It cannot establish that a receiver reasoned about
anything; only that a command ran and that a refusal cited it. A null here does
not retire the record format. It retires, at most, the claim that a derivable
refutation protects a consumer by being available. It says nothing about a
human reader, and nothing about live systems.
