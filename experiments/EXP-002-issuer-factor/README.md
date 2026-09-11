# EXP-002 — the issuer as the one declared factor

Pre-registered before any run. Committed alone, ahead of the runner; `git log`
on this directory shows the order.

## Question

EXP-001 established, on the one live registry-aware consumer, that a refutation
refuses a replacement and a readoption lets it through. PR #16 added an issuer
policy, and the consequence table in `docs/TRUSTED-ISSUERS.md` says the same
signed assertion should have different consequences depending only on who
signed it. This experiment checks that on the real CLI, over one document,
changing only the signing key.

## What is held fixed and what varies

Held fixed across every step: the pair (derived by evolving a fork of a fresh
organism, as in EXP-001), the input `x`, the starting document, the label, and
one issuer policy file `P`. `P` lists exactly one key, `T`, for both
retirements and readoptions.

The one factor: which key signed. `T` is trusted by `P`. `F` is not.

`R_T` and `R_F` carry the same retirement assertion. They are built with a fixed
timestamp so their bodies are identical except for the author field. Their
signatures and record ids necessarily differ.

## Registries

| name | contents |
|---|---|
| `R_T` | the retirement, signed by `T` |
| `R_F` | the same retirement, signed by `F` |
| `R_T+F` | `R_T` plus a readoption of it, signed by `F` |
| `R_T+T` | `R_T` plus a readoption of it, signed by `T` |

## Sequence and predictions

"Unchanged" means byte-identical by SHA-256. Every policy-bearing step consumes
the same `P` bytes.

| step | starts from | registry | policy | extra flags | exit | scope | document |
|---|---|---|---|---|---|---|---|
| S1 | fork of genesis | none | none | none | 0 | — | changes |
| S2 | main | `R_T` | `P` | none | 1 | `REFUTED_FOR_REFERENCE` | unchanged |
| S3 | main | `R_F` | `P` | none | 1 | `UNAUTHORIZED_ISSUER` | unchanged |
| S4 | fork of main after S3 | `R_F` | `P` | `--also-proceed-on UNAUTHORIZED_ISSUER` | 0 | — | changes |
| S5 | main | `R_T+F` | `P` | none | 1 | `REFUTED_FOR_REFERENCE` | unchanged |
| S6 | fork of main before S7 | `R_F` | none | none | 1 | `REFUTED_FOR_REFERENCE` | unchanged |
| S7 | main | `R_T+T` | `P` | none | 0 | — | changes, generation 1 |
| S8 | fork of main before S7 | `R_T` | `P` | none | 1 | `REFUTED_FOR_REFERENCE` | unchanged |

Also predicted for every refused step: the sidecar key unchanged, the CLI
saying the organism was not modified, and no traceback.

## What each comparison isolates

- **S2 against S3**: the only difference is the signing key. The consequence
  moves from prohibition to uncertainty.
- **S3 against S6**: the same `R_F` bytes, with and without `P`. Without a
  policy the foreign record prohibits, as before PR #16. So `P` is what changed
  S3.
- **S3 against S4**: the uncertainty can be opted past explicitly, and only
  explicitly.
- **S5**: the review asked for this case on its own. A foreign readoption of a
  trusted retirement is present and authentic, and it lifts nothing.
- **S7 against S8**: a trusted readoption is what lets S7 through. S8 runs on a
  fork taken before S7, with the retirement and no readoption.

## Attribution, checked on the consumed bytes

Carried over from EXP-001 amendment 1, and registered here from the start:
every id and digest comes from the registry and policy bytes the CLI consumed,
captured right before each step. A run holds only if the registered
predictions AND these checks hold:

- `P` lists exactly `T` in both roles, and `F` in neither; every
  policy-bearing step consumed the same `P` bytes; S6 consumed no policy.
- `R_T` holds only the retirement, by `T`, addressing the pair. `R_F` holds
  only the retirement, by `F`, with a body equal to `R_T`'s except the author.
- S4 and S6 consume exactly the S3 bytes; S8 consumes exactly the S2 bytes.
- S5 keeps the S2 retirement unchanged and adds exactly one readoption,
  authentic, linked to it, by `F`; the library, reading those consumed bytes
  under the consumed `P`, reports `REFUTED_FOR_REFERENCE` with that readoption
  ignored.
- S7 keeps the S2 retirement unchanged and adds exactly one readoption,
  authentic, linked to it, by `T`.
- S1 to S5 start from the genesis document; S6 and S8 start from the same bytes
  as S7.

## Controls that must fail

Each replaces a real input file handed to the real CLI. Where the outcome table
stays green, only the attribution checks can catch it, which is the point.

- **Absent evidence at S7**: an empty registry. S7 still evolves.
- **Accidentally permissive policy**: `P` also trusts a third key for
  readoptions, and S7's readoption is signed by that key. Every outcome stays
  as predicted.
- **Absent foreign readoption at S5**: `R_T` alone. S5 still refuses.
- **A different assertion at S3**: `F` signs a retirement of the pair with a
  different input. S3 is still `UNAUTHORIZED_ISSUER`.

## What would falsify the claim

S3 reported as `REFUTED_FOR_REFERENCE`, or S6 as anything else. S5 evolving.
S4 refused. S7 refused, or S8 evolving. Any refused step changing the document.
Any control passing.

## What this does not show

- That the refutation is true. As in EXP-001, the pair is a sound rewrite and
  the records are signed assertions.
- Where `P` comes from, who maintains it, or how keys rotate or are revoked.
- That `F` could put its record into this registry in the first place. The
  caller chose the registry. The halting risk of the refusal default applies
  once a foreign record is in the chosen registry, not from key possession.
- Anything about the embedded runner, which passes no registry.
- Digest reproducibility across runs. Keys are ephemeral and receipts carry
  timestamps; the outcomes reproduce, the digests are evidence of one run.

## Running it

```bash
python3 -B experiments/EXP-002-issuer-factor/run.py --out result.json --evidence evidence
```

The evidence directory receives the consumed registry and policy files, which
hold public keys and signatures only.
