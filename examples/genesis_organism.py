#!/usr/bin/env python3
"""
genesis_organism.py — Seeds and spawns the Genesis Organism (Gen #0000).
Part of Project Black-Heart (%🖤).

Produces: examples/organism_gen0.pdf
- Viewable in Preview/Acrobat with its phenotype cellular passport and vector proof nets.
- Runnable via 'python3 examples/organism_gen0.pdf --reproduce' to synthesize Gen #0001!
"""

import os
import sys

# Ensure parent directory is in path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from crypto import generate_keypair
from organism import Organism, Chromosome, PolyglotOrganismCompiler

def seed_genesis():
    print("\033[1;36m[*] Seeding Genesis Polyglot Organism (Gen #0000)...\033[0m")

    # 1. Generate Genesis Cryptographic Identity
    sk, pk = generate_keypair()

    # 2. Construct Genesis Genome
    chromosomes = [
        Chromosome(
            gene_id="GENE-ID-01",
            gene_name="Self-Preservation Identity Carrier",
            expression="🌿 🖤 🖤 SovereignCore",
            expected_normal_form="SovereignCore",
            max_atp=50
        ),
        Chromosome(
            gene_id="GENE-METAB-02",
            gene_name="Black Cone Entropy Absorption",
            expression="🖤 VitalNutrient EntropyNoise",
            expected_normal_form="VitalNutrient",
            max_atp=20
        ),
        Chromosome(
            gene_id="GENE-BRANCH-03",
            gene_name="Adaptive Decision Fork",
            expression="(🖤 🤍) DormantBranch ExpressedBranch",
            expected_normal_form="ExpressedBranch",
            max_atp=30
        )
    ]

    genesis = Organism(
        generation=0,
        parent_hash="00" * 32,
        public_key_hex=pk,
        secret_key_hex=sk,
        chromosomes=chromosomes
    )

    out_pdf = os.path.join(ROOT, "examples", "organism_gen0.pdf")
    PolyglotOrganismCompiler.compile(genesis, out_pdf)

    print(f"\n\033[1;32m[✓] Spawned Genesis Organism: {out_pdf}\033[0m")
    print(f"    - Hash:        {genesis.organism_hash[:24]}...")
    print(f"    - Identity PK: {genesis.public_key_hex[:24]}...")
    print(f"    - Visual Form: open {out_pdf}")
    print(f"    - Check Status: python3 {out_pdf} --status")
    print(f"    - Reproduce:    python3 {out_pdf} --reproduce\n")

if __name__ == "__main__":
    seed_genesis()
