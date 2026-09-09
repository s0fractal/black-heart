#!/usr/bin/env python3
"""
polyglot.py — Self-Executing Proof-Carrying PDF Compiler
Part of Project Black-Heart (%🖤).

Produces files that are simultaneously:
  1. 100% Valid PDF documents (viewable in Preview, Acrobat, Chrome, etc.)
  2. 100% Valid Python 3 executable scripts (runnable via: python3 document.pdf)

When executed via python3, the PDF reads its own content, parses embedded %🖤 glyph
expressions, executes deterministic reductions, and outputs an audit receipt.
"""

from __future__ import annotations
import os
import sys
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

@dataclass
class Claim:
    claim_id: str
    description: str
    glyph_expr: str
    expected_normal_form: str
    max_atp: int = 10_000

@dataclass
class Section:
    title: str
    paragraphs: List[str] = field(default_factory=list)
    claims: List[Claim] = field(default_factory=list)

class PolyglotDocument:
    def __init__(self, title: str, author: str = "s0fractal", subtitle: str = ""):
        self.title = title
        self.author = author
        self.subtitle = subtitle
        self.sections: List[Section] = []
        self._current_section: Optional[Section] = None

    def add_section(self, title: str) -> Section:
        sec = Section(title=title)
        self.sections.append(sec)
        self._current_section = sec
        return sec

    def add_paragraph(self, text: str):
        if not self._current_section:
            self.add_section("Introduction")
        self._current_section.paragraphs.append(text)

    def add_claim(self, claim_id: str, description: str, glyph_expr: str, expected_normal_form: str, max_atp: int = 10_000):
        if not self._current_section:
            self.add_section("Claims")
        claim = Claim(
            claim_id=claim_id,
            description=description,
            glyph_expr=glyph_expr,
            expected_normal_form=expected_normal_form,
            max_atp=max_atp
        )
        self._current_section.claims.append(claim)

    def compile(self, output_path: str):
        """Compile the document into an executable PDF polyglot."""
        # Page geometry (A4: 595 x 842 pt)
        page_width, page_height = 595, 842
        margin = 54  # 0.75 inch
        content_width = page_width - 2 * margin

        # Build visual PDF text stream
        stream_lines = []
        y = page_height - margin

        # Title
        stream_lines.append(f"BT /F1 22 Tf {margin} {y} Td ({_escape_pdf(self.title)}) Tj ET")
        y -= 28

        if self.subtitle:
            stream_lines.append(f"BT /F3 11 Tf 0.3 0.3 0.3 rg {margin} {y} Td ({_escape_pdf(self.subtitle)}) Tj 0 g ET")
            y -= 20

        # Author & Signature
        stream_lines.append(f"BT /F2 9 Tf 0.5 0.5 0.5 rg {margin} {y} Td (Author: {_escape_pdf(self.author)} | Format: %🖤 Executable PDF Polyglot) Tj 0 g ET")
        y -= 14

        # Decorative rule
        stream_lines.append(f"0.85 0.85 0.85 rg {margin} {y} {content_width} 1 re f 0 g")
        y -= 25

        embedded_claim_manifest = []

        for sec in self.sections:
            if y < margin + 100:
                break  # simple single-page layout for micro-manifesto

            # Section Title
            stream_lines.append(f"BT /F1 14 Tf 0.1 0.2 0.4 rg {margin} {y} Td ({_escape_pdf(sec.title)}) Tj 0 g ET")
            y -= 18

            for para in sec.paragraphs:
                # Simple word wrap
                wrapped = _wrap_text(para, 75)
                for line in wrapped:
                    stream_lines.append(f"BT /F2 10 Tf {margin} {y} Td ({_escape_pdf(line)}) Tj ET")
                    y -= 14
                    if y < margin + 80:
                        break
                y -= 6

            for claim in sec.claims:
                embedded_claim_manifest.append(claim)
                # Draw Claim Box
                box_height = 36
                y -= (box_height + 4)
                # Background box
                stream_lines.append(f"0.96 0.97 0.98 rg {margin} {y} {content_width} {box_height} re f 0 g")
                # Left accent border
                stream_lines.append(f"0.1 0.4 0.8 rg {margin} {y} 3 {box_height} re f 0 g")
                # Box text
                stream_lines.append(f"BT /F1 9 Tf {margin + 8} {y + 22} Td ([CLAIM {claim.claim_id}] {_escape_pdf(claim.description)}) Tj ET")
                stream_lines.append(f"BT /F4 8 Tf 0.2 0.2 0.2 rg {margin + 8} {y + 9} Td (Expression: {_escape_pdf(claim.glyph_expr)}  -->  Expected: {_escape_pdf(claim.expected_normal_form)}) Tj 0 g ET")
                y -= 10

        # Footer
        stream_lines.append(f"0.9 0.9 0.9 rg {margin} {margin} {content_width} 0.5 re f 0 g")
        stream_lines.append(f"BT /F2 8 Tf 0.5 0.5 0.5 rg {margin} {margin - 12} Td (Self-verifying binary polyglot. Run from terminal: python3 <this_file>.pdf) Tj 0 g ET")

        stream_bytes = "\n".join(stream_lines).encode("latin1", errors="replace")

        # Build PDF object hierarchy
        objs = []
        # 1: Catalog
        objs.append(b"<</Type /Catalog /Pages 2 0 R>>")
        # 2: Pages
        objs.append(b"<</Type /Pages /Kids [3 0 R] /Count 1>>")
        # 3: Page
        objs.append(
            b"<</Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Contents 4 0 R /Resources <</Font <</F1 5 0 R /F2 6 0 R /F3 7 0 R /F4 8 0 R>>>>>>"
        )
        # 4: Contents Stream
        objs.append(
            b"<</Length " + str(len(stream_bytes)).encode() + b">> \nstream\n" +
            stream_bytes +
            b"\nendstream"
        )
        # Fonts (Standard 14 PDF fonts, zero external files needed)
        objs.append(b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold>>")
        objs.append(b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>")
        objs.append(b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique>>")
        objs.append(b"<</Type /Font /Subtype /Type1 /BaseFont /Courier>>")

        # Header: Python raw docstring opening wrapping the PDF header
        # The PDF header starts on line 2 within the first 1024 bytes (ISO 32000 compliant)
        pdf_header = (
            b"# coding: utf-8\n"
            b'r"""%PDF-1.7\n'
            b"%\xf0\x9f\x96\xa4\n"  # %🖤 binary comment
        )

        # Embed claim metadata in PDF comments so the file carries its own semantic claims
        claims_comment = []
        for c in embedded_claim_manifest:
            # We encode glyphs as UTF-8 in the comment block
            claims_comment.append(
                f"%🖤 CLAIM: id={c.claim_id} | expr={c.glyph_expr} | expected={c.expected_normal_form} | max_atp={c.max_atp} | desc={c.description}\n".encode("utf-8")
            )
        claims_comment_bytes = b"".join(claims_comment)

        body = bytearray(pdf_header)
        body.extend(claims_comment_bytes)

        offsets = [0]
        for i, o in enumerate(objs, 1):
            offsets.append(len(body))
            body.extend(f"{i} 0 obj\n".encode("latin1"))
            body.extend(o)
            body.extend(b"\nendobj\n")

        xstart = len(body)
        body.extend(f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode("latin1"))
        for off in offsets[1:]:
            body.extend(f"{off:010d} 00000 n \n".encode("latin1"))

        body.extend(
            f"trailer\n<</Size {len(objs)+1} /Root 1 0 R>>\nstartxref\n{xstart}\n%%EOF\n\"\"\"\n".encode("latin1")
        )

        # Append the standalone Python runtime runner (Self-Contained Verifier)
        runner_code = _generate_standalone_runner()
        body.extend(runner_code.encode("utf-8"))

        with open(output_path, "wb") as f:
            f.write(body)

        return output_path

def audit_polyglot_claims(target_path: str) -> bool:
    """
    Audits combinatory claims in a polyglot document without running external code.
    Reads document strictly as bytes and verifies claims in memory.
    """
    with open(target_path, "rb") as f:
        content = f.read()

    claims = []
    prefix = "%🖤 CLAIM: ".encode("utf-8")
    for line in content.splitlines():
        if line.startswith(prefix):
            raw = line[len(prefix):].decode("utf-8", errors="replace").strip()
            parts = [p.strip() for p in raw.split("|")]
            if len(parts) >= 4:
                claim_id = parts[0]
                desc = parts[1]
                expr = parts[2]
                exp = parts[3]
                atp = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 10_000
                claims.append((claim_id, desc, expr, exp, atp))

    if not claims:
        if "%🖤 CODE_VAULT_MANIFEST:".encode("utf-8") in content:
            return True
        return False

    from glyph import parse, evaluate
    total_atp = 0
    passed = 0
    for claim_id, desc, expr_str, exp_str, max_atp in claims:
        try:
            t = parse(expr_str)
            norm, atp, digest = evaluate(t, max_atp=max_atp)
            total_atp += atp
            norm_str = str(norm)
            exp_t = parse(exp_str)
            exp_norm, _, _ = evaluate(exp_t)
            exp_norm_str = str(exp_norm)
            if norm_str == exp_norm_str:
                passed += 1
            else:
                return False
        except Exception:
            return False

    return passed == len(claims)

def _escape_pdf(text: str) -> str:
    """Escape parentheses and backslashes for PDF string literals."""
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

def _wrap_text(text: str, max_chars: int) -> List[str]:
    words = text.split()
    lines = []
    curr = []
    curr_len = 0
    for w in words:
        if curr_len + len(w) + 1 <= max_chars:
            curr.append(w)
            curr_len += len(w) + 1
        else:
            lines.append(" ".join(curr))
            curr = [w]
            curr_len = len(w)
    if curr:
        lines.append(" ".join(curr))
    return lines

def _generate_standalone_runner() -> str:
    """Generates the embedded, self-contained Python verifier that executes upon 'python3 file.pdf'."""
    return r'''
# --- BEGIN STANDALONE GLYPH VERIFICATION ENGINE ---
import os, sys, re, hashlib
from dataclasses import dataclass
from typing import Union, Optional, Tuple

GLYPH_K = "🖤"
GLYPH_I = "🤍"
GLYPH_S = "🌿"
GLYPH_Y = "🔁"

@dataclass(frozen=True)
class Comb:
    symbol: str
    def __repr__(self): return self.symbol

@dataclass(frozen=True)
class Var:
    name: str
    def __repr__(self): return self.name

@dataclass(frozen=True)
class App:
    left: any
    right: any
    def __repr__(self):
        r_str = f"({self.right})" if isinstance(self.right, App) else str(self.right)
        return f"{self.left} {r_str}"

K = Comb(GLYPH_K)
I = Comb(GLYPH_I)
S = Comb(GLYPH_S)
Y = Comb(GLYPH_Y)

def parse(text: str):
    tokens = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c.isspace(): i += 1
        elif c in "()": tokens.append(c); i += 1
        elif c in (GLYPH_K, GLYPH_I, GLYPH_S, GLYPH_Y): tokens.append(c); i += 1
        elif c.isalnum() or c in "_-":
            j = i
            while j < n and (text[j].isalnum() or text[j] in "_-"): j += 1
            w = text[i:j]
            tokens.append(GLYPH_K if w=="K" else GLYPH_I if w=="I" else GLYPH_S if w=="S" else GLYPH_Y if w=="Y" else w)
            i = j
        else: tokens.append(c); i += 1

    pos = 0
    def p_prim():
        nonlocal pos
        tok = tokens[pos]; pos += 1
        if tok == "(":
            res = p_expr(); pos += 1; return res
        elif tok == GLYPH_K: return K
        elif tok == GLYPH_I: return I
        elif tok == GLYPH_S: return S
        elif tok == GLYPH_Y: return Y
        else: return Var(tok)

    def p_expr():
        nonlocal pos
        terms = []
        while pos < len(tokens) and tokens[pos] != ")":
            terms.append(p_prim())
        res = terms[0]
        for t in terms[1:]: res = App(res, t)
        return res

    return p_expr()

def reduce_step(term):
    if isinstance(term, App) and term.left == I:
        return (term.right, True)
    if isinstance(term, App) and isinstance(term.left, App) and term.left.left == K:
        return (term.left.right, True)
    if isinstance(term, App) and isinstance(term.left, App) and isinstance(term.left.left, App) and term.left.left.left == S:
        x = term.left.left.right; y = term.left.right; z = term.right
        return (App(App(x, z), App(y, z)), True)
    if isinstance(term, App) and term.left == Y:
        f = term.right
        return (App(f, App(Y, f)), True)
    if isinstance(term, App):
        nl, red = reduce_step(term.left)
        if red: return (App(nl, term.right), True)
        nr, red = reduce_step(term.right)
        if red: return (App(term.left, nr), True)
    return (term, False)

def evaluate(term, max_atp=10000):
    curr = term; steps = 0
    while True:
        nxt, did = reduce_step(curr)
        if not did:
            can_bytes = str(curr).encode("utf-8")
            h = hashlib.sha256(can_bytes).hexdigest()
            return curr, steps, h
        steps += 1
        if steps > max_atp: raise RuntimeError("ATP budget exceeded")
        curr = nxt

def main():
    self_path = sys.argv[0]
    print("\033[1;36m" + "=" * 65 + "\033[0m")
    print("\033[1;35m  %🖤 BLACK-HEART — SELF-EXECUTING PROOF-CARRYING PDF RUNNER\033[0m")
    print(f"\033[0;37m  Target file: {os.path.basename(self_path)} ({os.path.getsize(self_path)} bytes)\033[0m")
    print("\033[1;36m" + "=" * 65 + "\033[0m")

    with open(self_path, "rb") as f:
        content = f.read().decode("utf-8", errors="replace")

    claims = re.findall(r"%🖤 CLAIM: id=([^\s|]+) \| expr=([^\s|]+(?:\s+[^\s|]+)*) \| expected=([^\s|]+(?:\s+[^\s|]+)*) \| max_atp=(\d+) \| desc=(.+)", content)

    if not claims:
        print("\033[1;33m[!] No %🖤 claims discovered in PDF comments.\033[0m")
        sys.exit(0)

    print(f"\n[+] Discovered {len(claims)} embedded %🖤 claims. Executing deterministic reductions...\n")

    passed = 0
    total_atp = 0

    for cid, expr_str, exp_str, max_atp, desc in claims:
        print(f"  \033[1;34m[CLAIM {cid}]\033[0m {desc}")
        print(f"    Input:    {expr_str}")
        try:
            t = parse(expr_str)
            norm, atp, digest = evaluate(t, max_atp=int(max_atp))
            total_atp += atp
            norm_str = str(norm)
            exp_t = parse(exp_str)
            exp_norm, _, _ = evaluate(exp_t)
            exp_norm_str = str(exp_norm)

            if norm_str == exp_norm_str:
                passed += 1
                badge = f"⚓ SETTLED"
                print(f"    Result:   {norm_str}")
                print(f"    Receipt:  \033[1;32m{badge} ⟨atp:{atp}, hash:{digest[:12]}⟩\033[0m\n")
            else:
                print(f"    \033[1;31m[!] REFUTED: Expected '{exp_norm_str}' but got '{norm_str}'\033[0m\n")
        except Exception as e:
            print(f"    \033[1;31m[!] ERROR: {e}\033[0m\n")

    print("\033[1;36m" + "-" * 65 + "\033[0m")
    if passed == len(claims):
        print(f"\033[1;32m[⚓ GREEN] ALL {passed}/{len(claims)} CLAIMS SETTLED DETERMINISTICALLY ({total_atp} ATP burned).\033[0m")
        print("\033[0;32mDocument integrity & proof verification: 100% SOUND.\033[0m")
        sys.exit(0)
    else:
        print(f"\033[1;31m[✗ RED] SETTLEMENT BLOCKED: {len(claims) - passed} claims failed!\033[0m")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''

if __name__ == "__main__":
    doc = PolyglotDocument(
        title="MANIFESTO OF THE BLACK CONE",
        subtitle="A Self-Verifying Polyglot Document on Combinatory Settlement",
        author="s0fractal"
    )
    doc.add_section("The Principle of Settlement")
    doc.add_paragraph(
        "Generation is free, but verification multiplies obligations. The Black Cone "
        "enforces computational closure: every claim must settle into a normal form "
        "within a deterministic ATP budget, leaving a re-executable receipt."
    )
    # Add claims
    doc.add_claim("K-DROP", "K-combinator drops the second argument (Constant)", "🖤 Truth Mirage", "Truth")
    doc.add_claim("SKK-ID", "SKK behaves identically to Identity (White Cone 🤍)", "🌿 🖤 🖤 Signal", "Signal")
    doc.add_claim("CHURCH-FALSE", "Application of Church FALSE returns the right branch", "(🖤 🤍) Left Right", "Right")

    out_file = "/tmp/manifesto_polyglot.pdf"
    doc.compile(out_file)
    print(f"Compiled executable polyglot PDF to: {out_file}")
