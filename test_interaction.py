#!/usr/bin/env python3
"""
test_interaction.py — Unit Tests for Lafont's Symmetric Interaction Combinators.
Part of Project Black-Heart (%🖤).
"""

import unittest
from interaction import (
    InteractionNet,
    PortRef,
    AGENT_CONSTRUCT,
    AGENT_DUPLICATE,
    AGENT_ERASE,
    PORT_PRINCIPAL,
    PORT_LEFT,
    PORT_RIGHT
)

class TestInteractionCombinators(unittest.TestCase):
    """Verifies all interaction rules (Annihilation, Erasure, Commutation) and ATP burning."""

    def test_annihilation_constructors(self):
        """🌱 ⋈ 🌱: Both constructors vanish, auxiliary ports rewire directly."""
        net = InteractionNet()
        c1 = net.create_node(AGENT_CONSTRUCT)
        c2 = net.create_node(AGENT_CONSTRUCT)

        # Wire principal ports together
        net.link(PortRef(c1, PORT_PRINCIPAL), PortRef(c2, PORT_PRINCIPAL))

        atp, digest, settled = net.reduce()
        self.assertTrue(settled)
        self.assertEqual(atp, 1) # exactly 1 interaction step
        self.assertEqual(len(net.nodes), 0) # both vanished

    def test_annihilation_duplicators(self):
        """👥 ⋈ 👥: Both duplicators vanish."""
        net = InteractionNet()
        d1 = net.create_node(AGENT_DUPLICATE)
        d2 = net.create_node(AGENT_DUPLICATE)
        net.link(PortRef(d1, PORT_PRINCIPAL), PortRef(d2, PORT_PRINCIPAL))

        atp, digest, settled = net.reduce()
        self.assertTrue(settled)
        self.assertEqual(atp, 1)
        self.assertEqual(len(net.nodes), 0)

    def test_annihilation_erasers(self):
        """🕳️ ⋈ 🕳️: Two erasers vanish into empty set."""
        net = InteractionNet()
        e1 = net.create_node(AGENT_ERASE)
        e2 = net.create_node(AGENT_ERASE)
        net.link(PortRef(e1, PORT_PRINCIPAL), PortRef(e2, PORT_PRINCIPAL))

        atp, digest, settled = net.reduce()
        self.assertTrue(settled)
        self.assertEqual(atp, 1)
        self.assertEqual(len(net.nodes), 0)

    def test_erasure_constructor(self):
        """🌱 ⋈ 🕳️: Eraser destroys constructor and spawns two new erasers on auxiliary ports."""
        net = InteractionNet()
        c = net.create_node(AGENT_CONSTRUCT)
        e = net.create_node(AGENT_ERASE)

        # External target nodes to be erased
        target1 = net.create_node(AGENT_CONSTRUCT)
        target2 = net.create_node(AGENT_CONSTRUCT)
        net.link(PortRef(c, PORT_LEFT), PortRef(target1, PORT_PRINCIPAL))
        net.link(PortRef(c, PORT_RIGHT), PortRef(target2, PORT_PRINCIPAL))

        # Active pair: c ⋈ e
        net.link(PortRef(c, PORT_PRINCIPAL), PortRef(e, PORT_PRINCIPAL))

        atp, digest, settled = net.reduce()
        self.assertTrue(settled)
        # Step 1: c ⋈ e spawns two erasers connected to target1 and target2
        # Step 2 & 3: each eraser meets target constructor and vanishes
        self.assertGreaterEqual(atp, 1)

    def test_commutation_construct_duplicate(self):
        """🌱 ⋈ 👥: Commutation cross-wires 2 new duplicators and 2 new constructors."""
        net = InteractionNet()
        seed = net.create_node(AGENT_CONSTRUCT)
        clone = net.create_node(AGENT_DUPLICATE)

        net.link(PortRef(seed, PORT_PRINCIPAL), PortRef(clone, PORT_PRINCIPAL))

        # One step of commutation
        step_done = net.step()
        self.assertTrue(step_done)

        # Original nodes removed, 4 new nodes created
        self.assertEqual(len(net.nodes), 4)

        # Verify new node types (2 constructors, 2 duplicators)
        types = [n.agent_type for n in net.nodes.values()]
        self.assertEqual(types.count(AGENT_CONSTRUCT), 2)
        self.assertEqual(types.count(AGENT_DUPLICATE), 2)

    def test_canonical_digest_deterministic(self):
        """Canonical digest of two identical net topologies must be bitwise identical."""
        net1 = InteractionNet()
        n1 = net1.create_node(AGENT_CONSTRUCT)
        n2 = net1.create_node(AGENT_DUPLICATE)
        net1.link(PortRef(n1, PORT_LEFT), PortRef(n2, PORT_RIGHT))

        net2 = InteractionNet()
        m1 = net2.create_node(AGENT_CONSTRUCT)
        m2 = net2.create_node(AGENT_DUPLICATE)
        net2.link(PortRef(m1, PORT_LEFT), PortRef(m2, PORT_RIGHT))

        self.assertEqual(net1.canonical_digest(), net2.canonical_digest())

if __name__ == "__main__":
    unittest.main()
