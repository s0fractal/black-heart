# RVB-BH-1a execution preparation — DRAFT, LAUNCH BLOCKED

PR #65 merged at b92cb87 (accepted e522d75), then PR #66 at e29419a
(accepted abe9dec). This is the next task, not permission to launch.
Accepted cards, plan, schedule, key and historical receipts are unchanged.

Completed offline work:

- Four fixed plaintext prompts built from the accepted rubric and exact card order.
  Neither the key nor reviewer comments are supplied to annotators.
- Strict JSON answer parser rejects duplicate JSON keys, duplicate/missing IDs,
  bad types/labels and missing or overlong public justifications.
- Scoring implements all four comparisons and the accepted decision priority.
  Six tests cover reference/order invariance, all-SUPPORTED/OPEN/AMBIGUOUS,
  missing/duplicate IDs and JSON keys, 6/8 versus 7/8, critical overclaims,
  invalid infrastructure and a changed/invalid key.
- Candidate native backends: A = gpt-6-astra via codex-cli 0.154.0;
  B = claude-opus-5 via Claude Code 2.1.270 and existing native Max login.
  Both request medium effort; versions were read without invoking models.
  Claude --safe-mode and --tools "" are listed in this installed client's help.
  No OAuth rewriting proxy, copied credentials or API purchase is used.

## Why launch is still blocked

The native configuration inspection is not an isolation proof. Before this is
an execution-ready package, retain offline evidence of the actual context/tool
surface for both configured clients. In particular, disabled Codex feature flags
have not yet established that every built-in tool is absent. Claude's current
single-result JSON mode does not expose enough of its intermediate events for
the promised tool/context audit. The runner/parser needs complete native public
traces, preserved without unnecessary reserialization, and tests with simulated
client events (tool calls, partial lines, timeout and client errors).

`freeze.json` therefore has `launch_ready: false`; run_slot.py refuses before
claiming any slot or invoking a client. Changing that flag alone is not a fix:
complete the context preflight and trace-retention tests, freeze the new package,
and obtain its exact-head review before launch. No model availability probe or
annotation session was performed. Actual served model identity remains unknown.
Native login presence does not establish model availability or complete isolation.

The candidate B is from the same Claude family as the key reviewer: no independent
reviewer/annotator relationship is claimed. A is from the designer's family too.
Provider/client context differs even with the same task; quantify only the
accepted bounded agreement measures, not a pure model effect.

The candidate runner claims slots once, requires an attributed prior audit before
the next invocation, keeps runtime failures distinct from format failures, and
has a fixed 180-second session limit. It is unfinished and intentionally gated.
Do not combine audit creation and launch in one tool-call chain. Do not delete
stale claims to retry after a crash. No results or policy activation are claimed.

## Offline checks

```sh
python3 experiments/rvb-bh-1a/validate_cards.py
python3 experiments/rvb-bh-1a/execution/test_score.py
```

`prepare.py` creates stimuli once and hashes the candidate package. It is not a
model launcher. `offline-check.json` retains test output and source hashes.
The [official Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
is a configuration source, not proof that our particular native invocation is isolated.
