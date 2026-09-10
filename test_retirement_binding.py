#!/usr/bin/env python3
"""
Regression: a retirement / re-adoption record must be accepted only when the
signature covers THE BODY THAT IS BEING USED.

The defect this pins (reproduced at origin/main 1d1908f):
`signature_message()` is `domain || record_id`, and `record_id` is carried in
the serialized record rather than recomputed from the body. So a record whose
`mode`, ATP figure, loss text or subject was rewritten under an unchanged
`record_id` still returned True from `verify_signature()`, and every admission
path in the project consumed that as authenticity.

What each section pins:

  A  positive controls: honest records verify, round-trip, admit, inoculate.
     These must keep passing; a fix that refuses everything fails here.
  B  body binding: each semantically consumed field, changed under a kept
     id + signature, must be refused.
  C  identifier handling: recomputed id with an old signature, malformed id,
     empty id. A malformed id must be a refusal, never an exception.
  D  in-place mutation after load must not survive re-verification, and no
     cached verdict may stand in for it.
  E  a re-adoption must name the retirement record and target it claims.
  F  numbers that are actually consumed must be real numbers in their declared
     range: bool is not int, NaN/Infinity is not coverage.
  G  use sites: HorizontalInoculation (mandatory), swarm broadcast, registry
     deserialization. After every refusal the registry is byte-unchanged.

Out of scope on purpose (see PR text): whether the signing key is *authorized*
to retire the subject. A valid signature by an arbitrary key remains a valid
signature; that is authorization, and it is a separate package.

Keys here are ephemeral, generated per test, never written to disk or printed.
"""
from __future__ import annotations

import copy
import json
import os
import sys
import unittest

# --- import hygiene, and why it is needed here ------------------------------
# Several generated runners prepend a HARD-CODED absolute checkout path to
# sys.path (`goedel.py:527`, `anyon_glyph.py:462`, `cross_proof.py:602,815`,
# `continuum.py:451`, `zk_glyph.py:439`, `morpho_net.py:512`). Suites that
# execute those runners in-process therefore leave that directory ahead of the
# working tree, and a later suite can silently import project modules from a
# DIFFERENT checkout. Observed while writing this file: after
# `test_security_audit`, `epistemic_immune` resolved to another clone and this
# suite tested code that was not the code under change.
#
# This does not fix that defect (it belongs with the runner/trust-root work).
# It refuses to inherit it: modules that shadow files in this directory are
# dropped so they are re-imported from here, and the resolution is asserted.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path[:1]:
    sys.path.insert(0, _HERE)
for _name, _mod in list(sys.modules.items()):
    _file = getattr(_mod, "__file__", None)
    if not _file:
        continue
    _dir = os.path.dirname(os.path.abspath(_file))
    if _dir != _HERE and os.path.exists(os.path.join(_HERE, os.path.basename(_file))):
        del sys.modules[_name]

import crypto
from controlled_forgetting import (
    RetirementRecord,
    ReAdoptionRecord,
    RetirementMode,
    EpistemicTombstoneRegistry,
    EpistemicResurrectionError,
)
from epistemic_immune import EpistemicOrganism, HorizontalInoculation
from organism import Chromosome

import controlled_forgetting as _cf
import epistemic_immune as _ei

for _module in (_cf, _ei, crypto):
    if os.path.dirname(os.path.abspath(_module.__file__)) != _HERE:
        raise ImportError(
            f"{_module.__name__} resolved to {_module.__file__}, outside the checkout "
            f"under test ({_HERE}). Refusing to report results about another tree."
        )


def _retirement(sk: str, pk: str, **over) -> RetirementRecord:
    kw = dict(
        record_id="",
        target_id="GENE-X",
        target_digest="d" * 64,
        mode=RetirementMode.ARCHIVED,
        loss_declaration="Superseded by a cheaper reduction; the original reduction path is kept in history.",
        negative_space_coverage=0.4,
        atp_gas_recovered=130,
        author_pk_hex=pk,
        signature_hex="",
    )
    kw.update(over)
    rec = RetirementRecord(**kw)
    rec.sign(sk)
    return rec


