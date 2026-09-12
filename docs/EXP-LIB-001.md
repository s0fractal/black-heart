# EXP-LIB-001 — First living-library experiment

Status: **proposed** (protocol for review; no run yet). Revision 2.

Goal: the first Black-Heart PDF whose verifiable history — claim, application,
counterexample, refinement — replays from its **oldest reachable confirmed
ancestor** using only the deposited bytes, with provenance and publication kept
as separate, separately-checked results.

Components and acceptance criteria are defined first (§1–§6). Which residual
defects block the release is decided from that basis (§8), not the reverse.

## 1. The loop, with concrete operands

One empirical claim is carried through four phases. Concrete operands are fixed
now so a green sequence cannot later be mistaken for the claimed cause.

- **Fixtures** `X = { I x, I y, I z }` (three closed terms), each with its
  settled normal form under `glyph.evaluate`.
- **Claim C1 (EMPIRICAL).** "`I t == t` for every t" — asserted, and tested,
  only on `X`. This is a *bounded* result with an explicit non-universal
  caveat, which the grade's own badge already prints.
- **Counterexample C2 (COUNTEREXAMPLE).** A witness `y* ∉ X` on which the
  *universal generalization of C1* fails — e.g. a term where the naive rule
  C1 might be over-read to apply but the reduction diverges. C2 refutes the
  generalization, **not** C1's bounded empirical result, which remains correct.
- **Refinement C3.** C1 narrowed to a stated domain that excludes `y*` (or an
  AXIOMATIC restatement carrying a real derivation). C3 is a *new* claim and
  must be audited on its own; the succession from C1 to C3 is recorded, but the
  recording does not establish C3.

| phase | operation | input | expected verdict | establishes | does NOT establish |
|---|---|---|---|---|---|
| claim | `WarrantVerifier.audit_claim(C1)` | C1 (EMPIRICAL, fixtures X) | `PASS` (EMPIRICAL, k=3) | C1 holds on X | that C1 is universal |
| application | replay C1 from the journal under the caller trust root | C1 | same `PASS`, byte-identical | the record reproduces C1's verdict | anything about C2/C3 |
| counterexample | `audit_claim(C2)` | C2 (COUNTEREXAMPLE at y*) | `PASS` (refutation confirmed) | the *generalization* of C1 is false | that C1's bounded result is wrong |
| refinement | `audit_claim(C3)` | C3 (narrowed / axiomatic) | `PASS` | C3 holds as stated | that `readopt` alone proved C3 |

`controlled_forgetting.retire`/`readopt` express the C1→C3 succession as
intent; they are **not** the history (see §3) and do not substitute for
`audit_claim(C3)`.

## 2. Components and dependency set

The executed loop imports only:

```
crypto, glyph, warrant_kernel, controlled_forgetting
```

plus the experiment's own append-only journal (§3). `warrant_kernel` depends
only on `crypto` and `glyph`; `controlled_forgetting` on the standard library.
The controls in §4 are scoped to exactly these executed operations — no claim
is made about consumers the loop does not run (§4 note).

## 3. History: an explicit append-only event journal

`controlled_forgetting`'s registry is a **mutable keyed store**, not a journal:
`retire` replaces the slot for a target and deletes any prior readoption
(`controlled_forgetting.py:753,756`). It is therefore unfit as the history of
record. The experiment defines its own journal instead — no library rewrite.

- The journal is an ordered list of **immutable signed events**
  `e0, e1, …, en`. Each event:
  `{ index, prev_event_hash, kind ∈ {CLAIM, APPLY, COUNTEREXAMPLE, REFINE},
     payload, author_pk_hex, signature_hex }`.
- `event_hash = sha256(canonical_jcs(index | prev_event_hash | kind | payload
  | author_pk_hex))`; `e0.prev_event_hash = "00"*32`.
- **Append-only:** a new event only ever extends the tip; no event is edited or
  removed. A retire/readoption is itself recorded as an event, so the refuted
  claim, the counterexample, and the refinement all remain.
- **Replay rules:** starting from the tip, walk `prev_event_hash` to `e0`
  (the oldest reachable ancestor); for each event verify (a) the hash chains
  to its predecessor, (b) the author signature, and (c) for APPLY events,
  re-run `audit_claim` under the **fixed caller trust root** and require the
  recorded verdict. The **oldest reachable confirmed ancestor** is `e0` when
  the whole chain confirms; if a prefix fails, the confirmed region is the
  contiguous run from `e0` up to the first failure, and that boundary is a
  reported result, not a silent truncation.

## 4. Controls (scoped to executed operations)

Each is a required negative assertion, adversarial input built from ephemeral
throwaway keys, and cites the merged fix that makes the executed path hold:

