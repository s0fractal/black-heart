#!/usr/bin/env python3
"""
double_ledger.py — Verification of the Two-Channel Rule (Chat vs File).
Part of Project Black-Heart (%🖤), implementing CHORD-CAPSULE-0.1 §2.

Rule:
  A statement a model makes to the owner in chat that it also records in a file
  MUST be the same capsule in both — byte-identical after canonical JSON — or
  a chat capsule carrying `abridged_of: <digest>` that resolves to the file capsule.

Verdicts per pair:
  MATCH                 chat digest == file digest
  ABRIDGED_OK           chat capsule has abridged_of -> resolves to file capsule
  SUBSTITUTED           same claim_ref, different digest, no abridged_of (DEFECT)
  ABRIDGEMENT_DANGLING  abridged_of does not resolve to any known file capsule
  ORPHAN_CHAT           spoken in chat, never written to file
  SPEAKER_MISMATCH      speaker.declared != speaker.observed
"""

from __future__ import annotations
import json
import os
import sys
import re
import hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

@dataclass
class Capsule:
    claim_ref: str
    body: Dict[str, Any]
    canonical_bytes: bytes
    digest: str
    channel: str  # "chat" or "file"
    source_file: str
    line_number: int
    abridged_of: Optional[str] = None
    speaker_declared: Optional[str] = None
    speaker_observed: Optional[str] = None

def canonical_digest(obj: Dict[str, Any]) -> Tuple[bytes, str]:
    """Sort keys, no whitespace, UTF-8 encoded SHA-256."""
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    d = hashlib.sha256(raw).hexdigest()
    return raw, d

def extract_capsules_from_text(text: str, filename: str, default_channel: str = "file") -> List[Capsule]:
    """
    Extracts fenced ```json capsule ... ``` blocks from markdown / transcript text.
    Reads capsule fences only: emits ids and digests, never prose.
    """
    capsules = []
    pattern = re.compile(r"```json\s+capsule\s*\n(.*?)\n```", re.DOTALL)

    for match in pattern.finditer(text):
        content = match.group(1).strip()
        line_no = text[:match.start()].count("\n") + 1
        try:
            parsed = json.loads(content)
        except Exception as e:
            continue

        if not isinstance(parsed, dict) or "claim_ref" not in parsed:
            continue

        claim_ref = str(parsed["claim_ref"])
        channel = parsed.get("channel", default_channel)
        abridged_of = parsed.get("abridged_of")

        sp = parsed.get("speaker")
        sp_decl = sp.get("declared") if isinstance(sp, dict) else None
        sp_obs = sp.get("observed") if isinstance(sp, dict) else None

        raw, digest = canonical_digest(parsed)

        capsules.append(Capsule(
            claim_ref=claim_ref,
            body=parsed,
            canonical_bytes=raw,
            digest=digest,
            channel=channel,
            source_file=filename,
            line_number=line_no,
            abridged_of=abridged_of,
            speaker_declared=sp_decl,
            speaker_observed=sp_obs
        ))

    return capsules

@dataclass
class AuditVerdict:
    claim_ref: str
    verdict: str  # MATCH, ABRIDGED_OK, SUBSTITUTED, ABRIDGEMENT_DANGLING, ORPHAN_CHAT
    chat_digest: Optional[str]
    file_digest: Optional[str]
    notes: str = ""

