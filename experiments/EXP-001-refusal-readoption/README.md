# EXP-001 — refusal, readoption, evolution

Pre-registered before the first run. The predictions below were committed on
their own, ahead of `result.json`; `git log` on this directory shows the order.

## Question

PR #14 gave one live consumer, `cli.py autopoiesis evolve --tombstones FILE`,
a scoped refutation check with a caller policy. Its tests check each case in
isolation. This experiment checks that the same document moves through a
realistic sequence of registries and ends where the policy says it should:
refused while a refutation stands, still refused when the evidence concerns
another reference, and evolved once the refutation is readopted.

## Roles

- **Issuer**: writes the registry files with the library API. It signs one
  refutation record and later one readoption of it, each with an ephemeral key.
- **Consumer**: the real CLI, run as a subprocess against one organism document.
  Every admission decision in this experiment is made by the consumer.

## Pair under test

The pair is the replacement evolution really makes on a fresh organism. It is
derived by evolving a copy of the document, not hard-coded. On a fresh
organism this is `S(K x)(K y) -> K(x y)` on one gene. That is a sound rewrite,
so no genuine counterexample to it exists. The refutation record is therefore a
**signed assertion** about that pair. This experiment measures how the consumer
treats an authentic record. It does not measure whether the issuer was right.

## Sequence and predictions

`D0` is the document right after genesis. "Unchanged" means byte-identical,
compared by SHA-256 digest.

| step | registry | CLI flags | predicted exit | predicted scope in output | predicted document |
|---|---|---|---|---|---|
| S1 | none | none | 0 | — | changes (on a **fork**, to learn the pair) |
| S2 | `R_same`: refutation of (reference, candidate) | `--tombstones` | 1 | `REFUTED_FOR_REFERENCE` | unchanged, `D0` |
| S3 | `R_other`: refutation of (another reference, candidate) | `--tombstones` | 1 | `REFUTED_FOR_ANOTHER_REFERENCE` | unchanged, `D0` |
| S4 | `R_other` | `--tombstones --also-proceed-on REFUTED_FOR_ANOTHER_REFERENCE` | 0 | — | changes (on a **fork**) |
| S5 | `R_same` with its readoption added | `--tombstones` | 0 | — | changes, generation 1 |
| S6 | `R_same` again, without the readoption | `--tombstones` | 1 | `REFUTED_FOR_REFERENCE` | unchanged from after S5 |

S6 is the control that the readoption, not the passage of time or the first
success, is what let S5 through. By S6 the main document is at generation 1,
and its next replacement is a different pair, so S6 needs its own
prediction. It runs against a **fork taken before S5**, where the refuted pair
is still the next replacement. Its prediction is the same as S2.

Also predicted, in every refused step: the sidecar key file is unchanged, and
the refusal says the organism was not modified.

## What would falsify the claim

Any refused step that changes the document. S5 not evolving. S6 evolving.
S3 reported as `REFUTED_FOR_REFERENCE`, which would mean uncertainty is being
presented as refutation. S4 refused, which would mean the explicit policy is
ignored.

## What this does not show

- That the refutation is true. See "Pair under test".
- That the issuer was entitled to sign it. Issuer trust is not decided anywhere
  in this path.
- That the registry is complete or fresh. An absent record is read as absent.
- Anything about the embedded runner, which passes no registry.
- Digest reproducibility across runs. Keys are ephemeral and receipts carry
  timestamps, so digests differ every run. The outcomes are what reproduce; the
  digests in `result.json` are evidence about that one run.

## Running it

```bash
python3 -B experiments/EXP-001-refusal-readoption/run.py --out result.json
```

It works in a temporary directory, prints a table, and writes the record. It
never writes a secret key into the record. `test_exp001.py` runs it and checks
every prediction, so CI keeps it reproducible.
