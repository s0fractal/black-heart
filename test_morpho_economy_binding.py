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

Review R1 (amendment). The checks above re-derive each receipt's economy from
the receipt's OWN declared pair, which does not establish that the pair
describes THIS epoch's change. Measured by the reviewer's probe at 19ae2a6:
lifting a genuine, already-paid pair out of an earlier epoch and transplanting
it into a later epoch where the genome never moved -- keeping generation,
parent and organism hashes, balancing the arithmetic, and signing with the
document's own real key -- audited True and carried +30 unearned ATP through
the next evolve, which accepted the document.

  recycled_transition_audit True  unearned_credit 30  genome_unchanged True
  next_evolve_accepted True  excess_balance 30  genome_still_unchanged True

Amendment fix: the audit replays the genome BACKWARDS through the chain and
requires every receipt's already-signed organism_hash to reconstruct from the
genome that receipt's own epoch actually held, so a pair is pinned to the real
parent->result transition. For that replay to reconstruct genesis-era genomes
exactly, seed expressions are now stored canonically (`str(parse(x))`, which
renders glyphs); every later epoch already stored canonical spelling. The
recorded site must be the deepest address at which the pair differs, and the
experiment id must be the producer's own derivation over the five transition
fields, so they cannot be re-mixed independently. No new receipt field is
added: the binding re-reads fields that were already signed.

Sections:
  A  honest positive: a real improvement is credited; nothing found credits zero
  B  the reproduced defect, as permanent negative controls
  C  replay: named, not silently prevented
  D  review R1: a pair is bound to the transition it claims to describe
