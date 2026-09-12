#!/usr/bin/env python3
"""
Regression: a peer's ledger block cannot inject executable code into the
locally compiled polyglot.

Security scan of e549de3, `code-injection.peer-ledger-python-wrapper`
(living_ledger.py). The polyglot emits the whole PDF body inside a Python
`r"..."` docstring, then appends the verifier after it. Peer-controlled block
fields (signer_name, signer_role, action_type, timestamp_utc, description,
title, combinator_claim) were interpolated into that body, several of them
unescaped, and `_escape_pdf` neutralized only `\\ ( )`. A block whose
signer_name embedded a docstring terminator followed by Python therefore
closed the wrapper and ran arbitrary code -- BEFORE the verifier -- when the
operator executed the document. The peer signs the block with their OWN key,
so `verify_block_integrity` passes: authenticity of the signer is not
authority to run code on the operator's machine.

Measured on the pre-fix code: `verify_block_integrity` True; running the
compiled ledger created an attacker-chosen marker file; exit 0.

Fix, two independent layers:
  1. `_escape_pdf` now also replaces every double-quote and collapses every
     control char, and every dynamic field is routed through it.
  2. `compile()` refuses to emit a body carrying more than the two expected
     triple-quote runs (the wrapper's own open and close), as a choke point
     that holds even if a field is ever added without routing.

Sections:
  A  the injection, reproduced then closed, with a positive control
  B  each dynamic field is neutralized
  C  the compile-time choke point is independent of per-field escaping
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
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

import living_ledger as LL
from mesh import verify_block_integrity
from crypto import generate_keypair

if os.path.dirname(os.path.abspath(LL.__file__)) != _HERE:
    raise ImportError(f"living_ledger resolved to {LL.__file__}, outside {_HERE}")


def breakout(marker_path: str) -> str:
    """A signer_name that, unfixed, closes the docstring and writes a marker."""
    return ('Eve\n"""\n'
            f'import os\nopen({marker_path!r}, "w").write("pwned")\n'
            'r"""\n')


class InjectionTest(unittest.TestCase):
    """Section A."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.d = self._tmp.name
        self.op_sk, _ = generate_keypair()

    def peer_block_via_wire(self, ledger, tip, **fields):
        """Build a block with an EPHEMERAL peer key, serialize as a peer POSTs,
        and return the deserialized block after the real integrity gate."""
        atk_sk, _ = generate_keypair()
        staging = LL.LivingLedger(title="x")
        staging.blocks.append(ledger.blocks[0])
        block = staging.append_block(
            fields.get("signer_name", "Eve"), fields.get("signer_role", "AUDITOR"),
            atk_sk, fields.get("action_type", "SETTLE"),
            fields.get("description", "routine"),
            combinator_claim=fields.get("combinator_claim"))
        received = LL.LedgerBlock.from_dict(json.loads(json.dumps(block.to_dict())))
        self.assertTrue(verify_block_integrity(received, expected_prev_hash=tip),
                        "a peer block signed with the peer's own key must pass the gate")
        return received

    def test_A1_signer_name_cannot_execute_when_the_operator_runs_the_doc(self):
        marker = os.path.join(self.d, "PWNED")
        led = LL.LivingLedger(title="Operator")
        led.create_genesis("Operator", "FOUNDER", self.op_sk)
        tip = led.blocks[-1].block_hash
        led.append_existing_block(self.peer_block_via_wire(led, tip, signer_name=breakout(marker)))

        out = os.path.join(self.d, "ledger.pdf")
        led.compile(out)
        self.assertFalse(os.path.exists(marker))
        r = subprocess.run([sys.executable, out], capture_output=True, text=True, cwd=self.d, timeout=120)
        self.assertFalse(os.path.exists(marker), "the compiled document executed peer-supplied code")
        # the document is still a valid, runnable polyglot
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_A2_positive_control_a_benign_ledger_still_runs_and_verifies(self):
        led = LL.LivingLedger(title="Operator")
        led.create_genesis("Operator", "FOUNDER", self.op_sk)
        led.append_block("Alice", "AUDITOR", self.op_sk, "SETTLE", "honest block")
        out = os.path.join(self.d, "good.pdf")
        led.compile(out)
        r = subprocess.run([sys.executable, out], capture_output=True, text=True, cwd=self.d, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertRegex(r.stdout.upper(), r"LEDGER|BLOCK|VERIF", "the verifier did not run")


class FieldNeutralizationTest(unittest.TestCase):
    """Section B: no dynamic field can carry a docstring terminator into the body."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.d = self._tmp.name
        self.sk, _ = generate_keypair()

    def compiled_body(self, **block_fields):
        title = block_fields.pop("title", "Ledger")
        led = LL.LivingLedger(title=title)
        led.create_genesis("Operator", "FOUNDER", self.sk)
        if block_fields:
            led.append_block(block_fields.get("signer_name", "S"),
                             block_fields.get("signer_role", "R"), self.sk,
                             block_fields.get("action_type", "SETTLE"),
                             block_fields.get("description", "d"),
                             combinator_claim=block_fields.get("combinator_claim"))
        out = os.path.join(self.d, "o.pdf")
        led.compile(out)
        with open(out, "rb") as f:
            return f.read()

    def test_B1_escape_pdf_removes_quotes_and_control_chars(self):
        got = LL._escape_pdf('a"""b\nc\rd\te')
        self.assertNotIn('"', got)
        self.assertNotIn("\n", got)
        self.assertNotIn("\r", got)
        self.assertNotIn("\t", got)

    def test_B2_every_free_text_field_is_neutralized_in_the_body(self):
        payload = 'x"""y\nimport os\nr"""z'
        for field in ("title", "signer_name", "signer_role", "action_type", "description"):
            with self.subTest(field=field):
                body = self.compiled_body(**{field: payload})
                self.assertEqual(body.count(b'"""'), 2,
                                 f"{field} introduced an extra docstring terminator")

    def test_B3_a_malicious_combinator_claim_is_neutralized(self):
        body = self.compiled_body(combinator_claim={"expr": 'a"""\nimport os\nr"""',
                                                     "expected": 'b"""c', "atp": 1})
        self.assertEqual(body.count(b'"""'), 2)


class ChokePointTest(unittest.TestCase):
    """Section C: the compile-time guard is independent of per-field escaping."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.d = self._tmp.name
        self.sk, _ = generate_keypair()

    def test_C1_a_field_that_bypasses_the_sanitizer_is_refused_at_compile(self):
        led = LL.LivingLedger(title="Operator")
        led.create_genesis("Operator", "FOUNDER", self.sk)
        led.append_block('Eve"""\nimport os\nr"""', "A", self.sk, "SETTLE", "x")
        # neutralize the per-field defense to prove the choke point stands alone
        with mock.patch.object(LL, "_escape_pdf", lambda t: str(t)):
            with self.assertRaises(ValueError) as caught:
                led.compile(os.path.join(self.d, "o.pdf"))
        self.assertIn("docstring terminator", str(caught.exception))
        self.assertFalse(os.path.exists(os.path.join(self.d, "o.pdf")))

    def test_C2_an_honest_ledger_has_exactly_two_terminators(self):
        led = LL.LivingLedger(title="Operator")
        led.create_genesis("Operator", "FOUNDER", self.sk)
        led.append_block("Alice", "AUDITOR", self.sk, "SETTLE", "honest")
        out = os.path.join(self.d, "o.pdf")
        led.compile(out)
        with open(out, "rb") as f:
            self.assertEqual(f.read().count(b'"""'), 2)


if __name__ == "__main__":
    unittest.main()
