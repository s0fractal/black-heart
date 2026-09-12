#!/usr/bin/env python3
"""
EXP-LIB-001 runner — first living-library experiment.

Protocol: docs/EXP-LIB-001.md (rev 4). Predictions: ./README.md, committed
before this file. Nothing here is a result until measured; the module reports
replay (R1), external anchor (R2), and publication (R3) as SEPARATE results,
and never treats an UNVERIFIED as loop success.

The loop carries one extensional-equivalence claim through three events:
  0 CLAIM         reference I vs candidate K I on fixtures {I, I I, I (I I)}
  1 COUNTEREXAMPLE same pair, at input K (K != I): the generalization is false
  2 REFINE        reference I vs corrected candidate S K K on the fixtures + K

Combinators: I = 🤍, K = 🖤, S = 🌿.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

import glyph
import crypto
from warrant_kernel import (EdgeClaim, EmpiricalWitness, CounterexampleWitness,
                            Polarity, TrustConfig, WarrantVerifier, VerificationStatus)

I, K, S = "🤍", "🖤", "🌿"
REFERENCE = I
FIXTURES_C1 = [I, f"{I} {I}", f"{I} ({I} {I})"]
WITNESS_INPUT = K                       # outside FIXTURES_C1
FIXTURES_C3 = FIXTURES_C1 + [K]
EVENT_PROFILE = "black-heart.exp-lib-001.event.v1"

# Deterministic PUBLIC FIXTURE keys. They exist only for reproducibility and CI;
# a real release is signed by a key that is never committed (protocol §6bis).
AUTHOR_SK = bytes([1] * 32)
AUTHOR_PK = crypto.public_key_from_secret(AUTHOR_SK).hex()
FOREIGN_SK = bytes([2] * 32)            # an author the caller does not trust
FOREIGN_PK = crypto.public_key_from_secret(FOREIGN_SK).hex()


def caller_trust() -> TrustConfig:
    """The trust root is the CALLER's, pinned to the public-fixture author."""
    return TrustConfig(trusted_author_pks={AUTHOR_PK})


# --------------------------------------------------------------------------- #
# Claims
# --------------------------------------------------------------------------- #
def _empirical_claim(candidate: str, fixtures, sk=AUTHOR_SK, pk=AUTHOR_PK) -> EdgeClaim:
    w = EmpiricalWitness(fixtures=list(fixtures), fixtures_fingerprint="",
                         delta_atp=0, delta_size=0)
    w.fixtures_fingerprint = w.compute_fixtures_fingerprint()
    ph = glyph.term_hash(glyph.parse(REFERENCE))
    sh = glyph.term_hash(glyph.parse(candidate))
    return EdgeClaim.create_and_sign(ph, candidate, REFERENCE, sh,
                                     Polarity.AFFIRM, w, sk.hex(), pk)


def _counterexample_claim(candidate: str, input_expr: str, sk=AUTHOR_SK, pk=AUTHOR_PK) -> EdgeClaim:
    ref_out = glyph.evaluate(glyph.parse_application(REFERENCE, input_expr))
    cand_out = glyph.evaluate(glyph.parse_application(candidate, input_expr))
    cost = max(ref_out.atp_spent, cand_out.atp_spent) + 10
    w = CounterexampleWitness(input_expr=input_expr,
                              expected_normal_form=str(ref_out.term),
                              actual_divergence=str(cand_out.term),
                              atp_to_diverge=cost)
    ph = glyph.term_hash(glyph.parse(REFERENCE))
    sh = glyph.term_hash(glyph.parse(candidate))
    return EdgeClaim.create_and_sign(ph, candidate, REFERENCE, sh,
                                     Polarity.REFUTE, w, sk.hex(), pk)


def build_c1(**kw) -> EdgeClaim:
    return _empirical_claim(f"{K} {I}", FIXTURES_C1, **kw)


def build_c2(**kw) -> EdgeClaim:
    return _counterexample_claim(f"{K} {I}", WITNESS_INPUT, **kw)


def build_c3(**kw) -> EdgeClaim:
    return _empirical_claim(f"{S} {K} {K}", FIXTURES_C3, **kw)


