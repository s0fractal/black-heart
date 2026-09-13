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


# --------------------------------------------------------------------------- #
# LI-2: evidence evaluation and an attributed admission decision
# Contract: docs/LIBRARY-INTERACTION-LI2.md
# --------------------------------------------------------------------------- #
POLICY_PROFILE = "black-heart.library-interaction.policy.v1"
DECISION_PROFILE = "black-heart.library-interaction.decision.v1"
EVALUATOR_PROFILE = "black-heart.li2.grounded-evaluator.v1"
EVALUATOR_VERSION = "1"
DECISION_SIG_DOMAIN = b"bh-li2-decision-v1:"

# The only grade LI-2 supports. Any other grade is a named unsupported
# operation until a later slice selects it -- including inside a policy, which
# is refused rather than silently narrowed.
SUPPORTED_GRADE = wk.EvidenceGrade.GROUNDED.value          # "GROUNDED"

# Taken FROM the enum, never restated: VerificationStatus values are lowercase
# ("pass"/"fail"/"unverified") while EvidenceGrade values are uppercase. Writing
# the strings by hand here silently disabled admission and would have made
# verify_decision refuse every genuine decision.
VERDICT_PASS = wk.VerificationStatus.PASS.value
VERDICT_VALUES = frozenset(v.value for v in wk.VerificationStatus)
MAX_POLICY_BYTES = 1 * 1024 * 1024
MAX_DECISION_BYTES = 4 * 1024 * 1024


def load_policy(path: str) -> Dict[str, Any]:
    """The CALLER's policy. Never read from the parent document, the proposal or
    a default. Two shapes are refused outright instead of being used: an
    implicit trust-all author set, and a policy that waives signature checks."""
    raw, refusal = _read_file(path, MAX_POLICY_BYTES,
                              "POLICY_UNREADABLE", "POLICY_TOO_LARGE")
    if refusal:
        return refusal
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_dupe_pairs)
    except UnicodeDecodeError as e:
        return _refuse("POLICY_NOT_JSON", f"not UTF-8: {e}")
    except ValueError as e:
        name = ("POLICY_DUPLICATE_KEYS" if "duplicate JSON key" in str(e)
                else "POLICY_NOT_JSON")
        return _refuse(name, str(e))
    if not isinstance(doc, dict):
        return _refuse("POLICY_NOT_OBJECT", f"policy is {type(doc).__name__}, not an object")
    if doc.get("profile") != POLICY_PROFILE:
        return _refuse("POLICY_UNSUPPORTED_PROFILE", f"{doc.get('profile')!r}")

    for field, want, tname in (("trust_config", dict, "object"),
                               ("allowed_operations", list, "list"),
                               ("allowed_grades", list, "list")):
        if field not in doc:
            return _refuse("POLICY_FIELD_MISSING", f"policy has no {field!r}")
        if not isinstance(doc[field], want) or isinstance(doc[field], bool):
            return _refuse("POLICY_FIELD_TYPE",
                           f"{field!r} is {type(doc[field]).__name__}, not a {tname}")
    tc_raw = doc["trust_config"]

    # is_author_trusted() treats None as TRUST EVERYONE. An empty list is a
    # legitimate deny-all and is accepted; an absent/None allowlist is not.
    if tc_raw.get("trusted_author_pks", None) is None:
        return _refuse("POLICY_TRUST_ALL",
                       "trusted_author_pks is absent or null, which means trust-all; "
                       "supply an explicit list (an empty list is a valid deny-all)")
    if not isinstance(tc_raw["trusted_author_pks"], list):
        return _refuse("POLICY_FIELD_TYPE", "trusted_author_pks is not a list")
    for pk in tc_raw["trusted_author_pks"]:
        if not (_is_hex(pk, 64) and crypto.is_valid_public_key(pk)):
            return _refuse("POLICY_FIELD_TYPE", f"trusted author {pk!r} is not a public key")
    if tc_raw.get("require_bound_signature", None) is not True:
        return _refuse("POLICY_NO_SIGNATURE",
                       "require_bound_signature must be exactly true")

    budget = tc_raw.get("max_atp_budget", None)
    if not (isinstance(budget, int) and not isinstance(budget, bool) and budget > 0):
        return _refuse("POLICY_BUDGET_INVALID",
                       f"max_atp_budget must be a positive int, got {budget!r}")

    admitted = tc_raw.get("admitted_grades", None)
    if not isinstance(admitted, list) or not admitted:
        return _refuse("POLICY_FIELD_TYPE", "admitted_grades must be a non-empty list")
    for collection, label in ((admitted, "admitted_grades"),
                              (doc["allowed_grades"], "allowed_grades")):
        for g in collection:
            if g != SUPPORTED_GRADE:
                return _refuse("POLICY_UNSUPPORTED_GRADE",
                               f"{label} contains {g!r}; only {SUPPORTED_GRADE!r} is "
                               "supported in LI-2")
    if not doc["allowed_operations"]:
        return _refuse("POLICY_FIELD_TYPE", "allowed_operations must be non-empty")
    for op in doc["allowed_operations"]:
        if op != SUPPORTED_OPERATION:
            return _refuse("POLICY_UNSUPPORTED_OPERATION",
                           f"allowed_operations contains {op!r}")

    try:
        trust = wk.TrustConfig(
            trusted_author_pks=set(tc_raw["trusted_author_pks"]),
            admitted_grades={wk.EvidenceGrade(g) for g in admitted},
            max_atp_budget=budget,
            require_bound_signature=True)
    except Exception as e:                                   # noqa: BLE001
        return _refuse("POLICY_FIELD_TYPE", f"{type(e).__name__}: {e}")

    return _ok(policy=doc, trust_config=trust,
               policy_sha256=hashlib.sha256(wk.canonical_jcs(doc)).hexdigest(),
               allowed_operations=list(doc["allowed_operations"]),
               allowed_grades=list(doc["allowed_grades"]),
               max_atp_budget=budget)


