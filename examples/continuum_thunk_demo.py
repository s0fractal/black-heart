#!/usr/bin/env python3
"""
continuum_thunk_demo.py — Compiles and demonstrates Resumable Continuum Polyglot PDFs.
Part of Project Black-Heart (%🖤).

Produces: examples/resumable_computation.pdf
  - Visual PDF displaying a vector ATP fuel gauge and execution progress.
  - Executable script: 'python3 examples/resumable_computation.pdf'
  - Incremental Resumption: 'python3 examples/resumable_computation.pdf --fuel 5000'
"""

import os
import sys

# Ensure parent directory is in path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from crypto import generate_keypair
from continuum import ResumableComputationPolyglot, resume_computation_in_pdf

def run_demo():
    print("\033[1;36m=================================================================\033[0m")
    print("  %🖤 CONTINUUM THUNK DEMONSTRATION: RESUMABLE COMPUTATION POLYGLOT")
    print("\033[1;36m=================================================================\033[0m\n")

    sk, pk = generate_keypair()
    out_pdf = os.path.join(ROOT, "examples", "resumable_computation.pdf")

    # A combinator expression that takes multiple reduction steps:
    # S (K (K I)) (K I) Alpha Beta -> Beta
    expr = "🌿 (🖤 (🖤 🤍)) (🖤 🤍) Alpha Beta"
    print(f"[*] Initial Combinator Problem:")
    print(f"    Expression: {expr}")
    print(f"    Prover PK:  {pk[:16]}...\n")

    # Step 1: Genesis with 2 ATP budget (suspends)
    poly = ResumableComputationPolyglot("AUTONOMOUS CONTINUUM REDUCTION")
    cp0 = poly.initialize(expr, initial_fuel=2, secret_key_hex=sk, public_key_hex=pk)
    print(f"[+] Step 1 (Genesis): Evaluated 2 ATP fuel.")
    print(f"    State: #{cp0.height} [{cp0.status}] -> {cp0.current_expr}")
    print(f"    Checkpoint Hash: ⚓ {cp0.checkpoint_hash[:16]}...")
    poly.compile(out_pdf)
    print(f"    [✓] Written initial polyglot to: {out_pdf}\n")

    # Step 2: Resume with 2 more ATP fuel (settles)
    print("[+] Step 2 (Incremental Resumption): Supplying 5 more ATP fuel...")
    cp1 = resume_computation_in_pdf(out_pdf, additional_atp=5, secret_key_hex=sk)
    print(f"    State: #{cp1.height} [{cp1.status}] -> Normal Form: '{cp1.current_expr}'")
    print(f"    Final Checkpoint Hash: ⚓ {cp1.checkpoint_hash}\n")

    print("\033[1;32m[✓] DEMO COMPLETE: Multi-Page Resumable Polyglot Settled!\033[0m")
    print(f"    Inspect visually: open {out_pdf}")
    print(f"    Audit via code:   python3 {out_pdf}\n")

if __name__ == "__main__":
    run_demo()
