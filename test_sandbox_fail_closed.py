#!/usr/bin/env python3
"""
Regression: tools/sandbox.py reports SOUND only on positive confirmation.

Security scan of e549de3, `improper-verification.fail-open-polyglot-auditor`.
`cryptographic_seals_valid` and `hermetic_evaluation_valid` defaulted True and
flipped only on a proven negative, and `is_sound()` required the mere absence
of a negative. So a document with a valid PDF header and binary marker but no
verifiable evidence -- no manifest, a malformed manifest (a parse error only
appended a note), or a signature whose signed content could not be determined
-- was reported SOUND. Measured on pre-fix code: all of those returned SOUND.

Fix: soundness is a POSITIVE confirmation. is_sound requires the container to
be valid, at least one signature or hermetic claim to be positively verified,
and nothing to have failed, been left unconfirmed, or errored.

Sections:
  A  the fail-open cases are now UNSOUND (missing / malformed / unconfirmed)
  B  honest verified evidence (signature, or settled claim) is SOUND
  C  proven negatives remain UNSOUND (mismatch, non-settling claim)
"""
from __future__ import annotations

import json
import os
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
from tools import sandbox
from tools.sandbox import audit_polyglot_hermetic
from crypto import sign_bytes, public_key_from_secret

if os.path.dirname(os.path.abspath(sandbox.__file__)) != os.path.join(_HERE, "tools"):
    raise ImportError(f"sandbox resolved to {sandbox.__file__}, outside {_HERE}/tools")

HEADER = b"%PDF-1.7\n%\xf0\x9f\x96\xa4\n"       # valid header + high-byte binary marker
CONTRACT = "%🖤 CONTRACT_MANIFEST: ".encode("utf-8")