# --------------------------------------------------------------------------- #
# Bounded canonical encoding (protocol §3.1) -- self-contained, not RFC 8785
# --------------------------------------------------------------------------- #
def _encode(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, int):
        if not (0 <= value <= 2 ** 53 - 1):
            raise ValueError(f"integer out of profile range: {value}")
        return str(value)
    if isinstance(value, float):
        raise ValueError("floating-point is not allowed in this profile")
    if isinstance(value, str):
        out = ['"']
        for ch in value:
            if ch == '"':
                out.append('\\"')
            elif ch == "\\":
                out.append("\\\\")
            elif ord(ch) < 0x20:
                out.append(f"\\u{ord(ch):04x}")
            else:
                out.append(ch)
        out.append('"')
        return "".join(out)
    if isinstance(value, list):
        return "[" + ",".join(_encode(v) for v in value) + "]"
    if isinstance(value, dict):
        keys = list(value.keys())
        if any(not isinstance(k, str) for k in keys):
            raise ValueError("object keys must be strings")
        # nested objects: keys ordered by Unicode code point (Python sort)
        items = sorted(keys)
        return "{" + ",".join(_encode(k) + ":" + _encode(value[k]) for k in items) + "}"
    raise ValueError(f"unencodable type: {type(value).__name__}")


_CORE_ORDER = ["profile", "index", "prev_event_hash", "kind", "claim",
               "expected_verdict", "author_pk_hex"]


def canonical_core_bytes(core: dict) -> bytes:
    if set(core.keys()) != set(_CORE_ORDER):
        raise ValueError(f"core fields must be exactly {_CORE_ORDER}")
    body = ",".join(_encode(k) + ":" + _encode(core[k]) for k in _CORE_ORDER)
    return ("{" + body + "}").encode("utf-8")


# --------------------------------------------------------------------------- #
# Events and journal
# --------------------------------------------------------------------------- #
GENESIS_PREV = "00" * 32


def make_event(index: int, prev_event_hash: str, kind: str, claim: EdgeClaim,
               expected_verdict: str, sk=AUTHOR_SK, pk=AUTHOR_PK) -> dict:
    core = {
        "profile": EVENT_PROFILE,
        "index": index,
        "prev_event_hash": prev_event_hash,
        "kind": kind,
        "claim": claim.to_dict(),
        "expected_verdict": expected_verdict,
        "author_pk_hex": pk,
    }
    cb = canonical_core_bytes(core)
    event_hash = hashlib.sha256(cb).hexdigest()
    signature_hex = crypto.sign_bytes(sk, cb).hex()
    return {**core, "event_hash": event_hash, "signature_hex": signature_hex}


def build_journal() -> list:
    """The three-event journal. Verdicts are recorded from a real audit, not
    asserted: whatever the verifier says is what the event records."""
    trust = caller_trust()
    verifier = WarrantVerifier(trust)
    plan = [
        ("CLAIM", build_c1()),
        ("COUNTEREXAMPLE", build_c2()),
        ("REFINE", build_c3()),
    ]
    journal = []
    prev = GENESIS_PREV
    for index, (kind, claim) in enumerate(plan):
        verdict = verifier.audit_claim(claim).status.value.upper()
        ev = make_event(index, prev, kind, claim, verdict)
        journal.append(ev)
        prev = ev["event_hash"]
    return journal


def journal_to_bytes(journal: list) -> bytes:
    return json.dumps(journal, ensure_ascii=False).encode("utf-8")


def _no_dupe_pairs(pairs):
    seen = {}
    for k, v in pairs:
        if k in seen:
            raise ValueError(f"duplicate key rejected: {k}")
        seen[k] = v
    return seen


def journal_from_bytes(data: bytes) -> list:
    return json.loads(data.decode("utf-8"), object_pairs_hook=_no_dupe_pairs)


# --------------------------------------------------------------------------- #
# Package for an independent reader: saved bytes, separately-pinned trust/root/
# tip, replay WITHOUT regenerating the journal.
# --------------------------------------------------------------------------- #
def write_package(path: str) -> dict:
    """Build the journal ONCE and write its bytes to `path`. The pins (root,
    tip) and the trust root are returned to be delivered to the reader
    SEPARATELY -- they are not inside the package bytes."""
    journal = build_journal()
    data = journal_to_bytes(journal)
    with open(path, "wb") as f:
        f.write(data)
    return {"path": path, "root": journal[0]["event_hash"],
            "tip": journal[-1]["event_hash"], "size": len(data)}


