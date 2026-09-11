#!/usr/bin/env python3
"""
Regression: one live consumer asks the scoped refutation question.

The consumer is the autopoiesis Palimpsest guard, on the path
`cli.py autopoiesis evolve` -> `evolve_autopoietic_organism` -> guard ->
in-place ISO 32000 append. Measured at 45bfcef, before this change:

  * a measured, audited refutation of exactly the replacement being proposed,
    recorded under a label, was invisible to the guard: `safe=True`;
  * a legacy tombstone filed under the gene id refused EVERY candidate for that
    gene, including the unchanged reference itself;
  * neither production entry point passed a registry at all, so on those paths
    the guard consulted an empty one.

What the sections pin:

  A  the guard, called directly: same-reference prohibition, another-reference
     and untrusted evidence refused by default as uncertainty (not as
     refutation) and proceeding only when the caller's policy names them, valid
     readoption, no measurement, the unchanged reference, an unrelated
     candidate, and the preserved legacy label gate
  B  the actual state change: `evolve_autopoietic_organism` on a real document
     leaves its bytes identical on refusal and appends a generation otherwise
  C  the same through the CLI, as a process, with a registry file: a malformed
     envelope is refused by name instead of read as an empty registry, and the
     CLI offers no override for untrusted evidence it could never reach
  D  the strict loader for external documents, and the lenient legacy loader
     left exactly as it was

The replacement used in B and C is the one evolution really makes on a fresh
organism, derived by running evolution on a copy rather than hard-coded. It is
a sound rewrite, so no genuine counterexample to it exists: the records in B
and C are signed ASSERTIONS about that pair. What these sections test is that
the consumer honours an authentic record for the exact pair it replaces. Whether
the record's author was right is issuer trust, deliberately not decided here.
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

# Same import guard, and same reason, as test_rule_identity.py.
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
from keystore import PRIVATE_KEY_SUFFIX
from autopoiesis import (check_palimpsest_guard, evolve_autopoietic_organism,
                         init_autopoietic_organism)
from controlled_forgetting import (EpistemicTombstoneRegistry, RetirementMode,
                                   RuleIdentity)
from epistemic_immune import RefutationAdmissionPolicy, RefutationScope
from organism import Chromosome

for _m in (autopoiesis, ei):
    if os.path.dirname(os.path.abspath(_m.__file__)) != _HERE:
        raise ImportError(f"{_m.__name__} resolved to {_m.__file__}, outside {_HERE}")

ANOTHER = RefutationScope.REFUTED_FOR_ANOTHER_REFERENCE
UNTRUSTED = RefutationScope.UNTRUSTED_EVIDENCE
DEFAULT = RefutationAdmissionPolicy()


def _replacement_evolution_makes(pdf_path):
    """Run evolution on a COPY and report (gene_id, reference, candidate)."""
    with tempfile.TemporaryDirectory() as scratch:
        copy_pdf = os.path.join(scratch, "copy.pdf")
        shutil.copy(pdf_path, copy_pdf)
        shutil.copy(pdf_path + PRIVATE_KEY_SUFFIX, copy_pdf + PRIVATE_KEY_SUFFIX)
        before = {c.gene_id: c.expression
                  for c in autopoiesis.organism_from_dict(
                      _manifest(copy_pdf)["current_organism"], "").chromosomes}
        succ, _ = evolve_autopoietic_organism(copy_pdf)
        changed = [(c.gene_id, before[c.gene_id], c.expression)
                   for c in succ.chromosomes if before[c.gene_id] != c.expression]
    assert len(changed) == 1, changed
    return changed[0]


def _malformed_variants(good):
    """Envelopes that must never be read as an empty registry."""
    return {
        "renamed tombstones": {"tombstone": good["tombstones"],
                               "readoptions": good["readoptions"]},
        "missing tombstones": {"readoptions": good["readoptions"]},
        "missing readoptions": {"tombstones": good["tombstones"]},
        "unknown extra key": dict(good, note="x"),
        "tombstones not an object": {"tombstones": list(good["tombstones"].values()),
                                     "readoptions": {}},
        "entry not an object": {"tombstones": {"asserted-refutation": "nope"},
                                "readoptions": {}},
        "top level not an object": [good],
        "empty object": {},
    }


def _manifest(pdf_path):
    with open(pdf_path, "rb") as fh:
        content = fh.read()
    prefix = autopoiesis.AUTOPOIESIS_MANIFEST_PREFIX.encode("utf-8")
    idx = content.rfind(prefix)
    end = content.find(b"\n", idx)
    return json.loads(content[idx + len(prefix):end].decode("utf-8"))


class _Fixture(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.pdf = os.path.join(self.dir.name, "organism.pdf")
        self.org0, _ = init_autopoietic_organism(self.pdf)
        self.gene, self.reference, self.candidate = _replacement_evolution_makes(self.pdf)
        self.sk, self.pk = crypto.generate_keypair()

    def pdf_bytes(self):
        with open(self.pdf, "rb") as fh:
            return fh.read()

    def key_bytes(self):
        with open(self.pdf + PRIVATE_KEY_SUFFIX, "rb") as fh:
            return fh.read()

    def registry_with(self, reference, candidate, label="asserted-refutation"):
        registry = EpistemicTombstoneRegistry()
        registry.retire(label, "d" * 64, RetirementMode.REFUTED,
                        "a signed assertion about one pair", self.sk, self.pk,
                        rule_identity=RuleIdentity.from_terms(label, reference,
                                                              candidate, "x"))
        return registry

    def candidate_org(self, expression):
        succ = copy.deepcopy(self.org0)
        succ.generation = self.org0.generation + 1
        succ.chromosomes = [
            Chromosome(gene_id=c.gene_id, gene_name=c.gene_name,
                       expression=expression if c.gene_id == self.gene else c.expression,
                       expected_normal_form=c.expected_normal_form, max_atp=c.max_atp)
            for c in self.org0.chromosomes]
        return succ

    def guard(self, registry, expression=None, policy=None):
        target = self.org0 if expression is None else self.candidate_org(expression)
        ok, msg, _ = check_palimpsest_guard(self.org0, target, registry, policy)
        return ok, msg


class GuardTest(_Fixture):
    """Section A: the guard, called directly."""

    def test_A0_the_fixture_is_the_replacement_evolution_really_makes(self):
        self.assertNotEqual(self.reference, self.candidate)
        self.assertIn(self.gene, {c.gene_id for c in self.org0.chromosomes})

    def test_A1_a_same_reference_refutation_refuses(self):
        ok, msg = self.guard(self.registry_with(self.reference, self.candidate),
                             self.candidate)
        self.assertFalse(ok)
        self.assertIn("REFUTED_FOR_REFERENCE", msg)

    def test_A2_another_reference_is_uncertainty_not_permission(self):
        registry = self.registry_with("\U0001f90d", self.candidate)
        ok, msg = self.guard(registry, self.candidate)
        self.assertFalse(ok, "not proven prohibited must not mean permitted")
        self.assertIn("REFUTED_FOR_ANOTHER_REFERENCE", msg)
        self.assertNotIn("REFUTED_FOR_REFERENCE:", msg)
        ok, msg = self.guard(registry, self.candidate,
                             RefutationAdmissionPolicy(frozenset(
                                 {RefutationScope.NO_MEASURED_REFUTATION, ANOTHER})))
        self.assertTrue(ok, msg)

    def test_A3_untrusted_evidence_is_uncertainty_not_permission(self):
        registry = self.registry_with(self.reference, self.candidate)
        registry.tombstones["asserted-refutation"].signature_hex = "00" * 64
        ok, msg = self.guard(registry, self.candidate)
        self.assertFalse(ok)
        self.assertIn("UNTRUSTED_EVIDENCE", msg)
        ok, msg = self.guard(registry, self.candidate,
                             RefutationAdmissionPolicy(frozenset(
                                 {RefutationScope.NO_MEASURED_REFUTATION, UNTRUSTED})))
        self.assertTrue(ok, msg)

    def test_A4_a_valid_readoption_lets_the_replacement_proceed(self):
        registry = self.registry_with(self.reference, self.candidate)
        registry.readopt(target_id="asserted-refutation", justification="new evidence",
                         new_evidence_claim_id="c" * 64,
                         author_sk_hex=self.sk, author_pk_hex=self.pk)
        ok, msg = self.guard(registry, self.candidate)
        self.assertTrue(ok, msg)

    def test_A5_nothing_measured_proceeds(self):
        for registry in (None, EpistemicTombstoneRegistry()):
            with self.subTest(registry=registry):
                ok, msg = self.guard(registry, self.candidate)
                self.assertTrue(ok, msg)

    def test_A6_the_unchanged_reference_is_not_a_replacement(self):
        ok, msg = self.guard(self.registry_with(self.reference, self.candidate))
        self.assertTrue(ok, msg)

    def test_A6b_unreadable_evidence_stops_only_replacements(self):
        """Nothing replaced, nothing to ask: untrusted records do not freeze a genome."""
        registry = self.registry_with(self.reference, self.candidate)
        registry.tombstones["asserted-refutation"].signature_hex = "00" * 64
        ok, msg = self.guard(registry)
        self.assertTrue(ok, msg)

    def test_A7_the_record_addresses_one_pair_not_the_gene(self):
        registry = self.registry_with(self.reference, self.candidate)
        ok, msg = self.guard(registry, "\U0001f5a4 (\U0001f33f \U0001f90d \U0001f90d) \U0001f90d")
        self.assertNotIn("refutation scope", msg)

    def test_A8_the_legacy_label_gate_is_preserved(self):
        """A gene-id tombstone still refuses everything for that gene."""
        legacy = EpistemicTombstoneRegistry()
        legacy.retire(self.gene, "d" * 64, RetirementMode.REFUTED, "legacy", self.sk, self.pk)
        for expression in (None, self.candidate):
            with self.subTest(expression=expression):
                ok, msg = self.guard(legacy, expression)
                self.assertFalse(ok)
                self.assertIn("quarantined tombstone allele", msg)

    def test_A9_a_same_reference_refutation_cannot_be_opted_into(self):
        with self.assertRaises(ValueError):
            RefutationAdmissionPolicy(frozenset({RefutationScope.REFUTED_FOR_REFERENCE}))
        policy = RefutationAdmissionPolicy()
        object.__setattr__(policy, "proceed_on",
                           frozenset({RefutationScope.REFUTED_FOR_REFERENCE}))
        ok, _ = self.guard(self.registry_with(self.reference, self.candidate),
                           self.candidate, policy)
        self.assertFalse(ok, "a mutated policy is re-checked where it is used")

    def test_A10_a_policy_holds_only_scopes(self):
        with self.assertRaises(TypeError):
            RefutationAdmissionPolicy(frozenset({"NO_MEASURED_REFUTATION"}))
        ok, msg = self.guard(None, self.candidate, policy="proceed")
        self.assertFalse(ok)
        self.assertIn("not a RefutationAdmissionPolicy", msg)


class StateChangeTest(_Fixture):
    """Section B: the path to an actual state change."""

    def test_B1_a_same_reference_refutation_leaves_the_document_untouched(self):
        before = self.pdf_bytes()
        with self.assertRaises(ValueError) as caught:
            evolve_autopoietic_organism(
                self.pdf, tombstone_registry=self.registry_with(self.reference, self.candidate))
        self.assertIn("REFUTED_FOR_REFERENCE", str(caught.exception))
        self.assertEqual(self.pdf_bytes(), before)

    def test_B2_without_a_registry_evolution_proceeds_as_before(self):
        before = self.pdf_bytes()
        succ, receipt = evolve_autopoietic_organism(self.pdf)
        self.assertEqual(succ.generation, 1)
        self.assertEqual(receipt.gene_id, self.gene)
        self.assertTrue(self.pdf_bytes().startswith(before))
        self.assertGreater(len(self.pdf_bytes()), len(before))

    def test_B3_uncertainty_stops_evolution_unless_the_caller_names_it(self):
        registry = self.registry_with("\U0001f90d", self.candidate)
        before = self.pdf_bytes()
        with self.assertRaises(ValueError) as caught:
            evolve_autopoietic_organism(self.pdf, tombstone_registry=registry)
        self.assertIn("REFUTED_FOR_ANOTHER_REFERENCE", str(caught.exception))
        self.assertEqual(self.pdf_bytes(), before)
        succ, _ = evolve_autopoietic_organism(
            self.pdf, tombstone_registry=registry,
            refutation_policy=RefutationAdmissionPolicy(frozenset(
                {RefutationScope.NO_MEASURED_REFUTATION, ANOTHER})))
        self.assertEqual(succ.generation, 1)
        self.assertGreater(len(self.pdf_bytes()), len(before))


class CliTest(_Fixture):
    """Section C: the same, through the CLI, as a process."""

    CLI = os.path.join(_HERE, "cli.py")

    def evolve(self, *extra):
        return subprocess.run(
            [sys.executable, "-B", self.CLI, "autopoiesis", "evolve", self.pdf, *extra],
            cwd=_HERE, capture_output=True, text=True, timeout=300)

    def write_registry(self, registry):
        path = os.path.join(self.dir.name, "tombstones.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(registry.to_dict(), fh)
        return path

    def test_C1_a_same_reference_refutation_refuses_and_writes_nothing(self):
        path = self.write_registry(self.registry_with(self.reference, self.candidate))
        before = self.pdf_bytes()
        proc = self.evolve("--tombstones", path)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("REFUTED_FOR_REFERENCE", proc.stdout)
        self.assertEqual(self.pdf_bytes(), before)

    def test_C2_without_a_registry_the_cli_evolves_as_before(self):
        before = self.pdf_bytes()
        proc = self.evolve()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertGreater(len(self.pdf_bytes()), len(before))

    def test_C3_uncertainty_needs_an_explicit_flag(self):
        path = self.write_registry(self.registry_with("\U0001f90d", self.candidate))
        before = self.pdf_bytes()
        proc = self.evolve("--tombstones", path)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("REFUTED_FOR_ANOTHER_REFERENCE", proc.stdout)
        self.assertEqual(self.pdf_bytes(), before)
        proc = self.evolve("--tombstones", path,
                           "--also-proceed-on", "REFUTED_FOR_ANOTHER_REFERENCE")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertGreater(len(self.pdf_bytes()), len(before))

    def test_C4_an_unverifiable_registry_file_refuses_before_anything(self):
        data = self.registry_with(self.reference, self.candidate).to_dict()
        data["tombstones"]["asserted-refutation"]["signature_hex"] = "00" * 64
        path = os.path.join(self.dir.name, "bad.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        before = self.pdf_bytes()
        proc = self.evolve("--tombstones", path)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("could not be loaded", proc.stdout)
        self.assertEqual(self.pdf_bytes(), before)

    def test_C5_the_cli_cannot_opt_into_a_same_reference_refutation(self):
        before = self.pdf_bytes()
        proc = self.evolve("--also-proceed-on", "REFUTED_FOR_REFERENCE")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(self.pdf_bytes(), before)


    def assertRefusedUnchanged(self, proc, before, key_before):
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("could not be loaded", proc.stdout)
        self.assertNotIn("Traceback", proc.stderr)
        self.assertEqual(self.pdf_bytes(), before)
        self.assertEqual(self.key_bytes(), key_before)

    def test_C6_a_malformed_envelope_is_refused_by_name(self):
        """Round 1 of review: renaming `tombstones` appended a generation."""
        good = self.registry_with(self.reference, self.candidate).to_dict()
        path = os.path.join(self.dir.name, "malformed.json")
        before, key_before = self.pdf_bytes(), self.key_bytes()
        for name, doc in _malformed_variants(good).items():
            with self.subTest(variant=name):
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(doc, fh)
                self.assertRefusedUnchanged(self.evolve("--tombstones", path),
                                            before, key_before)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{ this is not json")
        self.assertRefusedUnchanged(self.evolve("--tombstones", path), before, key_before)

    def test_C7_an_explicitly_empty_registry_proceeds(self):
        path = self.write_registry(EpistemicTombstoneRegistry())
        before = self.pdf_bytes()
        proc = self.evolve("--tombstones", path)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertGreater(len(self.pdf_bytes()), len(before))

    def test_C8_a_valid_readopted_registry_proceeds(self):
        registry = self.registry_with(self.reference, self.candidate)
        registry.readopt(target_id="asserted-refutation", justification="new evidence",
                         new_evidence_claim_id="c" * 64,
                         author_sk_hex=self.sk, author_pk_hex=self.pk)
        path = self.write_registry(registry)
        before = self.pdf_bytes()
        proc = self.evolve("--tombstones", path)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertGreater(len(self.pdf_bytes()), len(before))

    def test_C9_the_cli_offers_no_untrusted_override(self):
        """The loader refuses unverifiable records before any policy, so the
        option could never do what it said. It is gone rather than weakened."""
        registry = self.registry_with(self.reference, self.candidate)
        registry.tombstones["asserted-refutation"].signature_hex = "00" * 64
        path = self.write_registry(registry)
        before = self.pdf_bytes()
        proc = self.evolve("--tombstones", path, "--also-proceed-on", "UNTRUSTED_EVIDENCE")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("invalid choice", proc.stderr)
        self.assertEqual(self.pdf_bytes(), before)
        proc = self.evolve("--tombstones", path)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(self.pdf_bytes(), before)


class RegistryDocumentTest(unittest.TestCase):
    """Section D: the strict loader, and the lenient one left alone."""

    def setUp(self):
        self.sk, self.pk = crypto.generate_keypair()
        registry = EpistemicTombstoneRegistry()
        registry.retire("s", "d" * 64, RetirementMode.REFUTED, "loss", self.sk, self.pk)
        self.good = registry.to_dict()

    def test_D1_what_to_dict_writes_loads(self):
        self.assertEqual(set(EpistemicTombstoneRegistry.from_document(self.good).tombstones),
                         {"s"})
        empty = EpistemicTombstoneRegistry().to_dict()
        self.assertEqual(EpistemicTombstoneRegistry.from_document(empty).tombstones, {})

    def test_D2_each_malformed_envelope_raises_value_error(self):
        for name, doc in _malformed_variants(self.good).items():
            with self.subTest(variant=name):
                with self.assertRaises(ValueError):
                    EpistemicTombstoneRegistry.from_document(doc)

    def test_D3_the_lenient_loader_is_unchanged(self):
        """Embedded callers still pass fragments; nothing about them changed."""
        self.assertEqual(EpistemicTombstoneRegistry.from_dict({}).tombstones, {})
        partial = {"tombstones": self.good["tombstones"]}
        self.assertEqual(set(EpistemicTombstoneRegistry.from_dict(partial).tombstones), {"s"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
