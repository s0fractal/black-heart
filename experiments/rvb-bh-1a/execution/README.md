# RVB-BH-1a execution package — REVIEW REQUIRED, NOT EXECUTED

PR #65 merged at b92cb87 (accepted e522d75), then PR #66 at e29419a
(accepted abe9dec). Accepted cards, plan, schedule, key and historical receipts
are unchanged. This package needs its own exact-head review before any model
session. No annotation, model availability call or result is claimed.

## Fixed inputs and annotators

Four stimuli contain the general rubric followed by the exact scheduled cards.
The general rule about `establishes/certifies` remains; the sentence naming S2,
R2, B1 and D2 is excluded. `test_no_card_identifiers_outside_cards` rejects all
eight card IDs before `CARDS` and compares the card bodies and order exactly.
`rubric.txt` is a separately frozen presentation excerpt, not a change to PLAN.
Neither the key nor reviewer comments are supplied to annotators.

- A: requested `claude-sonnet-5`, native Claude Code 2.1.270.
- B: requested `claude-opus-5`, native Claude Code 2.1.270.
- Both use the existing native Max login, medium effort, fresh nonpersistent
  sessions outside `~/Projects`, no tools, slash commands or MCP servers.
  The binary digest is pinned in `freeze.json`; a changed client blocks launch.

Both annotators are Anthropic/Claude. The key reviewer is reported by the owner
as Claude Opus 5, so B is from the reviewer's model and A from the same family.
A CANDIDATE_FOR_NEXT_PILOT result would establish only the planned agreement
within this family, not stability across providers. Shared model ancestry may
inflate the A1/B1 and A2/B2 comparisons.
The package designer is Codex/OpenAI. This is a comparison of two requested
models, not independent providers or an independent reviewer/annotator design.
Served model identity remains unknown until native runtime metadata is retained;
metadata is reported identity, not authentication. Unavailability stops the
study, with no replacement model. Native login presence does not prove availability.

The initial draft proposed Codex as A. Offline attempts found that the installed
Codex client still exposed builtin tools despite candidate feature settings
(one earlier attempt also failed configuration parsing). Before any annotation,
A was changed to Sonnet. The accepted plan leaves model assignment to this
package and requires different models, not different providers. The initial
candidate was never used for a study session. See `development-note.json`.

## Context boundary and what was actually checked

`runtime.py` supplies an allowlisted environment, including explicit
`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1`, and
`autoMemoryEnabled: false`. CLI settings sources are empty, with `--safe-mode`,
`--tools ''`, an empty strict MCP configuration and a fixed system prompt.
We do not infer isolation from these flags alone.

`context_probe.py` runs the actual installed client against a loopback HTTP stub.
The OS sandbox denies remote networking. The stub captures constructed request
bodies and returns a deliberate HTTP 400; it never forwards requests or generates
answers. Some invocations construct two requests; every captured request is
checked. HTTP errors here are expected offline refusals, not annotation results.

Retained `context/1.json` through `4.json` contain each exact stimulus, model,
system and message blocks and empty tool list. `context_check.py` accepts only
three fixed system blocks and the bounded native environment block, in addition
to the exact stimulus. Extra tools, messages, memory, prompt changes and model
changes are rejected by mutation tests. No reviewer key is sent. The billing
version suffix, working directory, platform, date and native model description
are visible context, not hidden from the reviewer.

A synthetic home contains canaries in user CLAUDE.md, project CLAUDE.md and
project memory. With hardening disabled, the marker appears in the captured
request and fails the checker. With hardening enabled it is absent. This is a
positive control for detecting injected context, not proof that every individual
memory source was loaded in the control. Real host memory is never edited.
The receipt also records an OS-denied connection to a numeric remote TCP
endpoint; successful local captures establish loopback access.

**Transport limit:** capture uses a dummy API key and a local endpoint. It does
not capture the native Max authorization path or establish that an authenticated
provider sees an identical request or no provider-side context. Request headers
are never retained; bodies retain only model/system/messages/tools plus the
whole-body digest and names of omitted noncontext fields. No credentials or
OAuth rewriting proxy are used. Before each study slot, the same prompt receives
a new local context check with the pinned client and flags; the native session
then runs separately. This is evidence of client construction under the capture
transport, not an in-flight audit of the later Max request. Review this limitation
before accepting the package. A preflight mismatch consumes the slot and stops
further sessions after its attributed audit.

