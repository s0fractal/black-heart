---
title: "A PDF That Runs Its Own Checks: What It Verifies, What It Does Not, and Two Bounded Records from Black-Heart"
author: "Serhii Glova (ORCID 0009-0001-8010-420X)"
date: 2026-09-14
license: "Paper CC BY-SA 4.0; the companion polyglot contains executable code under AGPL-3.0-only"
---

## Abstract

Black-Heart builds files that are at once PDF documents and Python programs: run
`python3 -I companion.pdf` and an embedded, standard-library runner reduces the
combinator claims written into the file's comments. We report three claims and keep
each at the strength of its evidence. (1) **Mechanism, measured.** A one-page
companion built with the repository's existing `PolyglotDocument` rebuilds
byte-identically, embeds no host path, and settles its three claims under the
runner, `cli.py verify` and the static sandbox. Six controls on copies bound what
this means: an edited expected value and a non-terminating claim fail; an
appended tautological claim, an edited visible title and a neighbouring shadow
module under plain `python3` do not fail. The runner nevertheless prints
"100% SOUND". (2) **A defect class, reported and regression-tested.** Treating a
budget-suspended reduction as a finished result was found in four consumers and
repaired; the 20 regression tests that pin the repair pass at the measured commit.
(3) **One transfer record, reported.** A fresh session of a different provider's
model executed a sender-designed differential and rejected synthetic early-return
advice (baseline 3/3, advice 2/3); a later three-arm pilot showed no advantage of
the evidence packet. Nothing here is peer-reviewed, and the anchor — trust in the
runner inside the same file — is stated, not removed.

## 1. What this paper is

This is a short experience report about one repository, `s0fractal/black-heart`,
measured at commit `1981386` (code identical to `origin/main` `62e3e80` plus the
measurement script). It makes exactly three claims. Each carries an evidence class:

| # | Claim | Evidence class |
|---|---|---|
| 1 | What a self-running PDF companion checks, and what it does not | **executed** here: `measurements/measurements.json` |
| 2 | "Suspended taken as settled" occurred in several consumers and is repaired | **reported** in the remediation ledger; its regression tests **executed** here |
| 3 | One receiver session rejected false advice after running a given check | **reported** records; their byte correspondence **executed** here |

The earlier idea for this paper was a document that "verifies its own tree rings":
incremental PDF updates, seals and a sandbox forming one self-checking artifact.
Reading the code at the measured commit did not support that claim. The pieces
exist separately — an append path that preserves earlier bytes, signed receipts,
a static auditor — but no verifier binds them into one check of a multi-page
document, and the ring verifier that exists reads only the last manifest. We
therefore do not claim it (§2.4).

## 2. Claim 1 — the companion polyglot

### 2.1 Construction

`polyglot.PolyglotDocument.compile` writes a file that begins with
`# coding: utf-8` and a Python raw string opener, so the PDF header sits at byte 20
and the whole PDF body is a string literal. After the PDF trailer the string closes
and a standard-library runner follows. Claims are PDF comment lines of the form
`%<U+1F5A4> CLAIM: id=… | expr=… | expected=… | max_atp=… | desc=…`, where
`<U+1F5A4>` is the black-heart emoji character. The runner scans the
file for such lines, reduces `expr` with its own S/K/I/Y engine under the stated
budget, reduces `expected`, and compares the rendered normal forms. A budget overrun
raises and counts as a failed claim; all claims settling equal exits 0.

The companion (`measurements/companion.pdf`, 8,627 bytes, sha256
`b7a8bab2…f2f278`) carries three claims: `S K K x → x`, `K I a b → b`,
`S f g x → f x (g x)`. `pdfinfo` reads it as a one-page A4 PDF 1.7.

### 2.2 What was measured

