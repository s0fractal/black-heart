#!/usr/bin/env python3
"""
cross_proof.py — Bilateral Interlocking Multi-Document Adjudication Protocol.
Part of Project Black-Heart (%🖤).

Implements:
  1. Cryptographic cross-verification between independent polyglot documents.
  2. TelemetryOraclePolyglot (signed infrastructure telemetry by Datadog/Cloudflare).
  3. BilateralAgreementPolyglot (SLA contract with embedded oracle public key constraint).
  4. Bilateral settlement receipt with joint cryptographic anchor:
     H_bilateral = SHA-256(H_agreement || H_oracle || Receipt)
"""

from __future__ import annotations
import os
import sys
import json
import time
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any

from crypto import (
    generate_keypair,
    public_key_from_secret,
    sign_bytes,
    verify_bytes,
    CryptographicSeal
)

ORACLE_MANIFEST_PREFIX = "%🖤 ORACLE_MANIFEST: "
AGREEMENT_MANIFEST_PREFIX = "%🖤 BILATERAL_MANIFEST: "

@dataclass
class TelemetryIncident:
    record_id: str
    timestamp_utc: str
    event_type: str
    duration_minutes: int
    raw_evidence_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "timestamp_utc": self.timestamp_utc,
            "event_type": self.event_type,
            "duration_minutes": self.duration_minutes,
            "raw_evidence_hash": self.raw_evidence_hash
        }

@dataclass
class BilateralSettlementReceipt:
    status: str  # "SETTLED_COMPLIANT" or "SETTLED_BREACH"
    agreement_title: str
    oracle_name: str
    oracle_pk_hex: str
    measured_uptime_percent: float
    target_uptime_percent: float
    penalty_due_usd: int
    net_service_due_usd: int
    agreement_anchor: str
    oracle_anchor: str
    joint_bilateral_digest: str
    timestamp_utc: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "agreement_title": self.agreement_title,
            "oracle_name": self.oracle_name,
            "oracle_pk_hex": self.oracle_pk_hex,
            "measured_uptime_percent": self.measured_uptime_percent,
            "target_uptime_percent": self.target_uptime_percent,
            "penalty_due_usd": self.penalty_due_usd,
            "net_service_due_usd": self.net_service_due_usd,
            "agreement_anchor": self.agreement_anchor,
            "oracle_anchor": self.oracle_anchor,
            "joint_bilateral_digest": self.joint_bilateral_digest,
            "timestamp_utc": self.timestamp_utc
        }

# ============================================================================
# TELEMETRY ORACLE COMPILER
# ============================================================================

