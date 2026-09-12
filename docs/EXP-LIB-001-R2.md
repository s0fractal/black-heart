# EXP-LIB-001 R2 — external-anchor profile

Status: **proposed** (profile for review; no R2 run yet). Revision 4. Companion to
`docs/EXP-LIB-001.md`. Defines what R2 is, before it is exercised. Until an
actual proof is verified, R2 is `NOT_DEMONSTRATED` and R3 is `NOT_RELEASED`.

R2 is one of three separate results (protocol §5): **R1** local replay (internal
consistency + verdict reproduction under a pinned trust root), **R2** external
anchor (existence-before-a-time of a chosen commitment against an independent
chain), **R3** publication (Zenodo DOI). R2 does not select or authenticate the
history — R1 with the pinned root does that — and R3 is not R2.

## 1. Commitment

R2 anchors the **root** (mandatory) and, for a release snapshot, the **tip**
(optional). The two are separate results with separate, narrow meanings:

- **root anchor** — the raw 32 bytes of the index-0 `event_hash` the reader
  pins. It confirms existence-before-a-time of the commitment of the *initial
  event only*. It does **not** date later events, and does **not** date any
  branches that grow from that root.
- **tip anchor** (optional) — the raw 32 bytes of the last event's
  `event_hash`. After the chain is replayed (R1), it can date the commitment of
  *this specific chain*. It does **not** prove global completeness of the
  library — only that this replayed chain's tip existed before a time.

The commitment is exactly those 32 bytes; §2 states precisely what the `.ots`
proof then commits to.

## 2. Proof and delivery

The proof is an OpenTimestamps detached `.ots` proof produced the **standard**
way: the commitment is written to a file of **exactly the 32 raw bytes** of the
event hash (`bytes.fromhex(...)`) — no hex text, no trailing newline — and
`ots stamp` SHA-256-hashes that file's content. So the detached proof commits
to `SHA256(the 32 root bytes)`; the leaf digest is that SHA-256, not the raw
bytes and not a hex re-encoding. (See the OTS client `stamp` path.) Tooling on
this host: `ots` v0.7.2, python `opentimestamps` 0.4.5; prior art
`.triad/continuity/ots_receipt_status.py`. Like the trust config, root and tip,
the `.ots` proof is delivered to the reader **separately** — it is not inside
the package bytes.

## 3. States (honest, and never assumed)

Following the offline, no-authority posture of the triad prior art — a Bitcoin
attestation *present* in a proof is **not** verified chain-time without a
Bitcoin header source:

| state | meaning |
|---|---|
| `NOT_DEMONSTRATED` | no proof supplied, or no OTS profile available |
| `REFUSED` | a proof was supplied but is malformed or does not bind the commitment — a distinct failure, never folded into `NOT_DEMONSTRATED` or `PENDING` |
| `PENDING` | the proof binds the commitment but carries only calendar commitments; no Bitcoin attestation yet |
| `ANCHORED_UNVERIFIED` | the proof carries a Bitcoin block attestation, but its chain time is **not** established against any accepted Bitcoin data source |
| `CONFIRMED` | the block attestation's Merkle root matches an accepted, reader-pinned **block header** at that height; the verified time is that header's timestamp |

**Default is `NOT_DEMONSTRATED`.** A proof is never assumed; a supplied proof
that does not bind the commitment is `REFUSED`, not absent; a present block
attestation is never reported as `CONFIRMED` without an accepted source.

## 4. Offline ceiling and authority

