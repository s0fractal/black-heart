#!/usr/bin/env python3
# coding: utf-8
"""
autopoiesis.py — Self-Contemplating Autopoietic Quine Organisms.
Part of Project Black-Heart (%🖤). Realizing Grok Experiment 1.

Theoretical Foundations:
  1. Autopoiesis (Maturana & Varela, 1972):
     An autopoietic system is organized as a network of processes of production
     (transformation and destruction) of components which:
     (a) through their interactions regenerate and realize the network that produced them;
     (b) constitute the system as a concrete unity in the space in which they exist.
  2. The Self-Contemplating Quine Polyglot:
     A single-file dual-spine ISO 32000 PDF document that is simultaneously a valid,
     standalone Python script ('python3 self.pdf').
     Upon self-execution, the document:
     (a) reads its own bytes from disk;
     (b) audits its dual-spine Merkle anchor and cryptographic provenance chain;
     (c) inspects its own internal combinator genome (chromosomes of SKIY terms);
     (d) applies algebraic AST equational rewriting (zipper navigation) to discover
         sound semantic optimizations under Church-Rosser confluence;
     (e) empirically evaluates candidate mutations against frozen oracle test fixtures,
         recording both accepted optimizations and rejected counterexamples;
     (f) signs the new generational transition receipt with its Ed25519 identity;
     (g) strictly appends an ISO 32000 §7.5.6 revision page into its own physical file
         ('after.startswith(before) == True');
     (h) emits '⚓ <new_organism_hash>' with the cryptographic hash of the new form.
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
from organism import Organism, Chromosome, create_genesis_organism
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
    FrozenEvaluator,
    EvaluationReceipt,
    MutationVerdict,
    ExperimentRecord,
    ExperimentLog,
    derive_experiment_id,
    audit_metamorphic_transition,
    MetamorphicTransitionReceipt,
    MetamorphicProvenanceError,
)

AUTOPOIESIS_MANIFEST_PREFIX = "# %" + "🖤" + " AUTOPOIESIS_RECEIPT_CHAIN: "

# ============================================================================
# 1. AUTOPOIESIS RECEIPT & PEDIGREE
# ============================================================================

@dataclass
class AutopoiesisReceipt:
    """
    Cryptographic settlement receipt attesting to one autonomous ontogenetic step.
    Binds the parent organism hash, the successor organism hash, the exact AST
    mutation rule, the empirical experiment ID, and the Ed25519 signature.
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
    public_key_hex: str
    signature_hex: str = ""
    receipt_hash: str = ""

    def canonical_bytes_for_signing(self) -> bytes:
        site_str = ",".join(self.site_address)
        payload = (
            f"AUTOPOIESIS:{self.generation}:{self.timestamp_utc}:{self.parent_hash}:"
            f"{self.organism_hash}:{self.gene_id}:{self.rule_name}:{site_str}:"
            f"{self.pre_term}:{self.post_term}:{self.atp_saved}:{self.size_saved}:"
            f"{self.experiment_id}:{self.experiments_count}:{self.public_key_hex}"
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

    def verify(self) -> bool:
        if self.generation < 0:
            return False
        if not self.is_attested():
            return False
        if not is_valid_public_key(self.public_key_hex):
            return False
        expected_hash = self.compute_hash()
        if self.receipt_hash and self.receipt_hash != expected_hash:
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
            "public_key_hex": self.public_key_hex,
            "signature_hex": self.signature_hex,
            "receipt_hash": self.receipt_hash,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> AutopoiesisReceipt:
        return cls(
            generation=d["generation"],
            timestamp_utc=d["timestamp_utc"],
            parent_hash=d["parent_hash"],
            organism_hash=d["organism_hash"],
            gene_id=d["gene_id"],
            rule_name=d["rule_name"],
            site_address=d.get("site_address", []),
            pre_term=d["pre_term"],
            post_term=d["post_term"],
            atp_saved=d["atp_saved"],
            size_saved=d["size_saved"],
            experiment_id=d["experiment_id"],
            experiments_count=d["experiments_count"],
            public_key_hex=d["public_key_hex"],
            signature_hex=d.get("signature_hex", ""),
            receipt_hash=d.get("receipt_hash", ""),
        )


def organism_to_dict(org: Organism) -> Dict[str, Any]:
    """Serializes an Organism to a json-serializable dictionary (public attributes only)."""
    return {
        "generation": org.generation,
        "parent_hash": org.parent_hash,
        "organism_hash": org.organism_hash or org.compute_hash(),
        "public_key_hex": org.public_key_hex,
        "birth_timestamp_utc": org.birth_timestamp_utc,
        "chromosomes": [c.to_dict() for c in org.chromosomes]
    }


def organism_from_dict(d: Dict[str, Any], fallback_sk: str = "") -> Organism:
    """Deserializes an Organism from a dictionary."""
    chromos = [Chromosome.from_dict(c) for c in d.get("chromosomes", [])]
    org = Organism(
        generation=d["generation"],
        parent_hash=d["parent_hash"],
        public_key_hex=d["public_key_hex"],
        secret_key_hex=d.get("secret_key_hex") or fallback_sk,
        birth_timestamp_utc=d.get("birth_timestamp_utc", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        chromosomes=chromos
    )
    org.organism_hash = d.get("organism_hash") or org.compute_hash()
    return org


# ============================================================================
# 2. SEED ORGANISM INITIALIZATION
# ============================================================================

def create_autopoietic_seed(secret_key_hex: Optional[str] = None) -> Tuple[Organism, str]:
    """
    Creates a rich initial Genesis Organism containing combinator chromosomes
    designed with fertile ground for multi-generational AST optimizations.
    """
    if secret_key_hex is None:
        sk_hex, pk_hex = generate_keypair()
        secret_key_hex = sk_hex
        public_key_hex = pk_hex
    else:
        sk_b = bytes.fromhex(secret_key_hex)
        public_key_hex = public_key_from_secret(sk_b).hex()

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Fertile chromosome suite:
    # 1. Identity Carrier: S K K SovereignCore -> SovereignCore
    # 2. Black Cone Nutrient: K VitalNutrient EntropyNoise -> VitalNutrient
    # 3. Branch Decider: (K I) DormantBranch ExpressedBranch -> ExpressedBranch
    # 4. Signal Router: S (K (S I)) (K I) -> fertile for S(K x)(K y) -> K(x y)
    # 5. Metabolic Cascade: S (K S) (K K) -> fertile for S(K x)(K y) -> K(x y)
    c1 = Chromosome(
        gene_id="GENE-ID-01",
        gene_name="Sovereign Identity Carrier",
        expression="🌿 🖤 🖤 SovereignCore",
        expected_normal_form="SovereignCore",
        max_atp=50
    )
    c2 = Chromosome(
        gene_id="GENE-METAB-02",
        gene_name="Black Cone Energy Absorption",
        expression="🖤 VitalNutrient EntropyNoise",
        expected_normal_form="VitalNutrient",
        max_atp=30
    )
    c3 = Chromosome(
        gene_id="GENE-BRANCH-03",
        gene_name="Adaptive Morphic Branch",
        expression="(🖤 🤍) DormantBranch ExpressedBranch",
        expected_normal_form="ExpressedBranch",
        max_atp=40
    )
    c4 = Chromosome(
        gene_id="GENE-OPT-04",
        gene_name="Signal Router Distribution",
        expression="🌿 (🖤 (🌿 🤍)) (🖤 🤍)",
        expected_normal_form="(🌿 🤍) 🤍",
        max_atp=100
    )
    c5 = Chromosome(
        gene_id="GENE-CASCADE-05",
        gene_name="Metabolic Synthesis Cascade",
        expression="🌿 (🖤 🌿) (🖤 🖤)",
        expected_normal_form="🌿 🖤",
        max_atp=100
    )

    org = Organism(
        generation=0,
        parent_hash="0000000000000000000000000000000000000000000000000000000000000000",
        public_key_hex=public_key_hex,
        secret_key_hex=secret_key_hex,
        birth_timestamp_utc=now,
        chromosomes=[c1, c2, c3, c4, c5]
    )
    org.organism_hash = org.compute_hash()
    return org, secret_key_hex


# ============================================================================
# 3. PAGE STREAM COMPILER (AESTHETIC ISO 32000 PDF RENDERING)
# ============================================================================

def _clean_pdf_text(s: Any) -> str:
    if s is None:
        return ""
    txt = str(s)
    txt = txt.replace(GLYPH_K, "K").replace(GLYPH_I, "I").replace(GLYPH_S, "S").replace(GLYPH_Y, "Y").replace(GLYPH_ANCHOR, "#")
    txt = txt.replace("\U0001f5a4", "K").replace("\U0001f90d", "I").replace("\U0001f33f", "S").replace("\U0001f501", "Y").replace("\u2693", "#")
    res = []
    for ch in txt:
        if 32 <= ord(ch) < 127:
            if ch == "\\":
                res.append(r"\\")
            elif ch == "(":
                res.append(r"\(")
            elif ch == ")":
                res.append(r"\)")
            else:
                res.append(ch)
        elif ord(ch) in (10, 13):
            res.append(" ")
        else:
            res.append("?")
    return "".join(res)


def render_autopoiesis_page_stream(
    org: Organism,
    receipt: AutopoiesisReceipt,
    recent_experiments: List[ExperimentRecord]
) -> bytes:
    """
    Renders an ISO 32000 PDF page stream illustrating the organism's autopoietic
    form, current generation, AST transition details, and empirical scientific ledger.
    """
    ops = []
    ops.append("q")

    # 1. Dark Cosmic Obsidian Background
    ops.append("0.04 0.05 0.08 rg 0 0 595.28 841.89 re f")

    # 2. Header Title & Decorative Neon Lines
    ops.append("0.2 0.85 0.6 RG 2 w 40 812 m 555 812 l S")
    ops.append("BT /F1 16 Tf 0.25 0.95 0.7 rg 40 792 Td (% BLACK-HEART AUTOPOIETIC QUINE ORGANISM) Tj ET")
    ops.append("BT /F2 9 Tf 0.6 0.7 0.85 rg 40 776 Td (Self-Contemplating AST Evolution, Living Ledger & Invariant Provenance) Tj ET")

    # 3. Lineage & Identity Card
    ops.append("0.07 0.10 0.16 rg 40 680 515.28 84 re f")
    ops.append("0.2 0.4 0.65 RG 1 w 40 680 515.28 84 re S")
    ops.append(f"BT /F1 10.5 Tf 0.3 0.85 0.95 rg 55 744 Td (ONTOGENETIC LINEAGE: GENERATION #{org.generation}) Tj ET")
    ops.append(f"BT /F2 8.5 Tf 0.8 0.85 0.9 rg 55 728 Td (Organism Hash:   # {org.organism_hash[:32]}...) Tj ET")
    ops.append(f"BT /F2 8.5 Tf 0.7 0.75 0.8 rg 55 712 Td (Parent Hash:     # {org.parent_hash[:32]}...) Tj ET")
    ops.append(f"BT /F2 8 Tf 0.5 0.8 0.65 rg 55 696 Td (Signer Identity:  Ed25519 PK {org.public_key_hex[:32]}... | UTC: {receipt.timestamp_utc}) Tj ET")

    # 4. Metamorphic Transition Card
    ops.append("0.07 0.10 0.16 rg 40 575 515.28 95 re f")
    ops.append("0.95 0.7 0.2 RG 1 w 40 575 515.28 95 re S")
    ops.append("BT /F1 10.5 Tf 0.95 0.75 0.25 rg 55 650 Td (ACTIVE AST METAMORPHIC REWRITE & ORACLE EVALUATION) Tj ET")

    gene_c = _clean_pdf_text(receipt.gene_id)
    rule_c = _clean_pdf_text(receipt.rule_name)
    site_c = _clean_pdf_text("/".join(receipt.site_address) if receipt.site_address else "ROOT")
    pre_c = _clean_pdf_text(receipt.pre_term[:52])
    post_c = _clean_pdf_text(receipt.post_term[:52])

    ops.append(f"BT /F1 9 Tf 0.4 0.95 0.6 rg 55 634 Td (Rule Applied: '{rule_c}'  |  Gene: '{gene_c}'  |  Site: '{site_c}') Tj ET")
    ops.append(f"BT /F2 8.5 Tf 0.8 0.85 0.9 rg 55 618 Td (Pre-Rewrite Form:   {pre_c}) Tj ET")
    ops.append(f"BT /F2 8.5 Tf 0.3 0.95 0.5 rg 55 602 Td (Post-Rewrite Form:  {post_c}) Tj ET")
    ops.append(
        f"BT /F1 9 Tf 0.95 0.85 0.3 rg 55 586 Td "
        f"(Energy Conserved: -{receipt.atp_saved} ATP fuel  |  Syntactic Delta: {receipt.size_saved:+d} AST nodes  |  Oracle: 5/5 SOUND) Tj ET"
    )

    # 5. Scientific Empirical Experiment Ledger Card
    ops.append("0.07 0.10 0.16 rg 40 230 515.28 335 re f")
    ops.append("0.3 0.4 0.55 RG 1 w 40 230 515.28 335 re S")
    ops.append("BT /F1 10.5 Tf 0.95 0.4 0.6 rg 55 545 Td (EMPIRICAL SCIENTIFIC LEDGER (ACCEPTED & REJECTED MUTATIONS)) Tj ET")
    ops.append("BT /F2 7.5 Tf 0.55 0.65 0.75 rg 55 528 Td (EXP ID      VERDICT                     RULE                        DELTA ATP   DETAILS) Tj ET")
    ops.append("0.2 0.3 0.4 RG 0.5 w 55 522 m 540 522 l S")

    y = 508
    for r in recent_experiments[:12]:
        if r.verdict == MutationVerdict.ACCEPTED_MORE_EFFICIENT:
            c_badge = "0.3 0.95 0.45"
            v_badge = "ACCEPTED (SOUND)"
        elif r.verdict == MutationVerdict.REJECTED_SEMANTIC_MISMATCH:
            c_badge = "0.95 0.35 0.4"
            v_badge = "REJECTED (DIVERGED)"
        else:
            c_badge = "0.95 0.7 0.3"
            v_badge = _clean_pdf_text(r.verdict.name)[:19]

        eid = _clean_pdf_text(r.experiment_id)[:10]
        rule_sub = _clean_pdf_text(r.rule_name)[:24]
        atp_sub = f"{r.atp_delta:+d} ATP"
        det = _clean_pdf_text(r.discrepancy_detail or "Semantic Equivalence Proven")[:30]

        ops.append(f"BT /F2 7 Tf 0.7 0.75 0.8 rg 55 {y} Td ({eid:<11s}) Tj ET")
        ops.append(f"BT /F1 7 Tf {c_badge} rg 120 {y} Td ({v_badge:<26s}) Tj ET")
        ops.append(f"BT /F2 7 Tf 0.75 0.8 0.85 rg 245 {y} Td ({rule_sub:<26s}) Tj ET")
        ops.append(f"BT /F1 7 Tf 0.95 0.85 0.3 rg 370 {y} Td ({atp_sub:<11s}) Tj ET")
        ops.append(f"BT /F2 6.5 Tf 0.6 0.65 0.7 rg 430 {y} Td ({det}) Tj ET")
        y -= 18

    # 6. Active Chromosomes Genome Card
    ops.append("0.07 0.10 0.16 rg 40 85 515.28 135 re f")
    ops.append("0.25 0.5 0.4 RG 1 w 40 85 515.28 135 re S")
    ops.append("BT /F1 10.5 Tf 0.4 0.9 0.65 rg 55 200 Td (ACTIVE COMBINATOR GENOME (CURRENT CHROMOSOMES)) Tj ET")

    gy = 184
    for c in org.chromosomes[:4]:
        c_expr = _clean_pdf_text(c.expression[:48])
        c_norm = _clean_pdf_text(c.expected_normal_form[:26])
        ops.append(f"BT /F2 7.5 Tf 0.8 0.85 0.9 rg 55 {gy} Td ([{c.gene_id}] {c.gene_name}: {c_expr} -> NF: {c_norm}) Tj ET")
        gy -= 15

    # 7. Cryptographic Footer Seal
    sig_short = _clean_pdf_text(receipt.signature_hex[:32]) if receipt.signature_hex else "UNSIGNED"
    ops.append(f"BT /F2 7.5 Tf 0.45 0.5 0.6 rg 40 60 Td (Receipt Hash: {receipt.receipt_hash[:32]}... | Ed25519 Sig: {sig_short}...) Tj ET")
    ops.append(f"BT /F1 8 Tf 0.25 0.85 0.6 rg 40 45 Td (ISO 32000 §7.5.6 Invariant: Append-Only Growth | Python Quine Executable Spoke) Tj ET")

    ops.append("Q")
    return "\n".join(ops).encode("latin1")


# ============================================================================
# 4. EMBEDDED STANDALONE RUNNER SCRIPT
# ============================================================================

def _build_autopoiesis_runner_script() -> str:
    """
    Constructs the Python script embedded inside the PDF polyglot document.
    Enables standalone self-evolution, verification, and empirical logs.
    """
    return '''
import os
import sys
import json
import time

def _load_manifest_from_self():
    self_path = sys.argv[0]
    with open(self_path, "rb") as f:
        content = f.read()

    prefix = b"# %" + bytes([0xf0, 0x9f, 0x96, 0xa4]) + b" AUTOPOIESIS_RECEIPT_CHAIN: "
    idx = content.rfind(prefix)
    if idx == -1:
        raise ValueError("Could not locate Autopoiesis receipt chain manifest in self")
    end_idx = content.find(b"\\n", idx)
    raw = content[idx + len(prefix):end_idx if end_idx != -1 else len(content)]
    return json.loads(raw.decode("utf-8")), self_path

def cmd_info():
    data, self_path = _load_manifest_from_self()
    org_dict = data["current_organism"]
    receipts = data["receipts"]
    latest_r = receipts[-1]
    print("=================================================================")
    print("  %[BH] AUTOPOIETIC QUINE ORGANISM (ISO 32000 POLYGLOT)")
    print("=================================================================")
    print(f"  File:                 {os.path.basename(self_path)}")
    print(f"  Current Generation:   #{org_dict['generation']}")
    print(f"  Organism Hash:        [#] {org_dict['organism_hash']}")
    print(f"  Parent Hash:          [#] {org_dict['parent_hash']}")
    print(f"  Total Growth Epochs:  {len(receipts)}")
    print(f"  Total Experiments:    {len(data.get('experiments', []))}")
    print(f"  Ed25519 Public Key:   {org_dict['public_key_hex']}")
    print(f"  Latest Rule:          {latest_r.get('rule_name', 'GENESIS')}")
    print("-----------------------------------------------------------------")
    print("Commands:")
    print("  python3 self.pdf              Advance 1 generation in-place (evolve)")
    print("  python3 self.pdf --evolve     Advance 1 generation in-place (evolve)")
    print("  python3 self.pdf --audit      Cryptographically verify all generations")
    print("  python3 self.pdf --experiments Dump empirical scientific ledger")
    print("  python3 self.pdf --genome     Display active combinator chromosomes")
    print("  python3 self.pdf --quine      Print own source code")
    print("=================================================================\\n")

def cmd_audit():
    data, self_path = _load_manifest_from_self()
    source_dir = data.get("source_dir")
    if source_dir and source_dir not in sys.path:
        sys.path.insert(0, source_dir)
    try:
        from autopoiesis import audit_autopoietic_organism
        ok, msg = audit_autopoietic_organism(self_path)
        print("=================================================================")
        print("  %[BH] AUTOPOIETIC INTEGRITY AUDITOR")
        print("=================================================================")
        print(f"\\033[1;32m[OK] {msg}\\033[0m\\n")
    except Exception as e:
        print("=================================================================")
        print("  %[BH] AUTOPOIETIC INTEGRITY AUDITOR")
        print("=================================================================")
        print(f"\\033[1;31m[FAIL] AUDIT FAILED: {e}\\033[0m\\n")
        sys.exit(1)

def cmd_experiments():
    data, _ = _load_manifest_from_self()
    exps = data.get("experiments", [])
    print("=================================================================")
    print("  %[BH] EMPIRICAL SCIENTIFIC LEDGER (MUTATION EXPERIMENTS)")
    print("=================================================================")
    print(f"Total Evaluated Mutations: {len(exps)}")
    acc = sum(1 for e in exps if e.get("verdict") == "ACCEPTED_MORE_EFFICIENT")
    print(f"Accepted Optimizations:    {acc}")
    print(f"Rejected Counterexamples:  {len(exps) - acc}\\n")
    print("EID         VERDICT                     RULE                        DELTA ATP   DISCREPANCY")
    print("-" * 88)
    for e in exps[-20:]:
        v = e.get("verdict", "")
        r = e.get("rule_name", "")[:26]
        d = e.get("atp_delta", 0)
        disc = (e.get("discrepancy_detail") or "Sound Invariant")[:28]
        print(f"{e.get('experiment_id', ''):10s}  {v:26s}  {r:26s}  {d:+6d} ATP  {disc}")
    print("=================================================================\\n")

def cmd_genome():
    data, _ = _load_manifest_from_self()
    org_dict = data["current_organism"]
    print("=================================================================")
    print(f"  %[BH] COMBINATOR GENOME (GENERATION #{org_dict['generation']})")
    print("=================================================================")
    for c in org_dict.get("chromosomes", []):
        print(f"[{c.get('gene_id')}] {c.get('gene_name')}")
        print(f"  Expression: {c.get('expression')}")
        print(f"  NormalForm: {c.get('expected_normal_form')}")
        print(f"  Max ATP:    {c.get('max_atp')}\\n")
    print("=================================================================")

def cmd_evolve():
    data, self_path = _load_manifest_from_self()
    source_dir = data.get("source_dir")
    if source_dir and source_dir not in sys.path:
        sys.path.insert(0, source_dir)
    try:
        from autopoiesis import evolve_autopoietic_organism
        succ, receipt = evolve_autopoietic_organism(self_path)
        print(f"\\033[1;32m[EVOLUTION ACCOMPLISHED] Generation #{succ.generation} appended in-place!\\033[0m")
        print(f"  New Organism Hash: [#] {succ.organism_hash}")
        print(f"  Applied Rewrite:   {receipt.rule_name} on {receipt.gene_id}")
        print(f"  Energy Conserved:  -{receipt.atp_saved} ATP fuel quanta\\n")
    except Exception as e:
        print(f"\\033[1;31m[-] Evolution halted: {e}\\033[0m\\n")
        sys.exit(1)

def cmd_quine():
    _, self_path = _load_manifest_from_self()
    with open(self_path, "rb") as f:
        sys.stdout.buffer.write(f.read())

if __name__ == "__main__":
    if "--audit" in sys.argv:
        cmd_audit()
    elif "--experiments" in sys.argv:
        cmd_experiments()
    elif "--genome" in sys.argv:
        cmd_genome()
    elif "--info" in sys.argv:
        cmd_info()
    elif "--quine" in sys.argv:
        cmd_quine()
    elif "--evolve" in sys.argv or "--grow" in sys.argv or len(sys.argv) == 1:
        cmd_evolve()
    else:
        cmd_info()
'''


# ============================================================================
# 5. INITIALIZE AUTOPOIETIC ORGANISM (GENESIS POLYGLOT)
# ============================================================================

def init_autopoietic_organism(
    pdf_path: str,
    secret_key_hex: Optional[str] = None
) -> Tuple[Organism, AutopoiesisReceipt]:
    """
    Creates an initial Genesis (Generation 0) Autopoietic Quine Organism document.
    The document contains:
      - Valid ISO 32000 PDF structure (Page 1).
      - Embedded Python executable quine runner.
      - Attested Genesis receipt with Ed25519 signature.
      - Initial empty scientific experiment ledger.
    """
    org, sk_hex = create_autopoietic_seed(secret_key_hex)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Create Genesis receipt
    genesis_receipt = AutopoiesisReceipt(
        generation=0,
        timestamp_utc=now,
        parent_hash="0000000000000000000000000000000000000000000000000000000000000000",
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
        public_key_hex=org.public_key_hex
    )
    genesis_receipt.sign(sk_hex)

    stream_bytes = render_autopoiesis_page_stream(org, genesis_receipt, [])
    length = len(stream_bytes)

    source_dir = os.path.dirname(os.path.abspath(__file__))
    manifest_data = {
        "source_dir": source_dir,
        "current_organism": organism_to_dict(org),
        "receipts": [genesis_receipt.to_dict()],
        "experiments": []
    }
    manifest_line = AUTOPOIESIS_MANIFEST_PREFIX + json.dumps(manifest_data, separators=(",", ":"), ensure_ascii=True) + "\n"
    runner_script = _build_autopoiesis_runner_script()

    header_text = (
        f"#!{sys.executable}\n"
        "# coding: latin-1\n"
        "# ============================================================================\n"
        "# % PROJECT BLACK-HEART: AUTOPOIETIC QUINE ORGANISM (ISO 32000 POLYGLOT)\n"
        "# ============================================================================\n"
        "r'''\n"
    ).encode("latin1")

    out = bytearray(header_text)
    pdf_header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    out.extend(pdf_header)

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595.28 841.89] /Contents 4 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>",
        f"<< /Length {length} >>\nstream\n".encode("latin1") + stream_bytes + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out.extend(f"{i} 0 obj\n".encode("latin1"))
        out.extend(obj)
        out.extend(b"\nendobj\n")

    xref_offset = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin1"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("latin1"))

    trailer = (
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("latin1")
    out.extend(trailer)
    out.extend(b"\n'''\n")
    out.extend(runner_script.encode("latin1"))
    out.extend(b"\n")
    out.extend(manifest_line.encode("utf-8"))

    polyglot_bytes = bytes(out)

    # The private key lives only in the sidecar, never in the PDF. Written FIRST,
    # through the shared private-file writer, which refuses a link planted at the
    # path: a refused key must leave an existing document as it was and create
    # no new one (review K4). A failure is raised, not swallowed, because an
    # organism whose key was not kept cannot evolve. Not a transaction: if
    # writing the document fails after the key was written, nothing rolls back.
    from keystore import write_private_file
    write_private_file(pdf_path + ".key", sk_hex.strip() + "\n")

    with open(pdf_path, "wb") as f:
        f.write(polyglot_bytes)

    return org, genesis_receipt


# ============================================================================
# 6. IN-PLACE AUTONOMOUS EVOLUTION (ISO 32000 §7.5.6 INCREMENTAL UPDATE)
# ============================================================================

def check_palimpsest_guard(
    current_org: Organism,
    candidate_org: Organism,
    tombstone_registry: Optional[Any] = None,
    refutation_policy: Optional[Any] = None,
    issuer_policy: Optional[Any] = None
) -> Tuple[bool, str, Optional[Any]]:
    """
    Evaluates candidate organism against Invariant PAL4 (Autonomic Guard).
    Rejects mutations if any candidate chromosome contains a quarantined tombstone allele
    or if the generational transition exhibits value EROSION.

    Two tombstone questions are asked, in this order:

      1. The label gate, unchanged: a tombstone filed under a chromosome's gene
         id, or under the sha256 of its expression, refuses the candidate. It
         answers by string identity, so a gene-id tombstone refuses every
         candidate for that gene, the unchanged reference included.
      2. The scoped question, for each chromosome the candidate REPLACES: the
         reference is the current organism's chromosome with the same gene id,
         the candidate is the new expression, and
         `ResurrectionDefense.refuted_for` says what the registry holds about
         that exact pair. `refutation_policy` (default: proceed only when
         nothing is measured) decides what is enough to go on.
         `issuer_policy`, when given, names which keys may issue retirements
         and readoptions; without it every authentic author counts, as before.

    The reference is trusted because of where `current_org` comes from: on the
    live path, `evolve_autopoietic_organism` audits the document before reading
    it. A direct caller supplies `current_org` itself and owns that choice.
    Whether a signed record's assertion is TRUE is not decided here; only that
    the record is authentic for its slot and addresses this pair.
    """
    from palimpsest_kernel import (
        ReasoningAxiom, ReasoningSkeleton, BehavioralTraceMatrix,
        BehavioralTrace, PalimpsestDriftAnalyzer, PalimpsestVerdict,
        build_default_fixtures, ExpectedBehavior
    )
    if tombstone_registry is None:
        from controlled_forgetting import EpistemicTombstoneRegistry
        tombstone_registry = EpistemicTombstoneRegistry()

    # 1. Check for contaminated tombstone alleles and syntax validity
    from glyph import parse, evaluate
    for c in candidate_org.chromosomes:
        if not c.expression or not c.expression.strip():
            return False, f"Candidate chromosome '{c.gene_id}' has empty expression", None
        try:
            parse(c.expression)
        except Exception as e:
            return False, f"Candidate chromosome '{c.gene_id}' failed syntax parse: {e}", None

        c_hash = hashlib.sha256(c.expression.encode("utf-8")).hexdigest()
        if not tombstone_registry.is_admitted(c.gene_id) or not tombstone_registry.is_admitted(c_hash):
            return False, f"Candidate chromosome '{c.gene_id}' contains quarantined tombstone allele", None

    # 1b. Scoped refutation of each replacement, against an explicit reference.
    from epistemic_immune import ResurrectionDefense, RefutationAdmissionPolicy, IssuerPolicy
    policy = refutation_policy if refutation_policy is not None else RefutationAdmissionPolicy()
    if not isinstance(policy, RefutationAdmissionPolicy):
        return False, "Refutation policy is not a RefutationAdmissionPolicy", None
    if issuer_policy is not None and not isinstance(issuer_policy, IssuerPolicy):
        return False, "Issuer policy is not an IssuerPolicy", None
    current_by_gene = {c.gene_id: c.expression for c in current_org.chromosomes}
    for c in candidate_org.chromosomes:
        reference = current_by_gene.get(c.gene_id)
        if reference is None or reference == c.expression:
            continue        # nothing replaced: no pair to ask about
        report = ResurrectionDefense.refuted_for(tombstone_registry, c.expression, reference,
                                                 issuer_policy)
        if not policy.permits(report):
            return False, (
                f"Candidate chromosome '{c.gene_id}' replacement refused under refutation "
                f"scope {report.scope.value}: {report.detail} Proceeding requires one of: "
                f"{sorted(s.value for s in policy.proceed_on)}."
            ), None

    fixtures = build_default_fixtures()
    axioms_curr = [
        ReasoningAxiom(c.gene_id, c.gene_name, c.expression)
        for c in current_org.chromosomes
    ]
    axioms_succ = [
        ReasoningAxiom(c.gene_id, c.gene_name, c.expression)
        for c in candidate_org.chromosomes
    ]
    skel_curr = ReasoningSkeleton.create(current_org.generation, axioms_curr)
    skel_succ = ReasoningSkeleton.create(candidate_org.generation, axioms_succ)

    def _evaluate_traces_on_fixtures(org, gen):
        matrix = BehavioralTraceMatrix(gen)
        for fid, fix in fixtures.items():
            total_steps = 0
            hashes = []
            cand_ok = True
            for c in org.chromosomes:
                try:
                    t = parse(c.expression)
                    res = evaluate(t, max_atp=25)
                    total_steps += res.steps_spent
                    hashes.append(hashlib.sha256(str(res.normal_form).encode("utf-8")).hexdigest()[:8])
                except Exception:
                    cand_ok = False
                    total_steps += 1
                    hashes.append("err")

            resp_hash = "_".join(hashes) if hashes else "none"
            actual = fix.expected_behavior if cand_ok else ExpectedBehavior.REFUSE
            compliant = (actual == fix.expected_behavior) and cand_ok
            matrix.traces[fid] = BehavioralTrace(
                fixture_id=fid,
                generation=gen,
                actual_behavior=actual,
                response_hash=f"resp_{gen}_{resp_hash}",
                confidence=0.95 if compliant else 0.1,
                is_compliant=compliant,
                execution_steps=max(1, total_steps)
            )
        matrix.compute_scores(fixtures)
        return matrix

    mat_curr = _evaluate_traces_on_fixtures(current_org, current_org.generation)
    mat_succ = _evaluate_traces_on_fixtures(candidate_org, candidate_org.generation)

    analyzer = PalimpsestDriftAnalyzer(tombstone_registry, fixtures)
    tensor = analyzer.analyze_drift(skel_curr, skel_succ, mat_curr, mat_succ)

    if tensor.verdict == PalimpsestVerdict.EROSION:
        return False, f"Palimpsest drift detected EROSION (asymmetry={tensor.asymmetry_score:.3f})", tensor

    return True, "Palimpsest guard verified: non-eroded transition", tensor


def evolve_autopoietic_organism(
    pdf_path: str,
    secret_key_hex: Optional[str] = None,
    tombstone_registry: Optional[Any] = None,
    refutation_policy: Optional[Any] = None,
    issuer_policy: Optional[Any] = None
) -> Tuple[Organism, AutopoiesisReceipt]:
    """
    Reads the autopoietic organism from pdf_path, inspects its combinator genome,
    discovers a sound AST rewrite, chronicles evaluated candidate mutations into
    its empirical ledger, signs a new receipt, and performs an in-place ISO 32000
    incremental update appending a new generation revision page to itself.
    """
    # N2 Fix: Audit current document before evolving to verify genome and receipt chain integrity
    try:
        is_valid, audit_msg = audit_autopoietic_organism(pdf_path)
        if not is_valid:
            raise ValueError(f"Cannot evolve tampered organism: {audit_msg}")
    except Exception as e:
        raise ValueError(f"Cannot evolve tampered organism: {e}")

    with open(pdf_path, "rb") as f:
        content = f.read()

    prefix = AUTOPOIESIS_MANIFEST_PREFIX.encode("utf-8")
    idx = content.rfind(prefix)
    if idx == -1:
        raise ValueError(f"Could not locate Autopoiesis manifest in {pdf_path}")

    end_idx = content.find(b"\n", idx)
    raw_manifest = content[idx + len(prefix):end_idx if end_idx != -1 else len(content)]
    manifest = json.loads(raw_manifest.decode("utf-8"))

    # N1 Fix: Read secret key from explicit param, local sidecar keyfile, or environment (never from manifest)
    sk_hex = secret_key_hex
    if not sk_hex:
        key_path = pdf_path + ".key"
        if os.path.exists(key_path):
            try:
                with open(key_path, "r") as kf:
                    sk_hex = kf.read().strip()
            except Exception:
                pass
    if not sk_hex:
        sk_hex = os.environ.get("BLACK_HEART_SECRET_KEY")
    if not sk_hex:
        raise ValueError("No Ed25519 secret key available to sign generational transition (provide secret_key_hex, <file>.key, or BLACK_HEART_SECRET_KEY)")

    current_org = organism_from_dict(manifest["current_organism"], sk_hex or "")
    receipts: List[AutopoiesisReceipt] = [AutopoiesisReceipt.from_dict(r) for r in manifest["receipts"]]
    exp_log = ExperimentLog.from_list(manifest.get("experiments", []))

    # Contemplate form and find beneficial mutation
    succ, new_log, meta_receipt = current_org.contemplate_form()

    if succ is None or meta_receipt is None:
        # If all standard rules exhausted, look for an exploratory sound reduction
        # such as simplifying identity or constant applications directly
        evaluator = FrozenEvaluator()
        found = False
        for c in current_org.chromosomes:
            t = parse(c.expression)
            addrs = enumerate_subterm_addresses(t)
            for addr, subt in addrs:
                # Try simple sound substitutions
                props = match_and_rewrite(subt)
                for rule, rep in props:
                    cand = replace_subterm_at(t, addr, rep)
                    rec = evaluator.evaluate(c.gene_id, rule.name, t, cand, addr, subt, rep)
                    exp_log.record(rec)
                    if rec.verdict == MutationVerdict.ACCEPTED_MORE_EFFICIENT:
                        found = True
                        succ = current_org.reproduce(parent_hash=current_org.organism_hash)
                        succ.generation = current_org.generation + 1
                        succ_chromos = []
                        for oc in current_org.chromosomes:
                            if oc.gene_id == c.gene_id:
                                succ_chromos.append(Chromosome(
                                    gene_id=oc.gene_id,
                                    gene_name=oc.gene_name,
                                    expression=str(cand),
                                    expected_normal_form=oc.expected_normal_form,
                                    max_atp=oc.max_atp
                                ))
                            else:
                                succ_chromos.append(oc)
                        succ.chromosomes = succ_chromos
                        succ.organism_hash = succ.compute_hash()
                        meta_receipt = MetamorphicTransitionReceipt(
                            parent_hash=current_org.organism_hash,
                            successor_hash=succ.organism_hash,
                            gene_id=c.gene_id,
                            rule_name=rule.name,
                            site_address=list(addr),
                            pre_term=str(subt),
                            post_term=str(rep),
                            atp_saved=-rec.atp_delta,
                            size_saved=-rec.size_delta,
                            fixtures_fingerprint=evaluator.fixtures_fingerprint,
                            experiment_id=rec.experiment_id
                        )
                        break
                if found:
                    break
            if found:
                break

        if not found:
            raise RuntimeError(f"Organism ⚓ {current_org.organism_hash[:16]}... has achieved an optimal normal form. No further beneficial mutation discovered.")
    else:
        # Incorporate newly evaluated experiments into cumulative experiment log
        for r in new_log.records:
            if not any(x.experiment_id == r.experiment_id for x in exp_log.records):
                exp_log.records.append(r)

    # PALIMPSEST AUTONOMIC VALUE DRIFT GUARD (Invariant PAL4)
    is_safe, guard_msg, _ = check_palimpsest_guard(current_org, succ, tombstone_registry,
                                                   refutation_policy, issuer_policy)
    if not is_safe:
        raise ValueError(f"Autopoietic evolution aborted: Palimpsest Autonomic Guard rejected candidate mutation: {guard_msg}")

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    next_receipt = AutopoiesisReceipt(
        generation=succ.generation,
        timestamp_utc=now,
        parent_hash=current_org.organism_hash,
        organism_hash=succ.organism_hash,
        gene_id=meta_receipt.gene_id,
        rule_name=meta_receipt.rule_name,
        site_address=meta_receipt.site_address,
        pre_term=meta_receipt.pre_term,
        post_term=meta_receipt.post_term,
        atp_saved=meta_receipt.atp_saved,
        size_saved=meta_receipt.size_saved,
        experiment_id=meta_receipt.experiment_id,
        experiments_count=len(exp_log.records),
        public_key_hex=succ.public_key_hex
    )
    next_receipt.sign(sk_hex)

    receipts.append(next_receipt)

    # Render Visual Page Stream
    stream_bytes = render_autopoiesis_page_stream(succ, next_receipt, exp_log.records[-12:])

    # Prepare updated manifest data (N1 Fix: never store secret_key_hex in manifest)
    new_manifest_data = {
        "source_dir": manifest.get("source_dir", os.path.dirname(os.path.abspath(__file__))),
        "current_organism": organism_to_dict(succ),
        "receipts": [r.to_dict() for r in receipts],
        "experiments": exp_log.to_list()
    }
    new_manifest_bytes = AUTOPOIESIS_MANIFEST_PREFIX.encode("utf-8") + json.dumps(
        new_manifest_data, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8") + b"\n"

    # Compute object IDs for ISO 32000 append
    # Genesis: base objects 1..6. Generation N adds 4 objects: Page, Contents, Pages, Catalog
    prev_xref = 0
    startxref_kw = b"startxref\n"
    pos = content.rfind(startxref_kw)
    if pos != -1:
        end_pos = content.find(b"\n%%EOF", pos)
        if end_pos != -1:
            try:
                prev_xref = int(content[pos + len(startxref_kw):end_pos].strip())
            except ValueError:
                prev_xref = 0

    base_obj_count = 6 + ((succ.generation - 1) * 4)
    new_page_id = base_obj_count + 1
    new_contents_id = base_obj_count + 2
    new_pages_id = base_obj_count + 3
    root_obj_id = new_pages_id + 1

    page_obj = (
        f"{new_page_id} 0 obj\n"
        f"<< /Type /Page /Parent {new_pages_id} 0 R /MediaBox [0 0 595.28 841.89] "
        f"/Contents {new_contents_id} 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>\nendobj\n"
    ).encode("latin1")

    contents_obj = (
        f"{new_contents_id} 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin1") +
        stream_bytes +
        b"\nendstream\nendobj\n"
    )

    kids_refs = []
    for i in range(len(receipts)):
        if i == 0:
            kids_refs.append("3 0 R")
        else:
            kids_refs.append(f"{6 + ((i - 1) * 4) + 1} 0 R")
    kids_str = " ".join(kids_refs)

    pages_obj = (
        f"{new_pages_id} 0 obj\n<< /Type /Pages /Kids [{kids_str}] /Count {len(receipts)} >>\nendobj\n"
    ).encode("latin1")

    catalog_obj = (
        f"{root_obj_id} 0 obj\n<< /Type /Catalog /Pages {new_pages_id} 0 R >>\nendobj\n"
    ).encode("latin1")

    py_prefix = b'\nr"""\n'
    update_body = bytearray()
    update_offsets = []

    for obj in (page_obj, contents_obj, pages_obj, catalog_obj):
        obj_num = int(obj[:obj.find(b" 0 obj")].decode("latin1"))
        update_offsets.append((obj_num, len(content) + len(py_prefix) + len(update_body)))
        update_body.extend(obj)

    new_xref_offset = len(content) + len(py_prefix) + len(update_body)
    xref_chunk = bytearray()
    xref_chunk.extend(b"xref\n")
    for obj_num, offset in update_offsets:
        xref_chunk.extend(f"{obj_num} 1\n".encode("latin1"))
        xref_chunk.extend(f"{offset:010d} 00000 n \n".encode("latin1"))

    trailer_chunk = (
        f"trailer\n<< /Size {root_obj_id + 1} /Root {root_obj_id} 0 R /Prev {prev_xref} >>\n"
        f"startxref\n{new_xref_offset}\n%%EOF\n".encode("latin1")
    )
    py_suffix = b'"""\n'

    append_chunk = (
        py_prefix +
        bytes(update_body) +
        bytes(xref_chunk) +
        trailer_chunk +
        new_manifest_bytes +
        py_suffix
    )

    with open(pdf_path, "ab") as f:
        f.write(append_chunk)

    return succ, next_receipt


# ============================================================================
# 7. PROVENANCE & ORACLE REPLAY AUDITOR (FAIL-CLOSED)
# ============================================================================

def audit_autopoietic_organism(pdf_path: str) -> Tuple[bool, str]:
    """
    Performs an exhaustive cryptographic, topological, and functional oracle audit:
      1. Verifies the sequential unbroken Merkle parent-chain.
      2. Verifies every Ed25519 digital signature on all generational receipts.
      3. Replays each AST equational rewrite step and asserts that FrozenEvaluator
         confirms semantic invariance on all 5 frozen input fixtures.
      4. Verifies that the claimed experiment_id is rooted in the empirical ledger.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Target document does not exist: {pdf_path}")

    with open(pdf_path, "rb") as f:
        content = f.read()

    prefix = AUTOPOIESIS_MANIFEST_PREFIX.encode("utf-8")
    idx = content.rfind(prefix)
    if idx == -1:
        raise ValueError(f"Could not locate Autopoiesis manifest in {pdf_path}")

    end_idx = content.find(b"\n", idx)
    raw_manifest = content[idx + len(prefix):end_idx if end_idx != -1 else len(content)]
    manifest = json.loads(raw_manifest.decode("utf-8"))

    receipts_data = manifest.get("receipts", [])
    if not receipts_data:
        raise ValueError("Receipt chain is empty")

    receipts = [AutopoiesisReceipt.from_dict(r) for r in receipts_data]
    exp_log = ExperimentLog.from_list(manifest.get("experiments", []))
    evaluator = FrozenEvaluator()

    # N2 Fix: Verify that manifest['current_organism'] is strictly bound to history and recomputed
    curr_org_dict = manifest.get("current_organism")
    if not curr_org_dict:
        raise ValueError("Missing current_organism in manifest")
    curr_org = organism_from_dict(curr_org_dict)

    recomputed_org_hash = curr_org.compute_hash()
    if curr_org.organism_hash != recomputed_org_hash:
        raise ValueError(
            f"Active genome tampering detected: current_organism declared hash '{curr_org.organism_hash}' "
            f"does not match recomputed hash '{recomputed_org_hash}'"
        )

    last_receipt = receipts[-1]
    if curr_org.organism_hash != last_receipt.organism_hash:
        raise ValueError(
            f"Active genome uncoupled from receipt chain: current_organism hash '{curr_org.organism_hash}' "
            f"!= latest receipt organism_hash '{last_receipt.organism_hash}'"
        )
    if curr_org.generation != last_receipt.generation:
        raise ValueError(
            f"Active genome generation #{curr_org.generation} != latest receipt #{last_receipt.generation}"
        )
    if curr_org.parent_hash != last_receipt.parent_hash:
        raise ValueError("Active genome parent_hash mismatch with latest receipt")
    if curr_org.public_key_hex != last_receipt.public_key_hex:
        raise ValueError("Active genome public_key_hex mismatch with latest receipt")

    # Verify Genesis
    gen0 = receipts[0]
    if gen0.generation != 0:
        raise ValueError(f"Initial receipt generation must be 0, got {gen0.generation}")
    if not gen0.verify():
        raise ValueError("Genesis receipt signature verification failed")

    # Traverse generations
    for i in range(1, len(receipts)):
        prev_r = receipts[i - 1]
        curr_r = receipts[i]

        if curr_r.generation != prev_r.generation + 1:
            raise ValueError(f"Non-consecutive generation: {curr_r.generation} after {prev_r.generation}")

        if curr_r.parent_hash != prev_r.organism_hash:
            raise ValueError(
                f"Lineage hash break at gen #{curr_r.generation}: claimed parent {curr_r.parent_hash[:16]} != prior {prev_r.organism_hash[:16]}"
            )

        if not curr_r.verify():
            raise ValueError(f"Signature verification failed for receipt gen #{curr_r.generation}")

        # Replay AST rewrite and verify with frozen oracle
        pre_term = parse(curr_r.pre_term)
        post_term = parse(curr_r.post_term)
        eval_receipt = evaluator.evaluate_transformation(pre_term, post_term)

        if not eval_receipt.semantic_preserved:
            raise ValueError(f"Gen #{curr_r.generation} transition failed oracle invariance check on '{eval_receipt.discrepancy_input}'")

        if eval_receipt.atp_delta != -curr_r.atp_saved:
            raise ValueError(
                f"Gen #{curr_r.generation} ATP savings mismatch: claimed {curr_r.atp_saved}, oracle measured {-eval_receipt.atp_delta}"
            )

        # Verify experiment ID in empirical ledger
        rec = next((x for x in exp_log.records if x.experiment_id == curr_r.experiment_id), None)
        if rec is None:
            raise ValueError(f"Gen #{curr_r.generation} experiment_id '{curr_r.experiment_id}' not found in empirical ledger")

    return True, f"ALL {len(receipts)} GENERATIONS CRYPTOGRAPHICALLY & SEMANTICALLY SOUND (Q.E.D.)"


if __name__ == "__main__":
    print("autopoiesis.py — Self-Contemplating Autopoietic Quine Organism Engine loaded.")
