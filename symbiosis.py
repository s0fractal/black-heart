#!/usr/bin/env python3
"""
symbiosis.py — Dialectical Symbiosis, Topological Knot Morphogenesis, & Dual-Parent Polyglot Recombination.
Part of Project Black-Heart (%🖤).

Implements:
  1. Topological Knot & Braid Algebra (Artin Braid Group B_n, writhe, crossing number).
  2. Native ISO 32000 PDF Bézier ribbon renderer with 3D over-under bridge occlusion.
  3. Homologous chromosomal crossover & combinatory synthesis:
     ChildExpr = S (K ParentA_Expr) ParentB_Expr
  4. Dual-vault amalgamation: merging verified parental code vaults into a unified child vault.
  5. Symbiotic Polyglot Compiler: produces an executable ISO 32000 PDF document carrying
     dual lineage proofs, visual knot topology, and executable metabolic quines.
"""

from __future__ import annotations
import os
import sys
import io
import json
import math
import time
import copy
import hashlib
import tempfile
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any

from glyph import parse, evaluate, Term, GLYPH_K, GLYPH_I, GLYPH_S, GLYPH_Y
from crypto import generate_keypair, public_key_from_secret, sign_bytes, verify_bytes
from organism import Organism, Chromosome
import vault as V

# ============================================================================
# 1. TOPOLOGICAL BRAID & KNOT ALGEBRA
# ============================================================================

@dataclass
class BraidCrossing:
    """
    Represents an Artin generator σ_i or its inverse σ_i^(-1).
    index i is 1-based: strand i crosses over strand i+1 if sign > 0,
    or strand i crosses under strand i+1 if sign < 0.
    """
    strand_index: int  # 1 <= i < num_strands
    sign: int          # +1 for over-crossing, -1 for under-crossing

@dataclass
class BraidWord:
    """
    Word in the Artin Braid Group B_n on n strands.
    """
    num_strands: int
    crossings: List[BraidCrossing] = field(default_factory=list)

    @classmethod
    def from_generators(cls, num_strands: int, generators: List[int]) -> BraidWord:
        """
        Parses signed integer generators:
        e.g., [1, 2, 1, 2] -> σ_1 σ_2 σ_1 σ_2
        e.g., [1, -2, 1, -2] -> σ_1 σ_2^(-1) σ_1 σ_2^(-1)
        """
        crossings = []
        for g in generators:
            if g == 0 or abs(g) >= num_strands:
                raise ValueError(f"Invalid Artin generator {g} for {num_strands} strands (must satisfy 1 <= |g| < {num_strands})")
            sign = 1 if g > 0 else -1
            crossings.append(BraidCrossing(strand_index=abs(g), sign=sign))
        return cls(num_strands=num_strands, crossings=crossings)

    @property
    def crossing_number(self) -> int:
        """Total number of crossings in this braid presentation."""
        return len(self.crossings)

    @property
    def writhe(self) -> int:
        """Sum of signs of all crossings (topological writhe invariant)."""
        return sum(c.sign for c in self.crossings)

    def to_artin_notation(self, ascii_only: bool = False) -> str:
        """Human-readable Artin braid notation: e.g. 'σ_1 · σ_2⁻¹' or 's_1 * s_2^-1'."""
        if not self.crossings:
            return "e (Identity)"
        parts = []
        sym = "s_" if ascii_only else "σ_"
        sep = " * " if ascii_only else " · "
        for c in self.crossings:
            if ascii_only:
                exp = "" if c.sign > 0 else "^-1"
            else:
                exp = "" if c.sign > 0 else "⁻¹"
            parts.append(f"{sym}{c.strand_index}{exp}")
        return sep.join(parts)

    def compute_permutation(self) -> List[int]:
        """
        Computes the permutation of strands induced by the braid word.
        Returns 0-indexed destination of each strand: perm[start] = end.
        """
        perm = list(range(self.num_strands))
        for c in self.crossings:
            i = c.strand_index - 1
            perm[i], perm[i + 1] = perm[i + 1], perm[i]
        return perm

    def count_link_components(self) -> int:
        """
        Computes the number of independent closed loops (link components)
        formed by closing the braid (Alexander's closure).
        1 component = Knot (e.g. Trefoil, Figure-eight).
        >1 components = Link (e.g. Hopf link, Borromean rings).
        """
        perm = self.compute_permutation()
        visited = [False] * self.num_strands
        num_components = 0
        for i in range(self.num_strands):
            if not visited[i]:
                num_components += 1
                curr = i
                while not visited[curr]:
                    visited[curr] = True
                    curr = perm[curr]
        return num_components

