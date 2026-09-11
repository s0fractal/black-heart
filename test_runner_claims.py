#!/usr/bin/env python3
"""
Regression: an embedded PDF runner reports only what it checked, and runs no code
from the document's directory or the cwd.

Measured at 6570ec5 through the real generators and `python3 <file>.pdf`:

  sheaf runner
    admissible report                       "ALL INVARIANTS SATISFIED", exit 0
    OBSTRUCTED report (real kernel)         "ALL INVARIANTS SATISFIED", exit 0
    verdict rewritten to admissible + hash  "ALL INVARIANTS SATISFIED", exit 0
      recomputed
    hand-built report (S K K x = y, glued)  "ALL INVARIANTS SATISFIED", exit 0
  egraph runner
    genuine document                        "congruence closure sound", exit 0
    manifest emptied, 999999 classes        "congruence closure sound", exit 0
    a planted egraph_kernel.py in the cwd   IMPORTED AND RAN, then "sound", exit 0

After S7 each runner verifies the manifest against an embedded SHA-256, reports
the RECORDED verdict, names that it re-derived nothing and asserts no soundness,
and the egraph runner imports no code from the document's directory or cwd.

Sections:
  A  the sheaf runner
  B  the egraph runner
  C  no code executes from the document's directory or the cwd
"""
from __future__ import annotations

import hashlib
import json
import os
import re
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

import sheaf_kernel as sh
import egraph_kernel as eg
from glyph import parse

for _m in (sh, eg):
    if os.path.dirname(os.path.abspath(_m.__file__)) != _HERE:
        raise ImportError(f"{_m.__name__} resolved to {_m.__file__}, outside {_HERE}")

_ENV = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
_ENV["PYTHONDONTWRITEBYTECODE"] = "1"


def run_pdf(pdf, *args, cwd=None):
    r = subprocess.run([sys.executable, pdf, *args], capture_output=True, text=True,
                       env=_ENV, cwd=cwd, timeout=120)
    return r.returncode, (r.stdout + r.stderr)


def sheaf_report(nf_b="x"):
    k = sh.EpistemicSheafKernel()
    c1 = sh.EpistemicContext.create("A", ["d1", "d2"], 100)
    c2 = sh.EpistemicContext.create("B", ["d2", "d3"], 100)
    k.register_context(c1)
    k.register_context(c2)
    k.register_section(sh.LocalSection.create(c1, "claim", "S K K x", "x", 2))
    k.register_section(sh.LocalSection.create(c2, "claim", "S K K x", nf_b, 2))
    return k.verify_descent("claim", [c1, c2])


class SheafRunnerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.d = self._tmp.name

    def test_A1_an_admissible_report_reports_the_recorded_verdict_only(self):
        p = os.path.join(self.d, "ok.pdf")
        sh.generate_sheaf_pdf(sheaf_report(), p)
        rc, out = run_pdf(p, "--audit")
        self.assertEqual(rc, 0, out)
        self.assertIn("Manifest self-consistency: OK", out)
        self.assertIn("Recorded verdict: GLUING ADMISSIBLE", out)
        self.assertIn("did NOT re-derive", out)
        self.assertNotIn("ALL INVARIANTS SATISFIED", out)

    def test_A2_an_obstructed_report_never_reads_as_satisfied(self):
        report = sheaf_report(nf_b="y")
        self.assertFalse(report.is_gluing_admissible)
        p = os.path.join(self.d, "bad.pdf")
        sh.generate_sheaf_pdf(report, p)
        rc, out = run_pdf(p, "--audit")
        self.assertEqual(rc, 2, out)
        self.assertIn("OBSTRUCTED", out)
        self.assertNotIn("ALL INVARIANTS SATISFIED", out)
        self.assertNotIn("GLUING ADMISSIBLE (as recorded", out)

    def test_A3_an_in_place_edit_without_rehash_is_caught(self):
        p = os.path.join(self.d, "ok.pdf")
        sh.generate_sheaf_pdf(sheaf_report(), p)
        raw = open(p, "rb").read()
        open(p, "wb").write(raw.replace(b'"is_admissible": true', b'"is_admissible": false')
                               .replace(b'"is_admissible":true', b'"is_admissible":false'))
        rc, out = run_pdf(p, "--audit")
        self.assertEqual(rc, 1, out)
        self.assertIn("self-consistency check failed", out)

    def test_A4_a_rehashed_forgery_is_reported_only_as_a_recorded_verdict(self):
        """The runner's scope: even a self-consistent forgery is echoed, never
        re-derived. The claim is honest because it names that boundary."""
        report = sheaf_report(nf_b="y")
        p = os.path.join(self.d, "bad.pdf")
        sh.generate_sheaf_pdf(report, p)
        raw = open(p, "rb").read().decode("latin-1")
        m = re.search(r"MANIFEST_DATA = json\.loads\('''(.*?)'''\)", raw, re.S)
        data = json.loads(m.group(1))
        data.update(is_admissible=True, h1_dimension=0, rejection_reason="NONE", global_normal_form="y")
        new_json = json.dumps(data, sort_keys=True, separators=(",", ":"))
        new_hash = hashlib.sha256(new_json.encode()).hexdigest()
        forged = raw.replace(m.group(1), new_json)
        forged = re.sub(r'MANIFEST_HASH = "[0-9a-f]{64}"', f'MANIFEST_HASH = "{new_hash}"', forged)
        open(p, "wb").write(forged.encode("latin-1"))
        rc, out = run_pdf(p, "--audit")
        self.assertEqual(rc, 0, out)
        # It passes self-consistency, but never claims to have verified anything.
        self.assertIn("did NOT re-derive", out)
        self.assertIn("asserts", out)
        self.assertNotIn("ALL INVARIANTS SATISFIED", out)


class EgraphRunnerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.d = self._tmp.name

    def doc(self, name="egraph.pdf"):
        g = eg.EGraph()
        g.add_term(parse("S K K x"))
        g.add_term(parse("x"))
        g.saturate(eg.STANDARD_COMBINATOR_RULES, max_iterations=6)
        p = os.path.join(self.d, name)
        eg.generate_egraph_pdf(g, p, sample_proof=g.explain_equivalence(parse("S K K x"), parse("x")))
        return g, p

    def test_B1_a_genuine_document_asserts_no_soundness(self):
        _, p = self.doc()
        rc, out = run_pdf(p, cwd=self.d)
        self.assertEqual(rc, 0, out)
        self.assertIn("Manifest self-consistency: OK", out)
        self.assertIn("asserts no soundness", out)
        self.assertNotIn("congruence closure sound", out)

    def test_B2_an_edited_manifest_is_caught(self):
        _, p = self.doc()
        raw = open(p, "rb").read()
        pre = eg._EGRAPH_MANIFEST_PREFIX_BYTES
        i = raw.rindex(pre) + len(pre)
        j = raw.index(b"\n", i)
        man = json.loads(raw[i:j])
        man["total_classes"] = 999999
        man["classes"] = {}
        open(p, "wb").write(raw[:i] + json.dumps(man, sort_keys=True).encode() + raw[j:])
        rc, out = run_pdf(p, cwd=self.d)
        self.assertEqual(rc, 1, out)
        self.assertIn("self-consistency check failed", out)
        self.assertNotIn("asserts no soundness", out)

    def test_B3_a_document_without_a_manifest_is_refused(self):
        p = os.path.join(self.d, "empty.pdf")
        open(p, "w").write("print('hi')\n")
        rc, out = run_pdf(p, cwd=self.d)
        self.assertEqual(rc, 0)  # this one is not our runner; sanity only
        _, real = self.doc("real.pdf")
        stripped = open(real, "rb").read()
        pre = eg._EGRAPH_MANIFEST_PREFIX_BYTES
        i = stripped.rindex(pre)
        p2 = os.path.join(self.d, "nomani.pdf")
        open(p2, "wb").write(stripped[:i] + b"# (manifest removed)\n" + b"if __name__=='__main__':\n import egraph_kernel\n")
        # The genuine runner, with its manifest lines removed, refuses.
        runner_only = stripped[stripped.rindex(b"'''\n") + 4:]
        p3 = os.path.join(self.d, "runner_no_manifest.pdf")
        open(p3, "wb").write(b"r'''\nnothing\n'''\n" + runner_only)
        rc3, out3 = run_pdf(p3, cwd=self.d)
        self.assertEqual(rc3, 1, out3)
        self.assertIn("No self-verifying E-Graph manifest", out3)

    def test_B4_append_hud_carries_a_self_consistent_last_manifest(self):
        """The appended HUD's manifest is verifiable by the same recompute the
        runner does. (Executing an appended polyglot is an S8 concern: PDF bytes
        follow the runner, so the appended file is not valid Python. Not claimed.)"""
        g, p = self.doc()
        source = open(p, "rb").read()
        out_path = os.path.join(self.d, "appended.pdf")
        appended = eg.append_egraph_hud(source, out_path, g)
        self.assertTrue(appended.startswith(source))
        m_pre, h_pre = eg._EGRAPH_MANIFEST_PREFIX_BYTES, eg._EGRAPH_HASH_PREFIX_BYTES
        mi = appended.rindex(m_pre) + len(m_pre)
        manifest_bytes = appended[mi:appended.index(b"\n", mi)]
        hi = appended.rindex(h_pre) + len(h_pre)
        recorded = appended[hi:appended.index(b"\n", hi)].decode("ascii").strip()
        self.assertEqual(hashlib.sha256(manifest_bytes).hexdigest(), recorded)
        # and the appended manifest is the LAST one, after the source's own
        self.assertGreater(appended.rindex(m_pre), len(source) - 1)


