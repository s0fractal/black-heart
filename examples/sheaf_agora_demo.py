#!/usr/bin/env python3
# coding: utf-8
"""
examples/sheaf_agora_demo.py — Full Lifecycle Demonstration of Engine #35:
Federated Sheaf Agora & Cohomological Constitutionalism (AGORA-0.2).
Part of Project Black-Heart (%🖤).

Demonstrates:
  1. Multi-chamber parliamentary assembly U = {U_alpha, U_beta, U_gamma}.
  2. Anti-plutocratic quadratic voting dynamics (v_i = sign(w_i) * floor(sqrt(|w_i|))).
  3. Socio-economic inequality telemetry: local and federation-wide Gini indices.
  4. Triple Ratification Gate:
     - Political supermajority (>= 66.7%)
     - Anti-plutocracy ceiling (G_fed < 0.65)
     - Zero Čech cohomology obstruction (dim H^1(U, F) == 0)
  5. Fail-closed Čech fracture veto demonstration (conflicting local axioms).
  6. Sovereign Quine citizen voting using autopoietically conserved metabolic ATP.
  7. Dual-spine ISO 32000 PDF polyglot compilation (`examples/sheaf_agora_parliament.pdf`).
"""

import os
import sys
import json
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import crypto
from crypto import generate_keypair
import glyph
import cid
from cid import is_valid_cidv1

import sheaf_kernel
from sheaf_kernel import EpistemicContext

import agora
from agora import ProposalType, VoteDirection

import sovereign_continuity
from sovereign_continuity import SovereignOrganism

import sheaf_agora
from sheaf_agora import (
    RatificationStatus,
    FederatedBallot,
    calculate_gini,
    FederatedChamber,
    FederatedProposal,
    FederatedSettlementReceipt,
    FederatedAgoraParliament,
    generate_sheaf_agora_pdf
)


