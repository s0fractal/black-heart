#!/usr/bin/env python3
"""
interaction.py — Lafont's Symmetric Interaction Combinators on UTF-8 Glyphs.
Part of Project Black-Heart (%🖤).

Implements:
  - 3 Elementary Symmetric Agents:
      🌱 (Constructor / Seed: γ)
      👥 (Duplicator / Clone: δ)
      🕳️ (Eraser / Void: ε)
  - Pure local graph rewiring with constant-time O(1) step reduction.
  - Annihilation, Commutation, and Erasure rules.
  - Deterministic ATP accounting and normal form canonical digests.
"""

from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set

AGENT_CONSTRUCT = "🌱"  # Constructor / Seed
AGENT_DUPLICATE = "👥"  # Duplicator / Clone
AGENT_ERASE = "🕳️"      # Eraser / Void

PORT_PRINCIPAL = 0
PORT_LEFT = 1
PORT_RIGHT = 2

@dataclass(frozen=True)
class PortRef:
    node_id: int
    port_index: int

    def __repr__(self) -> str:
        return f"{self.node_id}:{self.port_index}"

@dataclass
class Node:
    node_id: int
    agent_type: str
    ports: Dict[int, Optional[PortRef]] = field(default_factory=dict)

    def __post_init__(self):
        if not self.ports:
            # Eraser has only principal port 0; Constructor and Duplicator have ports 0, 1, 2
            max_ports = 1 if self.agent_type == AGENT_ERASE else 3
            self.ports = {i: None for i in range(max_ports)}