def evaluate_evidence(claim, trust_config) -> Dict[str, Any]:
    """Replay the evidence through the REAL host verifier under the CALLER's
    policy. No reimplementation, no adapter defaults. This is the evidence
    quantity only -- it decides nothing about admission."""
    verdict = wk.WarrantVerifier(trust_config).audit_claim(claim)
    details = verdict.details if isinstance(getattr(verdict, "details", None), dict) else {}
    # Verdict.delta_atp DEFAULTS TO 0, so it cannot distinguish "measured zero"
    # from "never measured" -- most refusals return before any reduction runs.
    # Only an explicit details["atp_spent"] is a measurement; anything else is
    # recorded as null, never as 0.
    measured = "atp_spent" in details and isinstance(details["atp_spent"], int) \
        and not isinstance(details["atp_spent"], bool)
    return {"status": verdict.status.value,
            "grade": verdict.grade.value,
            "reason": verdict.reason,
            "atp_spent": int(details["atp_spent"]) if measured else None,
            "atp_spent_measured": bool(measured)}


def decide_admission(evaluation: Dict[str, Any], operation: str, grade: str,
                     allowed_operations, allowed_grades) -> Dict[str, Any]:
    """The POLICY quantity, computed separately from the evidence quantity.
    PASS is necessary but never sufficient; a refusal here is a policy outcome
    and never a mathematical claim about the claim."""
    if operation not in allowed_operations:
        return {"admitted": False,
                "reason": f"policy does not permit operation {operation!r}"}
    if grade not in allowed_grades:
        return {"admitted": False, "reason": f"policy does not permit grade {grade!r}"}
    if evaluation["status"] != VERDICT_PASS:
        return {"admitted": False,
                "reason": f"evidence did not pass (status {evaluation['status']}); "
                          "UNVERIFIED is no verdict and FAIL is a checked negative"}
    return {"admitted": True,
            "reason": "evidence PASSed and the caller policy permits this "
                      "operation and grade"}


def decision_body(proposal: Dict[str, Any], policy_sha256: str, evaluator: Dict[str, Any],
                  evaluation: Dict[str, Any], admission: Dict[str, Any],
                  decider_pk_hex: str) -> Dict[str, Any]:
    return {
        "proposal_id": proposal["proposal_id"],
        "parent_pdf_sha256": proposal["parent_pdf_sha256"],
        "policy_sha256": policy_sha256,
        "claim_id": proposal["claim_id"],
        "claim_author_pk_hex": proposal["claim_author_pk_hex"],
        "proposer_pk_hex": proposal["proposer_pk_hex"],
        "evaluator": evaluator,
        "evaluation": evaluation,
        "admission": admission,
        "decider_pk_hex": decider_pk_hex.lower(),
    }


def compute_decision_id(body: Dict[str, Any]) -> str:
    return hashlib.sha256(wk.canonical_jcs(body)).hexdigest()


def decision_message(decision_id: str) -> bytes:
    return DECISION_SIG_DOMAIN + bytes.fromhex(decision_id)


_EVALUATOR_FIELDS = {"profile", "version", "atp_budget_requested",
                     "atp_budget_limit", "atp_spent", "atp_spent_measured"}
_EVALUATION_FIELDS = {"status", "grade", "reason"}
_ADMISSION_FIELDS = {"admitted", "reason"}
_GRADE_VALUES = frozenset(g.value for g in wk.EvidenceGrade)


