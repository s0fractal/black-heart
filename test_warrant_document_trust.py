#!/usr/bin/env python3
"""
Regression: `cli.py warrant-kernel audit` takes its trust root from the
OPERATOR, never from the audited document.

Security scan of e549de3, `improper-authorization.document-trust-policy`
(cli.py). The audit path built its TrustConfig from
`manifest["trust_config"]` -- i.e. from the document being judged -- despite
TrustConfig's own contract ("A verifier's trust root comes from
configuration, never from inside the record"). A supplied warrant PDF could
therefore name its own author trusted (or set trusted_author_pks to
null / {} for trust-all) and an unsigned or unauthorized claim audited as
verified. The author signs with their own key, so signature checks pass:
authenticity of the signer is not authority under the operator's policy.

Measured on pre-fix main: a PDF whose embedded trust_config trusts its own
author audits `[G-GROUNDED] PASS`, exit 0.

Fix: `cli.py warrant-kernel audit` builds the verifier from `--trust-config`
or `--trusted-author-pk`; with neither, it trusts no author (fail closed).
The embedded trust_config is shown as descriptive only. Success requires
every claim VERIFIED under the operator root; an UNVERIFIED claim is a
refusal and exits non-zero.

Sections:
  A  the document's own trust policy cannot grant a PASS
  B  the operator's trust root decides; embedded policy is descriptive
  C  exit status reflects verification, not mere absence of FAIL

Not in scope, named: the self-executing embedded runner (`python3 doc.pdf
--audit`) audits against its own compile-time policy -- a distinct
self-contained trust model, not this operator path.
"""
from __future__ import annotations

import json
import os
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

import glyph
import warrant_kernel as WK
from warrant_kernel import (EdgeClaim, GroundedWitness, Polarity, TrustConfig,
                            generate_warrant_ledger_pdf)
from crypto import generate_keypair

if os.path.dirname(os.path.abspath(WK.__file__)) != _HERE:
    raise ImportError(f"warrant_kernel resolved to {WK.__file__}, outside {_HERE}")

CLI = os.path.join(_HERE, "cli.py")
ENV = dict(os.environ, PYTHONPATH=_HERE, PYTHONDONTWRITEBYTECODE="1")


class _Ledger(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.d = self._tmp.name
        self.sk, self.pk = generate_keypair()
        self.term = "🤍 (🖤 🤍)"
        self.h = glyph.evaluate(glyph.parse(self.term)).hash

    def claim(self, sk=None, pk=None):
        sk = sk or self.sk; pk = pk or self.pk
        return EdgeClaim.create_and_sign("p", "eval", "o", self.h, Polarity.AFFIRM,
                                         GroundedWitness(self.term, self.h), sk, pk)

    def make_pdf(self, claims, embedded_trust):
        pdf = os.path.join(self.d, f"w{abs(hash(str(embedded_trust)))}.pdf")
        generate_warrant_ledger_pdf(claims, pdf, embedded_trust)
        return pdf

    def audit(self, pdf, *extra):
        r = subprocess.run([sys.executable, "-B", CLI, "warrant-kernel", "audit", pdf, *extra],
                           capture_output=True, text=True, env=ENV, cwd=_HERE, timeout=120)
        return r.returncode, r.stdout


class DocumentPolicyTest(_Ledger):
    """Section A."""

    def test_A1_a_document_trusting_its_own_author_does_not_pass(self):
        pdf = self.make_pdf([self.claim()], TrustConfig(trusted_author_pks={self.pk}))
        rc, out = self.audit(pdf)                      # no operator trust root
        self.assertNotIn("PASS", out, "the document's own policy granted a PASS")
        self.assertIn("UNVERIFIED", out)
        self.assertNotEqual(rc, 0)

    def test_A2_a_document_declaring_trust_all_does_not_pass(self):
        # trusted_author_pks null => is_author_trusted True for everyone
        pdf = self.make_pdf([self.claim()], TrustConfig(trusted_author_pks=None))
        rc, out = self.audit(pdf)
        self.assertNotIn("PASS", out)
        self.assertNotEqual(rc, 0)

    def test_A3_the_embedded_policy_is_shown_but_marked_not_used(self):
        pdf = self.make_pdf([self.claim()], TrustConfig(trusted_author_pks={self.pk}))
        _, out = self.audit(pdf)
        self.assertIn("DESCRIPTIVE", out.upper())


class OperatorPolicyTest(_Ledger):
    """Section B."""

    def test_B1_operator_pinning_the_author_verifies(self):
        pdf = self.make_pdf([self.claim()], TrustConfig(trusted_author_pks={self.pk}))
        rc, out = self.audit(pdf, "--trusted-author-pk", self.pk)
        self.assertIn("PASS", out)
        self.assertEqual(rc, 0, out)

    def test_B2_operator_pinning_a_different_author_refuses(self):
        _, other_pk = generate_keypair()
        pdf = self.make_pdf([self.claim()], TrustConfig(trusted_author_pks={self.pk}))
        rc, out = self.audit(pdf, "--trusted-author-pk", other_pk)
        self.assertIn("UNVERIFIED", out)
        self.assertNotEqual(rc, 0)

    def test_B3_a_trust_config_file_is_honored(self):
        cfg = os.path.join(self.d, "trust.json")
        TrustConfig(trusted_author_pks={self.pk}).save_to_file(cfg)
        pdf = self.make_pdf([self.claim()], TrustConfig(trusted_author_pks=set()))
        rc, out = self.audit(pdf, "--trust-config", cfg)
        self.assertIn("PASS", out)
        self.assertEqual(rc, 0, out)

    def test_B4_the_operator_root_overrides_a_hostile_embedded_policy(self):
        """Even if the document says trust-all, the operator's narrow root wins."""
        _, other_pk = generate_keypair()
        pdf = self.make_pdf([self.claim()], TrustConfig(trusted_author_pks=None))
        rc, out = self.audit(pdf, "--trusted-author-pk", other_pk)
        self.assertIn("UNVERIFIED", out)
        self.assertNotEqual(rc, 0)


class ExitStatusTest(_Ledger):
    """Section C."""

    def test_C1_all_verified_exits_zero(self):
        pdf = self.make_pdf([self.claim()], TrustConfig())
        rc, out = self.audit(pdf, "--trusted-author-pk", self.pk)
        self.assertEqual(rc, 0, out)
        self.assertIn("1 verified, 0 rejected, 0 unverified", out)

    def test_C2_an_all_unverified_ledger_does_not_exit_zero(self):
        pdf = self.make_pdf([self.claim()], TrustConfig())
        rc, out = self.audit(pdf)                      # no root => all unverified
        self.assertNotEqual(rc, 0, "an entirely unverified audit reported success")
        self.assertIn("0 verified", out)


if __name__ == "__main__":
    unittest.main()
