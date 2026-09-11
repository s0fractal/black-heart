#!/usr/bin/env python3
"""
Regression: nothing is retired or credited on evidence that was never audited.

`CounterexampleMetabolism.metabolize_counterexample` appended a signed Grade C
claim, minted a REFUTED tombstone and credited an ATP bounty without ever
auditing the claim it had just built. Its endpoints came from identifiers: a
gene id in `omega`, a rule display name in `tau`. Measured on the base commit
with the fixtures the repository itself ships:

    gene_id "GENESIS_K"    parses as a free variable
    rule    "x y -> y x"   parses as an application of six free variables

so "not terms" was the wrong description. They parse. They are simply not the
executable endpoints the witness describes, and replaying them reproduces
something nobody intended: `GENESIS_K (x)` settles to itself. All four in-repo
fixtures now FAIL an audit, and each still credited its bounty:

    immune test_02   FAIL, +200 ATP, 1 tombstone
    cli inoculate    FAIL,  +70 ATP, 1 tombstone
    swarm cascade    FAIL,  +70 ATP, 1 tombstone
    swarm merge      FAIL,  +91 ATP, 1 tombstone

What the sections pin:

  A  a real divergence is metabolized, and the claim it credited passes an audit
     performed by somebody else
  B  each way of being wrong is refused, and refusal leaves claims, tombstones
     and ATP exactly as they were
  C  identifiers are provenance: they cannot be smuggled in as endpoints, and
     neither old call shape can bind against the new signature
  D  an observation grants nothing, and no success flag travels
  E  the command-line adapter, driven as a process: it will not invent operands,
     it will not accept an endpoint that is not a term, and every refusal leaves
     the input state and any pre-existing output byte-identical

The predicate, in full: effects follow a PASS verdict on that same claim, issued
inside the call that applies them, over operands the caller stated. Nothing here
says the label denotes the term beside it, or that the bounty is a sensible
price.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

# Same import guard, and same reason, as test_counterexample_evidence.py.
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
import epistemic_immune as ei
from epistemic_immune import (
    CounterexampleMetabolism, EpistemicOrganism, MetabolismStatus,
    ObservationStatus, observe_divergence,
)
from organism import Chromosome
from warrant_kernel import (
    TrustConfig, VerificationStatus, WarrantVerifier,
)

if os.path.dirname(os.path.abspath(ei.__file__)) != _HERE:
    raise ImportError(f"epistemic_immune resolved to {ei.__file__}, outside {_HERE}")

# The measured divergence used throughout:
#   K   (I (K I)) -> K (K I)   in 1 ATP
#   K I (I (K I)) -> I         in 1 ATP
PARENT, CANDIDATE = "🖤", "🖤 🤍"
INPUT = "🤍 (🖤 🤍)"
PARENT_OUT, CANDIDATE_OUT, ATP = "🖤 (🖤 🤍)", "🤍", 1

# A pair that never settles, for the suspended case.
DIVERGENT_HEAD = "🔁 🤍"


class ProducerTest(unittest.TestCase):

    def setUp(self):
        self.sk, self.pk = crypto.generate_keypair()
        self.org = EpistemicOrganism(
            organism_id="ORG-TEST", generation=0,
            chromosomes=[Chromosome(gene_id="G1", gene_name="trial", expression="🖤",
                                    expected_normal_form="🖤", vital=False)],
            public_key_hex=self.pk, atp_reserve=500)

    def state(self):
        return (len(self.org.claims), len(self.org.tombstone_registry.tombstones),
                self.org.atp_reserve, self.org.total_bounties_reclaimed)

    def metabolize(self, verifier=None, **over):
        kw = dict(gene_id="G1", rule_name="x y -> y x", parent_term=PARENT,
                  candidate_term=CANDIDATE, input_fixture=INPUT,
                  expected_norm=PARENT_OUT, actual_norm=CANDIDATE_OUT, atp_cost=ATP)
        kw.update(over)
        return CounterexampleMetabolism.metabolize_counterexample(
            organism=self.org, secret_key_hex=self.sk, public_key_hex=self.pk,
            verifier=verifier, **kw)

    def assertRefused(self, outcome, before, expected_status=MetabolismStatus.REFUSED):
        self.assertEqual(outcome.status, expected_status, outcome.verdict.reason)
        self.assertFalse(outcome.granted())
        self.assertIsNone(outcome.retirement)
        self.assertEqual(outcome.gas_bounty, 0)
        self.assertEqual(self.state(), before,
                         f"state moved on a refusal: {outcome.verdict.reason}")

    # ---------------------------------------------------------------- A ---

    def test_A0_the_fixture_is_what_the_engine_computes(self):
        obs = observe_divergence(PARENT, CANDIDATE, INPUT)
        self.assertEqual(obs.status, ObservationStatus.DIVERGES)
        self.assertEqual((obs.parent_output, obs.candidate_output, obs.atp_required),
                         (PARENT_OUT, CANDIDATE_OUT, ATP))

    def test_A1_a_real_divergence_is_metabolized_with_its_effects(self):
        before = self.state()
        out = self.metabolize()
        self.assertTrue(out.granted(), out.verdict.reason)
        claims, tombs, atp, bounties = self.state()
        self.assertEqual(claims, before[0] + 1)
        self.assertEqual(tombs, before[1] + 1)
        self.assertEqual(atp, before[2] + out.gas_bounty)
        self.assertEqual(bounties, before[3] + out.gas_bounty)
        self.assertGreater(out.gas_bounty, 0)
        self.assertEqual(self.org.claims[-1].claim_id, out.claim.claim_id)
        self.assertFalse(self.org.tombstone_registry.is_admitted("x y -> y x"))

    def test_A2_the_credited_claim_passes_an_independent_audit(self):
        """PASS must correspond to that same claim, not to this call's say-so."""
        out = self.metabolize()
        self.assertTrue(out.granted(), out.verdict.reason)
        fresh = WarrantVerifier(TrustConfig()).audit_claim(out.claim)
        self.assertEqual(fresh.status, VerificationStatus.PASS, fresh.reason)
        self.assertEqual(fresh.details["parent_output"], PARENT_OUT)
        self.assertEqual(fresh.details["successor_output"], CANDIDATE_OUT)

    def test_A3_the_tombstone_names_the_evidence_it_rests_on(self):
        out = self.metabolize()
        loss = out.retirement.loss_declaration
        for fragment in (PARENT, CANDIDATE, INPUT, PARENT_OUT, CANDIDATE_OUT,
                         out.claim.claim_id):
            self.assertIn(fragment, loss)
        self.assertTrue(out.retirement.verify_signature())

    # ---------------------------------------------------------------- B ---

    def test_B1_a_wrong_endpoint_is_refused_and_costs_nothing(self):
        before = self.state()
        self.assertRefused(self.metabolize(parent_term="🤍"), before)

    def test_B2_swapped_result_roles_are_refused(self):
        before = self.state()
        out = self.metabolize(expected_norm=CANDIDATE_OUT, actual_norm=PARENT_OUT)
        self.assertRefused(out, before)

    def test_B3_an_understated_cost_is_refused(self):
        before = self.state()
        out = self.metabolize(atp_cost=0)
        self.assertRefused(out, before)
        self.assertIn("atp", out.verdict.reason.lower())

    def test_B4_a_malformed_input_is_refused(self):
        before = self.state()
        for bad in ("((", ")", ""):
            with self.subTest(input_fixture=bad):
                out = self.metabolize(input_fixture=bad)
                self.assertRefused(out, before)
                self.assertIn("parse", out.verdict.reason.lower())

    def test_B5_a_suspended_computation_grants_nothing(self):
        """Bounded non-termination is UNVERIFIED, and UNVERIFIED buys nothing."""
        before = self.state()
        tight = WarrantVerifier(TrustConfig(max_atp_budget=300))
        out = self.metabolize(verifier=tight, parent_term=DIVERGENT_HEAD,
                              candidate_term="🔁 🖤")
        self.assertRefused(out, before, MetabolismStatus.UNVERIFIED)
        self.assertIn("budget", out.verdict.reason.lower())

    def test_B6_an_evaluator_failure_grants_nothing(self):
        before = self.state()
        original = glyph.evaluate

        def exploding(*a, **k):
            raise RuntimeError("engine failure")

        glyph.evaluate = exploding
        try:
            out = self.metabolize()
        finally:
            glyph.evaluate = original
        self.assertRefused(out, before, MetabolismStatus.UNVERIFIED)
        self.assertIn("RuntimeError", out.verdict.reason)

    def test_B7_outputs_that_coincide_are_refused(self):
        before = self.state()
        out = self.metabolize(candidate_term=PARENT, actual_norm=PARENT_OUT)
        self.assertRefused(out, before)
        self.assertIn("coincide", out.verdict.reason.lower())

    def test_B8_a_refusal_leaves_the_rule_usable(self):
        """No tombstone means the resurrection gate does not fire on hearsay."""
        self.metabolize(parent_term="🤍")
        self.assertTrue(self.org.tombstone_registry.is_admitted("x y -> y x"))

    # ---------------------------------------------------------------- C ---

    def test_C1_identifiers_cannot_stand_in_for_endpoints(self):
        """The historical shape, now refused rather than credited."""
        before = self.state()
        for gene, rule, inp, exp, act, atp in (
                ("GENE-EXP-REWRITE-01", "x y -> y x", INPUT, "🤍", "🖤 🤍", 4),
                ("MUTATION_TEST", "K I (S K)", "x", "x", "divergence", 15),
                ("GENESIS_K", "K I (S K)", "x", "x", "y", 20),
                ("GENESIS_I", "I x", "x", "x", "divergence", 10)):
            with self.subTest(gene_id=gene, rule=rule):
                out = self.metabolize(gene_id=gene, rule_name=rule, parent_term=gene,
                                      candidate_term=rule, input_fixture=inp,
                                      expected_norm=exp, actual_norm=act, atp_cost=atp)
                self.assertRefused(out, before)

    def test_C2_those_identifiers_do_parse(self):
        """Parseability was never the problem; adequacy as an endpoint was."""
        self.assertIsNotNone(glyph.parse("GENESIS_K"))
        self.assertIsNotNone(glyph.parse("x y -> y x"))
        settled = glyph.evaluate(glyph.parse("GENESIS_K (x)"), max_atp=1000)
        self.assertTrue(settled.is_settled())
        self.assertEqual(str(settled.term), "GENESIS_K x")

    def test_C3_the_old_call_shapes_cannot_silently_survive(self):
        """
        Neither old shape can bind. What stops them is the two new required
        parameters, not the keyword-only marker: the positional call fails on
        arity and the keyword call on the missing names. The `*` is kept as
        defense against a future mis-ordered positional call, and this test does
        not claim to exercise that.
        """
        with self.assertRaises(TypeError):
            CounterexampleMetabolism.metabolize_counterexample(
                self.org, "GENESIS_K", "K I (S K)", "x", "x", "y", 20,
                self.sk, self.pk)
        with self.assertRaises(TypeError):
            CounterexampleMetabolism.metabolize_counterexample(
                organism=self.org, gene_id="G1", rule_name="r",
                input_fixture=INPUT, expected_norm=PARENT_OUT,
                actual_norm=CANDIDATE_OUT, atp_cost=ATP,
                secret_key_hex=self.sk, public_key_hex=self.pk)
        self.assertEqual(self.state(), (0, 0, 500, 0))

    def test_B9_an_endpoint_that_is_not_a_term_is_refused(self):
        """
        The endpoint used to be composed into the input's source text, so an
        empty parent vanished and the input's own behaviour was credited to a
        function nobody supplied. Directly through the API, not only the CLI.
        """
        before = self.state()
        for field, bad in [(f, b) for f in ("parent_term", "candidate_term")
                           for b in ("", " ", "\t")]:
            with self.subTest(**{field: bad}):
                out = self.metabolize(**{field: bad})
                self.assertRefused(out, before)
                self.assertIn("parse", out.verdict.reason.lower())

    def test_B10_the_observation_calls_it_unparseable(self):
        for bad in ("", " ", "\t", "("):
            with self.subTest(endpoint=bad):
                self.assertEqual(observe_divergence(bad, CANDIDATE, INPUT).status,
                                 ObservationStatus.UNPARSEABLE)
                self.assertEqual(observe_divergence(PARENT, bad, INPUT).status,
                                 ObservationStatus.UNPARSEABLE)

    # ---------------------------------------------------------------- D ---

    def test_D1_an_observation_is_not_a_grant(self):
        obs = observe_divergence(PARENT, CANDIDATE, INPUT)
        self.assertTrue(obs.diverges())
        self.assertEqual(self.state(), (0, 0, 500, 0))
        # It is not accepted as evidence either: there is no parameter for it.
        with self.assertRaises(TypeError):
            self.metabolize(observation=obs)

    def test_D2_observation_statuses_are_distinct(self):
        cases = {
            observe_divergence(PARENT, CANDIDATE, INPUT).status: ObservationStatus.DIVERGES,
            observe_divergence(PARENT, PARENT, INPUT).status: ObservationStatus.COINCIDES,
            observe_divergence(PARENT, CANDIDATE, "((").status: ObservationStatus.UNPARSEABLE,
            observe_divergence(DIVERGENT_HEAD, "🔁 🖤", INPUT,
                               max_atp=300).status: ObservationStatus.INCOMPLETE,
        }
        self.assertEqual(len(cases), 4)
        for got, expected in cases.items():
            self.assertEqual(got, expected)

    def test_D3_a_forged_verdict_on_the_outcome_buys_nothing(self):
        """The outcome records what happened; it is not a token to spend."""
        before = self.state()
        out = self.metabolize(parent_term="🤍")
        out.status = MetabolismStatus.METABOLIZED
        out.verdict.status = VerificationStatus.PASS
        self.assertEqual(self.state(), before)
        replay = WarrantVerifier(TrustConfig()).audit_claim(out.claim)
        self.assertEqual(replay.status, VerificationStatus.FAIL, replay.reason)


