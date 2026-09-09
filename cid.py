#!/usr/bin/env python3
# coding: utf-8
"""
cid.py — Pure Standard Library IPFS Content Identifier (CIDv1) Engine.
Part of Project Black-Heart (%🖤).

Implements canonical IPFS CIDv1 generation for raw binary data and documents:
  - Multibase: 'b' (Base32, RFC 4648, lower-case, unpadded)
  - CID Version: 0x01 (CIDv1)
  - Multicodec: 0x55 (raw binary)
  - Multihash: 0x12 (SHA2-256), 0x20 (32-byte length)

Zero external dependencies: 100% Python standard library (hashlib, base64).
Compatible with Kubo (go-ipfs), IPFS Gateways, and IPLD standards.
"""

from __future__ import annotations
import os
import sys
import base64
import hashlib
from typing import Union

# Multicodec & Multihash Constants
CID_VERSION_1 = 0x01
CODEC_RAW = 0x55
HASH_SHA2_256 = 0x12
HASH_LENGTH_32 = 0x20

# Canonical 4-byte header for CIDv1 Raw SHA2-256: 0x01 0x55 0x12 0x20
CIDV1_RAW_HEADER = bytes([CID_VERSION_1, CODEC_RAW, HASH_SHA2_256, HASH_LENGTH_32])

def compute_cidv1_raw(data: bytes) -> str:
    """
    Computes canonical IPFS CIDv1 (raw/sha256/base32) for arbitrary bytes.
    Yields standard 'bafkrei...' multibase string.
    """
    digest = hashlib.sha256(data).digest()
    payload = CIDV1_RAW_HEADER + digest
    # RFC 4648 Base32 lower-case without '=' padding, prefixed with 'b'
    b32 = base64.b32encode(payload).decode("ascii").rstrip("=").lower()
    return "b" + b32

def compute_cidv1_for_file(filepath: str, chunk_size: int = 65536) -> str:
    """
    Streams file bytes from disk and computes its canonical CIDv1 raw identifier.
    """
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    payload = CIDV1_RAW_HEADER + h.digest()
    b32 = base64.b32encode(payload).decode("ascii").rstrip("=").lower()
    return "b" + b32

def is_valid_cidv1(cid: str) -> bool:
    """
    Validates whether a string is a well-formed CIDv1 raw Base32 identifier.
    Must start with 'bafkrei' and have length 59 characters.
    """
    if not isinstance(cid, str):
        return False
    # Standard raw CIDv1 base32 is always 59 chars starting with 'bafkrei'
    if not (cid.startswith("bafkrei") and len(cid) == 59):
        return False
    # Verify base32 alphabet (a-z, 2-7)
    valid_chars = set("abcdefghijklmnopqrstuvwxyz234567")
    return all(c in valid_chars for c in cid[1:])

def verify_data_cid(data: bytes, expected_cid: str) -> bool:
    """
    Verifies that the provided byte content matches the expected CIDv1.
    """
    if not is_valid_cidv1(expected_cid):
        return False
    actual_cid = compute_cidv1_raw(data)
    return actual_cid == expected_cid

def verify_file_cid(filepath: str, expected_cid: str) -> bool:
    """
    Verifies that the file on disk matches the expected CIDv1.
    """
    if not os.path.exists(filepath):
        return False
    actual_cid = compute_cidv1_for_file(filepath)
    return actual_cid == expected_cid

def main():
    """CLI utility for computing and verifying IPFS CIDs."""
    if len(sys.argv) < 2:
        print("Usage: python3 cid.py <filepath> [--verify <expected_cid>]")
        sys.exit(1)

    target_file = sys.argv[1]
    if not os.path.exists(target_file):
        print(f"Error: File '{target_file}' not found.")
        sys.exit(1)

    actual_cid = compute_cidv1_for_file(target_file)
    print(f"File: {target_file}")
    print(f"CIDv1: {actual_cid}")

    if len(sys.argv) >= 4 and sys.argv[2] == "--verify":
        expected = sys.argv[3]
        if actual_cid == expected:
            print("Status: [✓ MATCH] Content authentic and verified.")
            sys.exit(0)
        else:
            print(f"Status: [FAIL] Mismatch!\n  Expected: {expected}\n  Actual:   {actual_cid}")
            sys.exit(1)

if __name__ == "__main__":
    main()
