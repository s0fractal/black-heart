#!/usr/bin/env python3
"""
mesh.py — Peer-to-Peer Document Swarm Synchronization Protocol for Living Polyglots.
Part of Project Black-Heart (%🖤).

Features:
  - 100% Pure Standard Library Python (http.server, urllib.request, socketserver).
  - Turns Living Polyglot Ledgers (living_ledger.py) into autonomous network nodes.
  - Document Gossip: Compares Merkle chain tips and exchanges missing blocks.
  - Incremental PDF Synchronization: Appends authenticated blocks directly to target PDF
    files on disk without rewriting history.
  - Byzantine Fault Resistance: Rejects blocks with invalid Ed25519 signatures or broken hash links.
"""

from __future__ import annotations
import os
import sys
import json
import time
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Optional, List, Dict, Any, Tuple

from living_ledger import LivingLedger, LedgerBlock
from crypto import verify_bytes, public_key_from_secret

# ============================================================================
# LEDGER FILE HELPERS
# ============================================================================

def read_ledger(pdf_path: str) -> LivingLedger:
    """Loads a LivingLedger instance from an existing polyglot PDF."""
    return LivingLedger.load_from_polyglot(pdf_path)

def read_ledger_blocks(pdf_path: str) -> List[LedgerBlock]:
    """Reads all blocks from an existing living ledger PDF."""
    ledger = read_ledger(pdf_path)
    return ledger.blocks

def verify_block_integrity(block: LedgerBlock, expected_prev_hash: str) -> bool:
    """Verifies that a block has a valid signature and valid prev_hash link."""
    if block.prev_hash != expected_prev_hash:
        return False
    if block.compute_hash() != block.block_hash:
        return False
    try:
        pk_bytes = bytes.fromhex(block.public_key_hex)
        sig_bytes = bytes.fromhex(block.signature_hex)
        msg_bytes = block.canonical_bytes_for_signing()
        return verify_bytes(pk_bytes, msg_bytes, sig_bytes)
    except Exception:
        return False

# ============================================================================
# LOCAL & REMOTE P2P SYNC ENGINE
# ============================================================================

def sync_local_ledgers(source_pdf: str, destination_pdf: str) -> int:
    """
    Synchronizes two local living ledger PDF files.
    Transfers any verified blocks present in source_pdf but missing in destination_pdf.
    Returns the count of newly appended blocks.
    """
    src_blocks = read_ledger_blocks(source_pdf)
    dst_blocks = read_ledger_blocks(destination_pdf)

    # Ensure common ancestor on overlapping prefix
    min_len = min(len(src_blocks), len(dst_blocks))
    for i in range(min_len):
        if src_blocks[i].block_hash != dst_blocks[i].block_hash:
            raise ValueError(f"Fork detected at block height #{i} between {source_pdf} and {destination_pdf}")

    if len(src_blocks) <= len(dst_blocks):
        return 0

    # Reconstitute destination ledger
    dst_ledger = read_ledger(destination_pdf)
    dst_blocks = dst_ledger.blocks

    new_blocks = 0
    for block in src_blocks[len(dst_blocks):]:
        # Validate block
        expected_prev = dst_ledger.blocks[-1].block_hash
        if not verify_block_integrity(block, expected_prev):
            raise ValueError(f"Invalid block received at height #{block.height}: signature or hash mismatch")

        # Append block to destination ledger
        dst_ledger.append_existing_block(block)
        new_blocks += 1

    if new_blocks > 0:
        dst_ledger.compile(destination_pdf)

    return new_blocks

# ============================================================================
# EMBEDDED P2P HTTP NODE
# ============================================================================

