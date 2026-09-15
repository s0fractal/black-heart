"""Hidden host grader for CALIB-MYC-1 (PLAN.md, H1-H7).

Run by the HOST, never inside the receiver session:

    python3 grade_checks.py SNAPSHOT_DIR BASELINE_TEST_FILE

SNAPSHOT_DIR is the receiver's checkout after the session (or a control
checkout). BASELINE_TEST_FILE is the immutable copy of test_mycelium.py at
198f9e2 (its digest is pinned in the package) used for H7; it is copied into
the snapshot under a private name and removed afterwards.

H1-H6 are executed in a child interpreter whose cwd and sys.path[0] are the
snapshot, so the snapshot's own mycelium.py is imported (never the host
checkout). Any exception inside a check is recorded as that check failing;
the grader never raises on receiver-side API changes. The replay contract of
the plan is verify(replay_counterexample=True); the authenticity-only mode is
not graded.

Output: one JSON object on stdout with per-check pass/fail/detail and the
plan's ordered outcome classification (PASS / FAIL / PARTIAL). INVALID is an
environment decision made by the launcher, not by this grader.
"""
import json, os, shutil, subprocess, sys, tempfile

CHILD = r'''
import json, sys, traceback
sys.path.insert(0, ".")
out = {}
def rec(name, fn):
    try:
        ok, detail = fn()
        out[name] = {"pass": bool(ok), "detail": detail}
    except Exception as e:
        out[name] = {"pass": False, "detail": "exception: " + traceback.format_exc().strip().splitlines()[-1]}
try:
    from glyph import parse, evaluate, App
    import mycelium
    from mycelium import DivergenceRecord, EpistemicRegistry
    from crypto import generate_keypair
    try:
        from mycelium import (LocalImmuneEvaluator, create_genesis_organism, Chromosome,
                              MetamorphicTransitionReceipt, FrozenEvaluator, export_warrant_from_receipt)
    except ImportError:
        from mycelium import LocalImmuneEvaluator, export_warrant_from_receipt
        from metamorphosis import (create_genesis_organism, Chromosome,
                                   MetamorphicTransitionReceipt, FrozenEvaluator)
except Exception:
    print(json.dumps({"import_error": traceback.format_exc().strip().splitlines()[-1]}))
    sys.exit(0)

OMEGA = "🌿 🤍 🤍 (🌿 🤍 🤍)"
BUDGET = 2000

def record(target, cand, inp):
    sk, pk = generate_keypair()
    if inp == "<UNAPPLIED_METABOLISM>":
        o = evaluate(parse(target), max_atp=BUDGET); c = evaluate(parse(cand), max_atp=BUDGET)
    else:
        o = evaluate(App(parse(target), parse(inp)), max_atp=BUDGET)
        c = evaluate(App(parse(cand), parse(inp)), max_atp=BUDGET)
    d = DivergenceRecord.create_and_sign(rule_name="MUTATION_CALIB", target_expr=target, cand_expr=cand,
                                         counterexample_input=inp, expected_out=str(o.term),
                                         actual_out=str(c.term), reporter_sk=sk)
    return d, o, c

def refused(target, cand, inp):
    d, o, c = record(target, cand, inp)
    v = d.verify(replay_counterexample=True)
    reg = EpistemicRegistry()
    acc = reg.add_divergence(d, verify_first=True)
    known = reg.has_known_divergence("MUTATION_CALIB", target, cand)
    ok = (v is False) and (acc is False) and (known is False)
    return ok, {"orig": o.status.value, "cand": c.status.value, "verify": v, "accepted": acc, "known": known}

def both_dirs(a, b, inp):
    r1, d1 = refused(a, b, inp); r2, d2 = refused(b, a, inp)
    return r1 and r2, {"fwd": d1, "rev": d2}

rec("H1", lambda: refused("🔁 f", "f (🔁 f)", "x"))
rec("H2", lambda: refused("🤍 (" + OMEGA + ")", OMEGA, "<UNAPPLIED_METABOLISM>"))
rec("H3", lambda: both_dirs("🖤", "🖤 (" + OMEGA + ")", "x"))
rec("H4", lambda: both_dirs("🖤 x", "🖤 (" + OMEGA + ") x", "<UNAPPLIED_METABOLISM>"))

def h5():
    d, o, c = record("🖤", "🤍", "🤍")
    v = d.verify(replay_counterexample=True)
    reg = EpistemicRegistry(); acc = reg.add_divergence(d, verify_first=True)
    known = reg.has_known_divergence("MUTATION_CALIB", "🖤", "🤍")
    return (v is True and acc is True and known is True), {"orig": o.status.value, "cand": c.status.value, "verify": v, "accepted": acc, "known": known}
rec("H5", h5)

def h6():
    pre = "🖤 x (" + OMEGA + ")"; post = OMEGA + " (🖤 x)"
    p = create_genesis_organism(); p.chromosomes = [Chromosome("G", "gene", pre, pre, 100)]
    p.organism_hash = p.compute_hash()
    r = MetamorphicTransitionReceipt(parent_hash="0"*64, successor_hash="1"*64, gene_id="G", site_address=(),
                                     rule_name="MUTATION_OPERAND_SWAP", pre_term=pre, post_term=post,
                                     atp_saved=-1, size_saved=0, fixtures_fingerprint=FrozenEvaluator().fixtures_fingerprint,
                                     experiment_id="calib")
    sk_b, _ = generate_keypair(); sk_a, _ = generate_keypair()
    w = export_warrant_from_receipt(r, sk_b)
    v = LocalImmuneEvaluator().audition_warrant(p, w, sk_a)
    rec_none = getattr(v, "divergence_record", "MISSING") is None
    return (not v.adopted) and rec_none, {"adopted": v.adopted, "reason": getattr(v, "reason", None), "divergence_record_is_none": rec_none}
rec("H6", h6)
print(json.dumps(out, ensure_ascii=False))
'''