What makes the difference between `ANCHORED_UNVERIFIED` and `CONFIRMED` is an
**accepted Bitcoin data source**, not whether the network was touched.
`CONFIRMED` requires that the proof's block attestation be checked against a
Bitcoin data source the **reader** has accepted and pinned — which may be
block headers fetched earlier and independently pinned, and therefore verified
**offline**. Without an accepted source there is no confirmation: R2 is at most
`ANCHORED_UNVERIFIED`. The source, and how it is pinned, is the reader's
choice; it is **not** carried by the `.ots`. The accepted source is **block data**, not a bare Merkle-root string: the reader derives both the Merkle root and the block **time** from a pinned block header, so a `CONFIRMED` result carries an actual verified time (`attested_time`) and a derived `block_id`. A dictionary of Merkle-root hex alone carries no time and can never yield `CONFIRMED`. (Proof-of-work is not checked; accepting the header set is the reader's decision.) `network_calls` is reported as an
**observation**, never as the criterion of trust — a proof verified against a
pinned offline header set makes zero network calls and can still be
`CONFIRMED`, and a network call to an unaccepted server never earns it. The
report always states `time_verified`, `calendar_authenticity_verified`,
`accepted_source`, and `network_calls`.

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

The R2 reader is given `(commitment, ots_proof, accepted_source=None)`:

- `commitment` — the same pinned root R1 uses (its 32 raw bytes; §2);
- `ots_proof` — the detached `.ots` bytes (§2);
- `accepted_source` — **optional**, the reader's pinned Bitcoin data source
  (§4), a well-formed object
  `{"name": <non-empty str>, "block_headers": {<int height>: <80-byte header hex>}}`.
  The reader derives the Merkle root and block time from each pinned header; a
  bare `{height: merkle_root_hex}` map is **not** accepted (it carries no time).
  Its format is checked **before** any matching: a malformed source (missing
  name, or a value that is not exactly an 80-byte header) is **not used** —
  reported as `accepted_source: none` and never confirming. Without a usable
  source, `CONFIRMED` is **unreachable**: at most `ANCHORED_UNVERIFIED`.

It returns a structured result whose field names match §3/§4 exactly: `state`,
`commitment_sha256`, `proof_sha256`, `pending_calendars`,
`bitcoin_attestations` (each height + attested Merkle root, a 32-byte value),
`time_verified`, `attested_time` (the verified block time when `CONFIRMED`,
else `null`), `block_id` (derived from the pinned header when `CONFIRMED`, else
`null`), `calendar_authenticity_verified`, `accepted_source` (the name of the
well-formed source used, or `none`), and `network_calls`. A malformed or
non-binding proof is `REFUSED` (§3), returned as a named result, never an
exception (the same contract as the package reader). Supplying an
`accepted_source` is never by itself a confirmation: a Bitcoin attestation's
Merkle root must actually match a pinned header, which is also what yields the
reported time. `time_verified` is `true` only for `CONFIRMED`; no other state
reports a time.

## 8. Acceptance and the release gate

R2 **never gates R1**: R1 acceptance stands on its own. A release that **claims confirmed external time** requires `CONFIRMED`;
`ANCHORED_UNVERIFIED` is not sufficient for that claim. The specific Bitcoin
data source is **not chosen here** — it must be selected and pinned on the
reader side before such a release. Until R2 is actually run and verified it
stays `NOT_DEMONSTRATED`.

## 9. Deliverables (after this profile is accepted)

- An R2 reader in the experiment (offline by default), returning the §3 state
  and §4 flags; a named refusal for a malformed proof.
- Tests: `NOT_DEMONSTRATED` with no proof; `REFUSED` for a malformed or
  non-binding proof (distinct from absent/PENDING); `PENDING` and
  `ANCHORED_UNVERIFIED` from fixture proofs; the commitment file is exactly the
  32 raw bytes and equals the pinned root. `CONFIRMED` is exercised only against
  a well-formed, pinned block-header source whose Merkle root matches the
  attestation (asserting the derived `attested_time`), with the adjacent
  negatives -- same source but a mismatched header, a source missing its name,
  and the bare merkle-root-only shape -- all reaching at most
  `ANCHORED_UNVERIFIED`. It is otherwise reported, not asserted.
- R3 (Zenodo) remains out of scope until its own gate.
