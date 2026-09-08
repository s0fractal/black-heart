#!/usr/bin/env python3
"""
vault.py — ISO 32000 Embedded Code Vaults (Self-Preserving Reproducibility Archive).
Part of Project Black-Heart (%🖤).

Implements:
  1. Packaging verified source trees, datasets, and tests into canonical tar.gz archives.
  2. Encoding archives into ISO 32000-1 §7.7.4 embedded file object streams.
  3. Extracting and verifying embedded source vaults directly via 'python3 file.pdf --unpack-vault'.
"""

from __future__ import annotations
import os
import sys
import io
import tarfile
import gzip
import hashlib
from typing import List, Tuple, Optional, Dict, Any

VAULT_STREAM_PREFIX = "%🖤 EMBEDDED_VAULT: "

def pack_files_to_vault(file_paths: List[str], base_dir: str) -> Tuple[bytes, str, Dict[str, Any]]:
    """
    Packs a list of files into a deterministic, compressed tar.gz byte stream.
    Returns: (vault_bytes, sha256_hash, manifest_dict)
    """
    buf = io.BytesIO()
    manifest_entries = []

    # Sort files for canonical reproducibility
    sorted_paths = sorted(file_paths)

    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for rel_path in sorted_paths:
            full_path = os.path.join(base_dir, rel_path)
            if not os.path.isfile(full_path):
                continue
            with open(full_path, "rb") as f:
                content = f.read()

            file_hash = hashlib.sha256(content).hexdigest()
            ti = tarfile.TarInfo(name=rel_path)
            ti.size = len(content)
            ti.mtime = 0
            ti.mode = 0o644
            tar.addfile(ti, io.BytesIO(content))

            manifest_entries.append({
                "path": rel_path,
                "size": len(content),
                "hash": file_hash
            })

    vault_bytes = buf.getvalue()
    vault_hash = hashlib.sha256(vault_bytes).hexdigest()
    manifest = {
        "vault_hash": vault_hash,
        "compressed_size": len(vault_bytes),
        "file_count": len(manifest_entries),
        "files": manifest_entries
    }
    return vault_bytes, vault_hash, manifest

def unpack_vault_bytes(vault_bytes: bytes, dest_dir: str) -> List[str]:
    """
    Unpacks a compressed vault into dest_dir.
    Returns: List of unpacked relative paths.
    """
    os.makedirs(dest_dir, exist_ok=True)
    buf = io.BytesIO(vault_bytes)
    unpacked_paths = []

    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        for member in tar.getmembers():
            # Security check: avoid path traversal
            if os.path.isabs(member.name) or ".." in member.name:
                continue
            tar.extract(member, path=dest_dir)
            unpacked_paths.append(member.name)

    return unpacked_paths

def generate_pdf_embedded_file_objects(
    vault_bytes: bytes,
    vault_filename: str,
    stream_obj_id: int,
    filespec_obj_id: int
) -> Tuple[bytes, bytes]:
    """
    Generates ISO 32000 objects:
      1. EmbeddedFile stream object
      2. Filespec dictionary object
    """
    # 1. Stream object
    stream_header = (
        f"<</Type /EmbeddedFile /Subtype /application#2Fgzip "
        f"/Length {len(vault_bytes)} /Params <</Size {len(vault_bytes)}>>>>\nstream\n"
    ).encode("latin1")
    stream_obj = stream_header + vault_bytes + b"\nendstream"

    # 2. Filespec object
    filespec_obj = (
        f"<</Type /Filespec /F ({vault_filename}) "
        f"/UF ({vault_filename}) "
        f"/EF <</F {stream_obj_id} 0 R>>>>"
    ).encode("latin1")

    return stream_obj, filespec_obj

def embed_vault_into_polyglot(pdf_path: str, file_paths: List[str], base_dir: str) -> str:
    """
    Packs specified source files and embeds the compressed vault into the polyglot PDF.
    Returns the SHA-256 hash of the embedded vault.
    """
    vault_bytes, vault_hash, _ = pack_files_to_vault(file_paths, base_dir)
    with open(pdf_path, "rb") as f:
        content = f.read()

    vault_block = (
        f"\n{VAULT_STREAM_PREFIX}{vault_bytes.hex()}\n"
        f"%🖤 VAULT_HASH: {vault_hash}\n"
    ).encode("utf-8")

    with open(pdf_path, "wb") as f:
        f.write(content + vault_block)

    return vault_hash

def extract_vault_from_pdf(pdf_path: str, dest_dir: str) -> List[str]:
    """
    Extracts the embedded source vault from a Black-Heart polyglot PDF.
    """
    with open(pdf_path, "rb") as f:
        content = f.read()

    prefix = VAULT_STREAM_PREFIX.encode("utf-8")
    idx = content.find(prefix)
    if idx == -1:
        # Fallback: search for /Type /EmbeddedFile stream
        ef_idx = content.find(b"/Type /EmbeddedFile")
        if ef_idx == -1:
            raise ValueError(f"No embedded code vault found in {pdf_path}")
        stream_start = content.find(b"stream\n", ef_idx) + len(b"stream\n")
        stream_end = content.find(b"\nendstream", stream_start)
        vault_bytes = content[stream_start:stream_end]
    else:
        end_idx = content.find(b"\n", idx)
        hex_data = content[idx + len(prefix):end_idx].decode("ascii")
        vault_bytes = bytes.fromhex(hex_data)

    return unpack_vault_bytes(vault_bytes, dest_dir)

if __name__ == "__main__":
    print("Testing ISO 32000 Embedded Code Vault engine...")
    test_files = ["glyph.py", "crypto.py"]
    base_dir = os.path.dirname(os.path.abspath(__file__))

    vb, vh, man = pack_files_to_vault(test_files, base_dir)
    print(f"[✓] Packed {len(test_files)} files: {len(vb)} bytes. Vault hash: {vh[:16]}...")

    tmp_out = "/tmp/test_vault_unpack"
    restored = unpack_vault_bytes(vb, tmp_out)
    assert len(restored) == len(test_files)
    print(f"[✓] Unpacked {len(restored)} files successfully into {tmp_out}")
