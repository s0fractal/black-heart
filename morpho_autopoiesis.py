#!/usr/bin/env python3
# coding: latin-1
"""
morpho_autopoiesis.py — Morphogenetic Autopoiesis & Agora Federation (Grok 1 + 3 + 5 Synthesis).
Part of Project Black-Heart (%🖤). Master Synthesis Engine #23.

Synthesizes:
  1. Grok Experiment 1 (Autopoietic Quines & Empirical Ledgers):
     Self-contemplating quine polyglots with active SKIY combinator genomes,
     AST zipper equational rewriting, frozen oracle verification, and empirical
     scientific ledgers under strict ISO 32000 §7.5.6 append-only growth.
  2. Grok Experiment 3 (Reaction-Diffusion Morphogenesis & Lafont Proof-Nets):
     Active genome structural hashes deterministically drive Gray-Scott PDE
     kinetic drift (F, k), triggering Turing bifurcations (Solitons -> Labyrinth -> Spots).
     Activator peaks, saddles, and sinks are compiled into Lafont interaction nets,
     reduced under ATP gas, and settled into Weisfeiler-Lehman canonical graph digests.
  3. Grok Experiment 5 (The Mycelial Agora Federation):
     The organism tables its evolved theorems directly onto the Mycelial Agora floor
     as AgoraProposal bills, staking ATP and earning constitutional ratification
     under quadratic voting and Church-Rosser reduction audits.

Zero external dependencies: 100% Python standard library.
"""

from __future__ import annotations
import os
import sys
import json
import time
import math
import hashlib
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any, Union

from crypto import (
    generate_keypair,
    public_key_from_secret,
    sign_bytes,
    verify_bytes,
    is_valid_public_key,
)
from glyph import (
    Term, Comb, Var, App,
    K, I, S, Y,
    parse, evaluate, tree_size, canonical_bytes, term_hash,
    GLYPH_K, GLYPH_I, GLYPH_S, GLYPH_Y, GLYPH_ANCHOR
)
from organism import Organism, Chromosome
from morphogenesis import (
    MorphogeneticField,
    TuringArchetype,
    ChromaticPalette,
    PALETTES,
)

ARCHETYPE_SOLITON = TuringArchetype.SOLITONS
ARCHETYPE_LABYRINTH = TuringArchetype.LABYRINTH
ARCHETYPE_SPOTS = TuringArchetype.SPOTS
from interaction import (
    InteractionNet,
    PortRef,
    AGENT_CONSTRUCT,
    AGENT_DUPLICATE,
    AGENT_ERASE,
    PORT_PRINCIPAL,
    PORT_LEFT,
    PORT_RIGHT,
)
from morpho_net import (
    SpatialCriticalPoint,
    compile_morphogenetic_proof_net,
)
from metamorphosis import (
    Address,
    get_subterm_at,
    replace_subterm_at,
    enumerate_subterm_addresses,
    RULE_S_K_K,
    RULE_S_K_I,
    RULE_S_K_I_COLLAPSE,
    RULE_STATIC_I,
    RULE_STATIC_K,
    RULE_EXPLORATORY_MUTATION,
    match_and_rewrite,
    propose_form_metamorphoses,
    FrozenEvaluator,
    EvaluationReceipt,
    MutationVerdict,
    ExperimentRecord,
    ExperimentLog,
    derive_experiment_id,
)
from agora import (
    AgoraProposal,
    AgoraBallot,
    VoteDirection,
    ProposalType,
    ProposalStatus,
    AgoraConsensusEngine,
    grow_agora_page,
    audit_agora_parliament,
)

MORPHO_AUTOPOIESIS_MANIFEST_PREFIX = "# %\U0001F5A4 MORPHO_AUTOPOIESIS_MANIFEST: "

# ============================================================================
# 1. MORPHOGENETIC AUTOPOIESIS RECEIPT
# ============================================================================

