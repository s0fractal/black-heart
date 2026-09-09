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
    CryptographicSeal,
    L
)
from cid import compute_cidv1_raw, compute_cidv1_for_file
from zk_glyph import (
    SchnorrProof,
    schnorr_prove,
    schnorr_verify,
    ChaumPedersenProof,
    chaum_pedersen_prove,
    chaum_pedersen_verify,
    GENERATOR_H,
    _scalar_mult,
    _encode_point,
    BASE_POINT
)

ORACLE_MANIFEST_PREFIX = "%🖤 ORACLE_MANIFEST: "
AGREEMENT_MANIFEST_PREFIX = "%🖤 BILATERAL_MANIFEST: "
ZK_CHALLENGER_MANIFEST_PREFIX = "%🖤 ZK_CHALLENGER_MANIFEST: "
ZK_WITNESS_MANIFEST_PREFIX = "%🖤 ZK_WITNESS_MANIFEST: "


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
    agreement_author_pk_hex: str = ""
    trust_status: str = "TRUSTED"

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
            "timestamp_utc": self.timestamp_utc,
            "agreement_author_pk_hex": self.agreement_author_pk_hex,
            "trust_status": self.trust_status,
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
            "base_fee_usd": self.base_fee_usd,
            "parties": [
                {
                    "name": p["name"],
                    "public_key_hex": p["public_key_hex"],
                    "role": p["role"],
                }
                for p in self.parties
            ],
            "penalty_rate_usd": self.penalty_rate_usd,
            "target_uptime_percent": self.target_uptime_percent,
            "title": self.title,
            "trusted_oracle_pk_hex": self.trusted_oracle_pk_hex,
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

        runner = _generate_agreement_runner(author_pk_hex=self._pk)
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
    expected_agreement_hash: Optional[str] = None,
    expected_author_pk_hex: Optional[str] = None,
) -> BilateralSettlementReceipt:
    """
    Executes bilateral adjudication between an Agreement Polyglot and an Oracle Polyglot.
    Verifies mutual Ed25519 signatures, recomputed anchors, identity constraints,
    author authenticity pin, and mandatory registered party signatures.
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

    # 2. Verify Agreement Author Signature over canonical terms (including parties roster)
    parties = ag_manifest.get("parties", [])
    terms_dict = {
        "base_fee_usd": ag_manifest["base_fee_usd"],
        "parties": [
            {
                "name": p["name"],
                "public_key_hex": p["public_key_hex"],
                "role": p["role"],
            }
            for p in parties
        ],
        "penalty_rate_usd": ag_manifest["penalty_rate_usd"],
        "target_uptime_percent": ag_manifest["target_uptime_percent"],
        "title": ag_manifest["title"],
        "trusted_oracle_pk_hex": ag_manifest["trusted_oracle_pk_hex"],
    }
    terms_bytes = json.dumps(terms_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    author_pk = ag_manifest.get("agreement_author_pk_hex")
    author_sig = ag_manifest.get("agreement_signature_hex")
    if not author_pk or not author_sig:
        raise PermissionError("Agreement is missing cryptographic signature! Untrusted agreement.")

    if expected_author_pk_hex is not None:
        if author_pk != expected_author_pk_hex:
            raise PermissionError(f"Agreement author PK mismatch: expected {expected_author_pk_hex}, got {author_pk}")

    if not verify_bytes(bytes.fromhex(author_pk), terms_bytes, bytes.fromhex(author_sig)):
        raise PermissionError("Agreement terms altered or signature invalid! Refusing unverified agreement.")

    # 3. Mandatory verification of all registered party signatures
    for party in parties:
        sig_hex = party.get("signature_hex")
        if not sig_hex:
            raise PermissionError(f"Missing required signature for registered party '{party.get('name')}' ({party.get('role')})!")
        pk = bytes.fromhex(party["public_key_hex"])
        sig = bytes.fromhex(sig_hex)
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

    trust_status = "AUTHENTICATED_PINNED" if (expected_agreement_hash or expected_author_pk_hex) else "UNTRUSTED_ISSUER_EVALUATION"

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
        timestamp_utc=ts,
        agreement_author_pk_hex=author_pk,
        trust_status=trust_status,
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

def _generate_agreement_runner(author_pk_hex: str = "") -> str:
    return f'''
# --- BILATERAL AGREEMENT STANDALONE ADJUDICATOR ---
import os, sys, json

PINNED_AUTHOR_PK = "{author_pk_hex}"

def main():
    target = sys.argv[0]
    args = sys.argv[1:]
    print("\\033[1;36m" + "=" * 70)
    print("  %🖤 BLACK-HEART — BILATERAL INTERLOCKING CONTRACT RUNNER")
    print("=" * 70 + "\\033[0m\\n")

    if "--adjudicate-with" in args:
        idx = args.index("--adjudicate-with")
        if idx + 1 >= len(args):
            print("\\033[1;31m[!] Missing oracle PDF path!\\033[0m")
            sys.exit(1)
        oracle_pdf = args[idx + 1]

        # Ensure repo in sys.path
        target_dir = os.path.dirname(os.path.abspath(target))
        parent_dir = os.path.dirname(target_dir)
        for p in (target_dir, parent_dir):
            if p not in sys.path: sys.path.insert(0, p)

        from cross_proof import adjudicate_bilateral
        try:
            rcpt = adjudicate_bilateral(target, oracle_pdf, expected_author_pk_hex=PINNED_AUTHOR_PK or None)
            print("\\033[1;32m[✓ GREEN] BILATERAL CROSS-VERIFICATION SOUND & COMPLETED.\\033[0m")
            print(f"  Contract:         {{rcpt.agreement_title}}")
            print(f"  Trust Status:     {{rcpt.trust_status}}")
            print(f"  Author PK:        {{rcpt.agreement_author_pk_hex[:16]}}...")
            print(f"  Oracle Source:    {{rcpt.oracle_name}} ({{rcpt.oracle_pk_hex[:16]}}...)")
            print(f"  Measured Uptime:  {{rcpt.measured_uptime_percent}}% (Target: {{rcpt.target_uptime_percent}}%)")
            print(f"  Status:           \\033[1;31m{{rcpt.status}}\\033[0m" if rcpt.status == "SETTLED_BREACH" else f"  Status: \\033[1;32m{{rcpt.status}}\\033[0m")
            print(f"  Penalty Due:      \\033[1;31m${{rcpt.penalty_due_usd:,}} USD\\033[0m")
            print(f"  Net Service Due:  \\033[1;32m${{rcpt.net_service_due_usd:,}} USD\\033[0m")
            print(f"\\n  Joint Bilateral Witness Anchor:")
            print(f"  \\033[1;35m⚓ ⟨digest:{{rcpt.joint_bilateral_digest}}⟩\\033[0m\\n")
        except Exception as e:
            print(f"\\033[1;31m[✗ REFUTED] Bilateral Adjudication Blocked: {{e}}\\033[0m")
            sys.exit(1)
    else:
        print("[*] To adjudicate this contract against attested oracle telemetry, run:")
        print(f"    python3 {{os.path.basename(target)}} --adjudicate-with <telemetry_oracle.pdf>")
    print("\\033[1;36m" + "=" * 70 + "\\033[0m")
if __name__ == "__main__": main()
'''

def audit_agreement_polyglot(target_path: str) -> bool:
    """Verifies a Bilateral Agreement Polyglot as static data without executing code."""
    try:
        with open(target_path, "rb") as f:
            content = f.read()
        prefix = AGREEMENT_MANIFEST_PREFIX.encode("utf-8")
        idx = content.find(prefix)
        if idx == -1:
            return False
        end = content.find(b"\n", idx)
        man = json.loads(content[idx + len(prefix):end].decode("utf-8"))

        author_pk = man.get("agreement_author_pk_hex")
        author_sig = man.get("agreement_signature_hex")
        if not author_pk or not author_sig:
            return False

        parties = man.get("parties", [])
        terms_dict = {
            "base_fee_usd": man["base_fee_usd"],
            "parties": [
                {
                    "name": p["name"],
                    "public_key_hex": p["public_key_hex"],
                    "role": p["role"],
                }
                for p in parties
            ],
            "penalty_rate_usd": man["penalty_rate_usd"],
            "target_uptime_percent": man["target_uptime_percent"],
            "title": man["title"],
            "trusted_oracle_pk_hex": man["trusted_oracle_pk_hex"],
        }
        terms_bytes = json.dumps(terms_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        if not verify_bytes(bytes.fromhex(author_pk), terms_bytes, bytes.fromhex(author_sig)):
            return False

        for p in parties:
            if "signature_hex" in p:
                if not verify_bytes(bytes.fromhex(p["public_key_hex"]), terms_bytes, bytes.fromhex(p["signature_hex"])):
                    return False
        return True
    except Exception:
        return False

def audit_oracle_polyglot(target_path: str) -> bool:
    """Verifies a Telemetry Oracle Polyglot as static data without executing code."""
    try:
        with open(target_path, "rb") as f:
            content = f.read()
        prefix = ORACLE_MANIFEST_PREFIX.encode("utf-8")
        idx = content.find(prefix)
        if idx == -1:
            return False
        end = content.find(b"\n", idx)
        man = json.loads(content[idx + len(prefix):end].decode("utf-8"))

        payload_data = man.get("payload", {})
        payload_bytes = json.dumps(payload_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        pk_bytes = bytes.fromhex(man["public_key_hex"])
        sig_bytes = bytes.fromhex(man["signature_hex"])
        if not verify_bytes(pk_bytes, payload_bytes, sig_bytes):
            return False

        computed_or_anchor = hashlib.sha256(payload_bytes + sig_bytes).hexdigest()
        if man.get("oracle_anchor") != computed_or_anchor:
            return False
        return True
    except Exception:
        return False

# ============================================================================
# 5. BILATERAL ZERO-KNOWLEDGE CROSS-PROOF PROTOCOL (GROK EXP 4)
# ============================================================================

@dataclass
class BilateralZKSettlementReceipt:
    """
    Joint cryptographic settlement receipt for two independent interlocking documents
    authenticated via zero-knowledge proof without exposing private keys.
    """
    status: str                         # "ZK_SETTLED_SOUND" or "ZK_VERIFICATION_FAILED"
    statement_id: str                   # Unique statement / clause identifier
    challenger_title: str               # Title of Challenger Contract
    target_prover_pk_hex: str           # Target public key bound in contract
    challenger_cid: str                 # CIDv1 of Challenger PDF
    witness_cid: str                    # CIDv1 of Witness PDF
    proof_type: str                     # "SchnorrZKP" or "ChaumPedersenZKP"
    joint_bilateral_anchor: str         # SHA-256(cid_c || cid_w || proof || status)
    timestamp_utc: str
    details: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "statement_id": self.statement_id,
            "challenger_title": self.challenger_title,
            "target_prover_pk_hex": self.target_prover_pk_hex,
            "challenger_cid": self.challenger_cid,
            "witness_cid": self.witness_cid,
            "proof_type": self.proof_type,
            "joint_bilateral_anchor": self.joint_bilateral_anchor,
            "timestamp_utc": self.timestamp_utc,
            "details": self.details,
        }

def _generate_zk_cross_runner() -> str:
    return r'''
# --- ZERO-KNOWLEDGE BILATERAL CROSS-PROOF STANDALONE RUNNER ---
import os, sys, json

def main():
    target = sys.argv[0]
    args = sys.argv[1:]
    print("\033[1;36m" + "=" * 70)
    print("  %🖤 BLACK-HEART — ZERO-KNOWLEDGE BILATERAL CROSS-PROOF RUNNER")
    print("=" * 70 + "\033[0m\n")

    if "--cross-prove" in args or "--cross-prove-zk" in args:
        flag = "--cross-prove" if "--cross-prove" in args else "--cross-prove-zk"
        idx = args.index(flag)
        if idx + 1 >= len(args):
            print("\033[1;31m[!] Missing counterpart PDF path!\033[0m")
            sys.exit(1)
        other_pdf = args[idx + 1]

        target_dir = os.path.dirname(os.path.abspath(target))
        parent_dir = os.path.dirname(target_dir)
        for p in (target_dir, parent_dir, "/Users/s0fractal/Projects/black-heart"):
            if os.path.isdir(p) and p not in sys.path:
                sys.path.insert(0, p)

        from cross_proof import adjudicate_zk_bilateral, ZK_CHALLENGER_MANIFEST_PREFIX
        try:
            with open(target, "rb") as f:
                t_bytes = f.read()
            if ZK_CHALLENGER_MANIFEST_PREFIX.encode("utf-8") in t_bytes:
                challenger_pdf, witness_pdf = target, other_pdf
            else:
                challenger_pdf, witness_pdf = other_pdf, target

            rcpt = adjudicate_zk_bilateral(challenger_pdf, witness_pdf)
            print("\033[1;32m[✓ GREEN] ZERO-KNOWLEDGE BILATERAL SETTLEMENT SOUND & RATIFIED!\033[0m")
            print(f"  Status:             \033[1;32m{rcpt.status}\033[0m")
            print(f"  Statement ID:       {rcpt.statement_id}")
            print(f"  Contract Title:     {rcpt.challenger_title}")
            print(f"  Prover Public Key:  {rcpt.target_prover_pk_hex[:16]}... (ZK Verified)")
            print(f"  Challenger CIDv1:   {rcpt.challenger_cid}")
            print(f"  Witness CIDv1:      {rcpt.witness_cid}")
            print(f"  Proof System:       {rcpt.proof_type}")
            print(f"\n  Joint Merkle Bilateral Settlement Anchor:")
            print(f"  \033[1;35m⚓ ⟨digest:{rcpt.joint_bilateral_anchor}⟩\033[0m\n")
        except Exception as e:
            print(f"\033[1;31m[✗ REFUTED] Bilateral ZK Cross-Proof Failed: {e}\033[0m")
            sys.exit(1)
    else:
        print("[*] To cross-prove this document against its counterpart, execute:")
        print(f"    python3 {os.path.basename(target)} --cross-prove <counterpart.pdf>\n")
    print("\033[1;36m" + "=" * 70 + "\033[0m")

if __name__ == "__main__":
    main()
'''

class BilateralZKChallengerPolyglot:
    """
    Compiles Document A: A contractual challenge demanding a Non-Interactive
    Zero-Knowledge Proof (NIZK) for a specific public key or discrete log relation.
    """
    def __init__(
        self,
        title: str,
        statement_id: str,
        target_prover_pk_hex: str,
        clause_text: str = "Settlement authorized upon verifiable zero-knowledge proof of sovereign key possession.",
        proof_type: str = "SchnorrZKP",
        second_point_hex: Optional[str] = None,
        author_secret_key_hex: Optional[str] = None
    ):
        self.title = title
        self.statement_id = statement_id
        self.target_prover_pk_hex = target_prover_pk_hex
        self.clause_text = clause_text
        self.proof_type = proof_type
        self.second_point_hex = second_point_hex or ""
        if author_secret_key_hex:
            self._sk = author_secret_key_hex
            self._pk = public_key_from_secret(bytes.fromhex(author_secret_key_hex)).hex()
        else:
            self._sk, self._pk = generate_keypair()

    def canonical_claim_bytes(self) -> bytes:
        claim = {
            "clause_text": self.clause_text,
            "proof_type": self.proof_type,
            "second_point_hex": self.second_point_hex,
            "statement_id": self.statement_id,
            "target_prover_pk_hex": self.target_prover_pk_hex,
            "title": self.title
        }
        return json.dumps(claim, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def compile(self, output_path: str) -> str:
        claim_b = self.canonical_claim_bytes()
        author_sig = sign_bytes(bytes.fromhex(self._sk), claim_b).hex()

        manifest_dict = {
            "title": self.title,
            "statement_id": self.statement_id,
            "target_prover_pk_hex": self.target_prover_pk_hex,
            "proof_type": self.proof_type,
            "second_point_hex": self.second_point_hex,
            "clause_text": self.clause_text,
            "author_pk_hex": self._pk,
            "author_signature_hex": author_sig,
            "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        manifest_str = json.dumps(manifest_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        manifest_comment = f"{ZK_CHALLENGER_MANIFEST_PREFIX}{manifest_str}\n".encode("utf-8")

        # Visual PDF Stream
        page_width, page_height = 595, 842
        margin = 50
        y = page_height - margin

        stream_lines = [
            "q",
            # Dark Indigo Space
            "0.03 0.05 0.12 rg",
            f"0 0 {page_width} {page_height} re f",
            # Outer Cyan Border
            "0.15 0.75 0.95 RG 1.5 w",
            f"{margin - 15} {margin - 15} {page_width - 2*(margin - 15)} {page_height - 2*(margin - 15)} re S",
            # Header Box
            "0.06 0.10 0.20 rg",
            f"{margin} {y - 65} {page_width - 2*margin} 65 re f",
            "0.15 0.75 0.95 RG 1.0 w",
            f"{margin} {y - 65} {page_width - 2*margin} 65 re S",
            "1.0 1.0 1.0 rg",
            f"BT /F1 14 Tf {margin + 15} {y - 25} Td (PROJECT BLACK-HEART // BILATERAL ZK CHALLENGE) Tj ET",
            "0.2 0.85 1.0 rg",
            f"BT /F2 9 Tf {margin + 15} {y - 45} Td (STATEMENT: {_escape_pdf(self.statement_id)}  |  TYPE: {_escape_pdf(self.proof_type)}) Tj ET",
        ]
        y -= 85

        # Contract Terms Box
        box_h = 240
        stream_lines.extend([
            "0.05 0.08 0.16 rg",
            f"{margin} {y - box_h} {page_width - 2*margin} {box_h} re f",
            "0.20 0.55 0.80 RG 1.0 w",
            f"{margin} {y - box_h} {page_width - 2*margin} {box_h} re S",
            "1.0 1.0 1.0 rg",
            f"BT /F1 11 Tf {margin + 15} {y - 25} Td (CONTRACT TITLE: {_escape_pdf(self.title[:55])}) Tj ET",
            "0.75 0.85 0.95 rg",
            f"BT /F3 9 Tf {margin + 15} {y - 50} Td (Clause: {_escape_pdf(self.clause_text[:75])}) Tj ET",
            "0.85 0.70 0.20 rg",
            f"BT /F2 9 Tf {margin + 15} {y - 80} Td (Target Prover Public Key:) Tj ET",
            "1.0 1.0 1.0 rg",
            f"BT /F2 8 Tf {margin + 15} {y - 95} Td ({self.target_prover_pk_hex}) Tj ET",
        ])

        if self.second_point_hex:
            stream_lines.extend([
                "0.85 0.70 0.20 rg",
                f"BT /F2 9 Tf {margin + 15} {y - 120} Td (Second Generator Point H:) Tj ET",
                "1.0 1.0 1.0 rg",
                f"BT /F2 8 Tf {margin + 15} {y - 135} Td ({self.second_point_hex}) Tj ET",
            ])

        stream_lines.extend([
            "0.40 0.80 1.0 rg",
            f"BT /F2 9 Tf {margin + 15} {y - 165} Td (Author Ed25519 Identity:) Tj ET",
            "0.9 0.9 0.9 rg",
            f"BT /F2 8 Tf {margin + 15} {y - 180} Td ({self._pk}) Tj ET",
            "0.2 0.85 1.0 rg",
            f"BT /F2 8 Tf {margin + 15} {y - 205} Td (Execution: python3 <this_file>.pdf --cross-prove <witness.pdf>) Tj ET",
        ])
        y -= (box_h + 30)

        # Adjudication Instructions Box
        inst_h = 160
        stream_lines.extend([
            "0.04 0.06 0.12 rg",
            f"{margin} {y - inst_h} {page_width - 2*margin} {inst_h} re f",
            "0.15 0.65 0.85 RG 1.0 w",
            f"{margin} {y - inst_h} {page_width - 2*margin} {inst_h} re S",
            "1.0 1.0 1.0 rg",
            f"BT /F1 10 Tf {margin + 15} {y - 25} Td (ZERO-KNOWLEDGE ADJUDICATION PROTOCOL) Tj ET",
            "0.80 0.88 0.95 rg",
            f"BT /F3 8 Tf {margin + 15} {y - 50} Td (1. The witness document proves knowledge of the private scalar without revealing it.) Tj ET",
            f"BT /F3 8 Tf {margin + 15} {y - 70} Td (2. The proof is mathematically bound to this document's exact IPFS CIDv1.) Tj ET",
            f"BT /F3 8 Tf {margin + 15} {y - 90} Td (3. Any modification to either PDF breaks the content-addressed challenge context.) Tj ET",
            f"BT /F3 8 Tf {margin + 15} {y - 110} Td (4. Mutual settlement emits a joint Merkle witness anchor valid only if both exist.) Tj ET",
            "Q"
        ])

        stream_content = "\n".join(stream_lines).encode("utf-8")

        objs = [
            b"<</Type /Catalog /Pages 2 0 R>>",
            b"<</Type /Pages /Kids [3 0 R] /Count 1>>",
            (
                b"<</Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                b"/Contents 4 0 R /Resources <</Font <</F1 5 0 R /F2 6 0 R /F3 7 0 R>>>>>>"
            ),
            f"<</Length {len(stream_content)}>>\nstream\n".encode("latin1") + stream_content + b"\nendstream",
            b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold>>",
            b"<</Type /Font /Subtype /Type1 /BaseFont /Courier-Bold>>",
            b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>",
        ]

        pdf_header = b"# coding: utf-8\nr\"\"\"%PDF-1.7\n%\xe2\x9a\x93\n"
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
        body.extend(_generate_zk_cross_runner().encode("utf-8"))

        with open(output_path, "wb") as f:
            f.write(body)
        return output_path


class BilateralZKWitnessPolyglot:
    """
    Compiles Document B: An independent witness containing a Zero-Knowledge Proof
    (Schnorr or Chaum-Pedersen) mathematically bound to Document A's exact CIDv1.
    """
    def __init__(
        self,
        witness_name: str,
        challenger_pdf_path: str,
        prover_secret_key_hex: Optional[str] = None,
        prover_secret_scalar: Optional[int] = None,
        witness_author_secret_key_hex: Optional[str] = None
    ):
        self.witness_name = witness_name
        self.challenger_pdf_path = challenger_pdf_path
        self.prover_secret_key_hex = prover_secret_key_hex
        self.prover_secret_scalar = prover_secret_scalar
        if witness_author_secret_key_hex:
            self._sk = witness_author_secret_key_hex
            self._pk = public_key_from_secret(bytes.fromhex(witness_author_secret_key_hex)).hex()
        else:
            self._sk, self._pk = generate_keypair()

    def compile(self, output_path: str) -> str:
        with open(self.challenger_pdf_path, "rb") as f:
            c_bytes = f.read()
        challenger_cid = compute_cidv1_raw(c_bytes)

        prefix = ZK_CHALLENGER_MANIFEST_PREFIX.encode("utf-8")
        idx = c_bytes.rfind(prefix)
        if idx == -1:
            raise ValueError(f"No ZK_CHALLENGER_MANIFEST in '{self.challenger_pdf_path}'")
        end = c_bytes.find(b"\n", idx)
        c_manifest = json.loads(c_bytes[idx + len(prefix):end].decode("utf-8"))

        statement_id = c_manifest["statement_id"]
        proof_type = c_manifest["proof_type"]
        context = f"ZK_CROSS_PROOF:{challenger_cid}:{statement_id}"

        if proof_type == "SchnorrZKP":
            if not self.prover_secret_key_hex:
                raise ValueError("prover_secret_key_hex required for SchnorrZKP")
            zk_proof = schnorr_prove(self.prover_secret_key_hex, context=context)
            proof_dict = zk_proof.to_dict()
        elif proof_type == "ChaumPedersenZKP":
            scalar = self.prover_secret_scalar
            if scalar is None and self.prover_secret_key_hex:
                h = hashlib.sha512(bytes.fromhex(self.prover_secret_key_hex)).digest()
                scalar = int.from_bytes(h[:32], "little")
                scalar &= (1 << 254) - 8
                scalar |= (1 << 254)
                scalar %= L
            if scalar is None:
                raise ValueError("prover_secret_scalar required for ChaumPedersenZKP")
            zk_proof = chaum_pedersen_prove(scalar, context=context)
            proof_dict = zk_proof.to_dict()
        else:
            raise ValueError(f"Unknown proof type: {proof_type}")

        # Sign witness payload
        witness_payload = {
            "challenger_cid": challenger_cid,
            "proof": proof_dict,
            "statement_id": statement_id,
            "witness_name": self.witness_name
        }
        payload_b = json.dumps(witness_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        witness_sig = sign_bytes(bytes.fromhex(self._sk), payload_b).hex()

        manifest_dict = {
            "witness_name": self.witness_name,
            "challenger_cid": challenger_cid,
            "statement_id": statement_id,
            "proof": proof_dict,
            "witness_pk_hex": self._pk,
            "witness_signature_hex": witness_sig,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        manifest_str = json.dumps(manifest_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        manifest_comment = f"{ZK_WITNESS_MANIFEST_PREFIX}{manifest_str}\n".encode("utf-8")

        # Visual PDF Stream
        page_width, page_height = 595, 842
        margin = 50
        y = page_height - margin

        stream_lines = [
            "q",
            # Dark Amber / Obsidian Background
            "0.05 0.04 0.08 rg",
            f"0 0 {page_width} {page_height} re f",
            # Outer Gold Border
            "0.95 0.75 0.15 RG 1.5 w",
            f"{margin - 15} {margin - 15} {page_width - 2*(margin - 15)} {page_height - 2*(margin - 15)} re S",
            # Header Box
            "0.12 0.08 0.16 rg",
            f"{margin} {y - 65} {page_width - 2*margin} 65 re f",
            "0.95 0.75 0.15 RG 1.0 w",
            f"{margin} {y - 65} {page_width - 2*margin} 65 re S",
            "1.0 1.0 1.0 rg",
            f"BT /F1 14 Tf {margin + 15} {y - 25} Td (PROJECT BLACK-HEART // BILATERAL ZK WITNESS) Tj ET",
            "0.95 0.80 0.25 rg",
            f"BT /F2 9 Tf {margin + 15} {y - 45} Td (WITNESS: {_escape_pdf(self.witness_name)}  |  STATEMENT: {_escape_pdf(statement_id)}) Tj ET",
        ]
        y -= 85

        # Proof Data Box
        box_h = 240
        stream_lines.extend([
            "0.08 0.06 0.12 rg",
            f"{margin} {y - box_h} {page_width - 2*margin} {box_h} re f",
            "0.70 0.55 0.20 RG 1.0 w",
            f"{margin} {y - box_h} {page_width - 2*margin} {box_h} re S",
            "1.0 1.0 1.0 rg",
            f"BT /F1 11 Tf {margin + 15} {y - 25} Td (BOUND CONTRACT CIDv1 MERKLE TARGET:) Tj ET",
            "0.2 0.85 1.0 rg",
            f"BT /F2 8 Tf {margin + 15} {y - 42} Td ({challenger_cid}) Tj ET",
            "0.95 0.75 0.15 rg",
            f"BT /F2 9 Tf {margin + 15} {y - 70} Td (Commitment Nonce R:) Tj ET",
            "1.0 1.0 1.0 rg",
            f"BT /F2 8 Tf {margin + 15} {y - 85} Td ({proof_dict.get('commitment_R_hex', proof_dict.get('commitment_R1_hex', ''))}) Tj ET",
            "0.95 0.75 0.15 rg",
            f"BT /F2 9 Tf {margin + 15} {y - 110} Td (Response Scalar z:) Tj ET",
            "1.0 1.0 1.0 rg",
            f"BT /F2 8 Tf {margin + 15} {y - 125} Td ({proof_dict.get('response_z_hex', '')}) Tj ET",
            "0.85 0.85 0.85 rg",
            f"BT /F2 9 Tf {margin + 15} {y - 150} Td (Prover Public Key P:) Tj ET",
            "1.0 1.0 1.0 rg",
            f"BT /F2 8 Tf {margin + 15} {y - 165} Td ({proof_dict.get('prover_pk_hex', proof_dict.get('point_P1_hex', ''))}) Tj ET",
            "0.20 0.85 1.0 rg",
            f"BT /F2 8 Tf {margin + 15} {y - 205} Td (Execution: python3 <this_file>.pdf --cross-prove <challenger.pdf>) Tj ET",
        ])
        y -= (box_h + 30)

        # Verification Guarantee Box
        inst_h = 160
        stream_lines.extend([
            "0.06 0.05 0.10 rg",
            f"{margin} {y - inst_h} {page_width - 2*margin} {inst_h} re f",
            "0.70 0.50 0.15 RG 1.0 w",
            f"{margin} {y - inst_h} {page_width - 2*margin} {inst_h} re S",
            "1.0 1.0 1.0 rg",
            f"BT /F1 10 Tf {margin + 15} {y - 25} Td (ZERO-KNOWLEDGE NON-DISCLOSURE GUARANTEE) Tj ET",
            "0.90 0.85 0.75 rg",
            f"BT /F3 8 Tf {margin + 15} {y - 50} Td (1. The secret scalar s is never written or leaked into this document.) Tj ET",
            f"BT /F3 8 Tf {margin + 15} {y - 70} Td (2. The proof z is valid strictly under the challenger's unique content address.) Tj ET",
            f"BT /F3 8 Tf {margin + 15} {y - 90} Td (3. Any change in challenger bytes invalidates this proof completely.) Tj ET",
            f"BT /F3 8 Tf {margin + 15} {y - 110} Td (4. Dual-document cross-proving completes in 100% pure standard library Python.) Tj ET",
            "Q"
        ])

        stream_content = "\n".join(stream_lines).encode("utf-8")

        objs = [
            b"<</Type /Catalog /Pages 2 0 R>>",
            b"<</Type /Pages /Kids [3 0 R] /Count 1>>",
            (
                b"<</Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                b"/Contents 4 0 R /Resources <</Font <</F1 5 0 R /F2 6 0 R /F3 7 0 R>>>>>>"
            ),
            f"<</Length {len(stream_content)}>>\nstream\n".encode("latin1") + stream_content + b"\nendstream",
            b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold>>",
            b"<</Type /Font /Subtype /Type1 /BaseFont /Courier-Bold>>",
            b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>",
        ]

        pdf_header = b"# coding: utf-8\nr\"\"\"%PDF-1.7\n%\xe2\x9a\x93\n"
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
        body.extend(_generate_zk_cross_runner().encode("utf-8"))

        with open(output_path, "wb") as f:
            f.write(body)
        return output_path


def adjudicate_zk_bilateral(
    challenger_pdf_path: str,
    witness_pdf_path: str
) -> BilateralZKSettlementReceipt:
    """
    Executes bilateral zero-knowledge cross-proof adjudication between Document A
    and Document B without exposing private keys. Strictly fail-closed.
    """
    if not os.path.exists(challenger_pdf_path):
        raise FileNotFoundError(f"Challenger file not found: {challenger_pdf_path}")
    if not os.path.exists(witness_pdf_path):
        raise FileNotFoundError(f"Witness file not found: {witness_pdf_path}")

    with open(challenger_pdf_path, "rb") as f:
        c_bytes = f.read()
    with open(witness_pdf_path, "rb") as f:
        w_bytes = f.read()

    cid_c = compute_cidv1_raw(c_bytes)
    cid_w = compute_cidv1_raw(w_bytes)

    # 1. Extract and verify Challenger Manifest
    c_prefix = ZK_CHALLENGER_MANIFEST_PREFIX.encode("utf-8")
    c_idx = c_bytes.rfind(c_prefix)
    if c_idx == -1:
        raise PermissionError(f"No ZK_CHALLENGER_MANIFEST found in '{challenger_pdf_path}'")
    c_end = c_bytes.find(b"\n", c_idx)
    c_manifest = json.loads(c_bytes[c_idx + len(c_prefix):c_end].decode("utf-8"))

    c_claim_bytes = json.dumps({
        "clause_text": c_manifest["clause_text"],
        "proof_type": c_manifest["proof_type"],
        "second_point_hex": c_manifest.get("second_point_hex", ""),
        "statement_id": c_manifest["statement_id"],
        "target_prover_pk_hex": c_manifest["target_prover_pk_hex"],
        "title": c_manifest["title"]
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    if not verify_bytes(bytes.fromhex(c_manifest["author_pk_hex"]), c_claim_bytes, bytes.fromhex(c_manifest["author_signature_hex"])):
        raise PermissionError("Challenger contract author signature is invalid or tampered!")

    # 2. Extract and verify Witness Manifest
    w_prefix = ZK_WITNESS_MANIFEST_PREFIX.encode("utf-8")
    w_idx = w_bytes.rfind(w_prefix)
    if w_idx == -1:
        raise PermissionError(f"No ZK_WITNESS_MANIFEST found in '{witness_pdf_path}'")
    w_end = w_bytes.find(b"\n", w_idx)
    w_manifest = json.loads(w_bytes[w_idx + len(w_prefix):w_end].decode("utf-8"))

    w_payload_bytes = json.dumps({
        "challenger_cid": w_manifest["challenger_cid"],
        "proof": w_manifest["proof"],
        "statement_id": w_manifest["statement_id"],
        "witness_name": w_manifest["witness_name"]
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    if not verify_bytes(bytes.fromhex(w_manifest["witness_pk_hex"]), w_payload_bytes, bytes.fromhex(w_manifest["witness_signature_hex"])):
        raise PermissionError("Witness author signature is invalid or tampered!")

    # 3. Content-Address Binding Assertion (FAIL-CLOSED)
    if w_manifest["challenger_cid"] != cid_c:
        raise PermissionError(
            f"Bilateral CID mismatch: witness is bound to CID '{w_manifest['challenger_cid']}', "
            f"but provided contract CID is '{cid_c}'. Replay attack rejected!"
        )

    if w_manifest["statement_id"] != c_manifest["statement_id"]:
        raise PermissionError(
            f"Statement ID mismatch: contract specifies '{c_manifest['statement_id']}', "
            f"witness answers '{w_manifest['statement_id']}'"
        )

    # 4. Verify Zero-Knowledge Proof
    expected_context = f"ZK_CROSS_PROOF:{cid_c}:{c_manifest['statement_id']}"
    req_proof_type = c_manifest.get("proof_type", "SchnorrZKP")
    proof_dict = w_manifest.get("proof", {})
    proof_type = proof_dict.get("type")

    # Fail-closed: witness must strictly provide the exact proof type requested by contract
    if proof_type != req_proof_type:
        raise PermissionError(
            f"Proof type mismatch: contract requires '{req_proof_type}', "
            f"but witness provided '{proof_type}'"
        )

    if proof_type == "SchnorrZKP":
        proof = SchnorrProof.from_dict(proof_dict)
        if proof.context != expected_context:
            raise PermissionError("Witness Schnorr proof context does not match expected bilateral context!")
        if proof.prover_pk_hex.lower() != c_manifest["target_prover_pk_hex"].lower():
            raise PermissionError(
                f"Prover public key mismatch: expected '{c_manifest['target_prover_pk_hex']}', "
                f"witness proved for '{proof.prover_pk_hex}'"
            )
        if not schnorr_verify(proof):
            raise PermissionError("Schnorr zero-knowledge proof mathematical verification failed!")
        proof_fingerprint = f"{proof.commitment_R_hex}:{proof.response_z_hex}"

    elif proof_type == "ChaumPedersenZKP":
        proof = ChaumPedersenProof.from_dict(proof_dict)
        if proof.context != expected_context:
            raise PermissionError("Witness Chaum-Pedersen proof context does not match expected bilateral context!")
        if proof.point_P1_hex.lower() != c_manifest["target_prover_pk_hex"].lower():
            raise PermissionError("Prover point P1 mismatch with target public key!")
        expected_p2 = c_manifest.get("second_point_hex")
        if expected_p2:
            if not proof.point_P2_hex or proof.point_P2_hex.lower() != expected_p2.lower():
                raise PermissionError(
                    f"Prover point P2 mismatch: contract requires '{expected_p2}', "
                    f"witness provided '{proof.point_P2_hex}'"
                )
        if not chaum_pedersen_verify(proof):
            raise PermissionError("Chaum-Pedersen discrete log equality proof verification failed!")
        proof_fingerprint = f"{proof.commitment_R1_hex}:{proof.commitment_R2_hex}:{proof.response_z_hex}"
    else:
        raise PermissionError(f"Unsupported proof type: '{proof_type}'")

    # 5. Joint Bilateral Anchor
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    joint_data = f"{cid_c}|{cid_w}|{proof_fingerprint}|ZK_SETTLED_SOUND|{ts}".encode("utf-8")
    joint_anchor = hashlib.sha256(joint_data).hexdigest()

    return BilateralZKSettlementReceipt(
        status="ZK_SETTLED_SOUND",
        statement_id=c_manifest["statement_id"],
        challenger_title=c_manifest["title"],
        target_prover_pk_hex=c_manifest["target_prover_pk_hex"],
        challenger_cid=cid_c,
        witness_cid=cid_w,
        proof_type=proof_type,
        joint_bilateral_anchor=joint_anchor,
        timestamp_utc=ts,
        details="Non-interactive zero-knowledge bilateral settlement mathematically verified & sound."
    )

def audit_zk_challenger_polyglot(target_path: str) -> bool:
    """Verifies a ZK Challenger polyglot statically without execution."""
    try:
        with open(target_path, "rb") as f:
            c_bytes = f.read()
        prefix = ZK_CHALLENGER_MANIFEST_PREFIX.encode("utf-8")
        idx = c_bytes.rfind(prefix)
        if idx == -1:
            return False
        end = c_bytes.find(b"\n", idx)
        c_manifest = json.loads(c_bytes[idx + len(prefix):end].decode("utf-8"))
        c_claim_bytes = json.dumps({
            "clause_text": c_manifest["clause_text"],
            "proof_type": c_manifest["proof_type"],
            "second_point_hex": c_manifest.get("second_point_hex", ""),
            "statement_id": c_manifest["statement_id"],
            "target_prover_pk_hex": c_manifest["target_prover_pk_hex"],
            "title": c_manifest["title"]
        }, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return verify_bytes(bytes.fromhex(c_manifest["author_pk_hex"]), c_claim_bytes, bytes.fromhex(c_manifest["author_signature_hex"]))
    except Exception:
        return False

def audit_zk_witness_polyglot(target_path: str) -> bool:
    """Verifies a ZK Witness polyglot statically without execution."""
    try:
        with open(target_path, "rb") as f:
            w_bytes = f.read()
        prefix = ZK_WITNESS_MANIFEST_PREFIX.encode("utf-8")
        idx = w_bytes.rfind(prefix)
        if idx == -1:
            return False
        end = w_bytes.find(b"\n", idx)
        w_manifest = json.loads(w_bytes[idx + len(prefix):end].decode("utf-8"))
        w_payload_bytes = json.dumps({
            "challenger_cid": w_manifest["challenger_cid"],
            "proof": w_manifest["proof"],
            "statement_id": w_manifest["statement_id"],
            "witness_name": w_manifest["witness_name"]
        }, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return verify_bytes(bytes.fromhex(w_manifest["witness_pk_hex"]), w_payload_bytes, bytes.fromhex(w_manifest["witness_signature_hex"]))
    except Exception:
        return False

if __name__ == "__main__":
    print("cross_proof.py — Bilateral Interlocking Document Protocol loaded.")