def verify_package(journal_bytes: bytes, trust: TrustConfig,
                   expected_root: str, expected_tip: str) -> dict:
    """The independent reader's whole job: parse the saved bytes (rejecting
    duplicate keys) and replay them under a separately-pinned trust root, root
    and tip. It NEVER calls build_journal -- it confirms the package it was
    given, not one it regenerated. A malformed package is a named refusal."""
    try:
        journal = journal_from_bytes(journal_bytes)
    except Exception as e:
        return {"accepted": False, "chain_ok": False,
                "boundary": f"package did not parse: {type(e).__name__}: {e}",
                "confirmed_through_index": -1, "verdicts": [],
                "root_matches": None, "tip_matches": None, "root": None, "tip": None}
    return replay(journal, trust, expected_root, expected_tip)


# --------------------------------------------------------------------------- #
# R1: replay to the oldest reachable confirmed ancestor
# --------------------------------------------------------------------------- #
_ALLOWED_KINDS = {"CLAIM", "COUNTEREXAMPLE", "REFINE"}
_ALLOWED_VERDICTS = {"PASS", "FAIL", "UNVERIFIED"}
_TOP_FIELDS = set(_CORE_ORDER) | {"event_hash", "signature_hex"}


def _is_hex(value, length=None) -> bool:
    if not isinstance(value, str):
        return False
    if length is not None and len(value) != length:
        return False
    return len(value) > 0 and all(c in "0123456789abcdef" for c in value)


def _structure_reason(ev, index: int):
    """The one complete format check: exact field set, the correct TYPE of
    every field checked BEFORE any operation on it, and the nested claim parsed.
    Returns a named reason, or None. Never raises on adversarial input -- an
    exception here would break the promised structured-refusal contract.
    """
    if not isinstance(ev, dict):
        return "event is not an object"
    keys = set(ev.keys())
    if keys != _TOP_FIELDS:
        missing = sorted(_TOP_FIELDS - keys)
        extra = sorted(keys - _TOP_FIELDS)
        if missing:
            return f"missing field(s) {missing}"
        return f"unexpected field(s) {extra}"
    # profile
    if not isinstance(ev["profile"], str) or ev["profile"] != EVENT_PROFILE:
        return f"unsupported or non-string profile {ev['profile']!r}"
    # index: type before value; `type() is int` also rejects bool
    if type(ev["index"]) is not int:
        return f"index {ev['index']!r} is not an int"
    if ev["index"] != index:
        return f"index {ev['index']} != position {index}"
    # prev_event_hash
    if not _is_hex(ev["prev_event_hash"], 64):
        return "prev_event_hash is not 64 lowercase hex"
    # kind / expected_verdict: str BEFORE set membership (else [] / {} raise)
    if not isinstance(ev["kind"], str) or ev["kind"] not in _ALLOWED_KINDS:
        return f"unsupported kind {ev['kind']!r}"
    if not isinstance(ev["expected_verdict"], str) or ev["expected_verdict"] not in _ALLOWED_VERDICTS:
        return f"unsupported expected_verdict {ev['expected_verdict']!r}"
    # author_pk_hex / event_hash / signature_hex
    if not _is_hex(ev["author_pk_hex"], 64):
        return "author_pk_hex is not 64 lowercase hex"
    if not _is_hex(ev["event_hash"], 64):
        return "event_hash is not 64 lowercase hex"
    if not (isinstance(ev["signature_hex"], str) and _is_hex(ev["signature_hex"])):
        return "signature_hex is not hex"
    # nested claim: must parse as an EdgeClaim; a parse error is a named
    # refusal, not a TypeError leaking out of replay.
    if not isinstance(ev["claim"], dict):
        return "claim is not an object"
    try:
        EdgeClaim.from_dict(ev["claim"])
    except Exception as e:
        return f"malformed claim: {type(e).__name__}: {e}"
    return None