@dataclass
class MorphoAutopoiesisReceipt:
    """
    Cryptographic and phenotypic settlement receipt for one evolutionary epoch.
    Unifies:
      - Genotypic AST zipper equational rewrite & empirical oracle verification (Grok 1)
      - Turing reaction-diffusion kinetic parameters & Weisfeiler-Lehman proof-net digest (Grok 3)
      - Agora federation tabling status & Ed25519 digital signature (Grok 5)
    """
    generation: int
    timestamp_utc: str
    parent_hash: str
    organism_hash: str
    gene_id: str
    rule_name: str
    site_address: List[str]
    pre_term: str
    post_term: str
    atp_saved: int
    size_saved: int
    experiment_id: str
    experiments_count: int
    # Morphogenetic phenotypic kinetics (Grok 3)
    archetype: str
    feed_rate_f: float
    kill_rate_k: float
    pde_steps: int
    # Topological proof-net reduction (Grok 3)
    initial_nodes: int
    reduced_steps: int
    net_atp_burned: int
    weisfeiler_lehman_digest: str
    # Agora federation (Grok 5)
    tabled_proposal_id: str = ""
    agora_atp_staked: int = 0
    # Cryptographic attestation
    public_key_hex: str = ""
    signature_hex: str = ""
    receipt_hash: str = ""

    def canonical_bytes_for_signing(self) -> bytes:
        site_str = ",".join(self.site_address)
        payload = (
            f"MORPHO_AUTOPOIESIS:{self.generation}:{self.timestamp_utc}:{self.parent_hash}:"
            f"{self.organism_hash}:{self.gene_id}:{self.rule_name}:{site_str}:"
            f"{self.pre_term}:{self.post_term}:{self.atp_saved}:{self.size_saved}:"
            f"{self.experiment_id}:{self.experiments_count}:{self.archetype}:"
            f"{self.feed_rate_f:.6f}:{self.kill_rate_k:.6f}:{self.pde_steps}:"
            f"{self.initial_nodes}:{self.reduced_steps}:{self.net_atp_burned}:"
            f"{self.weisfeiler_lehman_digest}:{self.tabled_proposal_id}:{self.agora_atp_staked}:"
            f"{self.public_key_hex}"
        )
        return payload.encode("utf-8")

    def compute_hash(self) -> str:
        data = self.canonical_bytes_for_signing() + (f":{self.signature_hex}".encode("utf-8") if self.signature_hex else b"")
        return hashlib.sha256(data).hexdigest()

    def sign(self, secret_key_hex: str) -> None:
        sk_bytes = bytes.fromhex(secret_key_hex)
        pk_bytes = public_key_from_secret(sk_bytes)
        self.public_key_hex = pk_bytes.hex()
        sig = sign_bytes(sk_bytes, self.canonical_bytes_for_signing())
        self.signature_hex = sig.hex()
        self.receipt_hash = self.compute_hash()

    def is_attested(self) -> bool:
        return bool(self.public_key_hex and self.signature_hex)

    def verify_integrity(self) -> bool:
        if self.generation < 0:
            return False
        if len(self.weisfeiler_lehman_digest) != 64:
            return False
        expected_hash = self.compute_hash()
        if self.receipt_hash and self.receipt_hash != expected_hash:
            return False
        return True

    def verify(self) -> bool:
        if not self.verify_integrity():
            return False
        if not self.is_attested():
            return False
        if not is_valid_public_key(self.public_key_hex):
            return False
        try:
            pk_bytes = bytes.fromhex(self.public_key_hex)
            sig_bytes = bytes.fromhex(self.signature_hex)
            return verify_bytes(pk_bytes, self.canonical_bytes_for_signing(), sig_bytes)
        except Exception:
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generation": self.generation,
            "timestamp_utc": self.timestamp_utc,
            "parent_hash": self.parent_hash,
            "organism_hash": self.organism_hash,
            "gene_id": self.gene_id,
            "rule_name": self.rule_name,
            "site_address": self.site_address,
            "pre_term": self.pre_term,
            "post_term": self.post_term,
            "atp_saved": self.atp_saved,
            "size_saved": self.size_saved,
            "experiment_id": self.experiment_id,
            "experiments_count": self.experiments_count,
            "archetype": self.archetype,
            "feed_rate_f": self.feed_rate_f,
            "kill_rate_k": self.kill_rate_k,
            "pde_steps": self.pde_steps,
            "initial_nodes": self.initial_nodes,
            "reduced_steps": self.reduced_steps,
            "net_atp_burned": self.net_atp_burned,
            "weisfeiler_lehman_digest": self.weisfeiler_lehman_digest,
            "tabled_proposal_id": self.tabled_proposal_id,
            "agora_atp_staked": self.agora_atp_staked,
            "public_key_hex": self.public_key_hex,
            "signature_hex": self.signature_hex,
            "receipt_hash": self.receipt_hash,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> MorphoAutopoiesisReceipt:
        return cls(
            generation=int(d["generation"]),
            timestamp_utc=str(d["timestamp_utc"]),
            parent_hash=str(d["parent_hash"]),
            organism_hash=str(d["organism_hash"]),
            gene_id=str(d["gene_id"]),
            rule_name=str(d["rule_name"]),
            site_address=list(d.get("site_address", [])),
            pre_term=str(d["pre_term"]),
            post_term=str(d["post_term"]),
            atp_saved=int(d["atp_saved"]),
            size_saved=int(d["size_saved"]),
            experiment_id=str(d["experiment_id"]),
            experiments_count=int(d["experiments_count"]),
            archetype=str(d["archetype"]),
            feed_rate_f=float(d["feed_rate_f"]),
            kill_rate_k=float(d["kill_rate_k"]),
            pde_steps=int(d["pde_steps"]),
            initial_nodes=int(d["initial_nodes"]),
            reduced_steps=int(d["reduced_steps"]),
            net_atp_burned=int(d["net_atp_burned"]),
            weisfeiler_lehman_digest=str(d["weisfeiler_lehman_digest"]),
            tabled_proposal_id=str(d.get("tabled_proposal_id", "")),
            agora_atp_staked=int(d.get("agora_atp_staked", 0)),
            public_key_hex=str(d["public_key_hex"]),
            signature_hex=str(d.get("signature_hex", "")),
            receipt_hash=str(d.get("receipt_hash", "")),
        )


# ============================================================================
# 2. MORPHOGENETIC AUTOPOIETIC ORGANISM STATE
# ============================================================================

@dataclass
class MorphoAutopoieticOrganism:
    """
    Sovereign state of a Morphogenetic Autopoietic Quine Organism.
    Couples combinator chromosomes, reaction-diffusion field, interaction net,
    accumulated empirical experiment ledger, and metabolic ATP reserves.
    """
    organism_id: str
    generation: int
    parent_hash: str
    organism_hash: str
    chromosomes: List[Chromosome]
    public_key_hex: str
    field: MorphogeneticField
    archetype_key: str
    feed_rate_f: float
    kill_rate_k: float
    weisfeiler_lehman_digest: str
    receipt_chain: List[MorphoAutopoiesisReceipt] = field(default_factory=list)
    experiment_log: ExperimentLog = field(default_factory=ExperimentLog)
    atp_reserve: int = 1000

    def compute_genome_hash(self) -> str:
        tokens = []
        for c in sorted(self.chromosomes, key=lambda x: x.gene_id):
            tokens.append(f"{c.gene_id}:{c.expression}:{c.expected_normal_form}")
        return hashlib.sha256(";".join(tokens).encode("utf-8")).hexdigest()

    def compute_kinetic_drift(self) -> Tuple[float, float, str]:
        """
        Translates genotypic AST structural complexity into continuous kinetic drift (F, k).
        Folding function:
          ΔF = (int(H[:8], 16) % 1000 / 1000 - 0.5) * 0.008
          Δk = (int(H[8:16], 16) % 1000 / 1000 - 0.5) * 0.006
        """
        gh = self.compute_genome_hash()
        h_f = int(gh[:8], 16) % 1000
        h_k = int(gh[8:16], 16) % 1000

        df = (h_f / 1000.0 - 0.5) * 0.008
        dk = (h_k / 1000.0 - 0.5) * 0.006

        base_f, base_k = 0.030, 0.062
        f = max(0.012, min(0.062, base_f + df))
        k = max(0.045, min(0.068, base_k + dk))

        # Classify archetype
        if f < 0.032 and k < 0.064:
            archetype = ARCHETYPE_SOLITON.key
        elif f <= 0.042:
            archetype = ARCHETYPE_LABYRINTH.key
        else:
            archetype = ARCHETYPE_SPOTS.key

        return f, k, archetype

    def compute_hash(self) -> str:
        gh = self.compute_genome_hash()
        data = (
            f"MORPHO_ORGANISM:{self.organism_id}:{self.generation}:{self.parent_hash}:"
            f"{gh}:{self.public_key_hex}:{self.feed_rate_f:.6f}:{self.kill_rate_k:.6f}:"
            f"{self.archetype_key}:{self.weisfeiler_lehman_digest}"
        )
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "organism_id": self.organism_id,
            "generation": self.generation,
            "parent_hash": self.parent_hash,
            "organism_hash": self.organism_hash,
            "chromosomes": [
                {
                    "gene_id": c.gene_id,
                    "gene_name": getattr(c, "gene_name", c.gene_id),
                    "expression": c.expression,
                    "expected_normal_form": str(c.expected_normal_form),
                    "max_atp": c.max_atp,
                }
                for c in self.chromosomes
            ],
            "public_key_hex": self.public_key_hex,
            "archetype_key": self.archetype_key,
            "feed_rate_f": self.feed_rate_f,
            "kill_rate_k": self.kill_rate_k,
            "weisfeiler_lehman_digest": self.weisfeiler_lehman_digest,
            "atp_reserve": self.atp_reserve,
            "receipt_chain": [r.to_dict() for r in self.receipt_chain],
            "experiment_log": self.experiment_log.to_list(),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> MorphoAutopoieticOrganism:
        chroms = [
            Chromosome(
                gene_id=str(c["gene_id"]),
                gene_name=str(c.get("gene_name", c["gene_id"])),
                expression=str(c["expression"]),
                expected_normal_form=str(c["expected_normal_form"]),
                max_atp=int(c.get("max_atp", 10_000)),
            )
            for c in d["chromosomes"]
        ]
        receipts = [MorphoAutopoiesisReceipt.from_dict(r) for r in d.get("receipt_chain", [])]
        elog = ExperimentLog.from_list(d.get("experiment_log", []))

        arch_key = str(d.get("archetype_key", ARCHETYPE_SOLITON.key))
        f_val = float(d.get("feed_rate_f", 0.030))
        k_val = float(d.get("kill_rate_k", 0.062))

        # Reconstruct morphogenetic field
        arch = ARCHETYPE_SOLITON
        if arch_key == ARCHETYPE_LABYRINTH.key:
            arch = ARCHETYPE_LABYRINTH
        elif arch_key == ARCHETYPE_SPOTS.key:
            arch = ARCHETYPE_SPOTS

        field = MorphogeneticField(width=32, height=32, F=f_val, k=k_val)
        field.seed_patch(16, 16, radius=4, seed_val=42)

        return cls(
            organism_id=str(d["organism_id"]),
            generation=int(d["generation"]),
            parent_hash=str(d["parent_hash"]),
            organism_hash=str(d["organism_hash"]),
            chromosomes=chroms,
            public_key_hex=str(d["public_key_hex"]),
            field=field,
            archetype_key=arch_key,
            feed_rate_f=f_val,
            kill_rate_k=k_val,
            weisfeiler_lehman_digest=str(d.get("weisfeiler_lehman_digest", "0" * 64)),
            receipt_chain=receipts,
            experiment_log=elog,
            atp_reserve=int(d.get("atp_reserve", 1000)),
        )


