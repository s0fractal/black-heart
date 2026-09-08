#!/usr/bin/env python3
"""
organism.py — Autonomous Self-Replicating Polyglot Organism (Quine-Automata).
Part of Project Black-Heart (%🖤).

Implements:
  1. Von Neumann Self-Reproducing Automata inside ISO 32000 PDF streams.
  2. Genetic Code composed of SKIY combinator chromosomes.
  3. Phenotype visual morphology: Membrane color palette, cellular passport,
     and vector proof nets rendered directly via PostScript operators.
  4. Metabolic selection: Chromosomes must reduce to normal forms within bounded ATP.
  5. Quine reproduction: 'python3 organism.pdf --reproduce' physically synthesizes
     the next-generation offspring PDF on disk!
"""

from __future__ import annotations
import os
import sys
import json
import time
import random
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any

from glyph import parse, evaluate, Term
from crypto import generate_keypair, public_key_from_secret, sign_bytes, verify_bytes
from vector_net import VectorNetRenderer

# ============================================================================
# GENOMIC DATA STRUCTURES
# ============================================================================

@dataclass
class Chromosome:
    gene_id: str
    gene_name: str
    expression: str
    expected_normal_form: str
    max_atp: int = 100
    atp_burned: int = 0
    vital: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gene_id": self.gene_id,
            "gene_name": self.gene_name,
            "expression": self.expression,
            "expected_normal_form": self.expected_normal_form,
            "max_atp": self.max_atp,
            "atp_burned": self.atp_burned,
            "vital": self.vital
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Chromosome:
        return cls(
            gene_id=d["gene_id"],
            gene_name=d["gene_name"],
            expression=d["expression"],
            expected_normal_form=d["expected_normal_form"],
            max_atp=d.get("max_atp", 100),
            atp_burned=d.get("atp_burned", 0),
            vital=d.get("vital", True)
        )

@dataclass
class Organism:
    generation: int
    parent_hash: str
    public_key_hex: str
    secret_key_hex: str
    chromosomes: List[Chromosome] = field(default_factory=list)
    birth_timestamp_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    organism_hash: str = ""

    def compute_hash(self) -> str:
        data = {
            "generation": self.generation,
            "parent_hash": self.parent_hash,
            "public_key_hex": self.public_key_hex,
            "birth_timestamp_utc": self.birth_timestamp_utc,
            "chromosomes": [c.to_dict() for c in self.chromosomes]
        }
        raw = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def verify(self) -> bool:
        """
        Verifies the organism's structural, cryptographic, and metabolic soundness.
        Returns True if completely sound; False otherwise.
        """
        if self.organism_hash:
            if self.organism_hash != self.compute_hash():
                return False
        else:
            self.organism_hash = self.compute_hash()

        if not self.public_key_hex or len(self.public_key_hex) != 64:
            return False

        if self.secret_key_hex and len(self.secret_key_hex) == 64:
            try:
                derived_pk = public_key_from_secret(bytes.fromhex(self.secret_key_hex)).hex()
                if derived_pk != self.public_key_hex:
                    return False
            except Exception:
                return False

        viable, _ = self.run_metabolism()
        return viable

    def run_metabolism(self) -> Tuple[bool, int]:
        """
        Executes internal metabolic reduction of all chromosomes.
        Returns: (is_viable, total_atp_burned)
        """
        total_atp = 0
        for chrom in self.chromosomes:
            try:
                t = parse(chrom.expression)
                res = evaluate(t, max_atp=chrom.max_atp)
                if not res.is_settled():
                    chrom.vital = False
                    return False, total_atp

                chrom.atp_burned = res.atp_spent
                total_atp += res.atp_spent

                exp_t = parse(chrom.expected_normal_form)
                exp_res = evaluate(exp_t)

                if str(res.term) != str(exp_res.term):
                    chrom.vital = False
                    return False, total_atp
                chrom.vital = True
            except Exception:
                chrom.vital = False
                return False, total_atp

        return True, total_atp

    def reproduce(self, mutation_rate: float = 0.05) -> Organism:
        """
        Synthesizes a child organism:
          1. Verifies parent metabolism.
          2. Generates new child Ed25519 keypair.
          3. Applies stochastic mutations.
        """
        viable, _ = self.run_metabolism()
        if not viable:
            raise ValueError("Parent organism failed metabolic fitness test! Reproduction aborted.")

        if not self.organism_hash:
            self.organism_hash = self.compute_hash()

        child_sk, child_pk = generate_keypair()
        child_chromosomes: List[Chromosome] = []

        for chrom in self.chromosomes:
            # Clone gene
            child_chrom = Chromosome(
                gene_id=chrom.gene_id,
                gene_name=chrom.gene_name,
                expression=chrom.expression,
                expected_normal_form=chrom.expected_normal_form,
                max_atp=chrom.max_atp
            )
            # Stochastic mutation
            if random.random() < mutation_rate:
                child_chrom.max_atp = max(50, chrom.max_atp + random.randint(-10, 20))
            child_chromosomes.append(child_chrom)

        child = Organism(
            generation=self.generation + 1,
            parent_hash=self.organism_hash or self.compute_hash(),
            public_key_hex=child_pk,
            secret_key_hex=child_sk,
            chromosomes=child_chromosomes
        )
        child.organism_hash = child.compute_hash()
        return child

