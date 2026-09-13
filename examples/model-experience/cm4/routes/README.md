# CM-4 route trials and next experiments

**ACTIVE / PREPARED.** [plan.json](plan.json) fixes two compiler-designed requests
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