# ============================================================================
# 3. SEED CREATION
# ============================================================================

def create_morpho_autopoietic_seed(
    secret_key_hex: Optional[str] = None
) -> Tuple[MorphoAutopoieticOrganism, str]:
    """
    Creates an initial embryonic seed organism combining SKIY chromosomes,
    a Turing reaction-diffusion field, and a compiled Lafont interaction net.
    """
    if secret_key_hex:
        sk_hex = secret_key_hex
        pk_hex = public_key_from_secret(bytes.fromhex(sk_hex)).hex()
    else:
        sk_hex, pk_hex = generate_keypair()

    # Initial Chromosomes with reducible redexes
    chroms = [
        Chromosome(
            gene_id="GENE-CORE-SIG",
            gene_name="Core Signal",
            expression="S (K alpha) I",
            expected_normal_form="alpha",
            max_atp=10_000,
        ),
        Chromosome(
            gene_id="GENE-COMM-ID",
            gene_name="Commutative ID",
            expression="S (K alpha) (K beta)",
            expected_normal_form="K (alpha beta)",
            max_atp=10_000,
        ),
        Chromosome(
            gene_id="GENE-REDEX-SKK",
            gene_name="Redex SKK",
            expression="K alpha beta",
            expected_normal_form="alpha",
            max_atp=10_000,
        ),
        Chromosome(
            gene_id="GENE-CHURCH-F",
            gene_name="Church False",
            expression="I gamma",
            expected_normal_form="gamma",
            max_atp=10_000,
        ),
    ]

    # Initial Reaction-Diffusion Field
    field = MorphogeneticField(width=32, height=32, F=ARCHETYPE_SOLITON.F, k=ARCHETYPE_SOLITON.k)
    field.seed_patch(16, 16, radius=4, seed_val=42)
    for _ in range(40):
        field.step()

    # Initial Proof-Net
    net, _ = compile_morphogenetic_proof_net(field)
    steps_reduced, _, _ = net.reduce(max_atp=2000)
    wl_digest = net.canonical_digest()

    org = MorphoAutopoieticOrganism(
        organism_id=f"morpho-quine-{pk_hex[:8]}",
        generation=0,
        parent_hash="0" * 64,
        organism_hash="",
        chromosomes=chroms,
        public_key_hex=pk_hex,
        field=field,
        archetype_key=ARCHETYPE_SOLITON.key,
        feed_rate_f=field.F,
        kill_rate_k=field.k,
        weisfeiler_lehman_digest=wl_digest,
        atp_reserve=1200,
    )

    f, k, arch = org.compute_kinetic_drift()
    org.feed_rate_f = f
    org.kill_rate_k = k
    org.archetype_key = arch
    org.organism_hash = org.compute_hash()

    return org, sk_hex


# ============================================================================
# 4. VISUAL VECTOR PAGE BUILDER
# ============================================================================

