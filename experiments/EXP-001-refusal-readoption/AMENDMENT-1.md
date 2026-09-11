# EXP-001 — amendment 1

Dated 2026-09-11. Written after the first recorded run (`result.json`, runner at
`4e1c195`) and after review round 1 of PR #15. `README.md` and `result.json` are
left exactly as they were committed. Nothing below was pre-registered.

## Correction to the registration: where S6 starts

The registration's table gives S6's document outcome as "unchanged from after
S5". The prose under the table says S6 runs on a fork taken **before** S5, where
the refuted pair is still the next replacement.

The first recorded run implemented the prose. S6 ran on a fork copied from the
main document immediately before S5. Its starting bytes were the main
document's pre-S5 bytes, which equal the genesis bytes because every earlier
step on the main document was refused. The table cell is an error in the
registration. The correct reading is "unchanged from its own start, the main
document immediately before S5".

This is now a checked protocol field. Each step records where it starts from.
The amended runner requires S5 and S6 to start from identical bytes, and S1 to
S4 to start from the genesis document.

## What the first recorded run did and did not establish

Review round 1 replaced only the S5 registry file with an empty registry and
ran the unmodified sequence through the real CLI. S5 still evolved, S6 was
still refused, and all six predictions stayed green. The record still named a
readoption id, because the first runner took ids from the objects in memory and
digests from the files on disk.

So the six outcomes in `result.json` stand as observed. Its attribution does
not. The claim that the readoption is what let S5 through was not checked by
that runner. It cannot be checked now either: the registry files were in a
temporary directory and are gone. Their digests in `result.json` identify bytes
nobody can produce, so those digests are **not** recoverable evidence. The
attribution in `result.json` is an unverified summary.

## Checks added by this amendment

These are reported as `attribution_mismatches`, separately from the registered
predictions. A run holds only if both are empty.

- Every id and digest in the record is read from the bytes the CLI consumed,
  captured right before each step.
- S2's registry holds only the refutation, and that refutation addresses the
  pair under test.
- S3's registry holds only the other-reference refutation, and S4 consumes
  exactly those bytes.
- S5's registry keeps the S2 retirement unchanged and adds exactly one
  readoption, for the refuted subject, valid and linked to that retirement.
- S6 consumes exactly the S2 registry.
- S5 and S6 start from identical document bytes.

`test_exp001.py` runs three controls that must fail attribution: an empty S5
registry, which is review round 1's mutant and leaves the outcome table green; a
different retirement in S5 with a readoption linked to it; and a readoption
linked to another retirement. The honest sequence must pass.

Two checks cannot be reached by replacing an input file. S2 and S6 read the
same path, and the runner copies the forks itself, so no file tamper makes S6
read other bytes or makes S5 and S6 start apart. The mutation controls showed
this: removing either check killed nothing. `test_exp001.py` now exercises both
directly on the recorded inputs, with the honest inputs as the positive case.

## Evidence bundle

The successor run keeps the three consumed registry files in `evidence-a1/`.
They hold public keys and signatures only. Their digests and record ids match
`result-a1.json`, and the test checks that readback. The organism documents
are not kept; their per-step digests are in the record.

## Disposition

- `result.json`: outcomes observed; attribution unverified, and unverifiable now.
- `result-a1.json`: recorded under this amendment, on a clean tree, with the
  consumed registries kept.
