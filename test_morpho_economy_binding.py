#!/usr/bin/env python3
"""
Regression: the morpho-autopoiesis ATP reserve is bound to its signed receipt
chain, and a zero-change epoch credits zero.

Audit S6a: `evolve_morpho_autopoietic_organism` / `audit_morpho_autopoietic_organism`,
the one live boundary in this engine where a receipt gates a state change and an
ATP credit, reached by `cli.py morpho-autopoiesis evolve`.

Measured at 413f1ce with the real functions, no mocks:
  - A genome that has locally stabilized (every proposal, including the
    exploratory operand swaps, rejected) still minted a SIGNED receipt every
    later epoch: rule_name "METABOLIC_DRIFT", pre_term == post_term (literally
    no change), atp_saved = 1, crediting +5 ATP. Twelve `evolve` calls on a
    genesis organism gave 8 such receipts, +40 ATP for zero measured change,
    and this repeats without limit on every further call.
  - `MorphoAutopoieticOrganism.atp_reserve` is a bare int in the manifest, not
    covered by `compute_hash()` and not referenced by any receipt field.
    Editing it directly to 999999, with no new receipt at all, still audited
    sound.

Fields and their (pre-fix) source / independent check:
  atp_saved         source: `max(1, -eval_res.atp_delta)` when a proposal was
                     accepted, else the literal constant 1. checked by: nothing
                     -- audit never re-evaluated (pre_term, post_term).
  pre_term/post_term source: `prop.original_term`/`prop.candidate_term` when
                     accepted, else the SAME chromosome expression twice.
                     checked by: only the receipt's own signature (internal
                     self-consistency), never against a fresh evaluation.
  atp_reserve        source: `org.atp_reserve += max(5, atp_saved*2)`, an
                     ordinary Python int in the manifest dict. checked by:
                     nothing at all.

Fix: `MorphoAutopoiesisReceipt.resulting_atp_reserve`, now part of the signed
payload; `audit_morpho_autopoietic_organism` re-evaluates every claimed
transition under the same FrozenEvaluator, requires atp_saved/size_saved to
equal what that gives, requires a NO_MUTATION_FOUND epoch to claim exactly
zero and identical pre/post, requires each step's credit to follow from its
own atp_saved by one shared formula (`_expected_credit`), and requires the
live atp_reserve to equal the last receipt's committed value.

Sections:
  A  honest positive: a real improvement is credited; nothing found credits zero
  B  the reproduced defect, as permanent negative controls
  C  replay: named, not silently prevented
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path[:1]:
    sys.path.insert(0, _HERE)
for _name, _mod in list(sys.modules.items()):
    _file = getattr(_mod, "__file__", None)
    if not _file:
        continue
    if os.path.dirname(os.path.abspath(_file)) != _HERE and \
            os.path.exists(os.path.join(_HERE, os.path.basename(_file))):
        del sys.modules[_name]

import morpho_autopoiesis as M
from metamorphosis import FrozenEvaluator, MutationVerdict
from glyph import parse

if os.path.dirname(os.path.abspath(M.__file__)) != _HERE:
    raise ImportError(f"morpho_autopoiesis resolved to {M.__file__}, outside {_HERE}")


def read_manifest(pdf_path: str) -> dict:
    with open(pdf_path, "rb") as f:
        data = f.read()
    prefix = M.MORPHO_AUTOPOIESIS_MANIFEST_PREFIX.encode("utf-8")
    idx = data.rfind(prefix)
    line = data[idx + len(prefix):].split(b"\n", 1)[0]
    return json.loads(line)


def write_manifest(pdf_path: str, manifest: dict) -> None:
    with open(pdf_path, "rb") as f:
        data = f.read()
    prefix = M.MORPHO_AUTOPOIESIS_MANIFEST_PREFIX.encode("utf-8")
    idx = data.rfind(prefix)
    end = data.index(b"\n", idx)
    with open(pdf_path, "wb") as f:
        f.write(data[:idx] + prefix + json.dumps(manifest).encode("utf-8") + data[end:])


class _Organism(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.pdf = os.path.join(self._tmp.name, "org.pdf")
        self.org, self.genesis_rec = M.init_morpho_autopoietic_organism(self.pdf)
        with open(self.pdf + ".key") as f:
            self.sk = f.read().strip()

    def evolve(self):
        return M.evolve_morpho_autopoietic_organism(self.pdf, secret_key_hex=self.sk)

    def evolve_to_stable(self, max_steps=40):
        """Runs evolve until the genome stops changing (a NO_MUTATION_FOUND
        epoch is reached), or fails the test if that never happens."""
        for _ in range(max_steps):
            org, rec = self.evolve()
            if rec.rule_name == M.NO_MUTATION_FOUND_RULE:
                return org, rec
        self.fail(f"genome did not stabilize within {max_steps} epochs")


class HonestCreditTest(_Organism):
    """Section A."""

    def test_A1_a_real_improvement_credits_exactly_the_stated_formula(self):
        org, rec = self.evolve()
        self.assertNotEqual(rec.rule_name, M.NO_MUTATION_FOUND_RULE)
        self.assertGreater(rec.atp_saved, 0)
        self.assertEqual(org.atp_reserve, self.org.atp_reserve + max(5, rec.atp_saved * 2))
        self.assertEqual(rec.resulting_atp_reserve, org.atp_reserve)
        self.assertTrue(M.audit_morpho_autopoietic_organism(self.pdf))
        # Independently re-derivable: the SAME evaluator, given the receipt's
        # own pre/post terms, gives the SAME atp_saved.
        eval_res = FrozenEvaluator().evaluate_transformation(parse(rec.pre_term), parse(rec.post_term))
        self.assertEqual(eval_res.verdict, MutationVerdict.ACCEPTED_MORE_EFFICIENT)
        self.assertEqual(rec.atp_saved, max(1, -eval_res.atp_delta))

    def test_A0_the_shared_credit_formula_floors_small_savings(self):
        """Unit-level, direct: both evolve and audit call the SAME
        `_expected_credit`, so pinning its floor here holds regardless of
        whether any real epoch happens to save few enough ATP to exercise it."""
        self.assertEqual(M._expected_credit(0), 0)
        self.assertEqual(M._expected_credit(1), 5)
        self.assertEqual(M._expected_credit(2), 5)
        self.assertEqual(M._expected_credit(3), 6)
        self.assertEqual(M._expected_credit(100), 200)

    def test_A2_nothing_found_credits_exactly_zero(self):
        """The reproduced defect, now closed: a genome with every proposal
        rejected must stop earning ATP, not fabricate a 1-ATP receipt forever."""
        before_reserve = None
        org, rec = self.evolve_to_stable()
        for _ in range(5):  # confirm it stays flat, not just the first time
            reserve_before = org.atp_reserve
            org, rec = self.evolve()
            self.assertEqual(rec.rule_name, M.NO_MUTATION_FOUND_RULE)
            self.assertEqual(rec.pre_term, rec.post_term)
            self.assertEqual(rec.atp_saved, 0)
            self.assertEqual(rec.size_saved, 0)
            self.assertEqual(org.atp_reserve, reserve_before, "a stable genome earned ATP for no change")
            self.assertTrue(M.audit_morpho_autopoietic_organism(self.pdf))


class ReproducedDefectTest(_Organism):
    """Section B: the S6a probe's findings, as permanent negative controls.
    Each tamper must leave audit_morpho_autopoietic_organism False."""

    def tamper(self, mutate_manifest):
        manifest = read_manifest(self.pdf)
        mutate_manifest(manifest)
        write_manifest(self.pdf, manifest)
        return manifest

    def test_B1_atp_reserve_edited_directly_is_refused(self):
        """The probe's own headline finding: no receipt at all, audit was True."""
        self.evolve()
        self.assertTrue(M.audit_morpho_autopoietic_organism(self.pdf))
        self.tamper(lambda m: m.__setitem__("atp_reserve", 999_999))
        self.assertFalse(M.audit_morpho_autopoietic_organism(self.pdf))

    def test_B2_a_fabricated_no_op_credit_under_the_honest_name_is_refused(self):
        """Replays the exact old exploit shape under the new rule name: reach a
        genuine NO_MUTATION_FOUND epoch, then forge its atp_saved from 0 to 1
        with the reserve arithmetic otherwise kept fully self-consistent (bumped
        by exactly `_expected_credit(1)`), so this isolates the NO_MUTATION_FOUND
        honesty check itself -- the arithmetic and re-evaluation checks would
        both let this specific forgery through on their own."""
        self.evolve_to_stable()
        manifest = read_manifest(self.pdf)
        last = manifest["receipt_chain"][-1]
        forged = M.MorphoAutopoiesisReceipt.from_dict(last)
        self.assertEqual(forged.rule_name, M.NO_MUTATION_FOUND_RULE)
        self.assertEqual(forged.atp_saved, 0)
        forged.atp_saved = 1
        forged.resulting_atp_reserve += M._expected_credit(1)
        forged.sign(self.sk)  # the real key -- a genuine signature over false content
        manifest["receipt_chain"][-1] = forged.to_dict()
        manifest["atp_reserve"] = forged.resulting_atp_reserve
        write_manifest(self.pdf, manifest)
        self.assertFalse(M.audit_morpho_autopoietic_organism(self.pdf))

    def test_B3_a_fake_rule_name_over_a_real_pair_is_refused(self):
        """A real (pre != post) improving pair, relabeled under an invented rule
        name with an arbitrary atp_saved -- reserve arithmetic kept
        self-consistent with the FORGED atp_saved, so only re-evaluation of the
        claimed (pre_term, post_term) pair can catch it, not the arithmetic."""
        self.evolve()
        manifest = read_manifest(self.pdf)
        last = manifest["receipt_chain"][-1]
        prev_reserve = last["resulting_atp_reserve"] - M._expected_credit(last["atp_saved"])
        forged = M.MorphoAutopoiesisReceipt.from_dict(last)
        forged.rule_name = "FORGED_GAIN"
        forged.atp_saved = 50
        forged.resulting_atp_reserve = prev_reserve + M._expected_credit(50)
        forged.sign(self.sk)  # the real key -- a genuine signature over false content
        manifest["receipt_chain"][-1] = forged.to_dict()
        manifest["atp_reserve"] = forged.resulting_atp_reserve
        write_manifest(self.pdf, manifest)
        self.assertFalse(M.audit_morpho_autopoietic_organism(self.pdf))

    def test_B4_an_inflated_atp_saved_on_a_genuine_pair_is_refused(self):
        """The transition is real (pre != post, genuinely accepted), but the
        claimed atp_saved overstates what the evaluator actually measured."""
        org, rec = self.evolve()
        self.assertGreater(rec.atp_saved, 0)
        manifest = read_manifest(self.pdf)
        last = manifest["receipt_chain"][-1]
        forged = M.MorphoAutopoiesisReceipt.from_dict(last)
        forged.atp_saved = rec.atp_saved + 1000
        forged.resulting_atp_reserve += 1000 * 2
        forged.sign(self.sk)
        manifest["receipt_chain"][-1] = forged.to_dict()
        manifest["atp_reserve"] = forged.resulting_atp_reserve
        write_manifest(self.pdf, manifest)
        self.assertFalse(M.audit_morpho_autopoietic_organism(self.pdf))

    def test_B5_skipping_the_credit_arithmetic_is_refused(self):
        """resulting_atp_reserve silently NOT incremented for a real improvement."""
        org, rec = self.evolve()
        manifest = read_manifest(self.pdf)
        last = manifest["receipt_chain"][-1]
        forged = M.MorphoAutopoiesisReceipt.from_dict(last)
        forged.resulting_atp_reserve -= max(5, rec.atp_saved * 2)  # claim the PRE-credit balance
        forged.sign(self.sk)
        manifest["receipt_chain"][-1] = forged.to_dict()
        manifest["atp_reserve"] = forged.resulting_atp_reserve
        write_manifest(self.pdf, manifest)
        self.assertFalse(M.audit_morpho_autopoietic_organism(self.pdf))

    def test_B6_a_genuinely_signed_receipt_from_another_organism_does_not_splice_in(self):
        """A receipt signed by a DIFFERENT organism's key, otherwise well-formed,
        appended in place of this organism's own next receipt."""
        other_pdf = os.path.join(self._tmp.name, "other.pdf")
        other_org, _ = M.init_morpho_autopoietic_organism(other_pdf)
        with open(other_pdf + ".key") as f:
            other_sk = f.read().strip()
        _, foreign_rec = M.evolve_morpho_autopoietic_organism(other_pdf, secret_key_hex=other_sk)

        manifest = read_manifest(self.pdf)
        manifest["receipt_chain"].append(foreign_rec.to_dict())
        write_manifest(self.pdf, manifest)
        self.assertFalse(M.audit_morpho_autopoietic_organism(self.pdf))