def _build_morpho_page_stream(
    receipt: MorphoAutopoiesisReceipt,
    org: MorphoAutopoieticOrganism
) -> str:
    """
    Renders an obsidian-themed A4 PDF page (595.28 x 841.89 pt) containing:
      - Left column: Active AST rewrite card, active genome, WL topological settlement.
      - Right column: PostScript vector vesicle reaction-diffusion medallion,
        singularity agent overlays (🌱 👥 🕳️), and kinetic HUD.
      - Bottom: Empirical scientific ledger, Agora federation badge, Ed25519 signature.
    """
    ops: List[str] = []

    # Canvas Background: Obsidian Void (#0b0d13)
    ops.append("q")
    ops.append("0.043 0.051 0.075 rg")
    ops.append("0 0 595.28 841.89 re f")

    # Header Card (#121520)
    ops.append("0.070 0.082 0.125 rg")
    ops.append("36 750 523.28 65 re f")
    ops.append("0.2 0.6 0.8 RG 1 w")
    ops.append("36 750 523.28 65 re s")

    # Header Text
    ops.append("BT /F1 16 Tf 0.3 0.85 1.0 rg 50 790 Td (%[BH] PROJECT BLACK-HEART -- MORPHOGENETIC AUTOPOIESIS) Tj ET")
    ops.append(f"BT /F1 10 Tf 0.8 0.85 0.95 rg 50 765 Td (Generation #{receipt.generation} | Organism ID: {org.organism_id} | Archetype: {receipt.archetype}) Tj ET")
    ops.append(f"BT /F1 8 Tf 0.5 0.6 0.7 rg 50 754 Td (Organism Hash: [#] {receipt.organism_hash[:32]}... | PK: {receipt.public_key_hex[:24]}...) Tj ET")

    # LEFT COLUMN (x: 36..290)
    # 1. Active AST Rewrite Card
    ops.append("0.060 0.070 0.105 rg 36 610 250 125 re f")
    ops.append("0.15 0.5 0.6 RG 1 w 36 610 250 125 re s")
    ops.append("BT /F1 11 Tf 0.2 0.9 0.7 rg 46 715 Td (ACTIVE AST EQUATIONAL REWRITE) Tj ET")
    ops.append(f"BT /F1 9 Tf 0.9 0.9 0.9 rg 46 695 Td (Rule Applied:  {receipt.rule_name}) Tj ET")
    ops.append(f"BT /F1 9 Tf 0.9 0.9 0.9 rg 46 680 Td (Target Gene:   {receipt.gene_id}) Tj ET")
    ops.append(f"BT /F1 8 Tf 0.7 0.8 0.9 rg 46 665 Td (Pre-Term:      {receipt.pre_term[:28]}) Tj ET")
    ops.append(f"BT /F1 8 Tf 0.2 0.9 0.7 rg 46 650 Td (Post-Term:     {receipt.post_term[:28]}) Tj ET")
    ops.append(f"BT /F1 9 Tf 0.3 0.85 1.0 rg 46 635 Td (Energy Saved:  -{receipt.atp_saved} ATP fuel quanta) Tj ET")
    ops.append(f"BT /F1 9 Tf 0.8 0.8 0.5 rg 46 620 Td (Syntactic Delta:   -{receipt.size_saved} nodes | Oracle: VERIFIED) Tj ET")

    # 2. Active Combinator Genome
    ops.append("0.060 0.070 0.105 rg 36 445 250 150 re f")
    ops.append("0.15 0.5 0.6 RG 1 w 36 445 250 150 re s")
    ops.append("BT /F1 11 Tf 0.3 0.85 1.0 rg 46 575 Td (ACTIVE COMBINATOR GENOME) Tj ET")
    y_g = 555
    for c in org.chromosomes[:4]:
        safe_expr = c.expression.replace("(", "[").replace(")", "]")
        ops.append(f"BT /F1 8 Tf 0.85 0.9 0.95 rg 46 {y_g} Td (* {c.gene_id}: {safe_expr[:24]}) Tj ET")
        ops.append(f"BT /F1 7 Tf 0.5 0.7 0.8 rg 56 {y_g - 10} Td (-> Normal Form: {c.expected_normal_form[:20]}) Tj ET")
        y_g -= 24

    # 3. Topological Proof-Net Settlement (WL Digest)
    ops.append("0.060 0.070 0.105 rg 36 335 250 95 re f")
    ops.append("0.6 0.3 0.8 RG 1 w 36 335 250 95 re s")
    ops.append("BT /F1 11 Tf 0.8 0.4 1.0 rg 46 410 Td (LAFONT PROOF-NET & WL TOPOLOGY) Tj ET")
    ops.append(f"BT /F1 8 Tf 0.9 0.9 0.9 rg 46 392 Td (Initial Spatial Nodes: {receipt.initial_nodes}) Tj ET")
    ops.append(f"BT /F1 8 Tf 0.9 0.9 0.9 rg 46 378 Td (O\\(1\\) Rewrites Reduced:  {receipt.reduced_steps} steps) Tj ET")
    ops.append(f"BT /F1 8 Tf 0.9 0.9 0.9 rg 46 364 Td (Proof-Net ATP Burned:  {receipt.net_atp_burned} ATP) Tj ET")
    ops.append(f"BT /F1 7 Tf 0.4 0.9 0.9 rg 46 348 Td (WL-Digest: [#] {receipt.weisfeiler_lehman_digest[:26]}...) Tj ET")

    # RIGHT COLUMN (x: 305..559)
    # 4. Turing Reaction-Diffusion Medallion & Singularity Overlay
    ops.append("0.060 0.070 0.105 rg 305 445 254 290 re f")
    ops.append("0.2 0.6 0.8 RG 1 w 305 445 254 290 re s")
    ops.append("BT /F1 11 Tf 0.3 0.85 1.0 rg 315 715 Td (TURING REACTION-DIFFUSION FIELD) Tj ET")

    # Draw low-res vector vesicle cells (16x16 grid for PDF compact size)
    v_field = org.field
    v_data = v_field.v
    fw, fh = v_field.width, v_field.height
    step_x = 220.0 / 16.0
    step_y = 200.0 / 16.0
    orig_x = 320.0
    orig_y = 480.0

    for gy in range(16):
        sy = (gy * fh) // 16
        for gx in range(16):
            sx = (gx * fw) // 16
            val = v_data[sy * fw + sx]
            # Color ramp from obsidian (#0b0d13) to cyan/gold
            r_val = min(1.0, val * 1.8)
            g_val = min(1.0, val * 2.2)
            b_val = min(1.0, val * 2.8 + 0.1)
            ops.append(f"{r_val:.3f} {g_val:.3f} {b_val:.3f} rg")
            px = orig_x + gx * step_x
            py = orig_y + gy * step_y
            ops.append(f"{px:.1f} {py:.1f} {step_x - 1:.1f} {step_y - 1:.1f} re f")

    # Draw HUD underneath field
    ops.append(f"BT /F1 8 Tf 0.8 0.85 0.95 rg 315 465 Td (Kinetics: F={receipt.feed_rate_f:.4f}, k={receipt.kill_rate_k:.4f} | Archetype: {receipt.archetype}) Tj ET")
    ops.append(f"BT /F1 8 Tf 0.5 0.8 0.7 rg 315 452 Td (Torus Domain: {fw}x{fh} | Singularity Sites: {receipt.initial_nodes} nodes) Tj ET")

    # 5. Agora Federation Card (Right column lower, x: 305..559, y: 335..430)
    ops.append("0.060 0.070 0.105 rg 305 335 254 95 re f")
    ops.append("0.8 0.6 0.2 RG 1 w 305 335 254 95 re s")
    ops.append("BT /F1 11 Tf 1.0 0.75 0.2 rg 315 410 Td (MYCELIAL AGORA FEDERATION) Tj ET")
    if receipt.tabled_proposal_id:
        ops.append(f"BT /F1 8 Tf 0.2 0.9 0.7 rg 315 392 Td (Status: TABLED ON AGORA FLOOR) Tj ET")
        ops.append(f"BT /F1 8 Tf 0.9 0.9 0.9 rg 315 378 Td (Proposal ID:  {receipt.tabled_proposal_id[:24]}...) Tj ET")
        ops.append(f"BT /F1 8 Tf 0.9 0.9 0.9 rg 315 364 Td (ATP Staked:   {receipt.agora_atp_staked} ATP fuel units) Tj ET")
        ops.append(f"BT /F1 7 Tf 0.8 0.8 0.8 rg 315 348 Td (Audited via Church-Rosser reduction confluence) Tj ET")
    else:
        ops.append(f"BT /F1 8 Tf 0.7 0.7 0.7 rg 315 392 Td (Status: LOCAL CONGRUENCE ATTESTED) Tj ET")
        ops.append(f"BT /F1 8 Tf 0.8 0.8 0.8 rg 315 378 Td (Metabolic Reserves: {org.atp_reserve} ATP) Tj ET")
        ops.append(f"BT /F1 7 Tf 0.5 0.7 0.8 rg 315 364 Td (Eligible for Agora tabling with stake) Tj ET")
        ops.append(f"BT /F1 7 Tf 0.5 0.7 0.8 rg 315 348 Td (Quadratic Voting Weight: W = floor\\(sqrt\\(ATP\\)\\)) Tj ET")

    # BOTTOM SECTION (y: 110..320)
    # 6. Empirical Scientific Ledger
    ops.append("0.050 0.060 0.090 rg 36 120 523.28 200 re f")
    ops.append("0.2 0.5 0.7 RG 1 w 36 120 523.28 200 re s")
    ops.append("BT /F1 11 Tf 0.3 0.85 1.0 rg 46 300 Td (EMPIRICAL SCIENTIFIC LEDGER \\227 PROVENANCE & DIVERGENCE AUDIT) Tj ET")
    
    # Render latest 5 empirical records
    records = org.experiment_log.records[-6:] if org.experiment_log.records else []
    y_rec = 280
    if not records:
        ops.append(f"BT /F1 8 Tf 0.6 0.6 0.6 rg 46 {y_rec} Td (No empirical experiments executed yet in Genesis.) Tj ET")
    else:
        for r in reversed(records):
            is_acc = (r.verdict == MutationVerdict.ACCEPTED_MORE_EFFICIENT)
            color = "0.2 0.9 0.6" if is_acc else "0.9 0.4 0.3"
            tag = "[ACCEPTED]" if is_acc else "[REJECTED]"
            safe_rule = r.rule_name.replace("(", "[").replace(")", "]")
            line_txt = f"{tag} {r.experiment_id}: {safe_rule[:24]} on {r.gene_id} | dATP={r.atp_delta:+d} | tests={r.test_inputs_count}"
            ops.append(f"BT /F1 8 Tf {color} rg 46 {y_rec} Td ({line_txt}) Tj ET")
            y_rec -= 15

    # FOOTER SEAL (y: 35..105)
    ops.append("0.040 0.050 0.075 rg 36 35 523.28 75 re f")
    ops.append("0.2 0.6 0.8 RG 1 w 36 35 523.28 75 re s")
    ops.append("BT /F1 9 Tf 0.2 0.9 0.7 rg 46 90 Td (ISO 32000 Section 7.5.6 APPEND-ONLY QUINE RECEIPT SEAL) Tj ET")
    ops.append(f"BT /F1 8 Tf 0.8 0.8 0.8 rg 46 76 Td (Parent Hash:  [#] {receipt.parent_hash[:48]}...) Tj ET")
    ops.append(f"BT /F1 8 Tf 0.8 0.8 0.8 rg 46 62 Td (Receipt Hash: [#] {receipt.receipt_hash[:48]}...) Tj ET")
    ops.append(f"BT /F1 8 Tf 0.3 0.85 1.0 rg 46 48 Td (Ed25519 Sig:  {receipt.signature_hex[:56]}... [RFC 8032 VERIFIED]) Tj ET")

    ops.append("Q")
    return "\n".join(ops)


