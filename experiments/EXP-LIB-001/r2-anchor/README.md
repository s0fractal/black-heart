# EXP-LIB-001 — frozen R2 anchoring package

This directory freezes, **offline**, the exact reproduction package for the R2
external anchor (profile: `docs/EXP-LIB-001-R2.md`). It is frozen **before**
any `ots stamp` so the thing stamped is fixed and reviewable, and so the journal
is **not regenerated** between the freeze and the stamp.

## Files

| file | what it is |
|---|---|
| `journal.pkg` | the saved journal bytes the R1 reader confirms (deterministic) |
| `root.commitment` | **exactly the 32 raw bytes** of the root `event_hash` — the file to stamp |
| `MANIFEST.json` | `source_commit`, `package_sha256`, full `root`/`tip`, leaf `SHA256(commitment)`, and the posture |
| `verify_anchor_package.py` | offline verifier (no network, no OTS) — reproduces the bytes and checks every invariant |

Frozen values (see `MANIFEST.json` for the authoritative copy):

- source commit: `148eec969ed5b1fa546c2be2ad93e4cdf83957a1`
- root  (stamp commitment): `2b921b388a132f6ce0457f70015fa610cad1e797941c74a0967a014d72d93121`
- tip: `78db18f1b73719c8c7ea3fc9932e3c8fe44d0e32c71fcadef99edb9b6ff5b4ee`
- `package_sha256`: `b08c11b6a03e36d1493d056c9565dbc351268f6905406a9cf030a7e4c5cfff09`
- leaf the `.ots` will commit to (`SHA256` of the 32 bytes): `e71305f6ad4b3827d33d9f5651509fc2a7a1fd16fea630d47c2bca7cb987a6bf`

Verify offline:

```bash
python3 experiments/EXP-LIB-001/r2-anchor/verify_anchor_package.py
```

## Boundary (what a stamp of this would and would not mean)

This is **experiment history signed with PUBLIC FIXTURE keys**
(`AUTHOR_SK = bytes([1] * 32)`). A timestamp over `root.commitment` attests
**existence-before-a-time of the commitment only** — **not** the owner's
authorship, and **not** the authenticity of any future release. R2 is not R1
(authorship, checked by signature) and not R3 (publication).

## The stamp step (deliberate; not run here)

The public `ots stamp` is an outward, irreversible action and is **not executed
by this package**. When run, stamp exactly `root.commitment` (do not regenerate
the journal):

```bash
ots stamp experiments/EXP-LIB-001/r2-anchor/root.commitment
# -> writes root.commitment.ots (the detached proof), kept alongside as evidence
```

The reader is then `run.verify_external_anchor(commitment, ots_proof,
accepted_source)`. Immediately after stamping the result is expected `PENDING`
(calendar commitments only) until a Bitcoin attestation appears.

## Bitcoin header source (named, unresolved dependency)

`CONFIRMED` requires an independently accepted, reader-pinned Bitcoin header
source (profile rev 5 §4/§7): the reader derives the Merkle root **and** the
block time from a pinned 80-byte header.

- **Preferred:** the owner's own synced Bitcoin Core.
- **If external instead:** the exact headers used and the method of obtaining
  them must be saved here and this dependency named explicitly.

Until a real `.ots` proof is verified against such a source, **R2 is
`NOT_DEMONSTRATED` and R3 is `NOT_RELEASED`.**
