#!/usr/bin/env python3
"""
Regression: the private-key sidecar's extension is 🔑, and the vault detector
still recognizes a sidecar written before this rename.

The single-document sidecar (organism, autopoiesis, morpho-autopoiesis) was
named `<file>.key`. It is now `<file>` + `keystore.PRIVATE_KEY_SUFFIX`, the
single character 🔑 (U+1F511). This is a naming change only: every check that
existed before this file (write mode 0600, atomic replace, refusal of a
planted link, refusal to pack one into a vault) is unchanged and is exercised
in `test_public_export.py`; this file pins the rename itself.

Not touched: `.keys` (`keystore.KEYSTORE_SUFFIX`), the colony/swarm keystore --
a registry of several keys indexed by the public key each derives, a different
kind of file from one document's own single key.

Sections:
  A  the three single-key writers use the new suffix, and only the new suffix
  B  the vault detector still refuses a legacy `.key` sidecar it never wrote
"""
from __future__ import annotations

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

import keystore as ks
from crypto import generate_keypair
from organism import PolyglotOrganismCompiler, create_genesis_organism
from autopoiesis import init_autopoietic_organism
from morpho_autopoiesis import init_morpho_autopoietic_organism

if os.path.dirname(os.path.abspath(ks.__file__)) != _HERE:
    raise ImportError(f"keystore resolved to {ks.__file__}, outside {_HERE}")


class SuffixTest(unittest.TestCase):
    """Section A."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.d = self._tmp.name

    def test_A1_the_suffix_is_exactly_the_key_emoji(self):
        self.assertEqual(ks.PRIVATE_KEY_SUFFIX, "\U0001F511")
        self.assertEqual(ks.PRIVATE_KEY_SUFFIX, "🔑")

    def test_A2_organism_writes_the_new_suffix_and_not_the_old_one(self):
        pdf = os.path.join(self.d, "o.pdf")
        PolyglotOrganismCompiler.compile(create_genesis_organism(), pdf)
        self.assertTrue(os.path.exists(pdf + ks.PRIVATE_KEY_SUFFIX))
        self.assertFalse(os.path.exists(pdf + ".key"))
        self.assertEqual(sorted(os.listdir(self.d)), sorted(["o.pdf", "o.pdf" + ks.PRIVATE_KEY_SUFFIX]))

    def test_A3_autopoiesis_writes_the_new_suffix_and_not_the_old_one(self):
        pdf = os.path.join(self.d, "a.pdf")
        init_autopoietic_organism(pdf)
        self.assertTrue(os.path.exists(pdf + ks.PRIVATE_KEY_SUFFIX))
        self.assertFalse(os.path.exists(pdf + ".key"))

    def test_A4_morpho_autopoiesis_writes_the_new_suffix_and_not_the_old_one(self):
        pdf = os.path.join(self.d, "m.pdf")
        init_morpho_autopoietic_organism(pdf)
        self.assertTrue(os.path.exists(pdf + ks.PRIVATE_KEY_SUFFIX))
        self.assertFalse(os.path.exists(pdf + ".key"))

    def test_A5_the_sidecar_is_still_written_private_mode_0600(self):
        pdf = os.path.join(self.d, "o.pdf")
        PolyglotOrganismCompiler.compile(create_genesis_organism(), pdf)
        import stat
        self.assertEqual(stat.S_IMODE(os.stat(pdf + ks.PRIVATE_KEY_SUFFIX).st_mode), 0o600)


class LegacyDetectionTest(unittest.TestCase):
    """Section B: the vault must still refuse a sidecar named the OLD way --
    a checkout from before this rename may still have one lying around."""

    def test_B1_a_legacy_dot_key_file_is_still_named_by_the_detector(self):
        sk, _ = generate_keypair()
        reasons = ks.secret_material_reasons("organism.pdf.key", (sk + "\n").encode())
        self.assertTrue(reasons, "a legacy .key sidecar is no longer recognized")

    def test_B2_the_new_suffix_is_also_named_by_the_detector(self):
        sk, _ = generate_keypair()
        name = "organism.pdf" + ks.PRIVATE_KEY_SUFFIX
        reasons = ks.secret_material_reasons(name, (sk + "\n").encode())
        self.assertTrue(reasons, "the current sidecar suffix is not recognized")

    def test_B3_an_unrelated_name_is_not_flagged_by_suffix_alone(self):
        self.assertEqual(ks.secret_material_reasons("notes.txt", b"just some text"), [])

    def test_B4_a_legacy_sidecar_refuses_a_real_vault_pack(self):
        import vault
        with tempfile.TemporaryDirectory() as src:
            sk, _ = generate_keypair()
            with open(os.path.join(src, "readme.txt"), "w") as fh:
                fh.write("public\n")
            with open(os.path.join(src, "organism.pdf.key"), "w") as fh:
                fh.write(sk + "\n")
            with self.assertRaises(vault.SecretMaterialError):
                vault.pack_files_to_vault(["readme.txt", "organism.pdf.key"], src)


if __name__ == "__main__":
    unittest.main()
