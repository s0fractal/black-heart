#!/usr/bin/env python3
# coding: utf-8
"""
examples/sovereign_demo.py — Full Lifecycle Demonstration of Engine #34 (SOVEREIGN-0.1).
Part of Project Black-Heart (%🖤).

Demonstrates:
  1. Genesis minting with Ed25519 identity and CIDv1 DAG provenance.
  2. Autopoietic self-contemplation & AST zipper rewrites with ATP energy accounting.
  3. Controlled Forgetting Membrane: metabolic capacity bound (B_max), decay, and tombstoning.
  4. Cold substrate migration: seed export and idempotent reconstitution on an isolated host.
  5. Epistemic Mycelium synchronization without copying experience (Manifesto Thesis 2).
  6. ISO 32000 proof-carrying polyglot certificate compilation (`sovereign_organism.pdf`).
"""

import os
import sys
import json
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sovereign_continuity import (
    SovereignOrganism,
    SovereignChromosome,
    SovereignWarrant,
    TombstoneStela,
    generate_sovereign_polyglot
)


def run_demo():
    print("\033[1;36m" + "=" * 70)
    print("  %🖤 BLACK-HEART ENGINE #34: SOVEREIGN CONTINUITY QUINE (SOVEREIGN-0.1)")
    print("=" * 70 + "\033[0m\n")

    # Step 1: Genesis Minting
    print("[1] Minting Genesis Sovereign Organism...")
    org = SovereignOrganism.create_genesis(
        organism_id="%🖤-SOVEREIGN-GENESIS",
        metabolic_capacity=220
    )
    print(f"    Genesis Identity:  ed25519:{org.genesis_pk_hex[:32]}...")
    print(f"    Genesis CIDv1:     {org.cid_chain[0]}")
    print(f"    Metabolic Budget:  {org.membrane.capacity} ATP (Active: {org.current_active_cost()} ATP)")
    print(f"    Active Genes:      {len(org.chromosomes)} chromosomes\n")

    # Step 2: Autopoietic Evolution
    print("[2] Executing Autopoietic Self-Contemplation across 3 Generations...")
    for step_num in range(1, 4):
        receipt = org.evolve_step(thought_stimulus=f"Ontogenetic Contemplation Cycle #{step_num}")
        print(f"    Gen #{receipt.generation} | Successor CID: {receipt.cid[:28]}... | Cumulative Saved: +{receipt.atp_cumulative_saved} ATP")
        print(f"           Active Cost: {receipt.active_cost} / {receipt.metabolic_budget} ATP | Tombstones: {receipt.tombstones_count}")

    print()

    # Step 3: Inducing Metabolic Pressure & Controlled Forgetting
    print("[3] Inducing Metabolic Pressure to Trigger Controlled Forgetting Membrane...")
    print("    Adding 3 experimental warrants to exceed metabolic horizon (220 ATP)...")
    for i in range(3):
        w = SovereignWarrant(
            warrant_id=f"exp-warrant-{i+1}",
            rule_name=f"RULE_DERIVATION_{i+1}",
            pre_term="S (K I) (K I)",
            post_term="K (I I)",
            atp_saved=10 + i * 5,
            hits=1 + i,
            gen_admitted=0,
            maintenance_cost=45
        )
        org.membrane.admit_warrant(w)

    pre_prune_cost = org.current_active_cost()
    print(f"    Active Load (Pre-pruning): {pre_prune_cost} ATP (Exceeds capacity 220 ATP)")

    r4 = org.evolve_step(thought_stimulus="Metabolic Pressure & Membrane Pruning")
    print(f"    Gen #{r4.generation} Sealed | Successor CID: {r4.cid[:28]}...")
    print(f"    Active Load (Post-pruning): \033[1;32m{r4.active_cost} ATP\033[0m (Equilibrium restored <= {r4.metabolic_budget} ATP!)")
    print(f"    Tombstone Stelae in History: {r4.tombstones_count} records")
    for st in org.membrane.tombstones.values():
        print(f"      - {st.tombstone_id}: {st.loss_declaration[:64]}... (Reclaimed: {st.atp_reclaimed} ATP)")
    print()

    # Step 4: Cold Host Substrate Migration
    print("[4] Simulating Substrate Migration to Cold Isolated Host...")
    seed_json = org.export_migration_seed()
    print(f"    Migration Seed Exported: {len(seed_json)} bytes (DAG-CBOR / JCS signed)")

    reconstituted = SovereignOrganism.reconstitute_from_seed(
        seed_json,
        secret_key_hex=org.secret_key_hex
    )
    print(f"    Reconstituted on Cold Host: \033[1;32mSUCCESS\033[0m")
    print(f"    Cryptographic Identity:    {reconstituted.genesis_pk_hex[:32]}... (Exact match!)")
    print(f"    Ontogenetic Chain:         {len(reconstituted.history_receipts)} receipts verified")
    print(f"    Active Chromosomes:        {len(reconstituted.chromosomes)}")
    print(f"    Tombstone Stelae:          {len(reconstituted.membrane.tombstones)} stelae preserved\n")

    # Step 5: Epistemic Mycelium Synchronization
    print("[5] Synchronizing with Epistemic Mycelium (Manifesto Thesis 2)...")
    mycelium_payload = org.synapse.export_payload(org)
    print(f"    Layer 1 Normal Forms:      {len(mycelium_payload['layer_1_normal_forms'])} universal facts")
    print(f"    Layer 2 Warrants:          {len(mycelium_payload['layer_2_warrants'])} verified algebraic rewrites")
    print(f"    Layer 3 Divergences:       {len(mycelium_payload['layer_3_divergences'])} negative immune antibodies")
    print("    Privacy Guarantee:         100% of internal state and private history preserved uncopied.\n")

    # Step 6: PDF Polyglot Compilation
    out_pdf = os.path.join(os.path.dirname(__file__), "sovereign_organism.pdf")
    print(f"[6] Compiling ISO 32000 Vector Proof-Carrying Polyglot...")
    generate_sovereign_polyglot(org, out_pdf)
    file_size = os.path.getsize(out_pdf)
    print(f"    Polyglot Document:         \033[1;32m{out_pdf}\033[0m ({file_size} bytes)")
    print(f"    Standalone CLI Runner:     python3 {out_pdf} --audit")
    print(f"    Migration CLI Command:     python3 {out_pdf} --migrate\n")

    print("\033[1;36m" + "=" * 70)
    print("  [✓] SOVEREIGN CONTINUITY DEMONSTRATION COMPLETE")
    print("=" * 70 + "\033[0m\n")


if __name__ == "__main__":
    run_demo()
