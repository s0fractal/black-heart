# EXP-LIB-002 — one document's history through two transitions

A small end-to-end experiment of the living library, adding **no mechanism**: it
drives the existing `python3 cli.py library …` commands and records what they
produce for one document across **P0 → P1 → P2**.

| | commit |
|---|---|
| predictions, committed and pushed first | `70d9ab4` — [PREDICTIONS.md](PREDICTIONS.md) |
| runner, committed before the recorded run | `2b94e05` — [run.py](run.py) |
| code under test | `main` at `8fed8bb` (LI-1, LI-2, LI-3) |

## Result

**All 17 pre-registered predictions were confirmed; none was refuted.**

| group | predictions | outcome |
|---|---|---|
| H — honest history | H1–H9 | 9/9 confirmed |
| N — negative controls | N1a, N1b, N2, N3, N4 | 5/5 refused under exactly the predicted name |
| R — reproducibility | R1–R3 | 3/3 confirmed |

The history itself: T1 added C1 to P0 (1 → 2 claims) and T2 added C2 to P1
(2 → 3); both transitions verify as `COMPLETE` **without regeneration**; P0 and
P1 stayed byte-identical; every whole claim record of P0 is present in P1 and P2,
and every record of P1 in P2.

| control | what was presented | refused as |
|---|---|---|
| N1a / N1b | T1's receipt as T2's, and T2's as T1's | `RECEIPT_PARENT_MISMATCH` |
| N2 | P2 with C0 — inherited **from P0**, two generations back — modified, id kept | `RECEIPT_SUCCESSOR_MISMATCH` |
| N3 | the same P2 with a receipt **re-issued by the genuine issuer key** | `PARENT_CLAIMS_DROPPED` |
| N4 | T2 with its receipt missing | `RECEIPT_UNREADABLE` |

N2 and N3 are the informative pair: with the receipt's digest layer removed by a
genuine re-signature, the whole-record history still catches a change to a claim
inherited two transitions earlier.

### Reproducibility, and a finding

- **R1** outcomes are identical across `PYTHONHASHSEED` values.
- **R2** with a fixed `PYTHONHASHSEED`, all 12 saved artifacts are byte-identical
  across two runs on the same host.
- **R3** across seeds 0–5 the P0 digest is **not** stable (5 distinct values).

The stated cause of R3 was then checked separately, not just assumed
([R3_MECHANISM.json](R3_MECHANISM.json)): P0's bytes outside the manifest are
identical for every seed, and the manifests become identical once
`trust_config.admitted_grades` is sorted. Distinct orders (5) equal distinct
digests (5); seeds 3 and 5 happened to produce the same order.

**Finding:** `TrustConfig.to_dict` serialises `admitted_grades` from a *set*, so
a ledger PDF's bytes depend on the process's string-hash seed. Byte-reproducing
these documents therefore requires fixing `PYTHONHASHSEED`. This experiment only
records the property; changing the serialisation would alter future document
bytes and belongs in its own reviewed change.

**Not claimed:** byte identity across hosts. P0 begins with a shebang naming the
host interpreter, so digests are host-specific. The saved run still **verifies**
on any host, because verification never regenerates.

## Reproduce from the exact commit

```bash
git checkout <commit containing this README>
PYTHONHASHSEED=0 python3 experiments/EXP-LIB-002/run.py --out /tmp/exp-lib-002
python3 experiments/EXP-LIB-002/run.py --reproducibility --out /tmp/exp-lib-002-r
python3 experiments/EXP-LIB-002/run.py --verify-saved experiments/EXP-LIB-002/run
```

The first command re-runs the history and reports each H and N prediction; on the
same host with the same seed it reproduces the saved bytes. The last command
checks the **saved** history here — recorded digests and both transitions — with
the successor renderer made to raise, so nothing is regenerated.

## What the saved run contains

`run/` holds the honest history only: `P0.pdf`, `P1.pdf`, `P2.pdf`, `policy.json`,
and for each of `T1/`, `T2/` the `claim.json`, `proposal.json`, `decision.json`
and `receipt.json`, plus `RESULT.json` with observed values and digests. Forged
control artifacts were built in a scratch directory and are not kept. No secret
key material is stored: the four roles use deterministic **public fixture keys**
that exist only for reproducibility.

## Scope

Public fixture keys attest nothing about any real person. A `COMPLETE` transition
asserts that one bounded Grade-G check passed under one caller policy and that the
history was preserved — not that any document is true. No network, publication or
OTS stamping; R2/R3 of EXP-LIB-001 remain unchanged.