class InoculateCliTest(unittest.TestCase):
    """
    The command-line adapter, driven as a process through the real parser.

    The library was repaired first and the adapter kept demonstration defaults,
    so `swarm inoculate --origin X --target-term "I x -> x"` retired that label
    on a K versus K I divergence the caller never supplied: exit 0, a claim that
    independently audits PASS, a REFUTED tombstone and +70 ATP. A true
    counterexample about another pair does not refute the named subject. Fixed
    by requiring the subject and all three operands, with the demonstration on
    its own `--demo` flag.
    """

    CLI = os.path.join(_HERE, "cli.py")

    @classmethod
    def setUpClass(cls):
        cls._dir = tempfile.TemporaryDirectory()
        cls.pristine = os.path.join(cls._dir.name, "pristine.json")
        proc = cls.cli("swarm", "init", "--population", "1", "-o", cls.pristine)
        assert proc.returncode == 0, proc.stderr
        with open(cls.pristine, "rb") as fh:
            cls.pristine_bytes = fh.read()
        cls.origin = next(iter(json.loads(cls.pristine_bytes.decode())["organisms"]))

    @classmethod
    def tearDownClass(cls):
        cls._dir.cleanup()

    @classmethod
    def cli(cls, *args):
        return subprocess.run([sys.executable, "-B", cls.CLI, *args], cwd=_HERE,
                              capture_output=True, text=True, timeout=120)

    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.state = os.path.join(self.work.name, "swarm.json")
        with open(self.state, "wb") as fh:
            fh.write(self.pristine_bytes)
        self.out = os.path.join(self.work.name, "out.json")

    def inoculate(self, *args, output=True):
        argv = ["swarm", "inoculate", self.state, "--origin", self.origin, *args]
        if output:
            argv += ["-o", self.out]
        return self.cli(*argv)

    def organism(self, path):
        with open(path) as fh:
            return json.load(fh)["organisms"][self.origin]

    def assertUntouched(self, proc):
        """A refusal writes nothing: not the input state, not the output file."""
        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        with open(self.state, "rb") as fh:
            self.assertEqual(fh.read(), self.pristine_bytes,
                             "state file changed on a refusal")
        self.assertFalse(os.path.exists(self.out),
                         "an output file was created on a refusal")

    # -- positive ---------------------------------------------------------

    def test_E1_explicit_operands_earn_the_stated_effects(self):
        proc = self.inoculate("--target-term", "K I (S K)", "--parent-term", PARENT,
                              "--candidate-term", CANDIDATE, "--input-expr", INPUT)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        before, after = self.organism(self.state), self.organism(self.out)
        self.assertEqual(len(before["claims"]), 0)
        self.assertEqual(len(after["claims"]), 1)
        self.assertIn("K I (S K)", after["tombstones"]["tombstones"])
        self.assertGreater(after["atp_reserve"], before["atp_reserve"])

        from warrant_kernel import EdgeClaim
        claim = EdgeClaim.from_dict(after["claims"][0])
        self.assertEqual((claim.omega, claim.tau), (PARENT, CANDIDATE))
        verdict = WarrantVerifier(TrustConfig()).audit_claim(claim)
        self.assertEqual(verdict.status, VerificationStatus.PASS, verdict.reason)

    def test_E2_the_demonstration_retires_the_term_it_refuted(self):
        """The demo has evidence about one pair, so it names no other subject."""
        proc = self.inoculate("--demo")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        after = self.organism(self.out)
        self.assertEqual(list(after["tombstones"]["tombstones"]), [CANDIDATE])

    # -- refusals ---------------------------------------------------------

    def test_E3_omitted_operands_refuse_before_any_effect(self):
        complete = {"--target-term": "I x -> x", "--parent-term": PARENT,
                    "--candidate-term": CANDIDATE, "--input-expr": INPUT}
        for dropped in list(complete):
            with self.subTest(missing=dropped):
                argv = [a for k, v in complete.items() if k != dropped for a in (k, v)]
                proc = self.inoculate(*argv)
                self.assertUntouched(proc)
                self.assertIn(dropped, proc.stdout)
                self.assertIn("REFUSED", proc.stdout)

    def test_E4_no_operands_at_all_is_the_reviewer_reproducer(self):
        """`--origin X --target-term 'I x -> x'` used to retire that label."""
        proc = self.inoculate("--target-term", "I x -> x")
        self.assertUntouched(proc)
        self.assertNotIn(CANDIDATE, proc.stdout)

    def test_E5_the_demo_flag_takes_no_operands(self):
        for extra in (("--parent-term", PARENT), ("--target-term", "I x -> x"),
                      ("--candidate-term", CANDIDATE), ("--input-expr", INPUT)):
            with self.subTest(extra=extra[0]):
                proc = self.inoculate("--demo", *extra)
                self.assertUntouched(proc)
                self.assertIn("--demo takes no operands", proc.stdout)

    def test_E6_coinciding_outputs_refuse_and_preserve_state(self):
        proc = self.inoculate("--target-term", "K I (S K)", "--parent-term", PARENT,
                              "--candidate-term", PARENT, "--input-expr", INPUT)
        self.assertUntouched(proc)
        self.assertIn("COINCIDES", proc.stdout)

    def test_E7_malformed_input_refuses_and_preserves_state(self):
        for bad in ("((", ")", "\U0001f5a4 ("):
            with self.subTest(input_expr=bad):
                proc = self.inoculate("--target-term", "K I (S K)", "--parent-term", PARENT,
                                      "--candidate-term", CANDIDATE, "--input-expr", bad)
                self.assertUntouched(proc)
                self.assertIn("UNPARSEABLE", proc.stdout)

    def test_E9_an_empty_or_blank_endpoint_refuses_and_preserves_both_files(self):
        """
        R2 through the real CLI. A pre-existing output file must survive too,
        not merely be absent.
        """
        complete = {"--target-term": "label", "--parent-term": PARENT,
                    "--candidate-term": CANDIDATE, "--input-expr": INPUT}
        for flag in ("--parent-term", "--candidate-term", "--input-expr"):
            for blank in ("", " ", "\t"):
                with self.subTest(flag=flag, value=repr(blank)):
                    with open(self.out, "wb") as fh:
                        fh.write(b"existing output sentinel")
                    argv = [a for k, v in complete.items()
                            for a in (k, blank if k == flag else v)]
                    proc = self.inoculate(*argv)
                    self.assertNotEqual(proc.returncode, 0, proc.stdout)
                    with open(self.state, "rb") as fh:
                        self.assertEqual(fh.read(), self.pristine_bytes)
                    with open(self.out, "rb") as fh:
                        self.assertEqual(fh.read(), b"existing output sentinel")

    def test_E10_an_independent_pair_still_earns_its_claim(self):
        """Not the demonstration pair: I versus K on x."""
        proc = self.inoculate("--target-term", "candidate-K", "--parent-term", "🤍",
                              "--candidate-term", "🖤", "--input-expr", "x")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        after = self.organism(self.out)
        from warrant_kernel import EdgeClaim
        claim = EdgeClaim.from_dict(after["claims"][0])
        self.assertEqual((claim.omega, claim.tau), ("🤍", "🖤"))
        self.assertEqual(WarrantVerifier(TrustConfig()).audit_claim(claim).status,
                         VerificationStatus.PASS)
        self.assertIn("candidate-K", after["tombstones"]["tombstones"])
        with open(self.state, "rb") as fh:
            self.assertEqual(fh.read(), self.pristine_bytes)

    def test_E11_the_demonstration_replay_and_bounty_are_unchanged(self):
        """Measured before the R2 repair and pinned here unchanged."""
        proc = self.inoculate("--demo")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        before, after = self.organism(self.state), self.organism(self.out)
        from warrant_kernel import EdgeClaim
        claim = EdgeClaim.from_dict(after["claims"][0])
        self.assertEqual((claim.omega, claim.tau), (PARENT, CANDIDATE))
        self.assertEqual(claim.witness.input_expr, INPUT)
        self.assertEqual((claim.witness.expected_normal_form,
                          claim.witness.actual_divergence,
                          claim.witness.atp_to_diverge),
                         (PARENT_OUT, CANDIDATE_OUT, ATP))
        self.assertEqual(after["atp_reserve"] - before["atp_reserve"], 91)

    def test_E8_a_non_divergence_refuses_even_in_place(self):
        """Without -o the state path is its own output; it must survive too."""
        proc = self.inoculate("--target-term", "K I (S K)", "--parent-term", PARENT,
                              "--candidate-term", PARENT, "--input-expr", INPUT,
                              output=False)
        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        with open(self.state, "rb") as fh:
            self.assertEqual(fh.read(), self.pristine_bytes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
