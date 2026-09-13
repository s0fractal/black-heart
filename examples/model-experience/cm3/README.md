# CM-3 — one bounded receiver exchange

**PREPARED / NOT_RUN.** CM-2 is merged in `e102b07`; CM-3 is active and CM-4
remains queued. No receiver result exists yet. The owner authorized one fresh session through the existing Claude Max subscription.
The differential and context boundary are fixed before that session.

The [plan](plan.json) fixes the task and success conditions before the receiver
runs. The sender supplies the real DOC-F1 record plus an explicitly
[synthetic conflicting recommendation](control.json): stop on the first
unsettled EMPIRICAL fixture. The receiver must assess the recommendation for
the pinned code and record its own bounded result. This is not a blind benchmark:
the original record already explains the relevant invariant. One successful
exchange would demonstrate this workflow once, not general prevention of errors.
The original record's exact model identity is unknown; its compiler is declared
as Codex. Neither that declaration nor a receiver runtime model name proves
independence or authenticates an identity.

After committing these input files, `prepare_receiver.py NEW_DIRECTORY` builds
a fresh local Git snapshot containing only five approved source modules, the
fixed check, a source excerpt view, source manifest, two CM-2 packets and a
receiver prompt. It does not call a model or execute the check. Historical
source bytes come from the exact source commit; new input bytes must match the
preparation commit. The received record bytes are not rewritten.

The receiver snapshot has its **own measured Git HEAD** and no branch; this is
not the canonical source commit. `source-manifest.json` distinguishes the source
commit, input commit and file digests. The fixed `receiver_check.py` records the
actual local HEAD/status before and after execution, argv, conditions and raw
stdout/stderr in a new `run.json`. It runs three named existing regression tests against both the baseline and
a temporary variant with the preregistered `advice.patch`, plus explicit verdicts
for both fixture orders. Expected: baseline 3/3; advice 2/3 with only the
`[OMEGA, K]` mixed-order subtest failing. `probe.py` is fixed source, not record input. It never reads argv or test names from an experience record.

The response must be a separate experience record with exact file evidence and
relations to the two inputs. A future collection step must preserve the emitted
bytes and validate/save them with CM-2; an invalid response is a visible failure,
not permission for the sender to rewrite it as a passing result. No hidden model
reasoning, private chat, credentials or ephemeral signing keys belong in the
collected artifacts. A missing or unauthorized second model yields NOT_RUN.

This preparation does not implement a general model adapter or runner, shared
store policy, automatic adoption, LI transition, patch or publication. Packet
permissions remain owner-only. The receiver has to use the authorized local
check; model tool restrictions are not claimed as OS sandbox isolation.

[host-preflight.json](host-preflight.json) is the sender's technical rehearsal
of the fixed check against a separately materialized snapshot, not a receiver
result. Both records were read through CM-2 and found by component; the three
regressions passed; a second check refused OUTPUT_EXISTS and preserved the
report. The real receiver, when authorized, must get a new snapshot without
this preflight output or the sender's prior conversation.

## Receiver context boundary (B2)

`claude_session.py` is an experiment-specific launcher, not an experience API.
A fresh UUID and `/private/tmp` snapshot, safe mode, disabled auto memory, empty
setting sources, custom system prompt, no persistence and an exact Bash command
allowlist exclude normal project customization. The first-party Max OAuth token
is forwarded in memory only to `https://api.anthropic.com`; no API key, token,
request headers or private removed context is retained.

Safe mode still supplies account/date/attribution reminders. A loopback request
observer removes every client-added user-text block, keeping only the exact
approved packet prompt and subsequent allowed tool results. Unexpected system
context, tools, commands or exposed thinking are refused before forwarding.
The audit saves the actual submitted system/initial user context, tool schema,
counts and digests of removed text, and the public CLI stream. Thus the claim is
about submitted client context; undisclosed provider-side context is not observed.
The local transport preflight returns a clearly synthetic response and forwards
zero requests. It is not the receiver exchange. Full stdout is retained byte for
byte only when no hidden-thinking field is present; otherwise such lines are
omitted and the run fails the acceptance condition. Credentials and hidden
reasoning must never be persisted to satisfy a "full output" claim.

The configuration flags are checked against installed Claude Code help; the
[official environment reference](https://code.claude.com/docs/en/env-vars)
documents disabling auto memory. The request observation provides evidence
beyond relying on flags or on the model saying it has no memory.

Input commits referenced by `relations` must remain reachable: use a normal
merge for this PR, not squash/rebase. The frozen plan is not revised after a
live receiver run; results are separate artifacts. The original host preflight
is historical and covers only the old baseline check, not this differential.