class TelemetryOraclePolyglot:
    """
    Compiles an authenticated infrastructure telemetry report into an ISO 32000 PDF.
    Signed by the independent oracle's Ed25519 key.
    """
    def __init__(self, oracle_name: str, oracle_role: str = "INDEPENDENT_TELEMETRY_ORACLE"):
        self.oracle_name = oracle_name
        self.oracle_role = oracle_role
        self.incidents: List[TelemetryIncident] = []
        self.total_period_minutes: int = 43200 # 30 days

    def add_incident(self, record_id: str, timestamp_utc: str, event_type: str, duration_minutes: int):
        sig_str = f"{record_id}|{timestamp_utc}|{event_type}|{duration_minutes}"
        h = hashlib.sha256(sig_str.encode("utf-8")).hexdigest()
        self.incidents.append(TelemetryIncident(
            record_id=record_id,
            timestamp_utc=timestamp_utc,
            event_type=event_type,
            duration_minutes=duration_minutes,
            raw_evidence_hash=h
        ))

    def compile(self, output_path: str, oracle_secret_key_hex: str) -> str:
        sk_bytes = bytes.fromhex(oracle_secret_key_hex)
        pk_bytes = public_key_from_secret(sk_bytes)
        pk_hex = pk_bytes.hex()

        total_downtime = sum(i.duration_minutes for i in self.incidents)
        uptime_pct = ((self.total_period_minutes - total_downtime) / self.total_period_minutes) * 100.0

        # Sign canonical payload
        payload_data = {
            "oracle_name": self.oracle_name,
            "oracle_role": self.oracle_role,
            "total_period_minutes": self.total_period_minutes,
            "total_downtime_minutes": total_downtime,
            "measured_uptime_percent": round(uptime_pct, 4),
            "incidents": [i.to_dict() for i in self.incidents]
        }
        payload_bytes = json.dumps(payload_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        oracle_sig = sign_bytes(sk_bytes, payload_bytes).hex()
        oracle_anchor = hashlib.sha256(payload_bytes + bytes.fromhex(oracle_sig)).hexdigest()

        # Build PDF Stream
        page_width, page_height = 595, 842
        margin = 54
        content_width = page_width - 2 * margin

        stream_lines = []
        y = page_height - margin

        stream_lines.append(f"BT /F1 18 Tf 0.1 0.25 0.45 rg {margin} {y} Td (INDEPENDENT TELEMETRY ORACLE REPORT) Tj 0 g ET")
        y -= 22
        stream_lines.append(f"BT /F3 10 Tf 0.3 0.35 0.4 rg {margin} {y} Td (Oracle: {_escape_pdf(self.oracle_name)} | Ed25519 Signed Telemetry) Tj 0 g ET")
        y -= 14
        stream_lines.append(f"0.8 0.82 0.88 rg {margin} {y} {content_width} 1 re f 0 g")
        y -= 20

        # Telemetry Card Box
        card_h = 75
        stream_lines.append(f"0.96 0.97 0.99 rg {margin} {y - card_h + 10} {content_width} {card_h} re f 0 g")
        stream_lines.append(f"0.3 0.5 0.7 RG 1 w {margin} {y - card_h + 10} {content_width} {card_h} re s 0 g")

        stream_lines.append(f"BT /F1 11 Tf 0.1 0.2 0.4 rg {margin + 12} {y - 4} Td (Attested Measurement: {uptime_pct:.3f}% Uptime across {self.total_period_minutes} min) Tj 0 g ET")
        y -= 16
        stream_lines.append(f"BT /F4 8 Tf 0.2 0.2 0.2 rg {margin + 12} {y} Td (Oracle PK: {pk_hex[:32]}... | Signature: {oracle_sig[:24]}... [SOUND]) Tj 0 g ET")
        y -= 13
        stream_lines.append(f"BT /F4 8 Tf 0.2 0.2 0.2 rg {margin + 12} {y} Td (Total Incidents: {len(self.incidents)} | Total Outage Duration: {total_downtime} minutes) Tj 0 g ET")
        y -= 13
        stream_lines.append(f"BT /F1 9 Tf 0.1 0.4 0.2 rg {margin + 12} {y} Td (Oracle Merkle Anchor: {oracle_anchor}) Tj 0 g ET")
        y -= 35

        # Incident List
        stream_lines.append(f"BT /F1 12 Tf 0.15 0.2 0.3 rg {margin} {y} Td (Attested Incident Event Log) Tj 0 g ET")
        y -= 16
        for inc in self.incidents:
            stream_lines.append(f"BT /F4 8 Tf 0.3 0.1 0.1 rg {margin + 10} {y} Td ([INCIDENT] {inc.record_id}: {inc.event_type} ({inc.duration_minutes} min) | Hash: {inc.raw_evidence_hash[:16]}) Tj 0 g ET")
            y -= 13

        # Footer Box
        y = margin + 35
        stream_lines.append(f"0.92 0.94 0.97 rg {margin} {y - 20} {content_width} 24 re f 0 g")
        stream_lines.append(f"BT /F1 9 Tf 0.1 0.3 0.2 rg {margin + 10} {y - 8} Td (Oracle Certificate: Run 'python3 <this_file>.pdf' to verify authenticity) Tj 0 g ET")

        content_bytes = "\n".join(stream_lines).encode("latin1", errors="replace")

        objs: List[bytes] = []
        objs.append(b"<</Type /Catalog /Pages 2 0 R>>")
        objs.append(b"<</Type /Pages /Kids [3 0 R] /Count 1>>")
        objs.append(
            f"<</Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] "
            f"/Contents 4 0 R /Resources <</Font <</F1 5 0 R /F2 6 0 R /F3 7 0 R /F4 8 0 R>>>>>>".encode("latin1")
        )
        objs.append(
            f"<</Length {len(content_bytes)}>>\nstream\n".encode("latin1")
            + content_bytes
            + b"\nendstream"
        )
        objs.append(b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold>>")
        objs.append(b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>")
        objs.append(b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique>>")
        objs.append(b"<</Type /Font /Subtype /Type1 /BaseFont /Courier>>")

        pdf_header = (
            b"# coding: utf-8\n"
            b'r"""%PDF-1.7\n'
            b"%\xf0\x9f\x96\xa4\n"
        )

        manifest_dict = {
            "oracle_name": self.oracle_name,
            "oracle_role": self.oracle_role,
            "public_key_hex": pk_hex,
            "signature_hex": oracle_sig,
            "oracle_anchor": oracle_anchor,
            "payload": payload_data
        }
        manifest_str = json.dumps(manifest_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        manifest_comment = f"{ORACLE_MANIFEST_PREFIX}{manifest_str}\n".encode("utf-8")

        body = bytearray(pdf_header)
        body.extend(manifest_comment)

        offsets = [0]
        for i, o in enumerate(objs, 1):
            offsets.append(len(body))
            body.extend(f"{i} 0 obj\n".encode("latin1"))
            body.extend(o)
            body.extend(b"\nendobj\n")

        xstart = len(body)
        body.extend(f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode("latin1"))
        for off in offsets[1:]:
            body.extend(f"{off:010d} 00000 n \n".encode("latin1"))

        body.extend(
            f"trailer\n<</Size {len(objs)+1} /Root 1 0 R>>\nstartxref\n{xstart}\n%%EOF\n\"\"\"\n".encode("latin1")
        )

        # Standalone verifier
        runner = _generate_oracle_runner()
        body.extend(runner.encode("utf-8"))

        with open(output_path, "wb") as f:
            f.write(body)

        return output_path

# ============================================================================
# BILATERAL AGREEMENT COMPILER
# ============================================================================

class BilateralAgreementPolyglot:
    """
    Compiles an SLA agreement that defines bilateral adjudication against
    a trusted Telemetry Oracle. Terms are cryptographically signed by the issuer
    and registered parties.
    """
    def __init__(
        self,
        title: str,
        trusted_oracle_pk_hex: str,
        target_uptime_percent: float = 99.5,
        base_fee_usd: int = 10000,
        penalty_rate_usd: int = 500,
        agreement_secret_key_hex: Optional[str] = None
    ):
        self.title = title
        self.trusted_oracle_pk_hex = trusted_oracle_pk_hex
        self.target_uptime_percent = target_uptime_percent
        self.base_fee_usd = base_fee_usd
        self.penalty_rate_usd = penalty_rate_usd
        self.parties: List[Dict[str, Any]] = []
        if agreement_secret_key_hex:
            self._sk = agreement_secret_key_hex
            self._pk = public_key_from_secret(bytes.fromhex(agreement_secret_key_hex)).hex()
        else:
            self._sk, self._pk = generate_keypair()

    def canonical_terms_bytes(self) -> bytes:
        terms = {
            "title": self.title,
            "trusted_oracle_pk_hex": self.trusted_oracle_pk_hex,
            "target_uptime_percent": self.target_uptime_percent,
            "base_fee_usd": self.base_fee_usd,
            "penalty_rate_usd": self.penalty_rate_usd,
        }
        return json.dumps(terms, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def add_party(self, role: str, name: str, pk_hex: str, secret_key_hex: Optional[str] = None):
        self.parties.append({
            "role": role,
            "name": name,
            "public_key_hex": pk_hex,
            "secret_key_hex": secret_key_hex
        })

    def compile(self, output_path: str) -> str:
        page_width, page_height = 595, 842
        margin = 54
        content_width = page_width - 2 * margin

        terms_b = self.canonical_terms_bytes()
        author_sig = sign_bytes(bytes.fromhex(self._sk), terms_b).hex()

        compiled_parties = []
        for p in self.parties:
            cp = {
                "role": p["role"],
                "name": p["name"],
                "public_key_hex": p["public_key_hex"]
            }
            if p.get("secret_key_hex"):
                cp["signature_hex"] = sign_bytes(bytes.fromhex(p["secret_key_hex"]), terms_b).hex()
            compiled_parties.append(cp)

        stream_lines = []
        y = page_height - margin

        stream_lines.append(f"BT /F1 18 Tf 0.1 0.2 0.35 rg {margin} {y} Td ({_escape_pdf(self.title)}) Tj 0 g ET")
        y -= 22
        stream_lines.append(
            f"BT /F3 10 Tf 0.3 0.35 0.4 rg {margin} {y} Td "
            f"(Bilateral Interlocking Proof-Bearing Contract | Target Uptime: {self.target_uptime_percent}%) Tj 0 g ET"
        )
        y -= 14
        stream_lines.append(f"0.8 0.82 0.88 rg {margin} {y} {content_width} 1 re f 0 g")
        y -= 20

        # Agreement Terms Card
        card_h = 80
        stream_lines.append(f"0.97 0.98 0.99 rg {margin} {y - card_h + 10} {content_width} {card_h} re f 0 g")
        stream_lines.append(f"0.2 0.4 0.6 RG 1 w {margin} {y - card_h + 10} {content_width} {card_h} re s 0 g")

        stream_lines.append(f"BT /F1 11 Tf 0.1 0.25 0.5 rg {margin + 12} {y - 4} Td (Bilateral Terms & Expected Telemetry Oracle) Tj 0 g ET")
        y -= 16
        stream_lines.append(f"BT /F4 8 Tf 0.2 0.2 0.2 rg {margin + 12} {y} Td (Trusted Oracle PK: {self.trusted_oracle_pk_hex[:32]}...) Tj 0 g ET")
        y -= 13
        stream_lines.append(f"BT /F4 8 Tf 0.2 0.2 0.2 rg {margin + 12} {y} Td (Base Monthly Service Fee: ${self.base_fee_usd:,} USD | Penalty Rate: ${self.penalty_rate_usd} / 0.1% outage) Tj 0 g ET")
        y -= 13
        stream_lines.append(f"BT /F1 9 Tf 0.1 0.45 0.2 rg {margin + 12} {y} Td (Author PK: {self._pk[:32]}... | Signature: {author_sig[:24]}...) Tj 0 g ET")
        y -= 35

        # Footer Box
        y = margin + 35
        stream_lines.append(f"0.92 0.94 0.97 rg {margin} {y - 20} {content_width} 24 re f 0 g")
        stream_lines.append(f"BT /F1 9 Tf 0.1 0.3 0.2 rg {margin + 10} {y - 8} Td (Adjudication: Run 'python3 <this_file>.pdf --adjudicate-with <oracle.pdf>') Tj 0 g ET")

        content_bytes = "\n".join(stream_lines).encode("latin1", errors="replace")

        objs: List[bytes] = []
        objs.append(b"<</Type /Catalog /Pages 2 0 R>>")
        objs.append(b"<</Type /Pages /Kids [3 0 R] /Count 1>>")
        objs.append(
            f"<</Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] "
            f"/Contents 4 0 R /Resources <</Font <</F1 5 0 R /F2 6 0 R /F3 7 0 R /F4 8 0 R>>>>>>".encode("latin1")
        )
        objs.append(
            f"<</Length {len(content_bytes)}>>\nstream\n".encode("latin1")
            + content_bytes
            + b"\nendstream"
        )
        objs.append(b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold>>")
        objs.append(b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>")
        objs.append(b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique>>")
        objs.append(b"<</Type /Font /Subtype /Type1 /BaseFont /Courier>>")

        pdf_header = (
            b"# coding: utf-8\n"
            b'r"""%PDF-1.7\n'
            b"%\xf0\x9f\x96\xa4\n"
        )

        manifest_data = {
            "title": self.title,
            "trusted_oracle_pk_hex": self.trusted_oracle_pk_hex,
            "target_uptime_percent": self.target_uptime_percent,
            "base_fee_usd": self.base_fee_usd,
            "penalty_rate_usd": self.penalty_rate_usd,
            "agreement_author_pk_hex": self._pk,
            "agreement_signature_hex": author_sig,
            "parties": compiled_parties
        }
        manifest_str = json.dumps(manifest_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        manifest_comment = f"{AGREEMENT_MANIFEST_PREFIX}{manifest_str}\n".encode("utf-8")

        body = bytearray(pdf_header)
        body.extend(manifest_comment)

        offsets = [0]
        for i, o in enumerate(objs, 1):
            offsets.append(len(body))
            body.extend(f"{i} 0 obj\n".encode("latin1"))
            body.extend(o)
            body.extend(b"\nendobj\n")

        xstart = len(body)
        body.extend(f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode("latin1"))
        for off in offsets[1:]:
            body.extend(f"{off:010d} 00000 n \n".encode("latin1"))

        body.extend(
            f"trailer\n<</Size {len(objs)+1} /Root 1 0 R>>\nstartxref\n{xstart}\n%%EOF\n\"\"\"\n".encode("latin1")
        )

        runner = _generate_agreement_runner()
        body.extend(runner.encode("utf-8"))

        with open(output_path, "wb") as f:
            f.write(body)

        return output_path

# ============================================================================
# CROSS-DOCUMENT ADJUDICATION ENGINE
# ============================================================================

def adjudicate_bilateral(
    agreement_pdf_path: str,
    oracle_pdf_path: str,
    expected_agreement_hash: Optional[str] = None
) -> BilateralSettlementReceipt:
    """
    Executes bilateral adjudication between an Agreement Polyglot and an Oracle Polyglot.
    Verifies mutual Ed25519 signatures, recomputed anchors, and identity constraints.
    """
    # 1. Read Agreement Polyglot
    with open(agreement_pdf_path, "rb") as f:
        ag_content = f.read()

    if expected_agreement_hash:
        actual_ag_anchor = hashlib.sha256(ag_content).hexdigest()
        if actual_ag_anchor != expected_agreement_hash:
            raise PermissionError(f"Agreement anchor mismatch: expected {expected_agreement_hash}, got {actual_ag_anchor}")

    ag_prefix = AGREEMENT_MANIFEST_PREFIX.encode("utf-8")
    ag_idx = ag_content.find(ag_prefix)
    if ag_idx == -1:
        raise ValueError(f"No BILATERAL_MANIFEST found in {agreement_pdf_path}")
    ag_end = ag_content.find(b"\n", ag_idx)
    ag_manifest = json.loads(ag_content[ag_idx + len(ag_prefix):ag_end].decode("utf-8"))

    # 2. Verify Agreement Author Signature over canonical terms
    terms_dict = {
        "title": ag_manifest["title"],
        "trusted_oracle_pk_hex": ag_manifest["trusted_oracle_pk_hex"],
        "target_uptime_percent": ag_manifest["target_uptime_percent"],
        "base_fee_usd": ag_manifest["base_fee_usd"],
        "penalty_rate_usd": ag_manifest["penalty_rate_usd"],
    }
    terms_bytes = json.dumps(terms_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    author_pk = ag_manifest.get("agreement_author_pk_hex")
    author_sig = ag_manifest.get("agreement_signature_hex")
    if not author_pk or not author_sig:
        raise PermissionError("Agreement is missing cryptographic signature! Untrusted agreement.")

    if not verify_bytes(bytes.fromhex(author_pk), terms_bytes, bytes.fromhex(author_sig)):
        raise PermissionError("Agreement terms altered or signature invalid! Refusing unverified agreement.")

    # Also verify any registered party signatures if provided
    for party in ag_manifest.get("parties", []):
        if party.get("signature_hex"):
            pk = bytes.fromhex(party["public_key_hex"])
            sig = bytes.fromhex(party["signature_hex"])
            if not verify_bytes(pk, terms_bytes, sig):
                raise PermissionError(f"Party signature invalid for '{party.get('name')}'!")

    # 3. Read Oracle Polyglot
    with open(oracle_pdf_path, "rb") as f:
        or_content = f.read()

    or_prefix = ORACLE_MANIFEST_PREFIX.encode("utf-8")
    or_idx = or_content.find(or_prefix)
    if or_idx == -1:
        raise ValueError(f"No ORACLE_MANIFEST found in {oracle_pdf_path}")
    or_end = or_content.find(b"\n", or_idx)
    or_manifest = json.loads(or_content[or_idx + len(or_prefix):end_idx if (end_idx := or_end) != -1 else len(or_content)].decode("utf-8"))

    # 4. Verify Oracle's Ed25519 signature
    oracle_pk_bytes = bytes.fromhex(or_manifest["public_key_hex"])
    oracle_sig_bytes = bytes.fromhex(or_manifest["signature_hex"])
    payload_data = or_manifest["payload"]
    payload_bytes = json.dumps(payload_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    sig_ok = verify_bytes(oracle_pk_bytes, payload_bytes, oracle_sig_bytes)
    if not sig_ok:
        raise PermissionError("Oracle Ed25519 signature verification FAILED! Untrusted or tampered telemetry.")

    # 5. Recompute and verify Oracle anchor
    computed_or_anchor = hashlib.sha256(payload_bytes + oracle_sig_bytes).hexdigest()
    if or_manifest.get("oracle_anchor") != computed_or_anchor:
        raise PermissionError(f"Oracle anchor mismatch! Embedded: {or_manifest.get('oracle_anchor')}, Computed: {computed_or_anchor}")

    # 6. Verify Oracle Identity Constraint
    trusted_pk = ag_manifest["trusted_oracle_pk_hex"]
    if or_manifest["public_key_hex"] != trusted_pk:
        raise PermissionError(f"Oracle identity mismatch! Expected PK: {trusted_pk[:16]}..., got: {or_manifest['public_key_hex'][:16]}...")

    # 7. Extract oracle_name STRICTLY from signed payload
    oracle_name = payload_data.get("oracle_name", "UNKNOWN_ORACLE")

    # 8. Adjudicate SLA Formula against attested facts
    actual_uptime = payload_data["measured_uptime_percent"]
    target_uptime = ag_manifest["target_uptime_percent"]
    base_fee = ag_manifest["base_fee_usd"]
    penalty_rate = ag_manifest["penalty_rate_usd"]

    breach = actual_uptime < target_uptime
    deficit = max(0.0, target_uptime - actual_uptime)
    tenths = int(deficit * 10)
    penalty_due = tenths * penalty_rate
    net_payable = max(0, base_fee - penalty_due)

    status = "SETTLED_BREACH" if breach else "SETTLED_COMPLIANT"
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # 9. Joint Bilateral Digest
    ag_anchor = hashlib.sha256(ag_content).hexdigest()
    or_anchor = computed_or_anchor

    joint_payload = f"{ag_anchor}|{or_anchor}|{status}|{penalty_due}|{net_payable}|{ts}"
    joint_digest = hashlib.sha256(joint_payload.encode("utf-8")).hexdigest()

    return BilateralSettlementReceipt(
        status=status,
        agreement_title=ag_manifest["title"],
        oracle_name=oracle_name,
        oracle_pk_hex=or_manifest["public_key_hex"],
        measured_uptime_percent=actual_uptime,
        target_uptime_percent=target_uptime,
        penalty_due_usd=penalty_due,
        net_service_due_usd=net_payable,
        agreement_anchor=ag_anchor,
        oracle_anchor=or_anchor,
        joint_bilateral_digest=joint_digest,
        timestamp_utc=ts
    )

def _escape_pdf(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

def _generate_oracle_runner() -> str:
    return r'''
# --- ORACLE STANDALONE AUDITOR ---
import os, sys, json, hashlib

def main():
    target = sys.argv[0]
    print("\033[1;36m" + "=" * 65)
    print("  %🖤 BLACK-HEART — INDEPENDENT TELEMETRY ORACLE CERTIFICATE")
    print("=" * 65 + "\033[0m\n")
    with open(target, "rb") as f: content = f.read()
    prefix = "%🖤 ORACLE_MANIFEST: ".encode("utf-8")
    idx = content.find(prefix)
    if idx == -1:
        print("[FAIL] No ORACLE_MANIFEST block found")
        sys.exit(1)
    end_idx = content.find(b"\n", idx)
    man = json.loads(content[idx + len(prefix):end_idx].decode("utf-8"))

    # Cryptographic verification
    try:
        from crypto import verify_bytes
    except Exception:
        d = os.path.dirname(os.path.abspath(target))
        for p in (d, os.path.dirname(d), "/Users/s0fractal/Projects/black-heart"):
            if os.path.isdir(p) and p not in sys.path:
                sys.path.insert(0, p)
        from crypto import verify_bytes

    payload_data = man.get("payload", {})
    payload_bytes = json.dumps(payload_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    try:
        pk_bytes = bytes.fromhex(man["public_key_hex"])
        sig_bytes = bytes.fromhex(man["signature_hex"])
    except Exception as e:
        print(f"[FAIL] Invalid public key or signature hex: {e}")
        sys.exit(1)

    if not verify_bytes(pk_bytes, payload_bytes, sig_bytes):
        print("\033[1;31m[FAIL] RFC 8032 Signature verification FAILED! Invalid or forged telemetry.\033[0m")
        sys.exit(1)

    computed_anchor = hashlib.sha256(payload_bytes + sig_bytes).hexdigest()
    if man.get("oracle_anchor") != computed_anchor:
        print("[FAIL] Oracle anchor mismatch!")
        sys.exit(1)

    oracle_name = payload_data.get("oracle_name", man.get("oracle_name"))
    print(f"[*] Oracle:      {oracle_name} ({man.get('oracle_role', 'ORACLE')})")
    print(f"[*] Public Key:  {man['public_key_hex']}")
    print(f"[*] Signature:   {man['signature_hex'][:32]}... [RFC 8032 VERIFIED]")
    print(f"[*] Uptime Attested: {payload_data.get('measured_uptime_percent')}% across {payload_data.get('total_period_minutes')} min")
    print(f"[*] Anchor:      ⚓ ⟨digest:{computed_anchor[:16]}⟩")
    print("\033[1;36m" + "=" * 65 + "\033[0m")

if __name__ == "__main__": main()
'''

def _generate_agreement_runner() -> str:
    return r'''
# --- BILATERAL AGREEMENT STANDALONE ADJUDICATOR ---
import os, sys, json
def main():
    target = sys.argv[0]
    args = sys.argv[1:]
    print("\033[1;36m" + "=" * 70)
    print("  %🖤 BLACK-HEART — BILATERAL INTERLOCKING CONTRACT RUNNER")
    print("=" * 70 + "\033[0m\n")

    if "--adjudicate-with" in args:
        idx = args.index("--adjudicate-with")
        if idx + 1 >= len(args):
            print("\033[1;31m[!] Missing oracle PDF path!\033[0m")
            sys.exit(1)
        oracle_pdf = args[idx + 1]

        # Ensure repo in sys.path
        target_dir = os.path.dirname(os.path.abspath(target))
        parent_dir = os.path.dirname(target_dir)
        for p in (target_dir, parent_dir):
            if p not in sys.path: sys.path.insert(0, p)

        from cross_proof import adjudicate_bilateral
        try:
            rcpt = adjudicate_bilateral(target, oracle_pdf)
            print("\033[1;32m[✓ GREEN] BILATERAL CROSS-VERIFICATION SOUND & COMPLETED.\033[0m")
            print(f"  Contract:         {rcpt.agreement_title}")
            print(f"  Oracle Source:    {rcpt.oracle_name} ({rcpt.oracle_pk_hex[:16]}...)")
            print(f"  Measured Uptime:  {rcpt.measured_uptime_percent}% (Target: {rcpt.target_uptime_percent}%)")
            print(f"  Status:           \033[1;31m{rcpt.status}\033[0m" if rcpt.status == "SETTLED_BREACH" else f"  Status: \033[1;32m{rcpt.status}\033[0m")
            print(f"  Penalty Due:      \033[1;31m${rcpt.penalty_due_usd:,} USD\033[0m")
            print(f"  Net Service Due:  \033[1;32m${rcpt.net_service_due_usd:,} USD\033[0m")
            print(f"\n  Joint Bilateral Witness Anchor:")
            print(f"  \033[1;35m⚓ ⟨digest:{rcpt.joint_bilateral_digest}⟩\033[0m\n")
        except Exception as e:
            print(f"\033[1;31m[✗ REFUTED] Bilateral Adjudication Blocked: {e}\033[0m")
            sys.exit(1)
    else:
        print("[*] To adjudicate this contract against attested oracle telemetry, run:")
        print(f"    python3 {os.path.basename(target)} --adjudicate-with <telemetry_oracle.pdf>")
    print("\033[1;36m" + "=" * 70 + "\033[0m")
if __name__ == "__main__": main()
'''

if __name__ == "__main__":
    print("cross_proof.py — Bilateral Interlocking Document Protocol loaded.")
