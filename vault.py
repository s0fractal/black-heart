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
import stat
import tarfile
import gzip
import hashlib
import tempfile
import shutil
from typing import List, Tuple, Optional, Dict, Any

VAULT_STREAM_PREFIX = "%🖤 EMBEDDED_VAULT: "

class RollbackIncompleteError(OSError):
    """
    Raised when commit failure rollback cannot complete cleanly,
    providing full diagnostic visibility into partially mutated filesystem state.
    """
    def __init__(self, commit_error: BaseException, rollback_errors: List[Tuple[str, str]]):
        self.commit_error = commit_error
        self.rollback_errors = rollback_errors
        details = "; ".join(f"{path}: {err}" for path, err in rollback_errors)
        super().__init__(
            f"ROLLBACK_INCOMPLETE: Commit failed ({commit_error}) and rollback encountered errors: {details}"
        )

class SecretMaterialError(ValueError):
    """Refusal to pack files that look like private key material."""

    def __init__(self, findings: List[Tuple[str, List[str]]]):
        self.findings = findings
        listed = "; ".join(f"{path} ({', '.join(reasons)})" for path, reasons in findings)
        super().__init__(
            f"Refusing to pack private key material into a vault: {listed}. "
            "A vault is a public reproducibility archive, not a secret store.")


def find_secret_material(file_paths: List[str], base_dir: str) -> List[Tuple[str, List[str]]]:
    """Every member that looks like private key material, with the reasons."""
    from keystore import secret_material_reasons
    findings = []
    for rel_path in sorted(file_paths):
        abs_path = os.path.join(base_dir, rel_path)
        if not os.path.isfile(abs_path):
            continue
        with open(abs_path, "rb") as f:
            reasons = secret_material_reasons(os.path.basename(rel_path), f.read())
        if reasons:
            findings.append((rel_path, reasons))
    return findings


