#!/usr/bin/env python3
"""
Regression: the same signed assertion has different consequences by issuer.

The consequence table was committed first, in docs/TRUSTED-ISSUERS.md, before
any of this code existed. Rows C1 to C8 there are the rows tested here.

Before this change a registry record was authenticated for its slot, and its
author was then never compared with anything. Any key that signed a
well-formed refutation prohibited, and any key that signed a readoption lifted
one.

What the sections pin:

  A  the query, `refuted_for`, for every row of the table, plus the headline
     comparison: one assertion, two keys, two consequences
  B  the live guard with an issuer policy, under the default admission policy
     and an explicit one
  C  the CLI as a process, with `--trusted-issuers`: the foreign scope is
     reachable through the file path and can be opted into; a trusted one
     cannot; a foreign readoption lifts nothing; a malformed policy file is
     refused by name
  D  a key is its decoded bytes, not its spelling. Review round 1: an
     uppercase spelling of the trusted key turned the same signed retirement
     from REFUTED_FOR_REFERENCE into UNAUTHORIZED_ISSUER, which the override
     then let through
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
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

import crypto
import autopoiesis
import epistemic_immune as ei
from autopoiesis import (check_palimpsest_guard, evolve_autopoietic_organism,
                         init_autopoietic_organism)
from controlled_forgetting import EpistemicTombstoneRegistry, RetirementMode, RuleIdentity
from epistemic_immune import (IssuerPolicy, RefutationAdmissionPolicy, RefutationScope,
                              ResurrectionDefense)
from organism import Chromosome

for _m in (autopoiesis, ei):
    if os.path.dirname(os.path.abspath(_m.__file__)) != _HERE:
        raise ImportError(f"{_m.__name__} resolved to {_m.__file__}, outside {_HERE}")

REFUTED = RefutationScope.REFUTED_FOR_REFERENCE
UNAUTHORIZED = RefutationScope.UNAUTHORIZED_ISSUER
UNTRUSTED = RefutationScope.UNTRUSTED_EVIDENCE
ANOTHER = RefutationScope.REFUTED_FOR_ANOTHER_REFERENCE
NOTHING = RefutationScope.NO_MEASURED_REFUTATION

REF, CAND, OTHER_REF = "🖤", "🖤 🤍", "🤍"


class _Keys:
    def setUp(self):
        self.sk_t, self.pk_t = crypto.generate_keypair()     # the caller trusts this one
        self.sk_f, self.pk_f = crypto.generate_keypair()     # and not this one
        self.policy = IssuerPolicy.same_for_both({self.pk_t})

    def retire(self, registry, label, sk, pk, reference, candidate):
        registry.retire(label, "d" * 64, RetirementMode.REFUTED, "a signed assertion", sk, pk,
                        rule_identity=RuleIdentity.from_terms(label, reference, candidate, "x"))
        return registry

    def readopt(self, registry, label, sk, pk):
        return registry.readopt(target_id=label, justification="lifted",
                                new_evidence_claim_id="c" * 64,
                                author_sk_hex=sk, author_pk_hex=pk)


class QueryTest(_Keys, unittest.TestCase):
    """Section A: `refuted_for`, row by row."""

    def ask(self, registry, issuers="policy", candidate=CAND, reference=REF):
        policy = self.policy if issuers == "policy" else issuers
        return ResurrectionDefense.refuted_for(registry, candidate, reference, policy)

    def test_A0_one_assertion_two_keys_two_consequences(self):
        """The point of the package, C2 against C3."""
        by_trusted = self.retire(EpistemicTombstoneRegistry(), "r", self.sk_t, self.pk_t, REF, CAND)
        by_foreign = self.retire(EpistemicTombstoneRegistry(), "r", self.sk_f, self.pk_f, REF, CAND)
        trusted, foreign = self.ask(by_trusted), self.ask(by_foreign)
        self.assertEqual((trusted.scope, trusted.prohibits()), (REFUTED, True))
        self.assertEqual((foreign.scope, foreign.prohibits()), (UNAUTHORIZED, False))
        self.assertEqual(foreign.unauthorized_slots, ("r",))

    def test_C1_without_a_policy_every_authentic_author_counts(self):
        registry = self.retire(EpistemicTombstoneRegistry(), "r", self.sk_f, self.pk_f, REF, CAND)
        report = self.ask(registry, issuers=None)
        self.assertEqual(report.scope, REFUTED)
        self.assertEqual(report, ResurrectionDefense.refuted_for(registry, CAND, REF))

    def test_C2_a_trusted_retirement_prohibits(self):
        registry = self.retire(EpistemicTombstoneRegistry(), "r", self.sk_t, self.pk_t, REF, CAND)
        self.assertTrue(self.ask(registry).prohibits())

    def test_C3_the_same_retirement_by_a_foreign_key_is_uncertainty(self):
        registry = self.retire(EpistemicTombstoneRegistry(), "r", self.sk_f, self.pk_f, REF, CAND)
        report = self.ask(registry)
        self.assertEqual(report.scope, UNAUTHORIZED)
        self.assertFalse(report.prohibits())
        self.assertIsNone(report.target_id, "no authority is attributed to the foreign record")

    def test_C4_a_trusted_readoption_lifts_a_trusted_retirement(self):
        registry = self.retire(EpistemicTombstoneRegistry(), "r", self.sk_t, self.pk_t, REF, CAND)
        self.readopt(registry, "r", self.sk_t, self.pk_t)
        self.assertEqual(self.ask(registry).scope, NOTHING)

    def test_C5_a_foreign_readoption_lifts_nothing(self):
        registry = self.retire(EpistemicTombstoneRegistry(), "r", self.sk_t, self.pk_t, REF, CAND)
        self.readopt(registry, "r", self.sk_f, self.pk_f)
        self.assertTrue(registry.readoptions["r"].is_admissible_for(
            "r", registry.tombstones["r"]), "the readoption is authentic and linked")
        report = self.ask(registry)
        self.assertEqual(report.scope, REFUTED)
        self.assertEqual(report.ignored_readoptions, ("r",))

    def test_C6_a_foreign_retirement_beside_a_trusted_one(self):
        registry = self.retire(EpistemicTombstoneRegistry(), "trusted", self.sk_t, self.pk_t, REF, CAND)
        self.retire(registry, "foreign", self.sk_f, self.pk_f, REF, CAND)
        report = self.ask(registry)
        self.assertEqual(report.scope, REFUTED)
        self.assertEqual(report.target_id, "trusted")
        self.assertEqual(report.unauthorized_slots, ("foreign",))

    def test_C7_borrowing_a_trusted_name_fails_authentication_first(self):
        registry = self.retire(EpistemicTombstoneRegistry(), "r", self.sk_f, self.pk_f, REF, CAND)
        registry.tombstones["r"].author_pk_hex = self.pk_t      # claims the trusted key
        self.assertFalse(registry.tombstones["r"].verify_signature())
        report = self.ask(registry)
        self.assertEqual(report.scope, UNTRUSTED)
        self.assertEqual(report.untrusted_slots, ("r",))

    def test_C8_nothing_with_a_policy(self):
        self.assertEqual(self.ask(EpistemicTombstoneRegistry()).scope, NOTHING)

    def test_A9_retirement_and_readoption_lists_are_separate(self):
        sk_r, pk_r = crypto.generate_keypair()
        policy = IssuerPolicy(retirement_issuers={self.pk_t},
                              readoption_issuers={self.pk_t, pk_r})
        lifted = self.retire(EpistemicTombstoneRegistry(), "r", self.sk_t, self.pk_t, REF, CAND)
        self.readopt(lifted, "r", sk_r, pk_r)
        self.assertEqual(self.ask(lifted, issuers=policy).scope, NOTHING)
        by_reviewer = self.retire(EpistemicTombstoneRegistry(), "r", sk_r, pk_r, REF, CAND)
        self.assertEqual(self.ask(by_reviewer, issuers=policy).scope, UNAUTHORIZED)

    def test_A10_an_empty_list_means_nobody(self):
        registry = self.retire(EpistemicTombstoneRegistry(), "r", self.sk_t, self.pk_t, REF, CAND)
        self.assertEqual(self.ask(registry, issuers=IssuerPolicy.same_for_both(set())).scope,
                         UNAUTHORIZED)

    def test_A11_a_foreign_refutation_elsewhere_is_not_another_reference(self):
        registry = self.retire(EpistemicTombstoneRegistry(), "r", self.sk_f, self.pk_f,
                               OTHER_REF, CAND)
        self.assertEqual(self.ask(registry).scope, NOTHING)
        trusted = self.retire(EpistemicTombstoneRegistry(), "r", self.sk_t, self.pk_t,
                              OTHER_REF, CAND)
        self.assertEqual(self.ask(trusted).scope, ANOTHER)

    def test_A12_untrusted_outranks_unauthorized(self):
        registry = self.retire(EpistemicTombstoneRegistry(), "foreign", self.sk_f, self.pk_f, REF, CAND)
        self.retire(registry, "broken", self.sk_t, self.pk_t, REF, CAND)
        registry.tombstones["broken"].signature_hex = "00" * 64
        report = self.ask(registry)
        self.assertEqual(report.scope, UNTRUSTED)
        self.assertEqual(report.unauthorized_slots, ("foreign",))

    def test_A13_the_policy_validates_its_keys_and_its_document(self):
        with self.assertRaises(ValueError):
            IssuerPolicy.same_for_both({"not-a-key"})
        with self.assertRaises(TypeError):
            IssuerPolicy(retirement_issuers=self.pk_t, readoption_issuers=set())
        good = {"retirement_issuers": [self.pk_t], "readoption_issuers": [self.pk_t]}
        self.assertEqual(IssuerPolicy.from_document(good), self.policy)
        for name, doc in _malformed_policies(self.pk_t).items():
            with self.subTest(variant=name):
                with self.assertRaises((ValueError, TypeError)):
                    IssuerPolicy.from_document(doc)


def _malformed_policies(pk):
    return {
        "renamed key": {"retirement_issuer": [pk], "readoption_issuers": [pk]},
        "missing readoption list": {"retirement_issuers": [pk]},
        "unknown extra key": {"retirement_issuers": [pk], "readoption_issuers": [pk], "x": 1},
        "list is a string": {"retirement_issuers": pk, "readoption_issuers": [pk]},
        "entry not a string": {"retirement_issuers": [7], "readoption_issuers": [pk]},
        "entry not a key": {"retirement_issuers": ["00" * 32], "readoption_issuers": [pk]},
        "top level not an object": [pk],
    }


def _manifest(pdf_path):
    with open(pdf_path, "rb") as fh:
        content = fh.read()
    prefix = autopoiesis.AUTOPOIESIS_MANIFEST_PREFIX.encode("utf-8")
    idx = content.rfind(prefix)
    return json.loads(content[idx + len(prefix):content.find(b"\n", idx)].decode("utf-8"))


class _Organism(_Keys):

    def setUp(self):
        _Keys.setUp(self)
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.pdf = os.path.join(self.dir.name, "organism.pdf")
        self.org0, _ = init_autopoietic_organism(self.pdf)
        scratch = os.path.join(self.dir.name, "copy.pdf")
        shutil.copy(self.pdf, scratch)
        shutil.copy(self.pdf + ".key", scratch + ".key")
        before = {c["gene_id"]: c["expression"]
                  for c in _manifest(scratch)["current_organism"]["chromosomes"]}
        succ, _ = evolve_autopoietic_organism(scratch)
        (self.gene, self.reference, self.candidate), = [
            (c.gene_id, before[c.gene_id], c.expression)
            for c in succ.chromosomes if before[c.gene_id] != c.expression]

    def pdf_bytes(self):
        with open(self.pdf, "rb") as fh:
            return fh.read()

    def pair_registry(self, sk, pk, label="r"):
        return self.retire(EpistemicTombstoneRegistry(), label, sk, pk,
                           self.reference, self.candidate)


class GuardTest(_Organism, unittest.TestCase):
    """Section B: the live guard."""

    def guard(self, registry, issuers, policy=None):
        succ = copy.deepcopy(self.org0)
        succ.generation = 1
        succ.chromosomes = [Chromosome(gene_id=c.gene_id, gene_name=c.gene_name,
                                       expression=self.candidate if c.gene_id == self.gene
                                       else c.expression,
                                       expected_normal_form=c.expected_normal_form,
                                       max_atp=c.max_atp) for c in self.org0.chromosomes]
        ok, msg, _ = check_palimpsest_guard(self.org0, succ, registry, policy, issuers)
        return ok, msg

    def test_B1_a_trusted_refutation_refuses_and_cannot_be_opted_past(self):
        ok, msg = self.guard(self.pair_registry(self.sk_t, self.pk_t), self.policy)
        self.assertFalse(ok)
        self.assertIn("REFUTED_FOR_REFERENCE", msg)

    def test_B2_a_foreign_refutation_is_uncertainty_until_named(self):
        registry = self.pair_registry(self.sk_f, self.pk_f)
        ok, msg = self.guard(registry, self.policy)
        self.assertFalse(ok)
        self.assertIn("UNAUTHORIZED_ISSUER", msg)
        ok, msg = self.guard(registry, self.policy, RefutationAdmissionPolicy(
            frozenset({NOTHING, UNAUTHORIZED})))
        self.assertTrue(ok, msg)

    def test_B3_a_foreign_readoption_does_not_let_evolution_through(self):
        registry = self.pair_registry(self.sk_t, self.pk_t)
        self.readopt(registry, "r", self.sk_f, self.pk_f)
        ok, msg = self.guard(registry, self.policy)
        self.assertFalse(ok)
        self.assertIn("REFUTED_FOR_REFERENCE", msg)

    def test_B4_the_issuer_policy_must_be_one(self):
        ok, msg = self.guard(None, issuers=["a key"])
        self.assertFalse(ok)
        self.assertIn("not an IssuerPolicy", msg)


class CliTest(_Organism, unittest.TestCase):
    """Section C: the CLI as a process."""

    CLI = os.path.join(_HERE, "cli.py")

    def evolve(self, *extra):
        return subprocess.run([sys.executable, "-B", self.CLI, "autopoiesis", "evolve",
                               self.pdf, *extra],
                              cwd=_HERE, capture_output=True, text=True, timeout=300)

    def write(self, name, doc):
        path = os.path.join(self.dir.name, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh)
        return path

    def trusted_file(self):
        return self.write("issuers.json", {"retirement_issuers": [self.pk_t],
                                           "readoption_issuers": [self.pk_t]})

    def test_C1_a_trusted_refutation_refuses_and_writes_nothing(self):
        registry = self.write("reg.json", self.pair_registry(self.sk_t, self.pk_t).to_dict())
        before = self.pdf_bytes()
        proc = self.evolve("--tombstones", registry, "--trusted-issuers", self.trusted_file())
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("REFUTED_FOR_REFERENCE", proc.stdout)
        self.assertEqual(self.pdf_bytes(), before)

    def test_C2_a_foreign_refutation_is_reachable_and_can_be_opted_past(self):
        registry = self.write("reg.json", self.pair_registry(self.sk_f, self.pk_f).to_dict())
        before = self.pdf_bytes()
        proc = self.evolve("--tombstones", registry, "--trusted-issuers", self.trusted_file())
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("UNAUTHORIZED_ISSUER", proc.stdout)
        self.assertEqual(self.pdf_bytes(), before)
        proc = self.evolve("--tombstones", registry, "--trusted-issuers", self.trusted_file(),
                           "--also-proceed-on", "UNAUTHORIZED_ISSUER")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertGreater(len(self.pdf_bytes()), len(before))

    def test_C3_a_foreign_readoption_lifts_nothing(self):
        registry = self.pair_registry(self.sk_t, self.pk_t)
        self.readopt(registry, "r", self.sk_f, self.pk_f)
        path = self.write("reg.json", registry.to_dict())
        before = self.pdf_bytes()
        proc = self.evolve("--tombstones", path, "--trusted-issuers", self.trusted_file())
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(self.pdf_bytes(), before)

    def test_C4_without_a_policy_the_foreign_record_counts_as_before(self):
        registry = self.write("reg.json", self.pair_registry(self.sk_f, self.pk_f).to_dict())
        proc = self.evolve("--tombstones", registry)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("REFUTED_FOR_REFERENCE", proc.stdout)

    def test_C5_a_malformed_issuer_file_is_refused_by_name(self):
        registry = self.write("reg.json", self.pair_registry(self.sk_f, self.pk_f).to_dict())
        before = self.pdf_bytes()
        for name, doc in _malformed_policies(self.pk_t).items():
            with self.subTest(variant=name):
                path = self.write("bad-issuers.json", doc)
                proc = self.evolve("--tombstones", registry, "--trusted-issuers", path,
                                   "--also-proceed-on", "UNAUTHORIZED_ISSUER")
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertIn("issuer policy", proc.stdout)
                self.assertNotIn("Traceback", proc.stderr)
                self.assertEqual(self.pdf_bytes(), before)

    def test_C6_a_trusted_readoption_lets_evolution_through(self):
        registry = self.pair_registry(self.sk_t, self.pk_t)
        self.readopt(registry, "r", self.sk_t, self.pk_t)
        path = self.write("reg.json", registry.to_dict())
        before = self.pdf_bytes()
        proc = self.evolve("--tombstones", path, "--trusted-issuers", self.trusted_file())
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertGreater(len(self.pdf_bytes()), len(before))



def _spellings(pk):
    """Every hex spelling crypto validation accepts is a case pattern of the
    same 64 characters. A fixed sample: all lower, all upper, and patterns."""
    out = {"lower": pk.lower(), "upper": pk.upper(),
           "alternating": "".join(c.upper() if i % 2 else c.lower() for i, c in enumerate(pk)),
           "first half upper": pk[:32].upper() + pk[32:].lower(),
           "last half upper": pk[:32].lower() + pk[32:].upper()}
    for name, value in out.items():
        assert crypto.is_valid_public_key(value), name
    return out


class KeyIdentityTest(_Keys, unittest.TestCase):
    """Section D: identity is the decoded key, on both sides of the comparison."""

    def ask(self, registry, issuers):
        return ResurrectionDefense.refuted_for(registry, CAND, REF, issuers)

    def test_D1_every_spelling_in_the_policy_is_the_same_retirement_issuer(self):
        registry = self.retire(EpistemicTombstoneRegistry(), "r", self.sk_t, self.pk_t, REF, CAND)
        for name, spelling in _spellings(self.pk_t).items():
            with self.subTest(policy_spelling=name):
                report = self.ask(registry, IssuerPolicy.same_for_both({spelling}))
                self.assertEqual(report.scope, REFUTED)
                self.assertTrue(report.prohibits())

    def test_D2_every_spelling_in_the_policy_is_the_same_readoption_issuer(self):
        registry = self.retire(EpistemicTombstoneRegistry(), "r", self.sk_t, self.pk_t, REF, CAND)
        self.readopt(registry, "r", self.sk_t, self.pk_t)
        for name, spelling in _spellings(self.pk_t).items():
            with self.subTest(readoption_spelling=name):
                policy = IssuerPolicy(retirement_issuers={self.pk_t},
                                      readoption_issuers={spelling})
                self.assertEqual(self.ask(registry, policy).scope, NOTHING)

    def test_D3_a_signed_author_field_in_any_spelling_is_the_same_key(self):
        """The spelling here is inside the signed body, and the signature holds."""
        for name, spelling in _spellings(self.pk_t).items():
            with self.subTest(author_spelling=name):
                registry = self.retire(EpistemicTombstoneRegistry(), "r", self.sk_t, spelling,
                                       REF, CAND)
                self.assertTrue(registry.tombstones["r"].verify_signature())
                self.assertEqual(registry.tombstones["r"].author_pk_hex, spelling,
                                 "the signed body is not rewritten")
                self.assertEqual(self.ask(registry, self.policy).scope, REFUTED)

    def test_D3b_a_signed_readoption_author_in_any_spelling_is_the_same_key(self):
        """The readoption half of D3: its author spelling is inside its own signed body."""
        for name, spelling in _spellings(self.pk_t).items():
            with self.subTest(readoption_author_spelling=name):
                registry = self.retire(EpistemicTombstoneRegistry(), "r", self.sk_t, self.pk_t,
                                       REF, CAND)
                self.readopt(registry, "r", self.sk_t, spelling)
                self.assertTrue(registry.readoptions["r"].is_admissible_for(
                    "r", registry.tombstones["r"]))
                self.assertEqual(registry.readoptions["r"].author_pk_hex, spelling)
                self.assertEqual(self.ask(registry, self.policy).scope, NOTHING)

    def test_D4_the_policy_holds_one_identity_per_key(self):
        policy = IssuerPolicy.same_for_both(set(_spellings(self.pk_t).values()))
        self.assertEqual(policy.retirement_issuers, frozenset({self.pk_t.lower()}))
        self.assertEqual(policy, IssuerPolicy.same_for_both({self.pk_t.upper()}))

    def test_D5_a_really_different_key_stays_foreign_in_every_spelling(self):
        registry = self.retire(EpistemicTombstoneRegistry(), "r", self.sk_f, self.pk_f, REF, CAND)
        for name, spelling in _spellings(self.pk_t).items():
            with self.subTest(policy_spelling=name):
                self.assertEqual(self.ask(registry, IssuerPolicy.same_for_both({spelling})).scope,
                                 UNAUTHORIZED)

    def test_D6_a_borrowed_name_in_any_spelling_stays_untrusted(self):
        for name, spelling in _spellings(self.pk_t).items():
            with self.subTest(borrowed_spelling=name):
                registry = self.retire(EpistemicTombstoneRegistry(), "r", self.sk_f, self.pk_f,
                                       REF, CAND)
                registry.tombstones["r"].author_pk_hex = spelling
                self.assertFalse(registry.tombstones["r"].verify_signature())
                self.assertEqual(self.ask(registry, self.policy).scope, UNTRUSTED)

    def test_D7_the_two_role_lists_stay_separate_under_any_spelling(self):
        registry = self.retire(EpistemicTombstoneRegistry(), "r", self.sk_t, self.pk_t, REF, CAND)
        self.readopt(registry, "r", self.sk_t, self.pk_t)
        policy = IssuerPolicy(retirement_issuers={self.pk_t.upper()},
                              readoption_issuers={self.pk_f.upper()})
        report = self.ask(registry, policy)
        self.assertEqual(report.scope, REFUTED, "trusted for retiring, not for lifting")
        self.assertEqual(report.ignored_readoptions, ("r",))

    def test_D8_the_cli_file_accepts_any_spelling_as_the_same_key(self):
        """Pinned through the real CLI: the supported behaviour is normalization."""
        case = CliTest("test_C1_a_trusted_refutation_refuses_and_writes_nothing")
        case.setUp()
        try:
            registry = case.write("reg.json",
                                  case.pair_registry(case.sk_t, case.pk_t).to_dict())
            before = case.pdf_bytes()
            for name, spelling in _spellings(case.pk_t).items():
                with self.subTest(file_spelling=name):
                    issuers = case.write("issuers.json", {"retirement_issuers": [spelling],
                                                          "readoption_issuers": [spelling]})
                    proc = case.evolve("--tombstones", registry, "--trusted-issuers", issuers,
                                       "--also-proceed-on", "UNAUTHORIZED_ISSUER")
                    self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                    self.assertIn("REFUTED_FOR_REFERENCE", proc.stdout)
                    self.assertEqual(case.pdf_bytes(), before)
        finally:
            case.doCleanups()


if __name__ == "__main__":
    unittest.main(verbosity=2)
