#!/usr/bin/env python3
"""
zk_contract_demo.py — Compiles and executes a Confidential ZK Procurement Contract.
Part of Project Black-Heart (%🖤).

Produces: examples/confidential_procurement_contract.pdf
  - Viewable as an ISO 32000 PDF contract with a Zero-Knowledge Soundness seal.
  - Executable script: 'python3 examples/confidential_procurement_contract.pdf'
  - Proves supplier authorization and solvency in Zero Knowledge without revealing private keys.
"""

import os
import sys

# Ensure parent directory is in path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from crypto import generate_keypair
from zk_glyph import schnorr_prove, chaum_pedersen_prove, ZKProofPolyglot

def run_demo():
    print("\033[1;36m=================================================================\033[0m")
    print("  %🖤 ZERO-KNOWLEDGE PROCUREMENT CONTRACT DEMONSTRATION")
    print("\033[1;36m=================================================================\033[0m\n")

    # 1. Supplier generates private key (never shared)
    supplier_sk, supplier_pk = generate_keypair()
    print(f"[*] Supplier Sovereign Identity:")
    print(f"    Public Key: {supplier_pk}")
    print(f"    Secret Key: [CONCEALED / NEVER TRANSMITTED]\n")

    # 2. Supplier creates Schnorr NIZK proof of identity possession
    print("[+] Generating Schnorr Zero-Knowledge Proof of Authorization...")
    sp = schnorr_prove(supplier_sk, context="ENTERPRISE_PROCUREMENT_CLEARANCE_2026")
    print(f"    Commitment R: {sp.commitment_R_hex[:16]}...")
    print(f"    Response z:   {sp.response_z_hex[:16]}...\n")

    # 3. Supplier creates Chaum-Pedersen DLog equality proof of confidential escrow solvency
    print("[+] Generating Chaum-Pedersen Zero-Knowledge Proof of Solvency Commitment...")
    confidential_balance_scalar = 50_000_000 # $50M solvency commitment
    cpp = chaum_pedersen_prove(confidential_balance_scalar, context="SOLVENCY_RESERVE_PROOF")
    print(f"    Commitment R1: {cpp.commitment_R1_hex[:16]}...")
    print(f"    Commitment R2: {cpp.commitment_R2_hex[:16]}...\n")

    # 4. Compile into self-verifying ZK Polyglot PDF
    out_pdf = os.path.join(ROOT, "examples", "confidential_procurement_contract.pdf")
    poly = ZKProofPolyglot(
        title="CONFIDENTIAL ENTERPRISE PROCUREMENT AGREEMENT",
        author="s0fractal"
    )
    poly.add_schnorr_proof(sp)
    poly.add_chaum_pedersen_proof(cpp)
    poly.compile(out_pdf)

    print(f"\033[1;32m[✓] Compiled ZK Contract Polyglot: {out_pdf}\033[0m")
    print(f"    Inspect visually: open {out_pdf}")
    print(f"    Audit via code:   python3 {out_pdf}\n")

if __name__ == "__main__":
    run_demo()
