# LI-3 — immutable successor and a readable transition

Contract date: 2026-09-13. Status: **implemented; LI-3 format and write-order
specification.** Brief:
[LIVING-LIBRARY-INTERACTION.md](LIVING-LIBRARY-INTERACTION.md) (§ "LI-3").
Builds on [LI-1](LIBRARY-INTERACTION-LI1.md) and
[LI-2](LIBRARY-INTERACTION-LI2.md). Source inspected: `8ae60c4`.

## 0. The governing rule

**A saved `admitted: true` authorises nothing by itself.** `apply` re-verifies
the proposal, re-checks the parent's exact bytes, and **re-runs the evaluation
under the caller's current policy** at the point of use. The stored decision is
a report that is *also* checked; it is never the reason a successor exists.

## 1. Why a new renderer, measured not assumed

The brief says to inspect the chosen renderer before reuse and to prefer a
data-only output. Measured on a real `generate_warrant_ledger_pdf` artifact:

| property | existing parent profile | LI-3 successor profile |
|---|---|---|
| first bytes | a Python shebang; `%PDF` only at offset **300** | `%PDF-1.7` at offset 0 |
| `startxref` target | **wrong** — points 300 bytes early, into the prologue text | correct |
| every xref object offset | **wrong** by the same 300 bytes | correct |
| embedded self-auditor | yes, a Python runner that reads the document's own trust config | **none** |

So LI-3 does **not** reuse `generate_warrant_ledger_pdf`. It has its own
renderer that emits a data-only PDF. That renderer is new code in this PR, not a
change to `warrant_kernel`; the existing engine is left alone.

The successor carries the **same manifest line format** as the parent, so the
LI-1 reader parses it unchanged and **a successor can itself be the parent of
the next proposal** — verified on the prototype. The loop composes.

## 2. Artifacts

`apply` produces exactly two files:

1. **The successor PDF** — data-only, no executable code, carrying the parent's
   claims plus exactly the proposed one, and a visible instruction to verify
   with the host CLI rather than by running the document.
2. **A detached transition receipt** (`black-heart.library-interaction.transition.v1`)
   binding, inside a signed body: `parent_pdf_sha256`, `successor_pdf_sha256`,
   `proposal_id`, `decision_id`, `policy_sha256`, `added_claim_id`, and
   `issuer_pk_hex`.

The successor's byte address is derived **after** rendering. No whole-file hash
is ever embedded into the file it hashes; that is what the detached receipt is
for. The receipt's authorised issuer is **not** self-declared: a verifier
supplies `--expect-issuer-pk`, exactly as LI-2's decider is not self-authorising.

**The parent file is never written to.** It is opened read-only and its bytes
are re-checked before and at the point of use.

## 3. Write order, and what each crash point leaves behind

Two files are **not** a transaction, and nothing here claims one. The order is
chosen so that every interruption leaves a state a reader can *name*:

```
1. render successor bytes in memory
2. create   <successor>.partial      (exclusive create; refuses if present)
3. derive   successor_pdf_sha256 from the bytes actually written
4. create   <receipt>.partial        (exclusive create; refuses if present)
5. publish  <successor>.partial  ->  <successor>     (no-clobber)
6. publish  <receipt>.partial    ->  <receipt>       (no-clobber)  <-- completion
```

**Publication must refuse at the filesystem level, for both targets.**
`os.rename` *silently replaces* its destination, so checking `os.path.exists`
first is a TOCTOU window rather than a guarantee: a file created in between is
destroyed. Publication therefore hard-links the staging name onto the target —
`os.link` fails with `FileExistsError` when the target exists — and only then
removes the staging name. The earlier existence checks remain as an early,
precise error message; they are **not** the protection.

**The receipt is the completion marker, and it is published last.** Therefore:

| interrupted after step | on disk | how a reader names it |
|---|---|---|
| 1–4 | only `*.partial` files | **PREPARED** — nothing was published; no transition happened |
| 5 | successor published, no receipt | **INCOMPLETE** — a prepared artifact, *not* a completed transition |
| 6 | both published | **COMPLETE** |

A successor without a receipt is never reported as a transition. This is
**not rollback**: a published successor is left in place, and LI-3 deletes
nothing.