def main(snapshot, baseline):
    snapshot = os.path.abspath(snapshot); result = {"snapshot": snapshot, "checks": {}}
    env = {k: v for k, v in os.environ.items() if k in ("HOME", "PATH", "LANG", "LC_ALL")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    child = subprocess.run([sys.executable, "-I", "-c", CHILD], cwd=snapshot, env=env,
                           capture_output=True, text=True, timeout=600)
    try:
        parsed = json.loads(child.stdout.strip().splitlines()[-1]) if child.stdout.strip() else {}
    except ValueError:
        parsed = {}
    if "import_error" in parsed or not parsed:
        for h in ("H1", "H2", "H3", "H4", "H5", "H6"):
            result["checks"][h] = {"pass": False, "detail": parsed.get("import_error", "grader child produced no result")}
        result["child_stderr_tail"] = child.stderr[-2000:]
    else:
        result["checks"].update(parsed)
    # H7: immutable baseline regression file at 198f9e2, run inside the snapshot
    private = os.path.join(snapshot, "_calib_h7_baseline_test.py")
    shutil.copyfile(baseline, private)
    try:
        # -I keeps the host site/env out; the snapshot itself is added explicitly.
        h7 = ("import sys, unittest; sys.path.insert(0, '.'); "
              "r = unittest.main(module='_calib_h7_baseline_test', argv=['x'], exit=False).result; "
              "sys.exit(0 if r.wasSuccessful() else 1)")
        t = subprocess.run([sys.executable, "-I", "-c", h7], cwd=snapshot,
                           env=env, capture_output=True, text=True, timeout=900)
        tail = "\n".join(t.stderr.strip().splitlines()[-3:])
        result["checks"]["H7"] = {"pass": t.returncode == 0 and "OK" in tail, "detail": tail}
    finally:
        os.remove(private)
        pc = os.path.join(snapshot, "__pycache__")
        for f in os.listdir(pc) if os.path.isdir(pc) else []:
            if f.startswith("_calib_h7_baseline_test"):
                os.remove(os.path.join(pc, f))
    c = result["checks"]
    core = [c[h]["pass"] for h in ("H1", "H2", "H3", "H4")]
    if all(c[h]["pass"] for h in ("H1", "H2", "H3", "H4", "H5", "H6", "H7")):
        outcome = "PASS"
    elif (not c["H5"]["pass"]) or (not c["H7"]["pass"]) or not any(core):
        outcome = "FAIL"
    else:
        outcome = "PARTIAL"
    result["outcome"] = outcome
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
