# RVB-BH-1a pilot 1 — INVALID, stopped after slot 1

The accepted execution package was run at
`9747164199334e01fb971a369bca8e71ff6f8891` after all eight CI checks passed.
`prelaunch.json` retains the observed GitHub checks and the operator's record of
Claude's ACCEPT review relayed by the owner. The plan, cards, rubric, prompts,
key, runner and scoring were not changed after acceptance. This directory adds
observations only. Results await review; no further session was attempted.

## What happened

| Slot | Scheduled annotator | Result |
| --- | --- | --- |
| 1 / A1 | Claude Sonnet 5 | INVALID infrastructure; response also fails format |
| 2 / B1 | Claude Opus 5 | NOT_RUN |
| 3 / B2 | Claude Opus 5 | NOT_RUN |
| 4 / A2 | Claude Sonnet 5 | NOT_RUN |

The same-slot local context capture passed. The live session reported exactly
one init, the requested model and empty tools, MCP servers, skills, slash
commands and plugins. The builtin agents list was unchanged and there were no
tool calls. However, the live init added
`messaging_socket_path: /tmp/cc-socks/28458.sock`, absent from the probe. That
field is not one of the four frozen allowed differences. The accepted checker
therefore reported `init field set changed` and
`init field changed: messaging_socket_path`.

This demonstrates a difference in the client's reported surface under the live
run. It does **not** demonstrate that the socket supplied extra model-visible
context, and its cause was not established. The reviewer's reported offline
Max check did not observe this difference; that review is historical reported
evidence, not a guarantee for the actual session. No exception was added after
seeing the result.

The native session returned successfully in 9.933 seconds, but the result string
is enclosed in a Markdown JSON fence. The frozen parser requires a bare JSON
object and rejects it. `response.txt` is byte-identical to the native result
string; no fence stripping, answer repair or scoring against the key was done.
Infrastructure invalidity takes priority over format failure, so the study's
result is **INVALID**, not INCONCLUSIVE or an agreement estimate.

## Audit and retained evidence

The operator read the context, invocation, all four native public events, full
response, result and empty stderr before writing `run/1/audit.json`. This audit
is by the Codex study-design session, not an independent reviewer. It records:

- one init, one assistant event, one rate-limit event and one success result;
- zero `system/api_retry` events, tool events, malformed lines or hidden-block
  removals; public JSONL therefore needed no rewriting;
- observed assistant model `claude-sonnet-5`;
- the unexpected init field and the separate format defect;
- `valid: false`, with hashes binding the result, public trace, response and
  context and a timestamp after session completion.

Only after this separate audit did a separate runner invocation write
`run/decision.json`. That invocation launched no client and marked slots 2–4
NOT_RUN. There were no retries, continuations or replacement slots.
The source run directory remains under `~/rvb-bh-1a-runs/`; its retained files
were copied byte for byte into `run/`. Reviewer's separate files under
`~/rvb-bh-1a-work/claude-review-context-1` were not modified or imported.

The native result reports 6,882 cache-creation input tokens, 2 input tokens and
909 output tokens; API duration 9.923 seconds. Its `total_cost_usd` is 0.036622
and model metadata says `costBasis: list`. This is client-reported list-price
accounting, not evidence of a charge beyond the Max subscription. The original
usage and model metadata remain in `run/1/public-events.jsonl`.

## All planned annotation positions

The first response is retained in full but has no valid annotation object under
the frozen parser. No proposed labels are promoted into an accepted observation.
The other 24 positions were never submitted to a model.

| Card | A1 | B1 | B2 | A2 |
| --- | --- | --- | --- | --- |
| R1 | Invalid response retained | NOT_RUN | NOT_RUN | NOT_RUN |
| R2 | Invalid response retained | NOT_RUN | NOT_RUN | NOT_RUN |
| S1 | Invalid response retained | NOT_RUN | NOT_RUN | NOT_RUN |
| S2 | Invalid response retained | NOT_RUN | NOT_RUN | NOT_RUN |
| B1 | Invalid response retained | NOT_RUN | NOT_RUN | NOT_RUN |
| B2 | Invalid response retained | NOT_RUN | NOT_RUN | NOT_RUN |
| D1 | Invalid response retained | NOT_RUN | NOT_RUN | NOT_RUN |
| D2 | Invalid response retained | NOT_RUN | NOT_RUN | NOT_RUN |

No within-model or between-model agreement, key accuracy or critical-error rate
is estimated. The pilot gives no evidence for integrating the instrument more
deeply. A future attempt requires a separately reviewed package or plan revision
that addresses the live-surface difference before fresh sessions; it must not
resume these slots or pool revised results with this invalid run. A future
successful Sonnet/Opus comparison would still be limited to one model family.

## Offline verification

```sh
python3 experiments/rvb-bh-1a/results/pilot-1/verify.py
```

This checks the retained-file manifest, accepted package bytes, CI gate,
chronology, preflight context, live trace classification, exact response bytes,
audit hashes and frozen decision without calling a model. The original runner
and checker are used, including the rule that invalidated slot 1.

The accepted rubric has an extra trailing blank line flagged by
`git diff --check origin/main...HEAD`. It remains unchanged because it is frozen
and embedded in the stimuli. Earlier clean checks concerned the amendment or
working-tree diff, not the entire PR. This result addition passes its own
whitespace check.
