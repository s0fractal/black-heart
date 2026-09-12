# EXP-LIB-001 R2 — external-anchor profile

Status: **proposed** (profile for review; no R2 run yet). Companion to
`docs/EXP-LIB-001.md`. Defines what R2 is, before it is exercised. Until an
actual proof is verified, R2 is `NOT_DEMONSTRATED` and R3 is `NOT_RELEASED`.

R2 is one of three separate results (protocol §5): **R1** local replay (internal
consistency + verdict reproduction under a pinned trust root), **R2** external
anchor (existence-before-a-time of a chosen commitment against an independent
chain), **R3** publication (Zenodo DOI). R2 does not select or authenticate the
history — R1 with the pinned root does that — and R3 is not R2.

## 1. Commitment

R2 anchors the **root**: the raw 32 bytes `bytes.fromhex(root_event_hash)`,
where `root_event_hash` is the index-0 `event_hash` the independent reader
already pins (protocol §6). Anchoring the root ties external time to *this*
selected history. A second, independent anchor over the **tip** may attest the
claimed snapshot's completeness; it is optional and reported separately.

The commitment is exactly those 32 bytes — not the package file, not a
re-hash. Timestamping the raw root bytes keeps R2 verifiable from the same
value R1 already checks.

## 2. Proof and delivery

The proof is an OpenTimestamps `.ots` proof over the commitment (tooling on
this host: `ots` v0.7.2, python `opentimestamps` 0.4.5; prior art
`.triad/continuity/ots_receipt_status.py`). Like the trust config, root and
tip, the `.ots` proof is delivered to the reader **separately** — it is not
inside the package bytes.

## 3. States (honest, and never assumed)

Following the offline, no-authority posture of the triad prior art — a Bitcoin
attestation *present* in a proof is **not** verified chain-time without a
Bitcoin header source:

| state | meaning |
|---|---|
| `NOT_DEMONSTRATED` | no proof, or no OTS profile available |
| `PENDING` | proof carries only calendar commitments; no Bitcoin attestation yet |
| `ANCHORED_UNVERIFIED` | proof carries a Bitcoin block attestation, but chain time is **not** verified offline (no node/header authority) |
| `CONFIRMED` | the block attestation is verified against Bitcoin via a **named** header authority |

**Default is `NOT_DEMONSTRATED`.** A proof is never assumed; a present block
attestation is never reported as `CONFIRMED` without a named authority.

## 4. Offline ceiling and authority

Verified **offline** (no network, `authority: none`), R2 reaches at most
`ANCHORED_UNVERIFIED`: the proof binds the commitment and contains an
attestation, but the attestation's Bitcoin time is not established. `CONFIRMED`
requires a named Bitcoin header authority (a full node, or a pinned header
set) and a network call, both **declared** in the result (`authority`,
`network_calls`), never silent. The report always states `time_verified`,
`calendar_authenticity_verified`, `network_calls`, and `authority`.

## 5. What R2 is not

- Not provenance of authorship (that is a signature, checked in R1).
- Not selection of the history (that is the pinned root in R1).
- Not R3: a DOI records publication, not existence-before-time.
- A present-but-unverified attestation is not confirmed time.

## 6. Determinism

Unlike R1, R2 proofs are **not** byte-reproducible: they depend on calendar
servers and Bitcoin, so two `ots stamp` runs produce different `.ots` bytes.
R2 is therefore **exempt** from the R1 determinism criterion. Only the
**commitment** (the root hash) is deterministic; the proof over it is not.

## 7. Reader inputs and reported result

The R2 reader is given `(commitment, ots_proof)` — the commitment being the
same pinned root R1 uses — and returns a structured result: the state (§3),
the commitment and proof digests, any pending calendars, any Bitcoin
attestations (height + attested Merkle root), and the explicit
`time_verified` / `authority` / `network_calls` flags. A malformed or
non-binding proof is a named refusal, not an exception (the same contract as
the package reader).

## 8. Acceptance and the release gate

R2 **never gates R1**: R1 acceptance stands on its own. Whether the release
(R3, protocol §9) requires a particular R2 state — e.g. at least
`ANCHORED_UNVERIFIED`, or `CONFIRMED` under a named authority — is a release
decision to be fixed when R3 is planned, not part of R1 acceptance and not
decided here. Until R2 is actually run and verified, it stays
`NOT_DEMONSTRATED`.

## 9. Deliverables (after this profile is accepted)

- An R2 reader in the experiment (offline by default), returning the §3 state
  and §4 flags; a named refusal for a malformed proof.
- Tests: `NOT_DEMONSTRATED` with no proof; `PENDING` and `ANCHORED_UNVERIFIED`
  from fixture proofs; a malformed proof refused by name; the commitment equals
  the pinned root. `CONFIRMED` is exercised only under a named authority and is
  otherwise reported, not asserted.
- R3 (Zenodo) remains out of scope until its own gate.