def _is_nonneg_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def validate_decision_body(body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Check the NESTED content of a decision before any field is used.
    A decider signature is ATTRIBUTION -- it says who sealed the report. It is
    not evidence replay and not authority, so a re-signed body with an unknown
    evaluator, a wrongly-typed verdict, a missing reason, or an admission that
    contradicts its own verdict must be a named refusal, not an ok result and
    not an exception. Returns a refusal dict, or None when the body is sound."""
    ev = body["evaluator"]
    if set(ev.keys()) != _EVALUATOR_FIELDS:
        return _refuse("DECISION_FIELD_MISSING",
                       f"evaluator fields {sorted(ev.keys())} != {sorted(_EVALUATOR_FIELDS)}")
    if ev["profile"] != EVALUATOR_PROFILE:
        return _refuse("DECISION_UNSUPPORTED_EVALUATOR",
                       f"evaluator profile {ev['profile']!r} is not {EVALUATOR_PROFILE!r}")
    if ev["version"] != EVALUATOR_VERSION:
        return _refuse("DECISION_UNSUPPORTED_EVALUATOR",
                       f"evaluator version {ev['version']!r} is not {EVALUATOR_VERSION!r}")
    for f in ("atp_budget_requested", "atp_budget_limit"):
        if not _is_nonneg_int(ev[f]):
            return _refuse("DECISION_FIELD_TYPE", f"evaluator.{f} is not a non-negative int")
    if not isinstance(ev["atp_spent_measured"], bool):
        return _refuse("DECISION_FIELD_TYPE", "evaluator.atp_spent_measured is not a boolean")
    if ev["atp_spent_measured"]:
        if not _is_nonneg_int(ev["atp_spent"]):
            return _refuse("DECISION_FIELD_TYPE",
                           "evaluator.atp_spent is not a non-negative int although "
                           "it is marked as measured")
    elif ev["atp_spent"] is not None:
        # Absence of a measurement is null, never a number that reads as one.
        return _refuse("DECISION_FIELD_TYPE",
                       "evaluator.atp_spent must be null when nothing was measured")

    evl = body["evaluation"]
    if set(evl.keys()) != _EVALUATION_FIELDS:
        return _refuse("DECISION_FIELD_MISSING",
                       f"evaluation fields {sorted(evl.keys())} != {sorted(_EVALUATION_FIELDS)}")
    if not isinstance(evl["status"], str) or evl["status"] not in VERDICT_VALUES:
        return _refuse("DECISION_FIELD_TYPE",
                       f"evaluation.status {evl['status']!r} is not a verdict")
    if not isinstance(evl["grade"], str) or evl["grade"] not in _GRADE_VALUES:
        return _refuse("DECISION_FIELD_TYPE", f"evaluation.grade {evl['grade']!r} is not a grade")
    if not isinstance(evl["reason"], str):
        return _refuse("DECISION_FIELD_TYPE", "evaluation.reason is not a string")

    adm = body["admission"]
    if set(adm.keys()) != _ADMISSION_FIELDS:
        return _refuse("DECISION_FIELD_MISSING",
                       f"admission fields {sorted(adm.keys())} != {sorted(_ADMISSION_FIELDS)}")
    if not isinstance(adm["admitted"], bool):
        return _refuse("DECISION_FIELD_TYPE", "admission.admitted is not a boolean")
    if not isinstance(adm["reason"], str):
        return _refuse("DECISION_FIELD_TYPE", "admission.reason is not a string")
    # A decision that admits on a non-PASS verdict contradicts itself.
    if adm["admitted"] and evl["status"] != VERDICT_PASS:
        return _refuse("DECISION_INCONSISTENT",
                       f"admission.admitted is true while evaluation.status is "
                       f"{evl['status']!r}")

    for f in ("proposal_id", "parent_pdf_sha256", "policy_sha256", "claim_id"):
        if not _is_hex(body[f], 64):
            return _refuse("DECISION_FIELD_TYPE", f"{f} is not a 64-hex digest")
    for f in ("claim_author_pk_hex", "proposer_pk_hex", "decider_pk_hex"):
        if not (_is_hex(body[f], 64) and crypto.is_valid_public_key(body[f])):
            return _refuse("DECISION_FIELD_TYPE", f"{f} is not a valid public key")
    return None


def verify_decision(raw: bytes, expect_proposal_id: Optional[str] = None,
                    expect_parent_sha256: Optional[str] = None,
                    expect_policy_sha256: Optional[str] = None) -> Dict[str, Any]:
    """A saved decision is a REPORT, not a grant. Re-derive the id and the
    signature and check the caller's pins; never trust the stated fields."""
    if len(raw) > MAX_DECISION_BYTES:
        return _refuse("DECISION_TOO_LARGE", f"{len(raw)} bytes")
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_dupe_pairs)
    except UnicodeDecodeError as e:
        return _refuse("DECISION_NOT_JSON", f"not UTF-8: {e}")
    except ValueError as e:
        name = ("DECISION_DUPLICATE_KEYS" if "duplicate JSON key" in str(e)
                else "DECISION_NOT_JSON")
        return _refuse(name, str(e))
    if not isinstance(doc, dict):
        return _refuse("DECISION_MALFORMED", f"is {type(doc).__name__}, not an object")
    if set(doc.keys()) != {"profile", "body", "decision_id", "decision_signature_hex"}:
        return _refuse("DECISION_MALFORMED", f"unexpected fields: {sorted(doc.keys())}")
    if doc["profile"] != DECISION_PROFILE:
        return _refuse("DECISION_UNSUPPORTED_PROFILE", f"{doc['profile']!r}")
    body = doc["body"]
    if not isinstance(body, dict):
        return _refuse("DECISION_MALFORMED", "body is not an object")
    want = {"proposal_id", "parent_pdf_sha256", "policy_sha256", "claim_id",
            "claim_author_pk_hex", "proposer_pk_hex", "evaluator", "evaluation",
            "admission", "decider_pk_hex"}
    if set(body.keys()) != want:
        return _refuse("DECISION_MALFORMED", f"unexpected body fields: {sorted(body.keys())}")
    for f in ("evaluator", "evaluation", "admission"):
        if not isinstance(body[f], dict):
            return _refuse("DECISION_FIELD_TYPE", f"{f} is not an object")
    nested = validate_decision_body(body)
    if nested is not None:
        return nested
    if not _is_hex(doc["decision_id"], 64):
        return _refuse("DECISION_MALFORMED", "decision_id is not a 64-hex digest")

    recomputed = compute_decision_id(body)
    if recomputed != doc["decision_id"].lower():
        return _refuse("DECISION_ID_MISMATCH",
                       f"stated {doc['decision_id'][:16]}... != recomputed {recomputed[:16]}...")
    if not crypto.verify_hex(body["decider_pk_hex"], decision_message(recomputed),
                             doc["decision_signature_hex"]):
        return _refuse("DECISION_SIGNATURE_INVALID",
                       "decision signature does not verify under decider_pk_hex")

    # The caller's pins. A decision never transfers to another subject.
    for pin, field, name in ((expect_proposal_id, "proposal_id", "DECISION_PROPOSAL_MISMATCH"),
                             (expect_parent_sha256, "parent_pdf_sha256", "DECISION_PARENT_MISMATCH"),
                             (expect_policy_sha256, "policy_sha256", "DECISION_POLICY_MISMATCH")):
        if pin is not None and body[field].lower() != str(pin).strip().lower():
            return _refuse(name, f"decision binds {body[field][:16]}..., not {str(pin)[:16]}...")

    return _ok(decision_id=doc["decision_id"],
               proposal_id=body["proposal_id"],
               parent_pdf_sha256=body["parent_pdf_sha256"],
               policy_sha256=body["policy_sha256"],
               evaluation_status=body["evaluation"]["status"],
               admitted=body["admission"]["admitted"],
               admission_reason=body["admission"]["reason"],
               atp_spent=body["evaluator"]["atp_spent"],
               atp_spent_measured=body["evaluator"]["atp_spent_measured"],
               decider_pk_hex=body["decider_pk_hex"],
               # Explicit boundaries: verifying this artifact establishes WHO
               # sealed the report and that its content is well-formed and
               # self-consistent. It does NOT re-run the mathematics, and it
               # does NOT make the decider authorized -- a self-declared signing
               # key is not authority. A reader that needs either must do it.
               attribution_verified=True,
               evidence_replayed_by_reader=False,
               decider_authority_established=False,
               applied=False, status="DECISION_ONLY")


