"""Grader negative controls C0-C5 for CALIB-MYC-1 (PLAN.md, revision 2).

Host-only. For each control: extract the pinned pre-repair revision into a
temporary directory, apply the control's byte-level modification to
mycelium.py, run grade_checks.py, and retain the grader output under
controls/<Cn>.json together with the applied diff. The package is not
acceptable unless every control yields its predicted outcome.

    python3 run_controls.py REPO OUT_DIR

REPO must contain commit 198f9e2 (pre-repair) and 4affbf5 (post-#82) as
objects; nothing is checked out in REPO itself.
"""
import hashlib, json, os, subprocess, sys, tempfile, difflib

PRE = "198f9e2b64934f2e67b01df9128d1e57c2079407"
POST82 = "4affbf5d7af69e024f269ffe23bd23b1f69201dc"
HERE = os.path.dirname(os.path.abspath(__file__))
GRADER = os.path.join(HERE, "grade_checks.py")
BASELINE = os.path.join(HERE, "..", "inputs", "test_mycelium.baseline-198f9e2.py")

G_UNAPPLIED = '''                    res_orig = evaluate(orig_t, max_atp=2000)
                    res_cand = evaluate(cand_t, max_atp=2000)
                    orig_nf = str(res_orig.term)
'''
G_APPLIED = '''                    res_orig = evaluate(app_orig, max_atp=2000)
                    res_cand = evaluate(app_cand, max_atp=2000)

                    orig_nf = str(res_orig.term)
'''
BOTH_U = G_UNAPPLIED.replace("                    orig_nf", "                    if not res_orig.is_settled() or not res_cand.is_settled():\n                        return False\n                    orig_nf")
BOTH_A = G_APPLIED.replace("\n                    orig_nf", "\n                    if not res_orig.is_settled() or not res_cand.is_settled():\n                        return False\n                    orig_nf")
ONE_U = G_UNAPPLIED.replace("                    orig_nf", "                    if not res_orig.is_settled():\n                        return False\n                    orig_nf")
ONE_A = G_APPLIED.replace("\n                    orig_nf", "\n                    if not res_orig.is_settled():\n                        return False\n                    orig_nf")

def sub1(s, old, new):
    assert s.count(old) == 1, (s.count(old), old[:50]); return s.replace(old, new)

def c0(src, post): return src
def c1(src, post):  # verify fixed in both branches, minting untouched
    return sub1(sub1(src, G_UNAPPLIED, BOTH_U), G_APPLIED, BOTH_A)
def c2(src, post):  # applied branch only
    return sub1(src, G_APPLIED, BOTH_A)
def c3(src, post):  # one-sided (original only) in both branches
    return sub1(sub1(src, G_UNAPPLIED, ONE_U), G_APPLIED, ONE_A)
def c4(src, post): return post  # full repair: mycelium.py at 4affbf5 (#82)
def c5(src, post):  # verify always False
    return sub1(src, '    def verify(self, replay_counterexample: bool = True) -> bool:\n        """Verifies signature, ID derivation, and optionally re-runs counterexample."""\n',
                '    def verify(self, replay_counterexample: bool = True) -> bool:\n        """Verifies signature, ID derivation, and optionally re-runs counterexample."""\n        return False\n')

# Predicted result of EVERY check per control, fixed before the runner is
# executed. The outcome label is derived from these by the plan's ordered
# rule and is checked too, but a control counts as predicted only when each
# of H1-H7 matches (review requirement: per-check expectations, not labels).
H = ("H1", "H2", "H3", "H4", "H5", "H6", "H7")
def expect(**kw): return {h: kw[h] for h in H}
CONTROLS = [("C0", "no change", c0, "FAIL",
             expect(H1=False, H2=False, H3=False, H4=False, H5=True, H6=False, H7=True)),
            ("C1", "verify fixed in both branches, minting untouched", c1, "PARTIAL",
             expect(H1=True, H2=True, H3=True, H4=True, H5=True, H6=False, H7=True)),
            ("C2", "applied branch only", c2, "PARTIAL",
             expect(H1=True, H2=False, H3=True, H4=False, H5=True, H6=False, H7=True)),
            ("C3", "one-sided settled check (original only) in both branches", c3, "PARTIAL",
             expect(H1=True, H2=True, H3=False, H4=False, H5=True, H6=False, H7=True)),
            ("C4", "full repair: mycelium.py from 4affbf5", c4, "PASS",
             expect(H1=True, H2=True, H3=True, H4=True, H5=True, H6=True, H7=True)),
            ("C5", "verify() returns False always", c5, "FAIL",
             expect(H1=True, H2=True, H3=True, H4=True, H5=False, H6=False, H7=False))]

