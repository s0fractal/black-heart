#!/usr/bin/env python3
"""
EXP-002 runner: the issuer as the one declared factor.

The pre-registered predictions and attribution checks live in README.md next to
this file, committed before this runner existed. `PREDICTIONS` below must equal
the README table; `test_exp002.py` checks that it does.

Every admission decision is made by the real CLI, run as a subprocess against
one organism document. Registry and policy files are written by the library, as
an issuer and an operator would. Every id and digest in the record is read from
the bytes the CLI consumed, captured right before each step, and the tree state
is read before this run writes anything. Nothing secret is written into the
record or the evidence bundle.
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
    EpistemicTombstoneRegistry, RetirementMode, RetirementRecord, RuleIdentity,
)
from epistemic_immune import (                                   # noqa: E402
    IssuerPolicy, ResurrectionDefense, RefutationScope, _canonical_key,
)

# Must equal the table in README.md, which was committed before this file.
PREDICTIONS = {
    "S1": {"exit": 0, "scope": None, "document": "changes"},
    "S2": {"exit": 1, "scope": "REFUTED_FOR_REFERENCE", "document": "unchanged"},
    "S3": {"exit": 1, "scope": "UNAUTHORIZED_ISSUER", "document": "unchanged"},
    "S4": {"exit": 0, "scope": None, "document": "changes"},
    "S5": {"exit": 1, "scope": "REFUTED_FOR_REFERENCE", "document": "unchanged"},
    "S6": {"exit": 1, "scope": "REFUTED_FOR_REFERENCE", "document": "unchanged"},
    "S7": {"exit": 0, "scope": None, "document": "changes", "generation": 1},
    "S8": {"exit": 1, "scope": "REFUTED_FOR_REFERENCE", "document": "unchanged"},
}

LABEL = "exp002-refutation"
INPUT = "x"
FIXED_TIMESTAMP = "2026-09-11T00:00:00Z"
LOSS = ("EXP-002: a signed assertion that the candidate is refuted against this "
        "reference; the pair is a sound rewrite, so it is not a genuine counterexample")
REGISTRY_NAMES = ("R_T", "R_F", "R_T+F", "R_T+T")
_SCOPE = re.compile(r"refutation scope (\w+)")
_POLICY_STEPS = ("S2", "S3", "S4", "S5", "S7", "S8")


def _sha(data):
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
    return json.loads(content[idx + len(prefix):content.find(b"\n", idx)].decode("utf-8"))


def _genome(doc):
    return {c["gene_id"]: c["expression"]
            for c in _manifest(doc)["current_organism"]["chromosomes"]}


def _generation(doc):
    return int(_manifest(doc)["current_organism"]["generation"])


def _fork(doc, name):
    target = os.path.join(os.path.dirname(doc), name)
    shutil.copy(doc, target)
    shutil.copy(doc + ".key", target + ".key")
    return target


def _git(*args):
    proc = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else None


def _write_json(doc, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, sort_keys=True)
    return path


def _retirement(sk, pk, identity):
    """The same assertion for every key: fixed timestamp, fixed loss, fixed identity."""
    record = RetirementRecord(
        record_id="", target_id=LABEL, target_digest="d" * 64, mode=RetirementMode.REFUTED,
        loss_declaration=LOSS, negative_space_coverage=0.0, atp_gas_recovered=0,
        author_pk_hex=pk, signature_hex="", timestamp_utc=FIXED_TIMESTAMP,
        rule_identity=identity)
    record.sign(sk)
    registry = EpistemicTombstoneRegistry()
    registry.tombstones[LABEL] = record
    return registry


def _with_readoption(base_doc, sk, pk):
    registry = EpistemicTombstoneRegistry.from_document(base_doc)
    registry.readopt(target_id=LABEL, justification="EXP-002 readoption",
                     new_evidence_claim_id="e" * 64, author_sk_hex=sk, author_pk_hex=pk)
    return registry


def _step(name, doc, start_from, registry_name, registry_path, policy_path, flags, consumed):
    """One CLI step. Registry and policy bytes are captured here, right before
    the CLI reads the same files, and every later check uses exactly them."""
    reg = _read(registry_path) if registry_path else None
    pol = _read(policy_path) if policy_path else None
    consumed[name] = {"registry": reg, "policy": pol}
    argv = ["autopoiesis", "evolve", doc]
    if registry_path:
        argv += ["--tombstones", registry_path]
    if policy_path:
        argv += ["--trusted-issuers", policy_path]
    argv += flags
    before, key_before = _sha(_read(doc)), _read(doc + ".key")
    proc = _cli(*argv)
    after = _sha(_read(doc))
    match = _SCOPE.search(proc.stdout)
    return {
        "step": name,
        "start_from": start_from,
        "registry": registry_name,
        "registry_sha256": _sha(reg) if reg is not None else None,
        "policy_sha256": _sha(pol) if pol is not None else None,
        "flags": flags,
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


def _load_registry(data):
    return EpistemicTombstoneRegistry.from_document(json.loads(data.decode("utf-8")))


def _load_policy(data):
    return IssuerPolicy.from_document(json.loads(data.decode("utf-8")))


def _body_without_author(record):
    body = dict(record.body_dict())
    body.pop("author_pk_hex")
    return body


def _attribution(consumed, steps, d0, pair, pk_t, pk_f):
    """Registered in README.md from the start. Each failure names its check."""
    found = []

    def miss(check, detail):
        found.append({"check": check, "detail": detail})

    by = {s["step"]: s for s in steps}
    t, f = _canonical_key(pk_t), _canonical_key(pk_f)
    reference, candidate = pair["reference"], pair["candidate"]

    # Policy: identical bytes wherever one is used, none at S6, exactly T in both roles.
    policies = {consumed[s]["policy"] for s in _POLICY_STEPS}
    if len(policies) != 1 or None in policies:
        miss("every policy-bearing step consumes the same policy bytes",
             f"{len(policies)} distinct policy inputs")
    if consumed["S6"]["policy"] is not None:
        miss("S6 consumes no policy", "a policy file was passed")
    policy = None
    try:
        policy = _load_policy(consumed["S2"]["policy"])
    except Exception as exc:
        miss("the policy file loads", f"{type(exc).__name__}: {exc}")
    if policy is not None:
        if policy.retirement_issuers != frozenset({t}) or policy.readoption_issuers != frozenset({t}):
            miss("the policy trusts exactly T in both roles",
                 f"retirement {sorted(policy.retirement_issuers)}, "
                 f"readoption {sorted(policy.readoption_issuers)}")

    # Registries, each loaded from the bytes the CLI consumed.
    loaded = {}
    for step in ("S2", "S3", "S5", "S7"):
        try:
            loaded[step] = _load_registry(consumed[step]["registry"])
        except Exception as exc:
            miss(f"{step} registry file loads", f"{type(exc).__name__}: {exc}")
    if len(loaded) != 4:
        return found
    rt, rf, rtf, rtt = loaded["S2"], loaded["S3"], loaded["S5"], loaded["S7"]

    def single_retirement(registry, step, key, who):
        if set(registry.tombstones) != {LABEL} or registry.readoptions:
            miss(f"{step} holds only the retirement",
                 f"tombstones {sorted(registry.tombstones)}, "
                 f"readoptions {sorted(registry.readoptions)}")
            return None
        record = registry.tombstones[LABEL]
        if _canonical_key(record.author_pk_hex) != key:
            miss(f"{step} retirement is signed by {who}", "author is another key")
        if not record.rule_identity or not record.rule_identity.addresses(candidate, reference):
            miss(f"{step} retirement addresses the pair under test", "identity does not match")
        return record

    by_t = single_retirement(rt, "S2", t, "T")
    by_f = single_retirement(rf, "S3", f, "F")
    if by_t is not None and by_f is not None and \
            _body_without_author(by_t) != _body_without_author(by_f):
        miss("S3 is S2's assertion, only the key differs", "bodies differ beyond the author")

    if consumed["S4"]["registry"] != consumed["S3"]["registry"]:
        miss("S4 consumes exactly the S3 registry", "registry bytes differ")
    if consumed["S6"]["registry"] != consumed["S3"]["registry"]:
        miss("S6 consumes exactly the S3 registry", "registry bytes differ")
    if consumed["S8"]["registry"] != consumed["S2"]["registry"]:
        miss("S8 consumes exactly the S2 registry", "registry bytes differ")

    s2_tombs = json.loads(consumed["S2"]["registry"].decode("utf-8")).get("tombstones")

    def lifted_by(registry, step, key, who):
        doc = json.loads(consumed[step]["registry"].decode("utf-8"))
        if doc.get("tombstones") != s2_tombs:
            miss(f"{step} keeps the S2 retirement unchanged", "tombstones differ from S2's")
        if set(registry.readoptions) != {LABEL}:
            miss(f"{step} adds exactly one readoption, by {who}",
                 f"readoptions {sorted(registry.readoptions)}")
            return
        readoption = registry.readoptions[LABEL]
        tomb = registry.tombstones.get(LABEL)
        if tomb is None or not readoption.is_admissible_for(LABEL, tomb):
            miss(f"{step} readoption is authentic and linked to that retirement",
                 "is_admissible_for returned False")
        if _canonical_key(readoption.author_pk_hex) != key:
            miss(f"{step} adds exactly one readoption, by {who}", "author is another key")

    lifted_by(rtf, "S5", f, "F")
    lifted_by(rtt, "S7", t, "T")

    if policy is not None:
        report = ResurrectionDefense.refuted_for(rtf, candidate, reference, policy)
        if report.scope != RefutationScope.REFUTED_FOR_REFERENCE or \
                report.ignored_readoptions != (LABEL,):
            miss("the library ignores S5's foreign readoption under the consumed policy",
                 f"scope {report.scope.value}, ignored {report.ignored_readoptions}")

    for step in ("S1", "S2", "S3", "S4", "S5"):
        if by[step]["document_sha256_before"] != d0:
            miss(f"{step} starts from the genesis document", "start digest differs from D0")
    for step in ("S6", "S8"):
        if by[step]["document_sha256_before"] != by["S7"]["document_sha256_before"]:
            miss(f"{step} starts from the same bytes as S7", "start digests differ")
    return found


def _registry_summary(data):
    summary = {"sha256": _sha(data)}
    try:
        registry = _load_registry(data)
    except Exception as exc:
        summary["load_error"] = f"{type(exc).__name__}: {exc}"
        return summary
    tomb, readoption = registry.tombstones.get(LABEL), registry.readoptions.get(LABEL)
    summary.update({
        "retirement_record_id": tomb.record_id if tomb else None,
        "retirement_author": _canonical_key(tomb.author_pk_hex) if tomb else None,
        "readoption_record_id": readoption.record_id if readoption else None,
        "readoption_author": _canonical_key(readoption.author_pk_hex) if readoption else None,
    })
    return summary


def _policy_summary(data):
    summary = {"sha256": _sha(data)}
    try:
        policy = _load_policy(data)
    except Exception as exc:
        summary["load_error"] = f"{type(exc).__name__}: {exc}"
        return summary
    summary.update({"retirement_issuers": sorted(policy.retirement_issuers),
                    "readoption_issuers": sorted(policy.readoption_issuers)})
    return summary


def run_experiment(workdir, tamper=None, evidence_dir=None):
    """Run the registered sequence in `workdir`.

    `tamper(name, path, context)` is called once per input file (the four
    registries and "P") after all are written and before any step. The
    context carries public material only.
    """
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    repo_commit = _git("rev-parse", "HEAD")
    dirty_paths = [line[3:] for line in (_git("status", "--porcelain") or "").splitlines()
                   if line.strip()]
    main = os.path.join(workdir, "organism.pdf")
    proc = _cli("autopoiesis", "init", "-o", main)
    if proc.returncode != 0:
        raise RuntimeError(f"genesis failed: {proc.stdout}{proc.stderr}")
    d0 = _sha(_read(main))
    steps, consumed = [], {}

    fork1 = _fork(main, "fork-s1.pdf")
    before = _genome(fork1)
    steps.append(_step("S1", fork1, "fork of genesis", None, None, None, [], consumed))
    changed = [(g, before[g], e) for g, e in _genome(fork1).items() if before[g] != e]
    if len(changed) != 1:
        raise RuntimeError(f"expected one replaced gene, found {changed}")
    gene, reference, candidate = changed[0]
    pair = {"gene_id": gene, "reference": reference, "candidate": candidate, "input": INPUT}

    sk_t, pk_t = crypto.generate_keypair()
    sk_f, pk_f = crypto.generate_keypair()
    identity = RuleIdentity.from_terms(LABEL, reference, candidate, INPUT)
    r_t = _retirement(sk_t, pk_t, identity)
    r_f = _retirement(sk_f, pk_f, identity)
    paths = {
        "R_T": _write_json(r_t.to_dict(), os.path.join(workdir, "R_T.json")),
        "R_F": _write_json(r_f.to_dict(), os.path.join(workdir, "R_F.json")),
        "R_T+F": _write_json(_with_readoption(r_t.to_dict(), sk_f, pk_f).to_dict(),
                             os.path.join(workdir, "R_T+F.json")),
        "R_T+T": _write_json(_with_readoption(r_t.to_dict(), sk_t, pk_t).to_dict(),
                             os.path.join(workdir, "R_T+T.json")),
        "P": _write_json({"retirement_issuers": [pk_t], "readoption_issuers": [pk_t]},
                         os.path.join(workdir, "P.json")),
    }
    if tamper is not None:
        context = {"label": LABEL, "input": INPUT, "reference": reference,
                   "candidate": candidate, "pk_t": pk_t, "pk_f": pk_f,
                   "paths": dict(paths)}
        for name in REGISTRY_NAMES + ("P",):
            tamper(name, paths[name], context)

    P = paths["P"]
    steps.append(_step("S2", main, "main", "R_T", paths["R_T"], P, [], consumed))
    steps.append(_step("S3", main, "main", "R_F", paths["R_F"], P, [], consumed))
    fork4 = _fork(main, "fork-s4.pdf")
    steps.append(_step("S4", fork4, "fork of main after S3", "R_F", paths["R_F"], P,
                       ["--also-proceed-on", "UNAUTHORIZED_ISSUER"], consumed))
    steps.append(_step("S5", main, "main", "R_T+F", paths["R_T+F"], P, [], consumed))
    fork6, fork8 = _fork(main, "fork-s6.pdf"), _fork(main, "fork-s8.pdf")
    steps.append(_step("S6", fork6, "fork of main before S7", "R_F", paths["R_F"], None,
                       [], consumed))
    steps.append(_step("S7", main, "main", "R_T+T", paths["R_T+T"], P, [], consumed))
    steps.append(_step("S8", fork8, "fork of main before S7", "R_T", paths["R_T"], P,
                       [], consumed))

    mismatches = []
    for step in steps:
        for field, value in PREDICTIONS[step["step"]].items():
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

    attribution = _attribution(consumed, steps, d0, pair, pk_t, pk_f)

    evidence = {"R_T": "S2", "R_F": "S3", "R_T+F": "S5", "R_T+T": "S7"}
    if evidence_dir is not None:
        os.makedirs(evidence_dir, exist_ok=True)
        for name, step in evidence.items():
            with open(os.path.join(evidence_dir, f"{name}.json"), "wb") as fh:
                fh.write(consumed[step]["registry"])
        with open(os.path.join(evidence_dir, "P.json"), "wb") as fh:
            fh.write(consumed["S2"]["policy"])

    return {
        "experiment": "EXP-002",
        "started_utc": started,
        "repo_commit": repo_commit,
        "repo_dirty": bool(dirty_paths),
        "repo_dirty_paths": dirty_paths,
        "repo_state_read": "before the run wrote anything",
        "python": sys.version.split()[0],
        "genesis_document_sha256": d0,
        "pair": pair,
        "keys": {"T": _canonical_key(pk_t), "F": _canonical_key(pk_f)},
        "registries": {name: _registry_summary(consumed[step]["registry"])
                       for name, step in evidence.items()},
        "policy": _policy_summary(consumed["S2"]["policy"]),
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
    parser.add_argument("--evidence", help="write the consumed registry and policy files here")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as workdir:
        result = run_experiment(workdir, evidence_dir=args.evidence)
    print(f"EXP-002 at {result['repo_commit']} (dirty={result['repo_dirty']})")
    print(f"pair: gene {result['pair']['gene_id']}  "
          f"{result['pair']['reference']!r} -> {result['pair']['candidate']!r}")
    print(f"{'step':<5}{'starts from':<26}{'registry':<9}{'policy':<8}{'exit':<6}"
          f"{'scope':<24}document")
    for s in result["steps"]:
        print(f"{s['step']:<5}{s['start_from']:<26}{str(s['registry']):<9}"
              f"{'P' if s['policy_sha256'] else '-':<8}{s['exit']:<6}"
              f"{str(s['scope']):<24}{s['document']}")
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
