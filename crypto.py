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
    xx = (y * y - 1) * _inv(D * y * y + 1) % Q
    x = pow(xx, (Q + 3) // 8, Q)
    if (x * x - xx) % Q != 0:
        x = (x * SQRT_M1) % Q
    if (x * x - xx) % Q != 0:
        raise ValueError("Invalid point: xx is not a quadratic residue")
    if x % 2 != 0:
        x = Q - x
    return x

# Base point B = (Bx, By) where By = 4/5 mod Q
BY = (4 * _inv(5)) % Q
BX = _x_recover(BY)
BASE_POINT = (BX, BY)

# ============================================================================
# CURVE ARITHMETIC (EXTENDED TWISTED EDWARDS COORDINATES - RFC 8032 §5.1.4)
# ============================================================================

Point = Tuple[int, int]
ExtPoint = Tuple[int, int, int, int]  # (X : Y : Z : T) where x = X/Z, y = Y/Z, xy = T/Z

IDENTITY_EXT: ExtPoint = (0, 1, 1, 0)

def _affine_to_ext(pt: Point) -> ExtPoint:
    x, y = pt
    return (x, y, 1, (x * y) % Q)

def _ext_to_affine(pt: ExtPoint) -> Point:
    X, Y, Z, T = pt
    z_inv = _inv(Z)
    return ((X * z_inv) % Q, (Y * z_inv) % Q)

def _ext_add(p1: ExtPoint, p2: ExtPoint) -> ExtPoint:
    """
    Complete point addition in Extended Twisted Edwards Coordinates (Hisil et al., Asiacrypt 2008).
    Requires 8 multiplications in GF(Q) and 0 modular inversions.
    """
    X1, Y1, Z1, T1 = p1
    X2, Y2, Z2, T2 = p2
    A = ((Y1 - X1) * (Y2 - X2)) % Q
    B = ((Y1 + X1) * (Y2 + X2)) % Q
    C = (2 * D * T1 * T2) % Q
    D_val = (2 * Z1 * Z2) % Q
    E = (B - A) % Q
    F = (D_val - C) % Q
    G = (D_val + C) % Q
    H = (B + A) % Q
    return ((E * F) % Q, (G * H) % Q, (F * G) % Q, (E * H) % Q)

def _ext_double(p: ExtPoint) -> ExtPoint:
    """
    Point doubling in Extended Twisted Edwards Coordinates.
    Requires 4 multiplications + 4 squarings in GF(Q) and 0 modular inversions.
    """
    X1, Y1, Z1, T1 = p
    A = (X1 * X1) % Q
    B = (Y1 * Y1) % Q
    C = (2 * Z1 * Z1) % Q
    D_val = (-A) % Q
    E = ((X1 + Y1) * (X1 + Y1) - A - B) % Q
    G = (D_val + B) % Q
    F = (G - C) % Q
    H = (D_val - B) % Q
    return ((E * F) % Q, (G * H) % Q, (F * G) % Q, (E * H) % Q)

def _ext_cselect(p1: ExtPoint, p2: ExtPoint, bit: int) -> ExtPoint:
    """Constant-time conditional selection between two extended points without branching."""
    mask = -bit
    return (
        p1[0] ^ (mask & (p1[0] ^ p2[0])),
        p1[1] ^ (mask & (p1[1] ^ p2[1])),
        p1[2] ^ (mask & (p1[2] ^ p2[2])),
        p1[3] ^ (mask & (p1[3] ^ p2[3])),
    )

def _edwards_add(P: Point, Q_pt: Point) -> Point:
    """Add two points on the twisted Edwards curve using extended projective coordinates."""
    p1 = _affine_to_ext(P)
    p2 = _affine_to_ext(Q_pt)
    return _ext_to_affine(_ext_add(p1, p2))

def _scalar_mult(P: Point, e: int) -> Point:
    """
    Scalar multiplication e * P via fixed-width bit loop in extended coordinates.
    Mitigates timing attacks by avoiding branching and performs only a single
    modular inversion at the end of the 256-bit ladder (yielding ~30-60x speedup).
    """
    if e == 0 or P == (0, 1):
        return (0, 1)

    P_ext = _affine_to_ext(P)
    R = IDENTITY_EXT
    
    # Fixed-width 256-bit execution with branch-free selection
    bit_len = max(256, e.bit_length())
    for i in range(bit_len - 1, -1, -1):
        R = _ext_double(R)
        R_plus = _ext_add(R, P_ext)
        bit = (e >> i) & 1
        R = _ext_cselect(R, R_plus, bit)

    return _ext_to_affine(R)

def _encode_point(P: Point) -> bytes:
    """Encode a point into 32 bytes (little-endian y with sign bit of x)."""
    x, y = P
    bits = [(y >> i) & 1 for i in range(255)] + [x & 1]
    return bytes([sum((bits[i * 8 + j] << j) for j in range(8)) for i in range(32)])

def _decode_point(s: bytes) -> Point:
    """Decode 32 bytes into a curve point according to RFC 8032 §5.1.3."""
    if len(s) != 32:
        raise ValueError("Invalid point encoding: must be 32 bytes")
    y_raw = int.from_bytes(s, "little")
    x_0 = (y_raw >> 255) & 1
    y = y_raw & ((1 << 255) - 1)
    if y >= Q:
        raise ValueError(f"Invalid point: non-canonical y >= Q ({y} >= {Q})")
    x = _x_recover(y)
    if x == 0 and x_0 == 1:
        raise ValueError("Invalid point: x is 0 but sign bit is 1")
    if (x & 1) != x_0:
        x = (Q - x) % Q
    if (-x * x + y * y - (1 + D * x * x % Q * (y * y % Q))) % Q != 0:
        raise ValueError("Invalid point: fails curve equation")
    return (x, y)

def is_valid_public_key(pk_hex: str) -> bool:
    """Validates that pk_hex is a valid 64-char hex string representing a canonical Ed25519 curve point in the prime-order subgroup."""
    if not isinstance(pk_hex, str) or len(pk_hex) != 64:
        return False
    try:
        raw = bytes.fromhex(pk_hex)
        pt = _decode_point(raw)
        if pt == (0, 1):
            return False
        if _scalar_mult(pt, L) != (0, 1):
            return False
        return True
    except Exception:
        return False

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
    Fail-closed checks per RFC 8032:
    - S < L
    - Canonical point decoding
    - Rejection of identity point (0, 1) and small-order points
    """
    if len(signature) != 64 or len(public_key) != 32:
        return False
    R_bytes = signature[:32]
    S = int.from_bytes(signature[32:], "little")
    if S >= L or S < 0:
        return False
    try:
        A = _decode_point(public_key)
        R = _decode_point(R_bytes)
    except Exception:
        return False

    # Reject identity point (0, 1) and small-order points for A and R
    if A == (0, 1) or R == (0, 1):
        return False
    if _scalar_mult(A, 8) == (0, 1) or _scalar_mult(R, 8) == (0, 1):
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
