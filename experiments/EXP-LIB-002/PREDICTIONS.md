# EXP-LIB-002 — pre-registered predictions

Committed and pushed **before** the runner exists and before any part of this
experiment was run. Do not edit after the run: a wrong prediction is recorded as
wrong in the results, and a deviation from this protocol is written as
"deviation, because…", never as compliance.

Code under test: `main` at `8fed8bb` (LI-1, LI-2, LI-3 merged). This experiment
adds **no mechanism**: it drives the existing `python3 cli.py library …`
commands as subprocesses and records what they produce.

## What is being run

One document's history through two sequential transitions, **P0 → P1 → P2**:

| step | parent | proposed claim | expected successor |
|---|---|---|---|
| T1 | P0 (a real `generate_warrant_ledger_pdf` ledger holding C0) | C1: grounded `🤍 🤍` | P1 |
| T2 | P1 (the LI-3 successor, used as the next parent) | C2: grounded `🤍 (🤍 🤍)` | P2 |

Each step runs the real CLI: `add-claim` → `evaluate` → `apply`; each transition
is then checked with `explain-transition`. Every proposal, decision and receipt is
saved. All keys are **deterministic public fixture keys**, one per role (claim
author, proposer, decider, receipt issuer); they attest nothing about any real
person, and a timestamp or release of these artifacts would not either.

Predictions below were derived by **reading source**, not by running: the check
order in `explain_transition`, `crypto.sign_bytes` (RFC 8032, deterministic), and
`TrustConfig.to_dict` (serialises `admitted_grades` from a **set**).

## H — the history, when everything is honest

| id | prediction |
|---|---|
| H1 | T1 `evaluate`: `evaluation_status` = `pass`, `admitted` = true. `apply`: exit 0, `transition_state` = `COMPLETE`, `cleanup_complete` = true, claims 1 → 2. |
| H2 | T2 `evaluate`: `pass`, admitted. `apply`: exit 0, `COMPLETE`, `cleanup_complete` = true, claims 2 → 3. |
| H3 | `explain-transition` T1: exit 0, `COMPLETE`, `claims_preserved` = 1, `claims_after` = 2, `regenerated` = false. |
| H4 | `explain-transition` T2: exit 0, `COMPLETE`, `claims_preserved` = 2, `claims_after` = 3, `regenerated` = false. |
| H5 | P0 and P1 are byte-identical at the end of the run to their digests recorded when each was created (a parent is never written to). |
| H6 | History inclusion by **whole records** (canonical, with multiplicity): every claim record of P0 is present in P1 and in P2; every record of P1 is present in P2. |
| H7 | `library inspect --pdf P2` reports `claim_count` = 3 and format `WARRANT-0.2`. |
| H8 | For each evaluated claim, the recorded `atp_spent` is measured (`atp_spent_measured` = true) and equals the counter of an independent `glyph.evaluate` of the same term and budget. |
| H9 | Verifying both transitions with the successor renderer made to raise still yields `COMPLETE` — verification does not regenerate. |

## N — negative controls (each must be refused, and by exactly this name)

Derived from the check order in `explain_transition`: read parent → read
successor → read receipt → verify receipt → receipt/parent digest → receipt/
successor digest → proposal → decision → whole-record history.

| id | construction | predicted refusal |
|---|---|---|
| N1a | T1's receipt presented as T2's (parent P1, successor P2, T2 proposal and decision) | `RECEIPT_PARENT_MISMATCH` |
| N1b | T2's receipt presented as T1's | `RECEIPT_PARENT_MISMATCH` |
| N2 | P2 re-rendered with C0 — the claim inherited **from P0**, two generations back — given a changed body and its original `claim_id`; the genuine T2 receipt is kept | `RECEIPT_SUCCESSOR_MISMATCH` |
| N3 | the same modified P2, with a receipt **re-issued by the genuine fixture issuer key** for the new bytes | `PARENT_CLAIMS_DROPPED` |
| N4 | T2 explained with its receipt missing | `RECEIPT_UNREADABLE` |

N2 and N3 are deliberately paired: N2 shows the receipt digest catching the
change; N3 removes that layer (a genuine signature over the modified bytes) and
shows the whole-record history catching it on its own.

## R — reproducibility (supports the reproduction instructions)

| id | prediction |
|---|---|
| R1 | Outcomes — every H and N result above — are identical across repeated runs, whatever `PYTHONHASHSEED` is. |
| R2 | With `PYTHONHASHSEED` fixed to the same value on the same host, **every saved artifact is byte-identical** across two runs (P0, P1, P2, both proposals, decisions and receipts). |
| R3 | With `PYTHONHASHSEED` ∈ {0, 1, 2, 3, 4, 5}, the P0 digests are **not all equal**. Reason from source: `TrustConfig.to_dict` lists `admitted_grades` from a set of `str` enum members, whose iteration order follows the per-process string hash. |

**Not claimed:** byte identity across hosts. P0 begins with a shebang naming the
host's interpreter path, and P1/P2 embed a prefix of their parent's digest, so
their bytes are expected to be host-specific. Saved artifacts should still
**verify** on any host, because verification never regenerates.

## What would falsify this

Any H or R row observed otherwise; any N control accepted, or refused under a
different name; a parent's bytes changing; a transition verifying only when its
successor is regenerated.
