---
title: "What a Green Check Does Not Establish: A Self-Running PDF Companion and Two Records from Black-Heart"
author: "Serhii Glova (ORCID 0009-0001-8010-420X)"
date: 2026-09-14
license: "Paper CC BY-SA 4.0; the companion polyglot contains executable code under AGPL-3.0-only"
---

## Abstract

A passing check is easy to over-read. We examine one concrete case: a file from the
Black-Heart repository that is both a PDF document and a Python program, whose embedded
runner reduces the combinator claims written in the file and prints "100% SOUND". A
one-page companion built with the repository's existing `PolyglotDocument` rebuilds
byte-identically and passes its runner, `cli.py verify` and a static sandbox. Nine
controls on copies locate what that green result covers. A changed claim and a
non-terminating claim fail. An appended tautological claim, an edited visible title, a
wrong claim made unrecognizable by one space, and a file with no recognized claims all
exit 0; so does a file that writes to the filesystem under `python3 -I`. The runner and
the static sandbox also disagree on which lines are claims. The predicate actually
checked is narrow: *recognized* claim lines reduce to the normal forms written beside
them. Two records from the same repository illustrate the same boundary: budget-suspended
computations credited as results in four consumers (repaired; 20 regression tests pass),
and one receiver session that rejected synthetic advice after running a check someone
else designed. Nothing here is peer-reviewed; the paper is an engineering report, not a
measure of general reliability.

## 1. Question and scope

The question is not whether Black-Heart works, but what a green verification result from
it does and does not establish. We answer for one artifact and keep each statement at the
strength of its evidence:

| Part | Content | Evidence class |
|---|---|---|
| §3 main case | the companion polyglot and nine controls | **executed** here (`measurements/measurements.json`) |
| §4 supporting record | "suspended taken as settled" in four consumers | **reported** in the remediation ledger; regression tests **executed** here |
| §5 short example | one receiver rejected synthetic advice | **reported** records; byte correspondence **executed** here |

All measurements are at commit `30679a4` of `s0fractal/black-heart` (code identical to
`origin/main` `62e3e80` plus the measurement script). An earlier plan for this paper was a
document that "verifies its own tree rings" — incremental PDF updates, seals and sandbox as
one self-checking artifact. The code at that commit does not implement such a check (§3.5),
so it is not claimed.

## 2. Related approaches

Executable and reproducible research has established tools with different goals.
ActivePapers packages code, data and results of computer-aided research in one archive
designed for publication and long-term preservation [@activepapers]. ReproZip traces a
computational experiment and packs its files and dependencies so that others can re-run it
in another environment [@reprozip]. The obvious simple alternative to our artifact is a
PDF, a script and a manifest of digests side by side.

The companion is none of these. Its only distinctive property is packaging: one file that
a PDF viewer displays and a Python interpreter runs. We do not show that this is more useful
than a PDF plus a script, and it has real costs: the reader must execute code shipped by the
author, the visible text and the executed claims are not bound to each other, and a PDF with
a 20-byte non-PDF prefix relies on tolerant viewers. The contribution here is narrower and
applies to any of these approaches: an explicit account of what a green result from an
embedded check covers, measured with controls.

## 3. Main case — the companion polyglot

### 3.1 Construction

`polyglot.PolyglotDocument.compile` writes a file that begins with `# coding: utf-8` and a
Python raw-string opener, so the PDF header sits at byte 20 and the PDF body is a string
literal. After the PDF trailer the string closes and a standard-library runner follows.
Claims are PDF comment lines of the form
`%<U+1F5A4> CLAIM: id=… | expr=… | expected=… | max_atp=… | desc=…`, where `<U+1F5A4>` is
the black-heart emoji. The runner finds such lines with a regular expression, reduces
`expr` with its own S/K/I/Y engine under the stated budget, reduces `expected`, and compares
the rendered normal forms. A budget overrun counts as a failed claim.

The companion (`measurements/companion.pdf`, 8,627 bytes, sha256 `b7a8bab2…f2f278`) carries
three claims: `S K K x → x`, `K I a b → b`, `S f g x → f x (g x)`. `pdfinfo` reads it as a
one-page A4 PDF 1.7.