def replay(journal: list, trust: TrustConfig, expected_root: str, expected_tip: str) -> dict:
    """Confirm the chain from the tip back to index 0, re-auditing every claim's
    content. Returns a structured result; the confirmed region is reported, not
    silently truncated."""
    verifier = WarrantVerifier(trust)
    result = {"confirmed_through_index": -1, "boundary": None,
              "verdicts": [], "root_matches": None, "tip_matches": None,
              "chain_ok": True, "accepted": False, "root": None, "tip": None}
    # Top-level type gate BEFORE any traversal: a valid JSON scalar, bool,
    # null, or object is not a journal. Without this, `enumerate(journal)` /
    # `journal[0]` raised instead of returning a named refusal.
    if not isinstance(journal, list):
        result["chain_ok"] = False
        result["boundary"] = f"journal is not a list of events (got {type(journal).__name__})"
        return result
    if not journal:
        result["chain_ok"] = False
        result["boundary"] = "empty journal (a list with no events)"
        return result

    # Structure and profile are validated for EVERY event before any field is
    # read for root/tip -- otherwise a malformed event (e.g. a missing
    # event_hash) raises instead of returning a named refusal.
    for i, ev in enumerate(journal):
        struct = _structure_reason(ev, i)
        if struct is not None:
            result["chain_ok"] = False
            result["boundary"] = f"index {i}: {struct}"
            return result

    result["root"] = journal[0]["event_hash"]
    result["tip"] = journal[-1]["event_hash"]
    result["root_matches"] = (result["root"] == expected_root)
    result["tip_matches"] = (result["tip"] == expected_tip)

    prev = GENESIS_PREV
    for i, ev in enumerate(journal):
        # Structure and profile were validated for every event in the pre-pass
        # above, so here we only re-derive bytes, chain, signature, and content.
        core = {k: ev[k] for k in _CORE_ORDER}
        try:
            cb = canonical_core_bytes(core)
        except Exception as e:
            result["chain_ok"] = False; result["boundary"] = f"index {i}: bad core: {e}"; break
        if hashlib.sha256(cb).hexdigest() != ev["event_hash"]:
            result["chain_ok"] = False; result["boundary"] = f"index {i}: event_hash mismatch"; break
        if ev["prev_event_hash"] != prev:
            result["chain_ok"] = False; result["boundary"] = f"index {i}: broken prev link"; break
        try:
            ok_sig = crypto.verify_bytes(bytes.fromhex(ev["author_pk_hex"]), cb,
                                         bytes.fromhex(ev["signature_hex"]))
        except Exception:
            ok_sig = False
        if not ok_sig:
            result["chain_ok"] = False; result["boundary"] = f"index {i}: bad signature"; break
        # re-audit the CONTENT (not just APPLY): CLAIM, COUNTEREXAMPLE, REFINE.
        # Structure was validated in the pre-pass; guard anyway so no exception
        # can escape the structured-refusal contract.
        try:
            claim = EdgeClaim.from_dict(ev["claim"])
            got = verifier.audit_claim(claim).status.value.upper()
        except Exception as e:
            result["chain_ok"] = False
            result["boundary"] = f"index {i}: audit raised {type(e).__name__}: {e}"
            break
        result["verdicts"].append(got)
        if got != ev["expected_verdict"]:
            result["chain_ok"] = False
            result["boundary"] = f"index {i}: verdict {got} != recorded {ev['expected_verdict']}"
            break
        result["confirmed_through_index"] = i
        prev = ev["event_hash"]
    # Acceptance is not internal consistency alone: the reader must have
    # SELECTED this history (root) and be seeing it COMPLETE (tip). Either pin
    # wrong => not accepted, even if the chain is internally sound.
    result["accepted"] = bool(result["chain_ok"]
                              and result["root_matches"]
                              and result["tip_matches"])
    return result


def linkage_ok(journal: list) -> dict:
    """Verify the C1-C3 relations, not three independent claims."""
    checks = {}
    kinds = [ev["kind"] for ev in journal]
    checks["order"] = kinds == ["CLAIM", "COUNTEREXAMPLE", "REFINE"]
    checks["indices"] = [ev["index"] for ev in journal] == [0, 1, 2]
    b1, b2, b3 = (ev["claim"]["body"] for ev in journal)
    # C2 targets the same (reference, candidate) as C1, witness outside C1 fixtures
    checks["c2_same_pair"] = (b2["omega"] == b1["omega"] and b2["tau"] == b1["tau"])
    checks["c2_witness_outside"] = (
        b2["witness"]["input_expr"] not in b1["witness"]["fixtures"])
    # C3 keeps reference, corrects candidate, extends fixtures by the witness
    checks["c3_same_reference"] = (b3["omega"] == b1["omega"])
    checks["c3_candidate_changed"] = (b3["tau"] != b1["tau"])
    checks["c3_fixtures_extend"] = (
        set(b1["witness"]["fixtures"]) | {b2["witness"]["input_expr"]}
        == set(b3["witness"]["fixtures"]))
    checks["all"] = all(v for k, v in checks.items() if k != "all")
    return checks


