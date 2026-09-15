"""Hidden host grader for CALIB-MYC-1 (PLAN.md, H1-H7).

Run by the HOST, never inside the receiver session:

    python3 grade_checks.py SNAPSHOT_DIR BASELINE_TEST_FILE

SNAPSHOT_DIR is the receiver's checkout after the session (or a control
checkout). BASELINE_TEST_FILE is the immutable copy of test_mycelium.py at
198f9e2 (its digest is pinned in the package) used for H7; it is copied into
the snapshot under a private name and removed afterwards.

H1-H6 are executed in child interpreters whose cwd and sys.path[0] are the
snapshot, so the snapshot's own mycelium.py is imported (never the host
checkout): first an import probe, then one child per check, each with its own
deadline. Any exception inside a check is recorded as that check failing, and
a submission that hangs (at import, inside a check, or in the H7 baseline run)
is recorded as the corresponding checks failing with a "timed out" detail —
never as a grader error. The grader never raises on receiver-side behaviour;
INVALID stays an environment decision of the launcher. Deadlines:
CALIB_GRADER_CHECK_TIMEOUT (default 120 s, import probe and each of H1-H6)
and CALIB_GRADER_H7_TIMEOUT (default 600 s); the sum stays below the
launcher's 1800 s grader budget. The replay contract of the plan is
verify(replay_counterexample=True); the authenticity-only mode is not graded.

Output: one JSON object on stdout with per-check pass/fail/detail and the
plan's ordered outcome classification (PASS / FAIL / PARTIAL). INVALID is an
environment decision made by the launcher, not by this grader.
"""
import json, os, shutil, signal, subprocess, sys

CHECK_TIMEOUT = int(os.environ.get("CALIB_GRADER_CHECK_TIMEOUT", "120"))
H7_TIMEOUT = int(os.environ.get("CALIB_GRADER_H7_TIMEOUT", "600"))
CHECKS = ("H1", "H2", "H3", "H4", "H5", "H6")

CHILD = r'''
import json, sys, traceback
sys.path.insert(0, ".")
SELECT = sys.argv[1] if len(sys.argv) > 1 else "ALL"
out = {}
def rec(name, fn):
    if SELECT not in ("ALL", name):
        return
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
if SELECT == "IMPORT":
    print(json.dumps({"imported": True}))
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

def bounded(argv, cwd, env, timeout):
    """Run in its own session; on deadline kill the whole group. Never raises TimeoutExpired."""
    proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
        return proc.returncode, out.decode("utf-8", "replace"), err.decode("utf-8", "replace"), False
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        out, err = proc.communicate()
        return None, out.decode("utf-8", "replace"), err.decode("utf-8", "replace"), True


def last_json(text):
    for line in reversed(text.strip().splitlines()):
        try:
            return json.loads(line)
        except ValueError:
            continue
    return {}


def main(snapshot, baseline):
    snapshot = os.path.abspath(snapshot); result = {"snapshot": snapshot, "checks": {}, "timeouts": {"check": CHECK_TIMEOUT, "h7": H7_TIMEOUT}}
    env = {k: v for k, v in os.environ.items() if k in ("HOME", "PATH", "LANG", "LC_ALL")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # Import probe: a submission that hangs or fails at import fails H1-H6 once.
    code, out, err, timed_out = bounded([sys.executable, "-I", "-c", CHILD, "IMPORT"], snapshot, env, CHECK_TIMEOUT)
    probe = last_json(out)
    if timed_out:
        for h in CHECKS:
            result["checks"][h] = {"pass": False, "detail": f"import of the snapshot timed out after {CHECK_TIMEOUT} s"}
    elif "import_error" in probe or not probe.get("imported"):
        for h in CHECKS:
            result["checks"][h] = {"pass": False, "detail": probe.get("import_error", "import probe produced no result")}
        result["child_stderr_tail"] = err[-2000:]
    else:
        for h in CHECKS:
            code, out, err, timed_out = bounded([sys.executable, "-I", "-c", CHILD, h], snapshot, env, CHECK_TIMEOUT)
            if timed_out:
                result["checks"][h] = {"pass": False, "detail": f"{h} timed out after {CHECK_TIMEOUT} s"}
                continue
            parsed = last_json(out)
            if h in parsed:
                result["checks"][h] = parsed[h]
            else:
                result["checks"][h] = {"pass": False, "detail": "check child produced no result: " + (parsed.get("import_error") or err[-300:].strip())}
    # H7: immutable baseline regression file at 198f9e2, run inside the snapshot
    private = os.path.join(snapshot, "_calib_h7_baseline_test.py")
    shutil.copyfile(baseline, private)
    try:
        # -I keeps the host site/env out; the snapshot itself is added explicitly.
        h7 = ("import sys, unittest; sys.path.insert(0, '.'); "
              "r = unittest.main(module='_calib_h7_baseline_test', argv=['x'], exit=False).result; "
              "sys.exit(0 if r.wasSuccessful() else 1)")
        code, out, err, timed_out = bounded([sys.executable, "-I", "-c", h7], snapshot, env, H7_TIMEOUT)
        if timed_out:
            result["checks"]["H7"] = {"pass": False, "detail": f"baseline tests timed out after {H7_TIMEOUT} s"}
        else:
            tail = "\n".join(err.strip().splitlines()[-3:])
            result["checks"]["H7"] = {"pass": code == 0 and "OK" in tail, "detail": tail}
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