class ReplayTest(_Organism):
    """Section C: what re-presentation means for this contract, named explicitly."""

    def test_C1_forking_the_file_and_evolving_both_copies_is_allowed_by_design(self):
        """Copying the PDF and evolving each copy independently is NOT prevented:
        each fork is its own organism state from that point on, and each
        legitimately earns its own credit for its own (independent) measured
        improvement. There is no global registry across files that would make
        this a double-spend of one ledger; this is a stated boundary, not a
        silently-left gap."""
        fork_a = self.pdf
        fork_b = os.path.join(self._tmp.name, "fork_b.pdf")
        shutil.copy(self.pdf, fork_b)
        shutil.copy(self.pdf + ".key", fork_b + ".key")

        org_a, rec_a = M.evolve_morpho_autopoietic_organism(fork_a, secret_key_hex=self.sk)
        org_b, rec_b = M.evolve_morpho_autopoietic_organism(fork_b, secret_key_hex=self.sk)

        self.assertTrue(M.audit_morpho_autopoietic_organism(fork_a))
        self.assertTrue(M.audit_morpho_autopoietic_organism(fork_b))
        self.assertEqual(rec_a.atp_saved, rec_b.atp_saved)
        self.assertEqual(org_a.atp_reserve, org_b.atp_reserve)

    def test_C2_auditing_the_same_unmodified_file_repeatedly_has_no_effect(self):
        """Audit itself is read-only: presenting the identical file again and
        again neither changes atp_reserve nor mints anything."""
        self.evolve()
        before = read_manifest(self.pdf)
        for _ in range(3):
            self.assertTrue(M.audit_morpho_autopoietic_organism(self.pdf))
        self.assertEqual(read_manifest(self.pdf), before)


if __name__ == "__main__":
    unittest.main()
