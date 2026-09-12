# EXP-LIB-001 — First living-library experiment

Status: **proposed** (protocol for review; no runner yet). Revision 3.

Goal: the first Black-Heart PDF whose verifiable history — claim, application,
counterexample, refinement — replays from its **oldest reachable confirmed
ancestor** using only the deposited bytes plus a separately-pinned trust
configuration, with provenance and publication kept as separate, separately-
checked results.

Components and acceptance criteria are defined first (§1–§6); which residual
defects block the release is decided from that basis (§8).

## 1. The loop, with measured operands

The claim is an **extensional equivalence** between a reference combinator and
a candidate: for each input `a`, compare the settled normal form of
`reference a` against `candidate a`. Every reduction below SETTLES — the
counterexample is a genuine value mismatch, not a divergence.

Operands were chosen by a **preparatory measurement** (not an experiment
result), run through `glyph.evaluate` on this checkout:

| stage | operands | measured outcome |
|---|---|---|
| **C1** (EMPIRICAL) | reference `I`, candidate `K I`; inputs `I`, `I I`, `I (I I)` | on every input both sides settle to `I`; equal → PASS **on these inputs only** |
| **C2** (COUNTEREXAMPLE) | same pair, input `K` | reference `I K` → `K`; candidate `K I K` → `I`; both settled; `K ≠ I` → confirmed refutation |
| **C3** (EMPIRICAL) | reference `I`, **corrected** candidate `S K K`; inputs above **plus** `K` | on every input both settle equal (incl. `K`: `S K K K` → `K`) → PASS on the extended set |

`I t = t` is a correct reduction, so a non-terminating `t` is **not** a
counterexample to it; non-termination appears only as a control (§4), never as
the refutation mechanism. C2 refutes the **universal generalization** "`K I`
behaves as `I`", which is false; C1's bounded result on its three inputs stays
correct. C3 is a genuine **candidate fix** (`S K K ≡ I`), not C1 with `K`
excluded — excluding `K` would change nothing, since `K` was never in C1's
fixtures.

| phase | operation | expected verdict | establishes | does NOT establish |
|---|---|---|---|---|
| claim | audit C1 | `PASS` (EMPIRICAL, k=3) | C1 holds on its 3 inputs | that `K I` ≡ `I` in general |
| application | replay re-audits C1's content | same `PASS`, byte-identical | the record reproduces C1 | anything about C2/C3 |
| counterexample | audit C2 | `PASS` (refutation) | `K I` ≢ `I` (witness `K`) | that C1's bounded result is wrong |
| refinement | audit C3 | `PASS` (EMPIRICAL, k=4) | `S K K` ≡ `I` on the 4 inputs | that recording the succession proved C3 |

`controlled_forgetting.retire`/`readopt` may express the C1→C3 succession as
intent, but they do not audit C3 and are not the history (§3).

## 2. Components and dependency set

The executed loop imports only:

```
crypto, glyph, warrant_kernel, controlled_forgetting
```

plus the experiment's own event journal (§3). `warrant_kernel` and
`controlled_forgetting` both depend only on `crypto` and `glyph` (not stdlib
alone — corrected from rev 2), so the four-module set is closed under imports
and does not widen. Controls (§4) are scoped to exactly the operations this set
executes.

## 3. History: an explicit append-only signed event journal

`controlled_forgetting`'s registry is a **mutable keyed store**, not a journal:
`retire` overwrites the slot for a target and deletes any prior readoption
(`controlled_forgetting.py:753,756`). It is unfit as the history of record, so
the experiment defines its own journal — without rewriting the library.

### 3.1 Event encoding (profile `black-heart.exp-lib-001.event.v1`)

Each event is a JSON object with these named fields, and no others, in the
signed/hashed core:

```
{ "profile":          "black-heart.exp-lib-001.event.v1",
  "index":            <int, 0-based>,
  "prev_event_hash":  <64 lowercase hex; "00"*32 for index 0>,
  "kind":             "CLAIM" | "COUNTEREXAMPLE" | "REFINE",
  "claim":            <EdgeClaim.to_dict()>,
  "expected_verdict": "PASS" | "FAIL" | "UNVERIFIED",
  "author_pk_hex":    <64 hex> }
```

- **Canonical core bytes** = `canonical_jcs(core)` — the existing RFC 8785 JCS
  serializer at `controlled_forgetting.py:78`, UTF-8 output — over exactly the
  fields above. `event_hash` and `signature_hex` are **excluded** from the core
  (an object cannot hash or sign its own hash/signature).
- `event_hash = sha256(canonical core bytes)`, lowercase hex.
- `signature_hex` = Ed25519 over the **same** canonical core bytes, by
  `author_pk_hex`.
