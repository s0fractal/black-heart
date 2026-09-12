#!/usr/bin/env python3
"""Offline verifier for the frozen R2 anchoring package.

TWO SEPARATE checks, never conflated, each reporting PASS / FAIL /
NOT_PERFORMED. A missing source is NOT_PERFORMED -- never PASS.

  A. package reading  -- the saved bytes are read with SEPARATELY pinned
     trust/root/tip and are NOT regenerated. It has two parts:
       A1 byte facts, reader-independent (stdlib JSON only): sha256, the 32-byte
          commitment, and its equality with the root OF THE SAVED BYTES;
       A2 replay under the pinned trust/root/tip using the reader from the
          package's OWN source commit -- the reader contemporaneous with the
          package, not today's working tree.
  B. source reproducibility -- the generator is run from an exact, SEPARATELY
     EXPECTED source commit and its output compared with the frozen bytes.

Why A2 uses the contemporaneous reader: this package is historical evidence
bound to its own commit. Later evolution of the generator/reader must never
make it "invalid" or force the freeze to be rewritten. How today's in-tree
reader behaves on it is reported as a COMPATIBILITY observation only, and can
never fail this verification.

Check B (and A2) need the expected commit supplied by the caller, so the
manifest cannot attest to its own provenance; a manifest naming a different
commit is a FAIL, not a skip.

Nothing here touches the network or OpenTimestamps. Verifying this package is
NOT verifying an external anchor -- that is R2, which needs a real .ots proof
and an accepted Bitcoin source.

Exit: 0 = every check PASS; 1 = some check FAILED; 2 = no failure but something
NOT_PERFORMED.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

PASS, FAIL, NOT_PERFORMED = "PASS", "FAIL", "NOT_PERFORMED"

_HERE = Path(__file__).resolve().parent            # .../EXP-LIB-001/r2-anchor
_EXP = _HERE.parent                                # .../EXP-LIB-001
_REPO = _EXP.parent.parent                         # repo root

# Replay the SAVED bytes with the reader of a given tree, with regeneration
# forbidden. Prints one JSON line.
_REPLAY = """\
import json, pathlib, sys
sys.path.insert(0, sys.argv[1])
import run
def _forbidden(*a, **k):
    raise RuntimeError("the reading path must not regenerate the journal")
run.build_journal = _forbidden
pkg = pathlib.Path(sys.argv[2]).read_bytes()
rep = run.verify_package(pkg, run.caller_trust(), sys.argv[3], sys.argv[4])
print(json.dumps({"accepted": bool(rep["accepted"]),
                  "root_matches": rep["root_matches"],
                  "tip_matches": rep["tip_matches"],
                  "boundary": rep.get("boundary")}))
"""

_GENERATE = """\
import sys
sys.path.insert(0, sys.argv[1])
import run
sys.stdout.buffer.write(run.journal_to_bytes(run.build_journal()))
"""


def load_package(pkg_dir: Path):
    manifest = json.loads((pkg_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    package = (pkg_dir / "journal.pkg").read_bytes()
    commitment = (pkg_dir / "root.commitment").read_bytes()
    return manifest, package, commitment


def materialise_source(commit: str, dest: Path):
    """Extract the repo tree at `commit` into `dest`. Returns the path to that
    commit's experiments/EXP-LIB-001, or a reason string if unavailable."""
    if not commit:
        return "no expected source commit supplied"
    try:
        proc = subprocess.run(["git", "-C", str(_REPO), "archive",
                               "--format=tar", commit],
                              capture_output=True, timeout=120)
    except FileNotFoundError:
        return "git is not available on this host"
    except subprocess.TimeoutExpired:
        return "git archive timed out"
    if proc.returncode != 0:
        return (f"commit {commit[:12]} is not available here "
                "(shallow clone or missing object)")
    tar_path = dest / "tree.tar"
    tar_path.write_bytes(proc.stdout)
    with tarfile.open(tar_path) as tf:
        tf.extractall(dest)                                  # noqa: S202
    tar_path.unlink()
    gen = dest / "experiments" / "EXP-LIB-001"
    if not (gen / "run.py").is_file():
        return f"commit {commit[:12]} has no experiments/EXP-LIB-001/run.py"
    return gen