### 3.2 Baseline

| Check | Result |
|---|---|
| Two builds from the same script | byte-identical |
| Host home or repository path in the file | absent |
| `python3 -I companion.pdf` | exit 0, 3/3 settled |
| `python3 cli.py verify companion.pdf` | exit 0, "local checks passed for the reported scope" |
| `python3 cli.py sandbox companion.pdf` | exit 0, SOUND; scope "0 signature(s) and 3 claim(s) … NOT the whole document" |

### 3.3 Controls

Each control modifies a copy and runs it with `python3 -I` unless stated.

| Control | Runner exit | Reading |
|---|---|---|
| First claim's expected value changed to `y` | 1 | a changed, recognized claim is detected |
| Non-terminating claim `S I I (S I I)` appended | 1 | budget overrun fails closed |
| Tautological claim `a → a` appended | 0 | 4/4, "100% SOUND": appended claims are not authenticated |
| Visible title changed, same byte length | 0 | the rendered text is not bound to the claims |
| The wrong claim above, plus one space after `expected=` | 0 | 2/2, "100% SOUND": the wrong claim is no longer recognized |
| One extra space in every claim line | 0 | "No claims discovered"; exit 0 with nothing checked |
| Code added that writes a file, run with `-I` | 0 | the file was created; `-I` is not a sandbox |
| `hashlib.py` next to the file, plain `python3` | 7 | the neighbouring module ran first |
| The same, with `-I` | 0 | not imported under isolation mode |

The static sandbox, run on two of these copies, recognizes lines differently from the
runner. On the hidden wrong claim it reports UNSOUND (exit 1), where the runner reports
green. On the copy with an extra space in every line it still finds and settles all three
claims (SOUND), where the runner finds none. Two checkers shipped by the same repository
therefore disagree about which lines of one file are claims.

### 3.4 The predicate actually checked

The runner establishes this and no more: *every claim line its regular expression
recognizes reduces, under its own engine and budget, to the normal form of the value
written beside it.* An exit code of 0 does not show that anything was checked, that the
recognized set is the intended set, that a claim is substantive or authored by anyone in
particular, that the page says what the claims say, or that bytes were not appended. The
closing line "Document integrity & proof verification: 100% SOUND" is wider than this
predicate.

Running the companion is executing Python code shipped in the file, with the reader's
user permissions. `-I` isolates import paths and user site settings; it does not restrict
filesystem or network access, and it does not make an unknown file safe to run. The
non-executing alternative is the static sandbox, which has its own history: the
remediation ledger records that it once reported SOUND without verifying anything (found
by an independent security scan of `e549de3`), repaired so that SOUND requires at least
one positively verified element and zero failures, within an explicit "NOT the whole
document" scope.

### 3.5 What is not part of the companion

Incremental updates exist elsewhere in the repository:
`morpho_net.grow_ontogenetic_quine_in_pdf` appends a revision in place and keeps the file
runnable. Its audit checks a receipt chain but reads only the last manifest, takes the
public key from the receipt itself, passes unsigned revisions as "UNATTESTED", and its
runner falls back to a fixed local checkout path to import its engine. None of this is in
the companion, and "a document that verifies its own history" is not a claim of this paper.

## 4. Supporting record — "suspended" taken as "settled"

Black-Heart's evaluator returns `SUSPENDED`, with an intermediate term, when a reduction
exhausts its budget. Four consumers compared that intermediate term as if it were a result.
The remediation ledger (`docs/REMEDIATION-LEDGER.md`) records each:

