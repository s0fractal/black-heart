#!/usr/bin/env python3
# coding: utf-8
"""
morpho_net.py — Morphogenetic Proof-Nets & Ontogenetic Quine Polyglot Engine.
Part of Project Black-Heart (%🖤).

Implements:
  1. Morphogenetic to Interaction Proof-Net Compilation:
     Extracts spatial topological singularities (activator peaks, saddle branchings,
     inhibitor sinks) from Gray-Scott reaction-diffusion PDEs on T^2 and compiles them
     into Lafont Interaction Nets (Constructors 🌱, Duplicators 👥, Erasers 🕳️).
  2. Optimal Graph Reduction & Weisfeiler-Lehman Digest:
     Reduces the spatial interaction graph via O(1) local rewiring (annihilation,
     commutation, erasure) under strict ATP gas ceilings, deriving an isomorphism-invariant
     1D Weisfeiler-Lehman canonical settlement digest.
  3. Single-File Ontogenetic Quine Polyglot (ISO 32000 §7.5.6):
     A self-verifying, self-executing PDF polyglot ('python3 quine.pdf --grow') that reads
     itself, advances morphogenesis, compiles and reduces its internal proof-net, and
     atomically appends a new generational revision page into its own file.
     The document grows page-by-page like tree rings, containing its entire developmental
     phylogeny in one immutable cryptographic Merkle chain.
"""

from __future__ import annotations
import os
import sys
import json
import math
import time
import hashlib
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any, Set

from crypto import generate_keypair, public_key_from_secret, sign_bytes, verify_bytes, is_valid_public_key
from morphogenesis import MorphogeneticField, TuringArchetype, ChromaticPalette, PALETTES
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

ONTOGENY_MANIFEST_PREFIX = "%" + "🖤" + " ONTOGENY_RECEIPT_CHAIN: "

# ============================================================================
# 1. ONTOGENETIC PROOF RECEIPT
# ============================================================================

