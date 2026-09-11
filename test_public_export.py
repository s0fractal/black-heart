#!/usr/bin/env python3
"""
Regression: a public export carries no secret key, and continuing it needs an
explicit private key source.

Measured at 1aed5c9 by generating each export with its real writer and looking
for a 64-hex secret whose derived public key sits in the same bytes:

    organism PDF          1      colony JSON / PDF   4 / 4 (three organisms + authority)
    swarm JSON / PDF      2 / 2  vault of a directory: shipped the .key sidecar verbatim

The colony also signed with the all-zero key for an organism without one, and
signed its ledger with a freshly generated key when the authority's was absent.

Sections:
  A  every export, written by its real writer, carries no secret
  B  verification needs no private key
  C  continuing works from an explicit key source, and new keys are kept
  D  continuing without one is refused by name, before anything is written
  E  a vault refuses private key material
  F  historical artifacts are read, not rewritten, and their keys are not used
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
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

import io
import tarfile
from unittest import mock

import crypto
import keystore as ks_module
import vault as vault_module
from colony import Colony
from crypto import generate_keypair, public_key_from_secret
from epistemic_swarm import SwarmMembrane
from keystore import (KEYSTORE_PROFILE, Keystore, MissingKeyError, PrivateFileError,
                      resolve_keystore, secret_material_reasons, sidecar_path, write_private_file)
from organism import (PolyglotOrganismCompiler, create_genesis_organism,
                      document_carries_secret_key, extract_organism_from_pdf)
from vault import SecretMaterialError, pack_files_to_vault

if os.path.dirname(os.path.abspath(ks_module.__file__)) != _HERE:
    raise ImportError(f"keystore resolved to {ks_module.__file__}, outside {_HERE}")

CLI = os.path.join(_HERE, "cli.py")
_HEX = re.compile(rb"(?<![0-9a-fA-F])([0-9a-fA-F]{64})(?![0-9a-fA-F])")


def keypairs_in(data: bytes) -> int:
    """64-hex secrets in `data` whose derived public key is also in `data`."""
    lowered, n = data.lower(), 0
    for c in {m.group(1).lower() for m in _HEX.finditer(data)}:
        try:
            if public_key_from_secret(bytes.fromhex(c.decode())).hex().encode() in lowered:
                n += 1
        except Exception:
            pass
    return n


def cli(*args, cwd):
    return subprocess.run([sys.executable, "-B", CLI, *args], cwd=cwd,
                          capture_output=True, text=True, timeout=600)


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


def mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


class _Dir(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.d = self._tmp.name

    def path(self, name):
        return os.path.join(self.d, name)

    def colony_state(self):
        state = self.path("colony.json")
        r = cli("colony", "init", "-f", state, "-n", "probe", "-o", "3", "--seed", "1", cwd=self.d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return state

    def swarm_state(self, ext="json"):
        state = self.path(f"swarm.{ext}")
        r = cli("swarm", "init", "--population", "2", "-o", state, cwd=self.d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return state

    def organism_pdf(self):
        pdf = self.path("organism.pdf")
        PolyglotOrganismCompiler.compile(create_genesis_organism(), pdf)
        return pdf


class ExportTest(_Dir):
    """Section A: nothing secret in anything made to be shared."""

    def assertPublic(self, path):
        data = read(path)
        self.assertEqual(keypairs_in(data), 0, f"{os.path.basename(path)} holds a keypair")
        reasons = secret_material_reasons(os.path.basename(path), data)
        self.assertEqual(reasons, [], f"{os.path.basename(path)}: {reasons}")

    def test_A1_organism_pdf(self):
        pdf = self.organism_pdf()
        self.assertPublic(pdf)
        self.assertFalse(document_carries_secret_key(pdf))
        self.assertEqual(mode(pdf + ".key"), 0o600)

    def test_A2_colony_state_and_pdf(self):
        state = self.colony_state()
        self.assertPublic(state)
        self.assertNotIn("authority_sk_hex", read(state).decode())
        self.assertEqual(mode(sidecar_path(state)), 0o600)
        pdf = self.path("colony.pdf")
        r = cli("colony", "compile", "-f", state, "-o", pdf, cwd=self.d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertPublic(pdf)

    def test_A3_swarm_state_json_and_pdf(self):
        for ext in ("json", "pdf"):
            with self.subTest(ext=ext):
                state = self.swarm_state(ext)
                self.assertPublic(state)
                self.assertEqual(mode(sidecar_path(state)), 0o600)

    def test_A4_the_keystore_is_where_the_secrets_went(self):
        state = self.colony_state()
        store = Keystore.load(sidecar_path(state))
        colony = Colony.load_from_file(state)
        self.assertTrue(store.has(colony.authority_pk_hex))
        for st in colony.population:
            self.assertTrue(store.has(st.organism.public_key_hex))


class VerifyWithoutKeysTest(_Dir):
    """Section B: verifying never needs a secret."""

    def test_B1_organism_verifies_and_reports_status(self):
        pdf = self.organism_pdf()
        os.remove(pdf + ".key")
        org = extract_organism_from_pdf(pdf)
        self.assertEqual(org.secret_key_hex, "")
        self.assertTrue(org.verify())
        r = subprocess.run([sys.executable, pdf, "--status"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = cli("verify", pdf, cwd=self.d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_B2_colony_state_verifies_without_keys(self):
        state = self.colony_state()
        os.remove(sidecar_path(state))
        colony = Colony.load_from_file(state)
        self.assertEqual(colony.authority_sk_hex, "")
        self.assertTrue(colony.verify())
        r = cli("colony", "status", "-f", state, cwd=self.d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_B3_swarm_signatures_verify_without_keys(self):
        state = self.swarm_state()
        r = cli("swarm", "inoculate", state, "--origin",
                next(iter(json.loads(read(state))["organisms"])), "--demo", cwd=self.d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        os.remove(sidecar_path(state))
        swarm = SwarmMembrane.from_dict(json.loads(read(state)))
        tombstones = [t for org in swarm.organisms.values()
                      for t in org.tombstone_registry.tombstones.values()]
        self.assertTrue(tombstones)
        self.assertTrue(all(t.verify_signature() for t in tombstones))
        self.assertTrue(all(secret == "" for _, secret in swarm.organism_keys.values()))


class RecoveryTest(_Dir):
    """Section C: continuing from an explicit key source."""

    def test_C1_colony_steps_with_its_keystore(self):
        state = self.colony_state()
        r = cli("colony", "step", "-f", state, cwd=self.d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(len(json.loads(read(state))["epochs"]), 1)
        self.assertEqual(keypairs_in(read(state)), 0)

    def test_C2_colony_steps_with_an_explicit_keys_path(self):
        state = self.colony_state()
        elsewhere = self.path("private.keys")
        shutil.move(sidecar_path(state), elsewhere)
        r = cli("colony", "step", "-f", state, "--keys", elsewhere, cwd=self.d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(os.path.exists(sidecar_path(state)), "keys stay where the operator put them")

    def test_C3_organism_reproduces_from_its_sidecar(self):
        pdf = self.organism_pdf()
        r = subprocess.run([sys.executable, pdf, "--reproduce"], cwd=self.d,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        children = [f for f in os.listdir(self.d) if f.startswith("organism_gen0001_") and f.endswith(".pdf")]
        self.assertEqual(len(children), 1)
        child = self.path(children[0])
        self.assertEqual(keypairs_in(read(child)), 0)
        self.assertEqual(mode(child + ".key"), 0o600)

    def test_C4_swarm_steps_and_mating_keeps_the_new_key(self):
        state = self.swarm_state()
        r = cli("swarm", "step", state, cwd=self.d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        before = len(Keystore.load(sidecar_path(state)))
        oids = list(json.loads(read(state))["organisms"])
        r = cli("swarm", "mate", state, "--parent-a", oids[0], "--parent-b", oids[1], cwd=self.d)
        if r.returncode == 0:
            self.assertEqual(len(Keystore.load(sidecar_path(state))), before + 1)
            self.assertEqual(keypairs_in(read(state)), 0)
        else:
            self.assertIn("Epistemic", r.stdout + r.stderr, "mating refused for its own reasons")

    def test_C5_organism_reproduces_from_the_environment(self):
        pdf = self.organism_pdf()
        with open(pdf + ".key") as fh:
            sk = fh.read().strip()
        os.remove(pdf + ".key")
        env = dict(os.environ, BLACK_HEART_SECRET_KEY=sk)
        r = subprocess.run([sys.executable, pdf, "--reproduce"], cwd=self.d,
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        children = [f for f in os.listdir(self.d) if f.startswith("organism_gen0001_") and f.endswith(".pdf")]
        self.assertEqual(len(children), 1)
        self.assertEqual(keypairs_in(read(self.path(children[0]))), 0)

    def test_C6_an_explicit_secret_key_comes_before_the_sidecar(self):
        """The sidecar holds a foreign key; the explicit key is used, so it wins."""
        pdf = self.organism_pdf()
        with open(pdf + ".key") as fh:
            sk = fh.read().strip()
        with open(pdf + ".key", "w") as fh:
            fh.write(generate_keypair()[0])
        env = {k: v for k, v in os.environ.items() if k != "BLACK_HEART_SECRET_KEY"}
        r = subprocess.run([sys.executable, pdf, "--reproduce", "--secret-key", sk], cwd=self.d,
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("does not belong", r.stdout)

    def test_C7_swarm_steps_with_an_explicit_keys_path_and_keeps_it_there(self):
        state = self.swarm_state()
        explicit = self.path("elsewhere.keys")
        os.replace(sidecar_path(state), explicit)
        before = len(Keystore.load(explicit))
        r = cli("swarm", "step", state, "--keys", explicit, cwd=self.d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(os.path.exists(sidecar_path(state)), "keys were written beside the state instead")
        self.assertGreaterEqual(len(Keystore.load(explicit)), before)
        self.assertEqual(mode(explicit), 0o600)
        self.assertEqual(keypairs_in(read(state)), 0)


class RefusalTest(_Dir):
    """Section D: no key source means no signature and no write."""

    def test_D1_colony_step_without_keys_is_refused_and_writes_nothing(self):
        state = self.colony_state()
        os.remove(sidecar_path(state))
        before = read(state)
        r = cli("colony", "step", "-f", state, cwd=self.d)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("Step refused", r.stdout)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(read(state), before)

    def test_D2_a_keyless_colony_refuses_before_changing_itself(self):
        """The zero-key and fresh-authority fallbacks are gone, not just unused."""
        state = self.colony_state()
        colony = Colony.load_from_file(state)
        before = json.dumps(colony.to_dict(), sort_keys=True)
        with self.assertRaises(MissingKeyError):
            colony.step_epoch()
        self.assertEqual(json.dumps(colony.to_dict(), sort_keys=True), before)
        self.assertIn("authority", colony.missing_keys())

    def test_D3_one_missing_organism_key_is_enough_to_refuse(self):
        colony = Colony.create_genesis_colony(name="x", initial_organisms=2)
        colony.population[0].organism.secret_key_hex = ""
        with self.assertRaises(MissingKeyError):
            colony.step_epoch()

    def test_D4_organism_reproduction_without_a_key_is_refused(self):
        pdf = self.organism_pdf()
        os.remove(pdf + ".key")
        env = {k: v for k, v in os.environ.items() if k != "BLACK_HEART_SECRET_KEY"}
        r = subprocess.run([sys.executable, pdf, "--reproduce"], cwd=self.d,
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("no private key source", r.stdout)
        self.assertFalse([f for f in os.listdir(self.d) if f.startswith("organism_gen0001_")])

    def test_D5_organism_reproduction_with_another_organisms_key_is_refused(self):
        pdf = self.organism_pdf()
        other_sk, _ = generate_keypair()
        with open(pdf + ".key", "w") as fh:
            fh.write(other_sk)
        r = subprocess.run([sys.executable, pdf, "--reproduce"], cwd=self.d,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("does not belong to this organism", r.stdout)

    def test_D6_swarm_actions_without_keys_are_refused(self):
        state = self.swarm_state()
        os.remove(sidecar_path(state))
        before = read(state)
        oids = list(json.loads(before)["organisms"])
        for argv in (("swarm", "step", state),
                     ("swarm", "mate", state, "--parent-a", oids[0], "--parent-b", oids[1]),
                     ("swarm", "inoculate", state, "--origin", oids[0], "--demo")):
            with self.subTest(action=argv[1]):
                r = cli(*argv, cwd=self.d)
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertIn("no private key source", r.stdout)
                self.assertEqual(read(state), before)

    def test_D9_a_keystore_missing_one_organism_is_refused_before_writing(self):
        """A keystore that exists but lacks one signer's key: the source is found,
        and the action is still refused, naming who cannot sign."""
        state = self.swarm_state()
        doc = json.loads(read(state))
        store = Keystore.load(sidecar_path(state))
        dropped = sorted(doc["organism_public_keys"].items())[0]
        partial = Keystore()
        for pk in store.public_keys():
            if pk != bytes.fromhex(dropped[1]).hex():
                partial.add(store.secret_for(pk))
        self.assertEqual(len(partial), len(store) - 1)
        partial.save(sidecar_path(state))
        before = read(state)
        r = cli("swarm", "step", state, cwd=self.d)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn(dropped[0], r.stdout)
        self.assertEqual(read(state), before)

    def test_D7_a_keystore_is_loaded_strictly(self):
        sk, pk = generate_keypair()
        other_sk, _ = generate_keypair()
        good = {"profile": KEYSTORE_PROFILE, "keys": {pk: sk}}
        self.assertTrue(Keystore.from_document(good).has(pk))
        for name, doc in {
            "wrong profile": dict(good, profile="black-heart.keystore.v0"),
            "another key's secret": {"profile": KEYSTORE_PROFILE, "keys": {pk: other_sk}},
            "extra field": dict(good, note=1),
            "not an object": [good],
            "short secret": {"profile": KEYSTORE_PROFILE, "keys": {pk: sk[:10]}},
        }.items():
            with self.subTest(case=name):
                with self.assertRaises((ValueError, TypeError)):
                    Keystore.from_document(doc)

    def test_D8_resolution_order_is_explicit(self):
        state = self.path("s.json")
        with self.assertRaises(MissingKeyError):
            resolve_keystore(None, state)
        sk, _ = generate_keypair()
        store = Keystore(); store.add(sk)
        store.save(sidecar_path(state))
        explicit = store.save(self.path("explicit.keys"))
        self.assertEqual(resolve_keystore(None, state)[1], sidecar_path(state))
        self.assertEqual(resolve_keystore(explicit, state)[1], explicit)
        self.assertEqual(mode(explicit), 0o600)


class HardeningTest(_Dir):
    """Section G: review K1-K3 on PR #19, each reproduced at 357fc4e by the
    reviewer's probe before it was repaired."""

    def planted(self):
        target = self.path("public.txt")
        with open(target, "w") as fh:
            fh.write("innocent")
        return target

    def store(self):
        sk, pk = generate_keypair()
        s = Keystore()
        s.add(sk)
        return s, sk, pk

    def test_G1_a_link_at_the_old_temporary_name_is_not_followed(self):
        target, private = self.planted(), self.path("private.keys")
        os.symlink(target, f"{private}.tmp-{os.getpid()}")
        store, sk, pk = self.store()
        store.save(private)
        self.assertEqual(read(target), b"innocent")
        self.assertFalse(os.path.islink(private))
        self.assertEqual(mode(private), 0o600)
        self.assertTrue(Keystore.load(private).has(pk))

    def test_G2_a_link_at_the_private_path_is_refused_and_left_alone(self):
        target, private = self.planted(), self.path("private.keys")
        os.symlink(target, private)
        store, sk, pk = self.store()
        with self.assertRaises(PrivateFileError):
            store.save(private)
        self.assertEqual(read(target), b"innocent")
        self.assertTrue(os.path.islink(private))
        self.assertEqual(sorted(os.listdir(self.d)), ["private.keys", "public.txt"])

    def test_G3_the_organism_sidecar_refuses_a_link_before_anything_is_written(self):
        target, pdf = self.planted(), self.path("organism.pdf")
        os.symlink(target, pdf + ".key")
        with self.assertRaises(PrivateFileError):
            PolyglotOrganismCompiler.compile(create_genesis_organism(), pdf)
        self.assertEqual(read(target), b"innocent")
        self.assertFalse(os.path.exists(pdf))

    def test_G4_a_private_file_is_replaced_atomically_and_nothing_is_left_behind(self):
        path = self.path("k.key")
        write_private_file(path, "first\n")
        write_private_file(path, "second\n")
        self.assertEqual(read(path), b"second\n")
        self.assertEqual(mode(path), 0o600)
        self.assertEqual(os.listdir(self.d), ["k.key"])

    def test_G5_the_vault_archives_exactly_the_bytes_it_checked(self):
        """The file is replaced with a secret right after its check returns."""
        src = self.path("project")
        os.makedirs(src)
        payload = os.path.join(src, "payload.json")
        with open(payload, "wb") as fh:
            fh.write(b'{"safe": true}')
        _, sk, pk = self.store()
        secret_doc = json.dumps({"secret_key_hex": sk, "public_key_hex": pk}).encode()
        checked = {}
        real = ks_module.secret_material_reasons

        def check_then_swap(name, data):
            checked[name] = data
            answer = real(name, data)
            with open(payload, "wb") as fh:
                fh.write(secret_doc)
            return answer

        with mock.patch.object(ks_module, "secret_material_reasons", check_then_swap):
            packed, _, _ = pack_files_to_vault(["payload.json"], src)
        with tarfile.open(fileobj=io.BytesIO(packed), mode="r:gz") as archive:
            content = archive.extractfile("payload.json").read()
        self.assertEqual(content, checked["payload.json"])
        self.assertNotIn(sk.encode(), content)

    def test_G6_the_reviewers_model_scan_then_replace_does_not_reach_the_archive(self):
        src = self.path("project")
        os.makedirs(src)
        payload = os.path.join(src, "payload.json")
        with open(payload, "wb") as fh:
            fh.write(b'{"safe": true}')
        _, sk, pk = self.store()
        real = vault_module.find_secret_material

        def scan_then_replace(paths, base):
            answer = real(paths, base)
            with open(payload, "wb") as fh:
                fh.write(json.dumps({"secret_key_hex": sk, "public_key_hex": pk}).encode())
            return answer

        with mock.patch.object(vault_module, "find_secret_material", scan_then_replace):
            try:
                packed, _, _ = pack_files_to_vault(["payload.json"], src)
            except SecretMaterialError:
                return
        with tarfile.open(fileobj=io.BytesIO(packed), mode="r:gz") as archive:
            self.assertNotIn(sk.encode(), archive.extractfile("payload.json").read())

    def test_G8_the_older_sidecar_writers_refuse_a_planted_link_too(self):
        """autopoiesis and morpho-autopoiesis wrote their `.key` the same way
        before S5a (O_TRUNC, and a plain open plus chmod); they now share the writer."""
        from autopoiesis import init_autopoietic_organism
        from morpho_autopoiesis import init_morpho_autopoietic_organism
        for name, init in (("auto.pdf", init_autopoietic_organism),
                           ("morpho.pdf", init_morpho_autopoietic_organism)):
            with self.subTest(writer=name):
                target, pdf = self.planted(), self.path(name)
                os.symlink(target, pdf + ".key")
                with self.assertRaises(PrivateFileError):
                    init(pdf, secret_key_hex=generate_keypair()[0])
                self.assertEqual(read(target), b"innocent")
                self.assertTrue(os.path.islink(pdf + ".key"))
        pdf = self.path("clean.pdf")
        init_autopoietic_organism(pdf, secret_key_hex=generate_keypair()[0])
        self.assertEqual(mode(pdf + ".key"), 0o600)

    def test_G7_scan_exhaustion_is_a_refusal_not_a_clean_result(self):
        _, sk, pk = self.store()
        pad = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(513)]
        at_limit = json.dumps([sk, pk] + pad[:510]).encode()   # 512 distinct: scanned
        over = json.dumps([sk, pk] + pad[:511]).encode()        # 513: not scanned, refused
        self.assertIn("it holds a secret key next to the public key it derives",
                      secret_material_reasons("b.json", at_limit))
        self.assertTrue(any("cannot be cleared" in r for r in secret_material_reasons("b.json", over)))
        self.assertTrue(any("cannot be cleared" in r
                            for r in secret_material_reasons("b.json", json.dumps(pad).encode())))
        self.assertEqual(secret_material_reasons("b.json", json.dumps(pad[:20]).encode()), [])
        src = self.path("project")
        os.makedirs(src)
        with open(os.path.join(src, "blob.json"), "wb") as fh:
            fh.write(over)
        with self.assertRaises(SecretMaterialError):
            pack_files_to_vault(["blob.json"], src)


