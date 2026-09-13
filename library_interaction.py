#!/usr/bin/env python3
"""LI-1 -- proposal intake for one warrant-ledger PDF profile.

Contract: docs/LIBRARY-INTERACTION-LI1.md. Brief: docs/LIVING-LIBRARY-INTERACTION.md.

Two operations, `inspect` and `add_claim`, over ONE PDF profile. They produce a
PROPOSAL ONLY: nothing here evaluates the claim's mathematics, decides admission,
or writes a successor (LI-2 / LI-3). A well-formed proposal carrying false or
unverified mathematics is still only a proposal -- this module never reports an
"accepted claim".

The parent PDF is read as DATA: opened "rb" and scanned for one manifest line.
Its embedded Python runner is never executed and is never delegated to, and the
trust configuration the document advertises is reported as an advertisement that
carries no authority here.

Every function returns a structured result and never raises on adversarial
input; a failure is a NAMED refusal (see _REFUSALS in the contract).
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, Optional, Tuple

import crypto
import warrant_kernel as wk

PROPOSAL_PROFILE = "black-heart.library-interaction.proposal.v1"
SUPPORTED_OPERATION = "add-claim"
SUPPORTED_MANIFEST_FORMAT = "WARRANT-0.2"

# The manifest line, measured on a real generate_warrant_ledger_pdf artifact.
# NOTE: the bare substring b" WARRANT_KERNEL_MANIFEST: " occurs TWICE in an
# honest document (the second is inside the embedded runner's own source), so
# duplicate detection MUST anchor on this full line prefix at a line start.
MANIFEST_PREFIX = b"# %" + bytes([0xF0, 0x9F, 0x96, 0xA4]) + b" WARRANT_KERNEL_MANIFEST: "

# Domain separation: distinct from warrant's b"warrant-sig-v1:" so a claim
# signature can never be replayed as an envelope signature, or the reverse.
ENVELOPE_SIG_DOMAIN = b"bh-li1-proposal-v1:"

MAX_PARENT_BYTES = 16 * 1024 * 1024
MAX_MANIFEST_BYTES = 4 * 1024 * 1024
MAX_CLAIM_BYTES = 1 * 1024 * 1024
MAX_PROPOSAL_BYTES = 4 * 1024 * 1024


def _refuse(name: str, detail: str) -> Dict[str, Any]:
    return {"ok": False, "refusal": name, "detail": detail}


def _ok(**fields) -> Dict[str, Any]:
    out = {"ok": True, "refusal": None}
    out.update(fields)
    return out


def _no_dupe_pairs(pairs):
    """Reject duplicate JSON keys instead of letting the last one win."""
    seen = {}
    for k, v in pairs:
        if k in seen:
            raise ValueError(f"duplicate JSON key: {k!r}")
        seen[k] = v
    return seen


def _read_file(path: str, limit: int, unreadable: str, too_large: str):
    try:
        size = os.path.getsize(path)
    except OSError as e:
        return None, _refuse(unreadable, f"{type(e).__name__}: {e}")
    if size > limit:
        return None, _refuse(too_large, f"{size} bytes exceeds the {limit}-byte limit")
    try:
        with open(path, "rb") as f:
            return f.read(), None
    except OSError as e:
        return None, _refuse(unreadable, f"{type(e).__name__}: {e}")


def _is_hex(value: Any, length: Optional[int] = None) -> bool:
    if not isinstance(value, str):
        return False
    if length is not None and len(value) != length:
        return False
    return len(value) > 0 and all(c in "0123456789abcdef" for c in value.lower())


# --------------------------------------------------------------------------- #
# Parent PDF: read as data, never executed
# --------------------------------------------------------------------------- #
def find_prefix_offsets(raw: bytes):
    """Offsets of EVERY occurrence of the strict prefix, anchored or not."""
    offsets, i = [], 0
    while True:
        i = raw.find(MANIFEST_PREFIX, i)
        if i == -1:
            return offsets
        offsets.append(i)
        i += 1


def find_manifest_lines(raw: bytes):
    """Offsets of every strict prefix that actually BEGINS a line. Anchoring is
    what makes the envelope unambiguous: an occurrence that does not start a
    line is not a manifest line here, but a reader anchoring differently (the
    embedded runner uses a bare `find`) could select it instead. read_parent
    therefore refuses any file where the two disagree."""
    return [i for i in find_prefix_offsets(raw)
            if i == 0 or raw[i - 1:i] == b"\n"]


def read_parent(path: str) -> Dict[str, Any]:
    """Parse the supported parent profile out of a PDF, as data."""
    raw, refusal = _read_file(path, MAX_PARENT_BYTES,
                              "PARENT_UNREADABLE", "PARENT_TOO_LARGE")
    if refusal:
        return refusal

    offsets = find_manifest_lines(raw)
    # An unanchored occurrence of our own prefix is an ambiguity between
    # conforming readers, not a manifest. Refuse rather than pick one.
    stray = [i for i in find_prefix_offsets(raw) if i not in offsets]
    if stray:
        return _refuse("MANIFEST_AMBIGUOUS",
                       f"{len(stray)} manifest prefix(es) occur mid-line; another "
                       "reader anchoring differently could select one")
    if not offsets:
        return _refuse("MANIFEST_ABSENT", "no strict warrant manifest line found")
    if len(offsets) > 1:
        return _refuse("MANIFEST_DUPLICATE",
                       f"{len(offsets)} manifest lines found; exactly one is required")

    start = offsets[0] + len(MANIFEST_PREFIX)
    end = raw.find(b"\n", start)
    if end == -1:
        return _refuse("MANIFEST_UNTERMINATED", "manifest line has no terminating newline")
    payload = raw[start:end]
    if len(payload) > MAX_MANIFEST_BYTES:
        return _refuse("MANIFEST_TOO_LARGE",
                       f"{len(payload)} bytes exceeds the {MAX_MANIFEST_BYTES}-byte limit")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as e:
        return _refuse("MANIFEST_NOT_JSON", f"payload is not UTF-8: {e}")
    try:
        manifest = json.loads(text, object_pairs_hook=_no_dupe_pairs)
    except ValueError as e:
        name = ("MANIFEST_DUPLICATE_KEYS" if "duplicate JSON key" in str(e)
                else "MANIFEST_NOT_JSON")
        return _refuse(name, str(e))
    if not isinstance(manifest, dict):
        return _refuse("MANIFEST_NOT_OBJECT",
                       f"manifest is {type(manifest).__name__}, not an object")

    # Required fields. A MISSING claims collection is a refusal, never an empty
    # list -- unlike the embedded runner's manifest.get("claims", []).
    for field, want, tname in (("format", str, "string"),
                               ("claims", list, "list"),
                               ("trust_config", dict, "object")):
        if field not in manifest:
            return _refuse("MANIFEST_FIELD_MISSING", f"manifest has no {field!r}")
        if not isinstance(manifest[field], want) or isinstance(manifest[field], bool):
            return _refuse("MANIFEST_FIELD_TYPE",
                           f"{field!r} is {type(manifest[field]).__name__}, not a {tname}")
    if manifest["format"] != SUPPORTED_MANIFEST_FORMAT:
        return _refuse("MANIFEST_UNSUPPORTED_FORMAT",
                       f"{manifest['format']!r} is not {SUPPORTED_MANIFEST_FORMAT!r}")

    return _ok(pdf_sha256=hashlib.sha256(raw).hexdigest(),
               pdf_bytes=len(raw),
               manifest_format=manifest["format"],
               claim_count=len(manifest["claims"]),
               advertised_trust_config=manifest["trust_config"],
               manifest=manifest)


def inspect_parent(path: str, expect_parent_sha256: Optional[str] = None) -> Dict[str, Any]:
    """`inspect`: identify the exact bytes and the supported manifest profile."""
    res = read_parent(path)
    if not res["ok"]:
        return res
    if expect_parent_sha256 is not None and \
            res["pdf_sha256"].lower() != str(expect_parent_sha256).strip().lower():
        return _refuse("PARENT_PIN_MISMATCH",
                       f"actual {res['pdf_sha256']} != expected {expect_parent_sha256}")
    claims = res["manifest"]["claims"]
    summary = []
    for c in claims:
        if isinstance(c, dict):
            body = c.get("body") if isinstance(c.get("body"), dict) else {}
            summary.append({"claim_id": c.get("claim_id"),
                            "grade": body.get("grade"),
                            "author_pk_hex": body.get("author_pk_hex")})
        else:
            summary.append({"claim_id": None, "grade": None, "author_pk_hex": None})
    return _ok(pdf_sha256=res["pdf_sha256"], pdf_bytes=res["pdf_bytes"],
               manifest_format=res["manifest_format"],
               claim_count=res["claim_count"],
               claims=summary,
               # The document's own trust config is an ADVERTISEMENT. It confers
               # no authority here and LI-1 makes no decision from it.
               advertised_trust_config_note=(
                   "advertised by the document; carries no authority in LI-1"),
               advertised_trust_config=res["advertised_trust_config"],
               executed_input_pdf=False)


# --------------------------------------------------------------------------- #
# The supplied claim: parsed and AUTHENTICATED (not evaluated)
# --------------------------------------------------------------------------- #
def authenticate_claim_document(doc: Any) -> Dict[str, Any]:
    """THE claim check, shared by BOTH paths -- intake (`load_claim`) and the
    envelope reader (`verify_proposal`). A receiver of an external envelope must
    never assume it came through our own `add_claim`, so the reader repeats
    exactly this, not a weaker version of it.

    Structure, recomputed claim id and author signature only. It does NOT check
    the claim's mathematics: that is LI-2's evaluation, and nothing here implies
    the claim is true."""
    if not isinstance(doc, dict):
        return _refuse("CLAIM_MALFORMED",
                       f"claim is {type(doc).__name__}, not an object")
    try:
        claim = wk.EdgeClaim.from_dict(doc)
    except Exception as e:                                   # noqa: BLE001
        return _refuse("CLAIM_MALFORMED", f"{type(e).__name__}: {e}")

    # EdgeClaim.from_dict takes claim_id from the dict and __post_init__ only
    # fills it when empty, so the signature can cover an id that disagrees with
    # the body. audit_claim catches that, but LI-1 does not run audit_claim.
    recomputed = claim.compute_claim_id()
    if claim.claim_id != recomputed:
        return _refuse("CLAIM_ID_MISMATCH",
                       f"stated {claim.claim_id[:16]}... != recomputed {recomputed[:16]}...")
    if not claim.verify_signature():
        return _refuse("CLAIM_SIGNATURE_INVALID",
                       "Ed25519 signature does not verify under the stated author key")
    return _ok(claim=claim, claim_dict=claim.to_dict(),
               claim_id=claim.claim_id,
               grade=claim.grade.value,
               author_pk_hex=claim.author_pk_hex)


def load_claim(path: str) -> Dict[str, Any]:
    """Intake path: read the file, parse it, then run the SHARED check."""
    raw, refusal = _read_file(path, MAX_CLAIM_BYTES,
                              "CLAIM_UNREADABLE", "CLAIM_TOO_LARGE")
    if refusal:
        return refusal
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_dupe_pairs)
    except UnicodeDecodeError as e:
        return _refuse("CLAIM_NOT_JSON", f"not UTF-8: {e}")
    except ValueError as e:
        name = ("CLAIM_DUPLICATE_KEYS" if "duplicate JSON key" in str(e)
                else "CLAIM_NOT_JSON")
        return _refuse(name, str(e))
    return authenticate_claim_document(doc)


def load_proposer_key(path: str) -> Dict[str, Any]:
    """Read the proposer secret key from a FILE (never from argv). The key is
    never echoed; only the derived public key is returned."""
    raw, refusal = _read_file(path, 4096,
                              "PROPOSER_KEY_UNREADABLE", "PROPOSER_KEY_MALFORMED")
    if refusal:
        return refusal
    try:
        sk_hex = raw.decode("utf-8").strip()
    except UnicodeDecodeError as e:
        return _refuse("PROPOSER_KEY_MALFORMED", f"not UTF-8: {e}")
    if not _is_hex(sk_hex, 64):
        return _refuse("PROPOSER_KEY_MALFORMED",
                       "expected 64 hex characters of Ed25519 secret key")
    try:
        pk_hex = crypto.public_key_from_secret(bytes.fromhex(sk_hex)).hex()
    except Exception as e:                                   # noqa: BLE001
        return _refuse("PROPOSER_KEY_MALFORMED", f"{type(e).__name__}: {e}")
    return _ok(secret_key_hex=sk_hex, proposer_pk_hex=pk_hex)


# --------------------------------------------------------------------------- #
# The proposal envelope
# --------------------------------------------------------------------------- #
def proposal_body(operation: str, parent_pdf_sha256: str, parent_manifest_format: str,
                  claim_dict: Dict[str, Any], proposer_pk_hex: str) -> Dict[str, Any]:
    """Everything that could retarget the proposal lives here, under the
    signature. No file paths: paths are locators, not identities."""
    return {
        "operation": operation,
        "parent_pdf_sha256": parent_pdf_sha256.lower(),
        "parent_manifest_format": parent_manifest_format,
        "claim": claim_dict,
        "proposer_pk_hex": proposer_pk_hex.lower(),
    }


def compute_proposal_id(body: Dict[str, Any]) -> str:
    return hashlib.sha256(wk.canonical_jcs(body)).hexdigest()


def envelope_message(proposal_id: str) -> bytes:
    return ENVELOPE_SIG_DOMAIN + bytes.fromhex(proposal_id)


def build_proposal(parent: Dict[str, Any], claim_dict: Dict[str, Any],
                   secret_key_hex: str, proposer_pk_hex: str,
                   operation: str = SUPPORTED_OPERATION) -> Dict[str, Any]:
    body = proposal_body(operation, parent["pdf_sha256"], parent["manifest_format"],
                         claim_dict, proposer_pk_hex)
    pid = compute_proposal_id(body)
    sig = crypto.sign_hex(secret_key_hex, envelope_message(pid))
    return {"profile": PROPOSAL_PROFILE, "body": body,
            "proposal_id": pid, "envelope_signature_hex": sig}


def proposal_to_bytes(proposal: Dict[str, Any]) -> bytes:
    return json.dumps(proposal, sort_keys=True, indent=2).encode("utf-8") + b"\n"


def verify_proposal(raw: bytes, expect_parent_sha256: Optional[str] = None) -> Dict[str, Any]:
    """Parse and AUTHENTICATE a proposal. With expect_parent_sha256, also check
    the binding -- this is what stops a second parent consuming it as its own."""
    if len(raw) > MAX_PROPOSAL_BYTES:
        return _refuse("PROPOSAL_TOO_LARGE",
                       f"{len(raw)} bytes exceeds the {MAX_PROPOSAL_BYTES}-byte limit")
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_dupe_pairs)
    except UnicodeDecodeError as e:
        return _refuse("PROPOSAL_NOT_JSON", f"not UTF-8: {e}")
    except ValueError as e:
        name = ("PROPOSAL_DUPLICATE_KEYS" if "duplicate JSON key" in str(e)
                else "PROPOSAL_NOT_JSON")
        return _refuse(name, str(e))
    if not isinstance(doc, dict):
        return _refuse("PROPOSAL_MALFORMED", f"is {type(doc).__name__}, not an object")
    if set(doc.keys()) != {"profile", "body", "proposal_id", "envelope_signature_hex"}:
        return _refuse("PROPOSAL_MALFORMED",
                       f"unexpected top-level fields: {sorted(doc.keys())}")
    if doc["profile"] != PROPOSAL_PROFILE:
        return _refuse("PROPOSAL_UNSUPPORTED_PROFILE", f"{doc['profile']!r}")
    body = doc["body"]
    if not isinstance(body, dict):
        return _refuse("PROPOSAL_MALFORMED", "body is not an object")
    want = {"operation", "parent_pdf_sha256", "parent_manifest_format",
            "claim", "proposer_pk_hex"}
    if set(body.keys()) != want:
        return _refuse("PROPOSAL_MALFORMED", f"unexpected body fields: {sorted(body.keys())}")
    if body["operation"] != SUPPORTED_OPERATION:
        return _refuse("UNSUPPORTED_OPERATION", f"{body['operation']!r}")
    if not _is_hex(body["parent_pdf_sha256"], 64):
        return _refuse("PROPOSAL_MALFORMED", "parent_pdf_sha256 is not a 64-hex digest")
    if not (_is_hex(body["proposer_pk_hex"], 64) and
            crypto.is_valid_public_key(body["proposer_pk_hex"])):
        return _refuse("PROPOSAL_MALFORMED", "proposer_pk_hex is not a valid public key")
    if not _is_hex(doc["proposal_id"], 64):
        return _refuse("PROPOSAL_MALFORMED", "proposal_id is not a 64-hex digest")
    # A real signature over an unknown profile does not make it supported.
    if body["parent_manifest_format"] != SUPPORTED_MANIFEST_FORMAT:
        return _refuse("PROPOSAL_UNSUPPORTED_MANIFEST_FORMAT",
                       f"{body['parent_manifest_format']!r} is not "
                       f"{SUPPORTED_MANIFEST_FORMAT!r}")
    # The proposer's signature authenticates WHO sealed the envelope. It is NOT
    # a substitute for authenticating the claim inside it: an external envelope
    # need never have passed through our own add_claim.
    inner = authenticate_claim_document(body["claim"])
    if not inner["ok"]:
        return inner

    recomputed = compute_proposal_id(body)
    if recomputed != doc["proposal_id"].lower():
        return _refuse("PROPOSAL_ID_MISMATCH",
                       f"stated {doc['proposal_id'][:16]}... != recomputed {recomputed[:16]}...")
    if not crypto.verify_hex(body["proposer_pk_hex"], envelope_message(recomputed),
                             doc["envelope_signature_hex"]):
        return _refuse("PROPOSAL_SIGNATURE_INVALID",
                       "envelope signature does not verify under proposer_pk_hex")
    if expect_parent_sha256 is not None and \
            body["parent_pdf_sha256"] != str(expect_parent_sha256).strip().lower():
        return _refuse("PROPOSAL_PARENT_MISMATCH",
                       f"bound to {body['parent_pdf_sha256'][:16]}..., "
                       f"not {str(expect_parent_sha256)[:16]}...")
    return _ok(proposal_id=doc["proposal_id"],
               operation=body["operation"],
               parent_pdf_sha256=body["parent_pdf_sha256"],
               parent_manifest_format=body["parent_manifest_format"],
               proposer_pk_hex=body["proposer_pk_hex"],
               claim_author_pk_hex=inner["author_pk_hex"],
               claim_id=inner["claim_id"],
               claim_grade=inner["grade"],
               claim_authenticated=True,     # structure/id/signature only
               evaluated=False, admitted=False,
               status="PROPOSAL_ONLY")


# --------------------------------------------------------------------------- #
# add-claim: intake only
# --------------------------------------------------------------------------- #
def add_claim(pdf_path: str, expect_parent_sha256: str, claim_path: str,
              proposer_key_file: str, out_path: str) -> Dict[str, Any]:
    """Create a parent-bound, proposer-signed proposal. Admits nothing."""
    parent = read_parent(pdf_path)
    if not parent["ok"]:
        return parent
    if not _is_hex(str(expect_parent_sha256).strip(), 64):
        return _refuse("PARENT_PIN_MISMATCH",
                       "expected parent digest is not a 64-hex sha256")
    if parent["pdf_sha256"] != str(expect_parent_sha256).strip().lower():
        return _refuse("PARENT_PIN_MISMATCH",
                       f"actual {parent['pdf_sha256']} != expected {expect_parent_sha256}")

    claim = load_claim(claim_path)
    if not claim["ok"]:
        return claim
    key = load_proposer_key(proposer_key_file)
    if not key["ok"]:
        return key

    proposal = build_proposal(parent, claim["claim_dict"],
                              key["secret_key_hex"], key["proposer_pk_hex"])
    raw = proposal_to_bytes(proposal)
    try:
        # "xb": create-exclusive, so a pre-existing output is never overwritten
        # and no TOCTOU window is opened by a separate existence check.
        with open(out_path, "xb") as f:
            f.write(raw)
    except FileExistsError:
        return _refuse("OUTPUT_EXISTS", f"{out_path} already exists; refusing to overwrite")
    except OSError as e:
        return _refuse("OUTPUT_UNWRITABLE", f"{type(e).__name__}: {e}")

    return _ok(proposal_id=proposal["proposal_id"],
               parent_pdf_sha256=parent["pdf_sha256"],
               claim_id=claim["claim_id"],
               claim_grade=claim["grade"],
               claim_author_pk_hex=claim["author_pk_hex"],
               proposer_pk_hex=key["proposer_pk_hex"],
               out_path=out_path,
               # Intake authenticates WHO proposed WHAT against WHICH bytes. It
               # does not evaluate the claim's mathematics and admits nothing.
               evaluated=False, admitted=False, status="PROPOSAL_ONLY",
               note="proposal recorded; evidence not evaluated, nothing admitted")