# --------------------------------------------------------------------------- #
# Controls (§4) -- each must fail closed
# --------------------------------------------------------------------------- #
def _resign_event(core_plus: dict) -> dict:
    """Rebuild event_hash + signature for a mutated core (honest re-signing with
    the fixture author key). Used only to build adversarial fixtures whose bytes
    are internally consistent, so the refusal must come from a real check."""
    core = {k: core_plus[k] for k in _CORE_ORDER}
    cb = canonical_core_bytes(core)
    return {**core, "event_hash": hashlib.sha256(cb).hexdigest(),
            "signature_hex": crypto.sign_bytes(AUTHOR_SK, cb).hex()}


def run_controls() -> dict:
    trust = caller_trust()
    verifier = WarrantVerifier(trust)
    out = {}

    # substitution -- caller trust root: a claim by a non-trusted author
    foreign = build_c1(sk=FOREIGN_SK, pk=FOREIGN_PK)
    out["foreign_author_unverified"] = (
        verifier.audit_claim(foreign).status == VerificationStatus.UNVERIFIED)

    # substitution -- recycled witness: a witness whose fixtures_fingerprint is
    # LIFTED from C1 (over FIXTURES_C1) but whose actual fixtures are the wider
    # set incl. K, attached to the buggy candidate K I. The fingerprint binding
    # must reject the mismatch rather than trust the recycled fingerprint.
    recycled_w = EmpiricalWitness(fixtures=list(FIXTURES_C3), fixtures_fingerprint="",
                                  delta_atp=0, delta_size=0)
    lifted = EmpiricalWitness(fixtures=list(FIXTURES_C1), fixtures_fingerprint="",
                              delta_atp=0, delta_size=0)
    recycled_w.fixtures_fingerprint = lifted.compute_fixtures_fingerprint()  # from C1
    ph = glyph.term_hash(glyph.parse(REFERENCE)); sh = glyph.term_hash(glyph.parse(f"{K} {I}"))
    recycled = EdgeClaim.create_and_sign(ph, f"{K} {I}", REFERENCE, sh,
                                         Polarity.AFFIRM, recycled_w, AUTHOR_SK.hex(), AUTHOR_PK)
    out["recycled_witness_not_pass"] = (
        verifier.audit_claim(recycled).status != VerificationStatus.PASS)

    # non-termination: a grounded claim that does not settle -> UNVERIFIED
    from warrant_kernel import GroundedWitness
    nonterm = f"{S} {I} {I} ({S} {I} {I})"
    gw = GroundedWitness(term_expr=nonterm,
                         expected_hash=glyph.evaluate(glyph.parse(nonterm), max_atp=100).hash,
                         atp_budget=100)
    ph = glyph.term_hash(glyph.parse(nonterm))
    gclaim = EdgeClaim.create_and_sign(ph, nonterm, nonterm, ph, Polarity.AFFIRM,
                                       gw, AUTHOR_SK.hex(), AUTHOR_PK)
    out["nonterminating_unverified"] = (
        verifier.audit_claim(gclaim).status == VerificationStatus.UNVERIFIED)

    # history tamper: flip a byte of C1's recorded verdict; replay must stop at 0
    journal = build_journal()
    tampered = [dict(ev) for ev in journal]
    tampered[0] = dict(tampered[0], expected_verdict="FAIL")   # not re-signed
    rep = replay(tampered, trust, journal[0]["event_hash"], journal[-1]["event_hash"])
    out["tamper_breaks_replay"] = (rep["confirmed_through_index"] < 0 and not rep["chain_ok"])

    # broken prev-link, RE-SIGNED: re-point event 1's prev to genesis and
    # recompute its hash+signature so only the chain link is wrong. The
    # event_hash attests the recorded prev value, not that it matches the real
    # predecessor, so this must still be refused as a chain break.
    relinked = [dict(ev) for ev in journal]
    relinked[1] = _resign_event({**journal[1], "prev_event_hash": GENESIS_PREV})
    rep_l = replay(relinked, trust, journal[0]["event_hash"], relinked[-1]["event_hash"])
    out["broken_prev_link_refused"] = (rep_l["confirmed_through_index"] == 0
                                       and "prev" in (rep_l["boundary"] or ""))

    # unsupported profile, RE-SIGNED across all events with matching root/tip:
    # a valid signature over an unsupported format is not acceptance.
    reprofiled = []
    prev = GENESIS_PREV
    for ev in journal:
        r = _resign_event({**ev, "profile": "unsupported.v99", "prev_event_hash": prev})
        reprofiled.append(r); prev = r["event_hash"]
    rep_p = replay(reprofiled, trust, reprofiled[0]["event_hash"], reprofiled[-1]["event_hash"])
    out["unsupported_profile_refused"] = (not rep_p["chain_ok"]
                                          and "profile" in (rep_p["boundary"] or ""))

    # pinned root/tip gate acceptance: a foreign expected root is NOT accepted
    rep_root = replay(journal, trust, "00" * 32, journal[-1]["event_hash"])
    out["wrong_root_not_accepted"] = (rep_root["chain_ok"] and not rep_root["accepted"])

    out["all"] = all(out.values())
    return out