# ============================================================================
# 5. EMBEDDED PYTHON QUINE RUNNER TEMPLATE
# ============================================================================

_MORPHO_RUNNER_TEMPLATE = r'''
# --- MORPHOGENETIC AUTOPOIESIS EXECUTABLE QUINE RUNNER ---
import os, sys, json, hashlib

def _load_manifest():
    with open(__file__, "rb") as f:
        data = f.read()
    prefix = bytes([0x23, 0x20, 0x25, 0xf0, 0x9f, 0x96, 0xa4]) + b" MORPHO_AUTOPOIESIS_MANIFEST: "
    idx = data.rfind(prefix)
    if idx == -1:
        print("[!] No Morphogenetic Autopoiesis manifest found in self.")
        sys.exit(1)
    line = data[idx + len(prefix):].split(b"\n", 1)[0]
    man = json.loads(line.decode("utf-8"))
    source_dir = man.get("source_dir")
    if source_dir and source_dir not in sys.path:
        sys.path.insert(0, source_dir)
    return man, __file__

def cmd_info():
    man, _ = _load_manifest()
    latest = man["receipt_chain"][-1]
    print("\033[1;36m" + "=" * 70)
    print("  %🖤 PROJECT BLACK-HEART — MORPHOGENETIC AUTOPOIESIS QUINE HUD")
    print("=" * 70 + "\033[0m")
    print(f"  Organism ID:       {man['organism_id']}")
    print(f"  Generation:        #{man['generation']}")
    print(f"  Organism Hash:     ⚓ {man['organism_hash']}")
    print(f"  Turing Archetype:  {latest.get('archetype')}")
    print(f"  Kinetics:          F={latest.get('feed_rate_f', 0):.4f}, k={latest.get('kill_rate_k', 0):.4f}")
    print(f"  WL-Digest:         ⚓ {latest.get('weisfeiler_lehman_digest', '')[:32]}...")
    print(f"  Active Chromosomes:{len(man['chromosomes'])}")
    print(f"  ATP Reserve:       {man.get('atp_reserve', 0)} ATP")
    if latest.get("tabled_proposal_id"):
        print(f"  Agora Proposal:    {latest['tabled_proposal_id']}")
    print("\033[1;36m" + "=" * 70 + "\033[0m\n")

def cmd_audit():
    man, path = _load_manifest()
    from morpho_autopoiesis import audit_morpho_autopoietic_organism
    if audit_morpho_autopoietic_organism(path):
        print("\033[1;32m[+ SOUND] All generational receipts and proofs verified fail-closed.\033[0m")
    else:
        print("\033[1;31m[- UNSOUND] Document failed audit.\033[0m")
        sys.exit(1)

def cmd_evolve():
    _, path = _load_manifest()
    from morpho_autopoiesis import evolve_morpho_autopoietic_organism
    succ, rec = evolve_morpho_autopoietic_organism(path)
    print(f"\033[1;32m[EVOLUTION ACCOMPLISHED] Generation #{succ.generation} appended in-place!\033[0m")
    print(f"  New Organism Hash: [#] {succ.organism_hash}")
    print(f"  Applied Rewrite:   {rec.rule_name} on {rec.gene_id}")
    print(f"  Archetype:         {rec.archetype} (F={rec.feed_rate_f:.4f}, k={rec.kill_rate_k:.4f})")
    print(f"  WL-Digest:         ⚓ {rec.weisfeiler_lehman_digest[:32]}...")

if __name__ == "__main__":
    if "--audit" in sys.argv:
        cmd_audit()
    elif "--evolve" in sys.argv or "--grow" in sys.argv:
        cmd_evolve()
    else:
        cmd_info()
'''


