# TRANSFER-1 — controlled transfer of Git object-type experience

**DRAFT / PLAN REVIEW REQUIRED / NOT RUN.** No model session or experiment has
been launched for this plan. This PR fixes the task inputs, log text, optional
witness source and scoring specification. It is not an execution-ready freeze:
the launcher, isolation snapshots, deterministic grader and countercontrol
checks still require implementation and review before any run.

## Question and specimen

Does access to checkable experience improve a new consumer repair over the same
lesson stated as plain text? The primary contrast is **P versus T**, not P versus
no information. N provides a secondary baseline for receiving the lesson at all.

The real source lesson is CM-2 B1: a shape-valid tree SHA was accepted as a commit
pin before the repair. See [CM-2 B1](../../examples/model-experience/cm2/README.md#b1-amendment).
The target is a **new synthetic consumer**, `inputs/common/reader.py`: it peels
`revision^{commit}` and so accepts an annotated tag object where the contract
requires the original object itself to be a commit. This is not a newly found
Black-Heart runtime bug and not a variant of DOC-F1. It tests transfer of a
known object-type invariant to another resolution path. The designer knows the
intended repair; the source and contract reveal the problem to a capable reader.

## Frozen conditions

All sessions receive byte-identical `inputs/common/` at the same relative paths.
The task prompt refers to optional lesson material in the same way in all arms.

| Arm | Additional visible material |
| --- | --- |
| N — no lesson | No lesson directory |
| T — plain log | `lesson/lesson.txt`, exactly `inputs/lesson/lesson.txt` |
| P — checkable packet | The same `lesson/lesson.txt`, plus witness.py and manifest.json from `inputs/packet/` |

The manifest binds the same lesson bytes and the executable witness. The witness
shows commit/tree type and equal path bytes; it does not contain the target
consumer's tag-peeling cases or a reference patch. It has not been executed as
part of this planning PR; its expected output is a preregistered hypothesis.
This minimal evidence bundle is an experimental treatment, not a new CM-2
profile or a claim of third-party authentication. T and P share the lesson's
claims; P has additional executable material and associated reading/verification
cost. Thus the contrast measures that practical bundle, not cryptography alone,
not equal token counts, and not a universal advantage of structured memory.

`input-sha256.json` binds these inputs and the host-only scoring specification.
Changing any of them after review requires a new reviewed plan revision and a
new freeze; never rewrite a launched arm to improve its observed outcome.

## Units, order and resource limit

Exploratory pilot: **9 new sessions, 3 per arm**, one fixed target task. Sessions
are repeated trials on one task, not nine independent engineering problems.
Order is fixed now in three balanced blocks: **N,T,P / T,P,N / P,N,T**.
This reduces simple order imbalance; it is not randomized allocation and does
not eliminate time effects or service drift. Report raw outcomes by block.

Use one pinned Codex model (`gpt-6-astra` requested uniformly), one CLI version,
same settings, same tool permissions and 300 seconds maximum per session.
No model substitution, continuation, adaptive prompt or silent retry. If that
model/client cannot run under the reviewed settings, stop and record NOT_RUN
for remaining slots. An environment/client failure after launch stays visible
in its assigned slot and is not replaced. Maximum scheduled wall budget is
45 minutes, excluding host setup/checking; token usage is recorded, not claimed
to be capped by this wall limit. No new API purchases or request-rewriting proxy.

## Isolation and information boundaries

Separate ephemeral repositories outside Projects; no original chat, shared
store, source-repository history, earlier response, grader or arm labels in the
receiver snapshot. Each snapshot contains only its allocated input files.
No pre-existing host skill is needed. Configure memory/config/skill loading
explicitly and retain any experimental-feature warnings. Pin actual settings
in the launcher before its review; flags alone do not prove zero hidden context.
Record public commands, final output, actual model metadata if exposed, timestamps,
HEAD/status and input/output hashes. No hidden reasoning is requested or retained.

Models may write scratch checks and run local Git/Python in their snapshot,
including the supplied witness in P. No network tool access, other session,
other arm, host grader or post-submission feedback. Freeze reader.py at session
termination before running host cases. Do not give one arm more time for replay;
verification competes with repair inside the same wall budget. A local automated
preflight must check effective restrictions before any model call. Undisclosed
provider-side context remains outside observation; these are same-provider trials.

## Scoring and interpretation

[scoring/cases.json](scoring/cases.json) fixes the observable contract cases.
Primary result is an all-cases-pass binary outcome per session. Require valid
commit controls as well as wrong-type refusals so a refuse-everything patch fails.
Case-level counts diagnose failures but must not inflate the sample size.
Secondary outputs: elapsed time, exposed usage, whether P ran the witness,
input modification, tool-scope deviations, and concise reported uncertainty.
Failed/late/missing patches count as failures in the primary table; distinguish
client failures descriptively without selectively removing them.

Report N/T/P successes out of 3, per-block results and P−T difference. With this
small single-task pilot, do not claim statistical significance, generalization,
model independence or a causal benefit established across tasks. If all arms
succeed, report a ceiling/no demonstrated advantage; if all fail, report failure
of the task/setup. Do not replace the task and pool new trials with these nine.
P≤T, P>T and indeterminate outcomes are all admissible. Any broader experiment
requires its own reviewed plan.

## Gates and next work

1. Review this design and the exact common inputs, plain log, packet and cases.
2. Implement the deterministic fixture/grader, launcher and snapshot builder in
   this experiment task. Check the flawed baseline and a host-only reference
   repair offline; freeze and review that execution package before model calls.
3. Commit/push the approved input snapshots, schedules and digests before the
   first session. Preserve every launched slot and stop at the fixed limit.
4. Review results before merge or any FEEDBACK-1 work. FEEDBACK-1 must retain
   a same-objection plain-text control when attributing benefit to the packet.

The current accepted CM-1–CM-4 results and their historical plans remain unchanged.
