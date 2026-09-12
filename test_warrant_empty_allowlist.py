#!/usr/bin/env python3
"""
Regression: a deny-all TrustConfig survives serialization as deny-all.

Security scan of e549de3, `improper-authorization.empty-author-allowlist`
(warrant_kernel.py). `TrustConfig.trusted_author_pks` has three distinct
meanings:
  - None      -> no allowlist  -> trust ALL authors (is_author_trusted True)
  - set()     -> allowlist with nobody in it -> trust NO author (deny-all)
  - {a, b}    -> trust exactly those.

`to_dict` serialized `list(pks) if pks else None`, and an empty set is
falsy, so deny-all serialized to None -- and `from_dict` reads None back as
trust-all. A persisted or manifest-round-tripped deny-all policy therefore
silently became trust-all. Measured before the fix: an empty-set config
denies 'abc' in memory but its round-trip trusts 'abc'.

Fix: `to_dict` uses `is not None`, so an empty set serializes to `[]` and
round-trips to an empty set (still deny-all); None still serializes to None
(still trust-all).

Sections:
  A  the three policies each round-trip to the same authorization decision
  B  file save/load preserves deny-all
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

import warrant_kernel as WK
from warrant_kernel import TrustConfig

if os.path.dirname(os.path.abspath(WK.__file__)) != _HERE:
    raise ImportError(f"warrant_kernel resolved to {WK.__file__}, outside {_HERE}")


class RoundTripTest(unittest.TestCase):
    """Section A."""

    def test_A1_deny_all_stays_deny_all(self):
        deny = TrustConfig(trusted_author_pks=set())
        self.assertFalse(deny.is_author_trusted("anyone"))
        self.assertEqual(deny.to_dict()["trusted_author_pks"], [],
                         "deny-all must serialize to [], not None")
        rt = TrustConfig.from_dict(deny.to_dict())
        self.assertEqual(rt.trusted_author_pks, set())
        self.assertFalse(rt.is_author_trusted("anyone"),
                         "deny-all became trust-all on round-trip")

    def test_A2_trust_all_stays_trust_all(self):
        trust_all = TrustConfig(trusted_author_pks=None)
        self.assertTrue(trust_all.is_author_trusted("anyone"))
        self.assertIsNone(trust_all.to_dict()["trusted_author_pks"])
        rt = TrustConfig.from_dict(trust_all.to_dict())
        self.assertIsNone(rt.trusted_author_pks)
        self.assertTrue(rt.is_author_trusted("anyone"))

    def test_A3_an_explicit_allowlist_is_preserved(self):
        tc = TrustConfig(trusted_author_pks={"aa", "bb"})
        rt = TrustConfig.from_dict(tc.to_dict())
        self.assertEqual(rt.trusted_author_pks, {"aa", "bb"})
        self.assertTrue(rt.is_author_trusted("aa"))
        self.assertFalse(rt.is_author_trusted("cc"))

    def test_A4_deny_all_and_trust_all_serialize_differently(self):
        """The heart of the finding: the two opposite policies must not collapse
        to the same serialized form."""
        deny = TrustConfig(trusted_author_pks=set()).to_dict()["trusted_author_pks"]
        allow = TrustConfig(trusted_author_pks=None).to_dict()["trusted_author_pks"]
        self.assertNotEqual(deny, allow)
        self.assertEqual(deny, [])
        self.assertIsNone(allow)


class FileRoundTripTest(unittest.TestCase):
    """Section B."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = os.path.join(self._tmp.name, "trust.json")

    def test_B1_saved_deny_all_loads_as_deny_all(self):
        TrustConfig(trusted_author_pks=set()).save_to_file(self.path)
        with open(self.path) as fh:
            on_disk = json.load(fh)
        self.assertEqual(on_disk["trusted_author_pks"], [])
        rt = TrustConfig.load_from_file(self.path)
        self.assertFalse(rt.is_author_trusted("z"), "saved deny-all loaded as trust-all")

    def test_B2_saved_trust_all_loads_as_trust_all(self):
        TrustConfig(trusted_author_pks=None).save_to_file(self.path)
        rt = TrustConfig.load_from_file(self.path)
        self.assertTrue(rt.is_author_trusted("z"))


if __name__ == "__main__":
    unittest.main()