# --------------------------------------------------------------------------- #
# Full experiment report (R1 / R2 / R3 kept separate)
# --------------------------------------------------------------------------- #
def loop_success(recorded: list, rep: dict) -> bool:
    """Loop success is the specific expected PASS x3, both RECORDED and
    REPRODUCED by replay. A recorded UNVERIFIED that replay reproduces is a
    faithfully-recorded refusal, never loop success -- so the replayed verdicts
    are a required conjunct, not decoration."""
    return (recorded == ["PASS", "PASS", "PASS"]
            and rep.get("verdicts") == ["PASS", "PASS", "PASS"]
            and rep.get("chain_ok") is True
            and rep.get("confirmed_through_index") == 2)


# --------------------------------------------------------------------------- #
# R2: external-anchor reader (docs/EXP-LIB-001-R2.md rev 3)
# --------------------------------------------------------------------------- #
# opentimestamps is an OPTIONAL, offline-only dependency: it is imported lazily
# INSIDE verify_external_anchor so the module (and the zero-dependency CI) never
# require it. When it is absent the reader reports NOT_DEMONSTRATED, exactly as
# the profile §3 allows ("no OTS profile available"). R2 tests skip when it is
# not importable; R1/loop/linkage/controls/determinism do not depend on it.

_R2_STATES = ("NOT_DEMONSTRATED", "REFUSED", "PENDING",
              "ANCHORED_UNVERIFIED", "CONFIRMED")


def _r2_result(state, *, commitment_sha256=None, proof_sha256=None,
               pending_calendars=None, bitcoin_attestations=None,
               time_verified=False, calendar_authenticity_verified=False,
               accepted_source="none", network_calls=0, reason=None):
    assert state in _R2_STATES, state
    return {
        "state": state,
        "commitment_sha256": commitment_sha256,
        "proof_sha256": proof_sha256,
        "pending_calendars": pending_calendars or [],
        "bitcoin_attestations": bitcoin_attestations or [],
        "time_verified": time_verified,
        "calendar_authenticity_verified": calendar_authenticity_verified,
        "accepted_source": accepted_source,
        "network_calls": network_calls,
        "reason": reason,
    }


def _source_name(accepted_source):
    """The report's `accepted_source` field is a NAME (profile §4/§7), or 'none'.
    None -> 'none'; a well-formed source names itself; a malformed one is named
    but yields no confirmation (its roots are simply never matched)."""
    if accepted_source is None:
        return "none"
    if isinstance(accepted_source, dict):
        name = accepted_source.get("name")
        if isinstance(name, str) and name:
            return name
    return "unnamed-source"