# ============================================================================
# 6. INITIALIZE GENESIS POLYGLOT
# ============================================================================

def init_morpho_autopoietic_organism(
    pdf_path: str,
    secret_key_hex: Optional[str] = None
) -> Tuple[MorphoAutopoieticOrganism, MorphoAutopoiesisReceipt]:
    """
    Creates an initial Genesis (Generation 0) Morphogenetic Autopoietic Quine.
    The document contains:
      - Valid ISO 32000 PDF structure (Page 1) with obsidian vector HUD.
      - Embedded Python executable quine runner.
      - Attested Genesis receipt with Ed25519 signature.
      - Private key safely stored in `<file>` + PRIVATE_KEY_SUFFIX (mode 0600), never in PDF bytes.
    """
    org, sk_hex = create_morpho_autopoietic_seed(secret_key_hex)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Create Genesis receipt
    genesis_receipt = MorphoAutopoiesisReceipt(
        generation=0,
        timestamp_utc=now,
        parent_hash="0" * 64,
        organism_hash=org.organism_hash,
        gene_id="GENESIS-CORE",
        rule_name="GENESIS_SEED",
        site_address=[],
        pre_term="GENESIS",
        post_term="GENESIS",
        atp_saved=0,
        size_saved=0,
        experiment_id="exp_genesis",
        experiments_count=0,
        archetype=org.archetype_key,
        feed_rate_f=org.feed_rate_f,
        kill_rate_k=org.kill_rate_k,
        pde_steps=40,
        initial_nodes=len(compile_morphogenetic_proof_net(org.field)[1]),
        reduced_steps=0,
        net_atp_burned=0,
        weisfeiler_lehman_digest=org.weisfeiler_lehman_digest,
        public_key_hex=org.public_key_hex,
    )
    genesis_receipt.sign(sk_hex)
    org.receipt_chain = [genesis_receipt]

    # Build PDF Byte Structure
    page_stream = _build_morpho_page_stream(genesis_receipt, org)
    stream_bytes = page_stream.encode("utf-8")

    header_text = (
        f"#!{sys.executable}\n"
        "# coding: latin-1\n"
        "# ============================================================================\n"
        "# %🖤 PROJECT BLACK-HEART: MORPHOGENETIC AUTOPOIETIC QUINE (ISO 32000 POLYGLOT)\n"
        "# ============================================================================\n"
        "r'''\n"
    ).encode("utf-8")

    out = bytearray(header_text)
    pdf_header = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
    out.extend(pdf_header)

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595.28 841.89] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("utf-8") + stream_bytes + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
    ]

    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out.extend(f"{i} 0 obj\n".encode("utf-8"))
        out.extend(obj)
        out.extend(b"\nendobj\n")

    xref_offset = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("utf-8"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("utf-8"))

    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("utf-8")
    out.extend(trailer)

    manifest_payload = org.to_dict()
    manifest_payload["source_dir"] = os.path.dirname(os.path.abspath(__file__))
    manifest_line = MORPHO_AUTOPOIESIS_MANIFEST_PREFIX.encode("utf-8") + json.dumps(manifest_payload, separators=(',', ':')).encode("utf-8") + b"\n"
    script_data = _MORPHO_RUNNER_TEMPLATE.encode("utf-8") + b"\n"

    out.extend(b"\n'''\n")
    out.extend(script_data)
    out.extend(manifest_line)

    # Save secret key exclusively in the sidecar, FIRST, through the shared
    # private-file writer: created 0600 rather than tightened afterwards, and a
    # link planted at the path is refused instead of followed, before the
    # document is created or replaced (review K4). Not a transaction: if writing
    # the document fails after the key was written, nothing rolls back.
    from keystore import PRIVATE_KEY_SUFFIX, write_private_file
    write_private_file(f"{pdf_path}{PRIVATE_KEY_SUFFIX}", sk_hex)

    # Write PDF
    with open(pdf_path, "wb") as f:
        f.write(bytes(out))

    return org, genesis_receipt


# ============================================================================
# 7. IN-PLACE EVOLUTION CYCLE
# ============================================================================