- **Substitution — caller trust root.** `WarrantVerifier` is constructed with
  the **caller's** `TrustConfig`; a claim whose author is outside the caller's
  allowlist is `UNVERIFIED`, never `PASS`, and the journal never carries the
  trust root from inside a claim payload. (Library counterpart of #30; deny-all
  persists as deny-all, #31.)
- **Substitution — recycled witness.** A witness lifted from another claim does
  not verify against the claim it is attached to (claim-id / witness binding).
- **Non-termination.** A claim whose grounded reduction does not settle within
  budget is `UNVERIFIED`, never `PASS`. (#32)
- **History tamper.** Editing any event payload, re-pointing a
  `prev_event_hash`, or dropping an interior event breaks replay at that point
  and is reported as the confirmed-region boundary (§3).

**Note (scope).** This run does **not** execute the `cli.py` audit gate (#30),
the `tools/sandbox.py` auditor (#33), or swarm ratification/reward (#35); those
are sibling consumers hardened and tested elsewhere. No control here claims
anything about them — in particular there is **no** "not rewarded in any
consumer" claim, which this dependency set cannot reach.

## 5. Provenance and publication — three separate results

A signature inside the package proves who signed a payload, not when the
package existed or that it descends from an independent anchor. These are kept
distinct and reported separately:

- **R1 — local replay.** The journal replays from `e0` under the fixed caller
  trust root (§3). Establishes internal consistency and verdict reproduction.
  Self-contained; establishes **no** external time or origin.
- **R2 — external anchor.** An OTS/Bitcoin timestamp over `e0.event_hash`
  (and/or the tip). Establishes existence-before-a-time against an external
  chain, independent of the package's own signatures. (Ties to WRT-012 /
  the OTS prior art in `.triad`; the external half is a separate proof, not
  implied by R1.)
- **R3 — publication.** The Zenodo DOI records where the bytes were published.
  It is **not** provenance and does not stand in for R1 or R2.

## 6. Acceptance criteria

Run under a fixed caller `TrustConfig`, fixed time (`SOURCE_DATE_EPOCH`), with
byte-level capture before and after each phase. Passes iff:

1. **Honest loop.** C1 `PASS` (EMPIRICAL, k=3); C2 `PASS` (refutation of the
   generalization); C3 `PASS` on its own audit; every phase appends, none edits.
2. **Replay to oldest ancestor (R1).** An independent reader, given only the
   journal, walks to `e0`, confirms every event, and reproduces every APPLY
   verdict — with no external "latest state" input.
3. **Controls fail closed.** Every §4 control holds as an explicit negative.
4. **Provenance separation.** R1, R2, R3 are reported as three distinct
   results; a failure or absence of R2 does not silently pass as R1, and R3 is
   never treated as either.
5. **Mutation controls.** Each acceptance assertion is paired with a mutation
   that must kill it; documented mutual-redundancy survivors are named.
6. **Determinism.** Two runs from the same seed produce byte-identical journals.

A green sequence alone is not acceptance: criteria 2–5 are the substance.

## 7. Deliverables (after this protocol is accepted)

- `experiments/EXP-LIB-001/run.py`, with pre-registered predictions in a
  sibling `README.md` committed before the runner.
- `test_exp_lib_001.py` (acceptance criteria as tests), registered in
  `test_all.py`.
- A mutation harness for the acceptance assertions (scratch, not committed).
- R2 is exercised only if an OTS profile is available; otherwise it is reported
  `NOT_DEMONSTRATED`, never assumed.

## 8. Which residual defects block this release

The six open scan findings (`e549de3`) — `sheaf_agora` ballot weight, `colony`
ATP inflation, `monad` contract-hash closure, `ipfs_diary` field boundary,
`vector_net` layout DoS, `vault` preflight DoS — are **tentatively off the core
loop** (§2). Final exclusion is deferred until the **full run path and the
package-verification path are fixed and measured**: if implementing §7 pulls in
any module beyond §2 (for example, whatever renders the deposited PDF), that
module's open findings become in-scope and must be reproduced-then-fixed first.
This is a scoping claim about *this* release, not a judgement that any finding
is harmless.

The two findings that would block a claim-verification release — the
document-trust policy and the grounded-suspension pass — are already fixed
(#30, #32) and are load-bearing here (§4).

## 9. Release gate

Zenodo (R3) proceeds only after criteria 1–6 pass on a clean checkout and the
deposited PDF's journal replays to `e0` from the deposited bytes alone (R1).
R2, if demonstrated, is recorded alongside as a distinct proof. The deposit
attests the oldest confirmed ancestor and the replay, not a promise about
future state.