def _replay_with(gen_dir: Path, pkg_path: Path, root: str, tip: str):
    proc = subprocess.run([sys.executable, "-B", "-c", _REPLAY, str(gen_dir),
                           str(pkg_path), root, tip],
                          capture_output=True, timeout=300)
    if proc.returncode != 0:
        tail = proc.stderr.decode("utf-8", "replace").strip().splitlines()[-2:]
        return None, f"reader failed to run: {tail}"
    try:
        return json.loads(proc.stdout.decode("utf-8").strip()), None
    except Exception as e:                                   # noqa: BLE001
        return None, f"reader output unparseable: {type(e).__name__}: {e}"


def byte_facts(pkg_dir: Path):
    """A1: reader-independent facts about the frozen bytes (stdlib JSON only)."""
    try:
        manifest, package, commitment = load_package(pkg_dir)
    except Exception as e:                                   # noqa: BLE001
        return FAIL, [f"package files unreadable: {type(e).__name__}: {e}"]
    notes = []

    if hashlib.sha256(package).hexdigest() != manifest["package_sha256"]:
        return FAIL, ["journal.pkg sha256 != MANIFEST.package_sha256"]
    notes.append("journal.pkg matches MANIFEST.package_sha256")

    if len(commitment) != 32:
        return FAIL, [f"root.commitment is {len(commitment)} bytes, not 32"]
    if commitment.hex() != manifest["root_event_hash"]:
        return FAIL, ["root.commitment != MANIFEST.root_event_hash"]
    notes.append("root.commitment is exactly 32 raw bytes and equals the pinned root")

    if hashlib.sha256(commitment).hexdigest() != manifest["leaf_sha256_of_commitment"]:
        return FAIL, ["SHA256(commitment) != MANIFEST.leaf_sha256_of_commitment"]
    notes.append("leaf SHA256(commitment) matches the manifest")

    try:
        events = json.loads(package.decode("utf-8"))
        saved_root = events[0]["event_hash"]
        saved_tip = events[-1]["event_hash"]
    except Exception as e:                                   # noqa: BLE001
        return FAIL, [f"saved bytes are not a readable journal: {type(e).__name__}: {e}"]
    if saved_root != commitment.hex():
        return FAIL, ["root of the SAVED bytes != commitment"]
    if saved_tip != manifest["tip_event_hash"]:
        return FAIL, ["tip of the SAVED bytes != MANIFEST.tip_event_hash"]
    notes.append("root/tip of the saved bytes equal the separately pinned root/tip")
    return PASS, notes


def current_reader_compatibility(pkg_dir: Path):
    """Informational only: does TODAY's in-tree reader still accept the frozen
    package? A 'no' is a compatibility note, never an invalidation."""
    try:
        manifest, package, _c = load_package(pkg_dir)
        gen_dir = _EXP
        rep, err = _replay_with(gen_dir, pkg_dir / "journal.pkg",
                                manifest["root_event_hash"], manifest["tip_event_hash"])
        if err:
            return f"current in-tree reader could not run: {err}"
        if rep["accepted"]:
            return "current in-tree reader also accepts the frozen package"
        return ("current in-tree reader no longer accepts it "
                f"({rep['boundary']}) -- a compatibility note, NOT an invalidation")
    except Exception as e:                                   # noqa: BLE001
        return f"compatibility check could not run: {type(e).__name__}: {e}"


def check_package_reading(pkg_dir: Path, source_dir=None):
    """A: A1 byte facts (always) + A2 replay with the package's CONTEMPORANEOUS
    reader (needs the source tree). Without that source, A2 -- and therefore A --
    is NOT_PERFORMED, never PASS."""
    status, notes = byte_facts(pkg_dir)
    if status != PASS:
        return FAIL, notes

    if not isinstance(source_dir, Path):
        reason = source_dir if isinstance(source_dir, str) else "no source tree supplied"
        notes.append(f"A2 replay NOT PERFORMED: {reason}")
        notes.append(current_reader_compatibility(pkg_dir))
        return NOT_PERFORMED, notes

    manifest, _pkg, _c = load_package(pkg_dir)
    rep, err = _replay_with(source_dir, pkg_dir / "journal.pkg",
                            manifest["root_event_hash"], manifest["tip_event_hash"])
    if err:
        return FAIL, notes + [f"contemporaneous reader: {err}"]
    if not (rep["accepted"] and rep["root_matches"] and rep["tip_matches"]):
        return FAIL, notes + [f"contemporaneous reader did not accept: {rep}"]
    notes.append("replayed under the pinned trust/root/tip by the reader from the "
                 "package's own commit (regeneration forbidden: build_journal raises)")
    notes.append(current_reader_compatibility(pkg_dir))
    return PASS, notes