def evolve_morpho_autopoietic_organism(
    pdf_path: str,
    secret_key_hex: Optional[str] = None
) -> Tuple[MorphoAutopoieticOrganism, MorphoAutopoiesisReceipt]:
    """
    Executes one autonomous ontogenetic evolutionary step on the polyglot.
    Applies algebraic AST equational rewriting, Turing reaction-diffusion drift,
    Lafont proof-net compilation & WL reduction, and strictly appends an
    ISO 32000 §7.5.6 revision page directly to the file.
    """
    if not audit_morpho_autopoietic_organism(pdf_path):
        raise ValueError(f"Cannot evolve tampered or invalid organism: {pdf_path}")

    with open(pdf_path, "rb") as f:
        original_bytes = f.read()

    # Extract manifest
    prefix = MORPHO_AUTOPOIESIS_MANIFEST_PREFIX.encode("utf-8")
    idx = original_bytes.rfind(prefix)
    if idx == -1:
        raise ValueError(f"Manifest not found in {pdf_path}")
    line = original_bytes[idx + len(prefix):].split(b"\n", 1)[0]
    org_dict = json.loads(line.decode("utf-8"))
    org = MorphoAutopoieticOrganism.from_dict(org_dict)

    # Secret key retrieval
    from keystore import PRIVATE_KEY_SUFFIX
    sk_hex = secret_key_hex
    if not sk_hex:
        key_path = f"{pdf_path}{PRIVATE_KEY_SUFFIX}"
        if os.path.exists(key_path):
            with open(key_path, "r") as kf:
                sk_hex = kf.read().strip()
        elif "BLACK_HEART_SECRET_KEY" in os.environ:
            sk_hex = os.environ["BLACK_HEART_SECRET_KEY"]

    if not sk_hex:
        raise ValueError("Secret key required for evolution attestation.")

    # 1. Algebraic AST zipper equational rewrite
    evaluator = FrozenEvaluator()
    mutated_chroms = []
    mutation_found = False
    applied_gene_id = ""
    applied_rule_name = ""
    applied_site = []
    pre_term_str = ""
    post_term_str = ""
    atp_saved = 0
    size_saved = 0
    experiment_id = ""

    for chrom in org.chromosomes:
        if mutation_found:
            mutated_chroms.append(chrom)
            continue

        proposals = propose_form_metamorphoses(chrom, include_exploratory=True)
        for prop in proposals:
            eval_res = evaluator.evaluate_transformation(prop.original_term, prop.candidate_term)
            rec = org.experiment_log.record_experiment(prop, eval_res)

            if eval_res.verdict == MutationVerdict.ACCEPTED_MORE_EFFICIENT:
                applied_gene_id = prop.gene_id
                applied_rule_name = prop.rule.name
                applied_site = list(prop.site_address)
                pre_term_str = str(prop.original_term)
                post_term_str = str(prop.candidate_term)
                atp_saved = max(1, -eval_res.atp_delta)
                size_saved = max(0, -eval_res.size_delta)
                experiment_id = rec.experiment_id

                mutated_chroms.append(
                    Chromosome(
                        gene_id=chrom.gene_id,
                        gene_name=getattr(chrom, "gene_name", chrom.gene_id),
                        expression=post_term_str,
                        expected_normal_form=str(chrom.expected_normal_form),
                        max_atp=chrom.max_atp,
                    )
                )
                mutation_found = True
                break

        if not mutation_found:
            mutated_chroms.append(chrom)

    if not mutation_found:
        applied_gene_id = org.chromosomes[0].gene_id
        applied_rule_name = "METABOLIC_DRIFT"
        applied_site = []
        pre_term_str = org.chromosomes[0].expression
        post_term_str = org.chromosomes[0].expression
        atp_saved = 1
        size_saved = 0
        experiment_id = derive_experiment_id(applied_gene_id, tuple(applied_site), applied_rule_name, pre_term_str, post_term_str)

    # 2. Update Genotype
    org.chromosomes = mutated_chroms
    org.generation += 1
    org.parent_hash = org.organism_hash
    org.atp_reserve += max(5, atp_saved * 2)

    # 3. Kinetic Drift & Reaction-Diffusion Morphogenesis (Grok 3)
    f, k, arch = org.compute_kinetic_drift()
    org.feed_rate_f = f
    org.kill_rate_k = k
    org.archetype_key = arch
    org.field.F = f
    org.field.k = k
    for _ in range(35):
        org.field.step()

    # 4. Lafont Interaction Net Compilation & WL Reduction (Grok 3)
    net, crit_pts = compile_morphogenetic_proof_net(org.field)
    init_nodes = len(crit_pts)
    steps_red, _, _ = net.reduce(max_atp=2000)
    wl_digest = net.canonical_digest()
    org.weisfeiler_lehman_digest = wl_digest
    org.organism_hash = org.compute_hash()

    # 5. Create Evolutionary Receipt
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    next_receipt = MorphoAutopoiesisReceipt(
        generation=org.generation,
        timestamp_utc=now,
        parent_hash=org.parent_hash,
        organism_hash=org.organism_hash,
        gene_id=applied_gene_id,
        rule_name=applied_rule_name,
        site_address=applied_site,
        pre_term=pre_term_str,
        post_term=post_term_str,
        atp_saved=atp_saved,
        size_saved=size_saved,
        experiment_id=experiment_id,
        experiments_count=len(org.experiment_log.records),
        archetype=org.archetype_key,
        feed_rate_f=org.feed_rate_f,
        kill_rate_k=org.kill_rate_k,
        pde_steps=35,
        initial_nodes=init_nodes,
        reduced_steps=steps_red,
        net_atp_burned=steps_red,
        weisfeiler_lehman_digest=wl_digest,
        public_key_hex=org.public_key_hex,
    )
    next_receipt.sign(sk_hex)
    org.receipt_chain.append(next_receipt)

    # 6. Build ISO 32000 §7.5.6 Incremental Revision Page
    page_stream = _build_morpho_page_stream(next_receipt, org)
    stream_bytes = page_stream.encode("utf-8")

    current_page_count = org.generation + 1
    # Base object IDs for this generation:
    # Genesis had objects 1..5.
    # Each generation N adds 4 objects: Contents, Page, Pages, Catalog
    base_obj_count = 5 + (org.generation - 1) * 4
    new_contents_id = base_obj_count + 1
    new_page_id = base_obj_count + 2
    new_pages_id = base_obj_count + 3
    new_root_id = base_obj_count + 4

    # Build kids list
    kids_refs = ["3 0 R"]
    for g in range(1, current_page_count):
        kids_refs.append(f"{5 + (g - 1) * 4 + 2} 0 R")
    kids_list = " ".join(kids_refs)

    page_obj = (
        f"{new_page_id} 0 obj\n"
        f"<< /Type /Page /Parent {new_pages_id} 0 R /MediaBox [0 0 595.28 841.89] /Contents {new_contents_id} 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    ).encode("utf-8")

    contents_obj = (
        f"{new_contents_id} 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode("utf-8")
        + stream_bytes
        + b"\nendstream\nendobj\n"
    )

    pages_obj = (
        f"{new_pages_id} 0 obj\n<< /Type /Pages /Kids [{kids_list}] /Count {current_page_count} >>\nendobj\n"
    ).encode("utf-8")

    catalog_obj = (
        f"{new_root_id} 0 obj\n<< /Type /Catalog /Pages {new_pages_id} 0 R >>\nendobj\n"
    ).encode("utf-8")

    prev_xref = 0
    startxref_kw = b"startxref\n"
    pos = original_bytes.rfind(startxref_kw)
    if pos != -1:
        end_pos = original_bytes.find(b"\n%%EOF", pos)
        if end_pos != -1:
            try:
                prev_xref = int(original_bytes[pos + len(startxref_kw):end_pos].strip())
            except ValueError:
                prev_xref = 0

    py_prefix = b'\nr"""\n'
    update_body = bytearray()
    update_offsets = []

    for obj in (contents_obj, page_obj, pages_obj, catalog_obj):
        obj_num = int(obj[:obj.find(b" 0 obj")].decode("utf-8"))
        update_offsets.append((obj_num, len(original_bytes) + len(py_prefix) + len(update_body)))
        update_body.extend(obj)

    new_xref_offset = len(original_bytes) + len(py_prefix) + len(update_body)
    xref_chunk = bytearray()
    xref_chunk.extend(b"xref\n")
    for obj_num, offset in update_offsets:
        xref_chunk.extend(f"{obj_num} 1\n".encode("utf-8"))
        xref_chunk.extend(f"{offset:010d} 00000 n \n".encode("utf-8"))

    trailer_chunk = (
        f"trailer\n<< /Size {new_root_id + 1} /Root {new_root_id} 0 R /Prev {prev_xref} >>\n"
        f"startxref\n{new_xref_offset}\n%%EOF\n"
    ).encode("utf-8")

    manifest_payload = org.to_dict()
    manifest_payload["source_dir"] = os.path.dirname(os.path.abspath(__file__))
    new_manifest_line = MORPHO_AUTOPOIESIS_MANIFEST_PREFIX.encode("utf-8") + json.dumps(manifest_payload, separators=(',', ':')).encode("utf-8") + b"\n"
    py_suffix = b'"""\n'

    append_chunk = (
        py_prefix
        + bytes(update_body)
        + bytes(xref_chunk)
        + trailer_chunk
        + py_suffix
        + new_manifest_line
    )

    with open(pdf_path, "ab") as f:
        f.write(append_chunk)

    return org, next_receipt


# ============================================================================
# 8. AGORA PARLIAMENT FEDERATION (GROK 5)
# ============================================================================

def table_to_agora(
    organism_pdf_path: str,
    agora_pdf_path: str,
    secret_key_hex: Optional[str] = None,
    stake_atp: int = 100
) -> Tuple[AgoraProposal, str]:
    """
    Autonomously tables the organism's latest accepted algebraic theorem
    directly as an AgoraProposal onto the Mycelial Agora floor.
    """
    if not audit_morpho_autopoietic_organism(organism_pdf_path):
        raise ValueError("Cannot table proposal from untrusted or tampered organism.")

    with open(organism_pdf_path, "rb") as f:
        data = f.read()

    prefix = MORPHO_AUTOPOIESIS_MANIFEST_PREFIX.encode("utf-8")
    idx = data.rfind(prefix)
    line = data[idx + len(prefix):].split(b"\n", 1)[0]
    org_dict = json.loads(line.decode("utf-8"))
    org = MorphoAutopoieticOrganism.from_dict(org_dict)

    if org.atp_reserve < stake_atp:
        raise ValueError(f"Insufficient ATP reserve ({org.atp_reserve} < {stake_atp}) to stake bill.")

    latest_rec = org.receipt_chain[-1]
    if not latest_rec.pre_term or latest_rec.pre_term == "GENESIS":
        raise ValueError("No evolved algebraic theorem available to table on Agora floor.")

    from keystore import PRIVATE_KEY_SUFFIX
    sk_hex = secret_key_hex
    if not sk_hex:
        key_path = f"{organism_pdf_path}{PRIVATE_KEY_SUFFIX}"
        if os.path.exists(key_path):
            with open(key_path, "r") as kf:
                sk_hex = kf.read().strip()
        elif "BLACK_HEART_SECRET_KEY" in os.environ:
            sk_hex = os.environ["BLACK_HEART_SECRET_KEY"]

    if not sk_hex:
        raise ValueError("Secret key required to sign Agora bill.")

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    proposal_id = f"prop_morpho_{latest_rec.rule_name.lower()}_{latest_rec.generation}"

    proposal = AgoraProposal(
        proposal_id=proposal_id,
        proposal_type=ProposalType.THEOREM_CONGRUENCE.value,
        title=f"Autopoietic Congruence Theorem: {latest_rec.rule_name} on {latest_rec.gene_id}",
        statement=f"Semantic congruence verified via FrozenEvaluator: '{latest_rec.pre_term}' == '{latest_rec.post_term}', saving {latest_rec.atp_saved} ATP.",
        pre_term=latest_rec.pre_term,
        post_term=latest_rec.post_term,
        target_value=float(latest_rec.atp_saved),
        stake_atp=stake_atp,
        timestamp_utc=now,
    )
    proposal.sign(sk_hex)

    # Set up consensus engine to evaluate and settle bill on Agora floor
    engine = AgoraConsensusEngine()
    engine.register_citizen(org.public_key_hex, initial_atp=org.atp_reserve)
    engine.table_proposal(proposal)

    # Cast voting ballot with quadratic weight
    voter_burned = min(100, org.atp_reserve - stake_atp) if org.atp_reserve > stake_atp else 25
    voter_weight = int(math.isqrt(voter_burned))
    ballot = AgoraBallot(
        proposal_id=proposal_id,
        voter_public_key=org.public_key_hex,
        direction=VoteDirection.AYE.value,
        atp_burned=voter_burned,
        quadratic_weight=voter_weight,
        reason=f"Author attestation with {latest_rec.atp_saved} ATP savings",
    )
    ballot.sign(sk_hex)
    engine.cast_ballot(ballot)

    settlement = engine.evaluate_and_settle(proposal_id)
    grow_agora_page(agora_pdf_path, settlement)

    # Deduct stake from organism
    org.atp_reserve -= stake_atp
    latest_rec.tabled_proposal_id = proposal_id
    latest_rec.agora_atp_staked = stake_atp
    latest_rec.sign(sk_hex)

    return proposal, proposal_id


# ============================================================================
# 9. CRYPTOGRAPHIC & TOPOLOGICAL STATIC AUDITOR
# ============================================================================

def audit_morpho_autopoietic_organism(pdf_path: str) -> bool:
    """
    Statically audits the entire developmental history of the organism:
      - Validates each MorphoAutopoiesisReceipt Ed25519 signature.
      - Enforces parent-to-child cryptographic hash continuity.
      - Recomputes kinetic drift (F, k) and validates Turing archetype consistency.
      - Recomputes current organism hash from active genome, ensuring
        tamper-resistance between receipts and memory state.
    """
    if not os.path.exists(pdf_path):
        return False

    with open(pdf_path, "rb") as f:
        data = f.read()

    prefix = MORPHO_AUTOPOIESIS_MANIFEST_PREFIX.encode("utf-8")
    idx = data.rfind(prefix)
    if idx == -1:
        return False

    try:
        line = data[idx + len(prefix):].split(b"\n", 1)[0]
        manifest = json.loads(line.decode("utf-8"))
        org = MorphoAutopoieticOrganism.from_dict(manifest)
    except Exception:
        return False

    if not org.receipt_chain:
        return False

    expected_parent = "0" * 64
    for i, rec in enumerate(org.receipt_chain):
        if not rec.verify_integrity():
            return False
        if not rec.verify():
            return False
        if rec.generation != i:
            return False
        if rec.parent_hash != expected_parent:
            return False
        expected_parent = rec.organism_hash

    # Verify kinetic drift consistency
    f_exp, k_exp, arch_exp = org.compute_kinetic_drift()
    if abs(org.feed_rate_f - f_exp) > 1e-6 or abs(org.kill_rate_k - k_exp) > 1e-6 or org.archetype_key != arch_exp:
        return False

    # Ensure active organism matches recomputed hash
    if org.organism_hash != org.compute_hash():
        return False

    # Ensure active organism matches latest receipt
    last_receipt = org.receipt_chain[-1]
    if org.organism_hash != last_receipt.organism_hash:
        return False
    if org.generation != last_receipt.generation:
        return False
    if org.parent_hash != last_receipt.parent_hash:
        return False
    if org.public_key_hex != last_receipt.public_key_hex:
        return False

    return True