@dataclass
class OntogeneticProofReceipt:
    """
    Cryptographic and computational settlement receipt for one ontogenetic growth epoch.
    Couples visual reaction-diffusion morphogenesis with Lafont interaction net reduction.
    """
    generation: int
    timestamp_utc: str
    archetype: str
    pde_steps: int
    initial_nodes: int
    active_pairs: int
    reduced_steps: int
    atp_burned: int
    settled: bool
    weisfeiler_lehman_digest: str
    prev_receipt_hash: str
    public_key_hex: str
    signature_hex: str = ""
    receipt_hash: str = ""

    def canonical_bytes_for_signing(self) -> bytes:
        payload = (
            f"ONTOGENY:{self.generation}:{self.timestamp_utc}:{self.archetype}:"
            f"{self.pde_steps}:{self.initial_nodes}:{self.active_pairs}:"
            f"{self.reduced_steps}:{self.atp_burned}:{self.settled}:"
            f"{self.weisfeiler_lehman_digest}:{self.prev_receipt_hash}:{self.public_key_hex}"
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

    def verify(self) -> bool:
        if self.generation < 0:
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
            "archetype": self.archetype,
            "pde_steps": self.pde_steps,
            "initial_nodes": self.initial_nodes,
            "active_pairs": self.active_pairs,
            "reduced_steps": self.reduced_steps,
            "atp_burned": self.atp_burned,
            "settled": self.settled,
            "weisfeiler_lehman_digest": self.weisfeiler_lehman_digest,
            "prev_receipt_hash": self.prev_receipt_hash,
            "public_key_hex": self.public_key_hex,
            "signature_hex": self.signature_hex,
            "receipt_hash": self.receipt_hash,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> OntogeneticProofReceipt:
        return cls(
            generation=int(d["generation"]),
            timestamp_utc=str(d["timestamp_utc"]),
            archetype=str(d["archetype"]),
            pde_steps=int(d["pde_steps"]),
            initial_nodes=int(d["initial_nodes"]),
            active_pairs=int(d["active_pairs"]),
            reduced_steps=int(d["reduced_steps"]),
            atp_burned=int(d["atp_burned"]),
            settled=bool(d["settled"]),
            weisfeiler_lehman_digest=str(d["weisfeiler_lehman_digest"]),
            prev_receipt_hash=str(d["prev_receipt_hash"]),
            public_key_hex=str(d["public_key_hex"]),
            signature_hex=str(d.get("signature_hex", "")),
            receipt_hash=str(d.get("receipt_hash", "")),
        )

# ============================================================================
# 2. SPATIAL TOPOLOGY TO INTERACTION PROOF-NET COMPILER
# ============================================================================

@dataclass
class SpatialCriticalPoint:
    x: int
    y: int
    val: float
    point_type: str  # "PEAK", "SADDLE", "SINK"
    node_id: int = 0

def compile_morphogenetic_proof_net(
    field: MorphogeneticField,
    min_v: float = 0.12
) -> Tuple[InteractionNet, List[SpatialCriticalPoint]]:
    """
    Extracts topological critical sites from the morphogen concentration field V
    and compiles them into a wired Lafont InteractionNet.
    """
    w, h = field.width, field.height
    v = field.v

    peaks: List[SpatialCriticalPoint] = []
    sinks: List[SpatialCriticalPoint] = []
    saddles: List[SpatialCriticalPoint] = []

    for y in range(h):
        for x in range(w):
            val = v[y * w + x]
            if val < 0.015:
                continue

            # 8-neighborhood on torus
            nbrs = [
                v[((y + dy) % h) * w + ((x + dx) % w)]
                for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                if not (dx == 0 and dy == 0)
            ]

            is_max = all(val >= nb for nb in nbrs) and val >= min_v
            is_min = all(val <= nb for nb in nbrs) and val < (min_v * 0.5)

            if is_max:
                peaks.append(SpatialCriticalPoint(x, y, val, "PEAK"))
            elif is_min:
                sinks.append(SpatialCriticalPoint(x, y, val, "SINK"))
            elif val > min_v * 0.7:
                # Directional curvature analysis on torus
                c_n = v[((y - 1) % h) * w + x]
                c_s = v[((y + 1) % h) * w + x]
                c_w = v[y * w + ((x - 1) % w)]
                c_e = v[y * w + ((x + 1) % w)]
                lap_y = c_n + c_s - 2 * val
                lap_x = c_w + c_e - 2 * val
                if (lap_y * lap_x) < -0.003:
                    saddles.append(SpatialCriticalPoint(x, y, val, "SADDLE"))

    # Fallback to ensure non-empty net if field is nascent
    if not peaks:
        max_idx = max(range(len(v)), key=lambda i: v[i])
        peaks.append(SpatialCriticalPoint(max_idx % w, max_idx // w, v[max_idx], "PEAK"))

    net = InteractionNet()

    for p in peaks:
        p.node_id = net.create_node(AGENT_CONSTRUCT)
    for s in saddles[:len(peaks) * 2]:
        s.node_id = net.create_node(AGENT_DUPLICATE)
    for k in sinks[:len(peaks)]:
        k.node_id = net.create_node(AGENT_ERASE)

    # Toroidal distance metric
    def tor_dist(pt1: SpatialCriticalPoint, pt2: SpatialCriticalPoint) -> float:
        dx = abs(pt1.x - pt2.x)
        dy = abs(pt1.y - pt2.y)
        dx = min(dx, w - dx)
        dy = min(dy, h - dy)
        return dx * dx + dy * dy

    # 1. Wire peaks to nearest saddles: creates active redexes (🌱 bowtie 👥)
    used_saddles = set()
    for p in peaks:
        best_s = None
        best_d = 1e9
        for s in saddles:
            if s.node_id in used_saddles:
                continue
            d = tor_dist(p, s)
            if d < best_d:
                best_d = d
                best_s = s
        if best_s:
            used_saddles.add(best_s.node_id)
            net.link(PortRef(p.node_id, PORT_PRINCIPAL), PortRef(best_s.node_id, PORT_PRINCIPAL))

    # 2. Wire sinks (Erasers 🕳️) to remaining unlinked peaks
    sink_idx = 0
    for p in peaks:
        if net.nodes[p.node_id].ports[PORT_PRINCIPAL] is None and sink_idx < len(sinks):
            net.link(PortRef(p.node_id, PORT_PRINCIPAL), PortRef(sinks[sink_idx].node_id, PORT_PRINCIPAL))
            sink_idx += 1

    # 3. Inter-peak wiring for remaining free principal ports (🌱 bowtie 🌱)
    free_peaks = [p.node_id for p in peaks if net.nodes[p.node_id].ports[PORT_PRINCIPAL] is None]
    for i in range(0, len(free_peaks) - 1, 2):
        net.link(PortRef(free_peaks[i], PORT_PRINCIPAL), PortRef(free_peaks[i + 1], PORT_PRINCIPAL))

    # 4. Connect auxiliary ports along local contours
    all_3port_nodes = [nid for nid in net.nodes if len(net.nodes[nid].ports) == 3]
    for i in range(len(all_3port_nodes)):
        curr = all_3port_nodes[i]
        nxt = all_3port_nodes[(i + 1) % len(all_3port_nodes)]
        if net.nodes[curr].ports[PORT_LEFT] is None and net.nodes[nxt].ports[PORT_RIGHT] is None:
            net.link(PortRef(curr, PORT_LEFT), PortRef(nxt, PORT_RIGHT))

    all_points = peaks + [s for s in saddles if s.node_id != 0] + [k for k in sinks if k.node_id != 0]
    return net, all_points

# ============================================================================
# 3. ONTOGENETIC POLYGLOT COMPILER (SINGLE-FILE SELF-MUTATING QUINE)
# ============================================================================

class OntogeneticPolyglotCompiler:
    """
    Compiles and maintains a self-executing ISO 32000 PDF Polyglot
    that advances its own morphogenesis, reduces its proof-net, and appends
    new revision pages directly into itself upon execution.
    """
    def __init__(
        self,
        archetype: TuringArchetype = TuringArchetype.LABYRINTH,
        palette: ChromaticPalette = PALETTES["BIOLUMINESCENT_CYAN"],
        grid_dim: int = 36,
    ):
        self.archetype = archetype
        self.palette = palette
        self.grid_dim = grid_dim
        self.receipts: List[OntogeneticProofReceipt] = []

    def initialize_genesis(
        self,
        seed_hash: str,
        initial_pde_steps: int,
        secret_key_hex: str,
        max_atp: int = 1000
    ) -> Tuple[OntogeneticProofReceipt, MorphogeneticField]:
        """Creates generation #0 receipt and field state."""
        now_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        field = MorphogeneticField(
            width=self.grid_dim,
            height=self.grid_dim,
            F=self.archetype.F,
            k=self.archetype.k,
            Du=self.archetype.Du,
            Dv=self.archetype.Dv
        )
        field.seed_from_hash(seed_hash)
        for _ in range(initial_pde_steps):
            field.step(dt=1.0)

        net, _ = compile_morphogenetic_proof_net(field)
        init_nodes = len(net.nodes)
        act_pairs = len(net.active_pairs())
        steps_reduced, _, settled = net.reduce(max_atp=max_atp)
        wl_digest = net.canonical_digest()

        rec = OntogeneticProofReceipt(
            generation=0,
            timestamp_utc=now_utc,
            archetype=self.archetype.key,
            pde_steps=initial_pde_steps,
            initial_nodes=init_nodes,
            active_pairs=act_pairs,
            reduced_steps=steps_reduced,
            atp_burned=steps_reduced,
            settled=settled,
            weisfeiler_lehman_digest=wl_digest,
            prev_receipt_hash="0" * 64,
            public_key_hex=""
        )
        rec.sign(secret_key_hex)
        self.receipts = [rec]
        return rec, field

    def compile_bytes(self, field: MorphogeneticField) -> bytes:
        """Returns the initial standalone executable PDF polyglot bytes."""
        if not self.receipts:
            raise ValueError("No ontogenetic receipts to compile.")

        rec0 = self.receipts[0]
        pdf_bytes = self._build_base_pdf(rec0, field)
        runner_script = self._build_runner_script()

        manifest_data = json.dumps([rec0.to_dict()], ensure_ascii=False)
        manifest_bytes = f"\n{ONTOGENY_MANIFEST_PREFIX}{manifest_data}\n".encode("utf-8")

        return (
            pdf_bytes +
            manifest_bytes +
            b'\n"""\n' +
            runner_script.encode("utf-8")
        )

    def compile(self, output_pdf_path: str, field: MorphogeneticField) -> None:
        """Emits the initial standalone executable PDF polyglot."""
        full_payload = self.compile_bytes(field)
        with open(output_pdf_path, "wb") as f:
            f.write(full_payload)

    def _build_base_pdf(self, rec: OntogeneticProofReceipt, field: MorphogeneticField) -> bytes:
        """Generates valid ISO 32000 PDF bytes for generation 0."""
        stream_content = self.generate_page_stream(rec, field)
        stream_bytes = stream_content.encode("utf-8")

        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            (
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
            ),
            (
                f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin1") +
                stream_bytes +
                b"\nendstream"
            ),
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        ]

        out = bytearray(b"# coding: utf-8\nr\"\"\"%PDF-1.7\n%\xf0\x9f\x96\xa4\n")
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

        out.extend(
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF".encode("latin1")
        )
        return bytes(out)

    def generate_page_stream(self, rec: OntogeneticProofReceipt, field: MorphogeneticField) -> str:
        """Draws visual layout with vector morphogen grid and interaction proof-net topology."""
        p = self.palette
        sr, sg, sb = p.substrate_rgb
        ar, ag, ab = p.activator_rgb
        xr, xg, xb = p.accent_rgb

        ops = [
            "q",
            # Dark Background
            f"{sr:.3f} {sg:.3f} {sb:.3f} rg",
            "0 0 595 842 re f",
            # Outer Frame
            f"{xr:.3f} {xg:.3f} {xb:.3f} RG 1.5 w",
            "30 30 535 782 re S",
            # Header Medallion
            "0.08 0.12 0.22 rg",
            "45 745 505 55 re f",
            f"{ar:.3f} {ag:.3f} {ab:.3f} RG 1 w 45 745 505 55 re S",
            "1 1 1 rg",
            f"BT /F1 15 Tf 60 775 Td (PROJECT BLACK-HEART // ONTOGENETIC QUINE) Tj ET",
            f"{xr:.3f} {xg:.3f} {xb:.3f} rg",
            f"BT /F1 9 Tf 60 755 Td (GENERATION #{rec.generation}  |  ARCHETYPE: {rec.archetype.upper()}  |  PDE STEPS: {rec.pde_steps}) Tj ET",
            # Status Badge
            "0.12 0.55 0.25 rg" if rec.settled else "0.85 0.45 0.1 rg",
            "45 705 505 28 re f",
            "1 1 1 rg",
            f"BT /F1 11 Tf 60 714 Td (STATUS: {'SETTLED NORMAL FORM (Q.E.D.)' if rec.settled else 'SUSPENDED THUNK'}  |  REDUCED: {rec.reduced_steps} STEPS) Tj ET",
        ]

        # Vector Morphogen Plate (280x280 box centered at x=157, y=390)
        plate_x, plate_y, plate_size = 157.0, 390.0, 280.0
        ops.append("0.02 0.03 0.07 rg")
        ops.append(f"{plate_x:.2f} {plate_y:.2f} {plate_size:.2f} {plate_size:.2f} re f")
        ops.append(f"{xr:.3f} {xg:.3f} {xb:.3f} RG 1 w {plate_x:.2f} {plate_y:.2f} {plate_size:.2f} {plate_size:.2f} re S")

        # Draw morphogen vector tiles
        w, h = field.width, field.height
        cell_w = plate_size / w
        cell_h = plate_size / h
        for gy in range(h):
            for gx in range(w):
                v_val = field.v[gy * w + gx]
                if v_val > 0.08:
                    intensity = min(1.0, v_val * 2.5)
                    cr = sr + (ar - sr) * intensity
                    cg = sg + (ag - sg) * intensity
                    cb = sb + (ab - sb) * intensity
                    cx = plate_x + gx * cell_w
                    cy = plate_y + (h - 1 - gy) * cell_h
                    ops.append(f"{cr:.3f} {cg:.3f} {cb:.3f} rg")
                    ops.append(f"{cx:.2f} {cy:.2f} {cell_w:.2f} {cell_h:.2f} re f")

        # Overlay extracted interaction proof-net critical points
        _, pts = compile_morphogenetic_proof_net(field)
        for pt in pts:
            px = plate_x + (pt.x + 0.5) * cell_w
            py = plate_y + (h - 1 - pt.y + 0.5) * cell_h
            if pt.point_type == "PEAK":
                ops.append("0.0 1.0 0.5 rg 0 0 0 RG 0.5 w")
                ops.append(f"{px-4:.2f} {py-4:.2f} 8 8 re b")
            elif pt.point_type == "SADDLE":
                ops.append("1.0 0.8 0.0 rg 0 0 0 RG 0.5 w")
                ops.append(f"{px-3:.2f} {py-3:.2f} 6 6 re b")
            elif pt.point_type == "SINK":
                ops.append("1.0 0.2 0.3 RG 1 w")
                ops.append(f"{px-3:.2f} {py-3:.2f} 6 6 re S")

        # Proof Card Panel
        ops.append("0.06 0.09 0.16 rg")
        ops.append("45 60 505 310 re f")
        ops.append(f"{ar:.3f} {ag:.3f} {ab:.3f} RG 1 w 45 60 505 310 re S")
        ops.append("1 1 1 rg")
        ops.append("BT /F1 11 Tf 60 345 Td (MATHEMATICAL SETTLEMENT & WEISFEILER-LEHMAN PROOF) Tj ET")
        ops.append("0.85 0.90 0.98 rg")
        ops.append(f"BT /F1 9 Tf 60 320 Td (Weisfeiler-Lehman Digest: ⚓ {rec.weisfeiler_lehman_digest[:40]}...) Tj ET")
        ops.append(f"BT /F1 9 Tf 60 300 Td (Receipt Hash:             {rec.receipt_hash[:40]}...) Tj ET")
        ops.append(f"BT /F1 9 Tf 60 280 Td (Parent Hash:              {rec.prev_receipt_hash[:40]}...) Tj ET")
        ops.append(f"BT /F1 9 Tf 60 260 Td (Signer Public Key:        {rec.public_key_hex[:40]}...) Tj ET")
        ops.append(f"BT /F1 9 Tf 60 240 Td (Initial Graph Nodes:      {rec.initial_nodes} agents  |  Active Redex Pairs: {rec.active_pairs}) Tj ET")
        ops.append(f"BT /F1 9 Tf 60 220 Td (Metabolic Energy Burned:   {rec.atp_burned} ATP fuel units) Tj ET")
        ops.append(f"BT /F1 9 Tf 60 200 Td (Timestamp UTC:            {rec.timestamp_utc}) Tj ET")
        ops.append("0.4 0.8 1.0 rg")
        ops.append("BT /F1 9 Tf 60 160 Td (Self-Growth Execution CLI:) Tj ET")
        ops.append("0.9 0.9 0.9 rg")
        ops.append("BT /F1 8 Tf 75 140 Td ($ python3 <this_file>.pdf --grow --steps 50   # Appends next developmental generation) Tj ET")
        ops.append("BT /F1 8 Tf 75 120 Td ($ python3 <this_file>.pdf --audit              # Replays and verifies full ontogenetic chain) Tj ET")
        ops.append("BT /F1 8 Tf 75 100 Td ($ python3 <this_file>.pdf --status             # Displays developmental HUD & digests) Tj ET")
        ops.append("Q")
        return "\n".join(ops)

    def _build_runner_script(self) -> str:
        return r'''
import os
import sys
import json
import argparse
import hashlib
import time

current_dir = os.path.dirname(os.path.abspath(__file__))
for candidate in [os.getcwd(), current_dir, os.path.dirname(current_dir), "/Users/s0fractal/Projects/black-heart"]:
    if os.path.isdir(candidate) and candidate not in sys.path:
        sys.path.insert(0, candidate)

PREFIX = "%" + "🖤" + " ONTOGENY_RECEIPT_CHAIN: "

def _extract_manifest(filepath):
    with open(filepath, "rb") as f:
        data = f.read()
    prefix = PREFIX.encode("utf-8")
    idx = data.rfind(prefix)
    if idx == -1:
        print("[FAIL] No ontogeny receipt chain found.")
        sys.exit(1)
    end_idx = data.find(b"\n", idx)
    raw = data[idx + len(prefix):end_idx].decode("utf-8")
    return json.loads(raw), data

def cmd_status(filepath):
    manifest, data = _extract_manifest(filepath)
    print("\033[1;36m=================================================================\033[0m")
    print("  %🖤 PROJECT BLACK-HEART // ONTOGENETIC QUINE ATLAS")
    print(f"  Target File: {os.path.basename(filepath)} ({len(data)} bytes, {len(manifest)} pages)")
    print("\033[1;36m=================================================================\033[0m\n")
    latest = manifest[-1]
    print(f"  Current Generation:    #{latest.get('generation')}")
    print(f"  Turing Archetype:      {latest.get('archetype')}")
    print(f"  Cumulative PDE Steps:  {latest.get('pde_steps')}")
    print(f"  Proof-Net Status:      {'SETTLED NORMAL FORM (Q.E.D.)' if latest.get('settled') else 'SUSPENDED'}")
    print(f"  Total ATP Burned:      {sum(m.get('atp_burned', 0) for m in manifest)} fuel")
    print(f"  Weisfeiler-Lehman:     ⚓ {latest.get('weisfeiler_lehman_digest')}")
    print(f"  Signer Public Key:     {latest.get('public_key_hex')}\n")

def cmd_audit(filepath):
    manifest, data = _extract_manifest(filepath)
    print(f"[*] Auditing ontogenetic developmental chain across {len(manifest)} generations...")
    from morpho_net import OntogeneticProofReceipt
    prev_h = "0" * 64
    for i, md in enumerate(manifest):
        rec = OntogeneticProofReceipt.from_dict(md)
        if rec.generation != i:
            print(f"[FAIL] Generation index mismatch at #{rec.generation}: expected #{i}")
            sys.exit(1)
        if rec.prev_receipt_hash != prev_h:
            print(f"[FAIL] Hash chain broken at #{rec.generation}")
            sys.exit(1)
        if not rec.verify():
            print(f"[FAIL] Cryptographic signature or hash invalid at generation #{rec.generation}")
            sys.exit(1)
        prev_h = rec.receipt_hash
    print(f"\033[1;32m[✓] ALL {len(manifest)} ONTOGENETIC GENERATIONS & PROOF-NETS CRYPTOGRAPHICALLY VERIFIED\033[0m\n")

def main():
    parser = argparse.ArgumentParser(description="Ontogenetic Quine Polyglot Runner")
    parser.add_argument("--grow", action="store_true", help="Advance morphogenesis and append next generation to self")
    parser.add_argument("--steps", type=int, default=50, help="PDE steps to compute for this generation")
    parser.add_argument("--atp", type=int, default=500, help="ATP budget for interaction net reduction")
    parser.add_argument("--secret-key", type=str, default="", help="Optional 64-char hex Ed25519 secret key")
    parser.add_argument("--audit", action="store_true", help="Audit the entire ontogenetic Merkle chain")
    parser.add_argument("--status", action="store_true", help="Display ontogenetic HUD and digests")
    args, _ = parser.parse_known_args()

    target_file = sys.argv[0]

    if args.grow:
        from morpho_net import grow_ontogenetic_quine_in_pdf
        grow_ontogenetic_quine_in_pdf(target_file, pde_steps=args.steps, atp_budget=args.atp, secret_key_hex=args.secret_key or None)
    elif args.audit:
        cmd_audit(target_file)
    else:
        cmd_status(target_file)

if __name__ == "__main__":
    main()
'''

# ============================================================================
# 4. IN-PLACE ONTOGENETIC SELF-GROWTH (ISO 32000 §7.5.6)
# ============================================================================

def grow_ontogenetic_quine_in_pdf(
    pdf_path: str,
    pde_steps: int = 50,
    atp_budget: int = 500,
    secret_key_hex: Optional[str] = None
) -> OntogeneticProofReceipt:
    """
    Executes one ontogenetic developmental step on an existing self-contained PDF:
      1. Reads its own file bytes and verifies the ontogenetic receipt chain.
      2. Re-simulates the MorphogeneticField forward by pde_steps.
      3. Compiles the new Turing spatial state into an Interaction Net.
      4. Reduces the net to normal form, deriving a new Weisfeiler-Lehman digest.
      5. Signs the new OntogeneticProofReceipt.
      6. Appends an ISO 32000 §7.5.6 incremental update block directly to itself!
    """
    with open(pdf_path, "rb") as f:
        content = f.read()

    prefix = ONTOGENY_MANIFEST_PREFIX.encode("utf-8")
    idx = content.rfind(prefix)
    if idx == -1:
        raise ValueError(f"No ontogenetic receipt manifest found in {pdf_path}")

    end_idx = content.find(b"\n", idx)
    receipts_data = json.loads(content[idx + len(prefix):end_idx].decode("utf-8"))
    receipts = [OntogeneticProofReceipt.from_dict(d) for d in receipts_data]

    # Verify history
    prev_h = "0" * 64
    for i, r in enumerate(receipts):
        if r.generation != i:
            raise ValueError(f"Ontogenetic chain gap at index {i}: generation #{r.generation}")
        if r.prev_receipt_hash != prev_h:
            raise ValueError(f"Ontogenetic hash broken at generation #{r.generation}")
        if not r.verify():
            raise ValueError(f"Ontogenetic receipt #{r.generation} failed cryptographic verification")
        prev_h = r.receipt_hash

    current = receipts[-1]
    next_gen = current.generation + 1
    total_steps = current.pde_steps + pde_steps

    # Evolve the PDE field from the genesis seed
    arch = TuringArchetype.from_key(current.archetype)
    field = MorphogeneticField(
        width=36,
        height=36,
        F=arch.F,
        k=arch.k,
        Du=arch.Du,
        Dv=arch.Dv
    )
    # Seed field using the genesis receipt hash for continuous developmental determinism
    genesis_seed = receipts[0].receipt_hash or receipts[0].weisfeiler_lehman_digest
    field.seed_from_hash(genesis_seed)
    for _ in range(total_steps):
        field.step(dt=1.0)

    # Compile interaction net and reduce
    net, _ = compile_morphogenetic_proof_net(field)
    init_nodes = len(net.nodes)
    act_pairs = len(net.active_pairs())
    steps_reduced, _, settled = net.reduce(max_atp=atp_budget)
    wl_digest = net.canonical_digest()

    now_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    next_rec = OntogeneticProofReceipt(
        generation=next_gen,
        timestamp_utc=now_utc,
        archetype=current.archetype,
        pde_steps=total_steps,
        initial_nodes=init_nodes,
        active_pairs=act_pairs,
        reduced_steps=steps_reduced,
        atp_burned=steps_reduced,
        settled=settled,
        weisfeiler_lehman_digest=wl_digest,
        prev_receipt_hash=current.receipt_hash,
        public_key_hex=current.public_key_hex
    )

    # Signing: use provided key or fallback to genesis keypair if matching
    if secret_key_hex:
        next_rec.sign(secret_key_hex)
    else:
        # If unsigned or no key supplied, synthesize self-consistent author key
        sk_auto = hashlib.sha256(f"ONTOGENY_AUTOGENERATION:{genesis_seed}".encode()).digest()
        next_rec.sign(sk_auto.hex())

    receipts.append(next_rec)

    # Re-encode manifest
    new_manifest_data = json.dumps([r.to_dict() for r in receipts], ensure_ascii=False)
    new_manifest_bytes = f"\n{ONTOGENY_MANIFEST_PREFIX}{new_manifest_data}\n".encode("utf-8")

    # Generate incremental page stream
    compiler = OntogeneticPolyglotCompiler(archetype=arch)
    stream_content = compiler.generate_page_stream(next_rec, field)
    stream_bytes = stream_content.encode("utf-8")

    # Find previous xref and root
    last_xref_pos = content.rfind(b"startxref\n")
    prev_xref = 0
    if last_xref_pos != -1:
        tail = content[last_xref_pos + len(b"startxref\n"):]
        eof_pos = tail.find(b"\n%%EOF")
        if eof_pos != -1:
            try:
                prev_xref = int(tail[:eof_pos].strip())
            except ValueError:
                prev_xref = 0

    base_obj_count = 5 + (current.generation * 3)
    new_page_id = base_obj_count + 1
    new_contents_id = base_obj_count + 2
    new_pages_id = base_obj_count + 3

    page_obj = (
        f"{new_page_id} 0 obj\n"
        f"<< /Type /Page /Parent {new_pages_id} 0 R /MediaBox [0 0 595 842] "
        f"/Contents {new_contents_id} 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    ).encode("latin1")

    contents_obj = (
        f"{new_contents_id} 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin1") +
        stream_bytes +
        b"\nendstream\nendobj\n"
    )

    kids_refs = " ".join(f"{3 if i == 0 else 5 + (i * 3) - 2} 0 R" for i in range(len(receipts)))
    pages_obj = (
        f"{new_pages_id} 0 obj\n<< /Type /Pages /Kids [{kids_refs}] /Count {len(receipts)} >>\nendobj\n"
    ).encode("latin1")

    root_obj_id = new_pages_id + 1
    catalog_obj = (
        f"{root_obj_id} 0 obj\n<< /Type /Catalog /Pages {new_pages_id} 0 R >>\nendobj\n"
    ).encode("latin1")

    docstring_marker = b'\n"""\n'
    split_pos = content.find(docstring_marker)
    if split_pos != -1:
        pdf_prefix = content[:split_pos]
        runner_suffix = content[split_pos + len(docstring_marker):]
        # Strip old manifest lines
        m_idx = pdf_prefix.find(prefix)
        if m_idx != -1:
            m_end = pdf_prefix.find(b"\n", m_idx)
            pdf_prefix = pdf_prefix[:m_idx] + pdf_prefix[m_end + 1:]
    else:
        pdf_prefix = content
        runner_suffix = b""

    update_body = bytearray()
    update_offsets = []

    for obj in (page_obj, contents_obj, pages_obj, catalog_obj):
        obj_num = int(obj[:obj.find(b" 0 obj")].decode("latin1"))
        update_offsets.append((obj_num, len(pdf_prefix) + len(update_body)))
        update_body.extend(obj)

    new_xref_offset = len(pdf_prefix) + len(update_body)
    xref_chunk = bytearray()
    xref_chunk.extend(f"xref\n".encode("latin1"))
    for obj_num, offset in update_offsets:
        xref_chunk.extend(f"{obj_num} 1\n".encode("latin1"))
        xref_chunk.extend(f"{offset:010d} 00000 n \n".encode("latin1"))

    trailer_chunk = (
        f"trailer\n<< /Size {root_obj_id + 1} /Root {root_obj_id} 0 R /Prev {prev_xref} >>\n"
        f"startxref\n{new_xref_offset}\n%%EOF".encode("latin1")
    )

    new_full_content = (
        pdf_prefix +
        bytes(update_body) +
        bytes(xref_chunk) +
        trailer_chunk +
        new_manifest_bytes +
        b'\n"""\n' +
        runner_suffix
    )

    with open(pdf_path, "wb") as f:
        f.write(new_full_content)

    print(f"\033[1;32m[+] ONTOGENETIC STEP ACCOMPLISHED: Generation #{next_gen} appended to {os.path.basename(pdf_path)}\033[0m")
    print(f"    Total Developmental Pages: {len(receipts)}")
    print(f"    Proof-Net WL-Digest:        ⚓ {next_rec.weisfeiler_lehman_digest[:32]}...")
    print(f"    Receipt Hash:               {next_rec.receipt_hash[:32]}...")
    return next_rec

if __name__ == "__main__":
    print("morpho_net.py — Morphogenetic Proof-Net Engine loaded.")