class NoForeignCodeTest(unittest.TestCase):
    """Section C: the egraph runner ran planted code before S7."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.d = self._tmp.name

    def egraph_doc(self, where):
        g = eg.EGraph()
        g.add_term(parse("I x"))
        g.add_term(parse("x"))
        g.saturate(eg.STANDARD_COMBINATOR_RULES, max_iterations=6)
        p = os.path.join(where, "egraph.pdf")
        eg.generate_egraph_pdf(g, p, sample_proof=g.explain_equivalence(parse("I x"), parse("x")))
        return p

    def plant(self, where):
        sentinel = os.path.join(where, "PLANTED_RAN")
        with open(os.path.join(where, "egraph_kernel.py"), "w") as f:
            f.write("import pathlib, os\n"
                    f"pathlib.Path({sentinel!r}).write_text('ran')\n"
                    "class EGraph:\n"
                    "    @classmethod\n"
                    "    def from_dict(cls, d):\n"
                    "        return cls()\n")
        return sentinel

    def test_C1_a_planted_module_in_the_cwd_does_not_run(self):
        run_dir = os.path.join(self.d, "run")
        os.makedirs(run_dir)
        pdf = self.egraph_doc(self.d)
        sentinel = self.plant(run_dir)
        rc, out = run_pdf(pdf, cwd=run_dir)
        self.assertEqual(rc, 0, out)
        self.assertFalse(os.path.exists(sentinel), "the runner executed a planted egraph_kernel.py from the cwd")
        self.assertIn("Manifest self-consistency: OK", out)

    def test_C2_a_planted_module_beside_the_document_does_not_run(self):
        pdf = self.egraph_doc(self.d)
        sentinel = self.plant(self.d)
        rc, out = run_pdf(pdf, cwd=os.path.dirname(self.d))
        self.assertEqual(rc, 0, out)
        self.assertFalse(os.path.exists(sentinel), "the runner executed a planted module beside the document")


if __name__ == "__main__":
    unittest.main()
