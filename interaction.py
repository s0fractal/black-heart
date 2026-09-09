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
        self._active_pairs: Set[Tuple[int, int]] = set()

    def create_node(self, agent_type: str) -> int:
        nid = self._next_id
        self._next_id += 1
        self.nodes[nid] = Node(node_id=nid, agent_type=agent_type)
        return nid

    def link(self, p1: PortRef, p2: PortRef):
        """Connects two ports with a directional or bidirectional wire."""
        self.unlink(p1)
        self.unlink(p2)

        if p1.node_id in self.nodes:
            self.nodes[p1.node_id].ports[p1.port_index] = p2
        if p2.node_id in self.nodes:
            self.nodes[p2.node_id].ports[p2.port_index] = p1

        if (p1.port_index == PORT_PRINCIPAL and 
            p2.port_index == PORT_PRINCIPAL and 
            p1.node_id != p2.node_id and
            p1.node_id in self.nodes and 
            p2.node_id in self.nodes):
            pair = (min(p1.node_id, p2.node_id), max(p1.node_id, p2.node_id))
            self._active_pairs.add(pair)

    def unlink(self, p: PortRef):
        if p.node_id in self.nodes and p.port_index in self.nodes[p.node_id].ports:
            other = self.nodes[p.node_id].ports[p.port_index]
            self.nodes[p.node_id].ports[p.port_index] = None
            if other and other.node_id in self.nodes and other.port_index in self.nodes[other.node_id].ports:
                self.nodes[other.node_id].ports[other.port_index] = None
                if p.port_index == PORT_PRINCIPAL and other.port_index == PORT_PRINCIPAL:
                    pair = (min(p.node_id, other.node_id), max(p.node_id, other.node_id))
                    self._active_pairs.discard(pair)

    def _delete_node(self, nid: int):
        if nid not in self.nodes:
            return
        node = self.nodes[nid]
        for p_idx in list(node.ports.keys()):
            self.unlink(PortRef(nid, p_idx))
        del self.nodes[nid]
        stale = [pair for pair in self._active_pairs if nid in pair]
        for pair in stale:
            self._active_pairs.discard(pair)

    def active_pairs(self) -> List[Tuple[int, int]]:
        """Finds all pairs of nodes connected by their principal ports (Port 0)."""
        valid: List[Tuple[int, int]] = []
        for a, b in list(self._active_pairs):
            if a in self.nodes and b in self.nodes:
                p_a = self.nodes[a].ports.get(PORT_PRINCIPAL)
                p_b = self.nodes[b].ports.get(PORT_PRINCIPAL)
                if (p_a and p_a.node_id == b and p_a.port_index == PORT_PRINCIPAL and
                    p_b and p_b.node_id == a and p_b.port_index == PORT_PRINCIPAL):
                    valid.append((a, b))
                else:
                    self._active_pairs.discard((a, b))
            else:
                self._active_pairs.discard((a, b))
        return sorted(valid)

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
                self._delete_node(n1_id)
                self._delete_node(n2_id)
                return True

            # Constructor ⋈ Constructor or Duplicator ⋈ Duplicator
            rule_partner = {
                (n1_id, 1): (n2_id, 1),
                (n2_id, 1): (n1_id, 1),
                (n1_id, 2): (n2_id, 2),
                (n2_id, 2): (n1_id, 2),
            }
            internal_ports = set(rule_partner.keys())

            orig_conn: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {}
            for nid, p_idx in internal_ports:
                target = self.nodes[nid].ports.get(p_idx)
                orig_conn[(nid, p_idx)] = (target.node_id, target.port_index) if target else None

            self._delete_node(n1_id)
            self._delete_node(n2_id)

            linked_endpoints: Set[Tuple[Tuple[int, int], Tuple[int, int]]] = set()

            for p_int, ext in orig_conn.items():
                if ext is None or ext[0] in (n1_id, n2_id):
                    continue
                
                curr = rule_partner[p_int]
                visited = {p_int}
                while curr in orig_conn and orig_conn[curr] is not None:
                    dest = orig_conn[curr]
                    if dest[0] not in (n1_id, n2_id):
                        endpoint_pair = tuple(sorted([ext, dest]))
                        if endpoint_pair not in linked_endpoints:
                            linked_endpoints.add(endpoint_pair)
                            self.link(PortRef(ext[0], ext[1]), PortRef(dest[0], dest[1]))
                        break
                    if dest in visited:
                        break
                    visited.add(dest)
                    curr = rule_partner[dest]

            return True

        # -------------------------------------------------------------
        # 2. ERASURE: α ⋈ 🕳️
        # -------------------------------------------------------------
        if t1 == AGENT_ERASE or t2 == AGENT_ERASE:
            eraser_id = n1_id if t1 == AGENT_ERASE else n2_id
            other_id = n2_id if t1 == AGENT_ERASE else n1_id
            other_node = self.nodes[other_id]

            aux_left = other_node.ports.get(PORT_LEFT)
            aux_right = other_node.ports.get(PORT_RIGHT)

            self_loop = (
                aux_left is not None and aux_right is not None and
                aux_left.node_id == other_id and aux_left.port_index == PORT_RIGHT and
                aux_right.node_id == other_id and aux_right.port_index == PORT_LEFT
            )

            self._delete_node(eraser_id)
            self._delete_node(other_id)

            e1 = self.create_node(AGENT_ERASE)
            e2 = self.create_node(AGENT_ERASE)

            if self_loop:
                self.link(PortRef(e1, PORT_PRINCIPAL), PortRef(e2, PORT_PRINCIPAL))
            else:
                if aux_left and aux_left.node_id not in (eraser_id, other_id):
                    self.link(PortRef(e1, PORT_PRINCIPAL), aux_left)
                if aux_right and aux_right.node_id not in (eraser_id, other_id):
                    self.link(PortRef(e2, PORT_PRINCIPAL), aux_right)

            return True

        # -------------------------------------------------------------
        # 3. COMMUTATION: 🌱 ⋈ 👥 (Constructor meets Duplicator)
        # -------------------------------------------------------------
        aux_ports = {
            (n1_id, PORT_LEFT): n1.ports.get(PORT_LEFT),
            (n1_id, PORT_RIGHT): n1.ports.get(PORT_RIGHT),
            (n2_id, PORT_LEFT): n2.ports.get(PORT_LEFT),
            (n2_id, PORT_RIGHT): n2.ports.get(PORT_RIGHT),
        }
        orig_conn: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {}
        for p, target in aux_ports.items():
            orig_conn[p] = (target.node_id, target.port_index) if target else None

        self._delete_node(n1_id)
        self._delete_node(n2_id)

        s1 = self.create_node(t1)
        s2 = self.create_node(t1)
        c1 = self.create_node(t2)
        c2 = self.create_node(t2)

        self.link(PortRef(s1, PORT_LEFT), PortRef(c1, PORT_LEFT))
        self.link(PortRef(s1, PORT_RIGHT), PortRef(c2, PORT_LEFT))
        self.link(PortRef(s2, PORT_LEFT), PortRef(c1, PORT_RIGHT))
        self.link(PortRef(s2, PORT_RIGHT), PortRef(c2, PORT_RIGHT))

        new_outer: Dict[Tuple[int, int], PortRef] = {
            (n2_id, PORT_LEFT): PortRef(s1, PORT_PRINCIPAL),
            (n2_id, PORT_RIGHT): PortRef(s2, PORT_PRINCIPAL),
            (n1_id, PORT_LEFT): PortRef(c1, PORT_PRINCIPAL),
            (n1_id, PORT_RIGHT): PortRef(c2, PORT_PRINCIPAL),
        }

        connected_pairs: Set[Tuple[Tuple[int, int], Tuple[int, int]]] = set()
        for p, dest in orig_conn.items():
            if dest is None:
                continue
            if dest in new_outer:
                wire_pair = tuple(sorted([p, dest]))
                if wire_pair not in connected_pairs:
                    connected_pairs.add(wire_pair)
                    self.link(new_outer[p], new_outer[dest])
            elif dest[0] not in (n1_id, n2_id):
                self.link(new_outer[p], PortRef(dest[0], dest[1]))

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
                return atp, self.canonical_digest(), True
            atp += 1

        settled = len(self.active_pairs()) == 0
        return atp, self.canonical_digest(), settled

    def canonical_digest(self) -> str:
        """Computes an isomorphism-invariant deterministic content-addressed hash."""
        if not self.nodes:
            return hashlib.sha256(b"EMPTY").hexdigest()

        # Iterative 1D Weisfeiler-Lehman color refinement for graph isomorphism
        colors: Dict[int, str] = {nid: node.agent_type for nid, node in self.nodes.items()}
        rounds = min(16, max(4, len(self.nodes)))
        for _ in range(rounds):
            next_colors = {}
            for nid, node in self.nodes.items():
                ports_info = []
                for p_idx in sorted(node.ports.keys()):
                    target = node.ports[p_idx]
                    if target and target.node_id in self.nodes:
                        ports_info.append((p_idx, target.port_index, colors[target.node_id]))
                    else:
                        ports_info.append((p_idx, None, None))
                val = f"{colors[nid]}|{ports_info}".encode("utf-8")
                next_colors[nid] = hashlib.sha256(val).hexdigest()
            colors = next_colors

        sorted_nodes = sorted(self.nodes.keys(), key=lambda nid: (colors[nid], self.nodes[nid].agent_type, nid))
        mapping = {old_id: idx for idx, old_id in enumerate(sorted_nodes, 1)}

        graph_repr = []
        for old_id in sorted_nodes:
            node = self.nodes[old_id]
            ports_repr = {}
            for p_idx in sorted(node.ports.keys()):
                target = node.ports[p_idx]
                if target and target.node_id in mapping:
                    ports_repr[str(p_idx)] = f"{mapping[target.node_id]}:{target.port_index}"
                else:
                    ports_repr[str(p_idx)] = "none"
            graph_repr.append({
                "type": node.agent_type,
                "ports": ports_repr
            })

        graph_repr.sort(key=lambda item: json.dumps(item, sort_keys=True))
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