**Publication and cleanup are separate outcomes.** Each publish step is a
hard link followed by removal of the staging name. The link is the publication:
once it succeeds the final name exists, and nothing that follows undoes it.
Removing the staging name is only cleanup — if that fails, a leftover staging
name remains, but the publication **stands**, and `apply` carries on to the next
step rather than reporting a publication that did not happen.

The result therefore reports state **derived from facts**, never from which
step raised:

| field | meaning |
|---|---|
| `transition_state` | `COMPLETE` (both final names created by this run), `INCOMPLETE` (successor only), or `NOT_PUBLISHED` |
| `published_paths` | final names **this run's** link created — a file already at a target is not reported as ours |
| `leftover_staging_paths` | staging names observed on disk after the run |
| `cleanup_complete` | `false` when any leftover remains |

A transition can be `COMPLETE` with `cleanup_complete: false`: both artifacts are
published and verifiable, and a leftover staging name must be removed before
that output path is reused. Leftovers are named, never deleted automatically. Calling a reordered write sequence "atomic" would be false, so the
specification states the opposite explicitly.

Leftover `.partial` files are **never** reused or silently overwritten: a
second run refuses with `STAGING_EXISTS` so an operator inspects and removes
them deliberately.

## 4. Repeating an application

Repetition must not add a second claim and must not overwrite another output:

- `<successor>` or `<receipt>` already existing is a named refusal
  (`OUTPUT_EXISTS`, `RECEIPT_EXISTS`); neither is overwritten.
- If the parent **already contains** the proposed claim, `apply` refuses with
  `CLAIM_ALREADY_PRESENT` — so retrying against an already-updated parent
  cannot double-add.
- The parent digest and policy are re-checked **at the point of use**, so an
  intervening change to either is caught rather than assumed away
  (`PARENT_PIN_MISMATCH`, or a fresh non-admitting evaluation).

Two different proposals against the same parent legitimately produce **two
different children**. That is not a conflict, no election of a "newest state"
occurs, and neither child invalidates the other.

## 5. `explain-transition`

Given the exact parent, successor, proposal, decision and receipt plus the
caller's pins, a **fresh** verifier confirms, without regenerating anything:

- the parent bytes hash to the receipt's `parent_pdf_sha256`;
- the successor bytes hash to its `successor_pdf_sha256`;
- the receipt verifies under an issuer the **caller** pinned;
- the decision and proposal are the ones the receipt names;
- **every claim record of the parent is still present in the successor, and
  exactly one record was added, and it is the proposal's authenticated claim.**
  Records are compared **in full and with multiplicity**, never by identifier: a
  record that keeps its `claim_id` while its body is replaced is not preserved,
  a bare `{"claim_id": ...}` stub is not the claim, and a record appearing twice
  does not collapse into one.

Altering any artifact is detected for the property it purports to establish.
Regeneration is a *separate* result and is never required for verification — the
same separation the frozen R2 package uses.

Inspection reports grade and scope, and distinguishes **admitted** claims from
**merely proposed** ones. It never labels the whole document universally true: a
successor containing an admitted Grade-G claim asserts that one bounded
reduction was replayed under one policy, nothing more.

## 6. CLI

```
python3 cli.py library apply --pdf <parent> --proposal <p> --decision <d>
                            --policy <pol> --issuer-key-file <k>
                            --out <successor.pdf> --receipt <r.json>
python3 cli.py library explain-transition --parent <p.pdf> --successor <s.pdf>
                            --proposal <p> --decision <d> --receipt <r>
                            --expect-issuer-pk <hex> [--policy <pol>]
```

Exit `0` success, `2` named refusal, `1` unexpected error. Every input is left
byte-identical by any refusal.

**A refusal does not always mean nothing was published.** That claim was wrong
and is withdrawn: publication is two steps, and a failure at the second one
leaves the successor published with no receipt — the `INCOMPLETE` state of §3,
which the refusal message names explicitly. A refusal *before* the first
publication step publishes nothing; a refusal *at or after* it leaves the
successor in place, because nothing here rolls back.

## 7. Out of scope

No ATP, reward, promotion, deletion of contradicting claims, or reinterpretation
of any existing claim's scope. No network, no publication, no stamping.
Counterexample and refinement operations remain later slices.