"""
from __future__ import annotations

import copy
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


# The private-key sidecar suffix. Named once so the pending ".key" -> U+1F511
# rename (PR #26) lands on a single line when this branch rebases onto it.
KEY_SUFFIX = ".key"


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
        self.key_path = self.pdf + KEY_SUFFIX
        with open(self.key_path) as f:
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
        with open(other_pdf + KEY_SUFFIX) as f:
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
        shutil.copy(self.pdf + KEY_SUFFIX, fork_b + KEY_SUFFIX)

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


class TransitionBindingTest(_Organism):
    """Section D, review R1: a measured pair must describe THIS epoch's change.

    Every forgery here is signed with the document's OWN real key and keeps the
    credit arithmetic self-consistent, so neither the signature checks nor the
    economy checks can be what refuses it."""

    def stabilize_keeping_first_paid_receipt(self, max_steps=40):
        """Evolve to a NO_MUTATION_FOUND epoch, returning the first genuinely
        rewarded receipt along the way -- the donor of an already-paid pair."""
        donor = None
        for _ in range(max_steps):
            _, rec = self.evolve()
            if donor is None and rec.atp_saved > 0:
                donor = rec.to_dict()
            if rec.rule_name == M.NO_MUTATION_FOUND_RULE:
                self.assertIsNotNone(donor, "no rewarded epoch to recycle")
                return donor
        self.fail(f"genome did not stabilize within {max_steps} epochs")

    def recycle_into_last_receipt(self, also_transplant_location=False):
        """The reviewer's counterexample, rebuilt: move an earlier, already-paid
        transition onto the current unchanged epoch, add the matching credit and
        re-sign with the legitimate key. Returns (extra_credit, genome_before).

        `also_transplant_location` brings the donor's gene and site across with
        the pair and re-derives the experiment id from the transplanted fields,
        so every derived field is internally consistent and only the genome
        replay is left to refuse it."""
        donor = self.stabilize_keeping_first_paid_receipt()
        self.assertTrue(M.audit_morpho_autopoietic_organism(self.pdf))

        manifest = read_manifest(self.pdf)
        genome_before = copy.deepcopy(manifest["chromosomes"])
        target = M.MorphoAutopoiesisReceipt.from_dict(manifest["receipt_chain"][-1])
        self.assertEqual(target.rule_name, M.NO_MUTATION_FOUND_RULE)
        fields = ["rule_name", "pre_term", "post_term",
                  "atp_saved", "size_saved", "experiment_id"]
        if also_transplant_location:
            fields += ["gene_id", "site_address"]
        for field in fields:
            setattr(target, field, donor[field])
        if also_transplant_location:
            target.experiment_id = M.derive_experiment_id(
                target.gene_id, tuple(target.site_address), target.rule_name,
                target.pre_term, target.post_term)
        extra = M._expected_credit(donor["atp_saved"])
        self.assertGreater(extra, 0)
        target.resulting_atp_reserve += extra
        target.sign(self.sk)

        manifest["receipt_chain"][-1] = target.to_dict()
        manifest["atp_reserve"] += extra
        write_manifest(self.pdf, manifest)
        self.assertEqual(read_manifest(self.pdf)["chromosomes"], genome_before,
                         "the genome really did not move -- that is the whole point")
        return extra, genome_before

    def resign_last(self, mutate):
        """Apply `mutate` to the tip receipt and re-sign it with the real key."""
        manifest = read_manifest(self.pdf)
        rec = M.MorphoAutopoiesisReceipt.from_dict(manifest["receipt_chain"][-1])
        mutate(rec)
        rec.sign(self.sk)
        manifest["receipt_chain"][-1] = rec.to_dict()
        write_manifest(self.pdf, manifest)
        return rec

    def test_D1_a_previously_paid_transition_cannot_credit_an_unchanged_epoch(self):
        """The reviewer's probe exactly as written, as a permanent regression.

        It transplants the pair and its economy but leaves the target epoch's
        own gene and site in place. MEASURED by mutation control: this shape is
        refused by the experiment-id tie -- the id is derived from the gene, the
        site, the rule and both terms, so a copied id no longer matches -- and
        the genome replay is never reached. `test_D9` is the version an attacker
        who knows that public derivation would build; that one isolates the
        replay. Both are kept: this pins the reported artifact, D9 pins the
        mechanism."""
        self.recycle_into_last_receipt()
        self.assertFalse(M.audit_morpho_autopoietic_organism(self.pdf))

    def test_D9_recycling_stays_refused_when_every_derived_field_is_consistent(self):
        """The strongest form of the counterexample: the donor's gene and site
        travel with the pair and the experiment id is re-derived from them, so
        the economy, the arithmetic, the location, the id and the signature are
        all internally consistent. Only the backward genome replay can refuse
        this -- the recycled pair implies a parent genome that no longer hashes
        to the parent's committed organism_hash.

        Measured by mutation control: the replay's two halves (the
        reconstructed-hash comparison, and the gene/post_term binding that
        undoes each step) are MUTUALLY redundant for this artifact, so removing
        either one alone still refuses it. The control that pins this test
        therefore disables the whole loop rather than one line of it."""
        self.recycle_into_last_receipt(also_transplant_location=True)
        self.assertFalse(M.audit_morpho_autopoietic_organism(self.pdf))

    def test_D2_the_recycled_artifact_is_refused_before_evolve_writes(self):
        """Refusal must come before any state change: the document and its key
        sidecar stay byte-identical, and no generation is appended. Uses the
        harder D9 shape, so this exercises the replay path too."""
        self.recycle_into_last_receipt(also_transplant_location=True)

        def snapshot():
            with open(self.pdf, "rb") as f:
                doc = f.read()
            with open(self.key_path, "rb") as f:
                key = f.read()
            return doc, key

        doc_before, key_before = snapshot()
        with self.assertRaises(ValueError):
            self.evolve()
        doc_after, key_after = snapshot()

        self.assertEqual(doc_after, doc_before, "the refused call wrote to the document")
        self.assertEqual(key_after, key_before, "the refused call touched the key sidecar")

    def test_D3_a_genuine_pair_attributed_to_the_wrong_gene_is_refused(self):
        """Real, honestly-measured pair; only the gene it is attributed to is
        wrong. The experiment id is recomputed so it stays consistent, leaving
        the genome replay as the only check that can catch this."""
        _, rec = self.evolve()
        self.assertGreater(rec.atp_saved, 0)
        other = next(c.gene_id for c in self.org.chromosomes if c.gene_id != rec.gene_id)

        def mutate(r):
            r.gene_id = other
            r.experiment_id = M.derive_experiment_id(
                other, tuple(r.site_address), r.rule_name, r.pre_term, r.post_term)
        forged = self.resign_last(mutate)
        self.assertTrue(forged.verify(), "the forgery is validly signed; content is what must refuse it")
        self.assertFalse(M.audit_morpho_autopoietic_organism(self.pdf))

    def test_D4_a_genuine_pair_at_the_wrong_location_is_refused(self):
        """Real pair, real gene, but the recorded site is not where the terms
        differ. The experiment id is recomputed to stay consistent, isolating
        the location check."""
        _, rec = self.evolve()
        real_site = tuple(rec.site_address)
        wrong = real_site + ("L",) if real_site == () else ()
        self.assertNotEqual(wrong, real_site)

        def mutate(r):
            r.site_address = list(wrong)
            r.experiment_id = M.derive_experiment_id(
                r.gene_id, wrong, r.rule_name, r.pre_term, r.post_term)
        self.resign_last(mutate)
        self.assertFalse(M.audit_morpho_autopoietic_organism(self.pdf))

    def test_D5_the_recorded_site_must_be_the_deepest_one_not_merely_an_ancestor(self):
        """Directly pins the predicate: the root localizes every change
        vacuously, so a root claim over a strictly deeper rewrite is refused."""
        pre, post = parse("\U0001F5A4 alpha beta"), parse("\U0001F5A4 alpha gamma")
        deepest = ("R",)
        self.assertTrue(M._transition_is_local(pre, post, deepest))
        self.assertFalse(M._transition_is_local(pre, post, ()), "root must not localize vacuously")
        self.assertFalse(M._transition_is_local(pre, post, ("L",)))

        # The other half, and the one every honest receipt depends on: a change
        # that genuinely IS the whole term must still be local at the root.
        # Without this the predicate could degenerate to "reject ()" and every
        # real epoch on this organism would break -- measured, all of them
        # rewrite the whole chromosome and so record site [].
        root_pre, root_post = parse("\U0001F33F (\U0001F5A4 alpha) \U0001F91F"), parse("alpha")
        self.assertTrue(M._transition_is_local(root_pre, root_post, ()),
                        "a genuine root-level rewrite must be local at the root")

    def test_D8_a_rewritten_experiment_id_alone_is_refused(self):
        """Only the experiment id is changed -- the pair, gene, site, economy
        and genome all stay honest -- so only the tie between the id and the
        five transition fields it is derived from can catch this."""
        self.evolve()
        self.assertTrue(M.audit_morpho_autopoietic_organism(self.pdf))
        self.resign_last(lambda r: setattr(r, "experiment_id", "0" * 16))
        self.assertFalse(M.audit_morpho_autopoietic_organism(self.pdf))

    def test_D6_every_generation_reconstructs_from_the_replayed_genome(self):
        """Honest positive, re-derived independently of the audit: walking the
        chain backwards and undoing each declared transition reproduces every
        receipt's signed organism_hash, genesis included."""
        for _ in range(6):
            self.evolve()
        self.assertTrue(M.audit_morpho_autopoietic_organism(self.pdf))

        manifest = read_manifest(self.pdf)
        chain = manifest["receipt_chain"]
        self.assertGreater(len(chain), 1)
        genome = {c["gene_id"]: [c["expression"], c["expected_normal_form"]]
                  for c in manifest["chromosomes"]}

        for i in range(len(chain) - 1, -1, -1):
            rec = M.MorphoAutopoiesisReceipt.from_dict(chain[i])
            replayed = M._organism_hash_of(
                manifest["organism_id"], rec.generation, rec.parent_hash,
                M._genome_hash_of((g, e, nf) for g, (e, nf) in genome.items()),
                rec.public_key_hex, rec.feed_rate_f, rec.kill_rate_k,
                rec.archetype, rec.weisfeiler_lehman_digest)
            self.assertEqual(replayed, rec.organism_hash,
                             f"generation {rec.generation} does not reconstruct")
            if i == 0:
                break
            gene = genome[rec.gene_id]
            self.assertEqual(gene[0], rec.post_term)
            gene[0] = rec.pre_term

    def test_D7_every_stored_expression_is_canonically_spelled(self):
        """The invariant the backward replay rests on. Genesis expressions are
        written in ASCII in the source but stored as `str(parse(x))`."""
        for _ in range(3):
            self.evolve()
        for c in read_manifest(self.pdf)["chromosomes"]:
            self.assertEqual(c["expression"], str(parse(c["expression"])),
                             f"{c['gene_id']} is not stored canonically")


if __name__ == "__main__":
    unittest.main()