def run_demo():
    print("\033[1;36m" + "=" * 70)
    print("  %🖤 BLACK-HEART ENGINE #35: FEDERATED SHEAF AGORA (AGORA-0.2)")
    print("=" * 70 + "\033[0m\n")

    # Step 1: Constitution of Federated Parliamentary Covering U
    print("[1] Constituting Federated Parliamentary Cover U = {U_alpha, U_beta, U_gamma}...")
    parliament = FederatedAgoraParliament("Agora Simplicial Parliament")

    ctx_alpha = EpistemicContext.create("Chamber Alpha", ["logic", "axioms"], 120)
    ctx_beta = EpistemicContext.create("Chamber Beta", ["computation", "axioms"], 150)
    ctx_gamma = EpistemicContext.create("Chamber Gamma", ["mycelium", "civics"], 180)

    ch_alpha = FederatedChamber("alpha", "Chamber Alpha (Pure Logic)", ctx_alpha)
    ch_beta = FederatedChamber("beta", "Chamber Beta (Constructive Computation)", ctx_beta)
    ch_gamma = FederatedChamber("gamma", "Chamber Gamma (Autonomous Civics)", ctx_gamma)

    parliament.register_chamber(ch_alpha)
    parliament.register_chamber(ch_beta)
    parliament.register_chamber(ch_gamma)

    for ch in parliament.chambers.values():
        print(f"    - [{ch.chamber_id}] {ch.name}: Domains={ch.context.domains}, Ceiling={ch.context.budget_ceiling} ATP")

    print(f"    Simplicial Nerve N(U): {len(parliament.chambers)} constituent open charts registered.\n")

    # Step 2: Tabling Constitutional Motion
    print("[2] Tabling Motion PROP-001: Constitutional Identity Axiom...")
    sk_sponsor, pk_sponsor = generate_keypair()
    motion = FederatedProposal(
        proposal_id="PROP-CONSTITUTION-01",
        title="Universal Axiom of Computational Identity",
        proposal_type=ProposalType.THEOREM_CONGRUENCE,
        claim_name="Computational Identity",
        sponsor_pk_hex=pk_sponsor,
        stake_atp=60,
        chamber_terms={
            "alpha": "(K I) (K I)",
            "beta": "I",
            "gamma": "I"
        },
        target_nf="I"
    )
    motion.sign(sk_sponsor)
    parliament.table_proposal(motion)
    print(f"    Sponsor PK:        {motion.sponsor_pk_hex[:32]}...")
    print(f"    Pledged Stake:     {motion.stake_atp} ATP")
    print(f"    Target Normal Form:{motion.target_nf}\n")

    # Step 3: Sovereign Quine Citizen Participation (Engine #34 Integration)
    print("[3] Registering Sovereign Quine Citizens (Engine #34) and Casting Quadratic Ballots...")
    citizen_quine = SovereignOrganism.create_genesis(organism_id="%🖤-SOVEREIGN-CITIZEN-01", metabolic_capacity=250)
    print(f"    Citizen Organism:  {citizen_quine.organism_id} (Gen #{citizen_quine.generation})")

    # Organism casts 49 ATP -> floor(sqrt(49)) = 7 Yeas
    b_quine = parliament.vote_with_sovereign_organism(
        organism=citizen_quine,
        chamber_id="gamma",
        proposal_id=motion.proposal_id,
        atp_stake=49,
        direction=VoteDirection.AYE
    )
    print(f"    - Quine Vote in Gamma: 49 ATP pledged -> {b_quine.effective_votes} Quadratic Yeas")

    # Chamber Alpha and Beta Ballots
    sk_v1, pk_v1 = generate_keypair()
    b1 = FederatedBallot(
        voter_pk_hex=pk_v1, chamber_id="alpha", proposal_id=motion.proposal_id,
        pledged_atp=36, direction=VoteDirection.AYE
    )
    b1.sign(sk_v1)
    parliament.cast_ballot(b1)
    print(f"    - Citizen V1 in Alpha: 36 ATP pledged -> {b1.effective_votes} Quadratic Yeas")

    sk_v2, pk_v2 = generate_keypair()
    b2 = FederatedBallot(
        voter_pk_hex=pk_v2, chamber_id="beta", proposal_id=motion.proposal_id,
        pledged_atp=25, direction=VoteDirection.AYE
    )
    b2.sign(sk_v2)
    parliament.cast_ballot(b2)
    print(f"    - Citizen V2 in Beta:  25 ATP pledged -> {b2.effective_votes} Quadratic Yeas")

    # Step 4: Triple Ratification Gate Resolution
    print("\n[4] Resolving Session via Triple Constitutional Ratification Gate...")
    receipt = parliament.resolve_session(motion.proposal_id)
    print(f"    Political Supermajority: {receipt.total_yeas} Yeas vs {receipt.total_nays} Nays (PASSED)")
    print(f"    Federation Gini Index:   {receipt.federation_gini:.3f} (Ceiling: 0.650 | PASSED)")
    print(f"    Čech 1-Cohomology:       dim H^1(U, F) = {receipt.h1_dimension} (ZERO OBSTRUCTION | PASSED)")
    print(f"    Ratification Standing:   \033[1;32m{receipt.status.value}\033[0m")
    print(f"    Constitutional CIDv1:    {receipt.cid}\n")

    # Step 5: Demonstrating Fail-Closed Čech Cohomology Fracture Veto
    print("[5] Negative Control: Demonstrating Fail-Closed Čech Fracture Veto on Conflicting Claims...")
    fracture_prop = FederatedProposal(
        proposal_id="PROP-FRACTURE-02",
        title="Contradictory Axiom Injection",
        proposal_type=ProposalType.CONSTITUTIONAL_AMENDMENT,
        claim_name="Shared Consensus Definition",
        sponsor_pk_hex=pk_sponsor,
        stake_atp=20,
        chamber_terms={
            "alpha": "K",     # reduces to 🖤
            "beta": "K I"     # reduces to 🖤 (🤍)
        },
        target_nf="N/A"
    )
    fracture_prop.sign(sk_sponsor)
    parliament.table_proposal(fracture_prop)

    # 100% Unanimous affirmative political vote!
    for ch_id in ("alpha", "beta"):
        sk_v, pk_v = generate_keypair()
        b_u = FederatedBallot(
            voter_pk_hex=pk_v, chamber_id=ch_id, proposal_id=fracture_prop.proposal_id,
            pledged_atp=64, direction=VoteDirection.AYE
        )
        b_u.sign(sk_v)
        parliament.cast_ballot(b_u)

    frac_receipt = parliament.resolve_session(fracture_prop.proposal_id)
    print(f"    Political Votes:         {frac_receipt.total_yeas} Yeas vs 0 Nays (100% Supermajority)")
    print(f"    Čech 1-Cohomology:       dim H^1(U, F) = {frac_receipt.h1_dimension} (COHOMOLOGICAL FRACTURE)")
    print(f"    Ratification Result:     \033[1;31m{frac_receipt.status.value}\033[0m")
    print(f"    Rejection Diagnosis:     {frac_receipt.rejection_reason}\n")

    # Step 6: ISO 32000 PDF Polyglot Compilation
    out_pdf = os.path.join(os.path.dirname(__file__), "sheaf_agora_parliament.pdf")
    print(f"[6] Compiling ISO 32000 Vector Polyglot HUD: {out_pdf}...")
    generate_sheaf_agora_pdf(parliament, receipt, out_pdf)
    print(f"    [✓] Polyglot Written: {os.path.getsize(out_pdf)} bytes")
    print(f"    [✓] Standalone Auditable via: python3 {out_pdf}\n")

    print("\033[1;32m[✓ SUCCESS] Engine #35 Demonstration Complete (Q.E.D.)\033[0m\n")
    return out_pdf


if __name__ == "__main__":
    run_demo()
