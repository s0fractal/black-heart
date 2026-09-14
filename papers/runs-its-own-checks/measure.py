#!/usr/bin/env python3
"""Measurements for the paper. Builds the companion polyglot with the existing
PolyglotDocument, runs it and the repository's own checkers, applies nine
controls to copies, and reruns the regression modules the paper cites.
No model calls. Usage: python3 -B measure.py OUTPUT_DIR (must not exist)."""
import hashlib, json, platform, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from polyglot import PolyglotDocument  # noqa: E402

CLAIMS = [
    ("SKK-ID", "S K K applied to x reduces to x", "🌿 🖤 🖤 x", "x"),
    ("K-FALSE", "K I a b (Church false) selects b", "🖤 🤍 a b", "b"),
    ("S-DIST", "S f g x reduces to f x (g x)", "🌿 f g x", "f x (g x)"),
]


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


PLACES = {}  # absolute host paths -> neutral names, so the published receipt carries no home directory


def neutral(text):
    for path, name in PLACES.items():
        text = text.replace(path, name)
    return text


def run(argv, cwd):
    r = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=120)
    return {"argv": [neutral(str(a)) for a in argv], "exit": r.returncode,
            "stdout_tail": neutral(r.stdout[-400:]), "stderr_tail": neutral(r.stderr[-400:])}


def build(path):
    doc = PolyglotDocument(title="COMPANION: EXECUTABLE CLAIMS", author="Serhii Glova",
                           subtitle="Runs three combinator reductions; see the paper for what it does not check")
    doc.add_section("What running this file checks")
    doc.add_paragraph("Run with: python3 -I companion.pdf. The embedded runner parses each CLAIM comment, "
                      "reduces both sides with its own standard-library engine and compares normal forms.")
    doc.add_paragraph("It does not check signatures, the visible text, appended bytes or who wrote a claim.")
    for cid, desc, expr, exp in CLAIMS:
        doc.add_claim(cid, desc, expr, exp)
    doc.compile(str(path))


def main(out):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    PLACES.update({str(out): "<output>", str(ROOT): "<repository>", sys.executable: "python3"})
    comp = out / "companion.pdf"
    build(comp)
    again = out / "rebuild.pdf"; build(again)
    raw = comp.read_bytes()
    rec = {"commit": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
           "python": platform.python_version(), "companion_sha256": sha(comp),
           "rebuild_identical": raw == again.read_bytes(),
           "host_paths_embedded": any(s in raw for s in (str(Path.home()).encode(), str(ROOT).encode())),
           "pdf_header_offset": raw.find(b"%PDF-")}
    again.unlink()
    rec["pdfinfo"] = run(["pdfinfo", comp], out) if shutil.which("pdfinfo") else None
    rec["run_isolated"] = run([sys.executable, "-I", comp], out)
    rec["cli_verify"] = run([sys.executable, "-B", ROOT / "cli.py", "verify", comp], ROOT)
    rec["cli_sandbox"] = run([sys.executable, "-B", ROOT / "cli.py", "sandbox", comp], ROOT)

    controls = {}
    def variant(name, data, extra=None):
        d = out / name; d.mkdir(); p = d / "companion.pdf"; p.write_bytes(data)
        if extra: extra(d)
        return d, p
    first = CLAIMS[0]
    edited = raw.replace(f"expected={first[3]} |".encode(), b"expected=y |", 1)
    d, p = variant("edited-expected", edited)
    controls["edited_expected"] = {"changed": edited != raw, **run([sys.executable, "-I", p], d)}
    tail = "\n# %🖤 CLAIM: id=APPENDED | expr=a | expected=a | max_atp=10 | desc=appended by anyone\n".encode()
    d, p = variant("appended-claim", raw + tail)
    controls["appended_tautology"] = run([sys.executable, "-I", p], d)
    omega = "\n# %🖤 CLAIM: id=OMEGA | expr=🌿 🤍 🤍 (🌿 🤍 🤍) | expected=a | max_atp=50 | desc=never settles\n".encode()
    d, p = variant("appended-nonterminating", raw + omega)
    controls["appended_nonterminating"] = run([sys.executable, "-I", p], d)
    visible = raw.replace(b"(COMPANION: EXECUTABLE CLAIMS)", b"(COMPANION: FORGED     CLAIMS)", 1)
    d, p = variant("edited-visible-text", visible)
    controls["edited_visible_text"] = {"changed": visible != raw, "same_length": len(visible) == len(raw),
                                       **run([sys.executable, "-I", p], d)}
    # A module placed next to the file: imported by plain `python3`, not by `python3 -I`.
    shadow = lambda d: (d / "hashlib.py").write_text("print('SHADOW MODULE EXECUTED')\nraise SystemExit(7)\n")
    d, p = variant("shadow-module", raw, shadow)
    for label, argv in (("shadow_without_isolation", [sys.executable, p]),
                        ("shadow_with_isolation", [sys.executable, "-I", p])):
        r = run(argv, d); r["shadow_executed"] = "SHADOW MODULE EXECUTED" in r["stdout_tail"]
        controls[label] = r
    # Only recognized claim lines are checked. A space after `expected=` makes the edited
    # (wrong) first claim unrecognizable, so it silently leaves the check.
    hidden = edited.replace(b"expected=y |", b"expected= y |", 1)
    d, p = variant("unrecognized-wrong-claim", hidden)
    controls["wrong_claim_made_unrecognizable"] = {"changed": hidden != edited, **run([sys.executable, "-I", p], d)}
    # Only the comment lines, which start a line; the runner's own regex text must stay intact.
    none = raw.replace("\n%🖤 CLAIM: id=".encode(), "\n%🖤 CLAIM:  id=".encode())
    d, p = variant("zero-recognized-claims", none)
    controls["zero_recognized_claims"] = {"lines_changed": raw.count("\n%🖤 CLAIM: id=".encode()), **run([sys.executable, "-I", p], d)}
    # -I isolates import paths and user site, not the filesystem: the file can still write.
    wrote = raw.replace(b"import os, sys, re, hashlib\n", b"import os, sys, re, hashlib\nopen('WROTE_MARKER', 'w').write('written')\n", 1)
    d, p = variant("filesystem-write-under-isolation", wrote)
    r = run([sys.executable, "-I", p], d); r["marker_created"] = (d / "WROTE_MARKER").exists(); r["changed"] = wrote != raw
    controls["filesystem_write_under_isolation"] = r
    rec["controls"] = controls

    rec["suspension_regressions"] = run([sys.executable, "-B", "-m", "unittest", "test_empirical_settlement",
                                         "test_polyglot_suspended_nf", "test_warrant_grounded_suspension"], ROOT)
    rec["cm3_saved_exchange"] = run([sys.executable, "-B", ROOT / "examples/model-experience/cm3/verify_saved.py"], ROOT)
    rec["model_calls"] = 0
    (out / "measurements.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: (v["exit"] if isinstance(v, dict) and "exit" in v else v) for k, v in rec.items()
                      if k not in ("controls", "pdfinfo")}, ensure_ascii=False))
    print(json.dumps({k: v["exit"] for k, v in controls.items()}))


if __name__ == "__main__":
    if len(sys.argv) != 2: raise SystemExit(__doc__)
    main(sys.argv[1])