def _readoption(sk: str, pk: str, tomb: RetirementRecord, **over) -> ReAdoptionRecord:
    kw = dict(
        record_id="",
        target_id=tomb.target_id,
        retirement_record_id=tomb.record_id,
        new_evidence_claim_id="claim-fresh-001",
        justification="New grounded witness replays the retired reduction.",
        author_pk_hex=pk,
        signature_hex="",
    )
    kw.update(over)
    rec = ReAdoptionRecord(**kw)
    rec.sign(sk)
    return rec


def _tamper(rec, **body_changes):
    """Serialize, rewrite body fields, keep record_id and signature, reload.

    This is the attacker's move: the transport format carries the id, so the
    body can be replaced under it.
    """
    d = copy.deepcopy(rec.to_dict())
    d["body"].update(body_changes)
    return type(rec).from_dict(d)


def _organism(oid: str = "ORG-1") -> EpistemicOrganism:
    return EpistemicOrganism(
        organism_id=oid,
        generation=0,
        chromosomes=[Chromosome(gene_id="G-I", gene_name="Identity",
                                expression="I x", expected_normal_form="x", vital=True)],
        public_key_hex=crypto.generate_keypair()[1],
        atp_reserve=500,
    )


class RetirementBindingTest(unittest.TestCase):

    def setUp(self):
        self.sk, self.pk = crypto.generate_keypair()
        self.sk_other, self.pk_other = crypto.generate_keypair()
        self.rec = _retirement(self.sk, self.pk)

    # ---------------------------------------------------------------- A ---

    def test_A1_honest_record_verifies(self):
        self.assertTrue(self.rec.verify_signature())
        self.assertEqual(self.rec.record_id, self.rec.compute_record_id())

    def test_A2_honest_round_trip_survives(self):
        again = RetirementRecord.from_dict(self.rec.to_dict())
        self.assertEqual(again.record_id, self.rec.record_id)
        self.assertTrue(again.verify_signature())

    def test_A3_honest_readoption_admits(self):
        reg = EpistemicTombstoneRegistry()
        tomb = reg.retire("GENE-X", "d" * 64, RetirementMode.ARCHIVED,
                          "Retired for the test.", self.sk, self.pk, rule_or_pattern="x y -> y x")
        self.assertFalse(reg.is_admitted("GENE-X"))
        with self.assertRaises(EpistemicResurrectionError):
            reg.assert_viable_for_admission("GENE-X")
        reg.readopt("GENE-X", "Fresh witness.", "claim-1", self.sk, self.pk)
        self.assertTrue(reg.is_admitted("GENE-X"))
        reg.assert_viable_for_admission("GENE-X")
        self.assertTrue(tomb.verify_signature())

    def test_A4_honest_tombstone_is_absorbed(self):
        donor = EpistemicTombstoneRegistry()
        donor.retire("GENE-X", "d" * 64, RetirementMode.REFUTED,
                     "Counterexample found.", self.sk, self.pk, rule_or_pattern="x y -> y x")
        org = _organism()
        report = HorizontalInoculation.inoculate(org, donor)
        self.assertEqual(report.absorbed_tombstones_count, 1)
        self.assertEqual(report.rejected_signatures_count, 0)
        self.assertIn("GENE-X", org.tombstone_registry.tombstones)

    # ---------------------------------------------------------------- B ---

    def test_B1_mode_change_is_refused(self):
        bad = _tamper(self.rec, mode="REFUTED")
        self.assertEqual(bad.record_id, self.rec.record_id)
        self.assertNotEqual(bad.compute_record_id(), bad.record_id)
        self.assertFalse(bad.verify_signature())

    def test_B2_atp_figure_change_is_refused(self):
        self.assertFalse(_tamper(self.rec, atp_gas_recovered=999999).verify_signature())

    def test_B3_coverage_change_is_refused(self):
        self.assertFalse(_tamper(self.rec, negative_space_coverage=0.95).verify_signature())

    def test_B4_loss_declaration_change_is_refused(self):
        self.assertFalse(_tamper(self.rec, loss_declaration="nothing was lost").verify_signature())

    def test_B5_subject_change_is_refused(self):
        self.assertFalse(_tamper(self.rec, target_id="GENE-OTHER").verify_signature())
        self.assertFalse(_tamper(self.rec, target_digest="e" * 64).verify_signature())

    def test_B6_replacement_id_change_is_refused(self):
        sup = _retirement(self.sk, self.pk, mode=RetirementMode.SUPERSEDED, replacement_id="GENE-Y")
        self.assertTrue(sup.verify_signature())
        self.assertFalse(_tamper(sup, replacement_id="GENE-ATTACKER").verify_signature())

    def test_B7_timestamp_change_is_refused(self):
        self.assertFalse(_tamper(self.rec, timestamp_utc="1999-01-01T00:00:00Z").verify_signature())

    def test_B8_author_key_swap_is_refused(self):
        self.assertFalse(_tamper(self.rec, author_pk_hex=self.pk_other).verify_signature())

    def test_B9_readoption_body_change_is_refused(self):
        ro = _readoption(self.sk, self.pk, self.rec)
        self.assertTrue(ro.verify_signature())
        self.assertFalse(_tamper(ro, justification="because I said so").verify_signature())
        self.assertFalse(_tamper(ro, new_evidence_claim_id="claim-forged").verify_signature())
        self.assertFalse(_tamper(ro, retirement_record_id="f" * 64).verify_signature())

    # ---------------------------------------------------------------- C ---

    def test_C1_recomputed_id_with_old_signature_is_refused(self):
        d = copy.deepcopy(self.rec.to_dict())
        d["body"]["mode"] = "REFUTED"
        d["record_id"] = ""                      # force recomputation over the new body
        repaired = RetirementRecord.from_dict(d)
        self.assertEqual(repaired.record_id, repaired.compute_record_id())
        self.assertFalse(repaired.verify_signature())

    def test_C2_malformed_id_is_refused_not_raised(self):
        for bogus in ("zz" * 32, "abc", "", " " * 64, "0x" + "a" * 62):
            d = copy.deepcopy(self.rec.to_dict())
            d["body"]["mode"] = "REFUTED"        # keep it a forgery, not a re-derivation
            d["record_id"] = bogus
            try:
                rec = RetirementRecord.from_dict(d)
            except (ValueError, TypeError):
                continue                          # refused at the door is also a refusal
            self.assertFalse(rec.verify_signature(), f"malformed id accepted: {bogus!r}")

    def test_C3_foreign_key_is_refused(self):
        rec = _retirement(self.sk_other, self.pk)   # signed by a key that is not the named author
        self.assertFalse(rec.verify_signature())

    # ---------------------------------------------------------------- D ---

    def test_D1_mutation_after_load_is_refused(self):
        loaded = RetirementRecord.from_dict(self.rec.to_dict())
        self.assertTrue(loaded.verify_signature())
        loaded.mode = RetirementMode.REFUTED         # direct field write, no re-signing
        self.assertFalse(loaded.verify_signature())
        loaded.mode = RetirementMode.ARCHIVED
        self.assertTrue(loaded.verify_signature())   # and the honest body verifies again
        loaded.atp_gas_recovered = 10 ** 6
        self.assertFalse(loaded.verify_signature())

    def test_D2_mutated_record_does_not_admit_or_spread(self):
        reg = EpistemicTombstoneRegistry()
        reg.retire("GENE-X", "d" * 64, RetirementMode.ARCHIVED, "Retired.", self.sk, self.pk)
        reg.readopt("GENE-X", "Fresh witness.", "claim-1", self.sk, self.pk)
        self.assertTrue(reg.is_admitted("GENE-X"))
        reg.readoptions["GENE-X"].justification = "rewritten after signing"
        self.assertFalse(reg.is_admitted("GENE-X"))
        with self.assertRaises(EpistemicResurrectionError):
            reg.assert_viable_for_admission("GENE-X")

    # ---------------------------------------------------------------- E ---

    def test_E1_readoption_must_name_the_registered_retirement(self):
        reg = EpistemicTombstoneRegistry()
        reg.retire("GENE-X", "d" * 64, RetirementMode.ARCHIVED, "Retired.", self.sk, self.pk)
        other = _retirement(self.sk, self.pk, target_id="GENE-X", loss_declaration="A different retirement.")
        stray = _readoption(self.sk, self.pk, other)      # honestly signed, wrong retirement
        self.assertTrue(stray.verify_signature())
        reg.readoptions["GENE-X"] = stray
        self.assertFalse(reg.is_admitted("GENE-X"))

    def test_E2_readoption_for_another_target_does_not_admit(self):
        reg = EpistemicTombstoneRegistry()
        tomb = reg.retire("GENE-X", "d" * 64, RetirementMode.ARCHIVED, "Retired.", self.sk, self.pk)
        alien = _readoption(self.sk, self.pk, tomb, target_id="GENE-Z")
        self.assertTrue(alien.verify_signature())
        reg.readoptions["GENE-X"] = alien                  # filed under the wrong key
        self.assertFalse(reg.is_admitted("GENE-X"))

    def test_E3_retire_after_readoption_closes_the_surface_again(self):
        reg = EpistemicTombstoneRegistry()
        reg.retire("GENE-X", "d" * 64, RetirementMode.ARCHIVED, "Retired.", self.sk, self.pk)
        reg.readopt("GENE-X", "Fresh witness.", "claim-1", self.sk, self.pk)
        self.assertTrue(reg.is_admitted("GENE-X"))
        reg.retire("GENE-X", "d" * 64, RetirementMode.REFUTED, "Refuted again.", self.sk, self.pk)
        self.assertFalse(reg.is_admitted("GENE-X"))

    # ---------------------------------------------------------------- F ---

    def test_F1_non_finite_coverage_is_refused(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError, msg=f"accepted coverage {bad}"):
                _retirement(self.sk, self.pk, negative_space_coverage=bad)

    def test_F2_out_of_range_coverage_is_refused(self):
        for bad in (-0.01, 1.5):
            with self.assertRaises(ValueError, msg=f"accepted coverage {bad}"):
                _retirement(self.sk, self.pk, negative_space_coverage=bad)

    def test_F3_bool_is_not_an_atp_figure(self):
        with self.assertRaises((ValueError, TypeError)):
            _retirement(self.sk, self.pk, atp_gas_recovered=True)

    def test_F4_negative_atp_recovery_is_refused(self):
        with self.assertRaises(ValueError):
            _retirement(self.sk, self.pk, atp_gas_recovered=-1)

    def test_F5_declared_range_endpoints_are_accepted(self):
        for good in (0.0, 1.0, 0.5):
            rec = _retirement(self.sk, self.pk, negative_space_coverage=good)
            self.assertTrue(rec.verify_signature())
        self.assertTrue(_retirement(self.sk, self.pk, atp_gas_recovered=0).verify_signature())

    def test_F6_malformed_number_in_transport_is_refused(self):
        for bad in ("0.4", None, [0.4]):
            d = copy.deepcopy(self.rec.to_dict())
            d["body"]["negative_space_coverage"] = bad
            with self.assertRaises((ValueError, TypeError), msg=f"accepted {bad!r}"):
                RetirementRecord.from_dict(d)

    # ---------------------------------------------------------------- G ---

    def test_G1_inoculation_rejects_a_rewritten_tombstone(self):
        donor = EpistemicTombstoneRegistry()
        donor.retire("GENE-X", "d" * 64, RetirementMode.ARCHIVED, "Honest retirement.",
                     self.sk, self.pk, rule_or_pattern="x y -> y x")
        donor.tombstones["GENE-X"] = _tamper(donor.tombstones["GENE-X"],
                                             mode="REFUTED", atp_gas_recovered=999999)
        org = _organism()
        before = json.dumps(org.tombstone_registry.to_dict(), sort_keys=True)
        report = HorizontalInoculation.inoculate(org, donor)
        self.assertEqual(report.absorbed_tombstones_count, 0)
        self.assertEqual(report.rejected_signatures_count, 1)
        self.assertEqual(report.pruned_search_space_volume, 0.0)
        self.assertNotIn("GENE-X", org.tombstone_registry.tombstones)
        self.assertEqual(before, json.dumps(org.tombstone_registry.to_dict(), sort_keys=True))

    def test_G2_inoculation_rejects_a_rewritten_readoption(self):
        donor = EpistemicTombstoneRegistry()
        tomb = donor.retire("GENE-X", "d" * 64, RetirementMode.ARCHIVED, "Honest retirement.",
                            self.sk, self.pk)
        donor.readopt("GENE-X", "Honest re-adoption.", "claim-1", self.sk, self.pk)
        donor.readoptions["GENE-X"] = _tamper(donor.readoptions["GENE-X"],
                                              justification="rewritten after signing")
        org = _organism()
        HorizontalInoculation.inoculate(org, donor)
        self.assertNotIn("GENE-X", org.tombstone_registry.readoptions)
        self.assertTrue(tomb.verify_signature())

    def test_G7_inoculation_refuses_a_readoption_for_another_retirement(self):
        """An honestly signed re-adoption still has to name the retirement held here.

        Distinct from G2: nothing is rewritten, so the signature binding cannot
        catch this one. Only the link check can.
        """
        donor = EpistemicTombstoneRegistry()
        donor.retire("GENE-X", "d" * 64, RetirementMode.ARCHIVED, "Honest retirement.",
                     self.sk, self.pk)
        donor.readopt("GENE-X", "Honest re-adoption.", "claim-1", self.sk, self.pk)

        org = _organism()
        # The recipient holds its own, differently-worded retirement of the same
        # subject, so the donor's re-adoption names an id this organism never issued.
        org.tombstone_registry.retire("GENE-X", "d" * 64, RetirementMode.REFUTED,
                                      "A different retirement of the same subject.",
                                      self.sk, self.pk)
        self.assertTrue(donor.readoptions["GENE-X"].verify_signature())
        HorizontalInoculation.inoculate(org, donor)
        self.assertNotIn("GENE-X", org.tombstone_registry.readoptions)
        self.assertFalse(org.tombstone_registry.is_admitted("GENE-X"))

    def test_G3_swarm_broadcast_refuses_a_rewritten_tombstone(self):
        import epistemic_swarm as sw
        donor = EpistemicTombstoneRegistry()
        donor.retire("GENE-X", "d" * 64, RetirementMode.ARCHIVED, "Honest retirement.", self.sk, self.pk)
        bad = _tamper(donor.tombstones["GENE-X"], mode="REFUTED")

        membrane = sw.SwarmMembrane(grid_width=6, grid_height=6)
        for i in range(2):
            org = _organism(f"ORG-{i}")
            st = sw.SwarmOrganismState(organism_id=org.organism_id, x=i, y=0, heading=(1, 0), is_alive=True)
            membrane.add_organism(org, st, *crypto.generate_keypair()[::-1])
        before = {oid: json.dumps(o.tombstone_registry.to_dict(), sort_keys=True)
                  for oid, o in membrane.organisms.items()}
        with self.assertRaises(ValueError):
            sw.SwarmInoculationCascade.broadcast_tombstone(membrane, "ORG-0", bad)
        after = {oid: json.dumps(o.tombstone_registry.to_dict(), sort_keys=True)
                 for oid, o in membrane.organisms.items()}
        self.assertEqual(before, after)

    def test_G4_registry_load_refuses_a_rewritten_tombstone(self):
        reg = EpistemicTombstoneRegistry()
        reg.retire("GENE-X", "d" * 64, RetirementMode.ARCHIVED, "Honest retirement.", self.sk, self.pk)
        d = reg.to_dict()
        d["tombstones"]["GENE-X"]["body"]["mode"] = "REFUTED"
        with self.assertRaises(ValueError):
            EpistemicTombstoneRegistry.from_dict(d)

    def test_G5_registry_load_refuses_a_key_that_is_not_the_subject(self):
        reg = EpistemicTombstoneRegistry()
        reg.retire("GENE-X", "d" * 64, RetirementMode.ARCHIVED, "Honest retirement.", self.sk, self.pk)
        d = reg.to_dict()
        d["tombstones"]["GENE-MOVED"] = d["tombstones"].pop("GENE-X")
        with self.assertRaises(ValueError):
            EpistemicTombstoneRegistry.from_dict(d)

    def test_G6_honest_registry_round_trip_still_loads(self):
        reg = EpistemicTombstoneRegistry()
        reg.retire("GENE-X", "d" * 64, RetirementMode.ARCHIVED, "Honest retirement.", self.sk, self.pk)
        reg.readopt("GENE-X", "Honest re-adoption.", "claim-1", self.sk, self.pk)
        back = EpistemicTombstoneRegistry.from_dict(reg.to_dict())
        self.assertTrue(back.is_admitted("GENE-X"))
        self.assertEqual(json.dumps(reg.to_dict(), sort_keys=True),
                         json.dumps(back.to_dict(), sort_keys=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