| Consumer | Found by | Before repair | Disposition |
|---|---|---|---|
| Warrant verifier, Grade G | independent security scan of `e549de3`, reproduced | a non-terminating term with its hash pinned to the suspended intermediate audited PASS | BEHAVIOR_FIXED (`b386a23`) |
| polyglot claim auditor | same scan, reproduced | a non-terminating claim with expected = expression verified at the maximum budget | BEHAVIOR_FIXED (`8f199b0`) |
| swarm vote and settlement | same scan, reproduced end to end | the proposal was ratified and its author rewarded (300 → 330 ATP) | BEHAVIOR_FIXED (`8f199b0`) |
| Warrant verifier, EMPIRICAL (DOC-F1) | a documentation-floor review, repeated by a second model | two suspended sides audited pass on equal intermediates, fail on unequal ones | CLOSED in code by PR #49 |

The shared invariant after repair is that an unfinished computation is never credited as
confirmation. The refusal semantics differ by consumer. The Warrant Grade G and EMPIRICAL
branches return `UNVERIFIED`, a refusal distinct from `FAIL`; EMPIRICAL also keeps scanning
past a suspended fixture so that a later settled mismatch still yields `FAIL`. The polyglot
claim auditor returns `False` for the whole document, without distinguishing a suspended
claim from a wrong one. The swarm counts the proposal as unsound in the vote, so it is not
ratified, rewarded or added to the canon.

**Executed here:** 20 tests in three modules pass at the measured commit:

- `test_empirical_settlement`
- `test_polyglot_suspended_nf`
- `test_warrant_grounded_suspension`

The consequences and discovery attributions in the table are **reported** from the ledger,
not re-derived. The ledger also lists 13 same-shape candidates from a syntactic scan; they
are unverified and not counted here. Exceptions raised while evaluating an EMPIRICAL fixture
still map to `FAIL`; aligning that with other branches is an open decision.

## 5. Short example — a green differential and the advice it refuted

In a recorded exchange (CM-3), a sender supplied a real experience record and an explicitly
synthetic contradictory one advising an early `UNVERIFIED` return in the EMPIRICAL loop. A
fresh Claude Code session (runtime metadata `claude-opus-5[1m]`, not an authenticated
identity) ran a fixed differential prepared by the sender: baseline 3/3 regression tests,
advice applied 2/3, failing on fixture order `[ω ω, K]`. It rejected the advice for that
scope. The green differential established one thing — that this patch breaks this test on
this order — not that the receiver designed a check, that the advice was realistic, or that
experience packets help. A later pre-registered three-arm pilot (TRANSFER-1) found no
advantage of an evidence packet over plain text. **Executed here:** the saved-exchange
verifier re-checks byte correspondence of the retained records; it does not re-run a model.

## 6. Reproduction

From a clone at commit `30679a4`:

```sh
python3 -B papers/runs-its-own-checks/measure.py ~/new-output-dir
python3 -I ~/new-output-dir/companion.pdf
```

The script builds the companion, runs it, `cli.py verify` and `cli.py sandbox`, applies the
nine controls to copies (with the sandbox on two of them), and reruns the 20 regression
tests and the saved-exchange verifier. It makes no model call and writes only to the new
directory. The retained receipt `measurements/measurements.json` replaces host paths with
neutral names. Companion bytes and exit codes should match; timing lines will differ. The
paper PDF is built by `build.sh` (pandoc 3.11, tectonic 0.17.0, `SOURCE_DATE_EPOCH=1789344000`).

## 7. What would weaken these statements

- §3: a rebuild at the stated commit that differs in bytes, or a control with a different
  exit code on another Python 3 version. Viewer compatibility beyond `pdfinfo` was not tested.
- §4: a failing regression test at the commit, or a reproduction showing a listed consumer
  still credits a suspended result.
- §5: a byte mismatch between the saved records and their digests. A later receiver that
  accepts the advice would be a second observation, not a refutation of this one.

## 8. Provenance and limits

The repository, its reviews and this paper were produced with language-model assistance
(Claude, Codex); the reviews that shaped this version are model reviews, and there is no
independent human review. The author is the accountable human. Three toy reductions and the
repository's own regressions confirm specific behaviour; they are not a measurement of
general reliability, security or usefulness of Black-Heart. Related deposits by the same
author: the Σ-GLYPH engine [@sigma-glyph], Warrant decision records [@warrant], and a report
on verifier-reported verification load [@every-check].

## References