def pack_files_to_vault(file_paths: List[str], base_dir: str) -> Tuple[bytes, str, Dict[str, Any]]:
    """
    Packs a list of files into a deterministic, compressed tar.gz byte stream.
    Explicitly enforces mtime=0 in both gzip wrapper and tar member metadata
    to guarantee byte-identical, reproducible archives regardless of system clock.
    Computes cryptographic SHA-256 hash of the vault archive and builds manifest.

    Refuses, naming each file, when any member looks like private key material:
    a key or keystore file, a named secret field, or a secret next to its own
    public key. Checked here so no caller can skip it.
    """
    findings = find_secret_material(file_paths, base_dir)
    if findings:
        raise SecretMaterialError(findings)

    buf = io.BytesIO()
    manifest_entries = []

    # Sort file paths for reproducible canonical archive ordering
    sorted_files = sorted(file_paths)

    # Wrap in explicit GzipFile with fixed mtime=0 and empty filename for true determinism
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar:
            for rel_path in sorted_files:
                abs_path = os.path.join(base_dir, rel_path)
                if not os.path.isfile(abs_path):
                    raise FileNotFoundError(f"Vault member file not found: {abs_path}")

                with open(abs_path, "rb") as f:
                    content = f.read()

                f_hash = hashlib.sha256(content).hexdigest()
                manifest_entries.append({
                    "path": rel_path,
                    "size": len(content),
                    "sha256": f_hash
                })

                # Create deterministic tarinfo with fixed epoch mtime=0
                ti = tarfile.TarInfo(name=rel_path)
                ti.size = len(content)
                ti.mtime = 0
                ti.mode = 0o644
                ti.uname = "blackheart"
                ti.gname = "blackheart"
                tar.addfile(ti, io.BytesIO(content))

    vault_bytes = buf.getvalue()
    vault_hash = hashlib.sha256(vault_bytes).hexdigest()
    manifest = {
        "vault_hash": vault_hash,
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
    - Rejection of symlinks, hardlinks, and device special files in archive
    - Protection against decompression bombs (max size & count limits)
    - Two-phase extraction (preflight + temporary staging)
    - Destination symlink breakout prevention (refuses existing symlinks in target tree)
    - Transactional commit engine: preflights all target paths for symlinks and
      collisions. On commit failure, rolls back file bytes, permissions (mode), and
      timestamps, and cleans up created files/directories. If rollback itself
      encounters errors, raises RollbackIncompleteError detailing affected paths
      to prevent masking partial mutations.
    Returns: List of unpacked relative paths.
    """
    dest_real = os.path.realpath(dest_dir)
    buf = io.BytesIO(vault_bytes)
    total_size = 0

    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        members = tar.getmembers()
        if len(members) > MAX_VAULT_FILES:
            raise ValueError(f"Vault contains {len(members)} files, exceeding limit of {MAX_VAULT_FILES}")

        # Phase 1: Preflight validation across all members before touching filesystem
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

            # Boundary preflight check
            norm = os.path.normpath(member.name)
            if norm.startswith("..") or os.path.isabs(norm):
                raise ValueError(f"Directory traversal detected: {member.name}")

        # Phase 2: Extract into isolated temporary staging directory
        unpacked_paths = []
        with tempfile.TemporaryDirectory() as staging_dir:
            staging_real = os.path.realpath(staging_dir)
            for member in members:
                target_path = os.path.realpath(os.path.join(staging_real, member.name))
                if not target_path.startswith(staging_real + os.sep) and target_path != staging_real:
                    raise ValueError(f"Directory traversal detected: {member.name}")
                tar.extract(member, path=staging_real)
                unpacked_paths.append(member.name)

            # Phase 2.5: Destination conflict & symlink preflight (Transactional Gate)
            # Collect all staging directories and files to validate against destination
            # BEFORE making any changes to dest_real!
            for root, dirs, files in os.walk(staging_real):
                rel_dir = os.path.relpath(root, staging_real)
                target_sub = os.path.join(dest_real, rel_dir) if rel_dir != "." else dest_real

                # Check intermediate path components for symlinks or type collisions
                curr = dest_real
                parts = rel_dir.split(os.sep) if rel_dir != "." else []
                for part in parts:
                    curr = os.path.join(curr, part)
                    if os.path.islink(curr):
                        raise ValueError(f"Insecure destination: existing symlink detected at directory component {curr}")
                    if os.path.exists(curr) and not os.path.isdir(curr):
                        raise FileExistsError(f"Destination collision: path component {curr} exists and is not a directory")

                # Check each target file
                for f in files:
                    dst_f = os.path.join(target_sub, f)
                    if os.path.islink(dst_f):
                        raise ValueError(f"Insecure destination: existing symlink detected at target file {dst_f}")
                    if os.path.isdir(dst_f) and not os.path.islink(dst_f):
                        raise IsADirectoryError(f"Destination collision: target path {dst_f} exists and is a directory")
                    # Ensure realpath of destination file does not escape dest_real
                    real_dst_f = os.path.realpath(dst_f)
                    if not real_dst_f.startswith(dest_real + os.sep) and real_dst_f != dest_real:
                        raise ValueError(f"Directory traversal detected in destination path: {dst_f}")

            # Phase 3: Transactional commit engine with metadata rollback on failure
            dest_existed = os.path.exists(dest_real)
            created_dirs: List[str] = []
            created_files: List[str] = []
            backup_files: Dict[str, Tuple[bytes, int, int, int]] = {}

            try:
                if not dest_existed:
                    os.makedirs(dest_real, exist_ok=True)
                    created_dirs.append(dest_real)

                for root, dirs, files in os.walk(staging_real):
                    rel_dir = os.path.relpath(root, staging_real)
                    target_sub = os.path.join(dest_real, rel_dir) if rel_dir != "." else dest_real
                    if not os.path.exists(target_sub):
                        os.makedirs(target_sub, exist_ok=True)
                        created_dirs.append(target_sub)

                    for f in files:
                        src_f = os.path.join(root, f)
                        dst_f = os.path.join(target_sub, f)

                        if os.path.exists(dst_f):
                            if dst_f not in backup_files:
                                st = os.stat(dst_f)
                                with open(dst_f, "rb") as bf:
                                    data = bf.read()
                                backup_files[dst_f] = (
                                    data,
                                    stat.S_IMODE(st.st_mode),
                                    st.st_atime_ns,
                                    st.st_mtime_ns
                                )
                        else:
                            created_files.append(dst_f)

                        shutil.copy2(src_f, dst_f)
            except BaseException as commit_err:
                rollback_errors: List[Tuple[str, str]] = []

                # Rollback Phase: restore modified files to exact pre-commit bytes, permissions, and timestamps
                for dst_f, (orig_bytes, orig_mode, orig_atime_ns, orig_mtime_ns) in backup_files.items():
                    try:
                        with open(dst_f, "wb") as rf:
                            rf.write(orig_bytes)
                        os.chmod(dst_f, orig_mode)
                        os.utime(dst_f, ns=(orig_atime_ns, orig_mtime_ns))
                    except Exception as e:
                        rollback_errors.append((dst_f, str(e)))

                # Delete newly created files
                for dst_f in created_files:
                    try:
                        if os.path.lexists(dst_f):
                            os.remove(dst_f)
                    except Exception as e:
                        rollback_errors.append((dst_f, str(e)))

                # Delete newly created directories (deepest first)
                for d in reversed(created_dirs):
                    try:
                        if os.path.exists(d) and not os.listdir(d):
                            os.rmdir(d)
                    except Exception as e:
                        rollback_errors.append((d, str(e)))

                if not dest_existed and os.path.exists(dest_real):
                    try:
                        if not os.listdir(dest_real):
                            os.rmdir(dest_real)
                    except Exception as e:
                        rollback_errors.append((dest_real, str(e)))

                if rollback_errors:
                    raise RollbackIncompleteError(commit_err, rollback_errors) from commit_err
                raise

    return unpacked_paths

def generate_pdf_embedded_file_objects(
    vault_bytes: bytes,
    vault_filename: str,
    stream_obj_id: int,
    filespec_obj_id: int
) -> Tuple[bytes, bytes]:
    """
    Generates ISO 32000 objects:
      1. EmbeddedFile stream object (with /Filter /ASCIIHexDecode to ensure zero null bytes for polyglots)
      2. Filespec dictionary object
    """
    hex_body = vault_bytes.hex().encode("ascii") + b">\n"
    stream_header = (
        f"<</Type /EmbeddedFile /Subtype /application#2Fgzip /Filter /ASCIIHexDecode "
        f"/Length {len(hex_body)} /Params <</Size {len(vault_bytes)}>>>>\nstream\n"
    ).encode("latin1")
    stream_obj = stream_header + hex_body + b"endstream"

    # 2. Filespec object
    filespec_obj = (
        f"<</Type /Filespec /F ({vault_filename}) "
        f"/UF ({vault_filename}) "
        f"/EF <</F {stream_obj_id} 0 R>>>>"
    ).encode("latin1")

    return stream_obj, filespec_obj

def extract_vault_bytes_from_pdf(pdf_path: str) -> Optional[bytes]:
    """Extracts raw vault archive bytes from a polyglot PDF document."""
    with open(pdf_path, "rb") as f:
        content = f.read()

    prefix = VAULT_STREAM_PREFIX.encode("utf-8")
    idx = content.find(prefix)
    if idx != -1:
        end_idx = content.find(b"\n", idx)
        hex_data = content[idx + len(prefix):end_idx if end_idx != -1 else len(content)].decode("ascii").strip()
        return bytes.fromhex(hex_data)

    ef_idx = content.find(b"/Type /EmbeddedFile")
    if ef_idx != -1:
        stream_start = content.find(b"stream\n", ef_idx) + len(b"stream\n")
        stream_end = content.find(b"\nendstream", stream_start)
        raw_stream = content[stream_start:stream_end].strip()
        dict_header = content[ef_idx:stream_start]
        if b"/Filter /ASCIIHexDecode" in dict_header or b"/ASCIIHexDecode" in dict_header:
            hex_str = raw_stream.rstrip(b">").decode("ascii")
            return bytes.fromhex("".join(hex_str.split()))
        else:
            return raw_stream
    return None

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

def extract_vault_from_pdf(
    pdf_path: str,
    dest_dir: str,
    expected_vault_hash: Optional[str] = None,
    allow_unverified: bool = False
) -> List[str]:
    """
    Extracts the embedded source vault from a Black-Heart polyglot PDF.
    Enforces cryptographic hash verification against embedded VAULT_HASH
    and optional expected_vault_hash pin.
    Refuses extraction if VAULT_HASH marker is missing unless expected_vault_hash
    pin is provided or allow_unverified is explicitly True.
    """
    vault_bytes = extract_vault_bytes_from_pdf(pdf_path)
    if vault_bytes is None:
        raise ValueError(f"No embedded code vault found in {pdf_path}")

    with open(pdf_path, "rb") as f:
        content = f.read()

    actual_hash = hashlib.sha256(vault_bytes).hexdigest()

    # Enforce hash verification: either embedded VAULT_HASH marker or expected_vault_hash pin
    vh_marker = "%🖤 VAULT_HASH: ".encode("utf-8")
    vh_idx = content.find(vh_marker)
    if vh_idx != -1:
        vh_end = content.find(b"\n", vh_idx)
        embedded_hash = content[vh_idx + len(vh_marker):vh_end if vh_end != -1 else len(content)].decode("ascii").strip()
        if actual_hash != embedded_hash:
            raise ValueError(f"Vault integrity violation: computed hash {actual_hash} does not match embedded VAULT_HASH {embedded_hash}")
    else:
        if expected_vault_hash is None and not allow_unverified:
            raise ValueError(f"No VAULT_HASH marker found in {pdf_path}. Refusing unverified extraction without explicit expected_vault_hash pin.")

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