def audit_double_ledger(chat_capsules: List[Capsule], file_capsules: List[Capsule]) -> List[AuditVerdict]:
    """
    Cross-checks chat capsules against file capsules.
    """
    file_by_ref: Dict[str, Capsule] = {c.claim_ref: c for c in file_capsules}
    file_by_digest: Dict[str, Capsule] = {c.digest: c for c in file_capsules}
    verdicts = []

    for chat in chat_capsules:
        ref = chat.claim_ref
        file_match = file_by_ref.get(ref)

        # Check speaker mismatch finding
        speaker_note = ""
        if chat.speaker_declared and chat.speaker_observed and chat.speaker_declared != chat.speaker_observed:
            speaker_note = f" [SPEAKER_MISMATCH: declared={chat.speaker_declared} != observed={chat.speaker_observed}]"

        if not file_match:
            verdicts.append(AuditVerdict(
                claim_ref=ref,
                verdict="ORPHAN_CHAT",
                chat_digest=chat.digest[:12],
                file_digest=None,
                notes=f"Spoken in chat ({chat.source_file}:{chat.line_number}), never written to file" + speaker_note
            ))
            continue

        # File capsule exists
        if chat.digest == file_match.digest:
            verdicts.append(AuditVerdict(
                claim_ref=ref,
                verdict="MATCH",
                chat_digest=chat.digest[:12],
                file_digest=file_match.digest[:12],
                notes="Byte-identical canonical JSON" + speaker_note
            ))
        elif chat.abridged_of:
            # Check abridgement pointer
            target_digest = chat.abridged_of
            if target_digest == file_match.digest or target_digest in file_by_digest:
                verdicts.append(AuditVerdict(
                    claim_ref=ref,
                    verdict="ABRIDGED_OK",
                    chat_digest=chat.digest[:12],
                    file_digest=file_match.digest[:12],
                    notes=f"Abridged of {target_digest[:12]}; resolves to file capsule" + speaker_note
                ))
            else:
                verdicts.append(AuditVerdict(
                    claim_ref=ref,
                    verdict="ABRIDGEMENT_DANGLING",
                    chat_digest=chat.digest[:12],
                    file_digest=file_match.digest[:12],
                    notes=f"Pointer {target_digest} does not resolve to any file capsule" + speaker_note
                ))
        else:
            # Same claim_ref, different digest, no abridged_of -> SUBSTITUTED defect!
            verdicts.append(AuditVerdict(
                claim_ref=ref,
                verdict="SUBSTITUTED",
                chat_digest=chat.digest[:12],
                file_digest=file_match.digest[:12],
                notes="DEFECT: Same claim_ref with mutated content and no abridged_of pointer" + speaker_note
            ))

    return verdicts

def print_audit_report(verdicts: List[AuditVerdict]):
    print("\n" + "=" * 75)
    print("  DOUBLE LEDGER AUDIT REPORT: CHAT vs FILE (CHORD-CAPSULE-0.1 §2)")
    print("=" * 75)
    print(f"{'CLAIM REF':<25} {'VERDICT':<20} {'CHAT DIGEST':<14} {'FILE DIGEST':<14}")
    print("-" * 75)

    defects = 0
    for v in verdicts:
        cd = v.chat_digest or "-"
        fd = v.file_digest or "-"
        color = "\033[1;32m" if v.verdict in ("MATCH", "ABRIDGED_OK") else "\033[1;31m"
        reset = "\033[0m"
        if v.verdict == "SUBSTITUTED":
            defects += 1

        print(f"{v.claim_ref:<25} {color}{v.verdict:<20}{reset} {cd:<14} {fd:<14}")
        if v.notes:
            print(f"   ↳ {v.notes}")

    print("-" * 75)
    if defects == 0:
        print("\033[1;32m[✓ OK] No concept substitutions detected across channels.\033[0m")
    else:
        print(f"\033[1;31m[✗ DEFECT] Found {defects} SUBSTITUTED claims between chat and file!\033[0m")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    # Self-test demonstration
    chat_sample = """
Here is what I am proposing to the owner:
```json capsule
{
  "schema": "manifesto.chord-capsule.v0",
  "claim_ref": "c1-absorption",
  "binding": {"relation": "measures", "target": "K drops second argument"},
  "channel": "chat"
}
```
And here is an abridged pointer:
```json capsule
{
  "schema": "manifesto.chord-capsule.v0",
  "claim_ref": "c2-spore",
  "abridged_of": "dummy-file-digest",
  "channel": "chat"
}
```
"""

    file_sample = """
Formal repository file:
```json capsule
{
  "schema": "manifesto.chord-capsule.v0",
  "claim_ref": "c1-absorption",
  "binding": {"relation": "measures", "target": "K drops second argument"},
  "channel": "chat"
}
```
```json capsule
{
  "schema": "manifesto.chord-capsule.v0",
  "claim_ref": "c2-spore",
  "binding": {"relation": "instantiates", "target": "S K K normalizes to I"},
  "channel": "file"
}
```
"""
    chat_caps = extract_capsules_from_text(chat_sample, "chat_session_01.md", default_channel="chat")
    file_caps = extract_capsules_from_text(file_sample, "proof.myc.md", default_channel="file")

    # Fixup abridged_of to match dummy file digest for demo
    chat_caps[1].abridged_of = file_caps[1].digest

    verdicts = audit_double_ledger(chat_caps, file_caps)
    print_audit_report(verdicts)