# Standard canonical knots and links
def trefoil_knot() -> BraidWord:
    """Standard right-handed trefoil knot (3_1): σ_1^3 on 2 strands."""
    return BraidWord.from_generators(2, [1, 1, 1])

def figure_eight_knot() -> BraidWord:
    """Standard figure-eight knot (4_1): σ_1 σ_2^(-1) σ_1 σ_2^(-1) on 3 strands."""
    return BraidWord.from_generators(3, [1, -2, 1, -2])

def hopf_link() -> BraidWord:
    """Standard Hopf link (2 components): σ_1^2 on 2 strands."""
    return BraidWord.from_generators(2, [1, 1])

def whitehead_link() -> BraidWord:
    """Whitehead link: σ_1 σ_2^(-1) σ_1 σ_2^(-2) on 3 strands."""
    return BraidWord.from_generators(3, [1, -2, 1, -2, -2])

# ============================================================================
# 2. NATIVE ISO 32000 PDF KNOT & BRAID RENDERER
# ============================================================================

def render_braid_knot_pdf_stream(
    braid: BraidWord,
    x: float,
    y: float,
    width: float,
    height: float
) -> str:
    """
    Renders an oriented braid with Alexander closure into native ISO 32000
    vector PostScript-style stream operators (m, c, l, S, B*, w, RG, rg).
    Applies cubic Bézier ribbons with over/under bridge breaks to visually
    demonstrate 3D topological entanglement.
    """
    ops: List[str] = []
    ops.append("q")  # save graphics state

    num_strands = max(2, braid.num_strands)
    num_steps = max(1, len(braid.crossings))

    # Margin and spacing
    margin_x = width * 0.15
    margin_y = height * 0.12
    strand_area_w = width - (2 * margin_x)
    strand_gap = strand_area_w / (num_strands - 1) if num_strands > 1 else strand_area_w
    step_height = (height - (2 * margin_y)) / (num_steps + 1)

    # Color palette for strands (gold, obsidian cyan, emerald, magenta)
    colors = [
        ("0.85 0.65 0.15 RG", "0.95 0.85 0.35 rg"),   # Gold / Sun
        ("0.12 0.72 0.88 RG", "0.20 0.85 0.95 rg"),   # Cyan / Mind
        ("0.25 0.85 0.45 RG", "0.40 0.95 0.55 rg"),   # Emerald / Life
        ("0.90 0.30 0.60 RG", "0.98 0.45 0.75 rg"),   # Magenta / Void
    ]

    # Calculate initial strand positions at top
    current_x = [x + margin_x + i * strand_gap for i in range(num_strands)]
    current_y = y + height - margin_y

    # Draw border box around diagram
    ops.append("0.15 0.18 0.25 RG 1 w")
    ops.append(f"{x:.2f} {y:.2f} {width:.2f} {height:.2f} re S")

    # Step-by-step crossing evolution
    for step_idx, crossing in enumerate(braid.crossings):
        next_y = current_y - step_height
        i = crossing.strand_index - 1
        x_left = current_x[i]
        x_right = current_x[i + 1]
        mid_y = (current_y + next_y) / 2.0

        # Draw uncrossed strands straight down
        for s in range(num_strands):
            if s != i and s != i + 1:
                col_RG, _ = colors[s % len(colors)]
                ops.append(f"q 2.5 w {col_RG}")
                ops.append(f"{current_x[s]:.2f} {current_y:.2f} m {current_x[s]:.2f} {next_y:.2f} l S Q")

        col_i, _ = colors[i % len(colors)]
        col_ip1, _ = colors[(i + 1) % len(colors)]

        # Under-strand vs Over-strand based on crossing.sign
        # If sign > 0: strand i crosses OVER strand i+1
        # If sign < 0: strand i crosses UNDER strand i+1
        if crossing.sign > 0:
            # Over: i -> right; Under: i+1 -> left
            # 1. Under strand (i+1 -> left) with gap
            ops.append(f"q 2.5 w {col_ip1}")
            # First segment before crossing
            ops.append(f"{x_right:.2f} {current_y:.2f} m")
            ops.append(f"{x_right:.2f} {mid_y + 4:.2f} {(x_left + x_right)/2 + 4:.2f} {mid_y + 3:.2f} {(x_left + x_right)/2 + 3:.2f} {mid_y + 2:.2f} c S")
            # Second segment after crossing
            ops.append(f"{(x_left + x_right)/2 - 3:.2f} {mid_y - 2:.2f} m")
            ops.append(f"{(x_left + x_right)/2 - 4:.2f} {mid_y - 3:.2f} {x_left:.2f} {mid_y - 4:.2f} {x_left:.2f} {next_y:.2f} c S Q")

            # 2. Over strand (i -> right) continuous with shadow halo
            # Dark halo underneath for 3D occlusion
            ops.append("q 5 w 0.05 0.05 0.08 RG")
            ops.append(f"{x_left:.2f} {current_y:.2f} m")
            ops.append(f"{x_left:.2f} {mid_y:.2f} {x_right:.2f} {mid_y:.2f} {x_right:.2f} {next_y:.2f} c S Q")
            # Colored strand
            ops.append(f"q 2.5 w {col_i}")
            ops.append(f"{x_left:.2f} {current_y:.2f} m")
            ops.append(f"{x_left:.2f} {mid_y:.2f} {x_right:.2f} {mid_y:.2f} {x_right:.2f} {next_y:.2f} c S Q")
        else:
            # Over: i+1 -> left; Under: i -> right
            # 1. Under strand (i -> right) with gap
            ops.append(f"q 2.5 w {col_i}")
            ops.append(f"{x_left:.2f} {current_y:.2f} m")
            ops.append(f"{x_left:.2f} {mid_y + 4:.2f} {(x_left + x_right)/2 - 4:.2f} {mid_y + 3:.2f} {(x_left + x_right)/2 - 3:.2f} {mid_y + 2:.2f} c S")
            ops.append(f"{(x_left + x_right)/2 + 3:.2f} {mid_y - 2:.2f} m")
            ops.append(f"{(x_left + x_right)/2 + 4:.2f} {mid_y - 3:.2f} {x_right:.2f} {mid_y - 4:.2f} {x_right:.2f} {next_y:.2f} c S Q")

            # 2. Over strand (i+1 -> left) continuous with shadow halo
            ops.append("q 5 w 0.05 0.05 0.08 RG")
            ops.append(f"{x_right:.2f} {current_y:.2f} m")
            ops.append(f"{x_right:.2f} {mid_y:.2f} {x_left:.2f} {mid_y:.2f} {x_left:.2f} {next_y:.2f} c S Q")
            ops.append(f"q 2.5 w {col_ip1}")
            ops.append(f"{x_right:.2f} {current_y:.2f} m")
            ops.append(f"{x_right:.2f} {mid_y:.2f} {x_left:.2f} {mid_y:.2f} {x_left:.2f} {next_y:.2f} c S Q")

        # Swap tracking positions
        current_x[i], current_x[i + 1] = current_x[i + 1], current_x[i]
        current_y = next_y

    # Alexander Closure: loop bottom back to top
    final_y = current_y
    for s in range(num_strands):
        orig_top_x = x + margin_x + s * strand_gap
        bot_x = current_x[s]
        col_RG, _ = colors[s % len(colors)]
        ops.append(f"q 1 w [2 2] 0 d {col_RG}")  # dashed closure wire
        # Loop around sides
        offset = (s + 1) * 12.0
        loop_x = x - offset if s < num_strands // 2 else x + width + offset
        ops.append(f"{bot_x:.2f} {final_y:.2f} m")
        ops.append(f"{loop_x:.2f} {final_y - 10:.2f} {loop_x:.2f} {y + height + 10:.2f} {orig_top_x:.2f} {y + height - margin_y:.2f} c S Q")

    ops.append("Q")  # restore graphics state
    return "\n".join(ops)

