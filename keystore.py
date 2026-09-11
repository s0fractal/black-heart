#!/usr/bin/env python3
"""
keystore.py -- private key custody, kept apart from every public export.

Public documents in this repository (organism, colony and swarm PDFs and JSON
states, vaults) are made to be shared. Before S5a several of them carried the
secret keys needed to continue them, so publishing a document published the
authority to sign as it. This module is the other half of the split:

  * a Keystore holds secret keys, keyed by the public key each one derives,
    and is written only to its own file with mode 0600;
  * continuing a document needs an explicit key source, resolved in a stated
    order, and a missing key is a named refusal -- never a silent fallback to
    a generated or all-zero key;
  * `secret_material_reasons` lets a packer refuse secret material instead of
    shipping it. A vault is not a secret store.

Nothing here makes an exposed key safe again. A key that has already been
published stays exposed; see docs/KEY-CUSTODY.md.
"""
from __future__ import annotations

import json
import os
import re
import stat
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from crypto import is_valid_public_key, public_key_from_secret

KEYSTORE_PROFILE = "black-heart.keystore.v1"
KEYSTORE_SUFFIX = ".keys"
# A single organism/autopoiesis/morpho-autopoiesis document's own private-key
# sidecar. Written as the escape, not a literal glyph in this source file, so
# it survives regardless of an editor's or a tool's declared encoding; it is
# the same 🔑 (U+1F511) either way. Chosen over ".key" to read at a glance,
# consistent with this project's other glyph-named things (%🖤, GLYPH_K = 🖤).
PRIVATE_KEY_SUFFIX = "\U0001F511"
# ".key" is kept recognized here ONLY so the secret-material detector below
# still refuses a sidecar written by a checkout from before this rename; no
# writer in this repo creates ".key" going forward.
_LEGACY_PRIVATE_KEY_SUFFIX = ".key"
SECRET_FILE_SUFFIXES = (PRIVATE_KEY_SUFFIX, _LEGACY_PRIVATE_KEY_SUFFIX, KEYSTORE_SUFFIX)

_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
_HEX64_BYTES = re.compile(rb"(?<![0-9a-fA-F])([0-9a-fA-F]{64})(?![0-9a-fA-F])")
_SECRET_FIELD = re.compile(rb'"(?:secret_key_hex|authority_sk_hex|sk_hex)"\s*:\s*"[0-9a-fA-F]{64}"')
_PAIR_SCAN_LIMIT = 512


class MissingKeyError(RuntimeError):
    """A signing step was asked for and no private key source provides the key."""


class PrivateFileError(OSError):
    """A private key file was not written, because its path is not safe to write."""


def write_private_file(path: str, text: str) -> str:
    """Write `text` to `path` as a private file, mode 0600, replacing it atomically.

    - The temporary file is created exclusively (`mkstemp`: O_CREAT|O_EXCL,
      mode 0600) under an unpredictable name in the target's own directory,
      and written only through the descriptor that created it. A link planted
      at any temporary name cannot be followed, because no name is reopened.
    - An existing `path` is replaced only if it is a regular file. A link,
      directory or anything else there is refused and left as it is, so bytes
      behind a link are never touched. If a link appears after that check,
      `os.replace` renames over the link itself and still does not follow it.
    - On failure, only the temporary entry this call created is removed.

    Before the S5a review, `Keystore.save` opened `path.tmp-<pid>` with O_TRUNC
    and followed a link planted there, so the secret landed in the link's target.
    """
    try:
        existing = os.lstat(path)
    except FileNotFoundError:
        existing = None
    if existing is not None and not stat.S_ISREG(existing.st_mode):
        raise PrivateFileError(
            f"refusing to write a private key at {path}: it exists and is not a regular file "
            "(a link or other entry there is left untouched)")
    fd, tmp = tempfile.mkstemp(prefix=f".{os.path.basename(path)}.", suffix=".tmp",
                               dir=os.path.dirname(os.path.abspath(path)))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise
    return path


def _canonical_public(public_key_hex: str) -> str:
    if not isinstance(public_key_hex, str) or not is_valid_public_key(public_key_hex):
        raise ValueError(f"not a valid Ed25519 public key: {public_key_hex!r}")
    return bytes.fromhex(public_key_hex).hex()


def _derive_public(secret_key_hex: str) -> str:
    if not isinstance(secret_key_hex, str) or not _HEX64.match(secret_key_hex):
        raise ValueError("a secret key must be 64 hex characters")
    return public_key_from_secret(bytes.fromhex(secret_key_hex)).hex()