| Check | Result |
|---|---|
| Two builds from the same script | byte-identical |
| Host home or repository path in the file | absent |
| `python3 -I companion.pdf` | exit 0, 3/3 settled, 5 reduction steps |
| `python3 cli.py verify companion.pdf` | exit 0, "local checks passed for the reported scope" |
| `python3 cli.py sandbox companion.pdf` | exit 0, SOUND; scope "0 signature(s) and 3 claim(s) … NOT the whole document" |

### 2.3 Controls: the boundary of "checks itself"

Each control modifies a copy and runs it with `python3 -I` unless stated.

| Control | Exit | Reading |
|---|---|---|
| First claim's expected value changed to `y` | 1 | a changed claim is detected |
| Non-terminating claim `S I I (S I I)` appended in a Python comment | 1 | budget overrun fails closed |
| Tautological claim `a → a` appended in a Python comment | 0 | reports 4/4 and "100% SOUND": appended claims are not authenticated |
| Visible title changed, same byte length | 0 | the rendered text is not bound to the claims |
| `hashlib.py` placed next to the file, run with plain `python3` | 7 | the neighbouring module executed first |
| The same, with `python3 -I` | 0 | isolation mode did not import it |

So the runner verifies one predicate: *the reductions written in this file's claim
lines settle to the normal forms written next to them, under the runner's own
engine.* It does not verify who wrote a claim, whether a claim is substantive,
whether the page says what the claims say, or whether bytes were appended. Its
closing line, "Document integrity & proof verification: 100% SOUND", is wider than
that predicate. The runner also has no isolation gate: `-I` is the reader's duty.

### 2.4 The anchor, stated

A reader who runs the companion trusts the runner code carried in the same file,
the Python interpreter, and the statement in this paper that the runner is the one
`polyglot.py` generates. Nothing inside the file removes that trust. The static
sandbox is the repository's non-executing alternative, and it has its own record:
the remediation ledger lists "hermetic sandbox auditor reports SOUND without
verifying anything" (found by an independent security scan of `e549de3`), repaired
so that SOUND now requires at least one positively verified element and zero
failures, with an explicit "NOT the whole document" scope. Its SOUND on the
companion means three claims, nothing more.

Incremental updates exist elsewhere: `morpho_net.grow_ontogenetic_quine_in_pdf`
appends a revision in place and keeps the file runnable. Its audit checks a receipt
chain but reads only the last manifest, takes the public key from the receipt
itself, passes unsigned rings as "UNATTESTED", and its runner falls back to a fixed
local checkout path to import its engine. None of that is part of the companion, and
"a document that verifies its own history" is not a claim of this paper.

## 3. Claim 2 — "suspended" taken as "settled"

Black-Heart's evaluator returns `SUSPENDED` when a reduction exhausts its budget,
with the intermediate term. Four consumers compared that intermediate term as if it
were a result. The remediation ledger (`docs/REMEDIATION-LEDGER.md`) records each,
with its reproduction and repair:

| Consumer | How it was found | Consequence before repair | Disposition |
|---|---|---|---|
| Warrant verifier, Grade G (grounded) | independent security scan of `e549de3`, reproduced | a non-terminating term with its hash pinned to the suspended intermediate audited PASS | BEHAVIOR_FIXED (`b386a23`) |
| polyglot claim auditor | same scan, reproduced | a non-terminating claim with expected = expression verified at the maximum budget | BEHAVIOR_FIXED (`8f199b0`) |
| swarm vote and settlement | same scan, reproduced end to end | the same proposal was ratified and its author rewarded (300 → 330 ATP) | BEHAVIOR_FIXED (`8f199b0`) |
| Warrant verifier, EMPIRICAL (DOC-F1) | a documentation-floor review, repeated by a second model | two suspended sides audited pass on equal intermediates, fail on unequal ones | CLOSED in code by PR #49 |

The repair rule is the same in each: a comparison is admitted only when both sides
settle; a settled mismatch is a checked negative; otherwise the result is
`UNVERIFIED`, a refusal rather than a verdict. For EMPIRICAL the rule also keeps
scanning past a suspended fixture, because an early return would mask a later
settled mismatch in one fixture order.

