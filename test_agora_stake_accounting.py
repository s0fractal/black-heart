#!/usr/bin/env python3
"""
Regression: tabling a proposal on the Agora actually debits the organism, once.

Audit S6b: `morpho_autopoiesis.table_to_agora`, the one path where a
morpho-autopoietic organism spends ATP on an Agora submission.

Measured at 7259a36, stake 150, five submissions of the same theorem:

  #   file atp_reserve   agora records   sum of claimed stakes   proposal_id
  1   1230              2               150                     prop_morpho_s(k x)i -> x_1
  5   1230              6               750                     (the same id every time)

750 ATP of stakes claimed against a balance that never moved, five records
under one id, and `audit_morpho_autopoietic_organism` and
`audit_agora_parliament` both still returned True. Cause: `org.atp_reserve -=
stake_atp` mutated memory only -- nothing wrote the organism back, and only
`grow_agora_page` touched disk. The engine's own duplicate-id and sufficiency
checks (agora.py) were correct but ran on a FRESH engine registered from the
file balance, so they never saw a previous submission.

Fix: the debit is its own signed step in the receipt chain (`AGORA_STAKE`),
never a re-signing of an earlier receipt, and it is written BEFORE publishing.
It needs no new signed field -- `tabled_proposal_id` and `agora_atp_staked` are
already inside `canonical_bytes_for_signing` -- so the accepted domain of
existing state does not change.

Write order is debit then publish, chosen by which partial failure is safer:
publishing first would leave a proposal backed by a stake never taken (the
defect, made permanent). Debiting first can leave a stake taken whose
publication did not land; the next call RESUMES it and never debits twice. No
automatic refund: the Agora write may have landed before the error surfaced.

Scope: this is a guarantee about THIS submission path. It does not establish
that every record already on an Agora floor is backed. Votes and quorum are a
separate package and are not touched.

Sections:
  A  the honest submission, and what the stake step binds
  B  the four failure controls: repeat, before debit, between writes, after publish
  C  preconditions checked before the first write
  D  the auditor rejects forged stake accounting
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from unittest import mock

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
from agora import initialize_agora_assembly, audit_agora_parliament, AGORA_MANIFEST_PREFIX
from keystore import PRIVATE_KEY_SUFFIX

if os.path.dirname(os.path.abspath(M.__file__)) != _HERE:
    raise ImportError(f"morpho_autopoiesis resolved to {M.__file__}, outside {_HERE}")

STAKE = 150


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


class _Floor(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.d = self._tmp.name
        self.org_pdf = os.path.join(self.d, "org.pdf")
        self.agora_pdf = os.path.join(self.d, "agora.pdf")
        M.init_morpho_autopoietic_organism(self.org_pdf)
        with open(self.org_pdf + PRIVATE_KEY_SUFFIX) as f:
            self.sk = f.read().strip()
        M.evolve_morpho_autopoietic_organism(self.org_pdf, secret_key_hex=self.sk)
        initialize_agora_assembly(self.agora_pdf)

    # -- observations -------------------------------------------------------
    def reserve(self):
        return M._read_organism(self.org_pdf).atp_reserve

    def records(self):
        return len(M._agora_records(self.agora_pdf))

    def snapshot(self):
        return read_bytes(self.org_pdf), read_bytes(self.agora_pdf)

    def table(self, **kw):
        kw.setdefault("secret_key_hex", self.sk)
        kw.setdefault("stake_atp", STAKE)
        return M.table_to_agora(self.org_pdf, self.agora_pdf, **kw)

    def stabilize(self, limit=30):
        """Evolve until the genome stops changing, so a later `evolve` appends a
        NO_MUTATION_FOUND receipt without altering the theorem."""
        for _ in range(limit):
            _, rec = M.evolve_morpho_autopoietic_organism(self.org_pdf, secret_key_hex=self.sk)
            if rec.rule_name == M.NO_MUTATION_FOUND_RULE:
                return
        self.fail("genome did not stabilize")

    def fail_publish(self):
        """Debit lands, publication does not."""
        with mock.patch.object(M, "grow_agora_page", side_effect=OSError("injected")):
            with self.assertRaises(OSError):
                self.table()

    def assertSound(self):
        self.assertTrue(M.audit_morpho_autopoietic_organism(self.org_pdf), "organism audit")
        self.assertTrue(audit_agora_parliament(self.agora_pdf), "agora audit")


class HonestSubmissionTest(_Floor):
    """Section A."""

    def test_A1_one_submission_debits_exactly_once(self):
        before_reserve, before_records = self.reserve(), self.records()
        _, pid = self.table()
        self.assertEqual(self.reserve(), before_reserve - STAKE, "the file balance did not move")
        self.assertEqual(self.records(), before_records + 1)
        self.assertIn(pid, M._agora_proposal_ids(self.agora_pdf))
        self.assertSound()

    def test_A2_the_debit_is_its_own_signed_step_and_rewrites_nothing(self):
        org_before = M._read_organism(self.org_pdf)
        prior = org_before.receipt_chain[-1].to_dict()
        _, pid = self.table()
        org = M._read_organism(self.org_pdf)

        stake = org.receipt_chain[-1]
        self.assertEqual(stake.rule_name, M.AGORA_STAKE_RULE)
        self.assertEqual(stake.tabled_proposal_id, pid, "the step must name the submission it paid for")
        self.assertEqual(stake.agora_atp_staked, STAKE)
        self.assertEqual(stake.resulting_atp_reserve, org_before.atp_reserve - STAKE)
        self.assertEqual(stake.parent_hash, org_before.organism_hash, "it must bind the previous state")
        self.assertTrue(stake.verify(), "the step is signed by the organism")
        self.assertEqual(stake.atp_saved, 0, "a stake proves nothing and earns nothing")
        # the earlier receipt is untouched -- no re-signing of history
        self.assertEqual(org.receipt_chain[-2].to_dict(), prior)

    def test_A3_submission_identity_is_stable_and_organism_specific(self):
        """Rule name plus generation is not enough: a second organism reaching
        the same rule at the same generation must not collide."""
        _, pid = self.table()
        other = os.path.join(self.d, "other.pdf")
        M.init_morpho_autopoietic_organism(other)
        with open(other + PRIVATE_KEY_SUFFIX) as f:
            other_sk = f.read().strip()
        _, rec = M.evolve_morpho_autopoietic_organism(other, secret_key_hex=other_sk)
        theorem = M._latest_theorem(M._read_organism(self.org_pdf))
        self.assertEqual(rec.rule_name, theorem.rule_name)
        self.assertEqual(rec.generation, theorem.generation)
        _, other_pid = M.table_to_agora(other, self.agora_pdf, secret_key_hex=other_sk, stake_atp=STAKE)
        self.assertNotEqual(other_pid, pid, "different organisms must not share a submission id")


    def test_A4_the_agora_identity_distinguishes_documents(self):
        """Pins WHY the identity is the founder key. The obvious choice, the
        genesis receipt_hash, is wrong: two independently created floors carry
        the IDENTICAL one, because the ratified constitution is deterministic
        content and that hash does not cover the founder's signature. A stake
        taken for one floor could then be resumed onto another."""
        other = os.path.join(self.d, "other_floor.pdf")
        initialize_agora_assembly(other)
        self.assertNotEqual(M._agora_identity(self.agora_pdf), M._agora_identity(other),
                            "two floors must not share an identity")
        # Structural, not timing-dependent: the identity must not BE the
        # receipt_hash. (Measured while choosing it: two floors created in the
        # same second carry the identical genesis receipt_hash, because the
        # ratified constitution is deterministic and that hash covers neither
        # the founder's signature nor anything else unique. Asserting that
        # equality directly would be flaky -- the genesis timestamp comes from
        # the clock, so it only holds inside one second. This asserts the
        # property that actually matters instead.)
        a = M._agora_records(self.agora_pdf)[0]
        self.assertNotEqual(M._agora_identity(self.agora_pdf), a["receipt_hash"],
                            "identity must not be the genesis receipt_hash")
        self.assertEqual(M._agora_identity(self.agora_pdf),
                         a["proposal"]["author_public_key"],
                         "identity is the founder key")
        before = M._agora_identity(self.agora_pdf)
        self.table()
        self.assertEqual(M._agora_identity(self.agora_pdf), before,
                         "identity must survive the floor growing")


class FailureControlTest(_Floor):
    """Section B: the four controls named in the review."""

    def test_B1_repeat_after_success_is_refused_and_debits_nothing(self):
        _, pid = self.table()
        reserve, records = self.reserve(), self.records()
        with self.assertRaises(ValueError) as caught:
            self.table()
        self.assertIn("already tabled", str(caught.exception))
        self.assertEqual(self.reserve(), reserve, "a refused repeat debited again")
        self.assertEqual(self.records(), records, "a refused repeat published again")
        self.assertSound()

    def test_B2_failure_before_the_debit_leaves_both_files_byte_identical(self):
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.table(stake_atp=0)
        self.assertEqual(self.snapshot(), before, "a pre-debit refusal wrote something")

    def test_B3_failure_between_the_writes_resumes_without_debiting_twice(self):
        """The debit landed, publication did not. The next call must publish the
        SAME submission and take no second stake."""
        before_reserve, before_records = self.reserve(), self.records()
        agora_before = read_bytes(self.agora_pdf)
        with mock.patch.object(M, "grow_agora_page", side_effect=RuntimeError("floor unreachable")):
            with self.assertRaises(RuntimeError):
                self.table()
        self.assertEqual(self.reserve(), before_reserve - STAKE, "the debit should have landed")
        self.assertEqual(read_bytes(self.agora_pdf), agora_before, "the floor should be untouched")
        self.assertTrue(M.audit_morpho_autopoietic_organism(self.org_pdf))

        _, pid = self.table()                       # resume
        self.assertEqual(self.reserve(), before_reserve - STAKE, "resuming debited a second time")
        self.assertEqual(self.records(), before_records + 1)
        self.assertIn(pid, M._agora_proposal_ids(self.agora_pdf))
        self.assertSound()

    def test_B4_failure_after_the_agora_write_refuses_and_does_not_debit_twice(self):
        """The Agora record really landed; the call then failed before returning.
        A retry must be refused as a duplicate, not debited again."""
        real = M.grow_agora_page

        def land_then_fail(*a, **k):
            real(*a, **k)
            raise RuntimeError("crashed after publishing")

        before_reserve = self.reserve()
        with mock.patch.object(M, "grow_agora_page", side_effect=land_then_fail):
            with self.assertRaises(RuntimeError):
                self.table()
        after_reserve, after_records = self.reserve(), self.records()
        self.assertEqual(after_reserve, before_reserve - STAKE)

        with self.assertRaises(ValueError) as caught:
            self.table()
        self.assertIn("already tabled", str(caught.exception))
        self.assertEqual(self.reserve(), after_reserve, "a retry debited a second time")
        self.assertEqual(self.records(), after_records, "a retry published a second time")
        self.assertSound()

    def test_B5_an_unconfirmed_debit_aimed_at_a_different_agora_is_refused_by_name(self):
        with mock.patch.object(M, "grow_agora_page", side_effect=RuntimeError("floor unreachable")):
            with self.assertRaises(RuntimeError):
                self.table()
        reserve = self.reserve()
        elsewhere = os.path.join(self.d, "elsewhere.pdf")
        initialize_agora_assembly(elsewhere)
        with self.assertRaises(ValueError) as caught:
            M.table_to_agora(self.org_pdf, elsewhere, secret_key_hex=self.sk, stake_atp=STAKE)
        msg = str(caught.exception)
        self.assertIn("already debited", msg)
        self.assertIn("refunding is unsafe", msg)
        self.assertEqual(self.reserve(), reserve, "the refusal debited again")
        self.assertEqual(len(M._agora_records(elsewhere)), 1, "nothing was published elsewhere")


    def test_B6_a_floor_impersonating_another_founder_is_refused_before_any_write(self):
        """Security scan of e549de3, `improper-authentication.agora-genesis-identity`,
        reproduced: a second floor whose genesis `author_public_key` is changed
        to the victim floor's -- and NOTHING else -- still passes
        `audit_agora_parliament`, because the settlement hash does not cover the
        proposal author and that audit skips the genesis signature. It then
        derived the victim's identity, and the stake already published on the
        victim was re-published on it with NO second debit (measured: balance
        1080 -> 1080). The founder key is now authenticated against the genesis
        signature before it can stand for a floor."""
        _, pid = self.table()
        balance, records = self.reserve(), self.records()
        before = self.snapshot()

        impostor = os.path.join(self.d, "impostor.pdf")
        initialize_agora_assembly(impostor)
        victim_founder = M._agora_records(self.agora_pdf)[0]["proposal"]["author_public_key"]
        raw = read_bytes(impostor)
        pre = AGORA_MANIFEST_PREFIX.encode("utf-8")
        idx = raw.rfind(pre); end = raw.index(b"\n", idx)
        recs = json.loads(raw[idx + len(pre):end].decode("utf-8"))
        recs[0]["proposal"]["author_public_key"] = victim_founder
        with open(impostor, "wb") as f:
            f.write(raw[:idx] + pre + json.dumps(recs).encode("utf-8") + raw[end:])

        self.assertTrue(audit_agora_parliament(impostor),
                        "the impostor must still pass agora's own audit -- that is the point")
        with self.assertRaises(ValueError) as caught:
            M.table_to_agora(self.org_pdf, impostor, secret_key_hex=self.sk, stake_atp=STAKE)
        self.assertIn("not authenticated", str(caught.exception))
        self.assertEqual(self.snapshot(), before, "the refusal wrote something")
        self.assertEqual(self.reserve(), balance)
        self.assertEqual(self.records(), records)
        self.assertEqual(len(M._agora_records(impostor)), 1, "nothing was published on the impostor")

    def test_B7_concurrent_submissions_debit_once_and_publish_once(self):
        """Security scan of e549de3, `race-condition.agora-stake-publication`:
        two calls that both read before either writes would each append a
        successor (last-manifest-wins hiding one debit) and each publish,
        leaving two records for one debit. The critical section is now
        serialized, so exactly one submission lands."""
        before_reserve, before_records = self.reserve(), self.records()
        start = threading.Barrier(2)
        outcomes = []

        def submit():
            start.wait()
            try:
                outcomes.append(("ok", self.table()[1]))
            except Exception as exc:                     # noqa: BLE001 - recorded, not swallowed
                outcomes.append(("refused", f"{type(exc).__name__}: {exc}"))

        threads = [threading.Thread(target=submit) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=120)

        kinds = sorted(k for k, _ in outcomes)
        self.assertEqual(kinds, ["ok", "refused"], f"expected one of each, got {outcomes}")
        self.assertEqual(self.reserve(), before_reserve - STAKE, "the stake was debited more than once")
        self.assertEqual(self.records(), before_records + 1, "the proposal was published more than once")
        self.assertSound()


    def test_B8_an_intervening_evolution_does_not_hide_a_pending_payment(self):
        """Review r1 on PR #28, reproduced: recovery read only receipt_chain[-1],
        so an ordinary `evolve` appended after a failed publication pushed the
        pending stake off the end and the retry took a SECOND 150 ATP. Measured
        on 9ba10df: total_debit 300, two stake receipts for one submission id,
        one published record, and both audits still passed."""
        self.stabilize()
        before_reserve, before_records = self.reserve(), self.records()

        self.fail_publish()
        self.assertEqual(self.reserve(), before_reserve - STAKE)

        _, interleaved = M.evolve_morpho_autopoietic_organism(self.org_pdf, secret_key_hex=self.sk)
        self.assertEqual(interleaved.rule_name, M.NO_MUTATION_FOUND_RULE,
                         "the intervening step must not change the theorem")

        _, pid = self.table()                                  # retry: must RESUME
        org = M._read_organism(self.org_pdf)
        stakes = [r for r in org.receipt_chain
                  if r.rule_name == M.AGORA_STAKE_RULE and r.tabled_proposal_id == pid]
        self.assertEqual(len(stakes), 1, "the submission was paid twice")
        self.assertEqual(self.reserve(), before_reserve - STAKE, "total debit must stay one stake")
        self.assertEqual(self.records(), before_records + 1)
        self.assertSound()

    def test_B9_a_new_theorem_does_not_silently_strand_an_older_payment(self):
        """After a failed publication, evolving to a DIFFERENT theorem must not
        quietly abandon the ATP already paid for the first one."""
        before_reserve = self.reserve()
        first_theorem = M._latest_theorem(M._read_organism(self.org_pdf))
        self.fail_publish()
        self.assertEqual(self.reserve(), before_reserve - STAKE)

        _, new_rec = M.evolve_morpho_autopoietic_organism(self.org_pdf, secret_key_hex=self.sk)
        self.assertNotEqual(new_rec.rule_name, M.NO_MUTATION_FOUND_RULE,
                            "this control needs a genuinely new theorem")
        self.assertNotEqual(new_rec.organism_hash, first_theorem.organism_hash)

        reserve, records = self.reserve(), self.records()
        before = self.snapshot()
        with self.assertRaises(ValueError) as caught:
            self.table()
        msg = str(caught.exception)
        self.assertIn("already debited", msg)
        self.assertIn("stranded", msg)
        self.assertEqual(self.reserve(), reserve, "the refusal debited again")
        self.assertEqual(self.records(), records)
        self.assertEqual(self.snapshot(), before, "the refusal wrote something")


class PreconditionTest(_Floor):
    """Section C: everything checked before the first write."""

    def test_C1_the_stake_must_be_a_strictly_positive_int_and_never_a_bool(self):
        for bad in (0, -1, True, False, 1.5, "150", None):
            with self.subTest(stake=bad):
                before = self.snapshot()
                with self.assertRaises(ValueError):
                    self.table(stake_atp=bad)
                self.assertEqual(self.snapshot(), before)

    def test_C2_a_key_that_is_not_this_organisms_cannot_stake_its_atp(self):
        other = os.path.join(self.d, "other.pdf")
        M.init_morpho_autopoietic_organism(other)
        with open(other + PRIVATE_KEY_SUFFIX) as f:
            foreign_sk = f.read().strip()
        before = self.snapshot()
        with self.assertRaises(ValueError) as caught:
            self.table(secret_key_hex=foreign_sk)
        self.assertIn("does not belong to this organism", str(caught.exception))
        self.assertEqual(self.snapshot(), before)

    def test_C3_insufficient_balance_is_refused_before_any_write(self):
        before = self.snapshot()
        with self.assertRaises(ValueError) as caught:
            self.table(stake_atp=10 ** 9)
        self.assertIn("Insufficient ATP", str(caught.exception))
        self.assertEqual(self.snapshot(), before)

    def test_C4_a_tampered_agora_is_refused_before_any_write(self):
        """Appending junk after the manifest is NOT tampering -- the reader takes
        the last manifest, so the floor stays sound (measured: my first version
        of this test asserted a refusal that never fired). Corrupt the manifest
        itself, and assert the fixture really is invalid before asserting the
        refusal."""
        from agora import AGORA_MANIFEST_PREFIX
        raw = read_bytes(self.agora_pdf)
        pre = AGORA_MANIFEST_PREFIX.encode("utf-8")
        idx = raw.rfind(pre)
        end = raw.index(b"\n", idx)
        records = json.loads(raw[idx + len(pre):end].decode("utf-8"))
        records[-1]["receipt_hash"] = "0" * 64
        with open(self.agora_pdf, "wb") as f:
            f.write(raw[:idx] + pre + json.dumps(records).encode("utf-8") + raw[end:])

        self.assertFalse(audit_agora_parliament(self.agora_pdf),
                         "the fixture must actually be an invalid floor")
        before = self.snapshot()
        with self.assertRaises(ValueError) as caught:
            self.table()
        self.assertIn("Agora", str(caught.exception))
        self.assertEqual(self.snapshot(), before, "the organism was written despite a bad floor")


    def test_C5_the_whole_balance_cannot_be_staked(self):
        """The scan recorded this as a reliability issue, and it belongs to the
        validate-before-debit promise: staking the entire reserve persists the
        debit and then fails to publish, because the obligatory ballot has no
        ATP left to burn (agora.py refuses a ballot the voter cannot pay)."""
        reserve = self.reserve()
        before = self.snapshot()
        with self.assertRaises(ValueError) as caught:
            self.table(stake_atp=reserve)
        self.assertIn("Insufficient ATP", str(caught.exception))
        self.assertEqual(self.snapshot(), before, "the refusal wrote something")
        # one ATP less still works, so this is a boundary, not a blanket refusal
        _, pid = self.table(stake_atp=reserve - 1)
        self.assertEqual(self.reserve(), 1)
        self.assertSound()


class ForgedAccountingTest(_Floor):
    """Section D: the auditor re-derives the balance across credits and debits."""

    def rewrite_last(self, mutate):
        raw = read_bytes(self.org_pdf)
        pre = M.MORPHO_AUTOPOIESIS_MANIFEST_PREFIX.encode("utf-8")
        idx = raw.rfind(pre)
        end = raw.index(b"\n", idx)
        man = json.loads(raw[idx + len(pre):end].decode("utf-8"))
        mutate(man)
        with open(self.org_pdf, "wb") as f:
            f.write(raw[:idx] + pre + json.dumps(man).encode("utf-8") + raw[end:])

    def test_D1_a_stake_step_claiming_no_amount_is_refused(self):
        self.table()
        def mutate(man):
            rec = M.MorphoAutopoiesisReceipt.from_dict(man["receipt_chain"][-1])
            rec.agora_atp_staked = 0
            rec.resulting_atp_reserve += STAKE
            rec.sign(self.sk)
            man["receipt_chain"][-1] = rec.to_dict()
            man["atp_reserve"] += STAKE
        self.rewrite_last(mutate)
        self.assertFalse(M.audit_morpho_autopoietic_organism(self.org_pdf))

    def test_D2_an_ordinary_evolution_may_not_carry_stake_fields(self):
        """Otherwise a debit could be smuggled through a receipt that looks like
        an evolution -- or a credit inflated by hiding a negative stake."""
        def mutate(man):
            rec = M.MorphoAutopoiesisReceipt.from_dict(man["receipt_chain"][-1])
            self.assertNotEqual(rec.rule_name, M.AGORA_STAKE_RULE)
            rec.agora_atp_staked = -500          # a "debit" that pays the organism
            rec.resulting_atp_reserve += 500
            rec.sign(self.sk)
            man["receipt_chain"][-1] = rec.to_dict()
            man["atp_reserve"] += 500
        self.rewrite_last(mutate)
        self.assertFalse(M.audit_morpho_autopoietic_organism(self.org_pdf))

    def test_D3_the_balance_must_equal_genesis_plus_credits_minus_stakes(self):
        self.table()
        def mutate(man):
            rec = M.MorphoAutopoiesisReceipt.from_dict(man["receipt_chain"][-1])
            rec.resulting_atp_reserve += 1       # keeps the stake, moves the balance
            rec.sign(self.sk)
            man["receipt_chain"][-1] = rec.to_dict()
            man["atp_reserve"] += 1
        self.rewrite_last(mutate)
        self.assertFalse(M.audit_morpho_autopoietic_organism(self.org_pdf))


    def test_D4_one_submission_may_be_paid_only_once_in_a_chain(self):
        """A fully-signed second payment for the same submission id -- the state
        the review's probe produced -- must not audit sound."""
        _, pid = self.table()
        self.assertTrue(M.audit_morpho_autopoietic_organism(self.org_pdf))

        org = M._read_organism(self.org_pdf)
        original = next(r for r in org.receipt_chain
                        if r.rule_name == M.AGORA_STAKE_RULE and r.tabled_proposal_id == pid)
        gene0 = org.chromosomes[0]
        org.parent_hash = org.organism_hash
        org.generation = len(org.receipt_chain)
        org.atp_reserve -= STAKE
        org.organism_hash = org.compute_hash()
        duplicate = M.MorphoAutopoiesisReceipt(
            generation=org.generation, timestamp_utc=original.timestamp_utc,
            parent_hash=org.parent_hash, organism_hash=org.organism_hash,
            gene_id=gene0.gene_id, rule_name=M.AGORA_STAKE_RULE, site_address=[],
            pre_term=gene0.expression, post_term=gene0.expression,
            atp_saved=0, size_saved=0,
            experiment_id=M.derive_experiment_id(gene0.gene_id, (), M.AGORA_STAKE_RULE,
                                                 gene0.expression, gene0.expression),
            experiments_count=len(org.experiment_log.records), archetype=org.archetype_key,
            feed_rate_f=org.feed_rate_f, kill_rate_k=org.kill_rate_k, pde_steps=0,
            initial_nodes=0, reduced_steps=0, net_atp_burned=0,
            weisfeiler_lehman_digest=org.weisfeiler_lehman_digest,
            tabled_proposal_id=pid,                      # the SAME submission
            agora_atp_staked=STAKE, resulting_atp_reserve=org.atp_reserve,
            public_key_hex=org.public_key_hex)
        duplicate.sign(self.sk)
        self.assertTrue(duplicate.verify(), "the duplicate is genuinely signed")
        org.receipt_chain.append(duplicate)
        M._append_manifest_revision(self.org_pdf, org)

        self.assertFalse(M.audit_morpho_autopoietic_organism(self.org_pdf))


if __name__ == "__main__":
    unittest.main()