# ============================================================================
# COMPILER FOR POLYGLOT ORGANISM PDF
# ============================================================================

class PolyglotOrganismCompiler:
    """
    Compiles an Organism into a fully autonomous, self-reproducing ISO 32000 PDF polyglot.
    """
    @classmethod
    def compile(cls, organism: Organism, output_path: str) -> str:
        organism.organism_hash = organism.compute_hash()

        page_width, page_height = 595, 842 # A4
        margin = 54
        content_width = page_width - 2 * margin

        # Derive phenotype color palette from Ed25519 public key
        pk_seed = int(organism.public_key_hex[:8], 16)
        r_col = 0.1 + ((pk_seed & 0xFF) / 512.0)
        g_col = 0.15 + (((pk_seed >> 8) & 0xFF) / 512.0)
        b_col = 0.25 + (((pk_seed >> 16) & 0xFF) / 512.0)

        stream_lines = []
        y = page_height - margin

        # Header Title
        stream_lines.append(f"BT /F1 18 Tf {r_col:.2f} {g_col:.2f} {b_col:.2f} rg {margin} {y} Td (BLACK-HEART AUTONOMOUS POLYGLOT ORGANISM) Tj 0 g ET")
        y -= 22
        stream_lines.append(
            f"BT /F3 10 Tf 0.3 0.35 0.45 rg {margin} {y} Td "
            f"(Biological Digital Automata | Generation #{organism.generation:04d} | Quine-Replicating Genome) Tj 0 g ET"
        )
        y -= 14

        # Decorative rule in organism's signature color
        stream_lines.append(f"{r_col:.2f} {g_col:.2f} {b_col:.2f} rg {margin} {y} {content_width} 2 re f 0 g")
        y -= 20

        # Phenotype Passport Card
        card_top = y + 4
        card_h = 82
        stream_lines.append(f"0.97 0.98 0.99 rg {margin} {card_top - card_h} {content_width} {card_h} re f 0 g")
        stream_lines.append(f"{r_col:.2f} {g_col:.2f} {b_col:.2f} RG 1.5 w {margin} {card_top - card_h} {content_width} {card_h} re s 0 g")

        stream_lines.append(f"BT /F1 11 Tf 0.1 0.2 0.35 rg {margin + 12} {y - 4} Td (Cellular Passport & Genetic Identity) Tj 0 g ET")
        y -= 17
        stream_lines.append(f"BT /F4 8 Tf 0.2 0.2 0.2 rg {margin + 12} {y} Td (Organism Hash: {organism.organism_hash}) Tj 0 g ET")
        y -= 12
        stream_lines.append(f"BT /F4 8 Tf 0.2 0.2 0.2 rg {margin + 12} {y} Td (Parent Lineage: {organism.parent_hash[:32]}... | Born: {organism.birth_timestamp_utc}) Tj 0 g ET")
        y -= 12
        stream_lines.append(f"BT /F4 8 Tf 0.1 0.4 0.2 rg {margin + 12} {y} Td (Ed25519 Gene PK: {organism.public_key_hex[:32]}... [GENETIC REPLICATION KEY]) Tj 0 g ET")
        y -= 12
        stream_lines.append(f"BT /F1 9 Tf {r_col:.2f} {g_col:.2f} {b_col:.2f} rg {margin + 12} {y} Td (Chromosomes: {len(organism.chromosomes)} active genes | Metabolic State: VIABLE) Tj 0 g ET")
        y -= 45

        # Render Chromosome Vector Proof Nets
        renderer = VectorNetRenderer(node_radius=11.0, level_height=32.0)
        for chrom in organism.chromosomes[:2]: # Render top 2 genes visually
            if y < margin + 160:
                break

            expr_ascii = chrom.expression.replace("🖤", "K").replace("🤍", "I").replace("🌿", "S").replace("🔁", "Y")
            exp_ascii = chrom.expected_normal_form.replace("🖤", "K").replace("🤍", "I").replace("🌿", "S").replace("🔁", "Y")

            stream_lines.append(f"BT /F1 11 Tf 0.15 0.2 0.3 rg {margin} {y} Td (Chromosome {chrom.gene_id}: {_escape_pdf(chrom.gene_name)}) Tj 0 g ET")
            y -= 14
            stream_lines.append(f"BT /F2 8 Tf 0.35 0.35 0.4 rg {margin} {y} Td (Gene Expr: {_escape_pdf(expr_ascii)}  -->  Target Normal Form: {_escape_pdf(exp_ascii)}) Tj 0 g ET")
            y -= 12

            try:
                lhs = parse(chrom.expression)
                rhs = parse(chrom.expected_normal_form)
                net_h = 125
                net_ops = renderer.render_reduction_step(
                    lhs=lhs,
                    rhs=rhs,
                    x=margin,
                    y=y - net_h,
                    width=content_width,
                    height=net_h,
                    atp_cost=chrom.atp_burned or 1,
                    rule_name=f"{chrom.gene_id} Metabolic Folding"
                )
                stream_lines.append(net_ops)
                y -= (net_h + 26)
            except Exception as e:
                y -= 10

        # Footer Box: Quine Reproduction Command
        y = margin + 35
        stream_lines.append(f"0.92 0.94 0.98 rg {margin} {y - 20} {content_width} 24 re f 0 g")
        stream_lines.append(f"BT /F1 9 Tf 0.1 0.3 0.2 rg {margin + 10} {y - 8} Td (Quine Replication: Run 'python3 <this_file>.pdf --reproduce' to synthesize next generation) Tj 0 g ET")

        content_bytes = "\n".join(stream_lines).encode("latin1", errors="replace")

        # Standard 14 PDF Objects
        objs: List[bytes] = []
        objs.append(b"<</Type /Catalog /Pages 2 0 R>>")
        objs.append(b"<</Type /Pages /Kids [3 0 R] /Count 1>>")
        objs.append(
            f"<</Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] "
            f"/Contents 4 0 R /Resources <</Font <</F1 5 0 R /F2 6 0 R /F3 7 0 R /F4 8 0 R>>>>>>".encode("latin1")
        )
        objs.append(
            f"<</Length {len(content_bytes)}>>\nstream\n".encode("latin1")
            + content_bytes
            + b"\nendstream"
        )
        objs.append(b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold>>")
        objs.append(b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>")
        objs.append(b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique>>")
        objs.append(b"<</Type /Font /Subtype /Type1 /BaseFont /Courier>>")

        # Polyglot Header (Python raw docstring)
        pdf_header = (
            b"# coding: utf-8\n"
            b'r"""%PDF-1.7\n'
            b"%\xf0\x9f\x96\xa4\n"
        )

        # Embedded Organism Genome Comment
        genome_dict = {
            "generation": organism.generation,
            "parent_hash": organism.parent_hash,
            "organism_hash": organism.organism_hash,
            "public_key_hex": organism.public_key_hex,
            "secret_key_hex": organism.secret_key_hex,
            "birth_timestamp_utc": organism.birth_timestamp_utc,
            "source_dir": os.path.dirname(os.path.abspath(__file__)),
            "chromosomes": [c.to_dict() for c in organism.chromosomes]
        }
        genome_str = json.dumps(genome_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        genome_comment = f"%🖤 ORGANISM_GENOME: {genome_str}\n".encode("utf-8")

        body = bytearray(pdf_header)
        body.extend(genome_comment)

        offsets = [0]
        for i, o in enumerate(objs, 1):
            offsets.append(len(body))
            body.extend(f"{i} 0 obj\n".encode("latin1"))
            body.extend(o)
            body.extend(b"\nendobj\n")

        xstart = len(body)
        body.extend(f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode("latin1"))
        for off in offsets[1:]:
            body.extend(f"{off:010d} 00000 n \n".encode("latin1"))

        body.extend(
            f"trailer\n<</Size {len(objs)+1} /Root 1 0 R>>\nstartxref\n{xstart}\n%%EOF\n\"\"\"\n".encode("latin1")
        )

        # Append the standalone self-reproducing engine
        runner_code = _generate_organism_runner()
        body.extend(runner_code.encode("utf-8"))

        with open(output_path, "wb") as f:
            f.write(body)

        return output_path

    @classmethod
    def load_from_polyglot(cls, pdf_path: str) -> Organism:
        with open(pdf_path, "rb") as f:
            content = f.read()

        prefix = "%🖤 ORGANISM_GENOME: ".encode("utf-8")
        idx = content.find(prefix)
        if idx == -1:
            raise ValueError(f"No ORGANISM_GENOME found in {pdf_path}")

        end_idx = content.find(b"\n", idx)
        raw = content[idx + len(prefix):end_idx].decode("utf-8")
        d = json.loads(raw)

        org = Organism(
            generation=d["generation"],
            parent_hash=d["parent_hash"],
            public_key_hex=d["public_key_hex"],
            secret_key_hex=d.get("secret_key_hex", ""),
            birth_timestamp_utc=d["birth_timestamp_utc"],
            organism_hash=d.get("organism_hash", "")
        )
        for c_dict in d.get("chromosomes", []):
            org.chromosomes.append(Chromosome.from_dict(c_dict))
        return org

def extract_organism_from_pdf(pdf_path: str) -> Organism:
    """Extracts and parses an Organism genome from a polyglot PDF document."""
    return PolyglotOrganismCompiler.load_from_polyglot(pdf_path)

def _escape_pdf(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

def _generate_organism_runner() -> str:
    return r'''
# --- BEGIN STANDALONE AUTONOMOUS ORGANISM REPLICATION RUNNER ---
import os, sys, json, time, random, hashlib

def main():
    target_path = sys.argv[0]
    args = sys.argv[1:]

    with open(target_path, "rb") as f:
        content = f.read()

    prefix = "%🖤 ORGANISM_GENOME: ".encode("utf-8")
    idx = content.find(prefix)
    if idx == -1:
        print("\033[1;31m[!] CRITICAL ERROR: ORGANISM_GENOME block missing!\033[0m")
        sys.exit(1)

    end_idx = content.find(b"\n", idx)
    raw = content[idx + len(prefix):end_idx].decode("utf-8")
    genome = json.loads(raw)

    gen = genome["generation"]
    org_hash = genome.get("organism_hash", "")[:16]

    print("\033[1;36m" + "=" * 70)
    print("  %🖤 BLACK-HEART — AUTONOMOUS SELF-REPRODUCING ORGANISM")
    print(f"  Organism: Gen #{gen:04d} ⟨{org_hash}⟩ | File: {os.path.basename(target_path)}")
    print("=" * 70 + "\033[0m\n")

    if "--status" in args or not args:
        print(f"\033[1;34m[*] Generation:      \033[0m #{gen:04d}")
        print(f"\033[1;34m[*] Parent Hash:     \033[0m {genome['parent_hash']}")
        print(f"\033[1;34m[*] Public Key:      \033[0m {genome['public_key_hex']}")
        print(f"\033[1;34m[*] Born UTC:        \033[0m {genome['birth_timestamp_utc']}")
        print(f"\033[1;34m[*] Active Genome:   \033[0m {len(genome['chromosomes'])} chromosomes\n")
        for c in genome["chromosomes"]:
            print(f"    - [{c['gene_id']}] {c['gene_name']}: {c['expression']} (Target: {c['expected_normal_form']})")
        print("\n\033[0;37mCommands: Run with '--reproduce' to synthesize next-generation offspring.\033[0m")

    if "--reproduce" in args:
        print("\033[1;33m[*] INITIATING METABOLIC CHECK & QUINE REPRODUCTION...\033[0m")
        # In a standalone polyglot, import organism compiler to spawn child
        try:
            target_dir = os.path.dirname(os.path.abspath(target_path))
            parent_dir = os.path.dirname(target_dir)
            src_dir = genome.get("source_dir")
            for p in (target_dir, parent_dir, src_dir):
                if p and p not in sys.path:
                    sys.path.insert(0, p)

            # Reconstruct organism object and reproduce
            from organism import Organism, Chromosome, PolyglotOrganismCompiler
            org = Organism(
                generation=genome["generation"],
                parent_hash=genome["parent_hash"],
                public_key_hex=genome["public_key_hex"],
                secret_key_hex=genome["secret_key_hex"],
                birth_timestamp_utc=genome["birth_timestamp_utc"],
                organism_hash=genome["organism_hash"]
            )
            for cd in genome["chromosomes"]:
                org.chromosomes.append(Chromosome.from_dict(cd))

            viable, atp = org.run_metabolism()
            if not viable:
                print("\033[1;31m[✗ LETHAL MUTATION] Organism is sterile. Reproduction blocked!\033[0m")
                sys.exit(1)

            print(f"  \033[1;32m[✓ METABOLISM SOUND]\033[0m Burned {atp} ATP across {len(org.chromosomes)} chromosomes.")

            # Spawn child
            child = org.reproduce(mutation_rate=0.05)
            child_dir = os.path.dirname(os.path.abspath(target_path))
            child_filename = f"organism_gen{child.generation:04d}_{child.organism_hash[:8]}.pdf"
            child_path = os.path.join(child_dir, child_filename)

            PolyglotOrganismCompiler.compile(child, child_path)

            print(f"\n\033[1;32m[⚓ SUCCESS] BORN OFFSPRING: Gen #{child.generation:04d}!\033[0m")
            print(f"  Target File: \033[1;35m{child_path}\033[0m ({os.path.getsize(child_path)} bytes)")
            print(f"  Parent Hash: {child.parent_hash[:24]}...")
            print(f"  Child Key:   {child.public_key_hex[:24]}...")
            print(f"  Visual Form: open {child_path}")
            print(f"  Next Gen:    python3 {child_path} --reproduce\n")

        except Exception as e:
            print(f"\033[1;31m[!] Replication Error: {e}\033[0m")
            sys.exit(1)

    print("\033[1;36m" + "=" * 70 + "\033[0m")

if __name__ == "__main__":
    main()
'''

def create_genesis_organism(generation: int = 0) -> Organism:
    """
    Factory creating a sound, metabolically viable Genesis organism.
    """
    sk, pk = generate_keypair()
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
    org = Organism(
        generation=generation,
        parent_hash="00" * 32,
        public_key_hex=pk,
        secret_key_hex=sk,
        chromosomes=chromosomes
    )
    org.organism_hash = org.compute_hash()
    return org

if __name__ == "__main__":
    print("organism.py — Autonomous Polyglot Organism engine loaded.")