class InteractionNet:
    """
    Planar graph of interaction combinator agents wired at their ports.
    """
    def __init__(self):
        self.nodes: Dict[int, Node] = {}
        self._next_id: int = 1
        self.roots: List[PortRef] = []

    def create_node(self, agent_type: str) -> int:
        nid = self._next_id
        self._next_id += 1
        self.nodes[nid] = Node(node_id=nid, agent_type=agent_type)
        return nid

    def link(self, p1: PortRef, p2: PortRef):
        """Connects two ports with a directional or bidirectional wire."""
        if p1.node_id in self.nodes:
            self.nodes[p1.node_id].ports[p1.port_index] = p2
        if p2.node_id in self.nodes:
            self.nodes[p2.node_id].ports[p2.port_index] = p1

    def unlink(self, p: PortRef):
        if p.node_id in self.nodes and p.port_index in self.nodes[p.node_id].ports:
            other = self.nodes[p.node_id].ports[p.port_index]
            self.nodes[p.node_id].ports[p.port_index] = None
            if other and other.node_id in self.nodes and other.port_index in self.nodes[other.node_id].ports:
                self.nodes[other.node_id].ports[other.port_index] = None

    def active_pairs(self) -> List[Tuple[int, int]]:
        """Finds all pairs of nodes connected by their principal ports (Port 0)."""
        pairs: List[Tuple[int, int]] = []
        seen: Set[int] = set()

        for nid, node in list(self.nodes.items()):
            if nid in seen:
                continue
            p0 = node.ports.get(PORT_PRINCIPAL)
            if p0 and p0.port_index == PORT_PRINCIPAL and p0.node_id in self.nodes:
                other_id = p0.node_id
                if other_id != nid and other_id not in seen:
                    pairs.append((min(nid, other_id), max(nid, other_id)))
                    seen.add(nid)
                    seen.add(other_id)
        return pairs

    def step(self) -> bool:
        """
        Executes a single O(1) interaction step.
        Returns True if a reduction occurred, False if the net is in normal form.
        """
        pairs = self.active_pairs()
        if not pairs:
            return False

        n1_id, n2_id = pairs[0]
        n1 = self.nodes[n1_id]
        n2 = self.nodes[n2_id]

        t1 = n1.agent_type
        t2 = n2.agent_type

        # -------------------------------------------------------------
        # 1. ANNIHILATION: α ⋈ α
        # -------------------------------------------------------------
        if t1 == t2:
            if t1 == AGENT_ERASE:
                # Two erasers meet: both vanish
                del self.nodes[n1_id]
                del self.nodes[n2_id]
                return True

            # Constructor ⋈ Constructor or Duplicator ⋈ Duplicator
            # Rewire auxiliary ports: Aux1(n1) <-> Aux1(n2), Aux2(n1) <-> Aux2(n2)
            aux1_n1 = n1.ports.get(PORT_LEFT)
            aux2_n1 = n1.ports.get(PORT_RIGHT)
            aux1_n2 = n2.ports.get(PORT_LEFT)
            aux2_n2 = n2.ports.get(PORT_RIGHT)

            del self.nodes[n1_id]
            del self.nodes[n2_id]

            if aux1_n1 and aux1_n2:
                self.link(aux1_n1, aux1_n2)
            if aux2_n1 and aux2_n2:
                self.link(aux2_n1, aux2_n2)
            return True

        # -------------------------------------------------------------
        # 2. ERASURE: α ⋈ 🕳️
        # -------------------------------------------------------------
        if t1 == AGENT_ERASE or t2 == AGENT_ERASE:
            eraser_node = n1 if t1 == AGENT_ERASE else n2
            other_node = n2 if t1 == AGENT_ERASE else n1

            aux_left = other_node.ports.get(PORT_LEFT)
            aux_right = other_node.ports.get(PORT_RIGHT)

            del self.nodes[eraser_node.node_id]
            del self.nodes[other_node.node_id]

            # Spawn two new erasers to consume the dangling auxiliary wires
            if aux_left:
                e1 = self.create_node(AGENT_ERASE)
                self.link(PortRef(e1, PORT_PRINCIPAL), aux_left)
            if aux_right:
                e2 = self.create_node(AGENT_ERASE)
                self.link(PortRef(e2, PORT_PRINCIPAL), aux_right)
            return True

        # -------------------------------------------------------------
        # 3. COMMUTATION: 🌱 ⋈ 👥 (Constructor meets Duplicator)
        # -------------------------------------------------------------
        # When distinct binary nodes meet, they cross each other, duplicating
        # their shapes into 4 new nodes wired in a cross pattern.
        aux1_n1 = n1.ports.get(PORT_LEFT)
        aux2_n1 = n1.ports.get(PORT_RIGHT)
        aux1_n2 = n2.ports.get(PORT_LEFT)
        aux2_n2 = n2.ports.get(PORT_RIGHT)

        del self.nodes[n1_id]
        del self.nodes[n2_id]

        # Spawn two new nodes of type t2, and two of type t1
        # If n1 is Seed 🌱 and n2 is Clone 👥:
        # We create two Clones (c1, c2) and two Seeds (s1, s2)
        s1 = self.create_node(t1)
        s2 = self.create_node(t1)
        c1 = self.create_node(t2)
        c2 = self.create_node(t2)

        # Cross-wire the inner principal ports to the auxiliary ports
        self.link(PortRef(s1, PORT_LEFT), PortRef(c1, PORT_LEFT))
        self.link(PortRef(s1, PORT_RIGHT), PortRef(c2, PORT_LEFT))
        self.link(PortRef(s2, PORT_LEFT), PortRef(c1, PORT_RIGHT))
        self.link(PortRef(s2, PORT_RIGHT), PortRef(c2, PORT_RIGHT))

        # Connect outer principal ports to original auxiliary lines
        if aux1_n2:
            self.link(PortRef(s1, PORT_PRINCIPAL), aux1_n2)
        if aux2_n2:
            self.link(PortRef(s2, PORT_PRINCIPAL), aux2_n2)
        if aux1_n1:
            self.link(PortRef(c1, PORT_PRINCIPAL), aux1_n1)
        if aux2_n1:
            self.link(PortRef(c2, PORT_PRINCIPAL), aux2_n1)

        return True

    def reduce(self, max_atp: int = 10_000) -> Tuple[int, str, bool]:
        """
        Reduces the net until no active pairs remain or ATP is exhausted.
        Returns: (atp_spent, normal_form_digest, is_settled)
        """
        atp = 0
        while atp < max_atp:
            if not self.step():
                # Reached normal form
                digest = self.canonical_digest()
                return atp, digest, True
            atp += 1

        # ATP budget exceeded
        return atp, self.canonical_digest(), False

    def canonical_digest(self) -> str:
        """Computes a deterministic content-addressed hash of the net topology."""
        graph_repr = []
        for nid in sorted(self.nodes.keys()):
            node = self.nodes[nid]
            ports_repr = {}
            for p_idx, target in sorted(node.ports.items()):
                ports_repr[str(p_idx)] = f"{target.node_id}:{target.port_index}" if target else "none"
            graph_repr.append({
                "id": nid,
                "type": node.agent_type,
                "ports": ports_repr
            })
        raw = json.dumps(graph_repr, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

if __name__ == "__main__":
    print("Testing Lafont Interaction Combinators...")
    net = InteractionNet()

    # Create active pair: Seed 🌱 ⋈ Seed 🌱 (Annihilation)
    s1 = net.create_node(AGENT_CONSTRUCT)
    s2 = net.create_node(AGENT_CONSTRUCT)
    net.link(PortRef(s1, PORT_PRINCIPAL), PortRef(s2, PORT_PRINCIPAL))

    atp, digest, settled = net.reduce()
    assert settled is True
    assert atp == 1
    print(f"[✓] Annihilation Sound: 1 ATP burned, settled digest: {digest[:16]}...")