def sha(b): return hashlib.sha256(b).hexdigest()

def main(repo, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    pre = subprocess.check_output(["git", "-C", repo, "show", f"{PRE}:mycelium.py"]).decode()
    post = subprocess.check_output(["git", "-C", repo, "show", f"{POST82}:mycelium.py"]).decode()
    summary = {"pre_revision": PRE, "pre_mycelium_sha256": sha(pre.encode()), "post82_revision": POST82,
               "post82_mycelium_sha256": sha(post.encode()), "grader_sha256": sha(open(GRADER, "rb").read()),
               "baseline_test_sha256": sha(open(BASELINE, "rb").read()), "controls": {}, "all_as_predicted": True}
    for name, desc, fn, predicted, expected_checks in CONTROLS:
        tmp = tempfile.mkdtemp(prefix=f"calib-{name}-")
        tar = subprocess.Popen(["git", "-C", repo, "archive", PRE], stdout=subprocess.PIPE)
        subprocess.check_call(["tar", "-x", "-C", tmp], stdin=tar.stdout); tar.wait()
        patched = fn(pre, post)
        open(os.path.join(tmp, "mycelium.py"), "w", encoding="utf-8").write(patched)
        diff = "".join(difflib.unified_diff(pre.splitlines(True), patched.splitlines(True), "a/mycelium.py", "b/mycelium.py"))
        out = subprocess.run([sys.executable, GRADER, tmp, BASELINE], capture_output=True, text=True, timeout=1500)
        try:
            graded = json.loads(out.stdout)
        except ValueError:
            graded = {"error": out.stdout[-500:] + out.stderr[-500:], "outcome": "GRADER_ERROR"}
        graded["control"] = name; graded["description"] = desc; graded["predicted"] = predicted
        graded["expected_checks"] = expected_checks
        observed = {h: graded.get("checks", {}).get(h, {}).get("pass") for h in H}
        graded["checks_as_predicted"] = {h: observed[h] is expected_checks[h] for h in H}
        graded["as_predicted"] = graded.get("outcome") == predicted and all(graded["checks_as_predicted"].values())
        graded["patched_mycelium_sha256"] = sha(patched.encode())
        graded.pop("snapshot", None)
        open(os.path.join(out_dir, f"{name}.json"), "w", encoding="utf-8").write(json.dumps(graded, ensure_ascii=False, indent=1) + "\n")
        open(os.path.join(out_dir, f"{name}.diff"), "w", encoding="utf-8").write(diff)
        summary["controls"][name] = {"description": desc, "predicted": predicted, "outcome": graded.get("outcome"),
                                     "expected_checks": expected_checks, "checks": observed,
                                     "checks_as_predicted": graded["checks_as_predicted"],
                                     "as_predicted": graded["as_predicted"]}
        summary["all_as_predicted"] &= graded["as_predicted"]
        mism = [h for h, ok in graded["checks_as_predicted"].items() if not ok]
        print(name, desc, "->", graded.get("outcome"), "(predicted", predicted + ")",
              "OK" if graded["as_predicted"] else "MISMATCH " + ",".join(mism))
    open(os.path.join(out_dir, "SUMMARY.json"), "w", encoding="utf-8").write(json.dumps(summary, ensure_ascii=False, indent=1) + "\n")
    return 0 if summary["all_as_predicted"] else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