- The stored event is the core plus `event_hash` and `signature_hex`.

### 3.2 Replay rules

Given the journal, walk from the tip via `prev_event_hash` to index 0 (the
**oldest reachable ancestor**). For every event:

1. recompute `event_hash` from the core and require it equals the stored one;
2. require `prev_event_hash` equals the predecessor's `event_hash`
   (`"00"*32` at index 0);
3. verify `signature_hex` over the canonical core bytes by `author_pk_hex`;
4. **re-audit the content**: run `WarrantVerifier(caller_trust).audit_claim(
   EdgeClaim.from_dict(event["claim"]))` and require its status equals
   `expected_verdict`. This applies to **every** claim-bearing event —
   `CLAIM`, `COUNTEREXAMPLE`, and `REFINE` — so a signed `COUNTEREXAMPLE` or
   `REFINE` is a re-verified result, never an unchecked declaration.

The **oldest reachable confirmed ancestor** is index 0 when the whole chain
confirms; if a prefix fails, the confirmed region is the contiguous run from
index 0 to the first failure, and that boundary is a **reported result**, not a
silent truncation.

## 4. Controls (scoped to executed operations)

Each is a required negative assertion; adversarial input is built from
ephemeral throwaway keys; each cites the merged fix that makes the executed
path hold:

- **Substitution — caller trust root.** `WarrantVerifier` is built with the
  **caller's** `TrustConfig`; a claim whose author is outside the caller
  allowlist re-audits `UNVERIFIED`, never `PASS`, and no trust root is ever read
  from a claim payload. (Library counterpart of #30; deny-all persists, #31.)
- **Substitution — recycled witness.** A witness/operands lifted from another
  claim do not re-audit `PASS` against the claim they are attached to
  (claim-id / witness binding).
- **Non-termination.** A claim whose grounded reduction does not settle within
  budget re-audits `UNVERIFIED`, never `PASS`. (#32) — a control, not C2.
- **History tamper.** Editing any core field, re-pointing a `prev_event_hash`,
  dropping an interior event, or swapping a claim's `expected_verdict` breaks
  replay at that point and is reported as the confirmed-region boundary (§3.2).

**Note (scope).** This run does not execute the `cli.py` audit gate (#30), the
`tools/sandbox.py` auditor (#33), or swarm ratification/reward (#35); those are
sibling consumers hardened and tested elsewhere. No control here claims
anything about them; there is no "not rewarded in any consumer" claim, which
this dependency set cannot reach.

## 5. Provenance and publication — three separate results

A signature inside the package proves who signed a payload, not when the
package existed or that it descends from an independent anchor:

- **R1 — local replay.** The journal replays from index 0 under the pinned
  caller trust root and re-audits every claim (§3.2). Establishes internal
  consistency and verdict reproduction; establishes **no** external time or
  origin.
- **R2 — external anchor.** An OTS/Bitcoin timestamp over a chosen commitment
  (index-0 `event_hash`, and/or the tip). Establishes existence-before-a-time
  of that commitment against an external chain, independent of the package's
  own signatures. It does **not** by itself select *which* history is ours —
  R1 with the pinned root does that. (Ties to WRT-012 / the OTS prior art in
  `.triad`; the external half is a separate proof, not implied by R1.)
- **R3 — publication.** The Zenodo DOI records where the bytes were published.
  It is **not** provenance and does not stand in for R1 or R2.

## 6. Acceptance criteria

Run under a **pinned** caller `TrustConfig`, fixed time (`SOURCE_DATE_EPOCH`),
byte-level capture before and after each phase. The independent reader's input
is **the package plus the separately-pinned trust config, an expected root
hash, and an expected tip hash** — the root identifies *this* history, the tip
attests the claimed snapshot is complete; neither is the globally-newest state.
Passes iff:

1. **Honest loop.** C1 `PASS` (k=3); C2 `PASS` (refutation); C3 `PASS` (k=4);
   every phase appends, none edits.
2. **Replay to oldest ancestor (R1).** From the package + pinned trust config,
   the reader confirms the chain to index 0, matches the expected root and tip,
   and re-audits every claim's content to its recorded verdict.
3. **Controls fail closed.** Every §4 control holds as an explicit negative.
4. **Provenance separation.** R1, R2, R3 are reported as three distinct
   results; absence or failure of R2 never passes as R1, and R3 is never
   treated as either.
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
deposited PDF's journal replays to index 0 from the deposited bytes plus the
pinned trust config (R1), matching the expected root and tip. R2, if
demonstrated, is recorded alongside as a distinct proof. The deposit attests
the oldest confirmed ancestor and the replay, not a promise about future state.
