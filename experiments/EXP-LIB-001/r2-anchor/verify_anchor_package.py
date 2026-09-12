#!/usr/bin/env python3
"""Offline verifier for the frozen R2 anchoring package.

Checks the frozen bytes are internally consistent and reproducible WITHOUT any
network access and WITHOUT contacting OpenTimestamps. It verifies existence of a
well-formed commitment to stamp; it does NOT verify an external anchor (that is
R2, which needs a real .ots proof and an accepted Bitcoin source -- separate).

Exit 0 iff every invariant holds. Run from the repo root or anywhere.
"""
import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))          # .../EXP-LIB-001/r2-anchor
_EXP = os.path.dirname(_HERE)                               # .../EXP-LIB-001
_REPO = os.path.dirname(os.path.dirname(_EXP))              # repo root
sys.path.insert(0, _REPO)
sys.path.insert(0, _EXP)
import run as EXP


def _fail(msg):
    print("FAIL:", msg)
    raise SystemExit(1)


def main():
    man = json.load(open(os.path.join(_HERE, "MANIFEST.json")))
    pkg = open(os.path.join(_HERE, "journal.pkg"), "rb").read()
    commitment = open(os.path.join(_HERE, "root.commitment"), "rb").read()

    # 1. package bytes match the manifest digest
    if hashlib.sha256(pkg).hexdigest() != man["package_sha256"]:
        _fail("journal.pkg sha256 != MANIFEST.package_sha256")

    # 2. commitment file is EXACTLY 32 raw bytes and equals the manifest root
    if len(commitment) != 32:
        _fail(f"root.commitment is {len(commitment)} bytes, not 32")
    if commitment.hex() != man["root_event_hash"]:
        _fail("root.commitment != MANIFEST.root_event_hash")

    # 3. commitment equals the ROOT OF THE SAVED PACKAGE (not a rebuild)
    parsed = EXP.journal_from_bytes(pkg)
    if parsed[0]["event_hash"] != commitment.hex():
        _fail("saved package root != commitment")
    if parsed[-1]["event_hash"] != man["tip_event_hash"]:
        _fail("saved package tip != MANIFEST.tip_event_hash")

    # 4. the R1 reader accepts the saved bytes under the pinned root/tip
    rep = EXP.verify_package(pkg, EXP.caller_trust(),
                             man["root_event_hash"], man["tip_event_hash"])
    if not (rep["accepted"] and rep["root_matches"] and rep["tip_matches"]):
        _fail(f"R1 reader did not accept the saved package: {rep}")

    # 5. determinism: the current runner reproduces the frozen bytes exactly, so
    #    the frozen commitment still corresponds to this source (no drift)
    if EXP.journal_to_bytes(EXP.build_journal()) != pkg:
        _fail("current runner does not reproduce the frozen journal bytes "
              "(the frozen commitment no longer matches main)")

    # 6. leaf the .ots proof will commit to (SHA256 of the 32 raw bytes)
    leaf = hashlib.sha256(commitment).hexdigest()
    if leaf != man["leaf_sha256_of_commitment"]:
        _fail("leaf SHA256(commitment) != MANIFEST")

    print("PASS: frozen R2 anchoring package is consistent and reproducible")
    print("  source_commit :", man["source_commit"])
    print("  root          :", man["root_event_hash"])
    print("  tip           :", man["tip_event_hash"])
    print("  package_sha256:", man["package_sha256"])
    print("  stamp target  : root.commitment (32 raw bytes)")
    print("  leaf to anchor:", leaf)
    print("  R2 status     :", man["r2_status"], "| R3:", man["r3_status"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
