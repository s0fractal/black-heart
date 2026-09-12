# EXP-LIB-001 — pre-registered predictions

Committed **before** `run.py`. The runner and `test_exp_lib_001.py` must match
this table exactly; any deviation is recorded as an amendment with its reason,
never edited away. Protocol: `docs/EXP-LIB-001.md` (rev 4). Combinators:
`I = 🤍`, `K = 🖤`, `S = 🌿`.

## The claim under study

An extensional equivalence "candidate ≡ reference", tested by applying both to
each input and comparing settled normal forms. Reference is `I` throughout.

## Event journal (exact, pre-registered)

Three events, indices `0,1,2`, continuous; each `prev_event_hash` equals the
previous `event_hash`; index 0 uses `"00"*32`.

| index | kind | candidate | inputs | expected_verdict | grade |
|---|---|---|---|---|---|
| 0 | CLAIM | `K I` | `I`, `I I`, `I (I I)` | PASS | EMPIRICAL (k=3) |
| 1 | COUNTEREXAMPLE | `K I` | `K` | PASS | COUNTEREXAMPLE |
| 2 | REFINE | `S K K` | `I`, `I I`, `I (I I)`, `K` | PASS | EMPIRICAL (k=4) |

## Preparatory measurement (not a result)

Measured on this checkout via `glyph.evaluate`, used only to choose the operands:

- `I a` and `K I a` both settle to `I` for `a ∈ {I, I I, I (I I)}`; equal.
- at `a = K`: `I K → K`, `K I K → I`, both **settled**, `K ≠ I`.
- `I a` and `S K K a` settle equal for `a ∈ {I, I I, I (I I), K}` (incl.
  `S K K K → K`).

## Predicted outcomes (acceptance)

1. **Honest loop:** verdicts recorded and reproduced are exactly C1 PASS,
   C2 PASS, C3 PASS. A reproduced `UNVERIFIED` would be a faithfully-recorded
   refusal, **not** loop success.
2. **Replay to oldest ancestor (R1):** from the package + pinned trust config +
   expected root hash (index 0) + expected tip hash (index 2), every event's
   hash chains, signature verifies, and `audit_claim` re-run reproduces the
   recorded verdict.
3. **Linkage:** C2 targets the same `(I, K I)` as C1 with witness `K ∉` C1
   fixtures; C3 keeps reference `I`, uses candidate `S K K ≠ K I`, on C1
   fixtures ∪ `{K}`.
4. **Controls fail closed:** foreign-author claim → `UNVERIFIED`; recycled
   witness → not `PASS`; non-terminating grounded claim → `UNVERIFIED`;
   tampered event → replay boundary at that index.
5. **Provenance separation:** R1 reported; R2 (OTS) reported or
   `NOT_DEMONSTRATED`; R3 (DOI) publication only.
6. **Determinism:** two runs from the same seed produce byte-identical journals.

## Keys

The keys in the run and tests are **deterministic public fixtures**, committed
for reproducibility. They must never sign a real release; a release is signed by
a key that is never committed.
