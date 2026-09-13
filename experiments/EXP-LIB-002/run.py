#!/usr/bin/env python3
"""EXP-LIB-002 runner: one document's history through two transitions.

Predictions were committed first: experiments/EXP-LIB-002/PREDICTIONS.md.
This runner adds NO mechanism. It drives the existing `cli.py library ...`
commands as subprocesses, saves every artifact of the honest history, runs the
pre-registered negative controls, and records observed-vs-predicted.

    python3 experiments/EXP-LIB-002/run.py --out <new dir>
    python3 experiments/EXP-LIB-002/run.py --reproducibility --out <new dir>
    python3 experiments/EXP-LIB-002/run.py --verify-saved <saved run dir>

Keys are deterministic PUBLIC FIXTURE keys, one per role. They are written to a
private temporary directory, never into the saved run, and attest nothing about
any real person.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

import crypto                      # noqa: E402
import glyph                       # noqa: E402
import library_interaction as li   # noqa: E402
import warrant_kernel as wk        # noqa: E402

CLI = REPO / "cli.py"
K, I = "🖤", "🤍"
ROLE_SEEDS = {"author": 11, "proposer": 12, "decider": 13, "issuer": 14}
CLAIMS = {"C0": (K, 100), "C1": (f"{I} {I}", 100), "C2": (f"{I} ({I} {I})", 100)}
PREDICTED_REFUSALS = {"N1a": "RECEIPT_PARENT_MISMATCH", "N1b": "RECEIPT_PARENT_MISMATCH",
                      "N2": "RECEIPT_SUCCESSOR_MISMATCH", "N3": "PARENT_CLAIMS_DROPPED",
                      "N4": "RECEIPT_UNREADABLE"}


def sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fixture_key(role):
    sk = bytes([ROLE_SEEDS[role]] * 32)
    return sk.hex(), crypto.public_key_from_secret(sk).hex()


def grounded_claim(name):
    term, budget = CLAIMS[name]
    expected = glyph.evaluate(glyph.parse(term), max_atp=budget).hash
    ph = glyph.term_hash(glyph.parse(term))
    a_sk, a_pk = fixture_key("author")
    return wk.EdgeClaim.create_and_sign(
        ph, term, term, ph, wk.Polarity.AFFIRM,
        wk.GroundedWitness(term_expr=term, expected_hash=expected, atp_budget=budget),
        a_sk, a_pk)


def cli(*args):
    proc = subprocess.run([sys.executable, "-B", str(CLI), "library", *args, "--json"],
                          cwd=str(REPO), capture_output=True, text=True, timeout=300)
    try:
        body = json.loads(proc.stdout)
    except ValueError:
        body = {"ok": False, "refusal": "UNPARSEABLE_OUTPUT",
                "detail": (proc.stdout + proc.stderr)[-400:]}
    return proc.returncode, body


def records(pdf):
    """Whole claim records, canonically encoded, with multiplicity. Computed here,
    independently of library_interaction's own comparison."""
    res = li.read_parent(str(pdf))
    return collections.Counter(
        json.dumps(c, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        for c in res["manifest"]["claims"])


def included(smaller, larger) -> bool:
    return all(larger.get(k, 0) >= n for k, n in smaller.items())


def source_state():
    try:
        commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain",
                                "--", ".", ":!experiments/EXP-LIB-002/run"],
                               capture_output=True, text=True).stdout.strip()
        return commit or None, (not dirty) if commit else None
    except FileNotFoundError:
        return None, None


def transition(label, parent, claim, out, keys, policy):
    tdir = out / label
    tdir.mkdir()
    (tdir / "claim.json").write_text(json.dumps(claim.to_dict(), indent=2, sort_keys=True))
    parent_sha = sha(parent)
    succ = out / {"T1": "P1.pdf", "T2": "P2.pdf"}[label]
    steps = {}
    steps["add_claim"] = cli("add-claim", "--pdf", str(parent),
                             "--expect-parent-sha256", parent_sha,
                             "--claim", str(tdir / "claim.json"),
                             "--proposer-key-file", str(keys["proposer"]),
                             "--out", str(tdir / "proposal.json"))
    steps["evaluate"] = cli("evaluate", "--pdf", str(parent),
                            "--proposal", str(tdir / "proposal.json"),
                            "--policy", str(policy),
                            "--decider-key-file", str(keys["decider"]),
                            "--out", str(tdir / "decision.json"))
    steps["apply"] = cli("apply", "--pdf", str(parent),
                         "--proposal", str(tdir / "proposal.json"),
                         "--decision", str(tdir / "decision.json"),
                         "--policy", str(policy),
                         "--issuer-key-file", str(keys["issuer"]),
                         "--out", str(succ), "--receipt", str(tdir / "receipt.json"))
    return steps, succ