class Keystore:
    """Secret keys indexed by the canonical public key each derives."""

    def __init__(self) -> None:
        self._keys: Dict[str, str] = {}

    def add(self, secret_key_hex: str) -> str:
        public = _derive_public(secret_key_hex)
        self._keys[public] = secret_key_hex.lower()
        return public

    def has(self, public_key_hex: str) -> bool:
        try:
            return _canonical_public(public_key_hex) in self._keys
        except ValueError:
            return False

    def secret_for(self, public_key_hex: str) -> str:
        """The secret key for this public key, or a named MissingKeyError."""
        public = _canonical_public(public_key_hex)
        if public not in self._keys:
            raise MissingKeyError(f"no private key for {public[:16]}... in this keystore")
        return self._keys[public]

    def public_keys(self) -> List[str]:
        return sorted(self._keys)

    def __len__(self) -> int:
        return len(self._keys)

    def to_document(self) -> Dict[str, Any]:
        return {"profile": KEYSTORE_PROFILE, "keys": dict(sorted(self._keys.items()))}

    @classmethod
    def from_document(cls, d: Any) -> "Keystore":
        """Strict: exactly profile and keys, and every secret derives its own key."""
        if not isinstance(d, dict) or set(d) != {"profile", "keys"}:
            raise ValueError("a keystore document must be exactly {\"profile\", \"keys\"}")
        if d["profile"] != KEYSTORE_PROFILE:
            raise ValueError(f"unsupported keystore profile {d['profile']!r}")
        if not isinstance(d["keys"], dict):
            raise ValueError("keystore 'keys' must map public keys to secret keys")
        store = cls()
        for public, secret in d["keys"].items():
            if not isinstance(public, str) or not isinstance(secret, str):
                raise ValueError("keystore entries must be strings")
            if _derive_public(secret) != _canonical_public(public):
                raise ValueError(f"keystore entry for {public[:16]}... holds another key's secret")
            store.add(secret)
        return store

    def save(self, path: str) -> str:
        """Write as a private file; see `write_private_file`."""
        return write_private_file(path, json.dumps(self.to_document(), indent=2, sort_keys=True) + "\n")

    @classmethod
    def load(cls, path: str) -> "Keystore":
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_document(json.load(fh))

    @classmethod
    def from_legacy_secrets(cls, secrets: List[str]) -> "Keystore":
        """For an operator migrating a state written before S5a, deliberately.

        Those states carried their secrets in the public document, so every key
        recovered this way has already been exposed wherever the document went.
        """
        store = cls()
        for secret in secrets:
            if secret:
                store.add(secret)
        return store


def sidecar_path(state_path: str) -> str:
    return state_path + KEYSTORE_SUFFIX


def resolve_keystore(explicit_path: Optional[str], state_path: str) -> Tuple[Keystore, str]:
    """The key source for continuing `state_path`, in a stated order.

    1. an explicit path the operator passed (`--keys`);
    2. the keystore next to the state, `<state>.keys`.

    Anything else is a MissingKeyError. The public state itself is never a key
    source, whatever it contains.
    """
    if explicit_path:
        return Keystore.load(explicit_path), explicit_path
    side = sidecar_path(state_path)
    if os.path.exists(side):
        return Keystore.load(side), side
    raise MissingKeyError(
        f"no private key source: pass --keys PATH, or keep the keystore at {side}. "
        "Secret keys are never read from the public state.")


def secret_material_reasons(name: str, data: bytes) -> List[str]:
    """Why these bytes look like private key material, or [] if they do not.

    Four signals, each named: a private key file name, a keystore document, a
    field that holds a 64-hex secret by name, and a 64-hex value whose derived
    public key appears in the same bytes. The last is bounded, and exceeding
    the bound is itself a reason: a file with more than `_PAIR_SCAN_LIMIT`
    distinct 64-hex strings is not scanned for pairs, so it cannot be cleared
    and is refused. Measured: about 1.6 ms per candidate, so the limit costs
    under a second per file; no file in this repository holds more than 14.
    (Before the S5a review, exceeding it returned the other reasons, often
    none, so padding a secret with 513 digests made it pass.)

    This detects the declared patterns. It is not a guarantee against every
    encoding of a secret.
    """
    reasons: List[str] = []
    if name.endswith(SECRET_FILE_SUFFIXES):
        reasons.append("its name marks a private key file")
    if KEYSTORE_PROFILE.encode("ascii") in data:
        reasons.append("it holds a keystore")
    if _SECRET_FIELD.search(data):
        reasons.append("it holds a secret key in a named field")
    candidates = {m.group(1).lower() for m in _HEX64_BYTES.finditer(data)}
    if len(candidates) > _PAIR_SCAN_LIMIT:
        reasons.append(f"it holds {len(candidates)} distinct 64-hex strings, more than the "
                       f"{_PAIR_SCAN_LIMIT} the pair scan checks, so it cannot be cleared")
        return reasons
    lowered = data.lower()
    for candidate in candidates:
        try:
            derived = public_key_from_secret(bytes.fromhex(candidate.decode())).hex().encode()
        except Exception:
            continue
        if derived in lowered:
            reasons.append("it holds a secret key next to the public key it derives")
            break
    return reasons
