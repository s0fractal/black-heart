#!/usr/bin/env python3
"""
test_mesh.py — Unit Tests for Peer-to-Peer Living Polyglot Mesh Synchronization.
Part of Project Black-Heart (%🖤).
"""

import os
import sys
import unittest
import tempfile

from living_ledger import LivingLedger, LedgerBlock
from crypto import generate_keypair
from mesh import sync_local_ledgers, read_ledger_blocks, start_ledger_daemon, sync_from_remote_peer

class TestMeshSync(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.sk, self.pk = generate_keypair()
        self.pdf_a = os.path.join(self.tmp_dir, "node_a.pdf")
        self.pdf_b = os.path.join(self.tmp_dir, "node_b.pdf")

        import shutil
        # Initialize Genesis on Node A, and clone to Node B
        l_a = LivingLedger("SWARM LEDGER")
        l_a.create_genesis("Alice", "Originator", self.sk, "Genesis Block")
        l_a.compile(self.pdf_a)

        shutil.copy(self.pdf_a, self.pdf_b)

    def test_local_p2p_sync(self):
        l_a = LivingLedger.load_from_polyglot(self.pdf_a)
        l_a.append_block("Alice", "Originator", self.sk, "TX_TRANSFER", "Block 1 on A")
        l_a.append_block("Alice", "Originator", self.sk, "TX_ORACLE", "Block 2 on A")
        l_a.compile(self.pdf_a)

        blocks_a = read_ledger_blocks(self.pdf_a)
        blocks_b = read_ledger_blocks(self.pdf_b)
        self.assertEqual(len(blocks_a), 3)
        self.assertEqual(len(blocks_b), 1)

        # Sync B from A
        synced = sync_local_ledgers(self.pdf_a, self.pdf_b)
        self.assertEqual(synced, 2)

        blocks_b_after = read_ledger_blocks(self.pdf_b)
        self.assertEqual(len(blocks_b_after), 3)
        self.assertEqual(blocks_b_after[-1].block_hash, blocks_a[-1].block_hash)

    def test_byzantine_fork_rejection(self):
        other_sk, _ = generate_keypair()
        # Create divergent block on B
        l_b = LivingLedger.load_from_polyglot(self.pdf_b)
        l_b.append_block("Mallory", "Attacker", other_sk, "TX_FORK", "Divergent block on B")
        l_b.compile(self.pdf_b)

        # Add block on A
        l_a = LivingLedger.load_from_polyglot(self.pdf_a)
        l_a.append_block("Alice", "Originator", self.sk, "TX_HONEST", "Honest block on A")
        l_a.compile(self.pdf_a)

        # Syncing A into B must reject fork
        with self.assertRaises(ValueError) as ctx:
            sync_local_ledgers(self.pdf_a, self.pdf_b)
        self.assertIn("Fork detected", str(ctx.exception))

    def test_network_daemon_sync(self):
        l_a = LivingLedger.load_from_polyglot(self.pdf_a)
        l_a.append_block("Alice", "Originator", self.sk, "TX_NETWORK", "Network Block 1")
        l_a.compile(self.pdf_a)

        # Start daemon on dynamic port 9988
        port = 9988
        daemon = start_ledger_daemon(self.pdf_a, port=port)
        try:
            synced = sync_from_remote_peer(self.pdf_b, f"http://127.0.0.1:{port}")
            self.assertEqual(synced, 1)

            blocks_b = read_ledger_blocks(self.pdf_b)
            blocks_a = read_ledger_blocks(self.pdf_a)
            self.assertEqual(blocks_b[-1].block_hash, blocks_a[-1].block_hash)
        finally:
            daemon.shutdown()
            daemon.server_close()

if __name__ == "__main__":
    unittest.main()
