#!/usr/bin/env python3
"""
service_agreement_polyglot.py — Compiles a runnable self-verifying SLA agreement.
Part of Project Black-Heart (%🖤).

Produces: examples/service_agreement_polyglot.pdf
1. Openable in Preview/Acrobat as a clean legal contract.
2. Runnable via 'python3 examples/service_agreement_polyglot.pdf' to adjudicate
   SLA breach/compliance and emit a settlement receipt.
"""

import os
import sys

# Ensure parent directory is in path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monad import SelfVerifyingContractPolyglot

def build_agreement():
    contract = SelfVerifyingContractPolyglot(
        title="CLOUD SERVICE LEVEL AGREEMENT & ESCROW PROTOCOL",
        jurisdiction="Ukraine / International Commercial Arbitration"
    )

    # 1. Register Parties
    contract.add_party(
        role="PROVIDER",
        name="Nebula Hypercloud Infrastructure Ltd.",
        identifier="ed25519:e4f1a8c9b2010874ff"
    )
    contract.add_party(
        role="CLIENT",
        name="Axiom Financial Technologies Inc.",
        identifier="ed25519:7b03df129c8e541a02"
    )
    contract.add_party(
        role="ADJUDICATOR",
        name="Autonomous Black-Heart Settlement Arbiter",
        identifier="ed25519:c991823abf1055de77"
    )

    # 2. Preamble
    contract.add_preamble(
        "This Agreement governs mission-critical compute infrastructure. Both parties agree that "
        "adjudication of service availability, downtime incidents, and liquidated damages shall be "
        "executed deterministically by the embedded mathematical predicate of this document."
    )

    # 3. Legal Articles & Formal Computable Predicates
    contract.add_clause(
        clause_id="CLAUSE-SLA-01",
        article_title="Article 1. Availability Commitment (99.5% Uptime Target)",
        legal_prose=(
            "The Provider guarantees monthly compute cluster uptime of not less than ninety-nine "
            "and one-half percent (99.5%). Uptime is measured across a standard 30-day billing window "
            "(43,200 minutes). All unscheduled outages exceeding 5 minutes constitute downtime."
        ),
        predicate_name="uptime_check",
        expression="total_uptime >= target_uptime",
        expected_normal_form="BOOLEAN"
    )

    contract.add_clause(
        clause_id="CLAUSE-PENALTY-02",
        article_title="Article 2. Liquidated Damages & Penalty Schedule",
        legal_prose=(
            "In the event of an SLA breach, liquidated damages are assessed at Five Hundred US Dollars "
            "($500 USD) for each complete one-tenth of one percent (0.1%) of downtime below the target. "
            "Penalties are automatically deducted from the monthly invoice ($10,000 USD base fee)."
        ),
        predicate_name="penalty_calc",
        expression="floor((target_uptime - actual_uptime) * 10) * 500",
        expected_normal_form="INTEGER_USD"
    )

    # 4. Attach Incident Evidence Log
    contract.attach_evidence(
        record_id="INC-2026-09-02",
        timestamp="2026-09-02T04:15:00Z",
        event_type="Edge Gateway DNS Blackhole",
        duration_min=180,
        description="Core BGP route flapping triggered global edge ingress timeout."
    )
    contract.attach_evidence(
        record_id="INC-2026-09-05",
        timestamp="2026-09-05T11:30:00Z",
        event_type="NVMe Storage Fabric Degradation",
        duration_min=120,
        description="Distributed consensus partition stalled write-ahead logs on zone B."
    )

    # 5. Output file
    output_dir = os.path.dirname(os.path.abspath(__file__))
    out_pdf = os.path.join(output_dir, "service_agreement_polyglot.pdf")
    contract.compile(out_pdf)

    print(f"\033[1;32m[✓] Compiled Self-Verifying Contract Polyglot: {out_pdf}\033[0m")
    print(f"    - Visual Form: Open via PDF viewer (Preview, Acrobat, Chrome)")
    print(f"    - Executable Form: Run via 'python3 {out_pdf}'\n")

if __name__ == "__main__":
    build_agreement()
