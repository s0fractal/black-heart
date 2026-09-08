#!/usr/bin/env python3
"""
crypto.py — Zero-Dependency Pure-Python Ed25519 (RFC 8032) Cryptographic Engine.
Part of Project Black-Heart (%🖤).

Features:
  - 100% pure standard library Python (uses only hashlib.sha512 and os.urandom).
  - No external C or pip dependencies (no nacl, no cryptography).
  - Full Twisted Edwards curve arithmetic over GF(2^255 - 19).
  - Keypair generation, message signing, and signature verification.
  - CryptographicSeal dataclass for content-addressed proof-carrying documents.
"""

from __future__ import annotations
import os
import sys
import json
import time
import hashlib
from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Any

# ============================================================================
# ED25519 CONSTANTS (RFC 8032 §5.1)
# ============================================================================

# Prime field modulus: 2^255 - 19
Q = 2**255 - 19

# Order of the base point
L = 2**252 + 27742317777372353535851937790883648493

def _inv(x: int) -> int:
    """Modular inverse via Fermat's Little Theorem."""
    return pow(x, Q - 2, Q)

# Curve parameter d = -121665 / 121666 mod Q
D = (-121665 * _inv(121666)) % Q

# Square root of -1 modulo Q
SQRT_M1 = pow(2, (Q - 1) // 4, Q)

def _x_recover(y: int) -> int:
    """Recover x coordinate from y coordinate."""
    xx = (y * y - 1) * _inv(D * y * y + 1)
    x = pow(xx, (Q + 3) // 8, Q)
    if (x * x - xx) % Q != 0:
        x = (x * SQRT_M1) % Q
    if x % 2 != 0:
        x = Q - x
    return x

# Base point B = (Bx, By) where By = 4/5 mod Q
BY = (4 * _inv(5)) % Q
BX = _x_recover(BY)
BASE_POINT = (BX, BY)

# ============================================================================
# CURVE ARITHMETIC
# ============================================================================

Point = Tuple[int, int]

def _edwards_add(P: Point, Q_pt: Point) -> Point:
    """Add two points on the twisted Edwards curve."""
    x1, y1 = P
    x2, y2 = Q_pt
    x3 = (x1 * y2 + x2 * y1) * _inv(1 + D * x1 * x2 * y1 * y2) % Q
    y3 = (y1 * y2 + x1 * x2) * _inv(1 - D * x1 * x2 * y1 * y2) % Q
    return (x3, y3)

def _scalar_mult(P: Point, e: int) -> Point:
    """Scalar multiplication e * P via double-and-add."""
    if e == 0:
        return (0, 1)
    Q_pt = _scalar_mult(P, e // 2)
    Q_pt = _edwards_add(Q_pt, Q_pt)
    if e & 1:
        Q_pt = _edwards_add(Q_pt, P)
    return Q_pt

def _encode_point(P: Point) -> bytes:
    """Encode a point into 32 bytes (little-endian y with sign bit of x)."""
    x, y = P
    bits = [(y >> i) & 1 for i in range(255)] + [x & 1]
    return bytes([sum((bits[i * 8 + j] << j) for j in range(8)) for i in range(32)])

def _decode_point(s: bytes) -> Point:
    """Decode 32 bytes into a curve point."""
    y = sum(2**i * ((s[i // 8] >> (i % 8)) & 1) for i in range(255))
    x = _x_recover(y)
    if (x & 1) != ((s[31] >> 7) & 1):
        x = Q - x
    return (x, y)

# ============================================================================
# PUBLIC API: KEY DERIVATION, SIGN & VERIFY
# ============================================================================

def generate_keypair() -> Tuple[str, str]:
    """
    Generates a new random Ed25519 keypair.
    Returns: (secret_key_hex, public_key_hex)
    """
    sk_bytes = os.urandom(32)
    pk_bytes = public_key_from_secret(sk_bytes)
    return sk_bytes.hex(), pk_bytes.hex()

def public_key_from_secret(secret_key: bytes) -> bytes:
    """Derives 32-byte public key from 32-byte secret key."""
    h = hashlib.sha512(secret_key).digest()
    a = 2**254 + sum(2**i * ((h[i // 8] >> (i % 8)) & 1) for i in range(3, 254))
    A = _scalar_mult(BASE_POINT, a)
    return _encode_point(A)

def sign_bytes(secret_key: bytes, message: bytes) -> bytes:
    """
    Signs message bytes with 32-byte secret key according to RFC 8032.
    Returns: 64-byte signature.
    """
    h = hashlib.sha512(secret_key).digest()
    a = 2**254 + sum(2**i * ((h[i // 8] >> (i % 8)) & 1) for i in range(3, 254))
    A_bytes = _encode_point(_scalar_mult(BASE_POINT, a))

    # r = SHA-512(h[32:] || M) mod L
    r = int.from_bytes(hashlib.sha512(h[32:] + message).digest(), "little") % L
    R = _scalar_mult(BASE_POINT, r)
    R_bytes = _encode_point(R)

    # k = SHA-512(R || A || M) mod L
    k = int.from_bytes(hashlib.sha512(R_bytes + A_bytes + message).digest(), "little") % L

    # S = (r + k * a) mod L
    S = (r + k * a) % L
    return R_bytes + S.to_bytes(32, "little")

def verify_bytes(public_key: bytes, message: bytes, signature: bytes) -> bool:
    """
    Verifies a 64-byte Ed25519 signature against 32-byte public key and message.
    """
    if len(signature) != 64 or len(public_key) != 32:
        return False
    R_bytes = signature[:32]
    S = int.from_bytes(signature[32:], "little")
    if S >= L:
        return False
    try:
        A = _decode_point(public_key)
        R = _decode_point(R_bytes)
    except Exception:
        return False

    k = int.from_bytes(hashlib.sha512(R_bytes + public_key + message).digest(), "little") % L
    SB = _scalar_mult(BASE_POINT, S)
    RA = _edwards_add(R, _scalar_mult(A, k))
    return SB == RA

# Hex-string convenience wrappers
def sign_hex(secret_key_hex: str, message: bytes) -> str:
    sk = bytes.fromhex(secret_key_hex)
    return sign_bytes(sk, message).hex()

def verify_hex(public_key_hex: str, message: bytes, signature_hex: str) -> bool:
    pk = bytes.fromhex(public_key_hex)
    sig = bytes.fromhex(signature_hex)
    return verify_bytes(pk, message, sig)

# ============================================================================
# CRYPTOGRAPHIC SEAL
# ============================================================================

@dataclass(frozen=True)
class CryptographicSeal:
    """
    An immutable cryptographic seal certifying a payload digest.
    """
    signer_role: str
    signer_name: str
    public_key_hex: str
    signature_hex: str
    payload_digest: str
    timestamp_utc: str

    def verify(self, payload_bytes: bytes) -> bool:
        """Verifies that the seal matches the payload and signature is sound."""
        actual_digest = hashlib.sha256(payload_bytes).hexdigest()
        if actual_digest != self.payload_digest:
            return False
        return verify_hex(self.public_key_hex, payload_bytes, self.signature_hex)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signer_role": self.signer_role,
            "signer_name": self.signer_name,
            "public_key_hex": self.public_key_hex,
            "signature_hex": self.signature_hex,
            "payload_digest": self.payload_digest,
            "timestamp_utc": self.timestamp_utc
        }

    @classmethod
    def create(
        cls,
        signer_role: str,
        signer_name: str,
        secret_key_hex: str,
        payload_bytes: bytes,
        timestamp_utc: Optional[str] = None
    ) -> CryptographicSeal:
        sk = bytes.fromhex(secret_key_hex)
        pk = public_key_from_secret(sk).hex()
        digest = hashlib.sha256(payload_bytes).hexdigest()
        sig = sign_bytes(sk, payload_bytes).hex()
        ts = timestamp_utc or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return cls(
            signer_role=signer_role,
            signer_name=signer_name,
            public_key_hex=pk,
            signature_hex=sig,
            payload_digest=digest,
            timestamp_utc=ts
        )

if __name__ == "__main__":
    print("Testing Ed25519 engine...")
    sk, pk = generate_keypair()
    msg = b"Black-Heart: The Proof-Carrying Polyglot"
    seal = CryptographicSeal.create("ARBITER", "Settlement Node", sk, msg)
    assert seal.verify(msg) is True
    assert seal.verify(msg + b"tamper") is False
    print(f"[✓] Ed25519 Sound: PK={pk[:16]}... Sig={seal.signature_hex[:16]}...")