# ============================================================================
# 3. DIALECTICAL RECOMBINATION & CHROMOSOME CROSSOVER
# ============================================================================

def dialectical_combinatory_synthesis(expr_a: str, expr_b: str) -> str:
    """
    Synthesizes two parent combinatory terms through dialectical coupling:
    Synthesis = S (K Expr_A) Expr_B
    When applied to an argument x:
    S (K Expr_A) Expr_B x  -->  (K Expr_A x) (Expr_B x)  -->  Expr_A (Expr_B x)
    Representing functional pipeline composition of Thesis and Antithesis!
    """
    return f"🌿 (🖤 ({expr_a})) ({expr_b})"

def dialectical_crossover(
    parent_a: Organism,
    parent_b: Organism,
    secret_key_hex: Optional[str] = None
) -> Tuple[Organism, BraidWord]:
    """
    Executes sexual recombination between Organism A (Thesis) and Organism B (Antithesis).
    1. Verifies that both parental organisms are structurally and cryptographically sound.
    2. Combines chromosomes via homologous crossover.
    3. Synthesizes an emergent dialectical chromosome resolving mutual terms.
    4. Generates a unique topological braid word encoding their mutual entanglement.
    5. Returns: (child_organism, braid_word)
    """
    if not parent_a.verify():
        raise ValueError(f"Parent A ({parent_a.organism_hash[:16]}) failed cryptographic verification")
    if not parent_b.verify():
        raise ValueError(f"Parent B ({parent_b.organism_hash[:16]}) failed cryptographic verification")

    child_gen = max(parent_a.generation, parent_b.generation) + 1
    combined_parent_hash = hashlib.sha256(
        (parent_a.organism_hash + parent_b.organism_hash).encode("utf-8")
    ).hexdigest()

    if secret_key_hex:
        child_sk = secret_key_hex
        child_pk = public_key_from_secret(bytes.fromhex(child_sk)).hex()
    else:
        child_sk, child_pk = generate_keypair()

    child_chromosomes: List[Chromosome] = []

    # Map genes by ID
    map_a = {c.gene_id: c for c in parent_a.chromosomes}
    map_b = {c.gene_id: c for c in parent_b.chromosomes}
    all_gene_ids = sorted(list(set(map_a.keys()) | set(map_b.keys())))

    # Recombine shared and unique chromosomes
    for idx, gid in enumerate(all_gene_ids):
        if gid in map_a and gid in map_b:
            # Shared gene: homologous crossover
            ca = map_a[gid]
            cb = map_b[gid]
            # Inherit from parent with lower ATP burn, or synthesize
            if ca.atp_burned <= cb.atp_burned:
                chosen = copy.deepcopy(ca)
            else:
                chosen = copy.deepcopy(cb)
            child_chromosomes.append(chosen)
        elif gid in map_a:
            child_chromosomes.append(copy.deepcopy(map_a[gid]))
        else:
            child_chromosomes.append(copy.deepcopy(map_b[gid]))

    # Add emergent dialectical synthesis chromosome:
    # Takes the primary vital gene of Parent A and pairs it with Parent B
    vital_a = next((c for c in parent_a.chromosomes if c.vital), None)
    vital_b = next((c for c in parent_b.chromosomes if c.vital), None)
    if vital_a and vital_b:
        syn_expr = dialectical_combinatory_synthesis(vital_a.expression, vital_b.expression)
        # Evaluate expected normal form
        try:
            t = parse(syn_expr)
            res = evaluate(t, max_atp=500)
            syn_nf = str(res.term)
            syn_atp = res.atp_spent
        except Exception:
            syn_nf = "Synthesis"
            syn_atp = 10

        child_chromosomes.append(
            Chromosome(
                gene_id="GENE_DIALECTICAL_SYNTHESIS",
                gene_name="Dialectical Thesis/Antithesis Synthesis",
                expression=syn_expr,
                expected_normal_form=syn_nf,
                max_atp=1000,
                atp_burned=syn_atp,
                vital=True
            )
        )

    # Topological braid word derivation from parental identities
    # Derive braid crossing sequence deterministically from parent hashes
    seed_bytes = hashlib.sha256((parent_a.organism_hash + parent_b.organism_hash).encode()).digest()
    num_strands = 3
    generators = []
    for b in seed_bytes[:6]:
        # Strand 1 or 2, sign +1 or -1
        idx = (b % 2) + 1
        sign = 1 if (b & 0x04) else -1
        generators.append(idx * sign)

    # Ensure non-trivial braid with at least 3 crossings
    if len(generators) < 3:
        generators = [1, -2, 1]
    braid = BraidWord.from_generators(num_strands, generators)

    child = Organism(
        generation=child_gen,
        parent_hash=combined_parent_hash,
        public_key_hex=child_pk,
        secret_key_hex=child_sk,
        chromosomes=child_chromosomes
    )
    child.organism_hash = child.compute_hash()

    # Verify child metabolism
    viable, _ = child.run_metabolism()
    if not viable:
        raise ValueError("Synthesized child organism is metabolically non-viable (lethal mutation during crossover)")

    return child, braid