class VaultTest(_Dir):
    """Section E: a vault is not a secret store."""

    def project(self, **files):
        src = self.path("project")
        os.makedirs(src, exist_ok=True)
        for name, data in files.items():
            with open(os.path.join(src, name.replace("__", ".")), "wb") as fh:
                fh.write(data)
        return src

    def test_E1_each_kind_of_secret_is_refused_by_name(self):
        sk, pk = generate_keypair()
        store = Keystore(); store.add(sk)
        cases = {
            "a key sidecar": ("organism.pdf.key", (sk + "\n").encode()),
            "a keystore": ("private.json", json.dumps(store.to_document()).encode()),
            "a named secret field": ("state.json", json.dumps({"secret_key_hex": sk}).encode()),
            "a secret next to its public key": ("notes.txt", f"{pk}\n{sk}\n".encode()),
        }
        for label, (name, data) in cases.items():
            with self.subTest(case=label):
                src = self.path(f"p-{abs(hash(label))}")
                os.makedirs(src)
                with open(os.path.join(src, "README.txt"), "w") as fh:
                    fh.write("public notes\n")
                with open(os.path.join(src, name), "wb") as fh:
                    fh.write(data)
                with self.assertRaises(SecretMaterialError) as caught:
                    pack_files_to_vault(["README.txt", name], src)
                self.assertIn(name, str(caught.exception))
                out = self.path(f"v-{abs(hash(label))}.pdf")
                r = cli("vault", "pack", src, "-o", out, cwd=self.d)
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertIn("Vault refused", r.stdout)
                self.assertFalse(os.path.exists(out), "nothing is written on refusal")

    def test_E2_a_clean_directory_still_packs_and_unpacks(self):
        src = self.project(README__txt=b"public notes\n", data__json=b'{"hash": "' + b"ab" * 32 + b'"}')
        out = self.path("vault.pdf")
        r = cli("vault", "pack", src, "-o", out, cwd=self.d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        dest = self.path("unpacked")
        r = cli("vault", "unpack", out, "--dest", dest, cwd=self.d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(sorted(os.listdir(dest)), ["README.txt", "data.json"])


class HistoricalTest(unittest.TestCase):
    """Section F: read, not rewritten, and never used as a key source."""

    GEN0 = os.path.join(_HERE, "examples", "organism_gen0.pdf")

    def test_F1_the_committed_gen0_key_is_reported_and_not_used(self):
        digest = hashlib.sha256(read(self.GEN0)).hexdigest()
        self.assertTrue(document_carries_secret_key(self.GEN0), "the historical exposure is visible")
        org = extract_organism_from_pdf(self.GEN0)
        self.assertEqual(org.secret_key_hex, "")
        self.assertEqual(hashlib.sha256(read(self.GEN0)).hexdigest(), digest)

    def test_F2_a_legacy_colony_state_gives_up_no_secret(self):
        colony = Colony.create_genesis_colony(name="legacy", initial_organisms=2)
        legacy = colony.to_dict()
        legacy["authority_sk_hex"] = colony.authority_sk_hex
        for i, st in enumerate(legacy["population"]):
            st["organism"]["secret_key_hex"] = colony.population[i].organism.secret_key_hex
        loaded = Colony.from_dict(legacy)
        self.assertEqual(loaded.authority_sk_hex, "")
        self.assertTrue(all(st.organism.secret_key_hex == "" for st in loaded.population))
        store = Keystore.from_legacy_secrets(
            [legacy["authority_sk_hex"]] + [st["organism"]["secret_key_hex"] for st in legacy["population"]])
        loaded.attach_keys(store)
        self.assertEqual(loaded.missing_keys(), [])

    def test_F3_a_legacy_swarm_state_gives_up_no_secret(self):
        """A state in the pre-S5a shape, [public, secret] per organism, built
        from a real swarm: only the public half is read."""
        with tempfile.TemporaryDirectory() as d:
            state = os.path.join(d, "swarm.json")
            r = cli("swarm", "init", "--population", "2", "-o", state, cwd=d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            doc = json.loads(read(state))
            store = Keystore.load(sidecar_path(state))
        publics = doc.pop("organism_public_keys")
        doc["organism_keys"] = {oid: [pk, store.secret_for(pk)] for oid, pk in publics.items()}
        self.assertEqual(keypairs_in(json.dumps(doc).encode()), len(publics),
                         "the legacy fixture really carries its secrets")
        swarm = SwarmMembrane.from_dict(doc)
        self.assertEqual({oid: keys[0] for oid, keys in swarm.organism_keys.items()}, publics)
        self.assertTrue(all(secret == "" for _, secret in swarm.organism_keys.values()))
        with self.assertRaises(MissingKeyError):
            swarm.require_all_keys()
        swarm.attach_keys(store)
        swarm.require_all_keys()

if __name__ == "__main__":
    unittest.main(verbosity=2)
