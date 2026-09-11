#!/usr/bin/env python3
"""
EXP-001 runner: refusal, readoption, evolution.

The pre-registered predictions live in README.md next to this file, and
`PREDICTIONS` below must equal them; `test_exp001.py` checks that it does.
Amendment 1 (AMENDMENT-1.md) added the attribution checks after the first
recorded run. They were not pre-registered and are reported separately.

Every admission decision is made by the real CLI, run as a subprocess against
one organism document. The registry files are written by the library, as an
issuer would. Every identifier and digest in the record is derived from the
bytes the CLI actually consumed, read back from disk right before each step.
The first version of this runner took ids from the objects in memory and
digests from disk, so a record could name a readoption the consumed file did
not contain. Nothing secret is written into the record or the evidence bundle.
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
from keystore import PRIVATE_KEY_SUFFIX                          # noqa: E402

# Must equal the table in README.md, which was committed before this file.
PREDICTIONS = {
    "S1": {"exit": 0, "scope": None, "document": "changes"},
    "S2": {"exit": 1, "scope": "REFUTED_FOR_REFERENCE", "document": "unchanged"},
    "S3": {"exit": 1, "scope": "REFUTED_FOR_ANOTHER_REFERENCE", "document": "unchanged"},
    "S4": {"exit": 0, "scope": None, "document": "changes"},
    "S5": {"exit": 0, "scope": None, "document": "changes", "generation": 1},
    "S6": {"exit": 1, "scope": "REFUTED_FOR_REFERENCE", "document": "unchanged"},
}

PROTOCOL = "EXP-001 + amendment 1"
LABEL = "exp001-refutation"
INPUT = "x"
OTHER_REFERENCE = "\U0001f90d"
REGISTRY_NAMES = ("R_same", "R_other", "R_same_readopted")
_SCOPE = re.compile(r"refutation scope (\w+)")


def _sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


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
    shutil.copy(doc + PRIVATE_KEY_SUFFIX, target + PRIVATE_KEY_SUFFIX)
    return target


def _write_registry(registry, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(registry.to_dict(), fh, sort_keys=True)
    return path


def _git(*args):
    proc = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else None


def _step(name, doc, target, start_from, registry_name, registry_path, flags, consumed):
    """Run one CLI step. The registry bytes are read here, right before the CLI
    reads the same file, and kept so every later check uses exactly them."""
    registry_bytes = _read(registry_path) if registry_path else None
    if registry_bytes is not None:
        consumed[name] = registry_bytes
    before, key_before = _sha_bytes(_read(doc)), _read(doc + PRIVATE_KEY_SUFFIX)
    proc = _cli("autopoiesis", "evolve", doc, *flags)
    after = _sha_bytes(_read(doc))
    match = _SCOPE.search(proc.stdout)
    return {
        "step": name,
        "target": target,
        "start_from": start_from,
        "registry": registry_name,
        "registry_sha256": _sha_bytes(registry_bytes) if registry_bytes is not None else None,
        "flags": [f for f in flags if not f.endswith(".json")],
        "exit": proc.returncode,
        "scope": match.group(1) if match else None,
        "document": "unchanged" if before == after else "changes",
        "document_sha256_before": before,
        "document_sha256_after": after,
        "generation_after": _generation(doc),
        "key_unchanged": _read(doc + PRIVATE_KEY_SUFFIX) == key_before,
        "refusal_says_not_modified": "The organism was not modified" in proc.stdout,
        "traceback": "Traceback" in proc.stderr,
    }


def _load(registry_bytes):
    return EpistemicTombstoneRegistry.from_document(json.loads(registry_bytes.decode("utf-8")))


def _attribution(consumed, steps, d0, reference, candidate):
    """Amendment 1. Checks that the inputs the CLI consumed are the inputs the
    conclusion is about. Each failure is named by the check it breaks."""
    found = []

    def miss(check, detail):
        found.append({"check": check, "detail": detail})

    by = {s["step"]: s for s in steps}
    for step in ("S2", "S3", "S4", "S5", "S6"):
        if step not in consumed:
            miss(f"{step} consumed a registry file", "no registry bytes recorded")
    if found:
        return found

    if consumed["S6"] != consumed["S2"]:
        miss("S6 consumes exactly the S2 registry", "registry bytes differ")
    if consumed["S4"] != consumed["S3"]:
        miss("S4 consumes exactly the S3 registry", "registry bytes differ")

    loaded = {}
    for step in ("S2", "S3", "S5"):
        try:
            loaded[step] = _load(consumed[step])
        except Exception as exc:
            miss(f"{step} registry file loads", f"{type(exc).__name__}: {exc}")
    if len(loaded) != 3:
        return found
    same, other, readopted = loaded["S2"], loaded["S3"], loaded["S5"]

    if set(same.tombstones) != {LABEL} or same.readoptions:
        miss("S2 registry holds only the refutation",
             f"tombstones {sorted(same.tombstones)}, readoptions {sorted(same.readoptions)}")
    elif not same.tombstones[LABEL].rule_identity \
            or not same.tombstones[LABEL].rule_identity.addresses(candidate, reference):
        miss("S2 refutation addresses the pair under test", "identity does not match")
    if set(other.tombstones) != {LABEL} or other.readoptions:
        miss("S3 registry holds only the other-reference refutation",
             f"tombstones {sorted(other.tombstones)}, readoptions {sorted(other.readoptions)}")
    elif not other.tombstones[LABEL].rule_identity \
            or not other.tombstones[LABEL].rule_identity.addresses(candidate, OTHER_REFERENCE):
        miss("S3 refutation addresses the candidate against the other reference",
             "identity does not match")

    same_doc = json.loads(consumed["S2"].decode("utf-8"))
    s5_doc = json.loads(consumed["S5"].decode("utf-8"))
    if s5_doc.get("tombstones") != same_doc.get("tombstones"):
        miss("S5 retains the S2 retirement unchanged",
             f"S5 tombstones {sorted(s5_doc.get('tombstones') or {})} differ from S2's")
    if set(readopted.readoptions) != {LABEL}:
        miss("S5 adds exactly one readoption, for the refuted subject",
             f"readoptions {sorted(readopted.readoptions)}")
    else:
        tomb = readopted.tombstones.get(LABEL)
        if tomb is None or not readopted.readoptions[LABEL].is_admissible_for(LABEL, tomb):
            miss("S5 readoption is valid and linked to that retirement",
                 "is_admissible_for returned False")

    if by["S5"]["document_sha256_before"] != by["S6"]["document_sha256_before"]:
        miss("S5 and S6 start from identical document bytes", "start digests differ")
    for step in ("S1", "S2", "S3", "S4"):
        if by[step]["document_sha256_before"] != d0:
            miss(f"{step} starts from the genesis document", "start digest differs from D0")
    return found


def _registry_summary(registry_bytes):
    """Ids read from the consumed bytes. None where the file does not hold one."""
    summary = {"sha256": _sha_bytes(registry_bytes)}
    try:
        registry = _load(registry_bytes)
    except Exception as exc:
        summary["load_error"] = f"{type(exc).__name__}: {exc}"
        return summary
    tomb = registry.tombstones.get(LABEL)
    readoption = registry.readoptions.get(LABEL)
    summary["retirement_record_id"] = tomb.record_id if tomb else None
    summary["readoption_record_id"] = readoption.record_id if readoption else None
    return summary


def run_experiment(workdir, tamper=None, evidence_dir=None):
    """Run the sequence in `workdir`.

    `tamper(name, path, context)`, when given, is called once per registry file
    after all three are written and before any step, so a control can replace a
    real file handed to the real CLI. `evidence_dir`, when given, receives the
    consumed registry bytes, which hold public keys and signatures only.
    """
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # The tree is described as it was BEFORE this run wrote anything. Read at
    # the end, the flag also counted this run's own evidence bundle whenever
    # that was written inside the repository, and a clean checkout was reported
    # dirty.
    repo_commit = _git("rev-parse", "HEAD")
    dirty_paths = [line[3:] for line in (_git("status", "--porcelain") or "").splitlines()
                   if line.strip()]
    main = os.path.join(workdir, "organism.pdf")
    proc = _cli("autopoiesis", "init", "-o", main)
    if proc.returncode != 0:
        raise RuntimeError(f"genesis failed: {proc.stdout}{proc.stderr}")
    d0 = _sha_bytes(_read(main))
    steps, consumed = [], {}

    # S1: learn the pair evolution really makes, on a fork.
    fork1 = _fork(main, "fork-s1.pdf")
    genome_before = _genome(fork1)
    steps.append(_step("S1", fork1, "fork", "genesis document", None, None, [], consumed))
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
    readopted.readopt(target_id=LABEL, justification="EXP-001 readoption",
                      new_evidence_claim_id="e" * 64, author_sk_hex=sk, author_pk_hex=pk)
    paths = {
        "R_same": _write_registry(same, os.path.join(workdir, "R_same.json")),
        "R_other": _write_registry(other, os.path.join(workdir, "R_other.json")),
        "R_same_readopted": _write_registry(
            readopted, os.path.join(workdir, "R_same_readopted.json")),
    }
    if tamper is not None:
        context = {"label": LABEL, "reference": reference, "candidate": candidate,
                   "input": INPUT, "other_reference": OTHER_REFERENCE, "paths": dict(paths)}
        for name in REGISTRY_NAMES:
            tamper(name, paths[name], context)

    steps.append(_step("S2", main, "main", "genesis document", "R_same", paths["R_same"],
                       ["--tombstones", paths["R_same"]], consumed))
    steps.append(_step("S3", main, "main", "genesis document", "R_other", paths["R_other"],
                       ["--tombstones", paths["R_other"]], consumed))
    fork4 = _fork(main, "fork-s4.pdf")
    steps.append(_step("S4", fork4, "fork", "main after S3", "R_other", paths["R_other"],
                       ["--tombstones", paths["R_other"],
                        "--also-proceed-on", "REFUTED_FOR_ANOTHER_REFERENCE"], consumed))
    fork6 = _fork(main, "fork-s6.pdf")
    steps.append(_step("S5", main, "main", "main after S4", "R_same_readopted",
                       paths["R_same_readopted"],
                       ["--tombstones", paths["R_same_readopted"]], consumed))
    steps.append(_step("S6", fork6, "fork", "main immediately before S5", "R_same",
                       paths["R_same"], ["--tombstones", paths["R_same"]], consumed))

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

    attribution = _attribution(consumed, steps, d0, reference, candidate)

    if evidence_dir is not None:
        os.makedirs(evidence_dir, exist_ok=True)
        for name, step in (("R_same", "S2"), ("R_other", "S3"), ("R_same_readopted", "S5")):
            with open(os.path.join(evidence_dir, f"{name}.json"), "wb") as fh:
                fh.write(consumed[step])

    return {
        "experiment": "EXP-001",
        "protocol": PROTOCOL,
        "started_utc": started,
        "repo_commit": repo_commit,
        "repo_dirty": bool(dirty_paths),
        "repo_dirty_paths": dirty_paths,
        "repo_state_read": "before the run wrote anything",
        "python": sys.version.split()[0],
        "genesis_document_sha256": d0,
        "main_document_unchanged_through_s3": steps[1]["document_sha256_before"] == d0
                                              and steps[2]["document_sha256_after"] == d0,
        "pair": {"gene_id": gene, "reference": reference, "candidate": candidate,
                 "input": INPUT, "other_reference": OTHER_REFERENCE},
        "registries": {name: _registry_summary(consumed[step]) for name, step in
                       (("R_same", "S2"), ("R_other", "S3"), ("R_same_readopted", "S5"))},
        "issuer_public_key": pk,
        "steps": steps,
        "predictions": PREDICTIONS,
        "mismatches": mismatches,
        "all_predictions_held": not mismatches,
        "attribution_mismatches": attribution,
        "attribution_held": not attribution,
        "holds": not mismatches and not attribution,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", help="write the result record here")
    parser.add_argument("--evidence", help="write the consumed registry files here")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as workdir:
        result = run_experiment(workdir, evidence_dir=args.evidence)
    print(f"{result['protocol']} at {result['repo_commit']} (dirty={result['repo_dirty']})")
    print(f"pair: gene {result['pair']['gene_id']}  "
          f"{result['pair']['reference']!r} -> {result['pair']['candidate']!r}")
    print(f"{'step':<5}{'start from':<28}{'registry':<18}{'exit':<6}{'scope':<32}document")
    for s in result["steps"]:
        print(f"{s['step']:<5}{s['start_from']:<28}{str(s['registry']):<18}{s['exit']:<6}"
              f"{str(s['scope']):<32}{s['document']}")
    print("registered predictions held" if result["all_predictions_held"]
          else f"PREDICTION MISMATCHES: {result['mismatches']}")
    print("attribution checks held" if result["attribution_held"]
          else f"ATTRIBUTION MISMATCHES: {result['attribution_mismatches']}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, ensure_ascii=False, sort_keys=True)
            fh.write("\n")
    return 0 if result["holds"] else 1


if __name__ == "__main__":
    sys.exit(main())