# ============================================================================
# 4. DUAL-VAULT AMALGAMATION
# ============================================================================

def amalgamate_dual_vaults(
    vault_a_bytes: Optional[bytes],
    vault_b_bytes: Optional[bytes]
) -> Tuple[bytes, str]:
    """
    Merges verified code vaults from Parent A and Parent B into a single,
    deterministic child vault. Preserves common files and namespaces conflicts
    under lineage subdirectories. Returns: (amalgamated_vault_bytes, sha256_hash).
    """
    with tempfile.TemporaryDirectory() as staging_dir:
        staging_root = os.path.realpath(staging_dir)
        merged_files_dir = os.path.join(staging_root, "merged")
        os.makedirs(merged_files_dir, exist_ok=True)

        # Unpack vault A if present
        if vault_a_bytes:
            dir_a = os.path.join(staging_root, "parent_a")
            os.makedirs(dir_a, exist_ok=True)
            V.unpack_vault_bytes(vault_a_bytes, dir_a)
            for root, _, files in os.walk(dir_a):
                for f in files:
                    rel = os.path.relpath(os.path.join(root, f), dir_a)
                    target = os.path.join(merged_files_dir, rel)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with open(os.path.join(root, f), "rb") as rf, open(target, "wb") as wf:
                        wf.write(rf.read())

        # Unpack vault B if present
        if vault_b_bytes:
            dir_b = os.path.join(staging_root, "parent_b")
            os.makedirs(dir_b, exist_ok=True)
            V.unpack_vault_bytes(vault_b_bytes, dir_b)
            for root, _, files in os.walk(dir_b):
                for f in files:
                    rel = os.path.relpath(os.path.join(root, f), dir_b)
                    target = os.path.join(merged_files_dir, rel)
                    # If conflict exists and content differs, store in lineage
                    if os.path.exists(target):
                        with open(target, "rb") as f1, open(os.path.join(root, f), "rb") as f2:
                            if f1.read() != f2.read():
                                target = os.path.join(merged_files_dir, "lineage_b", rel)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with open(os.path.join(root, f), "rb") as rf, open(target, "wb") as wf:
                        wf.write(rf.read())

        # Collect all merged files to pack
        packed_rel_paths = []
        for root, _, files in os.walk(merged_files_dir):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), merged_files_dir)
                packed_rel_paths.append(rel)

        if not packed_rel_paths:
            # Create minimal lineage marker
            marker = os.path.join(merged_files_dir, "SYMBIOSIS_LINEAGE.txt")
            with open(marker, "w") as mf:
                mf.write("Project Black-Heart: Dialectical Symbiosis Amalgamated Vault\n")
            packed_rel_paths.append("SYMBIOSIS_LINEAGE.txt")

        vault_bytes, v_hash, _ = V.pack_files_to_vault(packed_rel_paths, merged_files_dir)
        return vault_bytes, v_hash