def evaluate(pdf_path: str, proposal_path: str, policy_path: str,
             decider_key_file: str, out_path: str) -> Dict[str, Any]:
    """LI-2 `evaluate`: re-authenticate, replay the evidence under the caller's
    policy, decide admission separately, and RECORD the decision. No successor,
    no reward, no change to the parent."""
    parent = read_parent(pdf_path)
    if not parent["ok"]:
        return parent
    praw, refusal = _read_file(proposal_path, MAX_PROPOSAL_BYTES,
                               "PROPOSAL_UNREADABLE", "PROPOSAL_TOO_LARGE")
    if refusal:
        return refusal
    # LI-1 authentication is re-run in full, bound to this parent's exact bytes.
    proposal = verify_proposal(praw, parent["pdf_sha256"])
    if not proposal["ok"]:
        return proposal
    policy = load_policy(policy_path)
    if not policy["ok"]:
        return policy
    key = load_proposer_key(decider_key_file)
    if not key["ok"]:
        return {"ok": False,
                "refusal": key["refusal"].replace("PROPOSER_KEY", "DECIDER_KEY"),
                "detail": key["detail"]}

    claim_res = authenticate_claim_document(
        json.loads(praw.decode("utf-8"))["body"]["claim"])
    if not claim_res["ok"]:
        return claim_res
    claim = claim_res["claim"]

    # The witness budget is recorded in the decision, so it must be admissible
    # BEFORE anything is executed or written -- otherwise evaluate can emit a
    # decision its own reader refuses. (from_dict coerces with int(), so a
    # negative value arrives here as a negative int rather than a type error.)
    requested = getattr(claim.witness, "atp_budget", None)
    if not _is_nonneg_int(requested):
        return _refuse("CLAIM_BUDGET_INVALID",
                       f"witness atp_budget {requested!r} is not a non-negative int")

    evaluation = evaluate_evidence(claim, policy["trust_config"])
    evaluator = {"profile": EVALUATOR_PROFILE, "version": EVALUATOR_VERSION,
                 "atp_budget_requested": requested,
                 "atp_budget_limit": policy["max_atp_budget"],
                 # null when the verifier reported no measurement (e.g. a policy
                 # refusal that returned before any reduction ran). Absence of a
                 # measurement is never written as zero.
                 "atp_spent": evaluation.pop("atp_spent"),
                 "atp_spent_measured": evaluation.pop("atp_spent_measured")}
    admission = decide_admission(evaluation, proposal["operation"], claim_res["grade"],
                                 policy["allowed_operations"], policy["allowed_grades"])

    body = decision_body(proposal, policy["policy_sha256"], evaluator, evaluation,
                         admission, key["proposer_pk_hex"])
    # Writer/reader agreement is structural, not a promise: the body goes
    # through the SAME validator the reader uses, before it is signed or
    # written. A body this host would refuse to read is never emitted.
    self_check = validate_decision_body(body)
    if self_check is not None:
        return _refuse("DECISION_SELF_CHECK_FAILED",
                       f"refusing to emit a decision this reader would reject: "
                       f"{self_check['refusal']}: {self_check['detail']}")
    did = compute_decision_id(body)
    decision = {"profile": DECISION_PROFILE, "body": body, "decision_id": did,
                "decision_signature_hex": crypto.sign_hex(key["secret_key_hex"],
                                                          decision_message(did))}
    try:
        with open(out_path, "xb") as f:
            f.write(json.dumps(decision, sort_keys=True, indent=2).encode("utf-8") + b"\n")
    except FileExistsError:
        return _refuse("OUTPUT_EXISTS", f"{out_path} already exists; refusing to overwrite")
    except OSError as e:
        return _refuse("OUTPUT_UNWRITABLE", f"{type(e).__name__}: {e}")

    return _ok(decision_id=did, proposal_id=proposal["proposal_id"],
               parent_pdf_sha256=parent["pdf_sha256"],
               policy_sha256=policy["policy_sha256"],
               evaluation_status=evaluation["status"],
               evaluation_reason=evaluation["reason"],
               atp_spent=evaluator["atp_spent"],
               admitted=admission["admitted"], admission_reason=admission["reason"],
               decider_pk_hex=key["proposer_pk_hex"], out_path=out_path,
               applied=False, status="DECISION_ONLY",
               note="decision recorded; no successor, no reward, parent unchanged")