The four sites are `warrant_kernel.WarrantVerifier.audit_claim` (grades G and E),
`polyglot.audit_polyglot_claims` and `epistemic_swarm.SwarmAgoraCommons.vote_and_settle`.

**Executed here:** 20 tests in three modules pass at the measured commit:

- `test_empirical_settlement`
- `test_polyglot_suspended_nf`
- `test_warrant_grounded_suspension`

 The
counts, rewards and discovery attributions above are **reported** from the ledger,
not re-derived. The ledger also lists 13 same-shape candidates from a syntactic
scan; they are unverified, and this paper does not count them. Exceptions raised
during an EMPIRICAL fixture still map to `fail`; aligning that with other branches
is a separate open decision.

## 4. Claim 3 — one receiver rejected false advice

Black-Heart's experience contract (`xC010-model-experience.md`) stores engineering
experience as records with pinned evidence. In the recorded exchange CM-3, a sender
(Codex) supplied the real DOC-F1 record and an explicitly synthetic contradictory
record advising an early `UNVERIFIED` return. A fresh Claude Code session — runtime
metadata `claude-opus-5[1m]`, not an authenticated identity — received only an
approved snapshot, ran a fixed differential prepared by the sender, and emitted its
own record. The baseline passed 3 of 3 regression tests; with the advice applied,
2 of 3, failing on the fixture order `[ω ω, K]`. The receiver rejected the advice
within that scope.

The limits are part of the result: one session; synthetic advice; the check was
designed by the sender and executed by the receiver, not designed by it; the
receiver's record has two documented defects (a misattributed evidence pointer and
the phrase "independent differential"); request context was observed at the client,
not at the provider. **Executed here:** the saved exchange verifier re-checks byte
correspondence of the retained records and reports ok; it does not re-run the model.

A subsequent pre-registered pilot (TRANSFER-1) compared no lesson, a plain-text
lesson and the same lesson with an executable witness on a new task. All three
first sessions succeeded, the early-stop rule ended the pilot, and no advantage of
the evidence packet was demonstrated. Claim 3 is therefore a record that the workflow
ran once as designed, not evidence that packets improve transfer.

## 5. Reproduction

From a clone at commit `1981386`:

```sh
python3 -B papers/runs-its-own-checks/measure.py ~/new-output-dir
python3 -I ~/new-output-dir/companion.pdf
```

The script builds the companion, runs it, `cli.py verify` and `cli.py sandbox`,
applies the six controls to copies, and reruns the 20 regression tests and the
saved CM-3 verifier. It makes no model call and writes only to the new directory.
The retained receipt is `measurements/measurements.json`, with host paths
replaced by neutral names. The companion's bytes should match the retained file; exit
codes should match the tables. Timing lines will differ. The paper PDF is built by
`build.sh` (pandoc 3.11, tectonic 0.17.0, `SOURCE_DATE_EPOCH=1789344000`).

## 6. What would weaken these claims

- **Claim 1:** a rebuild at the stated commit that differs in bytes, or any control
  with a different exit code on another Python 3 version. Viewer compatibility with
  the 20-byte prefix beyond `pdfinfo` was not tested.
- **Claim 2:** a regression test at the commit that fails, or a reproduction showing
  a listed consumer still credits a suspended result.
- **Claim 3:** a byte mismatch between the saved records and their digests. A later
  receiver that accepts the advice would not falsify this record; it would be a
  second observation.

## 7. Provenance and limits

The repository, its reviews and this paper were produced with language-model
assistance (Claude, Codex); reviews cited here are model reviews. There is no
independent human review. The author is the accountable human. The paper reports
engineering observations about one repository at one commit and makes no claim of
security, correctness of Black-Heart as a whole, or generality beyond the tables.
Related deposits by the same author: the Σ-GLYPH engine [@sigma-glyph], Warrant
decision records [@warrant], and a report on verifier-reported verification load
[@every-check].

## References
