#!/usr/bin/env python3
"""
EXP-001 runner: refusal, readoption, evolution.

The pre-registered predictions live in README.md next to this file, and
`PREDICTIONS` below must equal them; `test_exp001.py` checks that it does.

Every admission decision is made by the real CLI, run as a subprocess against
one organism document. The registry files are written by the library, as an
issuer would. Nothing secret is written into the record: keys are ephemeral,
live only in the temporary directory, and are compared, never copied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
if sys.path[:1] != [REPO]:
    sys.path.insert(0, REPO)

import crypto                                                    # noqa: E402
import autopoiesis                                               # noqa: E402
from controlled_forgetting import (                              # noqa: E402
    EpistemicTombstoneRegistry, RetirementMode, RuleIdentity,
)

# Must equal the table in README.md, which was committed before this file.
PREDICTIONS = {
    "S1": {"exit": 0, "scope": None, "document": "changes"},
    "S2": {"exit": 1, "scope": "REFUTED_FOR_REFERENCE", "document": "unchanged"},
    "S3": {"exit": 1, "scope": "REFUTED_FOR_ANOTHER_REFERENCE", "document": "unchanged"},
    "S4": {"exit": 0, "scope": None, "document": "changes"},
    "S5": {"exit": 0, "scope": None, "document": "changes", "generation": 1},
    "S6": {"exit": 1, "scope": "REFUTED_FOR_REFERENCE", "document": "unchanged"},
}

LABEL = "exp001-refutation"
INPUT = "x"
OTHER_REFERENCE = "\U0001f90d"
_SCOPE = re.compile(r"refutation scope (\w+)")


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _read(path):
    with open(path, "rb") as fh:
        return fh.read()


def _cli(*args):
    return subprocess.run([sys.executable, "-B", os.path.join(REPO, "cli.py"), *args],
                          cwd=REPO, capture_output=True, text=True, timeout=600)


def _manifest(doc):
    content = _read(doc)
    prefix = autopoiesis.AUTOPOIESIS_MANIFEST_PREFIX.encode("utf-8")
    idx = content.rfind(prefix)
    end = content.find(b"\n", idx)
    return json.loads(content[idx + len(prefix):end].decode("utf-8"))


def _genome(doc):
    organism = _manifest(doc)["current_organism"]
    return {c["gene_id"]: c["expression"] for c in organism["chromosomes"]}


def _generation(doc):
    return int(_manifest(doc)["current_organism"]["generation"])


def _fork(doc, name):
    target = os.path.join(os.path.dirname(doc), name)
    shutil.copy(doc, target)
    shutil.copy(doc + ".key", target + ".key")
    return target


def _write_registry(registry, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(registry.to_dict(), fh, sort_keys=True)
    return path


def _git(*args):
    proc = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else None


def _step(name, doc, target, registry_name, flags):
    before, key_before = _sha(doc), _read(doc + ".key")
    proc = _cli("autopoiesis", "evolve", doc, *flags)
    after = _sha(doc)
    match = _SCOPE.search(proc.stdout)
    return {
        "step": name,
        "target": target,
        "registry": registry_name,
        "flags": [f for f in flags if not f.endswith(".json")],
        "exit": proc.returncode,
        "scope": match.group(1) if match else None,
        "document": "unchanged" if before == after else "changes",
        "document_sha256_before": before,
        "document_sha256_after": after,
        "generation_after": _generation(doc),
        "key_unchanged": _read(doc + ".key") == key_before,
        "refusal_says_not_modified": "The organism was not modified" in proc.stdout,
        "traceback": "Traceback" in proc.stderr,
    }


def run_experiment(workdir):
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    main = os.path.join(workdir, "organism.pdf")
    proc = _cli("autopoiesis", "init", "-o", main)
    if proc.returncode != 0:
        raise RuntimeError(f"genesis failed: {proc.stdout}{proc.stderr}")
    d0 = _sha(main)
    steps = []

    # S1: learn the pair evolution really makes, on a fork.
    fork1 = _fork(main, "fork-s1.pdf")
    genome_before = _genome(fork1)
    steps.append(_step("S1", fork1, "fork taken at genesis", None, []))
    changed = [(g, genome_before[g], e) for g, e in _genome(fork1).items()
               if genome_before[g] != e]
    if len(changed) != 1:
        raise RuntimeError(f"expected one replaced gene, found {changed}")
    gene, reference, candidate = changed[0]

    # Issuer side: one refutation of the pair, one of another pair, one readoption.
    sk, pk = crypto.generate_keypair()
    same = EpistemicTombstoneRegistry()
    same.retire(LABEL, "d" * 64, RetirementMode.REFUTED,
                "EXP-001: a signed assertion that the candidate is refuted against "
                "this reference; the pair is a sound rewrite, so it is not a "
                "genuine counterexample", sk, pk,
                rule_identity=RuleIdentity.from_terms(LABEL, reference, candidate, INPUT))
    other = EpistemicTombstoneRegistry()
    other.retire(LABEL, "d" * 64, RetirementMode.REFUTED,
                 "EXP-001: the same candidate asserted refuted against another reference",
                 sk, pk,
                 rule_identity=RuleIdentity.from_terms(LABEL, OTHER_REFERENCE, candidate, INPUT))
    readopted = EpistemicTombstoneRegistry.from_document(same.to_dict())
    readoption = readopted.readopt(target_id=LABEL, justification="EXP-001 readoption",
                                   new_evidence_claim_id="e" * 64,
                                   author_sk_hex=sk, author_pk_hex=pk)
    r_same = _write_registry(same, os.path.join(workdir, "R_same.json"))
    r_other = _write_registry(other, os.path.join(workdir, "R_other.json"))
    r_readopted = _write_registry(readopted, os.path.join(workdir, "R_same_readopted.json"))

    steps.append(_step("S2", main, "main", "R_same", ["--tombstones", r_same]))
    steps.append(_step("S3", main, "main", "R_other", ["--tombstones", r_other]))
    fork4 = _fork(main, "fork-s4.pdf")
    steps.append(_step("S4", fork4, "fork taken after S3", "R_other",
                       ["--tombstones", r_other,
                        "--also-proceed-on", "REFUTED_FOR_ANOTHER_REFERENCE"]))
    fork6 = _fork(main, "fork-s6.pdf")
    steps.append(_step("S5", main, "main", "R_same_readopted",
                       ["--tombstones", r_readopted]))
    steps.append(_step("S6", fork6, "fork taken before S5", "R_same",
                       ["--tombstones", r_same]))

    mismatches = []
    for step in steps:
        expected = PREDICTIONS[step["step"]]
        for field, value in expected.items():
            actual = step["generation_after"] if field == "generation" else step[field]
            if actual != value:
                mismatches.append({"step": step["step"], "field": field,
                                   "predicted": value, "observed": actual})
        if step["exit"] != 0:
            for field, want in (("key_unchanged", True), ("refusal_says_not_modified", True),
                                ("traceback", False)):
                if step[field] != want:
                    mismatches.append({"step": step["step"], "field": field,
                                       "predicted": want, "observed": step[field]})

    return {
        "experiment": "EXP-001",
        "started_utc": started,
        "repo_commit": _git("rev-parse", "HEAD"),
        "repo_dirty": bool(_git("status", "--porcelain")),
        "python": sys.version.split()[0],
        "genesis_document_sha256": d0,
        "main_document_unchanged_through_s3": steps[1]["document_sha256_before"] == d0
                                              and steps[2]["document_sha256_after"] == d0,
        "pair": {"gene_id": gene, "reference": reference, "candidate": candidate,
                 "input": INPUT, "other_reference": OTHER_REFERENCE},
        "registries": {
            "R_same": {"sha256": _sha(r_same),
                       "record_id": same.tombstones[LABEL].record_id},
            "R_other": {"sha256": _sha(r_other),
                        "record_id": other.tombstones[LABEL].record_id},
            "R_same_readopted": {"sha256": _sha(r_readopted),
                                 "readoption_record_id": readoption.record_id},
        },
        "issuer_public_key": pk,
        "steps": steps,
        "predictions": PREDICTIONS,
        "mismatches": mismatches,
        "all_predictions_held": not mismatches,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", help="write the result record here")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as workdir:
        result = run_experiment(workdir)
    print(f"EXP-001 at {result['repo_commit']} (dirty={result['repo_dirty']})")
    print(f"pair: gene {result['pair']['gene_id']}  "
          f"{result['pair']['reference']!r} -> {result['pair']['candidate']!r}")
    print(f"{'step':<5}{'target':<24}{'registry':<18}{'exit':<6}{'scope':<32}document")
    for s in result["steps"]:
        print(f"{s['step']:<5}{s['target']:<24}{str(s['registry']):<18}{s['exit']:<6}"
              f"{str(s['scope']):<32}{s['document']}")
    print("all predictions held" if result["all_predictions_held"]
          else f"MISMATCHES: {result['mismatches']}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, ensure_ascii=False, sort_keys=True)
            fh.write("\n")
    return 0 if result["all_predictions_held"] else 1


if __name__ == "__main__":
    sys.exit(main())