## Retention, scoring and sequence

`events.py` retains native public JSONL incrementally, byte for byte unless a
recognized private reasoning block must be removed. Removed blocks and rewritten
lines are counted. Native stderr is retained. Public explanations are requested;
private reasoning is neither requested nor retained intentionally. Malformed
transport lines remain unparsed and require audit. The result string is written
unchanged to `response.txt`. The live trace must contain exactly one `system/init`. Its `tools`,
`mcp_servers`, `skills`, `slash_commands` and `plugins` must each be `[]`, and
`model` must equal the requested model. Its full field set and all other values
must match the init captured during that same slot's local preflight, except for
`cwd`, `session_id`, `uuid` and `apiKeySource`. Added, removed or changed fields
outside this allowance invalidate the slot. `init_count` and `init_errors` are
retained in the result. This directly checks the live client's reported surface;
it still does not establish transport equivalence or inspect provider-side context.
The probe's builtin `agents` list includes claude, Explore, general-purpose and
Plan; it is compared unchanged. With no tools they are not callable by the
annotator. The operator should explicitly note this surface in the audit.

Tool events, client errors, unexpected event types, absent assistant model
metadata and changed observed model metadata invalidate the run. Timeout is a
format failure only if the required init and assistant model were observed and
no infrastructure violation occurred; otherwise the missing evidence makes it
an infrastructure failure. Partial output is retained. No repair, continuation or silent retry.

`score.py` implements the accepted priority and four comparisons. Tests cover
exact output schema, duplicate JSON keys/IDs, missing IDs, thresholds, critical
overclaims, infrastructure failure, byte preservation, hidden-block removal,
tool calls, client failure, partial lines, timeout and audit hash binding.

Each command claims exactly one slot before preflight, and allows 180 seconds
for the native session. The operator must inspect context, invocation, public
events, stderr, response and result, then separately write `audit.json`:

```json
{
  "reviewer": "actual reviewer identity or reported designation",
  "audited_at": "actual ISO-8601 UTC timestamp after the result",
  "valid": true,
  "evidence": "concrete findings from the retained files",
  "hashes": {
    "result.json": "sha256",
    "public-events.jsonl": "sha256",
    "response.txt": "sha256 or null when absent",
    "context.json": "sha256 or null when absent"
  }
}
```

The next invocation requires this audit and matching hashes. A false audit or
invalid infrastructure stops with remaining slots NOT_RUN. Format failures stay
in the four-session result. Audit creation and launch are separate operator
steps, never one command chain. After the fourth audit, the same command writes
the final decision without invoking another client.

Only after acceptance of the exact package head:

```sh
python3 experiments/rvb-bh-1a/execution/run_slot.py --reviewed-head FULL_ACCEPTED_COMMIT
```

Outputs live under `~/rvb-bh-1a-runs/rvb-bh-1a-20260914-v2/`. A stale
`runner.claim` after SIGKILL must not be deleted to resume silently: preserve it,
record the interrupted slot as infrastructure failure with an attributed audit,
and review that incident before any operator recovery. Never repeat a slot.

## Offline verification

```sh
python3 experiments/rvb-bh-1a/validate_cards.py
python3 -m unittest discover -s experiments/rvb-bh-1a/execution -p 'test_*.py' -v
python3 experiments/rvb-bh-1a/execution/verify_package.py
```

To repeat native context construction on the pinned macOS client, without model
inference (choose a new output directory; existing outputs are refused):

```sh
python3 experiments/rvb-bh-1a/execution/offline.py ~/rvb-bh-1a-work/new-context-review
```

New captures are observations, not byte-identical receipts: directory names,
request metadata and dates vary. Keep them separate from retained `context/`.
`context/receipt.json` binds retained captures and historical source files on
`3e42c3f00eefd22706faef46196855122bb97dbc`; the verifier resolves those sources
through Git rather than pretending the old capture ran with the amended runner.
The capture bytes and `offline-v2.json` remain unchanged. `offline-v3.json`
records validation of the amended runner and live-init mutation tests. `offline-check.json` is the unchanged initial
six-test draft receipt. `prepare.py` deterministically rebuilds the prompts and
hashes the package before the first session; it refuses once the run directory
exists. `launch_ready: true` denotes an implemented runner, not review acceptance
or authorization to skip the review gate.
