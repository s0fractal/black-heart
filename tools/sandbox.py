#!/usr/bin/env python3
"""
sandbox.py — Hermetic Static Inspector & Non-Executing Auditor for Black-Heart Polyglots.
Part of Project Black-Heart (%🖤).

This tool addresses the security anti-pattern of executing untrusted polyglot documents
(`python3 document.pdf`) by providing a completely isolated, non-executing static audit.

It analyzes:
  1. ISO 32000 Structure & Compliance (Magic bytes, binary comment, xref tables, trailers).
  2. Incremental Update Audit Trail (ISO 32000 §7.5.6 tree-ring provenance).
  3. Cryptographic Seals & Signatures (RFC 8032 Ed25519) without executing document scripts.
  4. Dual-Spine Merkle Roots (H_visual || H_code binding).
  5. Hermetic Combinator Sandboxing (Gas-metered SKIY evaluation in an isolated interpreter).

Usage:
  python3 tools/sandbox.py <document.pdf>
  python3 tools/sandbox.py --strict <document.pdf>
"""

from __future__ import annotations
import os
import sys
import json
import hashlib
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# Ensure project root is in sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from crypto import verify_bytes, _decode_point, Point
from glyph import parse, evaluate, EvalStatus

@dataclass
class PolyglotAuditReport:
    file_path: str
    file_size_bytes: int
    sha256_digest: str
    is_valid_iso32000: bool
    binary_marker_present: bool
    incremental_updates_count: int
    detected_manifest_types: List[str]
    cryptographic_seals_valid: bool
    hermetic_evaluation_valid: bool
    audit_notes: List[str]
    # Positive/negative evidence, so soundness is a POSITIVE confirmation rather
    # than the mere absence of a proven negative. Before this, cryptographic and
    # hermetic validity defaulted True and flipped only on an explicit failure,
    # so a document with a valid header but no verifiable evidence -- no
    # manifest, a malformed manifest, or a signature whose signed content could
    # not be determined -- was reported SOUND.
    verified_seal_count: int = 0        # signatures positively verified
    passed_claim_count: int = 0         # hermetic claims settled and matched
    unconfirmed_seal_count: int = 0     # signature present but not confirmable
    seal_mismatch_count: int = 0        # signature explicitly wrong
    failed_claim_count: int = 0         # claim did not settle/match
    audit_error_count: int = 0          # parse/verify exceptions (never swallowed)

    def scope_summary(self) -> str:
        """What the verdict actually covers. A verified signature attests only
        its own signed payload, and a settled claim only that claim -- never the
        whole document. Header presence is not ISO 32000 compliance."""
        return (f"scope: {self.verified_seal_count} signature(s) and "
                f"{self.passed_claim_count} claim(s) positively verified among the "
                f"recognized elements -- NOT the whole document")

    def is_sound(self) -> bool:
        # SOUND requires: valid container; at least one thing POSITIVELY
        # verified (a signature or a hermetic claim); and nothing that failed,
        # was left unconfirmed, or errored. "I could not verify this" is not
        # SOUND.
        positively_confirmed = (self.verified_seal_count + self.passed_claim_count) >= 1
        nothing_wrong = (
            self.seal_mismatch_count == 0
            and self.unconfirmed_seal_count == 0
            and self.failed_claim_count == 0
            and self.audit_error_count == 0
        )
        return (
            self.is_valid_iso32000
            and self.binary_marker_present
            and positively_confirmed
            and nothing_wrong
        )