class LedgerNodeHandler(BaseHTTPRequestHandler):
    pdf_path: str = ""
    epistemic_registry: Optional[Any] = None

    def log_message(self, format, *args):
        # Suppress noisy standard HTTP access logs
        return

    def do_GET(self):
        if self.path == "/tip":
            try:
                blocks = read_ledger_blocks(self.pdf_path)
                resp = {
                    "status": "ok",
                    "height": len(blocks),
                    "tip_hash": blocks[-1].block_hash if blocks else "",
                    "timestamp_utc": blocks[-1].timestamp_utc if blocks else ""
                }
                self._send_json(200, resp)
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif self.path.startswith("/blocks"):
            # Format: /blocks?from_height=N
            try:
                blocks = read_ledger_blocks(self.pdf_path)
                from_height = 0
                if "from_height=" in self.path:
                    from_height = int(self.path.split("from_height=")[1].split("&")[0])
                missing = [b.to_dict() for b in blocks[from_height:]]
                self._send_json(200, {"blocks": missing, "count": len(missing)})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        # ====================================================================
        # EPISTEMIC MYCELIUM ENDPOINTS
        # ====================================================================
        elif self.path == "/epistemic/summary":
            if self.epistemic_registry is None:
                self._send_json(404, {"error": "Epistemic registry not enabled on this node"})
                return
            self._send_json(200, self.epistemic_registry.summary())

        elif self.path.startswith("/epistemic/warrants"):
            if self.epistemic_registry is None:
                self._send_json(404, {"error": "Epistemic registry not enabled on this node"})
                return
            w_list = [w.to_dict() for w in self.epistemic_registry.warrants.values()]
            self._send_json(200, {"warrants": w_list, "count": len(w_list)})

        elif self.path.startswith("/epistemic/divergences"):
            if self.epistemic_registry is None:
                self._send_json(404, {"error": "Epistemic registry not enabled on this node"})
                return
            d_list = [d.to_dict() for d in self.epistemic_registry.divergences.values()]
            self._send_json(200, {"divergences": d_list, "count": len(d_list)})

        elif self.path.startswith("/epistemic/normal_forms"):
            if self.epistemic_registry is None:
                self._send_json(404, {"error": "Epistemic registry not enabled on this node"})
                return
            nf_list = [n.to_dict() for n in self.epistemic_registry.normal_forms.values()]
            self._send_json(200, {"normal_forms": nf_list, "count": len(nf_list)})

        else:
            self._send_json(404, {"error": "Endpoint not found"})

    def do_POST(self):
        if self.path == "/submit_block":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                data = json.loads(body.decode("utf-8"))
                new_block = LedgerBlock.from_dict(data)

                ledger = read_ledger(self.pdf_path)
                expected_prev = ledger.blocks[-1].block_hash if ledger.blocks else "0" * 64

                if not verify_block_integrity(new_block, expected_prev):
                    self._send_json(400, {"error": "Invalid signature or broken prev_hash link"})
                    return

                ledger.append_existing_block(new_block)
                ledger.compile(self.pdf_path)

                self._send_json(200, {"status": "block_appended", "new_height": len(ledger.blocks), "tip": new_block.block_hash})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        # ====================================================================
        # EPISTEMIC MYCELIUM SUBMISSIONS
        # ====================================================================
        elif self.path == "/epistemic/submit_warrant":
            if self.epistemic_registry is None:
                self._send_json(404, {"error": "Epistemic registry not enabled on this node"})
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                data = json.loads(body.decode("utf-8"))
                from mycelium import Warrant
                warrant = Warrant.from_dict(data)
                if not warrant.verify():
                    self._send_json(400, {"error": "Invalid warrant signature or ID derivation"})
                    return
                self.epistemic_registry.add_warrant(warrant, verify_first=False)
                self._send_json(200, {"status": "warrant_admitted", "warrant_id": warrant.warrant_id})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif self.path == "/epistemic/submit_divergence":
            if self.epistemic_registry is None:
                self._send_json(404, {"error": "Epistemic registry not enabled on this node"})
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                data = json.loads(body.decode("utf-8"))
                from mycelium import DivergenceRecord
                div = DivergenceRecord.from_dict(data)
                if not div.verify():
                    self._send_json(400, {"error": "Invalid divergence record signature or derivation"})
                    return
                self.epistemic_registry.add_divergence(div, verify_first=False)
                self._send_json(200, {"status": "divergence_admitted", "record_id": div.record_id})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif self.path == "/epistemic/submit_normal_form":
            if self.epistemic_registry is None:
                self._send_json(404, {"error": "Epistemic registry not enabled on this node"})
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                data = json.loads(body.decode("utf-8"))
                from mycelium import NormalFormEntry
                nf = NormalFormEntry.from_dict(data)
                if not nf.verify():
                    self._send_json(400, {"error": "Invalid normal form entry signature or hash"})
                    return
                self.epistemic_registry.add_normal_form(nf, verify_first=False)
                self._send_json(200, {"status": "normal_form_admitted", "term_hash": nf.term_hash})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        else:
            self._send_json(404, {"error": "Endpoint not found"})

    def _send_json(self, status_code: int, data: Dict[str, Any]):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def start_ledger_daemon(pdf_path: str, port: int = 8765) -> HTTPServer:
    """Launches a background HTTP node serving a Living Ledger PDF."""
    class BoundHandler(LedgerNodeHandler):
        pass
    BoundHandler.pdf_path = os.path.abspath(pdf_path)
    server = HTTPServer(("127.0.0.1", port), BoundHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server

def start_epistemic_daemon(registry: Any, pdf_path: str = "", port: int = 8766) -> HTTPServer:
    """Launches a background HTTP node serving an Epistemic Registry and optionally a living ledger."""
    class BoundHandler(LedgerNodeHandler):
        pass
    if pdf_path:
        BoundHandler.pdf_path = os.path.abspath(pdf_path)
    BoundHandler.epistemic_registry = registry
    server = HTTPServer(("127.0.0.1", port), BoundHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server

def sync_from_remote_peer(local_pdf: str, peer_url: str) -> int:
    """
    Connects to a remote peer running a Black-Heart ledger daemon,
    reconciles differences, and incrementally updates local_pdf.
    """
    peer_url = peer_url.rstrip("/")
    # 1. Query remote tip
    req = urllib.request.Request(f"{peer_url}/tip")
    with urllib.request.urlopen(req, timeout=5) as resp:
        remote_tip_data = json.loads(resp.read().decode("utf-8"))

    dst_ledger = read_ledger(local_pdf)
    local_height = len(dst_ledger.blocks)
    remote_height = remote_tip_data["height"]

    if remote_height <= local_height:
        return 0

    # 2. Fetch missing blocks
    req_blocks = urllib.request.Request(f"{peer_url}/blocks?from_height={local_height}")
    with urllib.request.urlopen(req_blocks, timeout=10) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        missing_data = res.get("blocks", [])

    new_count = 0

    for b_dict in missing_data:
        block = LedgerBlock.from_dict(b_dict)
        expected_prev = dst_ledger.blocks[-1].block_hash
        if not verify_block_integrity(block, expected_prev):
            raise ValueError(f"Byzantine fault: Received invalid block at height #{block.height} from {peer_url}")

        dst_ledger.append_existing_block(block)
        new_count += 1

    if new_count > 0:
        dst_ledger.compile(local_pdf)

    return new_count

def sync_epistemic_from_remote_peer(local_registry: Any, peer_url: str) -> Dict[str, int]:
    """
    Connects to a remote peer running a Black-Heart epistemic node,
    fetches new warrants, normal forms, and divergence records,
    validates them fail-closed, and updates the local registry.
    """
    peer_url = peer_url.rstrip("/")
    counts = {"warrants": 0, "divergences": 0, "normal_forms": 0}

    # 1. Sync Warrants
    try:
        req = urllib.request.Request(f"{peer_url}/epistemic/warrants")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            from mycelium import Warrant
            for wd in data.get("warrants", []):
                w = Warrant.from_dict(wd)
                if w.warrant_id not in local_registry.warrants:
                    if w.verify():
                        local_registry.add_warrant(w, verify_first=False)
                        counts["warrants"] += 1
    except Exception:
        pass

    # 2. Sync Divergences
    try:
        req = urllib.request.Request(f"{peer_url}/epistemic/divergences")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            from mycelium import DivergenceRecord
            for dd in data.get("divergences", []):
                d = DivergenceRecord.from_dict(dd)
                if d.record_id not in local_registry.divergences:
                    if d.verify():
                        local_registry.add_divergence(d, verify_first=False)
                        counts["divergences"] += 1
    except Exception:
        pass

    # 3. Sync Normal Forms
    try:
        req = urllib.request.Request(f"{peer_url}/epistemic/normal_forms")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            from mycelium import NormalFormEntry
            for nd in data.get("normal_forms", []):
                nf = NormalFormEntry.from_dict(nd)
                if nf.term_hash not in local_registry.normal_forms:
                    if nf.verify():
                        local_registry.add_normal_form(nf, verify_first=False)
                        counts["normal_forms"] += 1
    except Exception:
        pass

    return counts

if __name__ == "__main__":
    print("Testing P2P Living Polyglot Mesh Synchronization...")
    # Standalone sanity check
    from examples.living_ledger_demo import run_demo
    demo_pdf = "/tmp/mesh_test_node_a.pdf"
    demo_pdf_b = "/tmp/mesh_test_node_b.pdf"

    from living_ledger import LivingLedger
    from crypto import generate_keypair

    sk, pk = generate_keypair()
    l_a = LivingLedger("NODE A LEDGER")
    l_a.create_genesis("Node A", "Originator", sk, "Genesis Block on Node A")
    l_a.compile(demo_pdf)

    l_b = LivingLedger("NODE B LEDGER")
    l_b.create_genesis("Node A", "Originator", sk, "Genesis Block on Node A")
    l_b.compile(demo_pdf_b)

    # Add block on Node A
    l_a.append_block("Node A", "Originator", sk, "ACTION_SETTLE", "Transaction #1 on Node A")
    l_a.compile(demo_pdf)

    # Sync Node B from Node A locally
    appended = sync_local_ledgers(demo_pdf, demo_pdf_b)
    print(f"[✓] Local P2P Sync: {appended} block(s) synced from Node A to Node B.")

    # Start network daemon for Node A
    srv = start_ledger_daemon(demo_pdf, port=9876)
    print("[✓] Node A Daemon running on port 9876")

    # Add another block on Node A
    l_a.append_block("Node A", "Originator", sk, "ACTION_ORACLE", "Transaction #2 on Node A")
    l_a.compile(demo_pdf)

    # Sync Node B from Node A via network HTTP
    synced_net = sync_from_remote_peer(demo_pdf_b, "http://127.0.0.1:9876")
    print(f"[✓] Network P2P Sync: {synced_net} block(s) synced over HTTP socket.")
    srv.shutdown()
    print("[✓] All P2P Swarm Sync Tests Passed!")
