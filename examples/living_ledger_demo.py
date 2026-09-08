#!/usr/bin/env python3
"""
living_ledger_demo.py — Compiles and demonstrates a multi-block Living Polyglot Ledger.
Part of Project Black-Heart (%🖤).

Produces: examples/living_ledger.pdf
- Viewable as a multi-page PDF document with vector proof net diagrams.
- Executable via 'python3 examples/living_ledger.pdf' to verify the Ed25519 signatures
  and Merkle hash chain across all blocks.
"""

import os
import sys

# Ensure parent directory is in path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from crypto import generate_keypair
from living_ledger import LivingLedger

def run_demo():
    print("\033[1;36m[*] Initializing Living Polyglot Ledger Demonstration...\033[0m")

    # 1. Generate Ed25519 Keypairs for network participants
    alice_sk, alice_pk = generate_keypair()
    bob_sk, bob_pk = generate_keypair()
    print(f"    - Alice [Originator] Public Key: {alice_pk[:16]}...")
    print(f"    - Bob   [Arbiter]    Public Key: {bob_pk[:16]}...")

    ledger = LivingLedger(title="BLACK-HEART AUTONOMOUS LIVING LEDGER")

    # 2. Block #0000: Genesis Block
    print("\n[*] Minting Block #0000 (GENESIS)...")
    ledger.create_genesis(
        signer_name="Alice (Sovereign Node)",
        signer_role="ORIGINATOR",
        secret_key_hex=alice_sk,
        description="Genesis activation: Binding combinator closure to physical PDF stream.",
        combinator_claim={
            "expr": "🌿 🖤 🖤 GenesisInvariant",
            "expected": "GenesisInvariant",
            "atp": 2
        }
    )

    # 3. Block #0001: Escrow Allocation
    print("[*] Minting Block #0001 (ESCROW_DEPOSIT)...")
    ledger.append_block(
        signer_name="Bob (Settlement Arbiter)",
        signer_role="ARBITER",
        secret_key_hex=bob_sk,
        action_type="ESCROW_DEPOSIT",
        description="Escrow committed: 10,000 ATP locked for SLA guarantee.",
        combinator_claim={
            "expr": "🖤 EscrowSound SpeculativeRisk",
            "expected": "EscrowSound",
            "atp": 1
        }
    )

    # 4. Block #0002: Autonomous Adjudication
    print("[*] Minting Block #0002 (SETTLEMENT_RELEASE)...")
    ledger.append_block(
        signer_name="Alice (Sovereign Node)",
        signer_role="ORIGINATOR",
        secret_key_hex=alice_sk,
        action_type="SETTLEMENT_RELEASE",
        description="Settlement adjudicated: Uptime verified 99.306%, releasing net payout.",
        combinator_claim={
            "expr": "(🖤 🤍) RefuseBranch SettleBranch",
            "expected": "SettleBranch",
            "atp": 2
        }
    )

    # 5. Compile to executable PDF
    out_pdf = os.path.join(ROOT, "examples", "living_ledger.pdf")
    ledger.compile(out_pdf)

    print(f"\n\033[1;32m[✓] Compiled Living Polyglot Ledger to: {out_pdf}\033[0m")
    print(f"    File Size: {os.path.getsize(out_pdf)} bytes across {len(ledger.blocks)} pages.")
    print(f"    Visual Form:     open {out_pdf}")
    print(f"    Executable Form: python3 {out_pdf}\n")

if __name__ == "__main__":
    run_demo()