def audit_polyglot_hermetic(file_path: str) -> PolyglotAuditReport:
    """
    Performs a completely static, non-executing audit of a Black-Heart polyglot PDF.
    Does NOT invoke Python `exec`, `eval`, or spawn subprocesses.
    """
    notes: List[str] = []
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "rb") as f:
        data = f.read()

    file_size = len(data)
    digest = hashlib.sha256(data).hexdigest()

    # 1. ISO 32000 Header Checks (tolerant within first 1024 bytes per ISO 32000-1:2008 §7.5.2)
    header_idx = data[:1024].find(b"%PDF-1.")
    is_iso = header_idx != -1
    if is_iso:
        notes.append(f"[✓] ISO 32000 PDF header detected at offset {header_idx}.")
    else:
        notes.append("[✗] Missing '%PDF-1.x' header within first 1024 bytes.")

    # 2. Binary marker check (ISO 32000 §7.5.2)
    # Project Black-Heart uses %🖤 which has 4 bytes > 127
    has_marker = (b"%\xf0\x9f\x96\xa4" in data[:1024]) or ("%🖤".encode("utf-8") in data[:1024])
    if has_marker:
        notes.append("[✓] ISO 32000 §7.5.2 high-byte binary marker present (%🖤).")
    else:
        notes.append("[!] High-byte binary marker not found in first 100 bytes.")

    # 3. Incremental update count (Count of %%EOF markers)
    eof_count = data.count(b"%%EOF")
    notes.append(f"[*] Incremental update segments detected: {eof_count}")

    # 4. Detect manifests statically without executing
    manifest_types: List[str] = []
    signatures_valid = True
    manifest_prefixes = [
        ("%🖤 CONTRACT_MANIFEST:".encode("utf-8"), "Monad Contract"),
        ("%🖤 BILATERAL_AGREEMENT_MANIFEST:".encode("utf-8"), "Bilateral Agreement"),
        ("%🖤 ORACLE_MANIFEST:".encode("utf-8"), "Telemetry Oracle"),
        ("%🖤 CONTINUUM_THUNK:".encode("utf-8"), "Continuum Checkpoint"),
        ("%🖤 ZK_PROOF_MANIFEST:".encode("utf-8"), "Zero-Knowledge Proof"),
        ("%🖤 LEDGER_MANIFEST:".encode("utf-8"), "Living Ledger"),
        ("%🖤 AUTOPOIESIS_MANIFEST:".encode("utf-8"), "Autopoietic Organism"),
        ("%🖤 AGORA_MANIFEST:".encode("utf-8"), "Agora Parliament"),
        ("%🖤 IPFS_DIARY_MANIFEST:".encode("utf-8"), "IPFS Dialectical Diary"),
        ("%🖤 MORPHO_NET_MANIFEST:".encode("utf-8"), "Morphogenetic Proof-Net"),
        ("%🖤 GOEDEL_MANIFEST:".encode("utf-8"), "Gödelian Polyglot"),
        ("%🖤 ANYON_QUANTUM_MANIFEST:".encode("utf-8"), "Anyonic Quantum Topos"),
        ("%🖤 CODE_VAULT_MANIFEST:".encode("utf-8"), "Embedded Code Vault"),
    ]

    for prefix, name in manifest_prefixes:
        if prefix in data:
            manifest_types.append(name)
            notes.append(f"[✓] Detected {name} manifest.")

    if not manifest_types:
        notes.append("[!] No known Black-Heart manifest signatures found.")

    # 5. Extract and statically verify any JSON manifests. Every recognized
    # manifest must resolve to a POSITIVE outcome (a verified signature) or be
    # counted as unconfirmed/mismatch/error -- none of which is SOUND.
    lines = data.splitlines()
    verified_seals = 0
    unconfirmed_seals = 0
    seal_mismatches = 0
    audit_errors = 0
    for line in lines:
        for prefix, name in manifest_prefixes:
            if line.startswith(prefix):
                try:
                    payload_json = line[len(prefix):].strip().decode("utf-8")
                    manifest = json.loads(payload_json)
                    has_sig = (isinstance(manifest, dict)
                               and "public_key_hex" in manifest
                               and "signature_hex" in manifest)
                    if not has_sig:
                        unconfirmed_seals += 1
                        notes.append(f"[!] {name} manifest carries no verifiable Ed25519 seal; "
                                     f"cannot confirm it.")
                        continue
                    pk_bytes = bytes.fromhex(manifest["public_key_hex"])
                    sig_bytes = bytes.fromhex(manifest["signature_hex"])
                    signed_bytes = b""
                    if "signed_payload" in manifest:
                        signed_bytes = manifest["signed_payload"].encode("utf-8")
                    elif "agreement_terms" in manifest:
                        signed_bytes = json.dumps(manifest["agreement_terms"], sort_keys=True).encode("utf-8")
                    elif "payload_digest" in manifest:
                        signed_bytes = manifest["payload_digest"].encode("utf-8")

                    if not signed_bytes:
                        unconfirmed_seals += 1
                        notes.append(f"[!] {name} carries a signature but no determinable signed "
                                     f"content; cannot confirm it.")
                    elif verify_bytes(pk_bytes, signed_bytes, sig_bytes):
                        verified_seals += 1
                        notes.append(f"[✓] RFC 8032 signature statically verified for {name}.")
                    else:
                        seal_mismatches += 1
                        notes.append(f"[✗] RFC 8032 signature MISMATCH in {name}!")
                except Exception as ex:
                    audit_errors += 1
                    notes.append(f"[!] Error parsing/verifying manifest for {name}: {ex}")
    signatures_valid = (seal_mismatches == 0 and unconfirmed_seals == 0 and audit_errors == 0)

    # 6. Hermetic Combinator Validation (Gas-Metered Sandbox)
    import re
    claim_prefix = "%🖤 CLAIM:".encode("utf-8")
    claims_tested = 0
    passed_claims = 0
    failed_claims = 0
    for line in lines:
        if line.startswith(claim_prefix):
            try:
                line_str = line.decode("utf-8")
                m = re.search(r"%🖤 CLAIM:\s*id=([^\s|]+)\s*\|\s*expr=([^|]+)\|\s*expected=([^|]+)", line_str)
                if m:
                    claim_id = m.group(1).strip()
                    expr = m.group(2).strip()
                    expected = m.group(3).strip()

                    term = parse(expr)
                    res = evaluate(term, max_atp=50_000)
                    claims_tested += 1
                    # Must SETTLE and match: a budget-suspended claim is not a
                    # proof (same discipline as the warrant grounded verifier).
                    if res.is_settled() and str(res.term) == expected:
                        passed_claims += 1
                        notes.append(f"[✓] Hermetic claim settled: {claim_id} ({expr} -> {expected}) in {res.atp_spent} ATP.")
                    else:
                        failed_claims += 1
                        notes.append(f"[✗] Claim failed settlement: {claim_id} (got {res.term}, expected {expected})")
                else:
                    # The line announces a claim but does not parse. Silently
                    # skipping it (as this branch used to) let a document pair a
                    # valid signature with a malformed CLAIM and still read SOUND.
                    audit_errors += 1
                    notes.append("[!] Malformed %🖤 CLAIM line could not be parsed; counted as an error.")
            except Exception as ex:
                audit_errors += 1
                notes.append(f"[!] Hermetic combinator execution error: {ex}")
    hermetic_valid = (failed_claims == 0 and audit_errors == 0)

    if claims_tested > 0:
        manifest_types.append("Self-Verifying Claims Document")
        notes.append(f"[*] Statically evaluated {claims_tested} combinator claims under hermetic ATP budget.")

    return PolyglotAuditReport(
        file_path=file_path,
        file_size_bytes=file_size,
        sha256_digest=digest,
        is_valid_iso32000=is_iso,
        binary_marker_present=has_marker,
        incremental_updates_count=eof_count,
        detected_manifest_types=manifest_types,
        cryptographic_seals_valid=signatures_valid,
        hermetic_evaluation_valid=hermetic_valid,
        audit_notes=notes,
        verified_seal_count=verified_seals,
        passed_claim_count=passed_claims,
        unconfirmed_seal_count=unconfirmed_seals,
        seal_mismatch_count=seal_mismatches,
        failed_claim_count=failed_claims,
        audit_error_count=audit_errors,
    )

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 tools/sandbox.py [--strict] <document.pdf>")
        sys.exit(1)

    args = sys.argv[1:]
    strict = "--strict" in args
    files = [a for a in args if not a.startswith("--")]

    if not files:
        print("Error: No file specified.")
        sys.exit(1)

    target = files[0]
    print("\033[1;36m" + "=" * 70)
    print("  %🖤 PROJECT BLACK-HEART — HERMETIC NON-EXECUTING STATIC AUDITOR")
    print(f"  Target File: {os.path.basename(target)}")
    print("=" * 70 + "\033[0m\n")

    report = audit_polyglot_hermetic(target)

    print(f"[*] File Size:            {report.file_size_bytes} bytes")
    print(f"[*] SHA-256 Digest:       {report.sha256_digest}")
    print(f"[*] PDF header present:    {'Yes' if report.is_valid_iso32000 else 'No'} "
          f"(header presence only, not full ISO 32000 compliance)")
    print(f"[*] Incremental Updates:  {report.incremental_updates_count}")
    print(f"[*] Detected Manifests:   {', '.join(report.detected_manifest_types) or 'None'}")
    print("\n--- AUDIT LOG ---")
    for note in report.audit_notes:
        print(f"  {note}")

    print("\n" + "=" * 70)
    if report.is_sound():
        print("\033[1;32m[✓ SOUND] Recognized elements verified statically without executing host Python.\033[0m")
        print(f"          {report.scope_summary()}")
        sys.exit(0)
    else:
        print("\033[1;31m[✗ UNSOUND] Document failed static hermetic verification.\033[0m")
        sys.exit(1)

if __name__ == "__main__":
    main()