def explain(parent, succ, tdir, receipt=None):
    _, i_pk = fixture_key("issuer")
    return cli("explain-transition", "--parent", str(parent), "--successor", str(succ),
               "--proposal", str(tdir / "proposal.json"),
               "--decision", str(tdir / "decision.json"),
               "--receipt", str(receipt if receipt is not None else tdir / "receipt.json"),
               "--expect-issuer-pk", i_pk)


def run_once(out: Path) -> dict:
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"--out {out} must be a new or empty directory")
    out.mkdir(parents=True, exist_ok=True)
    commit, clean = source_state()
    keydir = Path(tempfile.mkdtemp(prefix="exp-lib-002-keys-"))
    scratch = Path(tempfile.mkdtemp(prefix="exp-lib-002-controls-"))
    try:
        keys = {}
        for role in ("proposer", "decider", "issuer"):
            sk, _ = fixture_key(role)
            keys[role] = keydir / f"{role}.key"
            keys[role].write_text(sk + "\n")
        _, a_pk = fixture_key("author")
        policy = out / "policy.json"
        policy.write_text(json.dumps({
            "profile": li.POLICY_PROFILE,
            "trust_config": {"trusted_author_pks": [a_pk], "admitted_grades": ["GROUNDED"],
                             "max_atp_budget": 10000, "require_bound_signature": True},
            "allowed_operations": ["add-claim"], "allowed_grades": ["GROUNDED"]},
            indent=2, sort_keys=True))

        c = {n: grounded_claim(n) for n in CLAIMS}
        p0 = out / "P0.pdf"
        wk.generate_warrant_ledger_pdf([c["C0"]], str(p0), wk.TrustConfig())
        created = {"P0": sha(p0)}

        t1, p1 = transition("T1", p0, c["C1"], out, keys, policy)
        created["P1"] = sha(p1) if p1.exists() else None
        t2, p2 = transition("T2", p1, c["C2"], out, keys, policy)
        created["P2"] = sha(p2) if p2.exists() else None
        e1, e2 = explain(p0, p1, out / "T1"), explain(p1, p2, out / "T2")

        obs, ok = {}, {}

        def check(pid, observed, expected):
            obs[pid] = observed
            ok[pid] = observed == expected

        for pid, steps, before, after in (("H1", t1, 1, 2), ("H2", t2, 2, 3)):
            ev, ap = steps["evaluate"][1], steps["apply"][1]
            check(pid, {"evaluation_status": ev.get("evaluation_status"),
                        "admitted": ev.get("admitted"), "apply_exit": steps["apply"][0],
                        "transition_state": ap.get("transition_state"),
                        "cleanup_complete": ap.get("cleanup_complete"),
                        "claims": [ap.get("claims_before"), ap.get("claims_after")]},
                  {"evaluation_status": "pass", "admitted": True, "apply_exit": 0,
                   "transition_state": "COMPLETE", "cleanup_complete": True,
                   "claims": [before, after]})
        for pid, (code, body), before, after in (("H3", e1, 1, 2), ("H4", e2, 2, 3)):
            check(pid, {"exit": code, "transition": body.get("transition"),
                        "claims_preserved": body.get("claims_preserved"),
                        "claims_after": body.get("claims_after"),
                        "regenerated": body.get("regenerated")},
                  {"exit": 0, "transition": "COMPLETE", "claims_preserved": before,
                   "claims_after": after, "regenerated": False})
        check("H5", {"P0_unchanged": sha(p0) == created["P0"],
                     "P1_unchanged": created["P1"] is not None and sha(p1) == created["P1"]},
              {"P0_unchanged": True, "P1_unchanged": True})
        r0, r1, r2 = records(p0), records(p1), records(p2)
        check("H6", {"P0_in_P1": included(r0, r1), "P0_in_P2": included(r0, r2),
                     "P1_in_P2": included(r1, r2)},
              {"P0_in_P1": True, "P0_in_P2": True, "P1_in_P2": True})
        code, body = cli("inspect", "--pdf", str(p2))
        check("H7", {"claim_count": body.get("claim_count"),
                     "manifest_format": body.get("manifest_format")},
              {"claim_count": 3, "manifest_format": "WARRANT-0.2"})
        atp = {}
        for label, name in (("T1", "C1"), ("T2", "C2")):
            ev = json.loads((out / label / "decision.json").read_text())["body"]["evaluator"]
            term, budget = CLAIMS[name]
            actual = glyph.evaluate(glyph.parse(term), max_atp=budget).atp_spent
            atp[label] = {"measured": ev["atp_spent_measured"],
                          "equals_independent_count": ev["atp_spent"] == actual}
        check("H8", atp, {"T1": {"measured": True, "equals_independent_count": True},
                          "T2": {"measured": True, "equals_independent_count": True}})
        _, i_pk = fixture_key("issuer")
        with mock.patch.object(li, "render_successor_pdf",
                               side_effect=AssertionError("regeneration forbidden")):
            nr = [li.explain_transition(str(par), str(suc), str(out / t / "proposal.json"),
                                        str(out / t / "decision.json"),
                                        str(out / t / "receipt.json"), i_pk)
                  for par, suc, t in ((p0, p1, "T1"), (p1, p2, "T2"))]
        check("H9", [r.get("transition") for r in nr], ["COMPLETE", "COMPLETE"])

        # ---- negative controls (forged artifacts live in scratch, not in the run)
        refusals = {}
        refusals["N1a"] = explain(p1, p2, out / "T2", receipt=out / "T1" / "receipt.json")
        refusals["N1b"] = explain(p0, p1, out / "T1", receipt=out / "T2" / "receipt.json")
        claims = json.loads(json.dumps(li.read_parent(str(p2))["manifest"]["claims"]))
        for rec in claims:
            if rec.get("claim_id") == c["C0"].claim_id:
                rec["body"]["tau"] = "🌿 modified"          # body changed, id kept
        forged = scratch / "P2_modified.pdf"
        forged.write_bytes(li.render_successor_pdf(claims, ["forged: C0 modified"]))
        refusals["N2"] = cli("explain-transition", "--parent", str(p1), "--successor",
                             str(forged), "--proposal", str(out / "T2" / "proposal.json"),
                             "--decision", str(out / "T2" / "decision.json"),
                             "--receipt", str(out / "T2" / "receipt.json"),
                             "--expect-issuer-pk", i_pk)
        genuine = json.loads((out / "T2" / "receipt.json").read_text())["body"]
        body = li.receipt_body(genuine["parent_pdf_sha256"], sha(forged),
                               genuine["proposal_id"], genuine["decision_id"],
                               genuine["policy_sha256"], genuine["added_claim_id"], i_pk)
        rid = li.compute_receipt_id(body)
        i_sk, _ = fixture_key("issuer")
        reissued = scratch / "receipt_reissued.json"
        reissued.write_text(json.dumps({
            "profile": li.TRANSITION_PROFILE, "body": body, "receipt_id": rid,
            "receipt_signature_hex": crypto.sign_hex(i_sk, li.receipt_message(rid))}))
        refusals["N3"] = cli("explain-transition", "--parent", str(p1), "--successor",
                             str(forged), "--proposal", str(out / "T2" / "proposal.json"),
                             "--decision", str(out / "T2" / "decision.json"),
                             "--receipt", str(reissued), "--expect-issuer-pk", i_pk)
        refusals["N4"] = explain(p1, p2, out / "T2", receipt=scratch / "absent.json")
        for pid, (code, body) in refusals.items():
            check(pid, {"exit": code, "refusal": body.get("refusal")},
                  {"exit": 2, "refusal": PREDICTED_REFUSALS[pid]})

        digests = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob("*"))
                   if p.is_file() and p.name != "RESULT.json"}
        result = {
            "experiment": "EXP-LIB-002",
            "predictions": "experiments/EXP-LIB-002/PREDICTIONS.md",
            "source_commit": commit, "source_tree_clean": clean,
            "python": platform.python_version(), "platform": platform.platform(),
            "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
            "observed": obs,
            "verdicts": {k: ("CONFIRMED" if v else "REFUTED") for k, v in ok.items()},
            "all_confirmed": all(ok.values()),
            "digests": digests,
            "note": ("public fixture keys; outcomes attest one bounded check per claim "
                     "under one caller policy, not that any document is true"),
        }
        (out / "RESULT.json").write_text(json.dumps(result, indent=2, sort_keys=True,
                                                    ensure_ascii=False) + "\n")
        return result
    finally:
        shutil.rmtree(keydir, ignore_errors=True)
        shutil.rmtree(scratch, ignore_errors=True)


