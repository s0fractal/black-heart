#!/usr/bin/env python3
"""
bilateral_settlement_demo.py — Demonstrates bilateral cross-document adjudication.
Part of Project Black-Heart (%🖤).

Produces:
  1. examples/provider_telemetry_oracle.pdf (Signed telemetry report by Cloudflare/Datadog)
  2. examples/bilateral_agreement.pdf (Client SLA agreement referencing Oracle PK)
And runs mutual cryptographic adjudication!
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from crypto import generate_keypair
from cross_proof import (
    TelemetryOraclePolyglot,
    BilateralAgreementPolyglot,
    adjudicate_bilateral
)

def run_demo():
    print("\033[1;36m[*] Initializing Bilateral Interlocking Document Protocol...\033[0m")

    # 1. Oracle Keypair (Independent Observability Node)
    oracle_sk, oracle_pk = generate_keypair()
    print(f"    - Independent Oracle Public Key: {oracle_pk[:16]}...")

    # 2. Client & Provider Keys
    client_sk, client_pk = generate_keypair()
    provider_sk, provider_pk = generate_keypair()

    output_dir = os.path.join(ROOT, "examples")
    oracle_pdf = os.path.join(output_dir, "provider_telemetry_oracle.pdf")
    agreement_pdf = os.path.join(output_dir, "bilateral_agreement.pdf")

    # 3. Compile Document B: Independent Oracle Telemetry Polyglot
    print("\n[*] Compiling Document B: Telemetry Oracle Polyglot...")
    oracle = TelemetryOraclePolyglot(oracle_name="Cloudflare Global Observability Network")
    oracle.add_incident("INC-01", "2026-09-02T04:15:00Z", "Edge Transit Flapping", 180)
    oracle.add_incident("INC-02", "2026-09-05T11:30:00Z", "Storage Consensus Partition", 120)
    oracle.compile(oracle_pdf, oracle_secret_key_hex=oracle_sk)
    print(f"    [✓] Created Oracle Certificate: {oracle_pdf}")

    # 4. Compile Document A: Bilateral SLA Agreement referencing Oracle PK
    print("\n[*] Compiling Document A: Bilateral SLA Agreement...")
    agreement = BilateralAgreementPolyglot(
        title="ENTERPRISE CLOUD INFRASTRUCTURE SLA & ESCROW AGREEMENT",
        trusted_oracle_pk_hex=oracle_pk,
        target_uptime_percent=99.5,
        base_fee_usd=10000,
        penalty_rate_usd=500
    )
    agreement.add_party("CLIENT", "Axiom Financial Technologies Inc.", client_pk, secret_key_hex=client_sk)
    agreement.add_party("PROVIDER", "Nebula Hypercloud Infrastructure Ltd.", provider_pk, secret_key_hex=provider_sk)
    agreement.compile(agreement_pdf)
    print(f"    [✓] Created Bilateral Agreement: {agreement_pdf}")

    # 5. Execute Bilateral Adjudication
    print("\n\033[1;33m[*] ADJUDICATING BILATERAL CONTRACT AGAINST ATTESTED TELEMETRY...\033[0m")
    receipt = adjudicate_bilateral(agreement_pdf, oracle_pdf)

    print("\033[1;32m[⚓ SETTLEMENT COMPLETED BILATERALLY]\033[0m")
    print(f"    - Agreement:         {receipt.agreement_title}")
    print(f"    - Attested Oracle:   {receipt.oracle_name}")
    print(f"    - Measured Uptime:   {receipt.measured_uptime_percent}% (Target: {receipt.target_uptime_percent}%)")
    print(f"    - Verdict:           \033[1;31m{receipt.status}\033[0m")
    print(f"    - Penalty Assessed:  \033[1;31m${receipt.penalty_due_usd:,} USD\033[0m")
    print(f"    - Net Service Due:   \033[1;32m${receipt.net_service_due_usd:,} USD\033[0m (Base: $10,000 USD)")
    print(f"    - Bilateral Digest:  \033[1;35m⚓ ⟨joint:{receipt.joint_bilateral_digest[:16]}...⟩\033[0m\n")

if __name__ == "__main__":
    run_demo()
