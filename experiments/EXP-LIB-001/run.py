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
# R1: replay to the oldest reachable confirmed ancestor
# --------------------------------------------------------------------------- #
def replay(journal: list, trust: TrustConfig, expected_root: str, expected_tip: str) -> dict:
    """Confirm the chain from the tip back to index 0, re-auditing every claim's
    content. Returns a structured result; the confirmed region is reported, not
    silently truncated."""
    verifier = WarrantVerifier(trust)
    result = {"confirmed_through_index": -1, "boundary": None,
              "verdicts": [], "root_matches": None, "tip_matches": None,
              "chain_ok": True, "root": None, "tip": None}
    if not journal:
        result["chain_ok"] = False
        result["boundary"] = "empty journal"
        return result

    result["root"] = journal[0]["event_hash"]
    result["tip"] = journal[-1]["event_hash"]
    result["root_matches"] = (result["root"] == expected_root)
    result["tip_matches"] = (result["tip"] == expected_tip)

    prev = GENESIS_PREV
    for i, ev in enumerate(journal):
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
        # re-audit the CONTENT (not just APPLY): CLAIM, COUNTEREXAMPLE, REFINE
        claim = EdgeClaim.from_dict(ev["claim"])
        got = verifier.audit_claim(claim).status.value.upper()
        result["verdicts"].append(got)
        if got != ev["expected_verdict"]:
            result["chain_ok"] = False
            result["boundary"] = f"index {i}: verdict {got} != recorded {ev['expected_verdict']}"
            break
        result["confirmed_through_index"] = i
        prev = ev["event_hash"]
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
            "chain_ok": rep["chain_ok"],
            "confirmed_through_index": rep["confirmed_through_index"],
            "oldest_confirmed_ancestor_index": 0 if rep["chain_ok"] else None,
            "root_matches": rep["root_matches"], "tip_matches": rep["tip_matches"],
            "boundary": rep["boundary"], "root": root, "tip": tip},
        "linkage": links,
        "controls": controls,
        "R2_external_anchor": {"status": "NOT_DEMONSTRATED",
                               "reason": "no OTS profile available in this run"},
        "R3_publication": {"status": "NOT_RELEASED",
                           "note": "DOI is publication only, not provenance; gated on §9"},
        "determinism_ok": determinism_ok,
    }


def main():
    import pprint
    report = run_experiment()
    print("%🖤 EXP-LIB-001 — living-library experiment report\n")
    pprint.pprint(report, sort_dicts=False, width=100)
    ok = (report["loop"]["ok"] and report["R1_local_replay"]["chain_ok"]
          and report["linkage"]["all"] and report["controls"]["all"]
          and report["determinism_ok"])
    print("\nR1 (replay), loop, linkage, controls, determinism:",
          "ALL CONFIRMED" if ok else "NOT CONFIRMED")
    print("R2 (external anchor):", report["R2_external_anchor"]["status"])
    print("R3 (publication):", report["R3_publication"]["status"])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
