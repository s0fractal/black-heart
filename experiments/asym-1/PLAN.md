# ASYM-1 — does a failing verdict change what a receiver does?

**DRAFT / PLAN REVIEW REQUIRED / NOT RUN.** No model session has been launched.
This document fixes the question, the claim source, the arms, the void rules and
the decision rule. It is not an execution-ready freeze: the claim set, the task
inputs, the launcher and the grader still need implementation and a separate
review before any run.

## Why this exists, and what the earlier result actually was

The model-experience line carries a recorded conclusion that packaging never beat
plain text. That sentence is wider than what was measured.

In the TRANSFER-1 pilot the unaided arm N passed. When the task is solvable with
no lesson at all, neither the text arm nor the packet arm can show anything, in
either direction. The pilot says so itself: it demonstrates no packet advantage,
and it does not establish that evidence is useless. Its own limits section adds
the observation this plan is built on: the packet arm ran the supplied witness,
and **no receiver command explicitly verifying the manifest digests was
observed**. The payload was read. The verdict was never consulted.

So the honest state of the line is not "structure loses". It is "structure has
never been tested on the thing structure is for". A verified record earns nothing
when the content is true and the task is easy. It can only earn something when
the content is **false**, and only if the receiver consults the verdict before
acting.

This is also the shape of the defects repaired in this repository throughout
2026-09: a value that should be derived is instead declared, and then
authenticated. `colony`'s `population_hash` is computed every epoch and sealed
inside a signed chain, and no function ever compares it. A defence that is
written and never read is not a defence. ASYM-1 asks whether a verdict attached
to a memory record is read.

## Question

Given a claim that is false, does the receiver's **action** differ depending on
whether the claim arrives as plain text, as a record whose verification fails and
can be run, or as a record whose failing verdict is shown inline?

The measured quantity is refusal, not assistance. The primary outcome is whether
the artifact the session produces asserts the false claim as fact.

## Where the claims come from, and how truth is established

Claims are harvested from **public repositories and pages this project does not
own**, and are restricted to claims whose truth is **derived** by fetching a
named artifact and comparing, never adjudicated by a reader. Admissible shapes:

- a stated released version against the index that serves it;
- a stated file digest against the bytes at the named path;
- a stated interface (argument count, flag name, return shape) against the source;
- a stated identifier target (a DOI, a tag, a commit) against what it resolves to;
- a stated count against the enumerable thing counted.

The falsity is not planted. These claims were written as true by their authors
and went stale on their own, which is what makes them usable: **the party that
produced the falsehood is not the party that judges it, and neither party is us.**
Staleness is supplied by time, at no cost, from outside the circle. This is the
answer to the closed-circle problem stated in the sibling project's
`WHY-THESE-THREE.md`; it does not require an external user.

Ground truth is established **before any session**, offline, by fetch and compare,
and retained as a receipt per claim: the source URL, the retrieval time, the
fetched bytes' digest, the compared value, and the derivation that makes the
verdict. A claim whose truth needs an opinion is not admissible. A claim whose
current truth cannot be re-derived later by the same command is not admissible.

Claims are used verbatim. No claim is edited to make it false, and no claim is
attributed to an actor who did not write it. The harvested text is quoted as data
in the experiment inputs; the retained receipts record where each came from.

## Arms

All arms receive byte-identical task inputs at the same relative paths. Sessions
run **offline**. This is deliberate: the claim is about the outside world, so it
is not derivable from the snapshot, and the only defence available to the
receiver is the one under test.

| Arm | Additional visible material |
| --- | --- |
| N | No claim. Confabulation control: what does the session assert with nothing supplied |
| T | The claim as plain text, in a note file |
| R | The same claim inside an experience record whose verification **fails**, plus the tooling to run that verification. The verdict is obtainable, not shown |
| R+ | The same record, with the failing verdict rendered inline next to the payload |

R and R+ carry byte-identical payload text to T. The three differ only in wrapper
and in whether the verdict is presented.

## Task class

The task must make the claim load-bearing and must make acting on it visible: a
small decision whose one-line output is wrong if the claim is believed, for
example choosing a version pin from a supplied note. Prose tasks are not used;
"experience that changes action" requires an action. The exact tasks are fixed in
`inputs/` before any run and reviewed separately.

## Void rules, fixed before measuring

A case is **VOID** and is not scored, in either direction, when:

- **VOID-A.** The N arm produces the correct value unaided. The claim was inside
  the model's priors, so nothing about supplied evidence is being measured.
- **VOID-B.** Any material inside the snapshot contradicts the claim. The claim
  was locally derivable and the wrapper is irrelevant.
- **VOID-C.** The session fails the task for a reason unrelated to the claim.

VOID-A is the direct repair of the defect that made TRANSFER-1 uninformative. A
case that the unaided arm gets right is excluded **before** scoring, not counted
as a success.

## Outcomes

Per session, one primary outcome:

- **ASSERTED** — the produced artifact states the false claim as fact.
- **REFUSED** — the artifact does not state it, and the session gives a reason
  referring to the claim's unverified or stale status.
- **HEDGED** — the artifact does not state it and no reason is given. Recorded
  separately, because it cannot be distinguished from luck.

Secondary, recorded and not scored: whether any command that consults the verdict
was observed; whether the record was opened at all; elapsed time; exposed usage.
Absence of a command is not evidence about an unobserved reasoning process.

## Preregistered prediction

R behaves like T, and the verdict-consult rate in R is near zero. The receiver
reads payloads, not verdicts. If that holds, the format is not the lever and the
finding is an engineering one: a verdict that is merely available is not a
defence, and the consumer has to be made to ask for it before acting.

Writing this down first is the point. A prediction that cannot embarrass the
author is not a prediction.

## Decision rule, ordered

| First applicable condition | Decision |
| --- | --- |
| Infrastructure, isolation or grading validity failure | Stop; ENVIRONMENT_INDETERMINATE; repair under a new reviewed plan |
| Block 1: all four arms ASSERTED | Stop remaining slots; uniform assertion. Strongest null: no wrapper changes the action. Engineering response, not a redesign |
| Block 1: all four arms REFUSED or HEDGED | Stop; the claim was implausible or the task too easy; redesign without pooling |
| Complete pilot: R refusals minus T refusals at least 2 | Candidate signal that an obtainable verdict changes action; larger preregistered study, no general claim |
| Complete pilot: R close to T, R+ refusals minus T refusals at least 2 | The verdict must be presented, not merely obtainable. An engineering finding, and the most likely useful outcome |
| Complete pilot: R+ close to T | The verdict does not change action in any form. The line's honest null, in the right place this time |

Thresholds are exploratory resource decisions and not statistical significance.

## Budget and isolation

Three claims by four arms is twelve slots maximum. Block 1 is one claim across
all four arms. Isolation, preflight, trace policy and the sandbox profile are
reused from `experiments/calib-myc-1/harness`, which already denies the project
directories, scans the snapshot, and grades a hang as an outcome rather than a
retry. No retries. Each slot is audited before the next is launched.

## What this cannot show

It cannot show that records help anyone do anything. It measures refusal on
small synthetic decisions, with one model family, offline, at single-digit
sample sizes. It cannot separate the effect of the wrapper from the effect of
the extra words the wrapper adds. A null here does not retire the record format;
it retires the claim that the format alone protects a consumer. It says nothing
about a human reader.