# --------------------------------------------------------------------------- #
# LI-3: immutable successor and a readable transition
# Contract: docs/LIBRARY-INTERACTION-LI3.md
# --------------------------------------------------------------------------- #
TRANSITION_PROFILE = "black-heart.library-interaction.transition.v1"
RECEIPT_SIG_DOMAIN = b"bh-li3-transition-v1:"
STAGING_SUFFIX = ".partial"
MAX_RECEIPT_BYTES = 1 * 1024 * 1024

_VERIFY_NOTE = ("Verify with the host CLI, never by running this file: "
                "python3 cli.py library explain-transition ...")


def render_successor_pdf(claims: list, note_lines: list) -> bytes:
    """A DATA-ONLY successor: begins at %PDF with correct xref offsets and
    carries no executable code -- unlike the existing parent profile, whose
    Python prologue shifts every offset and whose embedded runner reads the
    document's own trust config. The manifest line keeps the SAME format, so the
    LI-1 reader parses a successor unchanged and it can be the next parent."""
    lines = ["q", "0.05 0.06 0.08 rg", "0 0 612 792 re f",
             "BT", "/F1 14 Tf", "1 1 1 rg", "45 740 Td",
             "(%# BLACK-HEART LIBRARY - DATA ONLY SUCCESSOR) Tj", "/F1 9 Tf"]
    for n in note_lines:
        lines += ["0 -16 Td", f"({wk._sanitize_pdf_text(str(n)[:95])}) Tj"]
    lines += ["ET", "Q"]
    content = "\n".join(lines).encode("latin-1", "replace")
    objs = [b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n",
            f"4 0 obj\n<< /Length {len(content)} >>\nstream\n".encode("latin-1")
            + content + b"\nendstream\nendobj\n",
            b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"]
    body = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
    offsets = []
    for o in objs:
        offsets.append(len(body))
        body += o
    xref_pos = len(body)
    xref = b"xref\n0 6\n0000000000 65535 f \n" + b"".join(
        f"{o:010d} 00000 n \n".encode("latin-1") for o in offsets)
    trailer = (f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_pos}\n"
               "%%EOF\n").encode("latin-1")
    manifest = {"format": SUPPORTED_MANIFEST_FORMAT,
                "claims": claims,
                "trust_config": wk.TrustConfig().to_dict()}
    mline = MANIFEST_PREFIX + json.dumps(manifest, sort_keys=True).encode("utf-8") + b"\n"
    return body + xref + trailer + mline


