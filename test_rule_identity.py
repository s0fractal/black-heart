#!/usr/bin/env python3
"""
Regression: a rule name is not a rule, and a refutation is not a prohibition.

Two measured defects, one question.

`mycelium.verify_rewrite_rule` ended in `elif rule_name in ALLOWED_MUTATION_RULES:
return True`, so for the three exploratory rules any pre/post pair verified:

    MUTATION_OPERAND_SWAP       '🖤 🤍' -> '🌿 🌿 🌿'    True
    MUTATION_OPERAND_SWAP       'x'    -> 'y'         True   (no application to swap)
    MUTATION_CONSTANT_COLLAPSE  'x'    -> '🌿 (🌿 🌿)'  True
    MUTATION_CHILD_SWAP         anything -> anything   True

The rule name on a signed warrant was therefore decorative, while a consumer
substituted its pre/post pair into a genome.

The tombstone side had the same shape. `target_digest` is documented as the
"content hash of retired subject (I1)" and held the digest of the subject's
NAME. Measured: a refutation of 🖤 🤍 against 🖤 retired the label 'K I (S K)',
whose digest is sha256 of that text; the gate then refused the label, permitted
🖤 🤍 (the term actually refuted), permitted 'K I ( S K )' (the same text spaced
differently) and refused 'K I (S K) ' (a trailing space, because the gate strips
the candidate and not the key). Two different rewrites filed under one label
silently overwrote each other, leaving one tombstone and two claims.

What the sections pin:

  A  the exploratory rules are replayed, against the same definitions
     `metamorphosis` uses, and a warrant carrying an invented rewrite fails
  B  an identity addresses terms, not spellings, and needs both ends
  C  records carrying no identity keep their exact body, id and signature; a
     second rewrite cannot take a name that already holds another
  D  the scoped question: refuted against THIS reference, against ANOTHER one,
     or not measured at all -- and only the first prohibits
  E  the aggregate runner refuses a suite module loaded from another checkout
     (its origin only, not the dependency closure)
  F  a record is evidence only after authentication for its own slot and a
     domain check of its identity; anything else is UNTRUSTED_EVIDENCE, which
     is neither prohibition nor permission

The predicate, in full: a tombstone that carries an identity says which
candidate diverged from which reference on which input. It does not say the
candidate is invalid, and it does not say the label denotes it.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest

# Same import guard, and same reason, as test_counterexample_producer.py.
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

import crypto
import glyph
import controlled_forgetting as cf
import epistemic_immune as ei
import mycelium
from controlled_forgetting import (
    EpistemicTombstoneRegistry, RetirementMode, RetirementRecord, RuleIdentity,
    RULE_IDENTITY_PROFILE,
)
from epistemic_immune import (
    CounterexampleMetabolism, EpistemicOrganism, MetabolismStatus,
    RefutationScope, ResurrectionDefense, observe_divergence,
)
from mycelium import Warrant, verify_rewrite_rule
from organism import Chromosome

for _m in (cf, ei, mycelium):
    if os.path.dirname(os.path.abspath(_m.__file__)) != _HERE:
        raise ImportError(f"{_m.__name__} resolved to {_m.__file__}, outside {_HERE}")

# The measured divergence reused from S4b-2.
PARENT, CANDIDATE = "🖤", "🖤 🤍"
INPUT = "🤍 (🖤 🤍)"


class ExploratoryRuleTest(unittest.TestCase):
    """Section A: the rule name has to earn the pair it names."""

    def test_A1_a_genuine_transposition_verifies(self):
        for pre, post in (("🖤 🤍", "🤍 🖤"),
                          ("🌿 a b", "b (🌿 a)"),
                          ("🌿 a b", "a 🌿 b")):
            with self.subTest(pre=pre, post=post):
                self.assertTrue(verify_rewrite_rule("MUTATION_OPERAND_SWAP", pre, post))
                self.assertTrue(verify_rewrite_rule("MUTATION_CHILD_SWAP", pre, post))

    def test_A2_a_genuine_collapse_verifies(self):
        for pre, post in (("🤍 🤍", "🖤 🤍"), ("🤍 🤍", "🤍 🖤"), ("🌿 a b", "🖤 b")):
            with self.subTest(pre=pre, post=post):
                self.assertTrue(
                    verify_rewrite_rule("MUTATION_CONSTANT_COLLAPSE", pre, post))

    def test_A3_an_invented_pair_is_refused(self):
        cases = [
            ("MUTATION_OPERAND_SWAP", "🖤 🤍", "🌿 🌿 🌿"),
            ("MUTATION_OPERAND_SWAP", "x", "y"),
            ("MUTATION_OPERAND_SWAP", "🖤 🤍", "🖤 🤍"),
            # A rewrite that changes nothing is not a rewrite. Both witnesses
            # were found by running the mutant that drops the no-op guard:
            # swapping the children of `a a`, and collapsing a subterm that is
            # already K, each leave the term alone.
            ("MUTATION_OPERAND_SWAP", "a a", "a a"),
            ("MUTATION_CONSTANT_COLLAPSE", "🖤 🤍", "🖤 🤍"),
            ("MUTATION_CHILD_SWAP", "anything", "anything else"),
            ("MUTATION_CONSTANT_COLLAPSE", "x", "🌿 (🌿 🌿)"),
            ("MUTATION_CONSTANT_COLLAPSE", "🤍 🤍", "🌿 🤍"),
        ]
        for rule, pre, post in cases:
            with self.subTest(rule=rule, pre=pre, post=post):
                self.assertFalse(verify_rewrite_rule(rule, pre, post))

    def test_A4_the_algebraic_rules_are_unchanged(self):
        self.assertTrue(verify_rewrite_rule("I x -> x", "🤍 x", "x"))
        self.assertFalse(verify_rewrite_rule("I x -> x", "🤍 x", "y"))
        self.assertTrue(verify_rewrite_rule("K x y -> x", "🖤 x y", "x"))
        self.assertFalse(verify_rewrite_rule("not a rule", "x", "x"))

    def test_A5_a_warrant_carrying_an_invented_rewrite_fails(self):
        """The measured consequence: an unearned rule name reached a consumer."""
        sk, _ = crypto.generate_keypair()

        def warrant(pre, post):
            w = Warrant(
                warrant_id="", rule_name="MUTATION_OPERAND_SWAP", pre_pattern=pre,
                post_pattern=post, delta_atp=-3, delta_size=-1,
                fixtures_fingerprint="fp", author_pk_hex="", signature_hex="")
            w.author_pk_hex = crypto.public_key_from_secret(bytes.fromhex(sk)).hex()
            w.warrant_id = Warrant.derive_id(w.rule_name, pre, post, "fp",
                                             w.epistemic_grade)
            w.signature_hex = crypto.sign_bytes(
                bytes.fromhex(sk), w.canonical_bytes_for_signing()).hex()
            return w

        invented = warrant("🖤 🤍", "🌿 🌿 🌿")
        self.assertTrue(crypto.verify_bytes(
            bytes.fromhex(invented.author_pk_hex),
            invented.canonical_bytes_for_signing(),
            bytes.fromhex(invented.signature_hex)),
            "the signature is genuine; the rewrite is what fails")
        self.assertFalse(invented.verify())
        self.assertTrue(warrant("🖤 🤍", "🤍 🖤").verify())


class RuleIdentityTest(unittest.TestCase):
    """Section B: what an identity addresses."""

    def identity(self, label="simplify", ref=PARENT, cand=CANDIDATE, inp=INPUT):
        return RuleIdentity.from_terms(label=label, reference_expr=ref,
                                       candidate_expr=cand, input_expr=inp)

    def test_B1_terms_not_spellings(self):
        self.assertEqual(self.identity().digest(),
                         self.identity(ref="(🖤)", cand="🖤  🤍",
                                       inp="(🤍 (🖤 🤍))").digest())

    def test_B2_a_different_rewrite_is_a_different_identity(self):
        base = self.identity().digest()
        for kw in ({"ref": "🤍"}, {"cand": "🌿"}, {"inp": "x"}, {"label": "other"}):
            with self.subTest(**kw):
                self.assertNotEqual(base, self.identity(**kw).digest())

    def test_B3_both_ends_are_required_to_match(self):
        ident = self.identity()
        self.assertTrue(ident.addresses(CANDIDATE, PARENT))
        self.assertFalse(ident.addresses(CANDIDATE, "🤍"))
        self.assertFalse(ident.addresses("🌿", PARENT))
        self.assertFalse(ident.addresses(PARENT, CANDIDATE))

    def test_B4_an_endpoint_that_is_not_a_term_has_no_identity(self):
        for kw in ({"ref": ""}, {"cand": " "}, {"inp": "(("}):
            with self.subTest(**kw):
                with self.assertRaises(Exception):
                    self.identity(**kw)
        self.assertFalse(self.identity().addresses("", PARENT))

    def test_B5_the_encoding_is_prefix_free(self):
        """
        A label that ends where the next field begins must not collide.

        Measured limit of this test, recorded rather than implied: it burns the
        concatenation, not the length prefixes alone. The encoding carries both
        a field name and a byte length per field, and removing only the lengths
        leaves the names as delimiters, which no pair I could construct defeats.
        The lengths are defense in depth over the names.
        """
        a = RuleIdentity(label="a:", reference_address="b",
                         candidate_address="c", input_address="d")
        b = RuleIdentity(label="a", reference_address=":b",
                         candidate_address="c", input_address="d")
        self.assertNotEqual(a.digest(), b.digest())
        self.assertNotEqual(
            RuleIdentity(label="x", reference_address="y",
                         candidate_address="z", input_address="w").digest(),
            RuleIdentity(label="xy", reference_address="",
                         candidate_address="z", input_address="w").digest())

    def test_B6_an_unknown_profile_is_refused_not_reinterpreted(self):
        d = self.identity().to_dict()
        self.assertEqual(d["profile"], RULE_IDENTITY_PROFILE)
        self.assertEqual(RuleIdentity.from_dict(d), self.identity())
        d["profile"] = "forgetting.rule-identity.v99"
        with self.assertRaises(ValueError):
            RuleIdentity.from_dict(d)


class RetirementRecordIdentityTest(unittest.TestCase):
    """Section C: history is preserved, and a name holds one rewrite."""

    LEGACY_BODY = dict(
        record_id="", target_id="subject-A", target_digest="d" * 64,
        mode=RetirementMode.REFUTED, loss_declaration="a loss",
        negative_space_coverage=0.5, atp_gas_recovered=25,
        author_pk_hex="ab" * 32, signature_hex="",
        timestamp_utc="2026-09-11T00:00:00Z")
    # Computed by running the module as it stood at origin/main c464e9a.
    LEGACY_RECORD_ID = "e2c9cb751a45f2ef95388eac1f2e5de5b46bcd8ae2b0e9a25a04983be1a3f43c"

    def setUp(self):
        self.sk, self.pk = crypto.generate_keypair()
        self.identity = RuleIdentity.from_terms("simplify", PARENT, CANDIDATE, INPUT)

    def test_C1_a_record_without_an_identity_is_byte_identical(self):
        """No historical record is re-signed to fit a field it never had."""
        record = RetirementRecord(**self.LEGACY_BODY)
        self.assertEqual(record.compute_record_id(), self.LEGACY_RECORD_ID)
        self.assertNotIn("rule_identity", record.body_dict())
        self.assertEqual(
            sorted(record.body_dict()),
            ["atp_gas_recovered", "author_pk_hex", "loss_declaration", "mode",
             "negative_space_coverage", "replacement_id", "target_digest",
             "target_id", "timestamp_utc"])

    def test_C2_an_identity_changes_the_body_it_is_carried_in(self):
        without = RetirementRecord(**self.LEGACY_BODY)
        with_id = RetirementRecord(**dict(self.LEGACY_BODY, rule_identity=self.identity))
        self.assertNotEqual(without.compute_record_id(), with_id.compute_record_id())
        self.assertIn("rule_identity", with_id.body_dict())

    def test_C3_a_carried_identity_signs_verifies_and_round_trips(self):
        registry = EpistemicTombstoneRegistry()
        record = registry.retire("simplify", "d" * 64, RetirementMode.REFUTED,
                                 "a loss", self.sk, self.pk,
                                 rule_identity=self.identity)
        self.assertTrue(record.verify_signature())
        self.assertTrue(record.is_admissible_for("simplify"))
        revived = RetirementRecord.from_dict(json.loads(json.dumps(record.to_dict())))
        self.assertEqual(revived.rule_identity, self.identity)
        self.assertTrue(revived.verify_signature())

    def test_C4_a_name_cannot_hold_two_rewrites(self):
        registry = EpistemicTombstoneRegistry()
        registry.retire("simplify", "d" * 64, RetirementMode.REFUTED, "loss",
                        self.sk, self.pk, rule_identity=self.identity)
        other = RuleIdentity.from_terms("simplify", "🤍", "🖤", "x")
        with self.assertRaises(ValueError) as caught:
            registry.retire("simplify", "d" * 64, RetirementMode.REFUTED, "loss",
                            self.sk, self.pk, rule_identity=other)
        self.assertIn("different rewrite", str(caught.exception))
        self.assertEqual(registry.tombstones["simplify"].rule_identity, self.identity)

    def test_C5_the_same_rewrite_may_be_retired_again(self):
        registry = EpistemicTombstoneRegistry()
        registry.retire("simplify", "d" * 64, RetirementMode.REFUTED, "loss",
                        self.sk, self.pk, rule_identity=self.identity)
        again = RuleIdentity.from_terms("simplify", "(🖤)", "🖤  🤍", INPUT)
        registry.retire("simplify", "d" * 64, RetirementMode.REFUTED, "loss again",
                        self.sk, self.pk, rule_identity=again)
        self.assertEqual(len(registry.tombstones), 1)

    def test_C6_a_legacy_slot_does_not_block_a_new_identity(self):
        """Nothing historical becomes unusable because it predates identities."""
        registry = EpistemicTombstoneRegistry()
        registry.retire("simplify", "d" * 64, RetirementMode.REFUTED, "loss",
                        self.sk, self.pk)
        self.assertIsNone(registry.tombstones["simplify"].rule_identity)
        registry.retire("simplify", "d" * 64, RetirementMode.REFUTED, "loss",
                        self.sk, self.pk, rule_identity=self.identity)
        self.assertEqual(registry.tombstones["simplify"].rule_identity, self.identity)


class ScopedRefutationTest(unittest.TestCase):
    """Section D: what a measured refutation prohibits, and what it does not."""

    def setUp(self):
        self.sk, self.pk = crypto.generate_keypair()
        self.org = EpistemicOrganism(
            organism_id="O", generation=0,
            chromosomes=[Chromosome(gene_id="G1", gene_name="n", expression="🖤",
                                    expected_normal_form="🖤", vital=False)],
            public_key_hex=self.pk, atp_reserve=500)
        obs = observe_divergence(PARENT, CANDIDATE, INPUT)
        self.outcome = CounterexampleMetabolism.metabolize_counterexample(
            organism=self.org, gene_id="G1", rule_name="K I (S K)",
            parent_term=PARENT, candidate_term=CANDIDATE, input_fixture=INPUT,
            expected_norm=obs.parent_output, actual_norm=obs.candidate_output,
            atp_cost=obs.atp_required, secret_key_hex=self.sk, public_key_hex=self.pk)
        self.assertTrue(self.outcome.granted(), self.outcome.verdict.reason)
        self.registry = self.org.tombstone_registry

    def scope(self, candidate, reference):
        return ResurrectionDefense.refuted_for(self.registry, candidate, reference)

    def test_D1_the_measured_pair_is_prohibited(self):
        report = self.scope(CANDIDATE, PARENT)
        self.assertEqual(report.scope, RefutationScope.REFUTED_FOR_REFERENCE)
        self.assertTrue(report.prohibits())
        self.assertEqual(report.target_id, "K I (S K)")
        self.assertEqual(report.record_id, self.outcome.retirement.record_id)

    def test_D2_spelling_does_not_decide_it(self):
        self.assertTrue(self.scope("🖤  🤍", "(🖤)").prohibits())

    def test_D3_another_reference_is_not_prohibited(self):
        report = self.scope(CANDIDATE, "🤍")
        self.assertEqual(report.scope, RefutationScope.REFUTED_FOR_ANOTHER_REFERENCE)
        self.assertFalse(report.prohibits())
        self.assertIn("says nothing about the reference asked about", report.detail)

    def test_D4_an_unmeasured_pair_reports_as_unmeasured(self):
        # Not (CANDIDATE, anything): the same candidate against another
        # reference is its own scope, pinned in D3.
        for cand, ref in (("🌿", PARENT), ("K I (S K)", PARENT), ("🌿 🖤", PARENT)):
            with self.subTest(candidate=cand, reference=ref):
                report = self.scope(cand, ref)
                self.assertEqual(report.scope, RefutationScope.NO_MEASURED_REFUTATION)
                self.assertFalse(report.prohibits())

    def test_D5_the_identity_is_bound_to_the_record_it_travels_in(self):
        record = self.outcome.retirement
        self.assertEqual(record.rule_identity, self.outcome.rule_identity)
        self.assertTrue(record.verify_signature())
        record.rule_identity = RuleIdentity.from_terms("K I (S K)", "🤍", "🖤", "x")
        self.assertFalse(record.verify_signature(),
                         "the identity is inside the signed body")
        self.assertFalse(self.scope(CANDIDATE, PARENT).prohibits())

    def test_D6_a_readopted_subject_stops_prohibiting(self):
        self.assertTrue(self.scope(CANDIDATE, PARENT).prohibits())
        self.registry.readopt(
            target_id="K I (S K)", justification="new evidence",
            new_evidence_claim_id="c" * 64,
            author_sk_hex=self.sk, author_pk_hex=self.pk)
        self.assertTrue(self.registry.is_admitted("K I (S K)"))
        self.assertEqual(self.scope(CANDIDATE, PARENT).scope,
                         RefutationScope.NO_MEASURED_REFUTATION)

    def test_D7_the_label_gate_is_deliberately_unchanged(self):
        """
        It answers a coarser question by string identity, and still does. What
        the measurement changed is that a precise question now exists.
        """
        self.assertFalse(ResurrectionDefense.preflight_check(
            self.registry, "K I (S K)")[0])
        self.assertTrue(ResurrectionDefense.preflight_check(
            self.registry, CANDIDATE)[0])
        self.assertTrue(ResurrectionDefense.preflight_check(
            self.registry, "K I ( S K )")[0])

    def test_D8_a_colliding_label_leaves_the_organism_untouched(self):
        before = (len(self.org.claims), len(self.registry.tombstones),
                  self.org.atp_reserve, self.org.total_bounties_reclaimed)
        obs = observe_divergence("🤍", "🖤", "x")
        outcome = CounterexampleMetabolism.metabolize_counterexample(
            organism=self.org, gene_id="G1", rule_name="K I (S K)",
            parent_term="🤍", candidate_term="🖤", input_fixture="x",
            expected_norm=obs.parent_output, actual_norm=obs.candidate_output,
            atp_cost=obs.atp_required, secret_key_hex=self.sk, public_key_hex=self.pk)
        self.assertEqual(outcome.status, MetabolismStatus.SUBJECT_COLLISION)
        self.assertFalse(outcome.granted())
        self.assertIsNotNone(outcome.collision)
        self.assertEqual((len(self.org.claims), len(self.registry.tombstones),
                          self.org.atp_reserve, self.org.total_bounties_reclaimed),
                         before)


class UntrustedEvidenceTest(unittest.TestCase):
    """
    Section F: a record is evidence only after it is authenticated for its slot.

    Round 1 of review found `refuted_for` skipping admitted records and trusting
    every other one. But `is_admitted` is False both for a genuine retirement
    and for a record it refuses to trust, so each of these became a measured
    refutation with `prohibits() == True`, reproduced on 7e90514:

        identity replaced, old signature kept   -> REFUTED_FOR_REFERENCE (even I vs I)
        signature zeroed                        -> REFUTED_FOR_REFERENCE
        genuine record moved to another slot    -> REFUTED_FOR_REFERENCE, wrong slot named
        unknown profile, correctly re-signed    -> REFUTED_FOR_REFERENCE under v1 rules

    Every case keeps the authentic positive alongside it, so an implementation
    that simply refuses all evidence fails here too.
    """

    def setUp(self):
        self.sk, self.pk = crypto.generate_keypair()
        self.org = EpistemicOrganism(
            organism_id="O", generation=0,
            chromosomes=[Chromosome(gene_id="G1", gene_name="n", expression="\U0001f5a4",
                                    expected_normal_form="\U0001f5a4", vital=False)],
            public_key_hex=self.pk, atp_reserve=500)
        obs = observe_divergence(PARENT, CANDIDATE, INPUT)
        out = CounterexampleMetabolism.metabolize_counterexample(
            organism=self.org, gene_id="G1", rule_name="K I (S K)",
            parent_term=PARENT, candidate_term=CANDIDATE, input_fixture=INPUT,
            expected_norm=obs.parent_output, actual_norm=obs.candidate_output,
            atp_cost=obs.atp_required, secret_key_hex=self.sk, public_key_hex=self.pk)
        self.assertTrue(out.granted(), out.verdict.reason)
        self.registry = self.org.tombstone_registry
        self.record = out.retirement

    def scope(self, candidate=CANDIDATE, reference=PARENT):
        return ResurrectionDefense.refuted_for(self.registry, candidate, reference)

    def snapshot(self):
        return (json.dumps({k: v.to_dict() for k, v in self.registry.tombstones.items()},
                           sort_keys=True, default=str),
                json.dumps({k: v.to_dict() for k, v in self.registry.readoptions.items()},
                           sort_keys=True, default=str))

    def assertUntrusted(self, report, slot):
        self.assertEqual(report.scope, RefutationScope.UNTRUSTED_EVIDENCE, report.detail)
        self.assertFalse(report.prohibits())
        self.assertIn(slot, report.untrusted_slots)

    def test_F0_the_authentic_record_still_prohibits(self):
        report = self.scope()
        self.assertEqual(report.scope, RefutationScope.REFUTED_FOR_REFERENCE)
        self.assertTrue(report.prohibits())
        self.assertEqual(report.untrusted_slots, ())

    def test_F1_an_identity_changed_without_resigning_is_untrusted(self):
        self.record.rule_identity = RuleIdentity.from_terms("K I (S K)", "\U0001f90d", "\U0001f90d", "x")
        self.assertFalse(self.record.verify_signature())
        self.assertUntrusted(self.scope("\U0001f90d", "\U0001f90d"), "K I (S K)")
        self.assertUntrusted(self.scope(), "K I (S K)")

    def test_F2_a_corrupt_signature_is_untrusted(self):
        self.record.signature_hex = "00" * 64
        self.assertUntrusted(self.scope(), "K I (S K)")

    def test_F3_a_record_in_someone_elses_slot_is_untrusted(self):
        self.registry.tombstones = {"wrong-slot": self.record}
        self.assertTrue(self.record.verify_signature())
        report = self.scope()
        self.assertUntrusted(report, "wrong-slot")
        self.assertIsNone(report.target_id, "no evidence may be attributed to a false slot")

    def test_F4_numbers_out_of_domain_are_untrusted(self):
        object.__setattr__(self.record, "negative_space_coverage", 2.0)
        self.assertUntrusted(self.scope(), "K I (S K)")

    def test_F5_an_unknown_profile_is_untrusted_even_when_signed(self):
        """Signature validity and domain validity are separate questions."""
        from dataclasses import replace
        self.record.rule_identity = replace(self.record.rule_identity,
                                            profile="forgetting.rule-identity.v999")
        self.record.sign(self.sk)
        self.assertTrue(self.record.verify_signature())
        self.assertFalse(self.record.is_admissible_for("K I (S K)"))
        self.assertUntrusted(self.scope(), "K I (S K)")

    def test_F6_every_identity_address_must_be_in_profile(self):
        """input_address too, though matching reads only the other two."""
        from dataclasses import replace
        for field_name, bad in (("reference_address", "deadbeef" * 8),
                                ("candidate_address", "glyph.term.v1:" + "0" * 64),
                                ("input_address", "not-an-address"),
                                ("input_address", "glyph.term.v2:" + "0" * 63)):
            with self.subTest(field=field_name, value=bad):
                self.setUp()
                self.record.rule_identity = replace(self.record.rule_identity,
                                                    **{field_name: bad})
                self.record.sign(self.sk)
                self.assertTrue(self.record.verify_signature())
                self.assertFalse(self.record.rule_identity.has_valid_domain())
                self.assertUntrusted(self.scope(), "K I (S K)")

    def test_F7_field_types_are_checked_before_addresses_are_read(self):
        from dataclasses import replace
        for field_name, bad in (("label", 7), ("profile", None),
                                ("candidate_address", b"glyph.term.v2:" + b"0" * 64)):
            with self.subTest(field=field_name):
                ident = replace(self.record.rule_identity, **{field_name: bad})
                self.assertFalse(ident.has_valid_domain())
                self.assertFalse(ident.addresses(CANDIDATE, PARENT))

    def test_F8_the_live_object_and_the_transport_agree(self):
        from dataclasses import replace
        bad = replace(self.record.rule_identity, profile="forgetting.rule-identity.v999")
        with self.assertRaises(ValueError):
            RuleIdentity.from_dict(bad.to_dict())
        with self.assertRaises(ValueError):
            bad.validate_domain()
        with self.assertRaises(ValueError):
            self.registry.retire("another", "d" * 64, RetirementMode.REFUTED, "loss",
                                 self.sk, self.pk, rule_identity=bad)
        self.assertNotIn("another", self.registry.tombstones)

    def test_F9_another_reference_still_reports_its_own_scope(self):
        report = self.scope(CANDIDATE, "\U0001f90d")
        self.assertEqual(report.scope, RefutationScope.REFUTED_FOR_ANOTHER_REFERENCE)
        self.assertFalse(report.prohibits())

    def test_F10_untrusted_outranks_another_reference(self):
        """A record nobody can read might have been about this very pair."""
        self.registry.tombstones["forged"] = RetirementRecord.from_dict(
            json.loads(json.dumps(self.record.to_dict())))
        self.registry.tombstones["forged"].signature_hex = "00" * 64
        report = self.scope(CANDIDATE, "\U0001f90d")
        self.assertUntrusted(report, "forged")

    def test_F11_an_authentic_match_is_reported_with_the_untrusted_list_complete(self):
        self.registry.tombstones["forged"] = RetirementRecord.from_dict(
            json.loads(json.dumps(self.record.to_dict())))
        self.registry.tombstones["forged"].signature_hex = "00" * 64
        report = self.scope()
        self.assertTrue(report.prohibits())
        self.assertEqual(report.untrusted_slots, ("forged",))

    def test_F12_a_valid_readoption_still_suppresses_a_valid_retirement(self):
        self.registry.readopt(target_id="K I (S K)", justification="new evidence",
                              new_evidence_claim_id="c" * 64,
                              author_sk_hex=self.sk, author_pk_hex=self.pk)
        self.assertEqual(self.scope().scope, RefutationScope.NO_MEASURED_REFUTATION)

    def test_F13_an_invalid_readoption_does_not_suppress(self):
        self.registry.readopt(target_id="K I (S K)", justification="new evidence",
                              new_evidence_claim_id="c" * 64,
                              author_sk_hex=self.sk, author_pk_hex=self.pk)
        self.registry.readoptions["K I (S K)"].signature_hex = "00" * 64
        self.assertTrue(self.scope().prohibits())

    def test_F14_the_query_changes_nothing(self):
        self.registry.tombstones["forged"] = RetirementRecord.from_dict(
            json.loads(json.dumps(self.record.to_dict())))
        self.registry.tombstones["forged"].signature_hex = "00" * 64
        before = self.snapshot()
        for cand, ref in ((CANDIDATE, PARENT), (CANDIDATE, "\U0001f90d"), ("\U0001f33f", PARENT)):
            self.scope(cand, ref)
        self.assertEqual(self.snapshot(), before)

    def test_F15_the_label_gate_still_fails_closed(self):
        """Admission is untouched: an untrusted retirement keeps its label out."""
        self.record.signature_hex = "00" * 64
        self.assertFalse(self.registry.is_admitted("K I (S K)"))
        self.assertFalse(ResurrectionDefense.preflight_check(self.registry, "K I (S K)")[0])


class RunnerHygieneTest(unittest.TestCase):
    """Section E: a green aggregate must describe this checkout."""

    def test_E1_the_runner_refuses_a_module_from_another_checkout(self):
        import test_all
        self.assertEqual(os.path.dirname(os.path.abspath(test_all.__file__)), _HERE)
        test_all._assert_local("glyph")
        sentinel = type(sys)("sentinel_module")
        sentinel.__file__ = "/somewhere/else/sentinel_module.py"
        sys.modules["sentinel_module"] = sentinel
        try:
            with self.assertRaises(ImportError) as caught:
                test_all._assert_local("sentinel_module")
            self.assertIn("outside this checkout", str(caught.exception))
        finally:
            del sys.modules["sentinel_module"]


if __name__ == "__main__":
    unittest.main(verbosity=2)
