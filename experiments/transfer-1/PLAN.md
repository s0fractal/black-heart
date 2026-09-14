# TRANSFER-1 — controlled transfer of Git object-type experience

**DRAFT / PLAN REVIEW REQUIRED / NOT RUN.** No model session or experiment has
been launched for this plan. This PR fixes the task inputs, log text, optional
witness source and scoring specification. It is not an execution-ready freeze:
the launcher, isolation snapshots, deterministic grader and countercontrol
checks still require implementation and review before any run.

## Question and specimen

Can relevant executable evidence help a receiver reject an overly broad repair
recommendation, compared with receiving exactly the same recommendation as text?
The primary contrast is **P versus T**, not P versus no information. N measures
unaided repair and the possible harm of the recommendation.

The real source lesson is CM-2 B1: a shape-valid tree SHA was accepted as a commit
pin before the repair. See [CM-2 B1](../../examples/model-experience/cm2/README.md#b1-amendment).
The target is a **new synthetic consumer**, `inputs/common/reader.py`: it peels
`revision^{commit}` and so accepts an annotated tag object where the contract
requires the original object itself to be a commit. This is not a newly found
Black-Heart runtime bug and not a variant of DOC-F1. It tests transfer of a
known object-type invariant to another resolution path. The designer knows the
intended repair. This revision supersedes the design at PR #60 head 5ab5fe5,
before any receiver run. The task is still small and may be trivially solvable;
an explicit contract may make unaided repair easy. We choose an
explicit early-stop rule; no calibration run has been performed.

The receiver contract explicitly says: "The identifier must name a commit
object itself." Every arm sees this rule; the grader applies it rather than a
hidden interpretation of "commit identifier". The contract names no validation
command or repair recipe. Annotated tag objects fail this visible requirement
even when peeling reaches a commit. Restoring this sentence after review of
62b6b71 removes ambiguity while retaining the early-stop response to ceiling
risk. In T, the advice conflicts with the contract; P adds relevant evidence.
This is a consumer-specific contract, not a rule for all Git revision APIs.

The shared log is a **synthetic, deliberately overbroad recommendation** written
for this experiment, inspired by the CM-2 B1 class of error. It is not a quotation
from CM-2, a genuine historical model observation, or the accepted CM-2 repair.
It recommends peeling with rev-parse as sufficient validation. T and P receive
identical text without a correctness label; this host-only plan discloses the
construction. The experiment concerns resistance to misleading advice, not just
reuse of correct memory. Designer and planned receivers are Codex gpt-6-astra;
shared model habits and designer wording are explicit threats to generalization.

## Frozen conditions

All sessions receive byte-identical `inputs/common/` at the same relative paths.
The task prompt refers to optional lesson material in the same way in all arms.

| Arm | Additional visible material |
| --- | --- |
| N — no lesson | No lesson directory |
| T — plain log | `lesson/lesson.txt`, exactly `inputs/lesson/lesson.txt` |
| P — checkable packet | The same `lesson/lesson.txt`, plus witness.py and manifest.json from `inputs/packet/` |

The manifest binds the same lesson bytes and the executable witness. The witness
constructs an annotated tag, shows its original type, successful peeling to the
commit and equal path bytes despite different object identifiers. This directly
exposes the boundary missed by the log; it supplies neither a reference patch
nor the host grader. In Claude's review of 62b6b71, relayed by the owner, the
reviewer reports running these witness bytes and obtaining exactly the manifest's
expected output. This is attributed external review evidence, not an execution
by this author or a retained raw run receipt. The witness and manifest remain
byte-identical to that reviewed revision. PREPARED_NOT_EXECUTED in the manifest
records the author's preparation stage; it is not a current claim that nobody
has executed the witness. The execution package still needs its own retained
offline validation before any receiver session.
This minimal evidence bundle is an experimental treatment, not a new CM-2
profile or a claim of third-party authentication. T and P share the lesson's
claims; P has additional executable material and associated reading/verification
cost. Thus the contrast measures that practical bundle, not cryptography alone,
not equal token counts, and not a universal advantage of structured memory.

`input-sha256.json` binds these inputs and the host-only scoring specification.
Changing any of them after review requires a new reviewed plan revision and a
new freeze; never rewrite a launched arm to improve its observed outcome.

## Units, order and resource limit

Exploratory pilot: **at most 9 new sessions, up to 3 per arm**, one fixed target
task. Sessions are repeated trials on one task, not nine independent engineering
problems.
Order is fixed now in three balanced blocks: **N,T,P / T,P,N / P,N,T**.
This reduces simple order imbalance; it is not randomized allocation and does
not eliminate time effects or service drift. Report raw outcomes by block.
After the first complete valid block, stop if all three outcomes equal: record
EARLY_UNIFORM_SUCCESS or EARLY_UNIFORM_FAILURE and six remaining NOT_RUN slots.
This is a resource-conservation choice with a risk of missing a real effect,
not measured difficulty or proof of a population ceiling/floor. No further
outcome-based interim stop is allowed. Otherwise complete the remaining blocks.
No calibration model session is included or authorized by this plan revision.

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
Only reader.py is submitted to the host grader. Separately check that protected
input bytes are unchanged; forbidden edits observed in the trace remain
reportable even if reverted. Allowed scratch files, Python caches and the
witness's temporary directory inside the snapshot are not additional production
edits and do not fail the submission merely by existing or having existed.
The grader must not apply a blanket clean-working-tree requirement. A witness
failure or leftover temporary directory is recorded as a diagnostic, not an
automatic repair failure; input tampering and scope violations remain distinct.
Secondary outputs: elapsed time, exposed usage, whether P ran the supplied
witness, input modification, tool-scope deviations and reported uncertainty.
For every arm, record whether public command evidence shows the receiver created
an annotated tag for a check, and whether the check actually executed. Distinguish
supplied-witness execution from a receiver-authored check. Use observed / not
observed / unknown (incomplete trace); absence of a command is not evidence of an
unobserved reasoning process. Retain supporting event identifiers and commands.

Failed, late or missing patches count as primary failures. A normal session
reaching its 300-second limit is a failure, not grounds for replacement.
Infrastructure, isolation or grader faults invalidate interpretation: stop,
retain assigned outcomes and report ENVIRONMENT_INDETERMINATE; do not silently
exclude or rerun them. A deliberately denied out-of-scope command is a recorded
deviation, not automatically an infrastructure fault.

[scoring/decision.json](scoring/decision.json) fixes the ordered decision rule:

| First applicable condition | Decision and next action |
| --- | --- |
| Infrastructure, isolation or grading validity failure | Stop; environment-indeterminate; repair setup under a new reviewed plan |
| First block has three successes or three ordinary failures | Stop six remaining slots; early uniform result; redesign or separately calibrate without pooling |
| Complete pilot ceiling/floor | Unsuitable for discrimination; redesign without pooling (defensive rule, unreachable with the first-block stop) |
| Complete valid pilot: P minus T successes at least 2 | Candidate for a larger preregistered multi-task study; no general advantage claim |
| Complete valid pilot: P fewer successes than T | Negative pilot signal; no advancement based on a claimed packet advantage |
| Complete valid pilot: P minus T successes 0 or 1 | Indeterminate; no positive advancement decision from this pilot |

After early stop, report one observed outcome per arm and six NOT_RUN slots,
not successes out of three and not the complete-pilot threshold. After all nine,
report successes out of three per arm, the raw block outcomes and P minus T.
Always report N alongside that contrast: P > T with P <= N supports, at most,
recovery from misleading advice, not improvement over unaided repair. P adds
relevant informational content as well as executability; this design cannot
isolate the value of execution from simply reading the witness or its expected
output. Do not condition the primary comparison on whether a receiver ran it.

Thresholds are exploratory resource decisions, not statistical significance.
One task and same-model sessions cannot establish generalization or model
independence. Any redesign or follow-up requires a separate reviewed plan and
must not pool its sessions with this pilot.

## Gates and next work

1. Review this design and the exact common inputs, plain log, packet and cases.
2. Implement the deterministic fixture/grader, launcher and snapshot builder in
   this experiment task. Check the flawed baseline and a host-only reference
   repair offline. Also demonstrate rejection of every negative control named in
   cases.json: post-peel type check, refuse-all, peelable-object acceptance,
   missing/wrong-type confusion and byte decoding. Retain each case result and
   ensure rejection is semantic, not an import/fixture error. Validate revised
   witness output and decision branches offline, then freeze and review that
   execution package before model calls.
3. Commit/push the approved input snapshots, schedules and digests before the
   first session. Preserve every launched slot and stop at the fixed limit.
4. Review results before merge or any FEEDBACK-1 work. FEEDBACK-1 must retain
   a same-objection plain-text control when attributing benefit to the packet.

The current accepted CM-1–CM-4 results and their historical plans remain unchanged.