def receipt_body(parent_sha: str, successor_sha: str, proposal_id: str,
                 decision_id: str, policy_sha: str, added_claim_id: str,
                 issuer_pk_hex: str) -> Dict[str, Any]:
    return {"parent_pdf_sha256": parent_sha.lower(),
            "successor_pdf_sha256": successor_sha.lower(),
            "proposal_id": proposal_id.lower(),
            "decision_id": decision_id.lower(),
            "policy_sha256": policy_sha.lower(),
            "added_claim_id": added_claim_id.lower(),
            "issuer_pk_hex": issuer_pk_hex.lower()}


def compute_receipt_id(body: Dict[str, Any]) -> str:
    return hashlib.sha256(wk.canonical_jcs(body)).hexdigest()


def receipt_message(receipt_id: str) -> bytes:
    return RECEIPT_SIG_DOMAIN + bytes.fromhex(receipt_id)


_RECEIPT_FIELDS = {"parent_pdf_sha256", "successor_pdf_sha256", "proposal_id",
                   "decision_id", "policy_sha256", "added_claim_id", "issuer_pk_hex"}


def verify_receipt(raw: bytes, expect_issuer_pk: Optional[str] = None) -> Dict[str, Any]:
    """Parse and authenticate a transition receipt. The issuer is NOT
    self-declaring: without a caller-supplied expected issuer key this reports
    that the issuer was not established, exactly as LI-2's decider does."""
    if len(raw) > MAX_RECEIPT_BYTES:
        return _refuse("RECEIPT_TOO_LARGE", f"{len(raw)} bytes")
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_dupe_pairs)
    except UnicodeDecodeError as e:
        return _refuse("RECEIPT_NOT_JSON", f"not UTF-8: {e}")
    except ValueError as e:
        name = ("RECEIPT_DUPLICATE_KEYS" if "duplicate JSON key" in str(e)
                else "RECEIPT_NOT_JSON")
        return _refuse(name, str(e))
    if not isinstance(doc, dict):
        return _refuse("RECEIPT_MALFORMED", f"is {type(doc).__name__}, not an object")
    if set(doc.keys()) != {"profile", "body", "receipt_id", "receipt_signature_hex"}:
        return _refuse("RECEIPT_MALFORMED", f"unexpected fields: {sorted(doc.keys())}")
    if doc["profile"] != TRANSITION_PROFILE:
        return _refuse("RECEIPT_UNSUPPORTED_PROFILE", f"{doc['profile']!r}")
    body = doc["body"]
    if not isinstance(body, dict):
        return _refuse("RECEIPT_MALFORMED", "body is not an object")
    if set(body.keys()) != _RECEIPT_FIELDS:
        return _refuse("RECEIPT_FIELD_MISSING",
                       f"body fields {sorted(body.keys())} != {sorted(_RECEIPT_FIELDS)}")
    for f in _RECEIPT_FIELDS:
        if not _is_hex(body[f], 64):
            return _refuse("RECEIPT_FIELD_TYPE", f"{f} is not a 64-hex value")
    if not crypto.is_valid_public_key(body["issuer_pk_hex"]):
        return _refuse("RECEIPT_FIELD_TYPE", "issuer_pk_hex is not a valid public key")
    if not _is_hex(doc["receipt_id"], 64):
        return _refuse("RECEIPT_MALFORMED", "receipt_id is not a 64-hex digest")
    recomputed = compute_receipt_id(body)
    if recomputed != doc["receipt_id"].lower():
        return _refuse("RECEIPT_ID_MISMATCH",
                       f"stated {doc['receipt_id'][:16]}... != recomputed {recomputed[:16]}...")
    if not crypto.verify_hex(body["issuer_pk_hex"], receipt_message(recomputed),
                             doc["receipt_signature_hex"]):
        return _refuse("RECEIPT_SIGNATURE_INVALID",
                       "receipt signature does not verify under issuer_pk_hex")
    issuer_ok = (expect_issuer_pk is not None and
                 body["issuer_pk_hex"] == str(expect_issuer_pk).strip().lower())
    if expect_issuer_pk is not None and not issuer_ok:
        return _refuse("RECEIPT_ISSUER_MISMATCH",
                       f"issued by {body['issuer_pk_hex'][:16]}..., not the expected issuer")
    out = dict(body)
    out.update(issuer_authorized_by_caller=issuer_ok)
    return _ok(receipt_id=doc["receipt_id"], **out)


def _claim_ids(manifest_claims) -> list:
    out = []
    for c in manifest_claims:
        out.append(c.get("claim_id") if isinstance(c, dict) else None)
    return out


