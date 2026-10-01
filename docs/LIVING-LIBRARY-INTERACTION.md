# Living library: proposals, decisions, and immutable PDF successors

Status: **LI-1–LI-3 implemented; local interaction over supported PDF profiles.**
Current implementation: [library_interaction.py](../library_interaction.py),
with CLI routing in [cli.py](../cli.py) and acceptance/regression tests in
[test_library_interaction.py](../test_library_interaction.py).

This page routes maintenance work. The original task brief and its acceptance
criteria remain in [the pre-consolidation revision](https://github.com/s0fractal/black-heart/blob/a0ca1ce22ae2395437d2a4d3e5efa96fd6d688e4/docs/LIVING-LIBRARY-INTERACTION.md).
That brief's “not implemented” and provisional CLI wording describe its original
stage, not the current implementation. The linked contracts own format details.

## LI-1 — proposal intake for one PDF profile (start here)

`inspect` reads the supported manifest as data; `add-claim` produces a signed
proposal bound to exact parent bytes and the supplied signed claim. Claim author
and proposer are separate identities. Intake neither evaluates evidence nor
admits a claim. See [LI-1: profiles, parsers, limits and refusals](LIBRARY-INTERACTION-LI1.md).

## LI-2 — evidence evaluation and an attributed admission decision

`evaluate` authenticates the proposal and evaluates its evidence through
`WarrantVerifier` under caller policy. The signed decision binds the proposal,
parent, policy and scoped evaluation. Evidence PASS and policy admission are
separate fields. No successor or reward is created.
See [LI-2: policy, evaluation and decision](LIBRARY-INTERACTION-LI2.md).

## LI-3 — immutable successor and a readable, replayable transition

`apply` checks the proposal, parent and decision bindings and **re-evaluates the
evidence under current caller policy**. A saved `admitted: true` is insufficient.
Admission produces a separate data-only successor PDF, preserving the parent's
claim records and adding exactly the proposed claim, plus a detached receipt.

`explain-transition` checks received artifacts and their exact change without
regenerating them or replaying the evidence. Its signature check does not establish
issuer authority unless the caller supplies an expected issuer key.
See [LI-3: receipt, publication order and recovery](LIBRARY-INTERACTION-LI3.md).

## Bindings and state semantics

- Input PDFs are read as data, never executed. Embedded trust configuration does
  not replace caller policy. Signed claim term addresses are not PDF byte hashes.
- A valid signature establishes key attribution, not human identity. Evidence
  verification, admission and authority to write remain separate checks.
- FAIL is a checked negative; UNVERIFIED is no verdict. A policy refusal is not a
  mathematical refutation. Neither failed nor unverified evaluation admits a claim.
- Parents remain byte-identical. A successor's address is computed after rendering;
  the receipt binds final bytes. Existing outputs are not silently overwritten.
- Multi-file publication is not an atomic transaction. Follow the LI-3 write-order
  and recovery contract; do not infer completion from a successor file alone.

## Completion and what stays out of scope

These operations provide a local proposal → decision → successor path. Tests cover
named refusals, substitutions, settlement and write failures; they do not establish
universal document truth, subjective agency or every possible failure interleaving.
No claim is made here that a CLI-driven transition is an autonomous document action.

Quorum, rewards, autonomous synthesis, executable self-modification and automatic
conflict resolution are outside LI-1–LI-3. Related proposals do not activate them.
Historical [EXP-LIB-001](EXP-LIB-001.md), [R2](EXP-LIB-001-R2.md), signatures and
recorded measurements remain unchanged. This consolidation closes no additional
[remediation-ledger](REMEDIATION-LEDGER.md) entries.

Related proposals: [conflict as an action prompt](CONFLICT-AS-ACTION-VECTOR.md)
and [Persona](../PERSONA.md).