def outcome_view(result):
    """Everything predicted for H and N, without digests or host detail."""
    return {k: v for k, v in result["observed"].items()}


def reproducibility(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=False)
    runs = {}
    for label, seed in [("seed0_a", "0"), ("seed0_b", "0")] + \
            [(f"seed{s}", str(s)) for s in range(1, 6)]:
        env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONDONTWRITEBYTECODE="1")
        proc = subprocess.run([sys.executable, "-B", str(Path(__file__)), "--out",
                               str(out / label)], cwd=str(REPO), env=env,
                              capture_output=True, text=True, timeout=1800)
        res = json.loads((out / label / "RESULT.json").read_text())
        runs[label] = {"seed": seed, "exit": proc.returncode, "result": res}
    first = outcome_view(runs["seed0_a"]["result"])
    r1 = all(outcome_view(r["result"]) == first for r in runs.values())
    a, b = runs["seed0_a"]["result"]["digests"], runs["seed0_b"]["result"]["digests"]
    r2 = a == b
    p0 = {label: runs[label]["result"]["digests"]["P0.pdf"]
          for label in ("seed0_a", "seed1", "seed2", "seed3", "seed4", "seed5")}
    r3 = len(set(p0.values())) > 1
    report = {
        "R1_outcomes_identical_across_seeds": r1,
        "R2_bytes_identical_with_fixed_seed": r2,
        "R2_differing_files": sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k)),
        "R3_p0_digests_not_all_equal_across_seeds_0_5": r3,
        "R3_distinct_p0_digests": len(set(p0.values())),
        "verdicts": {"R1": "CONFIRMED" if r1 else "REFUTED",
                     "R2": "CONFIRMED" if r2 else "REFUTED",
                     "R3": "CONFIRMED" if r3 else "REFUTED"},
        "every_run_confirmed_H_and_N": all(r["result"]["all_confirmed"]
                                           for r in runs.values()),
    }
    (out / "REPRODUCIBILITY.json").write_text(json.dumps(report, indent=2,
                                                         sort_keys=True) + "\n")
    return report