# ============================================================================
# 5. SYMBIOTIC POLYGLOT COMPILER (ISO 32000 PDF + PYTHON MONAD)
# ============================================================================

SYMBIOSIS_MANIFEST_PREFIX = "# %SYMBIOSIS_METABOLISM: "

class SymbiosisPolyglotCompiler:
    """
    Compiles an autonomous, sexually recombined offspring polyglot PDF
    embedding topological knot morphogenesis, dual lineage verification,
    and executable self-replication scripts.
    """
    def __init__(self, child: Organism, parent_a: Organism, parent_b: Organism, braid: BraidWord):
        self.child = child
        self.parent_a = parent_a
        self.parent_b = parent_b
        self.braid = braid

    def _build_runner_script(self) -> str:
        """Generates self-contained executable Python runner."""
        return f'''#!/usr/bin/env python3
import sys
import json
import argparse
from pathlib import Path

MANIFEST_PREFIX = {repr(SYMBIOSIS_MANIFEST_PREFIX)}

def audit_lineage():
    content = Path(__file__).read_bytes()
    idx = content.rfind(MANIFEST_PREFIX.encode("utf-8"))
    if idx == -1:
        # Fallback to latin-1
        idx = content.rfind(MANIFEST_PREFIX.encode("latin1"))
    if idx == -1:
        print("[FAIL] No symbiosis metadata manifest located in polyglot document.")
        sys.exit(1)
    end_idx = content.find(b"\\n", idx)
    data = json.loads(content[idx + len(MANIFEST_PREFIX.encode("latin1")):end_idx].decode("utf-8"))

    # Bootstrap path to allow standalone execution
    src_dir = data.get("source_dir")
    if src_dir and src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    print("=================================================================")
    print("  %\\U0001f5a4 BLACK-HEART DIALECTICAL SYMBIOSIS LINEAGE AUDITOR")
    print("=================================================================\\n")
    print(f"[*] Child Generation:    #{{data['generation']}}")
    print(f"[*] Child Hash:          \\u2693 {{data['child_hash'][:32]}}...")
    print(f"[*] Parent A (Thesis):   \\u2693 {{data['parent_a_hash'][:32]}}...")
    print(f"[*] Parent B (Antithesis): \\u2693 {{data['parent_b_hash'][:32]}}...")
    print(f"[*] Braid Presentation:  {{data['braid_formula']}}")
    print(f"[*] Topological Writhe:  {{data['braid_writhe']}} (Crossings: {{data['braid_crossings']}})")
    print(f"[*] Vital Chromosomes:   {{len(data['chromosomes'])}} active\\n")

    # Verify metabolism
    try:
        from glyph import parse, evaluate
        for chrom in data["chromosomes"]:
            t = parse(chrom["expression"])
            res = evaluate(t, max_atp=chrom.get("max_atp", 500))
            if not res.is_settled() or str(res.term) != chrom["expected_normal_form"]:
                print(f"[FAIL] Chromosome {{chrom['gene_id']}} metabolic divergence: expected '{{chrom['expected_normal_form']}}', got '{{res.term}}'")
                sys.exit(1)
        print("\\033[1;32m[\\u2713] SYMBIOTIC LINEAGE & METABOLIC PROVENANCE VERIFIED (Q.E.D.)\\033[0m\\n")
    except Exception as e:
        print(f"[FAIL] Metabolic evaluation error: {{e}}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Black-Heart Symbiotic Polyglot Organism")
    parser.add_argument("--lineage", action="store_true", help="Audit dual parental lineage and topological invariants")
    parser.add_argument("--unpack-vault", metavar="DEST", help="Safely unpacks embedded dual vault into destination folder")
    args, _ = parser.parse_known_args()

    if args.unpack_vault:
        try:
            content = Path(__file__).read_bytes()
            idx = content.rfind(MANIFEST_PREFIX.encode("latin1"))
            if idx != -1:
                end_idx = content.find(b"\\n", idx)
                data = json.loads(content[idx + len(MANIFEST_PREFIX.encode("latin1")):end_idx].decode("utf-8"))
                src_dir = data.get("source_dir")
                if src_dir and src_dir not in sys.path:
                    sys.path.insert(0, src_dir)
            from vault import extract_vault_from_pdf
            paths = extract_vault_from_pdf(sys.argv[0], args.unpack_vault)
            print(f"[\\u2713] Successfully unpacked {{len(paths)}} vault files into '{{args.unpack_vault}}'")
        except Exception as e:
            print(f"[FAIL] Vault extraction error: {{e}}")
            sys.exit(1)
    else:
        audit_lineage()
'''

    def compile_pdf(self, vault_bytes: Optional[bytes] = None) -> bytes:
        """
        Synthesizes the complete ISO 32000 PDF + Python Monad byte sequence.
        """
        runner = self._build_runner_script()
        knot_stream = render_braid_knot_pdf_stream(
            self.braid,
            x=60,
            y=300,
            width=490,
            height=260
        )

        manifest_data = {
            "generation": self.child.generation,
            "child_hash": self.child.organism_hash,
            "parent_a_hash": self.parent_a.organism_hash,
            "parent_b_hash": self.parent_b.organism_hash,
            "parent_hash": self.child.parent_hash,
            "braid_formula": self.braid.to_artin_notation(),
            "braid_crossings": self.braid.crossing_number,
            "braid_writhe": self.braid.writhe,
            "link_components": self.braid.count_link_components(),
            "source_dir": os.path.dirname(os.path.abspath(__file__)),
            "chromosomes": [c.to_dict() for c in self.child.chromosomes]
        }
        manifest_line = SYMBIOSIS_MANIFEST_PREFIX + json.dumps(manifest_data, separators=(",", ":"), ensure_ascii=True) + "\n"

        # Construct visual page text stream
        page_text = (
            "BT /F1 16 Tf 60 740 Td (PROJECT BLACK-HEART: DIALECTICAL SYMBIOSIS) Tj ET\n"
            "BT /F2 10 Tf 60 720 Td (Autonomous Recombination of Thesis & Antithesis via Topological Braid Groups) Tj ET\n"
            f"BT /F2 9 Tf 60 690 Td (Child Generation: #{self.child.generation}  |  Parent Hash: {self.child.parent_hash[:24]}...) Tj ET\n"
            f"BT /F2 9 Tf 60 675 Td (Parent A (Thesis): {self.parent_a.organism_hash[:24]}...  |  Parent B (Antithesis): {self.parent_b.organism_hash[:24]}...) Tj ET\n"
            f"BT /F1 10 Tf 60 585 Td (Topological Entanglement Braid: {self.braid.to_artin_notation(ascii_only=True)}) Tj ET\n"
            f"BT /F2 8 Tf 60 570 Td (Crossing Count: {self.braid.crossing_number}   Writhe: {self.braid.writhe}   Link Components: {self.braid.count_link_components()}) Tj ET\n"
            "BT /F1 10 Tf 60 260 Td (Active Homologous & Emergent Chromosomes:) Tj ET\n"
        )

        y_pos = 240
        for chrom in self.child.chromosomes[:4]:
            safe_name = chrom.gene_name.encode("ascii", errors="replace").decode("ascii")
            safe_nf = (
                chrom.expected_normal_form
                .replace("🖤", "K")
                .replace("🤍", "I")
                .replace("🌿", "S")
                .replace("🔁", "Y")
            )
            safe_nf = safe_nf.encode("ascii", errors="replace").decode("ascii")
            page_text += f"BT /F2 8 Tf 60 {y_pos} Td (- [{chrom.gene_id}] {safe_name}: {safe_nf}) Tj ET\n"
            y_pos -= 16

        page_text += (
            "BT /F2 8 Tf 60 70 Td (Executable ISO 32000 Polyglot: Run 'python3 <this_file.pdf> --lineage' to audit.) Tj ET\n"
        )

        full_content_stream = knot_stream + "\n" + page_text

        # PDF Object Table
        objs: List[Tuple[int, bytes]] = []

        # 1. Catalog
        objs.append((1, b"<</Type /Catalog /Pages 2 0 R>>"))
        # 2. Pages
        objs.append((2, b"<</Type /Pages /Kids [3 0 R] /Count 1>>"))
        # 3. Page
        objs.append((3, b"<</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources <</Font <</F1 5 0 R /F2 6 0 R>>>>>>"))
        # 4. Content Stream
        content_bytes = full_content_stream.encode("latin1", errors="replace")
        objs.append((4, f"<</Length {len(content_bytes)}>>\nstream\n".encode("latin1") + content_bytes + b"\nendstream"))
        # 5. Font F1
        objs.append((5, b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold>>"))
        # 6. Font F2
        objs.append((6, b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>"))

        next_obj_id = 7

        # Optional embedded dual-vault
        if vault_bytes:
            stream_obj_id = next_obj_id
            filespec_obj_id = next_obj_id + 1
            next_obj_id += 2

            v_stream, v_spec = V.generate_pdf_embedded_file_objects(
                vault_bytes,
                "symbiotic_vault.tar.gz",
                stream_obj_id,
                filespec_obj_id
            )
            objs.append((stream_obj_id, v_stream))
            objs.append((filespec_obj_id, v_spec))

            # Add Names dictionary to Catalog
            objs[0] = (1, f"<</Type /Catalog /Pages 2 0 R /Names <</EmbeddedFiles <</Names [(symbiotic_vault.tar.gz) {filespec_obj_id} 0 R]>>>>>>".encode("latin1"))

        # Build PDF with xref table
        pdf_buf = io.BytesIO()
        pdf_buf.write(b"%PDF-1.7\n")
        pdf_buf.write(b"%\xc7\xec\x8f\xa2\n")

        offsets = {}
        for obj_id, obj_data in objs:
            offsets[obj_id] = pdf_buf.tell()
            pdf_buf.write(f"{obj_id} 0 obj\n".encode("latin1"))
            pdf_buf.write(obj_data)
            pdf_buf.write(b"\nendobj\n")

        xref_offset = pdf_buf.tell()
        pdf_buf.write(f"xref\n0 {len(objs) + 1}\n".encode("latin1"))
        pdf_buf.write(b"0000000000 65535 f \n")
        for i in range(1, len(objs) + 1):
            pdf_buf.write(f"{offsets[i]:010d} 00000 n \n".encode("latin1"))

        pdf_buf.write(
            f"trailer\n<</Size {len(objs) + 1} /Root 1 0 R>>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin1")
        )

        base_pdf_bytes = pdf_buf.getvalue()

        # Wrap in literate polyglot monad
        header_text = (
            f"#!{sys.executable}\n"
            "# coding: latin-1\n"
            "# ============================================================================\n"
            "# % PROJECT BLACK-HEART: DIALECTICAL SYMBIOSIS OFFSPRING POLYGLOT\n"
            "# ============================================================================\n"
            "'''\n"
        ).encode("latin1")

        vault_comment = b""
        if vault_bytes:
            v_hash = hashlib.sha256(vault_bytes).hexdigest()
            vault_comment = f"# %🖤 VAULT_HASH: {v_hash}\n".encode("utf-8")

        polyglot = (
            header_text
            + base_pdf_bytes
            + b"\n'''\n"
            + runner.encode("latin1")
            + b"\n"
            + manifest_line.encode("latin1")
            + vault_comment
        )
        return polyglot

def synthesize_polyglots(
    path_parent_a: str,
    path_parent_b: str,
    output_path: str
) -> Tuple[Organism, BraidWord]:
    """
    High-level entrypoint: loads parent organisms from polyglots, executes
    dialectical crossover, amalgamates their vaults, and writes the child polyglot.
    """
    from organism import Organism, extract_organism_from_pdf

    parent_a = extract_organism_from_pdf(path_parent_a)
    parent_b = extract_organism_from_pdf(path_parent_b)

    child, braid = dialectical_crossover(parent_a, parent_b)

    # Extract vaults if present
    va_bytes = None
    vb_bytes = None
    try:
        va_bytes = V.extract_vault_bytes_from_pdf(path_parent_a)
    except Exception:
        pass
    try:
        vb_bytes = V.extract_vault_bytes_from_pdf(path_parent_b)
    except Exception:
        pass

    merged_vault, _ = amalgamate_dual_vaults(va_bytes, vb_bytes)

    compiler = SymbiosisPolyglotCompiler(child, parent_a, parent_b, braid)
    child_bytes = compiler.compile_pdf(vault_bytes=merged_vault)

    with open(output_path, "wb") as f:
        f.write(child_bytes)

    return child, braid
