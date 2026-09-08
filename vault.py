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

MAX_VAULT_FILES = 10_000
MAX_VAULT_SIZE = 500 * 1024 * 1024  # 500 MB limit

def unpack_vault_bytes(vault_bytes: bytes, dest_dir: str) -> List[str]:
    """
    Unpacks a compressed vault into dest_dir with strict security constraints:
    - Path traversal prevention (no absolute paths, no .., boundary check)
    - Rejection of symlinks, hardlinks, and device special files
    - Protection against decompression bombs (max size & count limits)
    Returns: List of unpacked relative paths.
    """
    dest_real = os.path.realpath(dest_dir)
    os.makedirs(dest_real, exist_ok=True)
    buf = io.BytesIO(vault_bytes)
    unpacked_paths = []
    total_size = 0

    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        members = tar.getmembers()
        if len(members) > MAX_VAULT_FILES:
            raise ValueError(f"Vault contains {len(members)} files, exceeding limit of {MAX_VAULT_FILES}")

        for member in members:
            # Security check: avoid path traversal
            parts = member.name.replace("\\", "/").split("/")
            if os.path.isabs(member.name) or ".." in parts or any(p.startswith("~") for p in parts):
                raise ValueError(f"Insecure archive member path rejected: {member.name}")

            # Reject symlinks, hard links, device nodes, and fifos
            if member.issym() or member.islnk() or member.isdev() or member.ischr() or member.isfifo():
                raise ValueError(f"Insecure archive member type rejected: {member.name}")

            total_size += member.size
            if total_size > MAX_VAULT_SIZE:
                raise ValueError(f"Vault uncompressed size exceeds maximum allowed limit ({MAX_VAULT_SIZE} bytes)")

            target_path = os.path.realpath(os.path.join(dest_real, member.name))
            if not target_path.startswith(dest_real + os.sep) and target_path != dest_real:
                raise ValueError(f"Directory traversal detected: {member.name}")

            tar.extract(member, path=dest_real)
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

def extract_vault_from_pdf(pdf_path: str, dest_dir: str, expected_vault_hash: Optional[str] = None) -> List[str]:
    """
    Extracts the embedded source vault from a Black-Heart polyglot PDF.
    Enforces cryptographic hash verification against embedded VAULT_HASH
    and optional expected_vault_hash pin.
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

    actual_hash = hashlib.sha256(vault_bytes).hexdigest()

    # Verify embedded VAULT_HASH marker if present
    vh_marker = "%🖤 VAULT_HASH: ".encode("utf-8")
    vh_idx = content.find(vh_marker)
    if vh_idx != -1:
        vh_end = content.find(b"\n", vh_idx)
        embedded_hash = content[vh_idx + len(vh_marker):vh_end if vh_end != -1 else len(content)].decode("ascii").strip()
        if actual_hash != embedded_hash:
            raise ValueError(f"Vault integrity violation: computed hash {actual_hash} does not match embedded VAULT_HASH {embedded_hash}")

    if expected_vault_hash is not None:
        if actual_hash != expected_vault_hash:
            raise ValueError(f"Vault pin verification failed: computed hash {actual_hash} != expected {expected_vault_hash}")

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