def check_source_reproducibility(pkg_dir: Path, expect_commit, source_dir=None):
    """B: run the generator from the exact, separately EXPECTED source commit and
    compare with the frozen bytes."""
    try:
        manifest, package, _c = load_package(pkg_dir)
    except Exception as e:                                   # noqa: BLE001
        return FAIL, [f"package files unreadable: {type(e).__name__}: {e}"]

    if not expect_commit:
        return NOT_PERFORMED, [
            "no expected source commit supplied; provenance from the named "
            "commit was NOT checked (a manifest may not attest to its own source)"]

    named = manifest.get("source_commit", "")
    if not (isinstance(named, str) and named.lower() == str(expect_commit).lower()):
        return FAIL, [f"MANIFEST.source_commit is {named!r}, expected {expect_commit!r}"]

    if not isinstance(source_dir, Path):
        reason = source_dir if isinstance(source_dir, str) else "source tree unavailable"
        return NOT_PERFORMED, [f"{reason}; the generator was NOT run"]

    proc = subprocess.run([sys.executable, "-B", "-c", _GENERATE, str(source_dir)],
                          capture_output=True, cwd=source_dir.parent.parent, timeout=300)
    if proc.returncode != 0:
        tail = proc.stderr.decode("utf-8", "replace").strip().splitlines()[-3:]
        return FAIL, [f"generator at {str(expect_commit)[:12]} failed: {tail}"]
    if proc.stdout != package:
        return FAIL, [
            f"generator at {str(expect_commit)[:12]} produced "
            f"{hashlib.sha256(proc.stdout).hexdigest()[:16]}..., frozen bytes are "
            f"{hashlib.sha256(package).hexdigest()[:16]}..."]
    return PASS, [f"generator run from {str(expect_commit)[:12]} reproduces the "
                  f"frozen bytes exactly ({len(package)} bytes)"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--expect-commit", default=os.environ.get("R2_EXPECT_COMMIT"),
                    help="the exact source commit the frozen package must come "
                         "from; without it A2 and B are NOT_PERFORMED")
    ap.add_argument("--package-dir", default=str(_HERE))
    args = ap.parse_args(argv)
    pkg_dir = Path(args.package_dir).resolve()

    with tempfile.TemporaryDirectory() as tmp:
        source = materialise_source(args.expect_commit, Path(tmp))
        results = [
            ("A. package reading (saved bytes, pinned trust/root/tip, no regeneration)",
             check_package_reading(pkg_dir, source)),
            ("B. source reproducibility (generator run from the expected commit)",
             check_source_reproducibility(pkg_dir, args.expect_commit, source)),
        ]

        print("Frozen R2 anchoring package -- two separate checks\n")
        for title, (status, notes) in results:
            print(f"[{status}] {title}")
            for n in notes:
                print(f"        - {n}")
        statuses = [s for _t, (s, _n) in results]

    manifest = json.loads((pkg_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    print(f"\n  manifest source_commit : {manifest.get('source_commit')!r} "
          "(claimed; checked only against an expectation supplied by the caller)")
    print("  stamp target           : root.commitment (32 raw bytes)")
    print(f"  R2 status              : {manifest.get('r2_status')} "
          f"| R3: {manifest.get('r3_status')}")

    if FAIL in statuses:
        print("\nRESULT: FAILED -- see the failing check above.")
        return 1
    if NOT_PERFORMED in statuses:
        print("\nRESULT: not fully verified -- something was NOT PERFORMED "
              "(this is not a pass).")
        return 2
    print("\nRESULT: both checks PASSED -- the frozen bytes are consistent, read "
          "by their contemporaneous reader, AND reproduced by the generator at "
          "the expected commit.\n        (This is not an external anchor: R2 "
          f"remains {manifest.get('r2_status')}.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