def verify_saved(saved: Path) -> dict:
    """Verify a saved history WITHOUT regenerating anything."""
    result = json.loads((saved / "RESULT.json").read_text())
    _, i_pk = fixture_key("issuer")
    out = {}
    for name in ("P0.pdf", "P1.pdf", "P2.pdf"):
        out[f"{name}_digest_matches_record"] = sha(saved / name) == result["digests"][name]
    with mock.patch.object(li, "render_successor_pdf",
                           side_effect=AssertionError("regeneration forbidden")):
        for par, suc, t in (("P0.pdf", "P1.pdf", "T1"), ("P1.pdf", "P2.pdf", "T2")):
            r = li.explain_transition(str(saved / par), str(saved / suc),
                                      str(saved / t / "proposal.json"),
                                      str(saved / t / "decision.json"),
                                      str(saved / t / "receipt.json"), i_pk)
            out[f"{t}_transition"] = r.get("transition") or r.get("refusal")
    out["all_ok"] = all(v is True or v == "COMPLETE" for v in out.values())
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--reproducibility", action="store_true")
    ap.add_argument("--verify-saved", type=Path)
    args = ap.parse_args(argv)
    if args.verify_saved:
        res = verify_saved(args.verify_saved)
        print(json.dumps(res, indent=2, sort_keys=True))
        return 0 if res["all_ok"] else 1
    if args.out is None:
        ap.error("--out is required")
    if args.reproducibility:
        res = reproducibility(args.out)
        print(json.dumps(res, indent=2, sort_keys=True))
        return 0 if all(v == "CONFIRMED" for v in res["verdicts"].values()) else 1
    res = run_once(args.out)
    for pid, verdict in sorted(res["verdicts"].items()):
        print(f"{pid:4s} {verdict}")
    print("ALL CONFIRMED" if res["all_confirmed"] else "NOT ALL CONFIRMED")
    return 0 if res["all_confirmed"] else 1


if __name__ == "__main__":
    sys.exit(main())