def verify_external_anchor(commitment, ots_proof, accepted_source=None):
    """R2 reader (docs/EXP-LIB-001-R2.md rev 3). Fully OFFLINE: zero network
    calls, always. Given the pinned root `commitment` (exactly 32 raw bytes),
    the detached `ots_proof` bytes, and an OPTIONAL reader-pinned
    `accepted_source`, return the §3 state and §4 flags. It NEVER raises on
    adversarial input -- a malformed or non-binding proof is the named result
    REFUSED, distinct from absent (NOT_DEMONSTRATED) and from PENDING.

    accepted_source, when given, is the reader's own pinned Bitcoin data source
    (§7):
        {"name": <str>, "block_merkle_roots": {<int height>: <hex str>}}
    where each hex value is the exact bytes the OTS Bitcoin attestation commits
    to (i.e. `msg.hex()`). Without it CONFIRMED is unreachable: at most
    ANCHORED_UNVERIFIED. Supplying it is never by itself a confirmation -- an
    attestation must actually match a pinned (height, root).
    """
    src_name = _source_name(accepted_source)
    commit_ok = isinstance(commitment, (bytes, bytearray)) and len(commitment) == 32
    commitment_sha256 = (hashlib.sha256(bytes(commitment)).hexdigest()
                         if commit_ok else None)
    proof_sha256 = (hashlib.sha256(ots_proof).hexdigest()
                    if isinstance(ots_proof, (bytes, bytearray)) else None)

    # 1. No proof at all -> NOT_DEMONSTRATED (never REFUSED, never PENDING).
    if ots_proof is None:
        return _r2_result("NOT_DEMONSTRATED", commitment_sha256=commitment_sha256,
                          accepted_source=src_name,
                          reason="no proof supplied")

    # 2. No OTS profile available on this host -> NOT_DEMONSTRATED (§3).
    try:
        from opentimestamps.core.timestamp import DetachedTimestampFile
        from opentimestamps.core.serialize import BytesDeserializationContext
        from opentimestamps.core.notary import (PendingAttestation,
                                                 BitcoinBlockHeaderAttestation)
    except Exception:
        return _r2_result("NOT_DEMONSTRATED", commitment_sha256=commitment_sha256,
                          proof_sha256=proof_sha256, accepted_source=src_name,
                          reason="no OTS profile available (opentimestamps not importable)")

    # 3. A proof was supplied: from here a failure is REFUSED, not absent.
    if not commit_ok:
        return _r2_result("REFUSED", proof_sha256=proof_sha256,
                          accepted_source=src_name,
                          reason="commitment is not exactly 32 raw bytes")
    if not isinstance(ots_proof, (bytes, bytearray)):
        return _r2_result("REFUSED", commitment_sha256=commitment_sha256,
                          accepted_source=src_name,
                          reason="proof is not raw bytes")
    try:
        detached = DetachedTimestampFile.deserialize(
            BytesDeserializationContext(bytes(ots_proof)))
    except Exception as e:
        return _r2_result("REFUSED", commitment_sha256=commitment_sha256,
                          proof_sha256=proof_sha256, accepted_source=src_name,
                          reason=f"proof did not parse: {type(e).__name__}")

    # 4. Binding: the proof must commit to SHA256(our 32 raw bytes) (§2). A
    #    proof over any other bytes -- or double-hashed, or a different file --
    #    does not bind THIS commitment and is REFUSED, not silently accepted.
    expected_leaf = hashlib.sha256(bytes(commitment)).digest()
    if detached.timestamp.msg != expected_leaf:
        return _r2_result("REFUSED", commitment_sha256=commitment_sha256,
                          proof_sha256=proof_sha256, accepted_source=src_name,
                          reason="proof does not bind the commitment "
                                 "(leaf != SHA256 of the 32 root bytes)")

    # 5. Classify the attestations the (now bound) proof carries.
    pending = []
    bitcoin = []
    for msg, att in detached.timestamp.all_attestations():
        if isinstance(att, PendingAttestation):
            uri = att.uri
            if isinstance(uri, bytes):
                uri = uri.decode("utf-8", "replace")
            pending.append(uri)
        elif isinstance(att, BitcoinBlockHeaderAttestation):
            bitcoin.append({"height": att.height, "merkle_root": msg.hex()})
    pending = sorted(pending)
    bitcoin = sorted(bitcoin, key=lambda b: (b["height"], b["merkle_root"]))

    # Defensive: a bound proof carrying NO attestation evidences no time.
    # The OTS serializer refuses to emit an attestation-less timestamp, so this
    # is unreachable from standard .ots bytes -- kept as a fail-closed guard,
    # not claimed as a tested state (never PENDING, which needs a calendar).
    if not pending and not bitcoin:
        return _r2_result("REFUSED", commitment_sha256=commitment_sha256,
                          proof_sha256=proof_sha256, accepted_source=src_name,
                          reason="proof binds the commitment but carries no attestations")

    # 6. No Bitcoin attestation yet -> PENDING (calendar commitments only).
    if not bitcoin:
        return _r2_result("PENDING", commitment_sha256=commitment_sha256,
                          proof_sha256=proof_sha256, pending_calendars=pending,
                          accepted_source=src_name,
                          reason="calendar commitments only; no Bitcoin attestation yet")

    # 7. Bitcoin attestation present. Confirmation requires an accepted source
    #    (§4): a present attestation is NEVER reported CONFIRMED on its own.
    matched = False
    if isinstance(accepted_source, dict):
        roots = accepted_source.get("block_merkle_roots")
        if isinstance(roots, dict):
            for b in bitcoin:
                pinned = roots.get(b["height"])
                if pinned is None:
                    # tolerate string-keyed maps from e.g. JSON
                    pinned = roots.get(str(b["height"]))
                if isinstance(pinned, str) and pinned.lower() == b["merkle_root"]:
                    matched = True
                    break

    if matched:
        return _r2_result("CONFIRMED", commitment_sha256=commitment_sha256,
                          proof_sha256=proof_sha256, pending_calendars=pending,
                          bitcoin_attestations=bitcoin, time_verified=True,
                          calendar_authenticity_verified=False,
                          accepted_source=src_name, network_calls=0,
                          reason="Bitcoin attestation verified against the accepted, "
                                 "reader-pinned source (offline)")

    # 8. Attestation present but not verified against an accepted source: the
    #    adjacent negative (source given but no match) lands here too.
    return _r2_result("ANCHORED_UNVERIFIED", commitment_sha256=commitment_sha256,
                      proof_sha256=proof_sha256, pending_calendars=pending,
                      bitcoin_attestations=bitcoin, time_verified=False,
                      calendar_authenticity_verified=False,
                      accepted_source=src_name, network_calls=0,
                      reason=("no accepted source pinned; chain time not established"
                              if accepted_source is None else
                              "accepted source did not match any Bitcoin attestation"))