def apply_transition(pdf_path: str, proposal_path: str, decision_path: str,
                     policy_path: str, issuer_key_file: str,
                     out_path: str, receipt_path: str) -> Dict[str, Any]:
    """LI-3 `apply`. A saved admitted=true authorises NOTHING: the proposal is
    re-verified, the parent's exact bytes re-checked, and the evaluation RE-RUN
    under the caller's current policy at the point of use. The parent file is
    never written to."""
    parent = read_parent(pdf_path)
    if not parent["ok"]:
        return parent
    praw, refusal = _read_file(proposal_path, MAX_PROPOSAL_BYTES,
                               "PROPOSAL_UNREADABLE", "PROPOSAL_TOO_LARGE")
    if refusal:
        return refusal
    proposal = verify_proposal(praw, parent["pdf_sha256"])
    if not proposal["ok"]:
        return proposal
    policy = load_policy(policy_path)
    if not policy["ok"]:
        return policy
    key = load_proposer_key(issuer_key_file)
    if not key["ok"]:
        return {"ok": False, "refusal": key["refusal"].replace("PROPOSER_KEY", "ISSUER_KEY"),
                "detail": key["detail"]}

    draw, refusal = _read_file(decision_path, MAX_DECISION_BYTES,
                               "DECISION_UNREADABLE", "DECISION_TOO_LARGE")
    if refusal:
        return refusal
    # The stored decision is checked too -- but it is a report, not the reason.
    decision = verify_decision(draw, expect_proposal_id=proposal["proposal_id"],
                               expect_parent_sha256=parent["pdf_sha256"],
                               expect_policy_sha256=policy["policy_sha256"])
    if not decision["ok"]:
        return decision

    claim_res = authenticate_claim_document(
        json.loads(praw.decode("utf-8"))["body"]["claim"])
    if not claim_res["ok"]:
        return claim_res
    claim = claim_res["claim"]
    requested = getattr(claim.witness, "atp_budget", None)
    if not _is_nonneg_int(requested):
        return _refuse("CLAIM_BUDGET_INVALID",
                       f"witness atp_budget {requested!r} is not a non-negative int")

    # Re-run the evaluation NOW, under the caller's CURRENT policy. The saved
    # decision cannot carry an authorisation past a policy or parent change.
    evaluation = evaluate_evidence(claim, policy["trust_config"])
    admission = decide_admission(evaluation, proposal["operation"], claim_res["grade"],
                                 policy["allowed_operations"], policy["allowed_grades"])
    if not admission["admitted"]:
        return _refuse("NOT_ADMITTED_NOW",
                       f"re-evaluation under the current policy does not admit this "
                       f"claim: {admission['reason']} (evidence {evaluation['status']})")

    existing = parent["manifest"]["claims"]
    if claim.claim_id in _claim_ids(existing):
        return _refuse("CLAIM_ALREADY_PRESENT",
                       f"parent already contains claim {claim.claim_id[:16]}...; "
                       "applying again would double-add")

    successor_claims = list(existing) + [claim_res["claim_dict"]]
    note = [f"Parent sha256: {parent['pdf_sha256'][:32]}...",
            f"Added claim:   {claim.claim_id[:32]}...",
            f"Grade:         {claim_res['grade']} (one bounded check, not a universal truth)",
            f"Claims:        {len(existing)} preserved + 1 added",
            _VERIFY_NOTE]
    successor_bytes = render_successor_pdf(successor_claims, note)

    # ---- staging, then publication; the receipt is published LAST ---------- #
    stage_out, stage_receipt = out_path + STAGING_SUFFIX, receipt_path + STAGING_SUFFIX
    for p, name in ((out_path, "OUTPUT_EXISTS"), (receipt_path, "RECEIPT_EXISTS"),
                    (stage_out, "STAGING_EXISTS"), (stage_receipt, "STAGING_EXISTS")):
        if os.path.exists(p):
            return _refuse(name, f"{p} already exists; refusing to overwrite or reuse")
    try:
        with open(stage_out, "xb") as f:
            f.write(successor_bytes)
    except FileExistsError:
        return _refuse("STAGING_EXISTS", f"{stage_out} already exists")
    except OSError as e:
        return _refuse("OUTPUT_UNWRITABLE", f"{type(e).__name__}: {e}")

    # The successor's address is derived AFTER rendering, from the bytes that
    # were actually written. No whole-file hash is embedded in the file itself.
    try:
        with open(stage_out, "rb") as f:
            written = f.read()
    except OSError as e:
        return _refuse("OUTPUT_UNWRITABLE", f"{type(e).__name__}: {e}")
    successor_sha = hashlib.sha256(written).hexdigest()

    rbody = receipt_body(parent["pdf_sha256"], successor_sha, proposal["proposal_id"],
                         decision["decision_id"], policy["policy_sha256"],
                         claim.claim_id, key["proposer_pk_hex"])
    rid = compute_receipt_id(rbody)
    receipt = {"profile": TRANSITION_PROFILE, "body": rbody, "receipt_id": rid,
               "receipt_signature_hex": crypto.sign_hex(key["secret_key_hex"],
                                                        receipt_message(rid))}
    rbytes = json.dumps(receipt, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    try:
        with open(stage_receipt, "xb") as f:
            f.write(rbytes)
    except OSError as e:
        return _refuse("RECEIPT_UNWRITABLE", f"{type(e).__name__}: {e}")

    try:
        os.rename(stage_out, out_path)          # publish the successor
        os.rename(stage_receipt, receipt_path)  # completion marker, published LAST
    except OSError as e:
        return _refuse("PUBLISH_FAILED",
                       f"{type(e).__name__}: {e}; staged files remain for inspection "
                       "-- nothing was rolled back")

    return _ok(successor_path=out_path, receipt_path=receipt_path,
               parent_pdf_sha256=parent["pdf_sha256"],
               successor_pdf_sha256=successor_sha,
               receipt_id=rid, added_claim_id=claim.claim_id,
               claims_before=len(existing), claims_after=len(successor_claims),
               parent_unchanged=True, status="TRANSITION_COMPLETE",
               note="successor and receipt published; the parent file was not written to")


def explain_transition(parent_path: str, successor_path: str, proposal_path: str,
                       decision_path: str, receipt_path: str,
                       expect_issuer_pk: Optional[str] = None) -> Dict[str, Any]:
    """A fresh verifier: confirm the old claims remain and EXACTLY the proposed
    claim was added, without regenerating the successor."""
    parent = read_parent(parent_path)
    if not parent["ok"]:
        return parent
    successor = read_parent(successor_path)
    if not successor["ok"]:
        return successor
    rraw, refusal = _read_file(receipt_path, MAX_RECEIPT_BYTES,
                               "RECEIPT_UNREADABLE", "RECEIPT_TOO_LARGE")
    if refusal:
        return refusal
    receipt = verify_receipt(rraw, expect_issuer_pk)
    if not receipt["ok"]:
        return receipt
    if receipt["parent_pdf_sha256"] != parent["pdf_sha256"]:
        return _refuse("RECEIPT_PARENT_MISMATCH",
                       "receipt does not bind these parent bytes")
    if receipt["successor_pdf_sha256"] != successor["pdf_sha256"]:
        return _refuse("RECEIPT_SUCCESSOR_MISMATCH",
                       "receipt does not bind these successor bytes")

    praw, refusal = _read_file(proposal_path, MAX_PROPOSAL_BYTES,
                               "PROPOSAL_UNREADABLE", "PROPOSAL_TOO_LARGE")
    if refusal:
        return refusal
    proposal = verify_proposal(praw, parent["pdf_sha256"])
    if not proposal["ok"]:
        return proposal
    if proposal["proposal_id"] != receipt["proposal_id"]:
        return _refuse("RECEIPT_PROPOSAL_MISMATCH", "receipt names another proposal")
    draw, refusal = _read_file(decision_path, MAX_DECISION_BYTES,
                               "DECISION_UNREADABLE", "DECISION_TOO_LARGE")
    if refusal:
        return refusal
    decision = verify_decision(draw, expect_proposal_id=proposal["proposal_id"],
                               expect_parent_sha256=parent["pdf_sha256"])
    if not decision["ok"]:
        return decision
    if decision["decision_id"] != receipt["decision_id"]:
        return _refuse("RECEIPT_DECISION_MISMATCH", "receipt names another decision")

    before, after = _claim_ids(parent["manifest"]["claims"]), \
        _claim_ids(successor["manifest"]["claims"])
    missing = [c for c in before if c not in after]
    if missing:
        return _refuse("PARENT_CLAIMS_DROPPED",
                       f"{len(missing)} parent claim(s) are absent from the successor")
    added = list(after)
    for c in before:
        added.remove(c)
    if len(added) != 1:
        return _refuse("CLAIM_COUNT_UNEXPECTED",
                       f"successor adds {len(added)} claims; exactly one was proposed")
    if added[0] != receipt["added_claim_id"] or added[0] != proposal["claim_id"]:
        return _refuse("ADDED_CLAIM_MISMATCH",
                       "the added claim is not the proposed one")

    return _ok(transition="COMPLETE",
               parent_pdf_sha256=parent["pdf_sha256"],
               successor_pdf_sha256=successor["pdf_sha256"],
               added_claim_id=added[0],
               claims_preserved=len(before), claims_after=len(after),
               admitted_claim_ids=[added[0]],
               issuer_pk_hex=receipt["issuer_pk_hex"],
               issuer_authorized_by_caller=receipt["issuer_authorized_by_caller"],
               regenerated=False,
               evidence_replayed_by_reader=False,
               note=("the parent's claims are all present and exactly the proposed "
                     "claim was added; this asserts one bounded check under one "
                     "policy, never that the document is universally true"))