class _Audit(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def sound(self, blob: bytes) -> bool:
        return self.report(blob).is_sound()

    def report(self, blob: bytes):
        path = os.path.join(self._tmp.name, "doc.pdf")
        with open(path, "wb") as f:
            f.write(blob)
        return audit_polyglot_hermetic(path)

    def signed_line(self, payload="hello world"):
        """A single CONTRACT manifest line carrying a genuinely valid signature."""
        sk = os.urandom(32)
        pk = public_key_from_secret(sk)
        sig = sign_bytes(sk, payload.encode("utf-8"))
        m = json.dumps({"public_key_hex": pk.hex(), "signature_hex": sig.hex(),
                        "signed_payload": payload}).encode("utf-8")
        return CONTRACT + m

    def signed_contract(self, payload="hello world"):
        return HEADER + self.signed_line(payload) + b"\n%%EOF\n"

    def doc(self, *manifest_lines):
        """A valid container carrying one or more manifest/claim lines."""
        return HEADER + b"\n".join(manifest_lines) + b"\n%%EOF\n"


class FailOpenClosedTest(_Audit):
    """Section A: what used to be SOUND for free."""

    def test_A1_no_manifest_is_not_sound(self):
        self.assertFalse(self.sound(HEADER + b"just some bytes\n%%EOF\n"))

    def test_A2_malformed_manifest_is_not_sound(self):
        self.assertFalse(self.sound(HEADER + CONTRACT + b"{not valid json}\n%%EOF\n"))

    def test_A3_signature_without_determinable_body_is_not_sound(self):
        m = json.dumps({"public_key_hex": "aa" * 32, "signature_hex": "bb" * 64}).encode("utf-8")
        self.assertFalse(self.sound(HEADER + CONTRACT + m + b"\n%%EOF\n"))

    def test_A4_a_recognized_manifest_carrying_no_seal_is_not_sound(self):
        m = json.dumps({"title": "unsigned", "blocks": []}).encode("utf-8")
        self.assertFalse(self.sound(HEADER + CONTRACT + m + b"\n%%EOF\n"))


class HonestSoundTest(_Audit):
    """Section B: positive confirmation is SOUND."""

    def test_B1_a_verified_signature_is_sound(self):
        self.assertTrue(self.sound(self.signed_contract()))

    def test_B3_the_scope_is_reported_as_recognized_elements_not_the_document(self):
        r = self.report(self.signed_contract())
        self.assertEqual(r.verified_seal_count, 1)
        self.assertIn("NOT the whole document", r.scope_summary())

    def test_B2_a_settled_claim_is_sound(self):
        settled = glyph.evaluate(glyph.parse("🤍 (🖤 🤍)")).term
        line = f"%🖤 CLAIM: id=c1 | expr=🤍 (🖤 🤍) | expected={settled}".encode("utf-8")
        self.assertTrue(self.sound(HEADER + line + b"\n%%EOF\n"))


class ProvenNegativeTest(_Audit):
    """Section C: real failures stay UNSOUND (so a blanket 'refuse all' would
    fail Section B, and a blanket 'accept all' would fail here)."""

    def test_C1_a_signature_mismatch_is_not_sound(self):
        sk = os.urandom(32); pk = public_key_from_secret(sk)
        sig = sign_bytes(sk, b"the real payload")
        m = json.dumps({"public_key_hex": pk.hex(), "signature_hex": sig.hex(),
                        "signed_payload": "a DIFFERENT payload"}).encode("utf-8")
        self.assertFalse(self.sound(HEADER + CONTRACT + m + b"\n%%EOF\n"))

    def test_C2_a_non_settling_claim_is_not_sound(self):
        line = "%🖤 CLAIM: id=c2 | expr=🌿 🤍 🤍 (🌿 🤍 🤍) | expected=x".encode("utf-8")
        self.assertFalse(self.sound(HEADER + line + b"\n%%EOF\n"))

    def test_C3_missing_container_is_not_sound_even_with_a_valid_seal(self):
        # a verified signature but NO PDF header/marker -> still not sound
        body = self.signed_contract().replace(HEADER, b"", 1)
        self.assertFalse(self.sound(body))


class MixedEvidenceTest(_Audit):
    """Section D: a positively-verified seal does NOT excuse a second piece of
    evidence that failed, was unconfirmed, or errored. Each isolates one
    `nothing_wrong` clause (the mutation harness showed Section A/C could not,
    since there the positive-confirmation guard alone already refused)."""

    def unconfirmed_line(self):
        m = json.dumps({"title": "unsigned", "blocks": []}).encode("utf-8")
        return CONTRACT + m

    def mismatch_line(self):
        sk = os.urandom(32); pk = public_key_from_secret(sk)
        sig = sign_bytes(sk, b"the real payload")
        m = json.dumps({"public_key_hex": pk.hex(), "signature_hex": sig.hex(),
                        "signed_payload": "a DIFFERENT payload"}).encode("utf-8")
        return CONTRACT + m

    def test_D1_verified_plus_unconfirmed_is_not_sound(self):
        self.assertFalse(self.sound(self.doc(self.signed_line(), self.unconfirmed_line())))

    def test_D2_verified_plus_malformed_is_not_sound(self):
        self.assertFalse(self.sound(self.doc(self.signed_line(), CONTRACT + b"{not json}")))

    def test_D3_verified_plus_mismatch_is_not_sound(self):
        self.assertFalse(self.sound(self.doc(self.signed_line(), self.mismatch_line())))

    def test_D4_verified_plus_failed_claim_is_not_sound(self):
        bad_claim = "%🖤 CLAIM: id=c2 | expr=🌿 🤍 🤍 (🌿 🤍 🤍) | expected=x".encode("utf-8")
        self.assertFalse(self.sound(self.doc(self.signed_line(), bad_claim)))

    def test_D5_two_verified_seals_are_still_sound(self):
        """Control: the mixed-doc machinery itself does not make a clean doc fail."""
        self.assertTrue(self.sound(self.doc(self.signed_line("one"), self.signed_line("two"))))

    def test_D6_verified_plus_malformed_claim_is_not_sound(self):
        """A line that announces a CLAIM but does not parse must count as an
        error, not be silently skipped -- otherwise a good signature paired with
        a malformed claim reads SOUND."""
        bad = "%🖤 CLAIM: this does not match the regex".encode("utf-8")
        self.assertFalse(self.sound(self.doc(self.signed_line(), bad)))


if __name__ == "__main__":
    unittest.main()