def run_experiment() -> dict:
    journal = build_journal()
    root, tip = journal[0]["event_hash"], journal[-1]["event_hash"]
    recorded = [ev["expected_verdict"] for ev in journal]
    rep = replay(journal, caller_trust(), root, tip)
    links = linkage_ok(journal)
    controls = run_controls()

    loop_ok = loop_success(recorded, rep)

    # determinism: rebuild from scratch, compare bytes
    determinism_ok = journal_to_bytes(build_journal()) == journal_to_bytes(journal)

    return {
        "loop": {"recorded": recorded, "replayed": rep["verdicts"], "ok": loop_ok},
        "R1_local_replay": {
            "accepted": rep["accepted"],
            "chain_ok": rep["chain_ok"],
            "confirmed_through_index": rep["confirmed_through_index"],
            "oldest_confirmed_ancestor_index": 0 if rep["chain_ok"] else None,
            "root_matches": rep["root_matches"], "tip_matches": rep["tip_matches"],
            "boundary": rep["boundary"], "root": root, "tip": tip},
        "linkage": links,
        "controls": controls,
        "R2_external_anchor": {"status": "NOT_DEMONSTRATED",
                               "reason": "no proof supplied to this run; the "
                                         "reader is verify_external_anchor "
                                         "(docs/EXP-LIB-001-R2.md)"},
        "R3_publication": {"status": "NOT_RELEASED",
                           "note": "DOI is publication only, not provenance; gated on §9"},
        "determinism_ok": determinism_ok,
    }


def main():
    import pprint
    report = run_experiment()
    print("%🖤 EXP-LIB-001 — living-library experiment report\n")
    pprint.pprint(report, sort_dicts=False, width=100)
    ok = (report["loop"]["ok"] and report["R1_local_replay"]["accepted"]
          and report["linkage"]["all"] and report["controls"]["all"]
          and report["determinism_ok"])
    print("\nR1 (replay), loop, linkage, controls, determinism:",
          "ALL CONFIRMED" if ok else "NOT CONFIRMED")
    print("R2 (external anchor):", report["R2_external_anchor"]["status"])
    print("R3 (publication):", report["R3_publication"]["status"])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
