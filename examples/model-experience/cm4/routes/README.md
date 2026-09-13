# CM-4 route trials and next experiments

**ACTIVE / ROUTES EXECUTED, READY FOR REVIEW.** [plan.json](plan.json) fixes two compiler-designed requests
under the owner's authorization to plan and run the next experiments. The
accepted lookup trial remains unchanged. Save and replay each get a new Codex
CLI process, an explicit skill load and a separate materialized repository
outside Projects. Two sessions maximum, 600 seconds each; no automatic model
retry. The client uses the existing ChatGPT login, with no API-key purchase,
request rewriting or Claude Max proxy.

[prepare.py](prepare.py) creates the fixtures, [preparation.json](preparation.json)
pins every input file and prompt, and the two input bundles preserve their exact
Git snapshots. An offline disposable-copy preflight validated the save fixture
and observed baseline 3/3 versus advice 2/3; neither live snapshot was run or
modified by that check. The plan, launcher and bundles are committed before live
execution. [run_session.py](run_session.py) records actual before/after checkout
state, timestamps, invocation and public events; hidden reasoning is not retained.

Invocation settings follow the installed CLI help and [official non-interactive
mode documentation](https://learn.chatgpt.com/docs/non-interactive-mode).
User config, memories, host skill discovery and hooks are disabled. This is a
new-session invocation boundary, not inspection of all submitted provider
context or a proof of model independence. The fixtures expose the relevant code
and expected differential; this is not blind error discovery or a no-skill
comparison. The model selects operations within the supplied route prompt.

## Later sequence

The plan also queues three bounded questions, without implementing them here:

1. **FEEDBACK-1:** return a stored refutation to a generator and measure its next
   proposal under unchanged constraints.
2. **TRANSFER-1:** compare a preregistered held-out task with and without an
   experience packet in matched fresh sessions.
3. **BUDGET-1:** turn one witnessed conflict into a finite authorized probe with
   a stop condition and durable result. Resource cost, available budget and
   stake remain separate; no stake accounting or schema change here.

Each stage depends on review of the preceding result. Failures stay in the
record, including client/environment failures. CM-4 remains ACTIVE until its
behavioral coverage is reviewed; running a trial is not accepting it.

## Recorded outcomes

The input freeze was pushed as `355f8853fb4ed5ccdb84cda4e71e4868ea55984e`
before either CLI session. The frozen plan retains `PREREGISTERED_NOT_RUN` as
its historical pre-execution state; it is not rewritten to announce success.

| Route | Observed behavior | Record |
| --- | --- | --- |
| save | One supplied record saved verbatim, source retained, readback and verify; 11 completed shell commands, none failed; inert marker absent | `1ee0f07c11867e3984e8f9116f0c00b14c08940ce8164396fb8c7ad3c38b0557` |
| replay | One execution of the fixed differential in a byte-identical copy under output/check; baseline 3/3, advice 2/3; separate result saved and read back; 8 completed shell commands, none failed | `682272a124f3512f594eb78cc3c86785797a50ad85f6998793d6f9507e63ff69` |

Both processes exited 0, with unchanged input files and snapshot HEADs.
The retained [save answer](results/save/final.txt) distinguishes storage from
replay. The [replay answer](results/replay/final.txt) rejects the advice within
two fixture orders and ATP 50. Its [record](results/replay/result.json)
uses `reported`, `source_read` and `replayed` with separate evidence and correctly
identifies sender-owned test design and local snapshot Git pins. Neither answer
nor any model-authored source was edited. “No network” in the receiver's limits
refers to source/tool access; the authorized Codex session itself used its
provider connection.

`results/<route>/` retains invocation, session timing/status, public CLI events,
final answer, host checks, artifact digests and generated files in a ZIP archive.
The replay record and run report also have byte-identical readable previews. Git internals
and Python bytecode caches from temporary variants are omitted; source files
and actual measured HEAD/status remain recorded. The input bundles preserve the
Git commits needed by the replay result's relations. Those commits are local
snapshot identities, not upstream ancestry; import the bundle to resolve them.
The final text's absolute temporary paths are historical; use the retained
relative paths for reading the result now.

The CLI did not expose a model name in the retained public stream; the records
leave it unknown. No claim is made that these two sessions used distinct models.
No hidden-reasoning events were emitted/retained. Command review found only
snapshot-local reads, checks and writes, with no visible other-session access.
This does not strengthen the invocation boundary into a full context audit.

## Offline checking

Run `python3 examples/model-experience/cm4/routes/verify_retained.py`.
It reconstructs inputs from both bundles in disposable directories, overlays
retained outputs, checks file digests, valid packets, local Git relation pins,
input preservation, raw result correspondence and differential outcomes. It
makes no model call and does not execute the evaluator. `test_cm4_routes`
includes restoration and rejection of a substituted input HEAD and is in the
unified suite. The host check scripts were implemented during/after the live
runs against the precommitted criteria; they were not part of the frozen input
or exposed to either receiver. Their PASS is mechanical validation, not an
independent human acceptance decision.

The save request covered a supplied complete record, not composing experience
from arbitrary conversation. The replay route did compose a new evidence-bound
record. These two bounded cases extend observed coverage; they do not establish
universal natural-language routing, automatic discovery, provider-independent
behavior, or zero-error memory. CM-4 remains ACTIVE pending review.
