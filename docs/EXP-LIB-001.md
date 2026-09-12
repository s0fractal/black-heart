# EXP-LIB-001 — First living-library experiment

Status: **proposed** (protocol for review; no run yet).
Target release: the first Black-Heart PDF whose whole verifiable history —
claim, application, counterexample, refinement — reduces to a **most-recent
confirmed ancestor**, without needing to know the globally newest state.

This document defines the components and acceptance criteria first. Which
residual defects block the release is decided in §7 from that basis, not the
other way round.

## 1. The loop

One epistemic edge-claim is carried through four phases, each an existing,
already-hardened library operation:

| phase | operation | module |
|---|---|---|
| **claim** | mint and sign an `EdgeClaim` with an evidence grade (G/A/E/C) | `warrant_kernel.EdgeClaim.create_and_sign` |
| **application** | audit it under a **caller-supplied** `TrustConfig` | `warrant_kernel.WarrantVerifier.audit_claim` |
| **counterexample** | a `COUNTEREXAMPLE` claim refuting the first, with structured witness operands | `warrant_kernel.CounterexampleWitness` |
| **refinement** | narrow or retire-and-readopt the claim, preserving the prior record | `controlled_forgetting.EpistemicTombstoneRegistry.retire` / `readopt` |

The point of the experiment is not that each phase works in isolation (each
has its own tests) but that the **four compose into one preserved history** an
independent party can replay to a confirmed ancestor.

## 2. Components and dependency set

The minimal loop imports only:

```
crypto, glyph, warrant_kernel, controlled_forgetting
```

`warrant_kernel` depends only on `crypto` and `glyph`; `controlled_forgetting`
on the standard library. Nothing in the loop imports `colony`, `sheaf_agora`,
`monad`, `ipfs_diary`, `vector_net`, or `vault`. This tight set is what makes
§7 answerable.

## 3. History preservation

- The record is **append-only**: each phase adds a signed entry; earlier bytes
  are never rewritten. Replaying the record from genesis must reconstruct every
  committed state exactly (the discipline S6a established for the
  morpho-autopoiesis chain, applied here to the claim record).
- Retirement does **not** delete: `retire` records a tombstone; `readopt`
  requires a verified re-adoption record bound to it. The refuted claim and its
  counterexample both remain in the history.
- "Confirmed ancestor" = the most recent entry whose signature, grade, and
  (for G/A) replay all check under a fixed caller trust root. The reader needs
  that ancestor and the entries after it, **not** the globally newest state.

## 4. Controls (each already enforced by a merged fix)

The experiment is only meaningful if the adversarial cases fail closed. Each
control below is a required assertion of the run, and cites the fix that makes
it hold:

- **Substitution — trust root.** A document that names its own author trusted,
  or declares trust-all, does not audit as verified; only the caller's trust
  root decides. (#30; persisted deny-all stays deny-all, #31.)
- **Substitution — author.** A claim signed by an author outside the caller's
  allowlist is `UNVERIFIED`, never `PASS`. (#30)
- **Substitution — recycled evidence.** A witness lifted from another claim
  does not verify against the claim it is attached to. (warrant witness binding;
  the transition-binding discipline of S6a.)
- **Non-termination.** A claim whose reduction does not settle within budget is
  `UNVERIFIED`, never `PASS`, and is never ratified, rewarded, or canonized in
  any consumer. (#32, #35)
- **Fail-closed audit.** "Could not verify" is never reported as success; a
  verdict is a positive confirmation. (#33)

## 5. Acceptance criteria

The experiment **passes** iff, run under a fixed caller `TrustConfig` and with
byte-level capture of the record before and after each phase:

1. **Honest loop completes.** The claim audits `PASS`; the counterexample
   audits `PASS` as a refutation; the refinement produces a new claim that
   audits `PASS`; every phase appends, none rewrites.
2. **History replays to the confirmed ancestor.** An independent reader,
   given only the record, reconstructs every committed state and identifies the
   most-recent confirmed ancestor without any external "latest state" input.
3. **Every control in §4 fails closed**, each as an explicit negative
   assertion with the adversarial input built from ephemeral throwaway keys.
4. **Mutation controls.** Each acceptance assertion is paired with a mutation
   that must kill it; documented mutual-redundancy survivors are named, not
   hidden.
5. **Determinism.** Two runs from the same seed produce byte-identical records
   (`SOURCE_DATE_EPOCH`-style fixed time), so the deposited artifact is
   reproducible.

A green aggregate alone is not acceptance: criteria 2–4 are the substance.

## 6. Deliverables

- `experiments/EXP-LIB-001/run.py` — the four-phase run, pre-registered
  predictions in a sibling `README.md` committed before the runner.
- `test_exp_lib_001.py` — the acceptance criteria as tests, registered in
  `test_all.py`.
- A mutation harness for the acceptance assertions (scratch, not committed).

## 7. Which residual defects block this release

From the six open scan findings (`e549de3`): `sheaf_agora` ballot weight,
`colony` ATP inflation, `monad` contract-hash closure, `ipfs_diary` field
boundary, `vector_net` layout DoS, `vault` preflight DoS.

**None sit on this experiment's dependency set (§2)**, so none blocks
EXP-LIB-001 on soundness grounds. They retain their separate triage. This is a
scoping claim about *this* release, not a judgement that they are harmless:
each remains open and must be reproduced-then-fixed before any release whose
path includes it.

The two findings that *would* block a claim-verification release — the warrant
document-trust policy and the grounded-suspension pass — are already fixed
(#30, #32) and are load-bearing controls here (§4).

## 8. Release gate

Zenodo deposit proceeds only after criteria 1–5 pass on a clean checkout and
the deposited PDF's history replays to its confirmed ancestor from the
deposited bytes alone. The DOI records that ancestor, not a promise about
future state.
