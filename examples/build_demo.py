#!/usr/bin/env python3
"""
build_demo.py — Compiles the showcase self-executing PDF polyglot into examples/
"""

import os
import sys

# Ensure black-heart root is in path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from polyglot import PolyglotDocument

def build_showcase():
    output_path = os.path.join(ROOT, "examples", "black_cone_proof.pdf")

    doc = PolyglotDocument(
        title="THE BLACK CONE: SELF-EXECUTING PROOF",
        subtitle="A Proof-Carrying Polyglot Demonstrating Combinator Settlement in PDF",
        author="s0fractal"
    )

    doc.add_section("1. The Principle of Settlement")
    doc.add_paragraph(
        "In a generative ecosystem, generation is asymptotically free. Without deterministic "
        "closure, obligations multiply unboundedly. The Black Cone enforces termination: "
        "every assertion must compile into a content-addressed normal form within an ATP quota."
    )

    doc.add_section("2. Mechanized Invariants on Glyphs")
    doc.add_paragraph(
        "Below are three embedded claims in the SKIY glyph calculus. This PDF file contains "
        "the executable proof of each claim within its own binary stream."
    )

    # Claims
    doc.add_claim(
        claim_id="C1-ABSORPTION",
        description="Black Cone K-combinator absorbs the speculative distractor",
        glyph_expr="🖤 GroundTruth Illusion",
        expected_normal_form="GroundTruth",
        max_atp=100
    )

    doc.add_claim(
        claim_id="C2-SPORE-ID",
        description="Spore distribution (S K K) normalizes to canonical Identity",
        glyph_expr="🌿 🖤 🖤 InvariantCarrier",
        expected_normal_form="InvariantCarrier",
        max_atp=200
    )

    doc.add_claim(
        claim_id="C3-BRANCHING",
        description="Church FALSE selects the bounded fallback branch",
        glyph_expr="(🖤 🤍) SpeculativeBranch VerifiableBranch",
        expected_normal_form="VerifiableBranch",
        max_atp=150
    )

    doc.compile(output_path)
    print(f"[+] Compiled showcase polyglot to: {output_path}")
    print(f"[+] File size: {os.path.getsize(output_path)} bytes")
    print(f"[+] Try viewing: open {output_path}")
    print(f"[+] Try running:  python3 {output_path}")

if __name__ == "__main__":
    build_showcase()
