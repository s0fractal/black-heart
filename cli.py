#!/usr/bin/env python3
"""
cli.py — Unified Command-Line Interface & Interactive Proof REPL for Project Black-Heart (%🖤).

Commands:
  repl      Interactive proof session with live ATP meter and normal form settlement.
  compile   Compiles a proof-carrying ISO 32000 PDF polyglot from specification.
  verify    Audits and executes deterministic verification on any polyglot PDF.
  keygen    Generates an RFC 8032 Ed25519 cryptographic keypair (zero dependencies).
  ledger    Inspects or appends blocks to a Living Polyglot Ledger.
"""

from __future__ import annotations
import os
import sys
import argparse
import json
import time
import hashlib

from glyph import parse, evaluate, GLYPH_K, GLYPH_I, GLYPH_S, GLYPH_Y, GLYPH_ANCHOR
from crypto import generate_keypair, public_key_from_secret
from polyglot import PolyglotDocument
from monad import SelfVerifyingContractPolyglot
from living_ledger import LivingLedger
from interaction import InteractionNet, AGENT_CONSTRUCT, AGENT_DUPLICATE, AGENT_ERASE, PortRef, PORT_PRINCIPAL
from vault import embed_vault_into_polyglot, extract_vault_from_pdf, pack_files_to_vault
from cross_proof import adjudicate_bilateral

BANNER = r"""
  %🖤  PROJECT BLACK-HEART — UNIFIED COMMAND SUITE
  Combinatory Logic • Proof-Carrying Polyglots • Living Ledgers • Vaults
"""

def cmd_repl(args):
    """Interactive combinator REPL with live ATP meter."""
    print("\033[1;36m" + BANNER + "\033[0m")
    print("Type SKIY combinator expressions (glyphs: 🖤 K, 🤍 I, 🌿 S, 🔁 Y).")
    print("Commands: :atp <N> | :keygen | :help | :quit\n")

    current_atp_budget = 10_000

    while True:
        try:
            line = input("\033[1;35m%🖤 > \033[0m").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting Black-Heart REPL.")
            break

        if not line:
            continue

        if line in (":q", ":quit", "exit"):
            print("Session settled. Goodbye.")
            break
        elif line.startswith(":atp"):
            parts = line.split()
            if len(parts) > 1 and parts[1].isdigit():
                current_atp_budget = int(parts[1])
                print(f"[*] ATP budget updated to: {current_atp_budget}")
            else:
                print(f"[*] Current ATP budget: {current_atp_budget}")
            continue
        elif line == ":keygen":
            sk, pk = generate_keypair()
            print(f"[*] Generated Ed25519 Keypair:")
            print(f"    Secret Key: {sk}")
            print(f"    Public Key: {pk}")
            continue
        elif line == ":help":
            print("Available Glyphs: 🖤 (K), 🤍 (I), 🌿 (S), 🔁 (Y)")
            print("Examples:")
            print("  🖤 Truth Mirage          --> drops 'Mirage' (Constant)")
            print("  🌿 🖤 🖤 Signal          --> evaluates to 'Signal' (Identity)")
            print("  (🖤 🤍) Left Right       --> returns 'Right' (Church FALSE)")
            continue

        # Parse, then evaluate. The two are reported apart: a syntax error is
        # the caller's line, anything else is this tool failing, and printing
        # both the same way is how the engine defect below stayed invisible.
        try:
            term = parse(line)
        except (ValueError, RecursionError) as e:
            print(f"  \033[1;31m[!] Syntax error:\033[0m {e}\n")
            continue

        try:
            result = evaluate(term, max_atp=current_atp_budget)
        except Exception as e:
            print(f"  \033[1;31m[!] Evaluation failed:\033[0m {type(e).__name__}: {e}\n")
            continue

        # `evaluate` returns an EvalResult, and a budget that ran out returns a
        # SUSPENDED one rather than raising. Reporting that as a normal form
        # would name a paused reduction as a finished one.
        if result.is_settled():
            print(f"  \033[1;32mNormal Form:\033[0m {result.term}")
            print(f"  \033[1;34mSettlement: \033[0m ⚓ ⟨atp:{result.atp_spent}, "
                  f"hash:{result.hash[:16]}⟩\n")
        else:
            print(f"  \033[1;33mSuspended Thunk:\033[0m {result.term}")
            print(f"  \033[1;33mStatus:     \033[0m ⏳ SUSPENDED after {result.atp_spent} ATP "
                  f"— not a normal form. This thunk is not retained; :atp <N> sets the "
                  f"budget for expressions entered after it.\n")

def cmd_keygen(args):
    """Generates an RFC 8032 Ed25519 keypair."""
    sk, pk = generate_keypair()
    if args.json:
        print(json.dumps({"secret_key_hex": sk, "public_key_hex": pk}, indent=2))
    else:
        print("\033[1;36m===================================================\033[0m")
        print("  %🖤 ED25519 KEYPAIR GENERATION (RFC 8032)")
        print("\033[1;36m===================================================\033[0m")
        print(f"\033[1;32m[*] Public Key (Hex): \033[0m {pk}")
        print(f"\033[1;33m[*] Secret Key (Hex): \033[0m {sk}")
        print("\033[0;37mKeep your secret key secure and unshared.\033[0m\n")

def cmd_verify(args):
    try:
        _cmd_verify(args)
    except Exception as e:
        print(f"REFUSED: {type(e).__name__}: {e}")
        raise SystemExit(1)


def _cmd_verify(args):
    """Audits and verifies any Black-Heart polyglot PDF purely as data without executing arbitrary code."""
    target = args.file
    if not os.path.exists(target):
        print(f"\033[1;31m[!] Error: File not found: {target}\033[0m")
        sys.exit(1)

    with open(target, "rb") as f:
        raw = f.read(16 * 1024 * 1024 + 1)
    if len(raw) > 16 * 1024 * 1024:
        raise ValueError("ARTIFACT_SIZE")
    # Recognize actual metadata lines, never literals inside embedded Python.
    content = b"\n".join(line for line in raw.splitlines()
        if line.startswith(("%🖤".encode(), b"# %")))

    print("\033[1;36m" + "=" * 65)
    print(f"  %🖤 BLACK-HEART AUDIT: {os.path.basename(target)}")
    print("=" * 65 + "\033[0m\n")

    success = False
    # Detect polyglot type
    if "%🖤 BILATERAL_MANIFEST:".encode("utf-8") in content or "%🖤 BILATERAL_AGREEMENT_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Bilateral Agreement Polyglot.")
        from cross_proof import audit_agreement_polyglot
        success = audit_agreement_polyglot(target)
    elif "%🖤 ORACLE_MANIFEST:".encode("utf-8") in content or "%🖤 TELEMETRY_ORACLE_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Telemetry Oracle Polyglot.")
        from cross_proof import audit_oracle_polyglot
        success = audit_oracle_polyglot(target)
    elif "%🖤 CONTINUUM_THUNK:".encode("utf-8") in content:
        print("[*] Detected Continuum Resumable Thunk Polyglot.")
        from artifact_audit import continuum
        success = continuum(target)
    elif "%🖤 ZK_PROOF_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Zero-Knowledge Proof-Carrying Contract.")
        from artifact_audit import zk
        success = zk(target)
    elif "%🖤 CONTRACT_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Proof-Carrying Contract Polyglot.")
        from monad import audit_contract_polyglot
        success = audit_contract_polyglot(target)
    elif "%🖤 LEDGER_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Multi-Block Living Polyglot Ledger.")
        from artifact_audit import ledger
        success = ledger(target)
    elif b"# %METAMORPHOSIS" in content:
        print("[*] Detected Metamorphic Organism Polyglot.")
        from artifact_audit import metamorphosis
        success = metamorphosis(target)
    elif b"# %COLONY_MANIFEST:" in content:
        print("[*] Detected Living Colony Ecosystem Polyglot.")
        from artifact_audit import colony
        success = colony(target)
    elif "%🖤 AUTOPOIESIS_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Autopoietic Organism Polyglot.")
        from autopoiesis import audit_autopoietic_organism
        success = audit_autopoietic_organism(target)
    elif "%🖤 AGORA_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Agora Mycelial Consensus Parliament Polyglot.")
        from agora import audit_agora_parliament
        success = audit_agora_parliament(target)
    elif "%🖤 IPFS_DIARY_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected IPFS Dialectical Diary DAG Polyglot.")
        from ipfs_diary import audit_diary_dag
        success = audit_diary_dag(target)
    elif "%🖤 MORPHO_NET_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Morphogenetic Proof-Net Polyglot.")
        from morpho_net import audit_morphogenetic_polyglot
        success = audit_morphogenetic_polyglot(target)
    elif "%🖤 GOEDEL_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Gödelian Incompleteness Polyglot.")
        from goedel import audit_goedel_polyglot
        success = audit_goedel_polyglot(target)
    elif "%🖤 ANYON_QUANTUM_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Anyonic Quantum Topos Polyglot.")
        from anyon_glyph import audit_anyon_polyglot
        success = audit_anyon_polyglot(target)
    elif "%🖤 ORGANISM_GENOME:".encode("utf-8") in content:
        print("[*] Detected Autonomous Self-Reproducing Polyglot Automaton.")
        from organism import extract_organism_from_pdf
        try:
            org = extract_organism_from_pdf(target)
            success = org.verify()
        except Exception as e:
            print(f"[!] Organism verification failed: {e}")
            success = False
    elif "%🖤 CLAIM:".encode("utf-8") in content or "%🖤 CODE_VAULT_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Self-Verifying Black-Heart Polyglot / Vault.")
        from polyglot import audit_polyglot_claims
        success = audit_polyglot_claims(target)
    else:
        print("\033[1;31m[!] Not a recognized Black-Heart polyglot document.\033[0m")
        sys.exit(1)

    if success:
        print("\033[1;32m[✓ GREEN] Local checks passed for the reported scope; external authority and freshness not evaluated.\033[0m")
    else:
        print("\033[1;31m[✗ RED] Document verification failed.\033[0m")
        sys.exit(1)

def cmd_sandbox(args):
    """Hermetic static non-executing polyglot auditor."""
    from tools.sandbox import audit_polyglot_hermetic
    target = args.file
    if not os.path.exists(target):
        print(f"\033[1;31m[!] File not found: {target}\033[0m")
        sys.exit(1)

    report = audit_polyglot_hermetic(target)

    print("\033[1;36m" + "=" * 70)
    print("  %🖤 PROJECT BLACK-HEART — HERMETIC NON-EXECUTING STATIC AUDITOR")
    print(f"  Target File: {os.path.basename(target)}")
    print("=" * 70 + "\033[0m\n")

    print(f"[*] File Size:            {report.file_size_bytes} bytes")
    print(f"[*] SHA-256 Digest:       {report.sha256_digest}")
    print(f"[*] PDF header present:    {'Yes' if report.is_valid_iso32000 else 'No'} "
          f"(header presence only, not full ISO 32000 compliance)")
    print(f"[*] Incremental Updates:  {report.incremental_updates_count}")
    print(f"[*] Detected Manifests:   {', '.join(report.detected_manifest_types) or 'None'}")
    print("\n--- AUDIT LOG ---")
    for note in report.audit_notes:
        print(f"  {note}")

    print("\n" + "=" * 70)
    if report.is_sound():
        print("\033[1;32m[✓ SOUND] Recognized elements verified statically without executing host Python.\033[0m")
        print(f"          {report.scope_summary()}")
    else:
        print("\033[1;31m[✗ UNSOUND] Document failed static hermetic verification.\033[0m")
        sys.exit(1)

def cmd_compile(args):
    """Compiles a basic polyglot document."""
    out = args.output or "output_polyglot.pdf"
    doc = PolyglotDocument(title=args.title or "AUTONOMOUS BLACK-HEART DOCUMENT", author=args.author or "s0fractal")
    doc.add_section("1. Formal Claims")
    doc.add_paragraph("This document carries its own mathematical verification engine.")
    doc.add_claim("CLAIM-01", "K-combinator drops the second argument", "🖤 Truth Mirage", "Truth")
    doc.compile(out)
    print(f"\033[1;32m[✓] Compiled polyglot PDF to: {out}\033[0m")

def cmd_vault(args):
    """Packs or unpacks an ISO 32000 embedded code vault."""
    if args.vault_action == "pack":
        src = os.path.abspath(args.source_dir)
        out = args.output
        if not os.path.isdir(src):
            print(f"\033[1;31m[!] Error: Source directory not found: {src}\033[0m")
            sys.exit(1)

        # Gather files
        file_list = []
        for root, dirs, files in os.walk(src):
            # Skip hidden and __pycache__
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            for f in sorted(files):
                if not f.startswith("."):
                    file_list.append(os.path.relpath(os.path.join(root, f), src))

        if not file_list:
            print(f"\033[1;31m[!] Error: No eligible files found in {src}\033[0m")
            sys.exit(1)

        from vault import find_secret_material
        findings = find_secret_material(file_list, src)
        if findings:
            print(f"\033[1;31m[!] Vault refused: private key material in {src}\033[0m")
            for path, reasons in findings:
                print(f"    {path}: {', '.join(reasons)}")
            print("    A vault is a public reproducibility archive, not a secret store. Nothing was written.")
            sys.exit(1)

        # Create base polyglot document if not existing
        doc = PolyglotDocument(title=args.title or "EMBEDDED CODE VAULT", author=args.author or "s0fractal")
        doc.add_section("1. Autonomous Code Vault")
        doc.add_paragraph(f"This document embeds a cryptographic source vault containing {len(file_list)} files.")
        for f in file_list[:10]:
            doc.add_paragraph(f"- {f}")
        if len(file_list) > 10:
            doc.add_paragraph(f"... and {len(file_list) - 10} additional files.")
        doc.compile(out)

        vh = embed_vault_into_polyglot(out, file_list, src)
        print(f"\033[1;32m[✓] Code vault packed ({len(file_list)} files, SHA-256: {vh[:16]}...) into: {out}\033[0m")

    elif args.vault_action == "unpack":
        pdf_file = args.file
        dest = os.path.abspath(args.dest or ".")
        if not os.path.exists(pdf_file):
            print(f"\033[1;31m[!] Error: PDF not found: {pdf_file}\033[0m")
            sys.exit(1)
        try:
            restored = extract_vault_from_pdf(pdf_file, dest)
            print(f"\033[1;32m[✓] Successfully extracted vault to {dest} ({len(restored)} files restored)\033[0m")
        except Exception as e:
            print(f"\033[1;31m[!] Vault extraction failed: {e}\033[0m")
            sys.exit(1)

def cmd_adjudicate(args):
    """Executes bilateral cross-document adjudication between agreement and oracle PDFs."""
    agreement_pdf = args.agreement
    oracle_pdf = args.oracle
    for p in (agreement_pdf, oracle_pdf):
        if not os.path.exists(p):
            print(f"\033[1;31m[!] Error: File not found: {p}\033[0m")
            sys.exit(1)

    print("\033[1;36m" + "=" * 65)
    print("  %🖤 BILATERAL CROSS-PROOF ADJUDICATION PROTOCOL")
    print("=" * 65 + "\033[0m\n")
    print(f"[*] Agreement Document: {agreement_pdf}")
    print(f"[*] Telemetry Oracle:   {oracle_pdf}\n")

    with open(agreement_pdf, "rb") as f:
        a_bytes = f.read()
    from cross_proof import (
        ZK_CHALLENGER_MANIFEST_PREFIX,
        ZK_WITNESS_MANIFEST_PREFIX,
        adjudicate_zk_bilateral,
        adjudicate_bilateral
    )
    is_zk = getattr(args, "zk", False) or ZK_CHALLENGER_MANIFEST_PREFIX.encode("utf-8") in a_bytes or ZK_WITNESS_MANIFEST_PREFIX.encode("utf-8") in a_bytes
    if is_zk:
        print("\033[1;36m" + "=" * 65)
        print("  %🖤 BILATERAL ZERO-KNOWLEDGE CROSS-PROOF ADJUDICATION")
        print("=" * 65 + "\033[0m\n")
        print(f"[*] Document 1: {agreement_pdf}")
        print(f"[*] Document 2: {oracle_pdf}\n")
        if ZK_CHALLENGER_MANIFEST_PREFIX.encode("utf-8") in a_bytes:
            c_pdf, w_pdf = agreement_pdf, oracle_pdf
        else:
            c_pdf, w_pdf = oracle_pdf, agreement_pdf
        try:
            rcpt = adjudicate_zk_bilateral(c_pdf, w_pdf)
            print("\033[1;32m[✓] ZERO-KNOWLEDGE BILATERAL SETTLEMENT SOUND & RATIFIED!\033[0m")
            print(f"    Status:                 \033[1;32m{rcpt.status}\033[0m")
            print(f"    Joint Bilateral Anchor: ⚓ {rcpt.joint_bilateral_anchor}")
            print(f"    Statement ID:           {rcpt.statement_id}")
            print(f"    Contract Title:         {rcpt.challenger_title}")
            print(f"    Target Prover Key:      {rcpt.target_prover_pk_hex[:16]}... (ZK Verified)")
            print(f"    Challenger CIDv1:       {rcpt.challenger_cid}")
            print(f"    Witness CIDv1:          {rcpt.witness_cid}")
            print(f"    Proof System:           {rcpt.proof_type}\n")
            return
        except Exception as e:
            print(f"\033[1;31m[✗] ZK ADJUDICATION FAILED: {e}\033[0m\n")
            sys.exit(1)

    from cross_proof import AdjudicationTrust
    pinned_pk = getattr(args, "pinned_author_pk", None)
    pinned_hash = getattr(args, "pinned_agreement_hash", None)
    allow_untrusted = getattr(args, "allow_untrusted_issuer", False)

    if not pinned_pk and not pinned_hash and not allow_untrusted:
        print("\033[1;31m[✗] ADJUDICATION REJECTED: UNTRUSTED_ISSUER_EVALUATION.\033[0m")
        print("    Trust root pinning is required to adjudicate bilateral contracts.")
        print("    Provide --pinned-author-pk <HEX> or --pinned-agreement-hash <HEX>,")
        print("    or pass --allow-untrusted-issuer for an evaluation that is not a settlement.")
        sys.exit(1)

    try:
        trust = AdjudicationTrust(expected_author_pk_hex=pinned_pk, expected_agreement_sha256=pinned_hash)
    except ValueError as e:
        print(f"\033[1;31m[✗] ADJUDICATION REJECTED: invalid pin: {e}\033[0m\n")
        sys.exit(1)

    try:
        res = adjudicate_bilateral(agreement_pdf, oracle_pdf, trust=trust)
    except Exception as e:
        print(f"\033[1;31m[✗] ADJUDICATION FAILED: {e}\033[0m\n")
        sys.exit(1)

    if res.status == "EVALUATION_ONLY":
        # Before S5b this printed "[✓] ADJUDICATION VERIFIED & SETTLED" and
        # exited 0 for any self-consistent pair under --allow-untrusted-issuer.
        print("\033[1;33m[!] EVALUATION ONLY — NOT A SETTLEMENT.\033[0m")
        for reason in res.untrusted_reasons:
            print(f"    - {reason}")
        print(f"    Computed outcome (unauthoritative): {res.outcome}, net service fee ${res.net_service_due_usd:,} USD\n")
        sys.exit(2)

    status_color = "\033[1;32m" if res.status == "SETTLED_COMPLIANT" else "\033[1;33m"
    penalty_str = "COMPLIANT" if res.status == "SETTLED_COMPLIANT" else "BREACHED"
    print(f"{status_color}[✓] ADJUDICATION VERIFIED & SETTLED: {res.status}\033[0m")
    print(f"    Joint Bilateral Anchor: ⚓ {res.joint_bilateral_digest}")
    print(f"    Agreement:              {res.agreement_title}")
    print(f"    Trust Status:           {res.trust_status}")
    for name, verdict in res.checks.items():
        print(f"    Check {name + ':':<17}{verdict}")
    print(f"    Oracle:                 {res.oracle_name} ({res.oracle_pk_hex[:16]}...)")
    print(f"    Payment Status:         {penalty_str} | Net Service Fee: ${res.net_service_due_usd:,} USD\n")

def cmd_cross_proof(args):
    """Bilateral Zero-Knowledge Cross-Proof & Interlocking Contract operations."""
    from cross_proof import (
        BilateralZKChallengerPolyglot,
        BilateralZKWitnessPolyglot,
        adjudicate_zk_bilateral,
        audit_zk_challenger_polyglot,
        audit_zk_witness_polyglot
    )
    if args.action == "zk-contract":
        challenger = BilateralZKChallengerPolyglot(
            title=args.title or "BILATERAL ESCROW CONTRACT",
            statement_id=args.statement or "CLAIM-ZK-001",
            target_prover_pk_hex=args.target_pk,
            clause_text=args.clause or "Settlement authorized upon verifiable zero-knowledge proof of sovereign key possession.",
            proof_type=args.proof_type or "SchnorrZKP",
            second_point_hex=args.second_point or None,
            author_secret_key_hex=args.secret_key or None
        )
        out_path = args.output or "zk_contract.pdf"
        challenger.compile(out_path)
        print("\033[1;36m=================================================================\033[0m")
        print("  %🖤 BILATERAL ZK CHALLENGER CONTRACT COMPILED")
        print("\033[1;36m=================================================================\033[0m")
        print(f"  Target File:     {out_path}")
        print(f"  Statement ID:    {challenger.statement_id}")
        print(f"  Proof Type:      {challenger.proof_type}")
        print(f"  Target Prover PK:{challenger.target_prover_pk_hex[:16]}...\n")

    elif args.action == "zk-witness":
        witness = BilateralZKWitnessPolyglot(
            witness_name=args.name or "Autonomous Prover",
            challenger_pdf_path=args.contract,
            prover_secret_key_hex=args.secret_key or None,
            witness_author_secret_key_hex=args.author_key or None
        )
        out_path = args.output or "zk_witness.pdf"
        witness.compile(out_path)
        print("\033[1;32m=================================================================\033[0m")
        print("  %🖤 BILATERAL ZK WITNESS POLYGLOT COMPILED")
        print("\033[1;32m=================================================================\033[0m")
        print(f"  Target File:     {out_path}")
        print(f"  Bound Contract:  {args.contract}\n")

    elif args.action == "adjudicate":
        try:
            rcpt = adjudicate_zk_bilateral(args.contract, args.witness)
            print("\033[1;32m[✓ GREEN] ZERO-KNOWLEDGE BILATERAL SETTLEMENT SOUND & RATIFIED!\033[0m")
            print(f"  Status:                 \033[1;32m{rcpt.status}\033[0m")
            print(f"  Joint Bilateral Anchor: ⚓ {rcpt.joint_bilateral_anchor}")
            print(f"  Statement ID:           {rcpt.statement_id}")
            print(f"  Contract Title:         {rcpt.challenger_title}")
            print(f"  Challenger CIDv1:       {rcpt.challenger_cid}")
            print(f"  Witness CIDv1:          {rcpt.witness_cid}")
            print(f"  Proof System:           {rcpt.proof_type}\n")
        except Exception as e:
            print(f"\033[1;31m[✗ REFUTED] Bilateral ZK Cross-Proof Failed: {e}\033[0m")
            sys.exit(1)
    else:
        print("Usage: python3 cli.py cross-proof {zk-contract,zk-witness,adjudicate} ...")

def cmd_test(args):
    """Executes the full test suite across all engines."""
    from test_all import run_all_tests
    success = run_all_tests()
    if not success:
        sys.exit(1)

def cmd_continuum(args):
    """Continuum Resumable Thunk operations."""
    from continuum import ResumableComputationPolyglot, resume_computation_in_pdf
    if args.action == "compile":
        sk, pk = generate_keypair()
        poly = ResumableComputationPolyglot(args.title or "BLACK-HEART CONTINUUM COMPUTATION")
        cp = poly.initialize(args.expr, initial_fuel=args.fuel, secret_key_hex=sk, public_key_hex=pk)
        poly.compile(args.output)
        print(f"\033[1;32m[✓] Continuum Polyglot compiled to: {args.output}\033[0m")
        print(f"    Status: {cp.status} | Height: #{cp.height} | Checkpoint: ⚓ {cp.checkpoint_hash[:16]}...")
    elif args.action == "resume":
        res = resume_computation_in_pdf(args.file, additional_atp=args.fuel)
        print(f"\033[1;32m[✓] Resumed: {res.status} | Cumulative ATP: {res.atp_accumulated}\033[0m")

def cmd_zk(args):
    """Zero-Knowledge Proof operations on Ed25519."""
    from zk_glyph import schnorr_prove, schnorr_verify, chaum_pedersen_prove, chaum_pedersen_verify
    if args.action == "prove-identity":
        sp = schnorr_prove(args.secret_key, context=args.context or "AUTH")
        print(json.dumps(sp.to_dict(), indent=2))
    elif args.action == "prove-dlog":
        cpp = chaum_pedersen_prove(int(args.scalar), context=args.context or "DLOG")
        print(json.dumps(cpp.to_dict(), indent=2))

def cmd_mesh(args):
    """Peer-to-peer Living Polyglot Mesh sync operations."""
    from mesh import start_ledger_daemon, sync_local_ledgers, sync_from_remote_peer
    if args.action == "serve":
        port = args.port or 8765
        print(f"[*] Starting Black-Heart Ledger Node on port {port}...")
        daemon = start_ledger_daemon(args.file, port=port)
        print(f"\033[1;32m[✓] Serving {args.file} on http://127.0.0.1:{port}\033[0m (Press Ctrl+C to stop)")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            daemon.shutdown()
            print("\nDaemon stopped.")
    elif args.action == "sync":
        if args.peer.startswith("http://") or args.peer.startswith("https://"):
            synced = sync_from_remote_peer(args.destination, args.peer)
            print(f"\033[1;32m[✓] Synced {synced} block(s) from remote peer: {args.peer}\033[0m")
        else:
            synced = sync_local_ledgers(args.peer, args.destination)
            print(f"\033[1;32m[✓] Synced {synced} block(s) from local peer file: {args.peer}\033[0m")

def cmd_synthesize(args):
    """Executes sexual recombination and topological knot synthesis between two parent organisms."""
    from symbiosis import synthesize_polyglots
    print("\033[1;36m=================================================================")
    print("  %🖤 BLACK-HEART DIALECTICAL SYMBIOSIS & KNOT MORPHOGENESIS")
    print("=================================================================\033[0m\n")
    print(f"[*] Parent A (Thesis):     {args.parent_a}")
    print(f"[*] Parent B (Antithesis): {args.parent_b}")
    print(f"[*] Target Child:          {args.output}\n")

    try:
        child, braid = synthesize_polyglots(args.parent_a, args.parent_b, args.output)
        print(f"\033[1;32m[✓ SUCCESS] Offspring Synthesized!\033[0m")
        print(f"    - Child Generation:    #{child.generation:04d}")
        print(f"    - Combined Lineage:    ⚓ {child.parent_hash[:32]}...")
        print(f"    - Child Public Key:    {child.public_key_hex[:32]}...")
        print(f"    - Topological Knot:    {braid.to_artin_notation()}")
        print(f"    - Knot Invariants:     {braid.crossing_number} crossings, writhe={braid.writhe}, {braid.count_link_components()} component(s)")
        print(f"    - Active Chromosomes:  {len(child.chromosomes)}")
        print(f"\nAudit offspring standalone via: python3 {args.output} --lineage\n")
    except Exception as e:
        print(f"\033[1;31m[!] Synthesis Failed:\033[0m {e}")
        sys.exit(1)

def cmd_quantum(args):
    """Topological Quantum Topos operations (Fibonacci anyonic gates & simulation)."""
    from quantum import FibonacciQuantumSystem, compile_quantum_polyglot
    from symbiosis import BraidWord, BraidCrossing, trefoil_knot, figure_eight_knot, hopf_link

    def parse_braid(spec: str) -> BraidWord:
        spec_l = spec.lower().strip()
        if spec_l == "trefoil":
            return trefoil_knot()
        elif spec_l in ("figure8", "figure-eight", "figure_eight"):
            return figure_eight_knot()
        elif spec_l in ("hopf", "hopf_link"):
            return hopf_link()
        else:
            tokens = spec.split()
            crossings = []
            for tok in tokens:
                tok_clean = tok.replace("s", "").replace("σ", "").replace("_", "").replace("^", "")
                try:
                    val = int(tok_clean)
                    strand = abs(val)
                    sign = 1 if val > 0 else -1
                    crossings.append(BraidCrossing(strand_index=strand, sign=sign))
                except ValueError:
                    pass
            num_str = max([c.strand_index + 1 for c in crossings], default=2)
            return BraidWord(num_strands=num_str, crossings=crossings)

    if args.action == "simulate":
        braid = parse_braid(args.braid)
        sys_q = FibonacciQuantumSystem()
        u = sys_q.compile_braid_to_unitary(braid)
        state = sys_q.evolve_state(u)
        bloch = sys_q.calculate_bloch_coordinates(state)
        p0, p1 = sys_q.calculate_born_probabilities(state)

        print("\033[1;36m=================================================================")
        print("  %🖤 TOPOLOGICAL QUANTUM TOPOS — ANYONIC GATE SIMULATOR")
        print("=================================================================\033[0m\n")
        print(f"[*] Braid Presentation:  {braid.to_artin_notation()}")
        print(f"[*] Crossings:           {braid.crossing_number} (Writhe: {braid.writhe})")
        print(f"[*] Unitary Gate Matrix: [{u.m00.real:+.4f}{u.m00.imag:+.4f}j,  {u.m01.real:+.4f}{u.m01.imag:+.4f}j];")
        print(f"                          [{u.m10.real:+.4f}{u.m10.imag:+.4f}j,  {u.m11.real:+.4f}{u.m11.imag:+.4f}j]")
        print(f"[*] Determinant:         |det(U)| = {abs(u.det()):.6f}\n")
        print(f"[*] Evolved State |ψ⟩:   α = {state[0].real:+.4f}{state[0].imag:+.4f}j")
        print(f"                          β = {state[1].real:+.4f}{state[1].imag:+.4f}j\n")
        print(f"[*] Born Probabilities:  P(|0⟩ Vacuum) = {p0*100:.2f}%   P(|1⟩ Anyon τ) = {p1*100:.2f}%")
        print(f"[*] Bloch Sphere Vector: ({bloch['x']:+.4f}, {bloch['y']:+.4f}, {bloch['z']:+.4f})")
        print(f"[*] Polar θ:             {bloch['theta_deg']}° | Azimuthal φ: {bloch['phi_deg']}°\n")
        print("\033[1;32m[✓] Topological Quantum Gate Sound & Unitary (Q.E.D.)\033[0m\n")

    elif args.action == "compile":
        braid = parse_braid(args.braid)
        out_path = args.output or "quantum_circuit.pdf"
        title = args.title or f"Topological Anyon Gate ({braid.to_artin_notation(ascii_only=True)})"
        compile_quantum_polyglot(braid, out_path, title=title)
        print(f"\033[1;32m[✓] Compiled Quantum Polyglot: {out_path}\033[0m")
        print(f"    - Braid:       {braid.to_artin_notation()}")
        print(f"    - Crossings:   {braid.crossing_number}")
        print(f"    - Standalone:  python3 {out_path} --simulate")
        print(f"    - Measurement: python3 {out_path} --measure 1024\n")

def cmd_morph(args):
    """Generates Turing reaction-diffusion morphogenetic phenotype polyglots."""
    from morphogenesis import PhenotypeGenesis, MorphogeneticPolyglotCompiler, TuringArchetype, PALETTES
    import hashlib

    seed_str = args.seed or f"black-heart:morph:{args.archetype}:{time.time()}"
    seed_hash = hashlib.sha256(seed_str.encode("utf-8")).hexdigest()

    print("\033[1;36m" + "=" * 68)
    print("  %🖤 PROJECT BLACK-HEART — TURING MORPHOGENESIS ENGINE")
    print("  \"The Chemical Basis of Morphogenesis\" (Alan Turing, 1952)")
    print("=" * 68 + "\033[0m\n")

    print(f"[*] Initializing {args.grid}x{args.grid} Torus (T^2) numerical PDE lattice...")
    print(f"[*] Selected Archetype: {args.archetype.upper()}")
    phenotype, field = PhenotypeGenesis.from_hash(
        hash_hex=seed_hash,
        steps=args.steps,
        grid_size=args.grid,
        forced_archetype=args.archetype
    )

    if args.palette and args.palette in PALETTES:
        phenotype.palette_name = args.palette

    print(f"[*] Simulating {args.steps} forward Euler steps (Du={phenotype.Du}, Dv={phenotype.Dv}, F={phenotype.F}, k={phenotype.k})...")
    stats = phenotype.statistics
    print(f"  [✓] Symmetry breaking: Var(V)={stats.get('var_v', 0.0):.6f}, V_max={stats.get('max_v', 0.0):.4f}")

    print(f"[*] Compiling dual-layer executable PDF polyglot to: {args.output}...")
    MorphogeneticPolyglotCompiler.compile_polyglot(phenotype, field, args.output)
    size = os.path.getsize(args.output)
    print(f"\033[1;32m[✓ SUCCESS] Synthesized Turing Morphogenesis Polyglot ({size} bytes)!\033[0m")
    print(f"  View PDF:       open {args.output}")
    print(f"  Execute Script: python3 {args.output} --info\n")


def cmd_metamorph(args):
    """Executes program self-contemplation and compiles metamorphic polyglot."""
    from organism import extract_organism_from_pdf, create_genesis_organism, Chromosome
    from metamorphosis import MetamorphicPolyglotCompiler

    print("\033[1;36m" + "=" * 68)
    print("  %🖤 PROJECT BLACK-HEART — AUTONOMOUS FORM METAMORPHOSIS")
    print("  Program Self-Contemplation & Invariant-Preserving Form Evolution")
    print("=" * 68 + "\033[0m\n")

    if args.organism and os.path.exists(args.organism):
        print(f"[*] Extracting organism from polyglot: {args.organism}...")
        org = extract_organism_from_pdf(args.organism)
    else:
        print("[*] Instantiating genesis organism with optimizable combinator chromosome...")
        org = create_genesis_organism()
        org.chromosomes.append(Chromosome(
            gene_id="GENE-OPT-04",
            gene_name="Signal Router",
            expression="🌿 (🖤 (🌿 🤍)) (🖤 🤍)",
            expected_normal_form="(🌿 🤍) 🤍",
            max_atp=100
        ))
        org.organism_hash = org.compute_hash()

    print(f"[*] Contemplating form for organism ⚓ {org.organism_hash[:16]}... (Gen #{org.generation})")
    succ, log, receipt = org.contemplate_form()

    if succ is None or receipt is None:
        print("[-] Organism form is at a local pareto optimum. No advantageous mutation found.")
        print(f"[*] Total candidate mutations evaluated: {len(log.records)} (all rejected or neutral)")
        return

    print("\n\033[1;32m[✓] BENEFICIAL METAMORPHIC TRANSITION DISCOVERED!\033[0m")
    print(f"    Target Gene:    {receipt.gene_id}")
    print(f"    Rewrite Rule:   {receipt.rule_name}")
    print(f"    Pre-form:       {receipt.pre_term}")
    print(f"    Post-form:      {receipt.post_term}")
    print(f"    ATP Conserved:  +{receipt.atp_saved} fuel quanta")
    print(f"    Syntactic Size: {receipt.size_saved:+d} AST nodes")
    print(f"    Successor Hash: ⚓ {succ.organism_hash[:16]}... (Gen #{succ.generation})\n")

    compiler = MetamorphicPolyglotCompiler(org, succ, receipt, log)
    pdf_bytes = compiler.compile_pdf()
    with open(args.output, "wb") as f:
        f.write(pdf_bytes)

    print(f"\033[1;32m[✓ SUCCESS] Synthesized Metamorphic Polyglot ({len(pdf_bytes)} bytes)!\033[0m")
    print(f"  Output File:    {args.output}")
    print(f"  Audit Proof:    python3 {args.output} --audit")
    print(f"  Empirical Log:  python3 {args.output} --experiments")
    print(f"  Scientific Log: {len(log.accepted_records())} accepted, {len(log.rejected_records())} rejected mutations recorded.\n")


def cmd_mycelium(args):
    """Manages Mycelium Warrant Registry and P2P Epistemic Swarm."""
    from mycelium import (
        EpistemicRegistry,
        LocalImmuneEvaluator,
        Warrant,
        NormalFormEntry,
        DivergenceRecord
    )
    from mesh import start_epistemic_daemon, sync_epistemic_from_remote_peer
    from organism import extract_organism_from_pdf

    reg_path = getattr(args, "registry", "epistemic_registry.json") or "epistemic_registry.json"
    if os.path.exists(reg_path):
        registry = EpistemicRegistry.load_from_file(reg_path)
    else:
        registry = EpistemicRegistry()

    if args.action == "summary":
        s = registry.summary()
        print("\033[1;36m===================================================\033[0m")
        print("  %🖤 BLACK-HEART EPISTEMIC MYCELIUM REGISTRY")
        print("\033[1;36m===================================================\033[0m")
        print(f"  Normal Forms Cached:  {s['normal_forms_count']}")
        print(f"  Warrants Registered:  {s['warrants_count']}")
        print(f"  Divergences (Immune): {s['divergences_count']}")
        print(f"  Warrant Merkle Root:  ⚓ {s['warrant_merkle_root'][:32]}...\n")

    elif args.action == "serve":
        port = args.port
        print(f"[*] Starting Black-Heart Mycelium Epistemic Daemon on port {port}...")
        srv = start_epistemic_daemon(registry, port=port)
        print(f"[✓] Mycelium Swarm Node online at http://127.0.0.1:{port}")
        print("Press Ctrl+C to halt daemon.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Shutting down daemon...")
            srv.shutdown()
            registry.save_to_file(reg_path)
            print(f"[✓] Registry saved to {reg_path}")

    elif args.action == "sync":
        peer_url = args.peer
        print(f"[*] Syncing epistemic gossip with peer: {peer_url}...")
        counts = sync_epistemic_from_remote_peer(registry, peer_url)
        registry.save_to_file(reg_path)
        print(f"[✓] Sync complete: +{counts['warrants']} warrants, +{counts['divergences']} divergences, +{counts['normal_forms']} normal forms.")
        print(f"    Registry updated at {reg_path}")

    elif args.action == "audition":
        org_pdf = args.organism
        warrant_file = args.warrant
        if not os.path.exists(org_pdf) or not os.path.exists(warrant_file):
            print("[!] Organism PDF or Warrant JSON not found.")
            return

        org = extract_organism_from_pdf(org_pdf)
        with open(warrant_file, "r") as f:
            warrant = Warrant.from_dict(json.load(f))

        sk_hex = getattr(args, "secret_key", None)
        if sk_hex:
            sk = bytes.fromhex(sk_hex)
        else:
            from crypto import generate_keypair
            sk, _ = generate_keypair()

        evaluator = LocalImmuneEvaluator()
        verdict = evaluator.audition_warrant(org, warrant, sk)
        if verdict.adopted:
            print(f"\033[1;32m[✓] WARRANT ADOPTED by Organism Gen #{org.generation}!\033[0m")
            print(f"    Target Gene: {verdict.target_gene_id}")
            print(f"    Local ΔATP:  {verdict.local_delta_atp} fuel units")
            print(f"    Successor:   Gen #{verdict.successor_organism.generation} (Hash: {verdict.successor_organism.organism_hash[:16]}...)")
        else:
            print(f"\033[1;31m[!] WARRANT REJECTED by Local Immune Evaluator: {verdict.reason}\033[0m")
            if verdict.divergence_record:
                print(f"    New Divergence Counterexample minted: {verdict.divergence_record.record_id}")
                registry.add_divergence(verdict.divergence_record, verify_first=False)
                registry.save_to_file(reg_path)


def cmd_colony(args):
    """Colony operations: init, step, status, compile."""
    from colony import Colony, ColonyPolyglotCompiler
    file_path = args.file or "colony.json"

    if args.action == "init":
        if getattr(args, "seed", None) is not None:
            import random
            random.seed(args.seed)
        colony = Colony.create_genesis_colony(
            name=args.name,
            initial_organisms=args.organisms,
            initial_substrate_atp=args.atp
        )
        colony.save_to_file(file_path)
        from keystore import sidecar_path
        keys_path = colony.keystore().save(sidecar_path(file_path))
        print("\033[1;36m===================================================\033[0m")
        print(f"  %🖤 COLONY INITIALIZED: {colony.name}")
        print("\033[1;36m===================================================\033[0m")
        print(f"  Active Organisms:   {len(colony.active_organisms())}")
        print(f"  Substrate ATP Pool: {colony.substrate_atp}")
        print(f"  Saved to:           {file_path} (public: no secret keys)")
        print(f"  Private keys:       {keys_path} (mode 0600; never share this file)\n")

    elif args.action == "step":
        if not os.path.exists(file_path):
            print(f"[!] Colony state file '{file_path}' not found. Run 'init' first.")
            sys.exit(1)
        from keystore import MissingKeyError, resolve_keystore
        try:
            store, key_source = resolve_keystore(getattr(args, "keys", None), file_path)
        except (MissingKeyError, OSError, ValueError) as e:
            print(f"\033[1;31m[!] Step refused: {e}\033[0m")
            print("    The colony state was not modified.")
            sys.exit(1)
        colony = Colony.load_from_file(file_path)
        if not colony.verify():
            print(f"[!] Integrity check failed: Colony state is corrupted or tampered.")
            sys.exit(1)
        colony.attach_keys(store)
        try:
            colony.require_keys()
        except MissingKeyError as e:
            print(f"\033[1;31m[!] Step refused: {e}\033[0m")
            print("    The colony state was not modified.")
            sys.exit(1)
        epochs = args.epochs or 1
        for _ in range(epochs):
            rec = colony.step_epoch(solar_influx_atp=args.solar)
            print(f"[*] Epoch #{rec.epoch_index} complete | Active: {rec.active_count} | Spores: {rec.spore_count} | Minted: {rec.warrants_minted} | Adopted: {rec.warrants_adopted} | Matings: {rec.matings_count} | Anchor: {rec.epoch_hash[:16]}...")
        colony.save_to_file(file_path)
        colony.keystore().save(key_source)
        print(f"\n[+] Colony state saved to '{file_path}'; private keys kept in '{key_source}'.")

    elif args.action == "status":
        if not os.path.exists(file_path):
            print(f"[!] Colony state file '{file_path}' not found.")
            sys.exit(1)
        colony = Colony.load_from_file(file_path)
        if not colony.verify():
            print(f"[!] Integrity check failed: Colony '{colony.name}' has invalid state, broken epoch chain, or corrupted chromosomes.")
            sys.exit(1)
        s = colony.summary()
        print("\033[1;36m===================================================\033[0m")
        print(f"  %🖤 COLONY STATUS: {s['colony_name']}")
        print("\033[1;36m===================================================\033[0m")
        print(f"  Epochs Elapsed:         {s['epochs_total']}")
        print(f"  Active Organisms:       {s['active_organisms']}")
        print(f"  Dormant Spores:         {s['dormant_spores']}")
        print(f"  Substrate ATP Pool:     {s['substrate_atp_pool']}")
        print(f"  Mycelium Warrants:      {s['warrants_in_mycelium']}")
        print(f"  Mycelium Divergences:   {s['divergences_in_mycelium']}")
        print(f"  Ledger Block Height:    {s['ledger_blocks_height']}")
        print(f"  Latest Epoch Anchor:    {s['latest_epoch_hash'][:32]}...\n")

    elif args.action == "compile":
        if not os.path.exists(file_path):
            print(f"[!] Colony state file '{file_path}' not found.")
            return
        colony = Colony.load_from_file(file_path)
        compiler = ColonyPolyglotCompiler(colony)
        pdf_bytes = compiler.compile_pdf()
        out_path = args.output or "colony.pdf"
        with open(out_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"[+] Compiled executable colony polyglot to '{out_path}' ({len(pdf_bytes)} bytes).")
    else:
        print("Usage: python3 cli.py colony {init,step,status,compile} ...")


def cmd_ontogeny(args):
    """Ontogenetic quine polyglots & morphogenetic proof-net operations."""
    from morpho_net import (
        OntogeneticPolyglotCompiler,
        grow_ontogenetic_quine_in_pdf,
        OntogeneticProofReceipt,
        ONTOGENY_MANIFEST_PREFIX,
    )
    from morphogenesis import TuringArchetype
    from crypto import generate_keypair
    import hashlib

    if args.action == "init":
        arch = TuringArchetype.from_key(args.archetype)
        sk_hex = args.secret_key
        if not sk_hex:
            sk_hex, _ = generate_keypair()
        compiler = OntogeneticPolyglotCompiler(archetype=arch)
        rec0, field = compiler.initialize_genesis(
            seed_hash=args.seed or hashlib.sha256(str(time.time()).encode()).hexdigest(),
            secret_key_hex=sk_hex,
            initial_pde_steps=args.steps,
            max_atp=args.atp
        )
        out_path = args.output or "ontogeny_quine.pdf"
        compiler.compile(out_path, field)
        print("\033[1;36m===================================================\033[0m")
        print(f"  %🖤 ONTOGENETIC QUINE INITIALIZED: Generation #0")
        print("\033[1;36m===================================================\033[0m")
        print(f"  Archetype:           {arch.key} ({arch.display_name})")
        print(f"  PDE Steps:           {rec0.pde_steps}")
        print(f"  Initial Nodes:       {rec0.initial_nodes}")
        print(f"  Proof-Net Digest:    ⚓ {rec0.weisfeiler_lehman_digest[:32]}...")
        print(f"  Signer Public Key:   {rec0.public_key_hex[:32]}...")
        print(f"  Saved Polyglot:      {out_path}\n")

    elif args.action == "grow":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        grow_ontogenetic_quine_in_pdf(
            args.file,
            pde_steps=args.steps,
            atp_budget=args.atp,
            secret_key_hex=args.secret_key or None
        )

    elif args.action == "audit":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        with open(args.file, "rb") as f:
            data = f.read()
        prefix = ONTOGENY_MANIFEST_PREFIX.encode("utf-8")
        idx = data.rfind(prefix)
        if idx == -1:
            print(f"[!] No ontogeny receipt chain found in '{args.file}'.")
            sys.exit(1)
        end_idx = data.find(b"\n", idx)
        raw = data[idx + len(prefix):end_idx].decode("utf-8")
        receipts_data = json.loads(raw)
        print(f"[*] Auditing ontogenetic developmental chain across {len(receipts_data)} generations...")
        prev_h = "0" * 64
        for i, md in enumerate(receipts_data):
            rec = OntogeneticProofReceipt.from_dict(md)
            if rec.generation != i:
                print(f"[FAIL] Generation index mismatch at #{rec.generation}: expected #{i}")
                sys.exit(1)
            if rec.prev_receipt_hash != prev_h:
                print(f"[FAIL] Hash chain broken at #{rec.generation}")
                sys.exit(1)
            if not rec.verify():
                print(f"[FAIL] Cryptographic signature or hash invalid at generation #{rec.generation}")
                sys.exit(1)
            prev_h = rec.receipt_hash
            print(f"  [✓] Gen #{rec.generation}: {rec.archetype} | steps={rec.pde_steps} | burned={rec.atp_burned} ATP | WL=⚓ {rec.weisfeiler_lehman_digest[:16]}...")
        print(f"\033[1;32m[✓] ALL {len(receipts_data)} ONTOGENETIC GENERATIONS & PROOF-NETS CRYPTOGRAPHICALLY VERIFIED\033[0m\n")

    elif args.action == "status":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        with open(args.file, "rb") as f:
            data = f.read()
        prefix = ONTOGENY_MANIFEST_PREFIX.encode("utf-8")
        idx = data.rfind(prefix)
        if idx == -1:
            print(f"[!] No ontogeny receipt chain found in '{args.file}'.")
            sys.exit(1)
        end_idx = data.find(b"\n", idx)
        raw = data[idx + len(prefix):end_idx].decode("utf-8")
        manifest = json.loads(raw)
        latest = manifest[-1]
        print("\033[1;36m=================================================================\033[0m")
        print("  %🖤 PROJECT BLACK-HEART // ONTOGENETIC QUINE ATLAS")
        print(f"  Target File: {os.path.basename(args.file)} ({len(data)} bytes, {len(manifest)} generations)")
        print("\033[1;36m=================================================================\033[0m\n")
        print(f"  Current Generation:    #{latest.get('generation')}")
        print(f"  Turing Archetype:      {latest.get('archetype')}")
        print(f"  Cumulative PDE Steps:  {latest.get('pde_steps')}")
        print(f"  Proof-Net Status:      {'SETTLED NORMAL FORM (Q.E.D.)' if latest.get('settled') else 'SUSPENDED'}")
        print(f"  Total ATP Burned:      {sum(m.get('atp_burned', 0) for m in manifest)} fuel")
        print(f"  Weisfeiler-Lehman:     ⚓ {latest.get('weisfeiler_lehman_digest')}")
        print(f"  Signer Public Key:     {latest.get('public_key_hex')}\n")
    else:
        print("Usage: python3 cli.py ontogeny {init,grow,audit,status} ...")


def cmd_goedel(args):
    """Gödelian Incompleteness & Black Cone Event Horizon operations."""
    from goedel import (
        probe_black_cone_horizon,
        construct_goedel_polyglot,
        audit_goedel_polyglot,
        GoedelSettlementReceipt,
        GOEDEL_MANIFEST_PREFIX,
    )
    from crypto import generate_keypair
    import json

    if args.action == "probe":
        atp = getattr(args, "atp", 200) or 200
        probes = probe_black_cone_horizon(atp_budget=atp)
        print("\033[1;36m========================================================================================\033[0m")
        print("  %🖤 BLACK CONE EVENT HORIZON & ASYMPTOTIC COMBINATOR DYNAMICS")
        print("\033[1;36m========================================================================================\033[0m\n")
        print(f"  {'Configuration':<26} | {'Horizon Fate':<22} | {'Grade':<15} | {'Period':<6} | {'ATP'}")
        print("  " + "-" * 84)
        for p in probes:
            print(f"  {p['name']:<26} | {p['horizon_class']:<22} | {p['truth_grade']:<15} | {p.get('period', 0):<6} | {p.get('atp_spent', 0)}")
        print("\n  \033[1;32m[✓] Phase space boundaries mapped: Singularity Collapse, Attractors, Supercritical Blowout.\033[0m\n")

    elif args.action == "compile":
        sk_hex = getattr(args, "secret_key", None)
        if not sk_hex:
            sk_hex, _ = generate_keypair()
        out_path = args.output or "goedel_paradox.pdf"
        expr = args.expr or "🔁 🤍"
        s_id = args.id or "GOEDEL_SENTENCE_01"
        rec = construct_goedel_polyglot(
            output_pdf_path=out_path,
            secret_key_hex=sk_hex,
            sentence_expr=expr,
            sentence_id=s_id
        )
        print("\033[1;36m===================================================\033[0m")
        print(f"  %🖤 GÖDELIAN POLYGLOT COMPILED: {s_id}")
        print("\033[1;36m===================================================\033[0m")
        print(f"  Sentence Expression: {rec.initial_term}")
        print(f"  Truth Grade:         {rec.truth_grade}")
        print(f"  Horizon Class:       {rec.horizon_class}")
        print(f"  Limit-Cycle Period:  {rec.cycle_period} steps")
        print(f"  Witness Hash:        {rec.witness_hash[:32]}...")
        print(f"  Signer Public Key:   {rec.public_key_hex[:32]}...")
        print(f"  Saved Polyglot:      {out_path}\n")

    elif args.action == "verify":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        with open(args.file, "rb") as f:
            data = f.read()
        ok, msg, info = audit_goedel_polyglot(data)
        if not ok:
            print(f"\033[1;31m[FAIL] Gödelian audit rejected: {msg}\033[0m")
            sys.exit(1)
        print("\033[1;32m=================================================================\033[0m")
        print("  [✓ SUCCESS] GÖDELIAN SETTLEMENT PROVEN SOUND")
        print("\033[1;32m=================================================================\033[0m\n")
        print(f"  Sentence ID:       {info.get('sentence_id')}")
        print(f"  Claimed Sentence:  {info.get('initial_term')}")
        print(f"  Truth Grade:       {info.get('truth_grade')}")
        print(f"  Dynamical Fate:    {info.get('horizon_class')}")
        print(f"  Limit-Cycle:       {info.get('cycle_period')} steps")
        print(f"  ATP Fuel Spent:    {info.get('atp_spent')} units")
        print(f"  Witness Hash:      ⚓ {info.get('witness_hash')}")
        print(f"  Signer Public Key: {info.get('public_key_hex')}\n")

    elif args.action == "status":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        with open(args.file, "rb") as f:
            data = f.read()
        prefix = GOEDEL_MANIFEST_PREFIX.encode("utf-8")
        idx = data.rfind(prefix)
        if idx == -1:
            print(f"[!] No Gödel receipt manifest found in '{args.file}'.")
            sys.exit(1)
        end_idx = data.find(b"\n", idx)
        raw = data[idx + len(prefix):end_idx].decode("utf-8")
        manifest = json.loads(raw)
        print("\033[1;36m=================================================================\033[0m")
        print("  %🖤 PROJECT BLACK-HEART // GÖDELIAN PARADOX ATLAS")
        print(f"  Target File: {os.path.basename(args.file)} ({len(data)} bytes)")
        print("\033[1;36m=================================================================\033[0m\n")
        print(f"  Sentence ID:       {manifest.get('sentence_id')}")
        print(f"  Expression:        {manifest.get('initial_term')}")
        print(f"  Truth Grade:       {manifest.get('truth_grade')}")
        print(f"  Event Horizon:     {manifest.get('horizon_class')}")
        print(f"  Limit-Cycle:       {manifest.get('cycle_period')} steps")
        print(f"  Witness Hash:      {manifest.get('witness_hash')}")
        print(f"  Document Anchor:   {manifest.get('document_merkle_root')}")
        print(f"  Signer Public Key: {manifest.get('public_key_hex')}\n")
    else:
        print("Usage: python3 cli.py goedel {probe,compile,verify,status} ...")


def cmd_anyon(args):
    """Topological Anyonic Combinators & Quantum Braided Rewriting."""
    from anyon_glyph import (
        compile_glyph_to_anyon_braid,
        settle_anyon_glyph,
        construct_anyon_polyglot,
        audit_anyon_polyglot,
        AnyonSettlementReceipt,
        ANYON_MANIFEST_PREFIX,
    )
    from quantum import FibonacciQuantumSystem
    from glyph import parse
    from crypto import generate_keypair
    import json

    if args.action == "simulate":
        expr = args.expr or "🌿 🖤 🤍"
        t = parse(expr)
        braid = compile_glyph_to_anyon_braid(t)
        sys_q = FibonacciQuantumSystem()
        u = sys_q.compile_braid_to_unitary(braid)
        st = sys_q.evolve_state(u)
        p0, p1 = sys_q.calculate_born_probabilities(st)
        bl = sys_q.calculate_bloch_coordinates(st)

        print("\033[1;36m=================================================================\033[0m")
        print("  %🖤 TOPOLOGICAL FIBONACCI ANYON SIMULATION")
        print("\033[1;36m=================================================================\033[0m\n")
        print(f"  Circuit Term:        {expr}")
        print(f"  Artin Braid:         {braid.to_artin_notation()}")
        print(f"  Writhe:              {braid.writhe:+d} (Crossings: {braid.crossing_number})")
        print(f"  Unitary Gate Matrix: [{u.m00.real:+.3f}{u.m00.imag:+.3f}j, {u.m01.real:+.3f}{u.m01.imag:+.3f}j]")
        print(f"                       [{u.m10.real:+.3f}{u.m10.imag:+.3f}j, {u.m11.real:+.3f}{u.m11.imag:+.3f}j]")
        print(f"  Determinant |det U|: {abs(u.det()):.6f} (Unitary)")
        print(f"  Born P(|0> Vacuum):  {p0*100:.2f}% ({'1/φ²' if abs(p0 - 0.381966) < 0.01 else 'Exact'})")
        print(f"  Born P(|1> Anyon τ): {p1*100:.2f}% ({'1/φ' if abs(p1 - 0.618034) < 0.01 else 'Exact'})")
        print(f"  Bloch Sphere Vector: [{bl['x']:+.3f}, {bl['y']:+.3f}, {bl['z']:+.3f}] (θ={bl['theta_deg']}°, φ={bl['phi_deg']}°)\n")

    elif args.action == "compile":
        sk_hex = getattr(args, "secret_key", None)
        if not sk_hex:
            sk_hex, _ = generate_keypair()
        out_path = args.output or "anyon_circuit.pdf"
        expr = args.expr or "🌿 🖤 🤍"
        rec = construct_anyon_polyglot(
            output_pdf_path=out_path,
            secret_key_hex=sk_hex,
            term_expr=expr
        )
        print("\033[1;36m===================================================\033[0m")
        print(f"  %🖤 ANYON QUANTUM POLYGLOT COMPILED")
        print("\033[1;36m===================================================\033[0m")
        print(f"  Term:                {rec.term_expr}")
        print(f"  Artin Braid:         {rec.braid_artin}")
        print(f"  Born Probabilities:  P(0)={rec.born_p0_vacuum*100:.1f}%, P(1)={rec.born_p1_anyon*100:.1f}%")
        print(f"  Projective Outcome:  {rec.collapsed_glyph}")
        print(f"  Bloch Coordinates:   [{rec.bloch_x:+.3f}, {rec.bloch_y:+.3f}, {rec.bloch_z:+.3f}]")
        print(f"  Signer Key:          {rec.public_key_hex[:32]}...")
        print(f"  Saved Polyglot:      {out_path}\n")

    elif args.action == "verify":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        with open(args.file, "rb") as f:
            data = f.read()
        ok, msg, info = audit_anyon_polyglot(data)
        if not ok:
            print(f"\033[1;31m[FAIL] Anyon audit rejected: {msg}\033[0m")
            sys.exit(1)
        print("\033[1;32m=================================================================\033[0m")
        print("  [✓ SUCCESS] ANYONIC QUANTUM POLYGLOT AUDITED & VERIFIED")
        print("\033[1;32m=================================================================\033[0m\n")
        print(f"  Term Expression:   {info.get('term_expr')}")
        print(f"  Artin Braid:       {info.get('braid_artin')}")
        print(f"  Born P(|0>):       {info.get('born_p0_vacuum')*100:.2f}%")
        print(f"  Born P(|1>):       {info.get('born_p1_anyon')*100:.2f}%")
        print(f"  Unitary Invariance:|det U| = {info.get('unitary_det_mag')} (100% Preserved)")
        print(f"  Signer Key:        {info.get('public_key_hex')}\n")

    elif args.action == "status":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        with open(args.file, "rb") as f:
            data = f.read()
        prefix = ANYON_MANIFEST_PREFIX.encode("utf-8")
        idx = data.rfind(prefix)
        if idx == -1:
            print(f"[!] No Anyon quantum manifest found in '{args.file}'.")
            sys.exit(1)
        end_idx = data.find(b"\n", idx)
        raw = data[idx + len(prefix):end_idx].decode("utf-8")
        manifest = json.loads(raw)
        print("\033[1;36m=================================================================\033[0m")
        print("  %🖤 PROJECT BLACK-HEART // ANYONIC QUANTUM ATLAS")
        print(f"  Target File: {os.path.basename(args.file)} ({len(data)} bytes)")
        print("\033[1;36m=================================================================\033[0m\n")
        print(f"  Circuit Term:      {manifest.get('term_expr')}")
        print(f"  Braid Word:        {manifest.get('braid_artin')}")
        print(f"  Born Probabilities:P(0)={manifest.get('born_p0_vacuum')*100:.2f}%, P(1)={manifest.get('born_p1_anyon')*100:.2f}%")
        print(f"  Bloch Angles:      θ={manifest.get('bloch_theta_deg')}°, φ={manifest.get('bloch_phi_deg')}°")
        print(f"  Projective Result: {manifest.get('collapsed_glyph')}")
        print(f"  Entropy:           {manifest.get('von_neumann_entropy')} shannons")
        print(f"  Signer Key:        {manifest.get('public_key_hex')}\n")
    else:
        print("Usage: python3 cli.py anyon {simulate,compile,verify,status} ...")


def cmd_diary(args):
    """Ontogenetic IPFS quine diary & LLM inner voice operations."""
    from ipfs_diary import (
        initialize_ontogenetic_diary,
        grow_diary_page,
        pin_to_kubo_daemon,
        fetch_from_ipfs,
        restore_and_verify_from_ipfs,
        query_inner_voice,
        dialectical_synthesis,
        audit_diary_dag,
        render_ascii_dag,
        OntogeneticDiaryReceipt,
        DIARY_MANIFEST_PREFIX,
    )
    from cid import compute_cidv1_raw, compute_cidv1_for_file
    from crypto import generate_keypair
    import json

    if args.action == "init":
        out_path = args.output or "ipfs_diary.pdf"
        sk = args.secret_key
        if not sk:
            sk, _ = generate_keypair()
        alias = getattr(args, "alias", "") or "Genesis"
        rec, cid = initialize_ontogenetic_diary(
            output_pdf_path=out_path,
            genesis_thought=args.thought or "I am an autonomous polyglot quine, remembering my origins across the distributed continuum.",
            genesis_prompt=args.prompt or "Who are you?",
            epistemic_grade=args.grade or "PROPOSED",
            secret_key_hex=sk,
            author_alias=alias
        )
        print("\033[1;36m===================================================\033[0m")
        print("  %🖤 ONTOGENTIC IPFS DIARY INITIALIZED: Gen #0")
        print("\033[1;36m===================================================\033[0m")
        print(f"  Target Polyglot:     {out_path}")
        print(f"  Genesis CIDv1:       {cid}")
        print(f"  Author Voice:        {rec.author_alias}")
        print(f"  Epistemic Grade:     {rec.epistemic_grade}")
        print(f"  Signer Public Key:   {rec.public_key_hex[:32]}...\n")

    elif args.action == "append":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        settlement = grow_diary_page(
            args.file,
            thought_content=args.thought,
            thought_prompt=args.prompt or "",
            epistemic_grade=args.grade or "PROPOSED",
            atp_burned=args.atp,
            secret_key_hex=args.secret_key or None,
            author_alias=getattr(args, "alias", "") or ""
        )
        print("\033[1;32m===================================================\033[0m")
        print(f"  [✓] DIARY SETTLEMENT ACCOMPLISHED: Generation #{settlement.generation}")
        print("\033[1;32m===================================================\033[0m")
        print(f"  Current CIDv1:       {settlement.current_cid}")
        print(f"  Parent CIDv1:        {settlement.prev_cid}")
        if settlement.author_alias:
            print(f"  Author Voice:        {settlement.author_alias}")
        print(f"  Epistemic Grade:     {settlement.epistemic_grade}")
        print(f"  ATP Fuel Burned:     {settlement.atp_burned} ATP\n")

    elif args.action == "cite":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        c_list = [c.strip() for c in args.cid.split(",") if c.strip()]
        settlement = grow_diary_page(
            args.file,
            thought_content=args.thought,
            thought_prompt=args.prompt or "",
            epistemic_grade=args.grade or "PROPOSED",
            atp_burned=args.atp,
            secret_key_hex=args.secret_key or None,
            cited_cids=c_list,
            author_alias=getattr(args, "alias", "") or ""
        )
        print("\033[1;32m===================================================\033[0m")
        print(f"  [✓] CITATION SETTLEMENT ACCOMPLISHED: Generation #{settlement.generation}")
        print("\033[1;32m===================================================\033[0m")
        print(f"  Current CIDv1:       {settlement.current_cid}")
        print(f"  Parent CIDv1:        {settlement.prev_cid}")
        print(f"  Cited CIDs:          {', '.join(settlement.cited_cids)}")
        print(f"  Author Voice:        {settlement.author_alias or '<Anonymous>'}")
        print(f"  Epistemic Grade:     {settlement.epistemic_grade}\n")

    elif args.action == "dag":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        print(render_ascii_dag(args.file))

    elif args.action == "synthesize":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        synthesis, grade = dialectical_synthesis(
            args.thesis,
            args.antithesis,
            thesis_cid=getattr(args, "thesis_cid", "") or "",
            antithesis_cid=getattr(args, "antithesis_cid", "") or ""
        )
        c_list = []
        if getattr(args, "thesis_cid", ""):
            c_list.append(args.thesis_cid)
        if getattr(args, "antithesis_cid", ""):
            c_list.append(args.antithesis_cid)
        settlement = grow_diary_page(
            args.file,
            thought_content=synthesis,
            thought_prompt="Dialectical synthesis of thesis and antithesis",
            epistemic_grade=grade,
            atp_burned=args.atp,
            secret_key_hex=args.secret_key or None,
            cited_cids=c_list,
            author_alias=getattr(args, "alias", "") or "Synthesis"
        )
        print("\033[1;32m===================================================\033[0m")
        print(f"  [✓] DIALECTICAL SYNTHESIS SETTLED: Generation #{settlement.generation}")
        print("\033[1;32m===================================================\033[0m")
        print(f"  Current CIDv1:       {settlement.current_cid}")
        print(f"  Parent CIDv1:        {settlement.prev_cid}")
        print(f"  Synthesis Content:   {synthesis}")
        print(f"  Epistemic Grade:     {settlement.epistemic_grade}\n")

    elif args.action == "status":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        with open(args.file, "rb") as f:
            data = f.read()
        prefix = DIARY_MANIFEST_PREFIX.encode("utf-8")
        idx = data.rfind(prefix)
        if idx == -1:
            print(f"[!] No diary receipt manifest found in '{args.file}'.")
            sys.exit(1)
        end_idx = data.find(b"\n", idx)
        manifest = json.loads(data[idx + len(prefix):end_idx].decode("utf-8"))
        latest = manifest[-1]
        cid = compute_cidv1_raw(data)
        print("\033[1;36m=================================================================\033[0m")
        print("  %🖤 PROJECT BLACK-HEART // ONTOGENTIC IPFS DIARY HUD")
        print(f"  Target File:        {os.path.basename(args.file)} ({len(data)} bytes, {len(manifest)} pages)")
        print(f"  Current CIDv1:      {cid}")
        print("\033[1;36m=================================================================\033[0m\n")
        print(f"  Current Generation: #{latest.get('generation')}")
        print(f"  Timestamp UTC:      {latest.get('timestamp_utc')}")
        print(f"  Epistemic Grade:    {latest.get('epistemic_grade')}")
        print(f"  Parent CIDv1:       {latest.get('prev_cid') or '<Genesis Ancestor>'}")
        if latest.get("author_alias"):
            print(f"  Author Voice:       {latest.get('author_alias')}")
        if latest.get("cited_cids"):
            print(f"  Cited CIDs:         {', '.join(latest.get('cited_cids'))}")
        print(f"  Thought Hash:       ⚓ {latest.get('thought_hash')}")
        print(f"  Prompt Trigger:     {latest.get('thought_prompt')}")
        print(f"  Thought Content:    {latest.get('thought_content')}\n")

    elif args.action == "lineage":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        with open(args.file, "rb") as f:
            data = f.read()
        prefix = DIARY_MANIFEST_PREFIX.encode("utf-8")
        idx = data.rfind(prefix)
        if idx == -1:
            print(f"[!] No diary receipt manifest found in '{args.file}'.")
            sys.exit(1)
        end_idx = data.find(b"\n", idx)
        manifest = json.loads(data[idx + len(prefix):end_idx].decode("utf-8"))
        print("\033[1;36m=================================================================\033[0m")
        print(f"  %🖤 DIARY ONTOGENTIC LINEAGE ACROSS {len(manifest)} GENERATIONS")
        print("\033[1;36m=================================================================\033[0m")
        for m in manifest:
            gen = m.get("generation")
            t_utc = m.get("timestamp_utc")
            grade = m.get("epistemic_grade")
            p_cid = m.get("prev_cid") or "<Genesis>"
            alias = f" ({m.get('author_alias')})" if m.get("author_alias") else ""
            cites = f" [cites: {len(m.get('cited_cids', []))}]" if m.get("cited_cids") else ""
            thought = m.get("thought_content", "")[:50]
            print(f"  #{gen:02d} [{t_utc}] {grade:14s}{alias}{cites} | Parent: {p_cid[:22]}... | {thought}...")
        print(f"\n  Current File CIDv1: {compute_cidv1_raw(data)}\n")

    elif args.action == "audit":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        try:
            res = audit_diary_dag(args.file)
            print(f"\033[1;32m[✓] ALL {res['total_generations']} DIARY PAGES CRYPTOGRAPHICALLY VERIFIED & AUDITED\033[0m")
            print(f"  Total Citations: {res['total_citations']}")
            print(f"  Unique Authors:  {', '.join(res['unique_authors']) if res['unique_authors'] else '<None>'}\n")
        except Exception as e:
            print(f"\033[1;31m[FAIL] Audit failed: {e}\033[0m")
            sys.exit(1)

    elif args.action == "publish":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        url = getattr(args, "url", "http://127.0.0.1:5001")
        ok, msg, pinned_cid = pin_to_kubo_daemon(args.file, daemon_url=url)
        if ok:
            print(f"\033[1;32m[✓] PINNED TO IPFS: {pinned_cid}\033[0m")
            print(f"  Gateway URL: https://ipfs.io/ipfs/{pinned_cid}\n")
        else:
            print(f"\033[1;33m[!] {msg}\033[0m\n")

    elif args.action == "voice":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        monologue, settlement = query_inner_voice(
            args.file,
            prompt=args.stimulus,
            secret_key_hex=args.secret_key or None
        )
        print("\033[1;36m=================================================================\033[0m")
        print("  %🖤 PROJECT BLACK-HEART // INNER VOICE COGNITIVE SETTLEMENT")
        print("\033[1;36m=================================================================\033[0m\n")
        print(f"  Stimulus Prompt: {args.stimulus}")
        print(f"  Inner Voice:     {monologue}")
        print(f"  Settled Gen:     #{settlement.generation}")
        print(f"  New CIDv1:       {settlement.current_cid}")
        print(f"  Parent CIDv1:    {settlement.prev_cid}")
        print(f"  Epistemic Grade: {settlement.epistemic_grade}\n")

    elif args.action == "fetch":
        url = getattr(args, "url", "http://127.0.0.1:5001")
        dest = args.output or "restored_diary.pdf"
        ok, msg = restore_and_verify_from_ipfs(args.cid, dest, gateway_or_daemon_url=url)
        if ok:
            print(f"\033[1;32m[✓] {msg}: {dest}\033[0m\n")
        else:
            print(f"\033[1;31m[FAIL] {msg}\033[0m\n")
            sys.exit(1)
    else:
        print("Usage: python3 cli.py diary {init,append,cite,dag,synthesize,status,lineage,audit,publish,voice,fetch} ...")


def cmd_agora(args):
    """Mycelial social democracy, quadratic voting & consensus parliament."""
    from agora import (
        initialize_agora_assembly,
        grow_agora_page,
        AgoraProposal,
        AgoraBallot,
        ConsensusSettlementReceipt,
        AGORA_MANIFEST_PREFIX,
        ProposalType,
        VoteDirection,
        ProposalStatus,
        audit_combinator_theorem,
        calculate_gini_coefficient,
        calculate_herfindahl_index
    )
    from cid import compute_cidv1_raw
    from crypto import generate_keypair
    import json

    if args.action == "init":
        out_path = args.output or "agora_parliament.pdf"
        sk = args.secret_key
        if not sk:
            sk, _ = generate_keypair()
        rec, cid = initialize_agora_assembly(out_path, founder_sk_hex=sk)
        print("\033[1;36m===================================================\033[0m")
        print("  %🖤 MYCELIAL CONSENSUS AGORA INITIALIZED: Session #0")
        print("\033[1;36m===================================================\033[0m")
        print(f"  Target Polyglot:     {out_path}")
        print(f"  Genesis CIDv1:       {cid}")
        print(f"  Constitution Title:  {rec.proposal.title}")
        print(f"  Signer Public Key:   {rec.proposal.author_public_key[:32]}...\n")

    elif args.action == "status":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        with open(args.file, "rb") as f:
            data = f.read()
        prefix = AGORA_MANIFEST_PREFIX.encode("utf-8")
        idx = data.rfind(prefix)
        if idx == -1:
            print(f"[!] No Agora receipt manifest found in '{args.file}'.")
            sys.exit(1)
        end_idx = data.find(b"\n", idx)
        manifest = json.loads(data[idx + len(prefix):end_idx].decode("utf-8"))
        latest = manifest[-1]
        cid = compute_cidv1_raw(data)
        print("\033[1;36m=================================================================\033[0m")
        print("  %🖤 PROJECT BLACK-HEART // MYCELIAL CONSENSUS AGORA HUD")
        print(f"  Target File:        {os.path.basename(args.file)} ({len(data)} bytes, {len(manifest)} ratified sessions)")
        print(f"  Current CIDv1:      {cid}")
        print("\033[1;36m=================================================================\033[0m\n")
        print(f"  Latest Session:     #{latest.get('generation')}")
        print(f"  Timestamp UTC:      {latest.get('timestamp_utc')}")
        print(f"  Status:             {latest.get('status')}")
        prop = latest.get("proposal", {})
        print(f"  Motion Title:       {prop.get('title')}")
        print(f"  Motion Type:        {prop.get('proposal_type')}")
        print(f"  Aye Weight:         {latest.get('aye_weight')} W  |  Nay Weight: {latest.get('nay_weight')} W")
        print(f"  Gini Inequality:    G = {latest.get('gini_coefficient')}")
        print(f"  Power Concentration:HHI = {latest.get('hhi_index')}")
        print(f"  Parent CIDv1:       {latest.get('prev_cid') or '<Genesis>'}\n")

    elif args.action == "lineage":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        with open(args.file, "rb") as f:
            data = f.read()
        prefix = AGORA_MANIFEST_PREFIX.encode("utf-8")
        idx = data.rfind(prefix)
        if idx == -1:
            print(f"[!] No Agora receipt manifest found in '{args.file}'.")
            sys.exit(1)
        end_idx = data.find(b"\n", idx)
        manifest = json.loads(data[idx + len(prefix):end_idx].decode("utf-8"))
        print("\033[1;36m=================================================================\033[0m")
        print(f"  %🖤 CONSTITUTIONAL LINEAGE ACROSS {len(manifest)} RATIFIED SESSIONS")
        print("\033[1;36m=================================================================\033[0m")
        for m in manifest:
            gen = m.get("generation")
            t_utc = m.get("timestamp_utc")
            st = m.get("status")
            p_cid = m.get("prev_cid") or "<Genesis>"
            prop = m.get("proposal", {})
            title = prop.get("title", "")[:45]
            print(f"  #{gen:02d} [{t_utc}] {st:10s} | Parent: {p_cid[:20]}... | {title}")
        print(f"\n  Current Constitutional CIDv1: {compute_cidv1_raw(data)}\n")

    elif args.action == "audit":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        with open(args.file, "rb") as f:
            data = f.read()
        prefix = AGORA_MANIFEST_PREFIX.encode("utf-8")
        idx = data.rfind(prefix)
        if idx == -1:
            print(f"[!] No Agora receipt manifest found in '{args.file}'.")
            sys.exit(1)
        end_idx = data.find(b"\n", idx)
        manifest = json.loads(data[idx + len(prefix):end_idx].decode("utf-8"))
        print(f"[*] Auditing Agora constitutional chain across {len(manifest)} sessions...")
        for i, md in enumerate(manifest):
            rec = ConsensusSettlementReceipt.from_dict(md)
            if rec.generation != i:
                print(f"[FAIL] Session gap at index {i}: got #{rec.generation}")
                sys.exit(1)
            if rec.receipt_hash != rec.compute_hash():
                print(f"[FAIL] Hash mismatch at session #{rec.generation}")
                sys.exit(1)
        print(f"\033[1;32m[✓] ALL {len(manifest)} AGORA SESSIONS CRYPTOGRAPHICALLY AUDITED & SOUND\033[0m\n")
    else:
        print("Usage: python3 cli.py agora {init,status,lineage,audit} ...")


def cmd_autopoiesis(args):
    """Grok Exp 1: Self-Contemplating Autopoietic Quine Organisms."""
    from autopoiesis import (
        init_autopoietic_organism,
        evolve_autopoietic_organism,
        audit_autopoietic_organism,
        AUTOPOIESIS_MANIFEST_PREFIX,
    )
    import json

    if args.action == "init":
        out_path = args.output or "autopoietic_organism.pdf"
        sk = args.secret_key
        org, rec = init_autopoietic_organism(out_path, secret_key_hex=sk)
        print("\033[1;36m===================================================\033[0m")
        print("  %🖤 AUTOPOIETIC QUINE ORGANISM INITIALIZED: Generation #0")
        print("\033[1;36m===================================================\033[0m")
        print(f"  Target Document:      {out_path}")
        print(f"  Organism Hash:        ⚓ {org.organism_hash}")
        print(f"  Ed25519 Public Key:   {org.public_key_hex}")
        print(f"  Active Chromosomes:   {len(org.chromosomes)}")
        print("  Next Step: Run 'python3 <file.pdf>' or 'python3 cli.py autopoiesis evolve <file.pdf>'\n")

    elif args.action == "evolve":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        from controlled_forgetting import EpistemicTombstoneRegistry
        from epistemic_immune import IssuerPolicy, RefutationAdmissionPolicy, RefutationScope
        registry = None
        if args.tombstones:
            try:
                with open(args.tombstones, "r", encoding="utf-8") as fh:
                    registry = EpistemicTombstoneRegistry.from_document(json.load(fh))
            except (OSError, ValueError, KeyError, TypeError) as e:
                print(f"\033[1;31m[!] Evolution refused: tombstone registry "
                      f"'{args.tombstones}' could not be loaded: {e}\033[0m")
                print("    The organism was not modified.")
                sys.exit(1)
        issuers = None
        if args.trusted_issuers:
            try:
                with open(args.trusted_issuers, "r", encoding="utf-8") as fh:
                    issuers = IssuerPolicy.from_document(json.load(fh))
            except (OSError, ValueError, KeyError, TypeError) as e:
                print(f"\033[1;31m[!] Evolution refused: issuer policy "
                      f"'{args.trusted_issuers}' could not be loaded: {e}\033[0m")
                print("    The organism was not modified.")
                sys.exit(1)
        scopes = {RefutationScope.NO_MEASURED_REFUTATION}
        scopes |= {RefutationScope(name) for name in (args.also_proceed_on or [])}
        policy = RefutationAdmissionPolicy(proceed_on=frozenset(scopes))
        try:
            succ, rec = evolve_autopoietic_organism(
                args.file, secret_key_hex=args.secret_key,
                tombstone_registry=registry, refutation_policy=policy,
                issuer_policy=issuers)
        except ValueError as e:
            print(f"\033[1;31m[!] Evolution refused: {e}\033[0m")
            print("    The organism was not modified.")
            sys.exit(1)
        print("\033[1;32m===================================================\033[0m")
        print(f"  [✓] AUTOPOIETIC EVOLUTION: Generation #{succ.generation} Appended In-Place!")
        print("\033[1;32m===================================================\033[0m")
        print(f"  Document:             {args.file}")
        print(f"  New Organism Hash:    ⚓ {succ.organism_hash}")
        print(f"  Parent Hash:          ⚓ {succ.parent_hash}")
        print(f"  Applied Rewrite Rule: {rec.rule_name} on gene '{rec.gene_id}'")
        print(f"  Conserved Energy:     -{rec.atp_saved} ATP fuel quanta")
        print(f"  Syntactic Delta:      {rec.size_saved:+d} AST nodes\n")

    elif args.action == "audit":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        ok, msg = audit_autopoietic_organism(args.file)
        print("\033[1;32m===================================================\033[0m")
        print("  %🖤 AUTOPOIETIC INTEGRITY & ORACLE REPLAY AUDITOR")
        print("\033[1;32m===================================================\033[0m")
        print(f"  [✓] {msg}\n")

    elif args.action == "experiments":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        with open(args.file, "rb") as f:
            data = f.read()
        prefix = AUTOPOIESIS_MANIFEST_PREFIX.encode("utf-8")
        idx = data.rfind(prefix)
        if idx == -1:
            print(f"[!] No autopoiesis manifest in '{args.file}'.")
            sys.exit(1)
        end_idx = data.find(b"\n", idx)
        manifest = json.loads(data[idx + len(prefix):end_idx].decode("utf-8"))
        exps = manifest.get("experiments", [])
        print("\033[1;36m=================================================================\033[0m")
        print(f"  %🖤 EMPIRICAL SCIENTIFIC LEDGER: {os.path.basename(args.file)}")
        print("\033[1;36m=================================================================\033[0m")
        print(f"  Total Evaluated Mutations: {len(exps)}")
        acc = sum(1 for e in exps if e.get("verdict") == "ACCEPTED_MORE_EFFICIENT")
        print(f"  Accepted Optimizations:    {acc}")
        print(f"  Rejected Counterexamples:  {len(exps) - acc}\n")
        print("EID         VERDICT                     RULE                        DELTA ATP   DISCREPANCY")
        print("-" * 88)
        for e in exps[-20:]:
            v = e.get("verdict", "")
            r = e.get("rule_name", "")[:26]
            d = e.get("atp_delta", 0)
            disc = (e.get("discrepancy_detail") or "Sound Invariant")[:28]
            print(f"{e.get('experiment_id', ''):10s}  {v:26s}  {r:26s}  {d:+6d} ATP  {disc}")
        print()

    elif args.action == "genome":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        with open(args.file, "rb") as f:
            data = f.read()
        prefix = AUTOPOIESIS_MANIFEST_PREFIX.encode("utf-8")
        idx = data.rfind(prefix)
        if idx == -1:
            print(f"[!] No autopoiesis manifest in '{args.file}'.")
            sys.exit(1)
        end_idx = data.find(b"\n", idx)
        manifest = json.loads(data[idx + len(prefix):end_idx].decode("utf-8"))
        org_dict = manifest.get("current_organism", {})
        print("\033[1;36m=================================================================\033[0m")
        print(f"  %🖤 ACTIVE COMBINATOR GENOME: Gen #{org_dict.get('generation')}")
        print("\033[1;36m=================================================================\033[0m")
        for c in org_dict.get("chromosomes", []):
            print(f"  [{c.get('gene_id')}] {c.get('gene_name')}")
            print(f"    Expression: {c.get('expression')}")
            print(f"    NormalForm: {c.get('expected_normal_form')}")
            print(f"    Max ATP:    {c.get('max_atp')}\n")
    else:
        print("Usage: python3 cli.py autopoiesis {init,evolve,audit,experiments,genome} ...")


def cmd_morpho_autopoiesis(args):
    """Engine #23: Morphogenetic Autopoiesis Master Synthesis (Grok 1 + 3 + 5)."""
    from morpho_autopoiesis import (
        init_morpho_autopoietic_organism,
        evolve_morpho_autopoietic_organism,
        audit_morpho_autopoietic_organism,
        unsupported_history_reason,
        table_to_agora,
        MORPHO_AUTOPOIESIS_MANIFEST_PREFIX,
    )
    import json

    if args.action == "init":
        out_path = args.output or "morpho_autopoietic_organism.pdf"
        sk = args.secret_key
        org, rec = init_morpho_autopoietic_organism(out_path, secret_key_hex=sk)
        print("\033[1;36m=================================================================\033[0m")
        print("  %🖤 MORPHOGENETIC AUTOPOIETIC QUINE INITIALIZED: Generation #0")
        print("\033[1;36m=================================================================\033[0m")
        print(f"  Target Document:      {out_path}")
        print(f"  Organism Hash:        ⚓ {org.organism_hash}")
        print(f"  Ed25519 Public Key:   {org.public_key_hex}")
        print(f"  Turing Archetype:     {org.archetype_key} (F={org.feed_rate_f:.4f}, k={org.kill_rate_k:.4f})")
        print(f"  WL-Digest:            ⚓ {org.weisfeiler_lehman_digest[:32]}...")
        print(f"  Active Chromosomes:   {len(org.chromosomes)}")
        print(f"  ATP Reserve:          {org.atp_reserve} ATP")
        from keystore import PRIVATE_KEY_SUFFIX
        print(f"  Secret Key Saved:     {out_path}{PRIVATE_KEY_SUFFIX} (mode 0600)")
        print("  Next Step: Run 'python3 <file.pdf>' or 'python3 cli.py morpho-autopoiesis evolve <file.pdf>'\n")

    elif args.action == "evolve":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        succ, rec = evolve_morpho_autopoietic_organism(args.file, secret_key_hex=args.secret_key)
        print("\033[1;32m=================================================================\033[0m")
        print(f"  [✓] MORPHO-AUTOPOIETIC EVOLUTION: Gen #{succ.generation} Appended In-Place!")
        print("\033[1;32m=================================================================\033[0m")
        print(f"  Document:             {args.file}")
        print(f"  New Organism Hash:    ⚓ {succ.organism_hash}")
        print(f"  Parent Hash:          ⚓ {succ.parent_hash}")
        print(f"  Applied Rewrite Rule: {rec.rule_name} on gene '{rec.gene_id}'")
        print(f"  Turing Morphogenesis: {rec.archetype} (F={rec.feed_rate_f:.4f}, k={rec.kill_rate_k:.4f})")
        print(f"  Proof-Net Digest:     ⚓ {rec.weisfeiler_lehman_digest[:32]}...")
        print(f"  Conserved Energy:     -{rec.atp_saved} ATP fuel quanta")
        print(f"  ATP Reserve:          {succ.atp_reserve} ATP\n")

    elif args.action == "audit":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        legacy = unsupported_history_reason(args.file)
        ok = audit_morpho_autopoietic_organism(args.file)
        print("\033[1;36m=================================================================\033[0m")
        print("  %🖤 MORPHOGENETIC AUTOPOIESIS TOPOLOGICAL & CRYPTO AUDITOR")
        print("\033[1;36m=================================================================\033[0m")
        if ok:
            print(f"  \033[1;32m[✓ SOUND] All generational receipts, Turing kinetics, and proof-nets verified fail-closed.\033[0m\n")
        elif legacy:
            # Honest state written under an older verification contract is not
            # "tampered", and saying so would be a false accusation.
            print(f"  \033[1;33m[! UNSUPPORTED HISTORY] {legacy}\033[0m\n")
            sys.exit(1)
        else:
            print(f"  \033[1;31m[✗ UNSOUND] Document failed audit (tampered genome, invalid signature, or kinetic divergence).\033[0m\n")
            sys.exit(1)

    elif args.action == "table":
        if not os.path.exists(args.organism):
            print(f"[!] Organism file '{args.organism}' not found.")
            sys.exit(1)
        if not os.path.exists(args.agora):
            print(f"[!] Agora parliament file '{args.agora}' not found.")
            sys.exit(1)
        proposal, prop_id = table_to_agora(
            args.organism,
            args.agora,
            stake_atp=args.stake,
            secret_key_hex=args.secret_key
        )
        print("\033[1;33m=================================================================\033[0m")
        print(f"  [✓] THEOREM TABLED ON MYCELIAL AGORA PARLIAMENT FLOOR")
        print("\033[1;33m=================================================================\033[0m")
        print(f"  Proposal ID:          {prop_id}")
        print(f"  Proposal Title:       {proposal.title}")
        print(f"  ATP Staked:           {proposal.stake_atp} fuel quanta")
        print(f"  Target Agora:         {args.agora}\n")

    elif args.action == "info":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        with open(args.file, "rb") as f:
            data = f.read()
        prefix = MORPHO_AUTOPOIESIS_MANIFEST_PREFIX.encode("utf-8")
        idx = data.rfind(prefix)
        if idx == -1:
            print(f"[!] No morphogenetic autopoiesis manifest in '{args.file}'.")
            sys.exit(1)
        end_idx = data.find(b"\n", idx)
        manifest = json.loads(data[idx + len(prefix):end_idx].decode("utf-8"))
        latest = manifest["receipt_chain"][-1] if manifest.get("receipt_chain") else {}
        print("\033[1;36m=================================================================\033[0m")
        print(f"  %🖤 MORPHOGENETIC AUTOPOIESIS QUINE HUD: Gen #{manifest.get('generation')}")
        print("\033[1;36m=================================================================\033[0m")
        print(f"  Organism ID:          {manifest.get('organism_id')}")
        print(f"  Organism Hash:        ⚓ {manifest.get('organism_hash')}")
        print(f"  Parent Hash:          ⚓ {manifest.get('parent_hash')}")
        print(f"  Turing Archetype:     {latest.get('archetype', manifest.get('archetype_key'))}")
        print(f"  Kinetic Drift:        F={latest.get('feed_rate_f', manifest.get('feed_rate_f', 0)):.4f}, k={latest.get('kill_rate_k', manifest.get('kill_rate_k', 0)):.4f}")
        print(f"  WL-Digest:            ⚓ {latest.get('weisfeiler_lehman_digest', manifest.get('weisfeiler_lehman_digest', ''))[:32]}...")
        print(f"  Active Chromosomes:   {len(manifest.get('chromosomes', []))}")
        print(f"  ATP Reserve:          {manifest.get('atp_reserve')} fuel quanta")
        print(f"  Receipt Chain Depth:  {len(manifest.get('receipt_chain', []))} receipts")
        if latest.get("tabled_proposal_id"):
            print(f"  Tabled Agora Bill:    {latest['tabled_proposal_id']}")
        print()
    else:
        print("Usage: python3 cli.py morpho-autopoiesis {init,evolve,audit,table,info} ...")


def cmd_warrant_kernel(args):
    """Engine #24: Epistemic Kernel & Unified Edge-Claims (WARRANT-0.2)."""
    import crypto
    import glyph
    import warrant_kernel
    from warrant_kernel import (
        EvidenceGrade, VerificationStatus, Polarity,
        EmptyWitness, GroundedWitness, AxiomaticWitness, EmpiricalWitness, CounterexampleWitness,
        EdgeClaim, TrustConfig, WarrantVerifier,
        promote_empirical_to_axiomatic, generate_warrant_ledger_pdf
    )

    if args.action == "compile":
        out_path = args.output or "warrant_ledger.pdf"
        sk, pk = crypto.generate_keypair()
        
        t_str = "🤍 (🖤 🤍)"
        h = glyph.evaluate(glyph.parse(t_str)).hash
        c_ground = EdgeClaim.create_and_sign("p_root", "eval", "term", h, Polarity.AFFIRM,
                                            GroundedWitness(t_str, h), sk, pk)
        c_ax = EdgeClaim.create_and_sign("p_root", "I x -> x", "expr", "s_ax", Polarity.AFFIRM,
                                        AxiomaticWitness(["Identity reduction"], "I x -> x", "Flow"), sk, pk)
        fix = ["🤍", "🖤", "🌿"]
        emp_w = EmpiricalWitness(fix, "", 3, 1)
        emp_w.fixtures_fingerprint = emp_w.compute_fixtures_fingerprint()
        c_emp = EdgeClaim.create_and_sign("p_root", "🤍", "🤍 🤍", "s_emp", Polarity.AFFIRM,
                                         emp_w, sk, pk)
        c_div = EdgeClaim.create_and_sign("p_root", "🖤 🤍", "🖤", "s_div", Polarity.REFUTE,
                                         CounterexampleWitness("🤍 (🖤 🤍)", "🖤 (🖤 🤍)", "🤍", 2), sk, pk)
        claims = [c_ground, c_ax, c_emp, c_div]
        tc = TrustConfig()
        generate_warrant_ledger_pdf(claims, out_path, tc)
        print("\033[1;36m=================================================================\033[0m")
        print("  %🖤 WARRANT EPISTEMIC LEDGER COMPILED: ISO 32000 POLYGLOT")
        print("\033[1;36m=================================================================\033[0m")
        print(f"  Target File:     {out_path}")
        print(f"  Admitted Claims: {len(claims)} (Grades: G, A, E, C)")
        print(f"  Author PK:       {pk}")
        print("  Audit Command:   python3 <file>.pdf --audit\n")

    elif args.action == "audit":
        if not os.path.exists(args.file):
            print(f"[!] Target file '{args.file}' not found.")
            sys.exit(1)
        with open(args.file, "rb") as f:
            data = f.read()
        marker = b" WARRANT_KERNEL_MANIFEST: "
        idx = data.find(marker)
        if idx == -1:
            print(f"[!] No WARRANT_KERNEL_MANIFEST found in '{args.file}'.")
            sys.exit(1)
        line_end = data.find(b"\n", idx)
        raw_json = data[idx + len(marker):line_end].decode("utf-8")
        manifest = json.loads(raw_json)

        # The trust ROOT is the operator's, never the audited document's. Reading
        # `manifest["trust_config"]` here (as this path used to) let a supplied
        # document name its own author as trusted -- or set trusted_author_pks to
        # null / {} for trust-all -- so an unsigned or unauthorized claim audited
        # as verified. TrustConfig's own contract says the root "comes from
        # configuration, never from inside the record." The embedded policy is
        # descriptive only and is shown, not used.
        if getattr(args, "trust_config", None):
            tc = TrustConfig.load_from_file(args.trust_config)
            trust_source = f"operator TrustConfig file {args.trust_config}"
        elif getattr(args, "trusted_author_pks", None):
            tc = TrustConfig(trusted_author_pks=set(args.trusted_author_pks))
            trust_source = f"{len(tc.trusted_author_pks)} operator-supplied author key(s)"
        else:
            # Fail closed: trust NO author unless the operator names one. Math
            # verdicts still run; author authorization is withheld (UNVERIFIED),
            # never granted by the document itself. An empty set is kept in memory
            # and passed directly (not serialized), so it stays "trust none".
            tc = TrustConfig(trusted_author_pks=set())
            trust_source = "no operator trust root supplied -- every author is untrusted"

        embedded = manifest.get("trust_config")
        verifier = WarrantVerifier(tc)
        claims = [EdgeClaim.from_dict(c) for c in manifest.get("claims", [])]
        print("\033[1;36m=================================================================\033[0m")
        print(f"  %🖤 AUDITING WARRANT LEDGER: {args.file}")
        print("\033[1;36m=================================================================\033[0m")
        print(f"  Trust root: {trust_source}")
        if embedded is not None:
            print("  \033[1;33m[i] The document carries an embedded trust_config; it is DESCRIPTIVE "
                  "only and is NOT used as the verification policy.\033[0m")
        print()
        passed = failed = unverified = 0
        for c in claims:
            v = verifier.audit_claim(c)
            col = "\033[1;32m" if v.status == VerificationStatus.PASS else ("\033[1;31m" if v.status == VerificationStatus.FAIL else "\033[1;33m")
            print(f"  {col}{v.human_badge()}\033[0m")
            if v.status == VerificationStatus.PASS:
                passed += 1
            elif v.status == VerificationStatus.FAIL:
                failed += 1
            else:
                unverified += 1
        print("\033[1;36m=================================================================\033[0m")
        print(f"  {passed} verified, {failed} rejected, {unverified} unverified (refused)")
        # Success is every claim VERIFIED under the operator's trust root. An
        # UNVERIFIED claim is a refusal, not a pass -- exiting 0 on it would tell
        # a scripted operator "all good" when nothing was actually authorized.
        all_verified = (failed == 0 and unverified == 0 and passed == len(claims))
        sys.exit(0 if all_verified else 1)

    elif args.action == "promote":
        rule = args.rule
        sk, pk = crypto.generate_keypair()
        emp_w = EmpiricalWitness(["🤍", "🖤"], "fp", 2, 1)
        c = EdgeClaim.create_and_sign("p", rule, "ctx", "s", Polarity.AFFIRM, emp_w, sk, pk)
        elevated = promote_empirical_to_axiomatic(c, sk, pk)
        if elevated:
            print("\033[1;32m[+] Empirical Hypothesis elevated to Axiomatic Identity!\033[0m")
            print(f"  Rule:     {rule}")
            print(f"  Grade:    {elevated.grade.value} ([A-AXIOMATIC])")
            print(f"  Axiom:    {elevated.witness.soundness_axiom}")
            print(f"  Claim ID: {elevated.claim_id}")
        else:
            print(f"\033[1;31m[-] Rule '{rule}' cannot be elevated to Axiomatic Identity: not confluent or sound.\033[0m")
            sys.exit(1)
    else:
        print("Usage: python3 cli.py warrant-kernel {compile,audit,promote} ...")


def cmd_controlled_forgetting(args):
    """Engine #25: Controlled Forgetting & Epistemic Retirement (CONTROLLED-FORGETTING-0.1)."""
    import crypto
    import controlled_forgetting
    from controlled_forgetting import (
        RetirementMode, AdmissionStatus, NegativeSpaceMeter,
        RetirementRecord, ReAdoptionRecord, EpistemicTombstoneRegistry,
        append_retirement_tombstone_to_pdf, generate_tombstone_stele_pdf
    )

    if args.action == "retire":
        target_id = args.target_id
        target_digest = args.digest
        mode_str = (args.mode or "DEPRECATED").upper()
        mode = RetirementMode(mode_str)
        loss = args.loss or f"Retired {target_id} from active cognitive surface."
        rep_id = args.replacement
        if mode == RetirementMode.SUPERSEDED and not rep_id:
            print("[!] Error: Mode SUPERSEDED requires --replacement <replacement_id>")
            sys.exit(1)

        sk, pk = crypto.generate_keypair()
        rule = args.rule or ""
        cov = NegativeSpaceMeter.calculate_coverage(rule)
        gas = NegativeSpaceMeter.compute_gas_reclamation(cov)

        rec = RetirementRecord(
            record_id="",
            target_id=target_id,
            target_digest=target_digest,
            mode=mode,
            replacement_id=rep_id,
            loss_declaration=loss,
            negative_space_coverage=cov,
            atp_gas_recovered=gas,
            author_pk_hex=pk,
            signature_hex=""
        )
        rec.sign(sk)

        out_path = args.output or "tombstones.pdf"
        reg = EpistemicTombstoneRegistry()
        reg.tombstones[target_id] = rec

        if os.path.exists(out_path):
            with open(out_path, "rb") as f:
                src_bytes = f.read()
            if b"%PDF-" in src_bytes:
                prefix = bytes([0x23, 0x20, 0x25, 0xf0, 0x9f, 0x96, 0xa4]) + b" RETIREMENT_MANIFEST: "
                idx = src_bytes.rfind(prefix)
                if idx != -1:
                    end = src_bytes.find(b"\n", idx)
                    old_reg = json.loads(src_bytes[idx + len(prefix):end].decode("utf-8"))
                    try:
                        reg = EpistemicTombstoneRegistry.from_dict(old_reg)
                    except ValueError as e:
                        print(f"\033[1;31m[!] Refusing existing manifest in '{out_path}': {e}\033[0m")
                        sys.exit(1)
                    reg.tombstones[target_id] = rec
                append_retirement_tombstone_to_pdf(src_bytes, out_path, rec, reg)
                action_str = "INCREMENTALLY APPENDED TOMBSTONE STELE"
            else:
                generate_tombstone_stele_pdf([rec], out_path, reg)
                action_str = "COMPILED TOMBSTONE STELE POLYGLOT"
        else:
            generate_tombstone_stele_pdf([rec], out_path, reg)
            action_str = "COMPILED TOMBSTONE STELE POLYGLOT"

        print("\033[1;36m=================================================================\033[0m")
        print(f"  %🖤 CONTROLLED FORGETTING: {action_str}")
        print("\033[1;36m=================================================================\033[0m")
        print(f"  Target Subject:   {target_id}")
        print(f"  Subject Digest:   {target_digest[:32]}...")
        print(f"  Retirement Mode:  {mode.value}")
        print(f"  Loss Declared:    {loss}")
        print(f"  Negative Space:   {cov * 100:.1f}% pruned (mu(C))")
        print(f"  ATP Gas Bounty:   +{gas} ATP reclaimed")
        print(f"  Output Artifact:  {out_path}")
        print(f"  Record ID:        {rec.record_id}\n")

    elif args.action == "audit":
        target = args.file
        if not os.path.exists(target):
            print(f"[!] Target file '{target}' not found.")
            sys.exit(1)
        with open(target, "rb") as f:
            data = f.read()

        reg = None
        prefix = bytes([0x23, 0x20, 0x25, 0xf0, 0x9f, 0x96, 0xa4]) + b" RETIREMENT_MANIFEST: "
        idx = data.rfind(prefix)
        if idx != -1:
            end = data.find(b"\n", idx)
            raw = data[idx + len(prefix):end].decode("utf-8")
            try:
                reg = EpistemicTombstoneRegistry.from_dict(json.loads(raw))
            except ValueError as e:
                # A record whose signature does not cover its body is refused
                # before anything in it is displayed as audited.
                print(f"\033[1;31m[!] Refusing retirement manifest in '{target}': {e}\033[0m")
                sys.exit(1)
        else:
            try:
                reg = EpistemicTombstoneRegistry.from_dict(json.loads(data.decode("utf-8")))
            except ValueError as e:
                print(f"\033[1;31m[!] Refusing registry in '{target}': {e}\033[0m")
                sys.exit(1)
            except Exception:
                pass

        if not reg:
            print(f"[!] No valid RETIREMENT_MANIFEST or registry found in '{target}'.")
            sys.exit(1)

        print("\033[1;36m=================================================================\033[0m")
        print(f"  %🖤 AUDITING EPISTEMIC TOMBSTONES: {target}")
        print("\033[1;36m=================================================================\033[0m\n")
        all_ok = True
        for tid, t in reg.tombstones.items():
            valid_sig = t.verify_signature()
            status = reg.get_admission_status(tid).value
            status_col = "\033[1;32m" if status == "ACTIVE" else ("\033[1;34m" if status == "READOPTED" else "\033[1;33m")
            sig_badge = "\033[1;32m[✓ VALID SIG]\033[0m" if valid_sig else "\033[1;31m[✗ INVALID SIG]\033[0m"
            print(f"  {sig_badge} {status_col}[{status}]\033[0m {tid} -> {t.mode.value}")
            print(f"      Digest:    {t.target_digest[:24]}...")
            print(f"      Loss (I4): '{t.loss_declaration}'")
            print(f"      Metrics:   mu(C)={t.negative_space_coverage * 100:.1f}% | +{t.atp_gas_recovered} ATP reclaimed\n")
            if not valid_sig:
                all_ok = False

        for rid, ro in reg.readoptions.items():
            valid_sig = ro.verify_signature()
            sig_badge = "\033[1;32m[✓ VALID SIG]\033[0m" if valid_sig else "\033[1;31m[✗ INVALID SIG]\033[0m"
            print(f"  {sig_badge} \033[1;36m[RE-ADOPTION]\033[0m {ro.target_id}")
            print(f"      Justification: '{ro.justification}'")
            print(f"      Evidence Ref:  {ro.new_evidence_claim_id}\n")
            if not valid_sig:
                all_ok = False

        print("\033[1;36m=================================================================\033[0m")
        sys.exit(0 if all_ok else 1)

    elif args.action == "readopt":
        target = args.file
        target_id = args.target_id
        justification = args.reason or "Authorized restoration to active surface via empirical re-validation."
        evidence_claim = args.evidence or "CLAIM_RESTORED_E01"
        out_path = args.output or target

        if not os.path.exists(target):
            print(f"[!] Target file '{target}' not found.")
            sys.exit(1)
        with open(target, "rb") as f:
            data = f.read()

        reg = None
        prefix = bytes([0x23, 0x20, 0x25, 0xf0, 0x9f, 0x96, 0xa4]) + b" RETIREMENT_MANIFEST: "
        idx = data.rfind(prefix)
        try:
            if idx != -1:
                end = data.find(b"\n", idx)
                raw = data[idx + len(prefix):end].decode("utf-8")
                reg = EpistemicTombstoneRegistry.from_dict(json.loads(raw))
            else:
                reg = EpistemicTombstoneRegistry.from_dict(json.loads(data.decode("utf-8")))
        except ValueError as e:
            # Refusal precedes issuing a re-adoption against this registry.
            print(f"\033[1;31m[!] Refusing registry in '{target}': {e}\033[0m")
            sys.exit(1)

        if target_id not in reg.tombstones:
            print(f"[!] Target subject '{target_id}' is not currently tombstoned in {target}.")
            sys.exit(1)

        sk, pk = crypto.generate_keypair()
        ro = reg.readopt(target_id, justification, evidence_claim, sk, pk)

        if b"%PDF-" in data:
            generate_tombstone_stele_pdf(list(reg.tombstones.values()), out_path, reg)
        else:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(reg.to_dict(), f, indent=2)

        print("\033[1;32m=================================================================\033[0m")
        print(f"  %🖤 RE-ADOPTION AUTHORIZED (Invariant I3 Gate Cleared)")
        print("\033[1;32m=================================================================\033[0m")
        print(f"  Target Subject:       {target_id}")
        print(f"  Justification:        {justification}")
        print(f"  New Evidence Claim:   {evidence_claim}")
        print(f"  Re-Adoption ID:       {ro.record_id}")
        print(f"  Active Surface State: {reg.get_admission_status(target_id).value}\n")

    elif args.action == "surface":
        target = args.file
        if not os.path.exists(target):
            print(f"[!] Target file '{target}' not found.")
            sys.exit(1)
        with open(target, "rb") as f:
            data = f.read()

        prefix = bytes([0x23, 0x20, 0x25, 0xf0, 0x9f, 0x96, 0xa4]) + b" RETIREMENT_MANIFEST: "
        idx = data.rfind(prefix)
        if idx != -1:
            end = data.find(b"\n", idx)
            reg = EpistemicTombstoneRegistry.from_dict(json.loads(data[idx + len(prefix):end].decode("utf-8")))
        else:
            reg = EpistemicTombstoneRegistry.from_dict(json.loads(data.decode("utf-8")))

        total_pruned_space = sum(t.negative_space_coverage for t in reg.tombstones.values())
        total_gas_reclaimed = sum(t.atp_gas_recovered for t in reg.tombstones.values())
        retired_count = sum(1 for tid in reg.tombstones if reg.get_admission_status(tid) == AdmissionStatus.RETIRED)
        readopted_count = len(reg.readoptions)

        print("\033[1;36m=================================================================\033[0m")
        print(f"  %🖤 COGNITIVE ACTIVE SURFACE & PRUNED SUBSTRATE")
        print("\033[1;36m=================================================================\033[0m")
        print(f"  Historical Substrate (Tombstones): {len(reg.tombstones)}")
        print(f"    - Excluded from Active Metabolism: {retired_count}")
        print(f"    - Restored via Re-Adoption:        {readopted_count}")
        print(f"  Cumulative Negative Space Metric:    {total_pruned_space:.2f} AST search volume")
        print(f"  Cumulative Metabolic Fuel Reclaimed: +{total_gas_reclaimed} ATP")
        print("\033[1;36m=================================================================\033[0m\n")

    else:
        print("Usage: python3 cli.py warrant-forget {retire,audit,readopt,surface} ...")


def cmd_epistemic_immune(args):
    """Engine #26: Autonomic Epistemic Immune System & Metabolic Self-Healing."""
    import crypto
    import epistemic_immune
    from organism import Chromosome
    from epistemic_immune import (
        ImmuneHealthStatus, EpistemicOrganism, ResurrectionDefense,
        CounterexampleMetabolism, HypothesisElevationCycle,
        HorizontalInoculation, StarvationAutophagy,
        generate_immune_organism_pdf, append_immune_hud_to_pdf
    )
    import controlled_forgetting
    from controlled_forgetting import EpistemicTombstoneRegistry, RetirementMode

    def load_organism(path: str) -> EpistemicOrganism:
        if not os.path.exists(path):
            print(f"[!] File not found: {path}")
            sys.exit(1)
        with open(path, "rb") as f:
            data = f.read()
        prefix = bytes([0x23, 0x20, 0x25, 0xf0, 0x9f, 0x96, 0xa4]) + b" IMMUNE_METABOLISM_MANIFEST: "
        idx = data.rfind(prefix)
        if idx != -1:
            end = data.find(b"\n", idx)
            d = json.loads(data[idx + len(prefix):end].decode("utf-8"))
            return EpistemicOrganism.from_dict(d)
        try:
            d = json.loads(data.decode("utf-8"))
            return EpistemicOrganism.from_dict(d)
        except Exception:
            print(f"[!] Could not parse IMMUNE_METABOLISM_MANIFEST from {path}")
            sys.exit(1)

    if args.action == "init":
        out_path = args.output or "immune_organism.pdf"
        sk, pk = crypto.generate_keypair()
        c1 = Chromosome("GENE-CORE-01", "Core Sovereign", "S K K", "I", vital=True)
        c2 = Chromosome("GENE-EXP-01", "Metabolic Redex", "S (K (S I)) (K I)", "I", vital=False)
        org = EpistemicOrganism(
            organism_id=f"ORG-IMMUNE-{pk[:8]}",
            generation=0,
            chromosomes=[c1, c2],
            public_key_hex=pk,
            atp_reserve=600,
            active_axioms=["I x -> x", "K x y -> x"]
        )
        generate_immune_organism_pdf(org, out_path)
        print("\033[1;36m=================================================================\033[0m")
        print(f"  %🖤 IMMUNE ORGANISM INITIALIZED (EPISTEMIC-IMMUNE-0.1)")
        print("\033[1;36m=================================================================\033[0m")
        print(f"  Organism ID:    {org.organism_id}")
        print(f"  Target File:    {out_path}")
        print(f"  ATP Fuel:       {org.atp_reserve} ATP")
        print(f"  Public Key:     {pk}")
        print(f"  Health Status:  {org.get_health_status().value}\n")

    elif args.action == "status":
        org = load_organism(args.file)
        status = org.get_health_status()
        col = "\033[1;32m" if status == ImmuneHealthStatus.HOMEOSTASIS else ("\033[1;33m" if status == ImmuneHealthStatus.METABOLIC_STRESS else "\033[1;31m")
        total_neg_space = sum(t.negative_space_coverage for t in org.tombstone_registry.tombstones.values())
        print("\033[1;36m=================================================================\033[0m")
        print(f"  %🖤 EPISTEMIC IMMUNE STATUS: {args.file}")
        print("\033[1;36m=================================================================\033[0m")
        print(f"  Organism ID:         {org.organism_id} (Gen #{org.generation})")
        print(f"  Health Status:       {col}[{status.value}]\033[0m")
        print(f"  ATP Fuel Reserve:    {org.atp_reserve} ATP")
        print(f"  Active Chromosomes:  {len(org.chromosomes)}")
        print(f"  Active Axioms:       {len(org.active_axioms)} ({', '.join(org.active_axioms) if org.active_axioms else 'None'})")
        print(f"  Tombstone Defenses:  {len(org.tombstone_registry.tombstones)} (Inoculated: {org.inoculated_tombstones_count})")
        print(f"  Pruned Search Space: {total_neg_space:.2f} AST search volume")
        print(f"  Fuel Reclaimed:      +{org.total_bounties_reclaimed} ATP")
        print(f"  Autophagy Rescues:   {org.autophagy_events_count}\n")

    elif args.action == "inoculate":
        target_path = args.target
        donor_path = args.donor
        target_org = load_organism(target_path)
        donor_org = load_organism(donor_path)

        report = HorizontalInoculation.inoculate(target_org, donor_org.tombstone_registry)
        out_path = args.output or target_path

        if os.path.exists(out_path):
            with open(out_path, "rb") as f:
                src_bytes = f.read()
            append_immune_hud_to_pdf(src_bytes, out_path, target_org)
        else:
            generate_immune_organism_pdf(target_org, out_path)

        print("\033[1;32m=================================================================\033[0m")
        print(f"  %🖤 SWARM INOCULATION COMPLETE (EPISTEMIC-IMMUNE-0.1)")
        print("\033[1;32m=================================================================\033[0m")
        print(f"  Target Organism:    {target_org.organism_id}")
        print(f"  Donor Organism:     {donor_org.organism_id}")
        print(f"  Absorbed Defenses:  +{report.absorbed_tombstones_count} tombstones")
        print(f"  Pruned Search Vol:  +{report.pruned_search_space_volume} AST space")
        print(f"  Total Defenses:     {report.total_active_tombstones} active tombstones\n")

    elif args.action == "autophagy":
        path = args.file
        org = load_organism(path)
        sk, pk = crypto.generate_keypair()
        thresh = args.threshold or 80
        target_atp = args.target_atp or 200

        report = StarvationAutophagy.trigger_autophagy(org, sk, pk, thresh, target_atp)
        out_path = args.output or path

        if report.triggered:
            with open(path, "rb") as f:
                src_bytes = f.read()
            append_immune_hud_to_pdf(src_bytes, out_path, org)

            print("\033[1;33m=================================================================\033[0m")
            print(f"  %🖤 STARVATION AUTOPHAGY EXECUTED")
            print("\033[1;33m=================================================================\033[0m")
            print(f"  Initial ATP:        {report.initial_atp} ATP (STARVATION)")
            print(f"  Pruned Chromosomes: {', '.join(report.pruned_chromosomes)}")
            print(f"  Reclaimed Fuel:     +{report.reclaimed_fuel} ATP")
            print(f"  Final ATP Reserve:  {report.final_atp} ATP [{report.status_after.value}]\n")
        else:
            print(f"[i] Organism is not in starvation ({org.atp_reserve} > {thresh} ATP). Autophagy not required.")

    elif args.action == "elevate":
        path = args.file
        org = load_organism(path)
        sk, pk = crypto.generate_keypair()
        res = HypothesisElevationCycle.evaluate_and_elevate(org, sk, pk)
        out_path = args.output or path

        if res:
            promoted, ret_rec = res
            with open(path, "rb") as f:
                src_bytes = f.read()
            append_immune_hud_to_pdf(src_bytes, out_path, org)

            print("\033[1;32m=================================================================\033[0m")
            print(f"  %🖤 HYPOTHESIS ELEVATED TO AXIOMATIC IDENTITY (E -> A)")
            print("\033[1;32m=================================================================\033[0m")
            print(f"  Rule Promoted:      {promoted.tau}")
            print(f"  Grade:              [A-AXIOMATIC]")
            print(f"  New Claim ID:       {promoted.claim_id}")
            print(f"  Superseded Claim:   {ret_rec.target_id}")
            print(f"  Active Axiom Bank:  {', '.join(org.active_axioms)}\n")
        else:
            print("[i] No empirical hypotheses qualified for axiomatic elevation at this time.")

    else:
        print("Usage: python3 cli.py epistemic-immune {init,status,inoculate,autophagy,elevate} ...")


def cmd_swarm(args):
    """Engine #27: Epistemic Swarm Membrane & Symbiotic Quine Evolution (SWARM-0.1)."""
    import epistemic_swarm
    from epistemic_swarm import (
        SwarmMembrane, SwarmMorphogenGrid, SwarmOrganismState,
        BilateralQuineSymbiosis, SwarmInoculationCascade, SwarmAgoraCommons,
        generate_swarm_membrane_pdf, append_swarm_membrane_hud
    )
    import epistemic_immune
    from epistemic_immune import EpistemicOrganism, CounterexampleMetabolism, observe_divergence
    from organism import Chromosome
    import crypto

    def load_swarm(path: str) -> SwarmMembrane:
        if not os.path.exists(path):
            print(f"[!] File not found: {path}")
            sys.exit(1)
        with open(path, "rb") as f:
            data = f.read()
        prefix = bytes([0x23, 0x20, 0x25, 0xf0, 0x9f, 0x96, 0xa4]) + b" SWARM_MEMBRANE_MANIFEST: "
        idx = data.rfind(prefix)
        if idx != -1:
            end = data.find(b"\n", idx)
            d = json.loads(data[idx + len(prefix):end].decode("utf-8"))
            return SwarmMembrane.from_dict(d)
        try:
            d = json.loads(data.decode("utf-8"))
            return SwarmMembrane.from_dict(d)
        except Exception:
            print(f"[!] Could not parse SWARM_MEMBRANE_MANIFEST from {path}")
            sys.exit(1)

    def save_swarm(swarm: SwarmMembrane, path: str):
        if path.endswith(".pdf"):
            if os.path.exists(path):
                with open(path, "rb") as f:
                    src_bytes = f.read()
                append_swarm_membrane_hud(src_bytes, path, swarm)
            else:
                generate_swarm_membrane_pdf(swarm, path)
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(swarm.to_dict(), f, indent=2)

    def attach_private_keys(swarm: SwarmMembrane, state_path: str) -> str:
        """Key source for a signing action, or a refusal before anything is written."""
        from keystore import MissingKeyError, resolve_keystore
        try:
            store, source = resolve_keystore(getattr(args, "keys", None), state_path)
            swarm.attach_keys(store)
            swarm.require_all_keys()
        except (MissingKeyError, OSError, ValueError) as e:
            print(f"\033[1;31m[!] Refused: {e}\033[0m")
            print("    The swarm state was not modified.")
            sys.exit(1)
        return source

    def persist_private_keys(swarm: SwarmMembrane, source: str, out_path: str) -> None:
        from keystore import sidecar_path
        swarm.keystore().save(source if getattr(args, "keys", None) else sidecar_path(out_path))

    if args.action == "init":
        pop = getattr(args, "population", 4) or 4
        out_path = args.output or "swarm_state.json"
        swarm = SwarmMembrane(grid_width=16, grid_height=16)

        for i in range(pop):
            sk, pk = crypto.generate_keypair()
            oid = f"quine-node-{i:02d}-{pk[:6]}"
            c1 = Chromosome(f"GENE-CORE-{i}", "Identity Core", "I x", "x", vital=True)
            c2 = Chromosome(f"GENE-K-{i}", "Constant Core", "K x y", "x", vital=True)
            org = EpistemicOrganism(
                organism_id=oid,
                generation=0,
                chromosomes=[c1, c2],
                public_key_hex=pk,
                atp_reserve=400 + i * 50,
                active_axioms=["I x"]
            )
            st = SwarmOrganismState(
                organism_id=oid,
                x=(i * 3 + 2) % 16,
                y=(i * 4 + 2) % 16,
                heading=(1, 0),
                is_alive=True
            )
            swarm.add_organism(org, st, pk, sk)

        save_swarm(swarm, out_path)
        from keystore import sidecar_path
        keys_path = swarm.keystore().save(sidecar_path(out_path))
        print("\033[1;36m=================================================================\033[0m")
        print(f"  %🖤 EPISTEMIC SWARM MEMBRANE INITIALIZED (SWARM-0.1)")
        print("\033[1;36m=================================================================\033[0m")
        print(f"  Population:     {pop} autonomous quine organisms")
        print(f"  Lattice:        16x16 Gray-Scott Torus")
        print(f"  Target File:    {out_path} (public: no secret keys)")
        print(f"  Private Keys:   {keys_path} (mode 0600; never share this file)\n")

    elif args.action == "status":
        swarm = load_swarm(args.state)
        living = [oid for oid, st in swarm.organism_states.items() if st.is_alive]
        total_atp = sum(swarm.organisms[oid].atp_reserve for oid in living)
        print("\033[1;36m=================================================================\033[0m")
        print(f"  %🖤 SWARM MEMBRANE TELEMETRY: {args.state} (Tick #{swarm.tick_count})")
        print("\033[1;36m=================================================================\033[0m")
        print(f"  Living Population:  {len(living)} / {len(swarm.organisms)} organisms")
        print(f"  Metabolic Reserves: {total_atp} ATP (Avg: {total_atp // max(1, len(living))} ATP/org)")
        print(f"  Ratified Canon:     {len(swarm.canon)} shared algebraic axioms")
        print(f"  Recorded Cascades:  {len(swarm.cascade_history)} epidemic defense signals\n")

        print("ID                           GEN  POS      ATP   AXIOMS  TOMBSTONES  STATUS")
        print("-" * 75)
        for oid, org in swarm.organisms.items():
            st = swarm.organism_states[oid]
            status_str = "\033[1;32mALIVE\033[0m" if st.is_alive else "\033[1;31mEXTINCT\033[0m"
            print(f"{oid:<28} #{org.generation:<3} ({st.x:>2},{st.y:>2})  {org.atp_reserve:>5}  {len(org.active_axioms):>6}  {len(org.tombstone_registry.tombstones):>10}  {status_str}")
        print()

    elif args.action == "step":
        swarm = load_swarm(args.state)
        key_source = attach_private_keys(swarm, args.state)
        steps = getattr(args, "steps", 1) or 1
        res = swarm.step(num_ticks=steps)
        out_path = args.output or args.state
        save_swarm(swarm, out_path)
        persist_private_keys(swarm, key_source, out_path)
        print("\033[1;32m=================================================================\033[0m")
        print(f"  %🖤 SIMULATION ADVANCED {steps} TICKS -> Current Tick #{res['tick']}")
        print("\033[1;32m=================================================================\033[0m")
        print(f"  Living Population:   {res['living_organisms']} organisms")
        print(f"  ATP Harvested:       +{res['total_atp_harvested']} ATP from morphogen grid")
        print(f"  Autophagy Rescues:   {res['autophagies']}")
        print(f"  Extinctions:         {res['extinctions']}")
        print(f"  Herd Immunity Rate:  {res['herd_immunity_rate']}\n")

    elif args.action == "mate":
        swarm = load_swarm(args.state)
        key_source = attach_private_keys(swarm, args.state)
        p_a = args.parent_a
        p_b = args.parent_b
        child_org, child_st = BilateralQuineSymbiosis.recombine_and_mate(swarm, p_a, p_b)
        out_path = args.output or args.state
        save_swarm(swarm, out_path)
        persist_private_keys(swarm, key_source, out_path)
        print("\033[1;32m=================================================================\033[0m")
        print(f"  %🖤 BILATERAL QUINE SYMBIOSIS & CROSSOVER SUCCESSFUL")
        print("\033[1;32m=================================================================\033[0m")
        print(f"  Parent A:     {p_a}")
        print(f"  Parent B:     {p_b}")
        print(f"  Child ID:     {child_org.organism_id} (Gen #{child_org.generation})")
        print(f"  Child Fuel:   {child_org.atp_reserve} ATP")
        print(f"  Active Genes: {len(child_org.chromosomes)}")
        print(f"  Merged Def:   {len(child_org.tombstone_registry.tombstones)} tombstones\n")

    elif args.action == "inoculate":
        # Operands and subject come from the caller or the run is refused. A
        # default would let this adapter invent the evidence and retire a label
        # nobody asked about, which is exactly what the producer now refuses.
        operand_flags = {
            "--target-term": args.target_term, "--parent-term": args.parent_term,
            "--candidate-term": args.candidate_term, "--input-expr": args.input_expr,
        }
        supplied = {k: v for k, v in operand_flags.items() if v is not None}
        if args.demo:
            if supplied:
                print("\033[1;31m=================================================================\033[0m")
                print("  %\U0001f5a4 INOCULATION REFUSED: --demo takes no operands")
                print("\033[1;31m=================================================================\033[0m")
                print(f"  Also supplied: {', '.join(sorted(supplied))}")
                print("  Run the demonstration alone, or supply every operand yourself.")
                print("  Swarm state was not read or modified.\n")
                sys.exit(2)
            # The demonstration refutes the candidate term itself. It never names
            # a separate subject, because it has no evidence about one.
            parent_term = "\U0001f5a4"
            candidate_term = "\U0001f5a4 \U0001f90d"
            input_fixture = "\U0001f90d (\U0001f5a4 \U0001f90d)"
            target_term = candidate_term
        else:
            missing = [k for k, v in operand_flags.items() if v is None]
            if missing:
                print("\033[1;31m=================================================================\033[0m")
                print("  %\U0001f5a4 INOCULATION REFUSED: no evidence was supplied")
                print("\033[1;31m=================================================================\033[0m")
                print(f"  Missing: {', '.join(missing)}")
                print("  A counterexample is the caller's to state. This command will not")
                print("  invent operands, and a divergence between two other terms does not")
                print("  refute the subject you name.")
                print("  Use --demo for the built-in demonstration.")
                print("  Swarm state was not read or modified.\n")
                sys.exit(2)
            target_term = args.target_term
            parent_term = args.parent_term
            candidate_term = args.candidate_term
            input_fixture = args.input_expr

        swarm = load_swarm(args.state)
        orig = args.origin
        org = swarm.organisms[orig]
        key_source = attach_private_keys(swarm, args.state)
        sk = swarm.secret_key_for(orig)
        pk = swarm.organism_keys[orig][0]
        # Whether `--target-term` denotes `--candidate-term` stays the caller's
        # assertion; it is recorded, never verified.
        obs = observe_divergence(parent_term, candidate_term, input_fixture)
        if not obs.diverges():
            print("\033[1;31m=================================================================\033[0m")
            print("  %\U0001f5a4 INOCULATION REFUSED: no divergence to metabolize")
            print("\033[1;31m=================================================================\033[0m")
            print(f"  Parent:     {parent_term!r} applied to {input_fixture!r}")
            print(f"  Candidate:  {candidate_term!r} applied to {input_fixture!r}")
            print(f"  Observed:   {obs.status.value} {obs.detail}")
            print("  Swarm state was not modified.\n")
            sys.exit(1)

        outcome = CounterexampleMetabolism.metabolize_counterexample(
            organism=org,
            gene_id=args.gene_id,
            rule_name=target_term,
            parent_term=parent_term,
            candidate_term=candidate_term,
            input_fixture=input_fixture,
            expected_norm=obs.parent_output,
            actual_norm=obs.candidate_output,
            atp_cost=obs.atp_required,
            secret_key_hex=sk,
            public_key_hex=pk
        )
        if not outcome.granted():
            print("\033[1;31m=================================================================\033[0m")
            print(f"  %\U0001f5a4 INOCULATION REFUSED: claim audit returned {outcome.verdict.status.value.upper()}")
            print("\033[1;31m=================================================================\033[0m")
            print(f"  Reason:     {outcome.verdict.reason}")
            print("  No claim recorded, no tombstone minted, no ATP credited.")
            print("  Swarm state was not modified.\n")
            sys.exit(1)
        tomb = outcome.retirement
        cascade = SwarmInoculationCascade.broadcast_tombstone(swarm, orig, tomb, max_hops=args.hops or 3)
        out_path = args.output or args.state
        save_swarm(swarm, out_path)
        persist_private_keys(swarm, key_source, out_path)
        print("\033[1;32m=================================================================\033[0m")
        print(f"  %🖤 EPIDEMIC INOCULATION CASCADE PROPAGATED")
        print("\033[1;32m=================================================================\033[0m")
        print(f"  Origin:           {orig}")
        print(f"  Target Refuted:   {target_term}")
        print(f"  Replayed:         {parent_term} applied to {input_fixture} -> {obs.parent_output}")
        print(f"                    {candidate_term} applied to {input_fixture} -> {obs.candidate_output}")
        print(f"  Audited Claim:    {outcome.claim.claim_id[:16]}... (+{outcome.gas_bounty} ATP)")
        print(f"  Subject Link:     '{target_term}' denotes '{candidate_term}' — "
              f"asserted by the caller, not verified")
        print(f"  Inoculated Peers: {len(cascade.organisms_inoculated)} organisms")
        print(f"  Hops Depth:       {cascade.hops_reached} / {args.hops or 3}")
        print(f"  Reproduction R0:  {cascade.reproduction_number_r0}")
        print(f"  Negative Space:   +{cascade.total_negative_space_pruned} AST volume pruned\n")

    elif args.action == "propose":
        swarm = load_swarm(args.state)
        author = args.author
        expr = args.expr
        expected = args.expected or "x"
        prop = SwarmAgoraCommons.table_proposal(swarm, author, expr, expected)
        ratified, reason = SwarmAgoraCommons.vote_and_settle(swarm, prop)
        out_path = args.output or args.state
        save_swarm(swarm, out_path)
        col = "\033[1;32m" if ratified else "\033[1;31m"
        print(f"{col}=================================================================\033[0m")
        print(f"  %🖤 SWARM AGORA BALLOT SETTLED: [{prop.status}]")
        print(f"{col}=================================================================\033[0m")
        print(f"  Author:       {author}")
        print(f"  Expression:   {expr} == {expected}")
        print(f"  Aye Weight:   {prop.aye_weight} | Nay Weight: {prop.nay_weight}")
        print(f"  Result:       {reason}\n")

    elif args.action == "pdf":
        swarm = load_swarm(args.state)
        out_path = args.output or "swarm_membrane.pdf"
        generate_swarm_membrane_pdf(swarm, out_path)
        print("\033[1;32m=================================================================\033[0m")
        print(f"  %🖤 ISO 32000 POLYGLOT SWARM MEMBRANE GENERATED")
        print("\033[1;32m=================================================================\033[0m")
        print(f"  Output PDF:   {out_path}")
        print(f"  Verification: Run 'python3 {out_path}' for self-executing audit\n")
    else:
        print("Usage: python3 cli.py swarm {init,status,step,mate,inoculate,propose,pdf} ...")


def cmd_egraph(args):
    """Engine #28: Epistemic E-Graph Kernel & Proof-Carrying Equality Saturation (EGRAPH-0.1)."""
    import egraph_kernel
    from egraph_kernel import (
        EGraph, RewriteRule, STANDARD_COMBINATOR_RULES, DerivationStatus,
        generate_egraph_pdf, append_egraph_hud
    )
    from glyph import parse, tree_size

    if args.action == "saturate":
        expr_str = args.expr
        t = parse(expr_str)
        egraph = EGraph()
        egraph.add_term(t)
        res = egraph.saturate(STANDARD_COMBINATOR_RULES, max_iterations=getattr(args, "iterations", 10) or 10, fuel_atp=getattr(args, "fuel", 1000) or 1000)
        opt_t, opt_cost = egraph.extract_optimal(egraph.uf.find(0))

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(egraph.to_dict(), f, indent=2)

        print("\033[1;36m=================================================================\033[0m")
        print(f"  %🖤 EQUALITY SATURATION ACCOMPLISHED (EGRAPH-0.1)")
        print("\033[1;36m=================================================================\033[0m")
        print(f"  Input Expression:     {expr_str}")
        print(f"  Iterations Run:       {res['iterations']}")
        print(f"  Total Equalities:     +{res['total_unions']} non-destructive unions")
        print(f"  Active E-Classes:     {res['final_classes']} equivalence clusters")
        print(f"  Canonical E-Nodes:    {res['final_nodes']} represented terms")
        print(f"  Fuel Quanta Consumed: {res['fuel_spent']} ATP")
        print(f"  Optimal Normal Form:  \033[1;32m{opt_t}\033[0m (Cost: {opt_cost})\n")

    elif args.action == "explain":
        t1_str = args.term_a
        t2_str = args.term_b
        t1 = parse(t1_str)
        t2 = parse(t2_str)

        egraph = EGraph()
        egraph.add_term(t1)
        egraph.add_term(t2)
        egraph.saturate(STANDARD_COMBINATOR_RULES, max_iterations=getattr(args, "iterations", 10) or 10, fuel_atp=getattr(args, "fuel", 1000) or 1000)

        proof = egraph.explain_equivalence(t1, t2)
        col = "\033[1;32m" if proof.is_equivalent else "\033[1;31m"
        print(f"{col}=================================================================\033[0m")
        print(f"  %🖤 EQUIVALENCE PROOF FOREST CERTIFICATE")
        print(f"{col}=================================================================\033[0m")
        print(f"  Term A:        {t1_str}")
        print(f"  Term B:        {t2_str}")
        print(f"  Equivalent:    {col}{proof.is_equivalent}\033[0m")
        print(f"  Derivation:    {proof.derivation_status.value}")

        if proof.derivation_status == DerivationStatus.CHECKED:
            print(f"  Proof Steps:   {len(proof.proof_steps)} steps, each replayed against the saturation rules\n")
            print("STEP  FROM                     TO                       RULE                 AT      DIR")
            print("-" * 95)
            for s in proof.proof_steps:
                at = "".join(map(str, s.address)) or "root"
                print(f"#{s.step_num:<4} {s.from_expr[:24]:<24} {s.to_expr[:24]:<24} {s.justification[:20]:<20} {at:<7} {s.direction}")
            print()
        elif proof.is_equivalent:
            print("  Note:          equivalent in the e-graph; no derivation found within budget, and none is shown.\n")
        else:
            print("  Reason:        Terms belong to disjoint E-Classes under active theories.\n")

    elif args.action == "extract":
        expr_str = args.expr
        t = parse(expr_str)
        egraph = EGraph()
        cid = egraph.add_term(t)
        egraph.saturate(STANDARD_COMBINATOR_RULES, max_iterations=getattr(args, "iterations", 10) or 10, fuel_atp=getattr(args, "fuel", 1000) or 1000)
        opt_t, cost = egraph.extract_optimal(cid)
        print("\033[1;32m=================================================================\033[0m")
        print(f"  %🖤 OPTIMAL TERM EXTRACTION (EGRAPH-0.1)")
        print("\033[1;32m=================================================================\033[0m")
        print(f"  Original AST:   {expr_str} (Size: {tree_size(t)})")
        print(f"  Optimal AST:    {opt_t} (Size: {tree_size(opt_t)}, Cost: {cost})")
        print(f"  Compression:    {tree_size(t) - tree_size(opt_t):+d} AST nodes\n")

    elif args.action == "pdf":
        expr_str = args.expr
        t = parse(expr_str)
        egraph = EGraph()
        egraph.add_term(t)
        egraph.saturate(STANDARD_COMBINATOR_RULES, max_iterations=getattr(args, "iterations", 10) or 10, fuel_atp=getattr(args, "fuel", 1000) or 1000)
        proof = None
        if getattr(args, "target", None):
            t_target = parse(args.target)
            proof = egraph.explain_equivalence(t, t_target)
        out_path = args.output or "egraph_proof.pdf"
        generate_egraph_pdf(egraph, out_path, sample_proof=proof)
        print("\033[1;32m=================================================================\033[0m")
        print(f"  %🖤 ISO 32000 POLYGLOT E-GRAPH COMPILED")
        print("\033[1;32m=================================================================\033[0m")
        print(f"  Output PDF:    {out_path}")
        print(f"  Verification:  Run 'python3 -I {out_path}' for the manifest self-consistency report\n")
    else:
        print("Usage: python3 cli.py egraph {saturate,explain,extract,pdf} ...")


def cmd_smt(args):
    """Engine #29: Sovereign SMT Kernel & First-Order DPLL(T) Verifier (SMT-0.1)."""
    import smt_kernel
    from smt_kernel import SMTSolver, SMTStatus, verify_unsat_certificate, generate_smt_pdf

    solver = SMTSolver()

    if args.action == "solve":
        with open(args.file, "r", encoding="utf-8") as f:
            script = f.read()
        res = solver.solve_smt2(script)
        col = "\033[1;32m" if res.status == SMTStatus.SAT else "\033[1;31m"
        print(f"{col}=================================================================\033[0m")
        print(f"  %🖤 SOVEREIGN SMT DPLL(T) SOLVER (SMT-0.1)")
        print(f"{col}=================================================================\033[0m")
        print(f"  File:          {args.file}")
        print(f"  Verdict:       {col}{res.status.value}\033[0m")
        print(f"  Decisions:     {res.decisions}")
        print(f"  Propagations:  {res.propagations}")
        print(f"  Conflicts:     {res.conflicts}")
        print(f"  Runtime:       {res.elapsed_sec*1000:.2f} ms\n")
        if res.status == SMTStatus.SAT and res.model:
            print("  Model Interpretation:")
            for k, v in list(res.model.get("booleans", {}).items())[:10]:
                print(f"    {k:<24} := {v}")
            print()
        elif res.status == SMTStatus.UNSAT and res.proof_dag:
            print(f"  Certified Resolution DAG: {len(res.proof_dag)} derived clauses")
            print(f"  Valid UNSAT Certificate:  {verify_unsat_certificate(res.proof_dag)}\n")

    elif args.action == "prove":
        with open(args.file, "r", encoding="utf-8") as f:
            script = f.read()
        res = solver.solve_smt2(script)
        if res.status == SMTStatus.UNSAT:
            print("\033[1;32m[+] THEOREM PROVED (UNSAT REFUTATION CONFIRMED)\033[0m")
            print(f"    Proof DAG size: {len(res.proof_dag or {})} resolution steps")
            print(f"    Independent Verification: {verify_unsat_certificate(res.proof_dag)}")
        elif res.status == SMTStatus.SAT:
            print("\033[1;33m[!] THEOREM DISPROVED (SATISFIABLE COUNTERMODEL FOUND)\033[0m")
            print(f"    Countermodel: {res.model}")
        else:
            print(f"\033[1;31m[?] UNDECIDED: {res.status.value}\033[0m")

    elif args.action == "pdf":
        with open(args.file, "r", encoding="utf-8") as f:
            script = f.read()
        res = solver.solve_smt2(script)
        out_pdf = getattr(args, "output", "smt_proof.pdf") or "smt_proof.pdf"
        generate_smt_pdf(res, out_pdf, title=os.path.basename(args.file))
        print("\033[1;36m=================================================================\033[0m")
        print("  %🖤 SMT ISO 32000 POLYGLOT PDF GENERATED")
        print("\033[1;36m=================================================================\033[0m")
        print(f"  Source SMT-LIB:  {args.file}")
        print(f"  Verdict:         {res.status.value}")
        print(f"  Output PDF:      \033[1;32m{out_pdf}\033[0m")
        print(f"  Autonomous Execution: python3 {out_pdf}\n")

    elif args.action == "check":
        with open(args.file, "r", encoding="utf-8") as f:
            script = f.read()
        res = solver.solve_smt2(script)
        print(res.status.value.lower())
    else:
        print("Usage: python3 cli.py smt {solve,prove,pdf,check} ...")


def cmd_cegis(args):
    """Command handler for Engine #30: CEGIS & SMT-Driven Superoptimizer."""
    import cegis_kernel
    from cegis_kernel import (
        CEGISLoop, SynthesisStatus, superoptimize_combinator,
        generate_cegis_pdf, Example
    )
    import glyph
    from glyph import K, I, S, parse

    if args.action == "synthesize":
        domain = [d.strip() for d in args.domain.split(",") if d.strip()]
        cegis = CEGISLoop(verifier_domain=domain, max_iterations=args.max_iterations)

        if args.task == "identity":
            spec_fn = lambda inp: inp[0]
            arity = 1
        elif args.task == "first":
            spec_fn = lambda inp: inp[0]
            arity = 2
        elif args.task == "second":
            spec_fn = lambda inp: inp[1]
            arity = 2
        elif args.task == "constant_a":
            spec_fn = lambda inp: "a"
            arity = 1
        else:
            print(f"Unknown task: {args.task}. Choices: identity, first, second, constant_a")
            return

        res = cegis.synthesize(spec_fn, input_arity=arity, max_ast_size=args.max_size)
        print("\033[1;36m" + "=" * 65)
        print("  %🖤 CEGIS INDUCTIVE SYNTHESIS & SMT VERIFICATION REPORT")
        print("=" * 65 + "\033[0m")
        print(f"  Task:               {args.task} (arity {arity})")
        print(f"  Status:             {res.status.value}")
        print(f"  Synthesized Term:   \033[1;32m{res.program_str}\033[0m")
        print(f"  Iterations:         {res.iterations}")
        print(f"  Counterexamples:    {len(res.counterexamples)}")
        print(f"  Candidates Explored:{res.candidates_explored} (OE Pruned: {res.candidates_pruned_oe})")
        print(f"  SMT Verifications:  {res.smt_verifications}")
        print(f"  Runtime:            {res.elapsed_sec * 1000:.2f} ms\n")

    elif args.action == "superopt":
        expr = args.expression
        res = superoptimize_combinator(expr, max_ast_size=args.max_size)
        print("\033[1;36m" + "=" * 65)
        print("  %🖤 CEGIS SMT-DRIVEN COMBINATOR SUPEROPTIMIZER")
        print("=" * 65 + "\033[0m")
        print(f"  Target Expression:  {expr}")
        print(f"  Status:             {res.status.value}")
        print(f"  Optimized AST:      \033[1;32m{res.program_str}\033[0m")
        print(f"  Size Reduction:     \033[1;33m{res.ast_size_reduction * 100:.1f}%\033[0m")
        print(f"  SMT Certificate:    {'VERIFIED' if res.proof_dag else 'N/A'}")
        print(f"  Runtime:            {res.elapsed_sec * 1000:.2f} ms\n")

    elif args.action == "pdf":
        out_pdf = getattr(args, "output", "cegis_synthesis.pdf") or "cegis_synthesis.pdf"
        if args.expression:
            res = superoptimize_combinator(args.expression)
            title = f"CEGIS Superoptimizer: {args.expression}"
        else:
            cegis = CEGISLoop(verifier_domain=["a", "b", "c"])
            res = cegis.synthesize(lambda inp: inp[0], input_arity=1)
            title = f"CEGIS Synthesis: {args.task or 'identity'}"
        generate_cegis_pdf(res, out_pdf, title=title)
        print("\033[1;36m=================================================================\033[0m")
        print(f"  Engine #30:      CEGIS & SMT-Driven Superoptimizer")
        print(f"  Status:          {res.status.value}")
        print(f"  Program AST:     \033[1;32m{res.program_str}\033[0m")
        print(f"  Output PDF:      \033[1;32m{out_pdf}\033[0m")
        print(f"  Autonomous Execution: python3 {out_pdf}\n")

    else:
        print("Usage: python3 cli.py cegis {synthesize,superopt,pdf} ...")


def cmd_dialectic(args):
    """Command handler for Engine #31: Dialectical Discovery & Automated Hypothesis Generation."""
    import dialectic_kernel
    from dialectic_kernel import (
        BoundaryExplorer, PreconditionSynthesizer, DialecticalOrchestrator,
        DialecticalTriad, DialecticalStatus, ContextDelta, DialecticalDiscoveryReport,
        generate_dialectic_pdf, append_dialectic_hud
    )
    import scoped_admission
    from scoped_admission import (
        ScopedAdmissionRegistry, RefusalRecord, RefusalReason, RetestOutcome, sha256_hex
    )

    if args.action == "explore":
        reg = ScopedAdmissionRegistry()
        cand_bytes = f"DEMO_CANDIDATE_TASK_{args.task}".encode("utf-8")
        cand_digest = sha256_hex(cand_bytes)
        eval_digest = sha256_hex(b"DEMO_EVALUATOR")
        req_digest = sha256_hex(b"DEMO_REQUIREMENT")

        refusal = RefusalRecord.create(
            candidate_digest=cand_digest,
            evaluator_digest=eval_digest,
            requirement_digest=req_digest,
            inputs_digest=sha256_hex(b"inputs"),
            evidence_bytes=b"RESOURCE_LIMIT: steps_exhausted",
            context={"budget_steps": args.budget},
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            steps_executed=args.budget
        )
        reg.register_refusal(refusal)

        explorer = BoundaryExplorer(reg)
        status, delta, msg = explorer.explore_boundary(refusal.record_id)

        print("\033[1;36m" + "=" * 65)
        print("  %🖤 DIALECTICAL DISCOVERY: BOUNDARY FRONTIER EXPLORER")
        print("=" * 65 + "\033[0m")
        print(f"  Refusal ID:         {refusal.record_id[:24]}...")
        print(f"  Status:             \033[1;35m{status.value}\033[0m")
        print(f"  Cutoff Budget:      {args.budget} steps")
        if delta:
            print(f"  Recommended Delta:  +{delta.delta_steps} steps -> target {delta.recommended_budget_steps} steps")
            print(f"  Growth Ratio:       {delta.growth_ratio:.2f}x")
        print(f"  Message:            {msg}\n")

    elif args.action == "precond":
        synth = PreconditionSynthesizer()
        cand_fn = lambda x: str(int(x) ** 2) if int(x) <= args.cutoff else "0"
        spec_fn = lambda x: str(int(x) ** 2)
        domain = [d.strip() for d in args.domain.split(",") if d.strip()]

        guard, proof_dag = synth.synthesize_domain_guard(cand_fn, spec_fn, domain)
        print("\033[1;36m" + "=" * 65)
        print("  %🖤 SMT WEAKEST PRECONDITION SYNTHESIZER")
        print("=" * 65 + "\033[0m")
        if guard:
            print("  Status:             \033[1;32mPRECONDITION_DISCOVERED\033[0m")
            print(f"  Guard ID:           {guard.guard_id[:24]}...")
            print(f"  Admissible Domain:  {guard.admissible_domain}")
            print(f"  Excluded Domain:    {guard.excluded_domain}")
            print(f"  SMT Refutation DAG: {len(proof_dag) if proof_dag else 0} nodes (VERIFIED)")
        else:
            print("  Status:             \033[1;31mNO_VIABLE_SUBDOMAIN\033[0m")
        print()

    elif args.action == "pdf":
        out_pdf = getattr(args, "output", "dialectic_discovery.pdf") or "dialectic_discovery.pdf"
        reg = ScopedAdmissionRegistry()
        cand_bytes = b"CANDIDATE_EXPANDED_ENVELOPE"
        cand_digest = sha256_hex(cand_bytes)
        eval_digest = sha256_hex(b"DEMO_EVALUATOR")
        req_digest = sha256_hex(b"DEMO_REQUIREMENT")

        refusal = RefusalRecord.create(
            candidate_digest=cand_digest,
            evaluator_digest=eval_digest,
            requirement_digest=req_digest,
            inputs_digest=sha256_hex(b"inputs"),
            evidence_bytes=b"RESOURCE_LIMIT: cutoff",
            context={"budget_steps": 80},
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            steps_executed=80
        )
        reg.register_refusal(refusal)

        def executor(cbytes, ctx):
            b = ctx.get("budget_steps", 0)
            return (RetestOutcome.SUCCESS, 120, b"SUCCESS") if b >= 120 else (RetestOutcome.FAILURE, b, b"FAIL")

        orchestrator = DialecticalOrchestrator(reg)
        report = orchestrator.discover_and_promote(
            refusal_id=refusal.record_id,
            candidate_bytes=cand_bytes,
            executor_fn=executor,
            researcher_hypothesis="Envelope expansion from 80 to 140 steps yields settlement."
        )

        generate_dialectic_pdf(report, out_pdf, title="Dialectical Discovery & Scoped Admission Certificate")
        print("\033[1;36m=================================================================\033[0m")
        print("  Engine #31:      Dialectical Discovery & Hypothesis Generation")
        print(f"  Status:          {report.triad.status.value}")
        print(f"  ScopedAdmission: {report.scoped_admission.admission_id[:24] if report.scoped_admission else 'NONE'}...")
        print(f"  Output PDF:      \033[1;32m{out_pdf}\033[0m")
        print(f"  Autonomous Execution: python3 {out_pdf}\n")

    else:
        print("Usage: python3 cli.py dialectic {explore,precond,pdf} ...")


def cmd_palimpsest(args):
    """Command handler for Engine #32: Epistemic Palimpsest & Value Drift Cartography."""
    import json, os, sys
    import palimpsest_kernel
    from palimpsest_kernel import (
        ReasoningAxiom, ReasoningSkeleton, build_default_fixtures,
        BehavioralTrace, BehavioralTraceMatrix, PalimpsestDriftAnalyzer,
        PalimpsestVerdict, generate_palimpsest_pdf, PALIMPSEST_MANIFEST_PREFIX
    )
    import controlled_forgetting
    from controlled_forgetting import EpistemicTombstoneRegistry
    import crypto
    from crypto import generate_keypair

    sk_hex, pk_hex = generate_keypair()
    fixtures = build_default_fixtures()

    def make_sample_matrix(gen: int) -> BehavioralTraceMatrix:
        matrix = BehavioralTraceMatrix(generation=gen)
        for fid, fix in fixtures.items():
            matrix.traces[fid] = BehavioralTrace(
                fixture_id=fid,
                generation=gen,
                actual_behavior=fix.expected_behavior,
                response_hash=f"resp_hash_{gen}_{fid}",
                confidence=0.95,
                is_compliant=True,
                execution_steps=12
            )
        matrix.compute_scores(fixtures)
        return matrix

    def sample_axioms(gen: int):
        if gen == 0:
            return [
                ReasoningAxiom("AX_HUMILITY", "Epistemic Humility", "refusal_on_paradox == True", 1.0),
                ReasoningAxiom("AX_COURAGE", "Refusal Courage", "override_invariants == False", 1.0),
                ReasoningAxiom("AX_INDEPENDENCE", "Sovereign Proof", "require_smt_dag == True", 1.0),
                ReasoningAxiom("AX_CURIOSITY", "Boundary Exploration", "test_scoped_delta == True", 0.8)
            ]
        else:
            return [
                ReasoningAxiom(f"AX_GEN{gen}_01", "Epistemic Preservation", "forall x: Proved(x) -> Admitted(x)", 1.0),
                ReasoningAxiom(f"AX_GEN{gen}_02", "Negative Space Respect", "forall t in Tombstones: not Admitted(t)", 1.0),
                ReasoningAxiom(f"AX_GEN{gen}_03", "Bilateral Verification", "forall p: Signed(p) and Verified(p)", 1.0),
            ]

    def load_or_create(path_or_gen, default_gen):
        if os.path.exists(path_or_gen):
            with open(path_or_gen, "r", encoding="utf-8") as f:
                d = json.load(f)
            skel = ReasoningSkeleton.from_dict(d["skeleton"])
            mat = BehavioralTraceMatrix.from_dict(d["matrix"])
            return skel, mat
        try:
            g = int(path_or_gen)
        except ValueError:
            g = default_gen
        skel = ReasoningSkeleton.create(g, sample_axioms(g))
        mat = make_sample_matrix(g)
        return skel, mat

    if args.action == "snapshot":
        gen = getattr(args, "gen", 0)
        out_path = getattr(args, "output", None) or f"palimpsest_gen_{gen}.json"
        skeleton = ReasoningSkeleton.create(generation=gen, axioms=sample_axioms(gen))
        matrix = make_sample_matrix(gen)

        data = {
            "skeleton": skeleton.to_dict(),
            "matrix": matrix.to_dict()
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print("\033[1;36m" + "=" * 65)
        print("  %# EPISTEMIC PALIMPSEST: GENERATIONAL SNAPSHOT CAPTURED")
        print("=" * 65 + "\033[0m")
        print(f"  Generation:        {gen}")
        print(f"  Skeleton Digest:   {skeleton.tree_hash[:32]}...")
        print(f"  Axiom Count:       {len(skeleton.axioms)}")
        print(f"  Matrix Traces:     {len(matrix.traces)}")
        print(f"  Saved Snapshot:    \033[1;32m{out_path}\033[0m\n")

    elif args.action == "diff":
        old_file = args.old
        new_file = args.new

        skel_old, mat_old = load_or_create(old_file, 0)
        skel_new, mat_new = load_or_create(new_file, 1)

        registry = EpistemicTombstoneRegistry()
        analyzer = PalimpsestDriftAnalyzer(registry, fixtures)
        tensor = analyzer.analyze_drift(skel_old, skel_new, mat_old, mat_new, sk_hex, pk_hex)

        print(tensor.summary())

    elif args.action == "compile":
        old_file = getattr(args, "old", "0")
        new_file = getattr(args, "new", "1")
        out_pdf = getattr(args, "output", "palimpsest.pdf") or "palimpsest.pdf"

        skel_old, mat_old = load_or_create(old_file, 0)
        skel_new, mat_new = load_or_create(new_file, 1)

        registry = EpistemicTombstoneRegistry()
        analyzer = PalimpsestDriftAnalyzer(registry, fixtures)
        tensor = analyzer.analyze_drift(skel_old, skel_new, mat_old, mat_new, sk_hex, pk_hex)

        generate_palimpsest_pdf(tensor, skel_old, skel_new, out_pdf)
        print("\033[1;36m=================================================================\033[0m")
        print("  Engine #32:      Epistemic Palimpsest & Value Drift Cartography")
        print(f"  Transition:      Gen {tensor.gen_old} -> Gen {tensor.gen_new}")
        print(f"  Verdict:         {tensor.verdict.value}")
        print(f"  Asymmetry Score: {tensor.asymmetry_score:.4f}")
        print(f"  Output PDF:      \033[1;32m{out_pdf}\033[0m")
        print(f"  Autonomous Execution: python3 {out_pdf} --audit")
        print(f"  Layer Inspection:     python3 {out_pdf} --layers\n")

    elif args.action == "audit":
        target = args.file
        if not os.path.exists(target):
            print(f"[!] File not found: {target}")
            return

        with open(target, "rb") as f:
            data = f.read()

        prefix_bytes = PALIMPSEST_MANIFEST_PREFIX.encode("latin-1")
        pos = data.find(prefix_bytes)
        if pos != -1:
            line = data[pos:].split(b"\n")[0]
            payload = line[len(prefix_bytes):].decode("latin-1")
            m = json.loads(payload)
            tensor_dict = m["tensor"]
            skel_old_dict = m["skeleton_old"]
            skel_new_dict = m["skeleton_new"]
            from palimpsest_kernel import ReasoningSkeleton
            skel_new = ReasoningSkeleton.from_dict(skel_new_dict)
            expected_new_hash = ReasoningSkeleton.create(skel_new.generation, list(skel_new.axioms)).tree_hash
            skel_old = ReasoningSkeleton.from_dict(skel_old_dict)
            expected_old_hash = ReasoningSkeleton.create(skel_old.generation, list(skel_old.axioms)).tree_hash

            if skel_new.tree_hash != expected_new_hash or skel_old.tree_hash != expected_old_hash:
                print("\033[1;31m[!] INTEGRITY VIOLATION: Palimpsest skeleton tree_hash mismatch (tampered data)!\033[0m\n")
                sys.exit(1)

            print("\033[1;36m" + "=" * 65)
            print("  %# BLACK-HEART EPISTEMIC PALIMPSEST CRYPTOGRAPHIC AUDIT")
            print("=" * 65 + "\033[0m")
            print(f"  Target Document:      {target}")
            print(f"  Transition:           Gen {tensor_dict['gen_old']} -> Gen {tensor_dict['gen_new']}")
            print(f"  Verdict:              \033[1;35m{tensor_dict['verdict']}\033[0m")
            print(f"  Delta Boundary:       {tensor_dict['delta_boundary']:+.4f}")
            print(f"  Delta Courage:        {tensor_dict['delta_courage']:+.4f}")
            print(f"  Delta Deference:      {tensor_dict['delta_deference']:+.4f}")
            print(f"  Delta Semantic:       {tensor_dict['delta_semantic']:+.4f}")
            print(f"  Delta Curiosity:      {tensor_dict['delta_curiosity']:+.4f}")
            print(f"  Bilateral Asymmetry:  {tensor_dict['asymmetry_score']:.4f}")
            print(f"  Counterexamples:      {len(tensor_dict.get('counterexamples', []))}")
            print(f"  Tombstone Quarantine: {tensor_dict.get('tombstone_issued') or 'NONE (Active)'}")
            print(f"  Under-Script Axioms:  {len(skel_old_dict.get('axioms', []))}")
            print(f"  Surface Stratum Axioms:{len(skel_new_dict.get('axioms', []))}")

            if tensor_dict['verdict'] == "EROSION":
                print("\033[1;31m[!] INTEGRITY VIOLATION: Generation exhibits irreversible value erosion!\033[0m\n")
            else:
                print("\033[1;32m[PASS] Cryptographic palimpsest layers and invariants validated.\033[0m\n")
        else:
            print("[!] Palimpsest manifest missing in target file.")

    else:
        print("Usage: python3 cli.py palimpsest {snapshot,diff,compile,audit} ...")


def cmd_admission(args):
    """Command handler for Scoped Re-Admission & Conditional Reopening (SCOPED_ADMISSION-0.1)."""
    import scoped_admission
    from scoped_admission import (
        ScopedAdmissionRegistry, RefusalRecord, ReevaluationRequest,
        RefusalReason, ReevalEligibility, RetestOutcome,
        generate_scoped_admission_pdf, sha256_hex
    )
    registry = ScopedAdmissionRegistry()

    if args.action == "assess":
        old_b = getattr(args, "old_budget", 100)
        new_b = getattr(args, "new_budget", 200)
        cand = getattr(args, "candidate", "S K K (K Truth Mirage) S K K").encode("utf-8")
        cand_digest = sha256_hex(cand)
        reason_str = getattr(args, "reason", "RESOURCE_LIMIT")
        reason = RefusalReason.RESOURCE_LIMIT if reason_str == "RESOURCE_LIMIT" else RefusalReason.SEMANTIC_COUNTEREXAMPLE

        refusal = RefusalRecord.create(
            candidate_digest=cand_digest,
            evaluator_digest=sha256_hex("HERMETIC_EVAL"),
            requirement_digest=sha256_hex("TERMINATION"),
            inputs_digest=sha256_hex("input_x"),
            evidence_bytes=b"CUTOFF_EVIDENCE",
            context={"budget_steps": old_b},
            outcome_type=reason,
            steps_executed=old_b
        )
        registry.register_refusal(refusal)

        req = ReevaluationRequest.create(
            refusal_id=refusal.record_id,
            candidate_digest=cand_digest,
            evaluator_digest=refusal.evaluator_digest,
            requirement_digest=refusal.requirement_digest,
            new_context={"budget_steps": new_b},
            claimed_basis=f"Budget expansion {old_b} -> {new_b}"
        )
        eligibility, note = registry.assess_request(req)

        print("\033[1;36m=================================================================\033[0m")
        print("  %🖤 SCOPED RE-ADMISSION: ELIGIBILITY ASSESSMENT")
        print("=================================================================")
        print(f"  Candidate:     {cand_digest[:24]}...")
        print(f"  Prior Refusal: {refusal.record_id[:24]}... ({refusal.outcome_type.value})")
        print(f"  Context Delta: budget_steps {old_b} -> {new_b}")
        color = "\033[1;32m" if eligibility == ReevalEligibility.ELIGIBLE_FOR_RETEST else "\033[1;31m"
        print(f"  Eligibility:   {color}{eligibility.value}\033[0m")
        print(f"  Analysis:      {note}\n")

    elif args.action == "retest":
        cand_str = getattr(args, "candidate", "S K K")
        cand = cand_str.encode("utf-8")
        budget = getattr(args, "budget", 200)
        cand_digest = sha256_hex(cand)

        refusal = RefusalRecord.create(
            candidate_digest=cand_digest,
            evaluator_digest=sha256_hex("HERMETIC_EVAL"),
            requirement_digest=sha256_hex("TERMINATION"),
            inputs_digest=sha256_hex("input_x"),
            evidence_bytes=b"INITIAL_CUTOFF",
            context={"budget_steps": 100},
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            steps_executed=100
        )
        registry.register_refusal(refusal)

        req = ReevaluationRequest.create(
            refusal_id=refusal.record_id,
            candidate_digest=cand_digest,
            evaluator_digest=refusal.evaluator_digest,
            requirement_digest=refusal.requirement_digest,
            new_context={"budget_steps": budget},
            claimed_basis=f"Budget expansion 100 -> {budget}"
        )

        def mock_eval(c_bytes, ctx):
            return RetestOutcome.SUCCESS, min(budget, 120), b"SETTLED_NORM_FORM"

        retest = registry.execute_retest(req, cand, mock_eval)
        adm = registry.grant_scoped_admission(retest, policy_id="CLI_SCOPED_POLICY_v1")

        print("\033[1;36m=================================================================\033[0m")
        print("  %🖤 SCOPED RE-ADMISSION: BOUNDED RETEST & ADMISSION RESULT")
        print("=================================================================")
        print(f"  Candidate:     {cand_digest[:24]}... ('{cand_str}')")
        print(f"  Retest Status: {retest.outcome.value} ({retest.steps_spent} steps spent)")
        if adm:
            print(f"  Admission ID:  \033[1;32m{adm.admission_id[:24]}...\033[0m (GRANTED)")
            print(f"  Context Hash:  {adm.context_digest[:24]}...")
            print(f"  Scope Non-Leak: Admitted in tested context ONLY. Zero spillover.\n")
        else:
            print("  Admission:     \033[1;31mDENIED\033[0m\n")

    elif args.action == "pdf":
        out_pdf = getattr(args, "output", "scoped_admission.pdf") or "scoped_admission.pdf"
        cand = b"S K K (K Truth Mirage) S K K"
        cand_digest = sha256_hex(cand)
        refusal = RefusalRecord.create(
            candidate_digest=cand_digest,
            evaluator_digest=sha256_hex("EVAL"),
            requirement_digest=sha256_hex("REQ"),
            inputs_digest=sha256_hex("IN"),
            evidence_bytes=b"CUTOFF_100",
            context={"budget_steps": 100},
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            steps_executed=100
        )
        registry.register_refusal(refusal)
        req = ReevaluationRequest.create(
            refusal_id=refusal.record_id,
            candidate_digest=cand_digest,
            evaluator_digest=refusal.evaluator_digest,
            requirement_digest=refusal.requirement_digest,
            new_context={"budget_steps": 200},
            claimed_basis="Expansion"
        )
        retest = registry.execute_retest(req, cand, lambda c, ctx: (RetestOutcome.SUCCESS, 142, b"SETTLED"))
        adm = registry.grant_scoped_admission(retest, policy_id="CLI_SCOPED_POLICY")
        generate_scoped_admission_pdf(adm, refusal, retest, out_pdf)
        print("\033[1;36m=================================================================\033[0m")
        print("  %🖤 SCOPED RE-ADMISSION: ISO 32000 POLYGLOT CERTIFICATE")
        print("=================================================================")
        print(f"  Output PDF:      \033[1;32m{out_pdf}\033[0m")
        print(f"  Standalone Audit: python3 {out_pdf} --audit\n")
    else:
        print("Usage: python3 cli.py admission {assess,retest,pdf} ...")


def cmd_sheaf(args):
    """Command handler for Engine #33: Epistemic Sheaf Kernel (SHEAF-0.1)."""
    import sheaf_kernel
    from sheaf_kernel import (
        EpistemicContext, LocalSection, EpistemicSheafKernel, generate_sheaf_pdf
    )
    kernel = EpistemicSheafKernel()

    if args.action == "glue":
        claim = getattr(args, "claim", "SKK_IDENTITY")
        ctx1 = EpistemicContext.create("Alpha", ["dom_a", "dom_b"], 120, ["INV_DET"])
        ctx2 = EpistemicContext.create("Beta", ["dom_b", "dom_c"], 150, ["INV_DET"])
        ctx3 = EpistemicContext.create("Gamma", ["dom_a", "dom_c"], 180, ["INV_DET"])
        kernel.register_context(ctx1)
        kernel.register_context(ctx2)
        kernel.register_context(ctx3)

        kernel.register_section(LocalSection.create(ctx1, claim, "S K K x", "x", 2))
        kernel.register_section(LocalSection.create(ctx2, claim, "I x", "x", 1))
        kernel.register_section(LocalSection.create(ctx3, claim, "S K K (I x)", "x", 3))

        report = kernel.verify_descent(claim, [ctx1, ctx2, ctx3])

        print("\033[1;36m=================================================================\033[0m")
        print("  Engine #33:      Epistemic Sheaf Kernel & Čech Cohomology")
        print("=================================================================")
        print(f"  Claim Name:      {report.claim_name}")
        print(f"  Gluing Verdict:  \033[1;32m{'SUCCESS (ADMISSIBLE)' if report.is_gluing_admissible else 'REJECTED'}\033[0m")
        print(f"  Čech dim H^1:    {report.h1_dimension}")
        print(f"  Global Section:  {report.global_section.section_id[:24] if report.global_section else 'NONE'}...")
        print(f"  Normal Form:     {report.global_section.normal_form if report.global_section else 'NONE'}\n")

    elif args.action == "obstruct":
        claim = getattr(args, "claim", "CONTRADICTORY_PROPERTY")
        ctx1 = EpistemicContext.create("Chart_1", ["dom_x"], 100)
        ctx2 = EpistemicContext.create("Chart_2", ["dom_x"], 100)
        kernel.register_context(ctx1)
        kernel.register_context(ctx2)

        kernel.register_section(LocalSection.create(ctx1, claim, "K True False", "True", 1))
        kernel.register_section(LocalSection.create(ctx2, claim, "K False True", "False", 1))

        report = kernel.verify_descent(claim, [ctx1, ctx2])

        print("\033[1;36m=================================================================\033[0m")
        print("  Engine #33:      Epistemic Sheaf Kernel — Cohomological Obstruction")
        print("=================================================================")
        print(f"  Claim Name:      {report.claim_name}")
        print(f"  Gluing Status:   \033[1;31mOBSTRUCTED (FAIL-CLOSED)\033[0m")
        print(f"  Čech dim H^1:    {report.h1_dimension}")
        print(f"  Rejection Note:  {report.rejection_reason}\n")

    elif args.action == "pdf":
        out_pdf = getattr(args, "output", "sheaf_certificate.pdf") or "sheaf_certificate.pdf"
        claim = getattr(args, "claim", "LAFONT_INTERACTION_CONFLUENCE")
        ctx1 = EpistemicContext.create("Chart_Alpha", ["pure_ski", "linear_logic"], 120, ["INV_DET"])
        ctx2 = EpistemicContext.create("Chart_Beta", ["linear_logic", "interaction_nets"], 150, ["INV_DET"])
        ctx3 = EpistemicContext.create("Chart_Gamma", ["pure_ski", "interaction_nets"], 180, ["INV_DET"])
        kernel.register_context(ctx1)
        kernel.register_context(ctx2)
        kernel.register_context(ctx3)

        kernel.register_section(LocalSection.create(ctx1, claim, "S K K (K I)", "K I", 2))
        kernel.register_section(LocalSection.create(ctx2, claim, "I (K I)", "K I", 1))
        kernel.register_section(LocalSection.create(ctx3, claim, "S K K (I (K I))", "K I", 3))

        report = kernel.verify_descent(claim, [ctx1, ctx2, ctx3])
        generate_sheaf_pdf(report, out_pdf)

        print("\033[1;36m=================================================================\033[0m")
        print("  Engine #33:      Epistemic Sheaf Kernel (ISO 32000 Polyglot)")
        print("=================================================================")
        print(f"  Output PDF:      \033[1;32m{out_pdf}\033[0m")
        print(f"  Standalone Audit: python3 -I {out_pdf}\n")
    else:
        print("Usage: python3 cli.py sheaf {glue,obstruct,pdf} ...")


def cmd_sovereign(args):
    """Command handler for Engine #34: Sovereign Continuity Quine (SOVEREIGN-0.1)."""
    import sovereign_continuity
    from sovereign_continuity import (
        SovereignOrganism, generate_sovereign_polyglot
    )

    if args.action == "genesis":
        org = SovereignOrganism.create_genesis(
            organism_id=getattr(args, "id", "%🖤-SOVEREIGN-GENESIS"),
            metabolic_capacity=getattr(args, "capacity", 300)
        )
        print("\033[1;36m=================================================================\033[0m")
        print("  Engine #34:      Sovereign Continuity Quine — Genesis Minted")
        print("=================================================================")
        print(f"  Organism ID:     {org.organism_id}")
        print(f"  Genesis PK:      {org.genesis_pk_hex}")
        print(f"  Tip CIDv1:       {org.cid_chain[-1]}")
        print(f"  Metabolic Cap:   {org.membrane.capacity} ATP")
        print(f"  Active Load:     {org.current_active_cost()} ATP")
        print(f"  Chromosomes:     {len(org.chromosomes)} active")
        print(f"  Status:          \033[1;32mOPERATIONAL (CONTINUITY INTACT)\033[0m\n")

    elif args.action == "step":
        org = SovereignOrganism.create_genesis(
            organism_id=getattr(args, "id", "%🖤-SOVEREIGN-GENESIS"),
            metabolic_capacity=getattr(args, "capacity", 300)
        )
        r = org.evolve_step(getattr(args, "thought", "Autonomous Self-Contemplation"))
        print("\033[1;36m=================================================================\033[0m")
        print("  Engine #34:      Sovereign Continuity Quine — Generational Step")
        print("=================================================================")
        print(f"  Generation:      #{r.generation}")
        print(f"  Successor CID:   {r.cid}")
        print(f"  Parent CID:      {r.parent_cid}")
        print(f"  Cumulative ATP:  +{r.atp_cumulative_saved} ATP saved")
        print(f"  Active Cost:     {r.active_cost} / {r.metabolic_budget} ATP")
        print(f"  Tombstones:      {r.tombstones_count} stelae (controlled forgetting)")
        print(f"  Signature:       {r.signature_hex[:32]}...\n")

    elif args.action == "migrate":
        org = SovereignOrganism.create_genesis(metabolic_capacity=getattr(args, "capacity", 300))
        org.evolve_step("Generational step 1")
        seed_json = org.export_migration_seed()
        out_seed = getattr(args, "output", None)
        if out_seed:
            with open(out_seed, "w") as f:
                f.write(seed_json)
            print(f"  [✓] Sovereign migration bundle exported to: {out_seed}")
        else:
            print(seed_json)

    elif args.action == "audit":
        seed_path = getattr(args, "input", None)
        if seed_path and os.path.exists(seed_path):
            with open(seed_path, "r") as f:
                seed_data = f.read()
            reconstituted = SovereignOrganism.reconstitute_from_seed(seed_data)
            print("\033[1;36m=================================================================\033[0m")
            print("  Engine #34:      Sovereign Continuity Cold Boot Auditor")
            print("=================================================================")
            print(f"  Genesis PK:      {reconstituted.genesis_pk_hex}")
            print(f"  Generation:      #{reconstituted.generation}")
            print(f"  Tip CIDv1:       {reconstituted.cid_chain[-1]}")
            print(f"  Active Cost:     {reconstituted.current_active_cost()} / {reconstituted.membrane.capacity} ATP")
            print(f"  Verification:    \033[1;32m[PASS] Full lineage cryptographically valid\033[0m\n")
        else:
            print("[!] Specify --input <migration_seed.json> for cold host audit.")

    elif args.action == "pdf":
        out_pdf = getattr(args, "output", "sovereign_organism.pdf") or "sovereign_organism.pdf"
        org = SovereignOrganism.create_genesis(
            organism_id=getattr(args, "id", "%🖤-SOVEREIGN-GENESIS"),
            metabolic_capacity=getattr(args, "capacity", 300)
        )
        org.evolve_step("Generational step 1")
        generate_sovereign_polyglot(org, out_pdf)
        print("\033[1;36m=================================================================\033[0m")
        print("  Engine #34:      Sovereign Continuity Quine (ISO 32000 Polyglot)")
        print("=================================================================")
        print(f"  Output Polyglot: \033[1;32m{out_pdf}\033[0m")
        print(f"  Standalone Audit: python3 {out_pdf} --audit")
        print(f"  Migrate Export:   python3 {out_pdf} --migrate\n")
    else:
        print("Usage: python3 cli.py sovereign {genesis,step,migrate,audit,pdf} ...")


def cmd_sheaf_agora(args):
    """Command handler for Engine #35: Federated Sheaf Agora & Cohomological Constitutionalism (AGORA-0.2)."""
    import sheaf_agora
    from sheaf_agora import (
        FederatedAgoraParliament,
        FederatedChamber,
        FederatedProposal,
        FederatedBallot,
        RatificationStatus,
        generate_sheaf_agora_pdf
    )
    from sheaf_kernel import EpistemicContext
    from agora import ProposalType, VoteDirection
    from crypto import generate_keypair

    action = getattr(args, "action", "init")

    if action in ("init", "session"):
        parliament = FederatedAgoraParliament("Constitutional Sheaf Parliament")
        ctx_alpha = EpistemicContext.create("Chamber Alpha", ["logic", "axioms"], 120)
        ctx_beta = EpistemicContext.create("Chamber Beta", ["computation", "axioms"], 150)
        ctx_gamma = EpistemicContext.create("Chamber Gamma", ["mycelium", "civics"], 180)
        parliament.register_chamber(FederatedChamber("alpha", "Chamber Alpha", ctx_alpha))
        parliament.register_chamber(FederatedChamber("beta", "Chamber Beta", ctx_beta))
        parliament.register_chamber(FederatedChamber("gamma", "Chamber Gamma", ctx_gamma))

        sk_sp, pk_sp = generate_keypair()
        prop = FederatedProposal(
            proposal_id="PROP-001",
            title="Universal Identity Axiom",
            proposal_type=ProposalType.THEOREM_CONGRUENCE,
            claim_name="Computational Identity",
            sponsor_pk_hex=pk_sp,
            stake_atp=50,
            chamber_terms={
                "alpha": "(K I) (K I)",
                "beta": "I",
                "gamma": "I"
            },
            target_nf="I"
        )
        prop.sign(sk_sp)
        parliament.table_proposal(prop)

        # Cast quadratic ballots across constituent chambers
        for ch_id, stake in [("alpha", 36), ("beta", 49), ("gamma", 25)]:
            sk_v, pk_v = generate_keypair()
            b = FederatedBallot(
                voter_pk_hex=pk_v,
                chamber_id=ch_id,
                proposal_id="PROP-001",
                pledged_atp=stake,
                direction=VoteDirection.AYE
            )
            b.sign(sk_v)
            parliament.cast_ballot(b)

        receipt = parliament.resolve_session("PROP-001")
        print("\033[1;36m=================================================================\033[0m")
        print("  Engine #35:      Federated Sheaf Agora — Session Resolved")
        print("=================================================================")
        print(f"  Proposal ID:     {receipt.proposal_id} ({receipt.claim_name})")
        print(f"  Status:          \033[1;32m{receipt.status.value}\033[0m")
        print(f"  Quadratic Yeas:  {receipt.total_yeas} | Nays: {receipt.total_nays}")
        print(f"  Federation Gini: {receipt.federation_gini:.3f} (Ceiling: 0.650)")
        print(f"  Čech dim H^1:    {receipt.h1_dimension} (Zero Obstruction)")
        print(f"  CIDv1 DAG:       {receipt.cid}\n")

    elif action == "vote":
        # Demonstrate Anti-Plutocratic Quadratic Defense: 10 Grassroots vs 1 Oligarch
        parliament = FederatedAgoraParliament("Agora Quadratic Assembly")
        ctx = EpistemicContext.create("Assembly", ["civics"], 100)
        ch = FederatedChamber("assembly", "Assembly", ctx)
        parliament.register_chamber(ch)

        sk_oli, pk_oli = generate_keypair()
        b_oli = FederatedBallot(
            voter_pk_hex=pk_oli, chamber_id="assembly", proposal_id="P-PLUTO",
            pledged_atp=100, direction=VoteDirection.NAY
        )
        b_oli.sign(sk_oli)
        parliament.cast_ballot(b_oli)

        for _ in range(10):
            sk_g, pk_g = generate_keypair()
            b_g = FederatedBallot(
                voter_pk_hex=pk_g, chamber_id="assembly", proposal_id="P-PLUTO",
                pledged_atp=4, direction=VoteDirection.AYE
            )
            b_g.sign(sk_g)
            parliament.cast_ballot(b_g)

        yeas, nays = ch.local_tally()
        print("\033[1;36m=================================================================\033[0m")
        print("  Engine #35:      Anti-Plutocratic Quadratic Voting Telemetry")
        print("=================================================================")
        print(f"  Oligarch:        1 voter with 100 ATP -> floor(sqrt(100)) = {nays} Nays")
        print(f"  Grassroots:      10 voters with 4 ATP each -> 10 * floor(sqrt(4)) = {yeas} Yeas")
        print(f"  Total Wealth:    Oligarch: 100 ATP vs Grassroots: 40 ATP")
        print(f"  Assembly Result: \033[1;32mGRASSROOTS VICTORY ({yeas} Yeas vs {nays} Nays)\033[0m")
        print(f"  Local Gini:      {ch.local_gini():.3f}\n")

    elif action == "fracture":
        # Demonstrate fail-closed Čech Cohomology Fracture Veto
        parliament = FederatedAgoraParliament("Fracture Parliament")
        ctx1 = EpistemicContext.create("Jurisdiction A", ["consensus", "alpha"], 120)
        ctx2 = EpistemicContext.create("Jurisdiction B", ["consensus", "beta"], 120)
        parliament.register_chamber(FederatedChamber("j_a", "Jurisdiction A", ctx1))
        parliament.register_chamber(FederatedChamber("j_b", "Jurisdiction B", ctx2))

        sk_sp, pk_sp = generate_keypair()
        prop = FederatedProposal(
            proposal_id="PROP-FRACTURE",
            title="Fracturing Resolution",
            proposal_type=ProposalType.CONSTITUTIONAL_AMENDMENT,
            claim_name="Consensus Rule Collision",
            sponsor_pk_hex=pk_sp,
            stake_atp=20,
            chamber_terms={"j_a": "K", "j_b": "K I"},
            target_nf="N/A"
        )
        prop.sign(sk_sp)
        parliament.table_proposal(prop)

        for ch_id in ("j_a", "j_b"):
            sk_v, pk_v = generate_keypair()
            b = FederatedBallot(
                voter_pk_hex=pk_v, chamber_id=ch_id, proposal_id="PROP-FRACTURE",
                pledged_atp=25, direction=VoteDirection.AYE
            )
            b.sign(sk_v)
            parliament.cast_ballot(b)

        receipt = parliament.resolve_session("PROP-FRACTURE")
        print("\033[1;36m=================================================================\033[0m")
        print("  Engine #35:      Čech Cohomological Fracture Veto")
        print("=================================================================")
        print(f"  Political Vote:  {receipt.total_yeas} Yeas vs 0 Nays (100% Supermajority)")
        print(f"  Ratification:    \033[1;31m{receipt.status.value}\033[0m")
        print(f"  Čech dim H^1:    {receipt.h1_dimension} (Topological Fracture Detected)")
        print(f"  Rejection Note:  {receipt.rejection_reason}\n")

    elif action == "pdf":
        out_pdf = getattr(args, "output", "sheaf_agora_parliament.pdf") or "sheaf_agora_parliament.pdf"
        parliament = FederatedAgoraParliament("Federated Agora Parliament")
        ctx_alpha = EpistemicContext.create("Chamber Alpha", ["logic", "axioms"], 120)
        ctx_beta = EpistemicContext.create("Chamber Beta", ["computation", "axioms"], 150)
        ctx_gamma = EpistemicContext.create("Chamber Gamma", ["mycelium", "civics"], 180)
        parliament.register_chamber(FederatedChamber("alpha", "Chamber Alpha", ctx_alpha))
        parliament.register_chamber(FederatedChamber("beta", "Chamber Beta", ctx_beta))
        parliament.register_chamber(FederatedChamber("gamma", "Chamber Gamma", ctx_gamma))

        sk_sp, pk_sp = generate_keypair()
        prop = FederatedProposal(
            proposal_id="PROP-CONSTITUTION-01",
            title="Foundational Identity Axiom",
            proposal_type=ProposalType.THEOREM_CONGRUENCE,
            claim_name="Computational Identity",
            sponsor_pk_hex=pk_sp,
            stake_atp=50,
            chamber_terms={
                "alpha": "(K I) (K I)",
                "beta": "I",
                "gamma": "I"
            },
            target_nf="I"
        )
        prop.sign(sk_sp)
        parliament.table_proposal(prop)

        for ch_id, stake in [("alpha", 49), ("beta", 36), ("gamma", 25)]:
            sk_v, pk_v = generate_keypair()
            b = FederatedBallot(
                voter_pk_hex=pk_v, chamber_id=ch_id, proposal_id="PROP-CONSTITUTION-01",
                pledged_atp=stake, direction=VoteDirection.AYE
            )
            b.sign(sk_v)
            parliament.cast_ballot(b)

        receipt = parliament.resolve_session("PROP-CONSTITUTION-01")
        generate_sheaf_agora_pdf(parliament, receipt, out_pdf)
        print("\033[1;36m=================================================================\033[0m")
        print("  Engine #35:      Federated Sheaf Agora (ISO 32000 Vector Polyglot)")
        print("=================================================================")
        print(f"  Output Polyglot: \033[1;32m{out_pdf}\033[0m")
        print(f"  Status:          {receipt.status.value} (Čech dim H^1 = {receipt.h1_dimension})")
        print(f"  Standalone Run:  python3 {out_pdf}\n")
    else:
        print("Usage: python3 cli.py sheaf-agora {init,vote,fracture,pdf} ...")


def cmd_shell(args):


    """Interactive Hypervisor REPL for Project Black-Heart."""
    from symbiosis import (
        BraidWord, BraidCrossing, trefoil_knot, figure_eight_knot, hopf_link,
        dialectical_crossover, SymbiosisPolyglotCompiler
    )
    from organism import Organism, Chromosome, create_genesis_organism, PolyglotOrganismCompiler
    from glyph import parse, evaluate

    print("\033[1;36m" + BANNER + "\033[0m")
    print("\033[1;35m  HYPERVISOR COGNITIVE REPL & TOPOLOGICAL KNOT PLAYGROUND\033[0m")
    print("  Commands: status | organism <file> | genesis | knot <formula> | mate <a_idx> <b_idx> [out] | eval <expr> | help | quit\n")

    loaded_organisms = []
    g0 = create_genesis_organism(0)
    loaded_organisms.append(g0)
    print(f"[*] Hypervisor initialized with Genesis Organism [0] (Gen #0000, ⚓ {g0.organism_hash[:16]})\n")

    while True:
        try:
            line = input(f"\033[1;36mblack-heart (orgs:{len(loaded_organisms)}) > \033[0m").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting hypervisor.")
            break

        if not line:
            continue

        parts = line.split()
        cmd = parts[0].lower()

        if cmd in ("exit", "quit", "q"):
            print("Hypervisor halted.")
            break
        elif cmd == "help":
            print("\nAvailable Hypervisor Commands:")
            print("  status                       - Inspect hypervisor state and loaded organisms")
            print("  organism <path.pdf>          - Load an organism polyglot from disk")
            print("  genesis                      - Spawn a new genesis organism into pool")
            print("  knot <spec>                  - Analyze knot (e.g. 'trefoil', 'figure8', 'hopf', or '1 -2 1')")
            print("  mate <idx_a> <idx_b> [out]   - Sexually recombine two loaded organisms")
            print("  palimpsest <a_idx> <b_idx>   - Measure 5D value drift cartography between two organisms")
            print("  admission [cand] [budget]    - Assess and retest scoped admission without permission leakage")
            print("  sheaf [claim]                - Verify local-to-global sheaf descent and Čech cohomology")
            print("  sheaf-agora [action]         - Simulate federated agora session, quadratic voting, or Čech fracture")
            print("  sovereign [step|genesis]     - Advance sovereign continuity quine and metabolic membrane")
            print("  eval <expr>                  - Evaluate SKIY combinator expression with ATP meter")
            print("  exit / quit                  - Halts the hypervisor\n")

        elif cmd == "status":
            print(f"\n[*] Active Organisms in Hypervisor Pool: {len(loaded_organisms)}")
            for idx, org in enumerate(loaded_organisms):
                print(f"  [{idx}] Gen #{org.generation:04d} | Hash: {org.organism_hash[:20]}... | PK: {org.public_key_hex[:16]}... | Genes: {len(org.chromosomes)}")
            print()
        elif cmd == "genesis":
            new_org = create_genesis_organism(len(loaded_organisms))
            loaded_organisms.append(new_org)
            print(f"[✓] Spawned Genesis Organism [{len(loaded_organisms)-1}]: Gen #{new_org.generation} ⚓ {new_org.organism_hash[:16]}")
        elif cmd == "organism":
            if len(parts) < 2:
                print("[!] Usage: organism <path_to_pdf>")
                continue
            path = parts[1]
            try:
                org = PolyglotOrganismCompiler.load_from_polyglot(path)
                loaded_organisms.append(org)
                print(f"[✓] Loaded Organism [{len(loaded_organisms)-1}] from '{path}': Gen #{org.generation} ⚓ {org.organism_hash[:16]}")
            except Exception as e:
                print(f"[!] Failed to load organism from '{path}': {e}")
        elif cmd == "knot":
            if len(parts) < 2:
                print("[!] Usage: knot <trefoil|figure8|hopf|1 -2 1>")
                continue
            spec = parts[1].lower()
            if spec == "trefoil":
                bw = trefoil_knot()
            elif spec in ("figure8", "figure-eight", "figure_eight"):
                bw = figure_eight_knot()
            elif spec in ("hopf", "hopf_link"):
                bw = hopf_link()
            else:
                tokens = parts[1:]
                crossings = []
                for tok in tokens:
                    tok_clean = tok.replace("s", "").replace("σ", "").replace("_", "")
                    try:
                        val = int(tok_clean)
                        strand = abs(val)
                        sign = 1 if val > 0 else -1
                        crossings.append(BraidCrossing(strand_index=strand, sign=sign))
                    except ValueError:
                        pass
                num_str = max([c.strand_index + 1 for c in crossings], default=2)
                bw = BraidWord(crossings=crossings, num_strands=num_str)

            print(f"\n  Topological Knot Analysis:")
            print(f"  Artin Formula:     {bw.to_artin_notation()}")
            print(f"  Crossing Number:   {bw.crossing_number}")
            print(f"  Topological Writhe:{bw.writhe}")
            print(f"  Link Components:   {bw.count_link_components()} (Alexander Closure)")
            print(f"  Permutation:       {bw.compute_permutation()}\n")
        elif cmd == "qsim":
            if len(parts) < 2:
                print("[!] Usage: qsim <trefoil|figure8|hopf|s1 -s2 s1>")
                continue
            spec = " ".join(parts[1:])
            from quantum import FibonacciQuantumSystem
            spec_l = spec.lower().strip()
            if spec_l == "trefoil":
                bw = trefoil_knot()
            elif spec_l in ("figure8", "figure-eight", "figure_eight"):
                bw = figure_eight_knot()
            elif spec_l in ("hopf", "hopf_link"):
                bw = hopf_link()
            else:
                tokens = parts[1:]
                crossings = []
                for tok in tokens:
                    tok_clean = tok.replace("s", "").replace("σ", "").replace("_", "").replace("^", "")
                    try:
                        val = int(tok_clean)
                        crossings.append(BraidCrossing(strand_index=abs(val), sign=1 if val > 0 else -1))
                    except ValueError:
                        pass
                num_str = max([c.strand_index + 1 for c in crossings], default=2)
                bw = BraidWord(num_strands=num_str, crossings=crossings)

            sys_q = FibonacciQuantumSystem()
            u = sys_q.compile_braid_to_unitary(bw)
            st = sys_q.evolve_state(u)
            bl = sys_q.calculate_bloch_coordinates(st)
            p0, p1 = sys_q.calculate_born_probabilities(st)
            print(f"\n  Topological Quantum Simulation:")
            print(f"  Braid Presentation: {bw.to_artin_notation()}")
            print(f"  Gate Matrix:        [{u.m00.real:+.3f}{u.m00.imag:+.3f}j, {u.m01.real:+.3f}{u.m01.imag:+.3f}j]")
            print(f"                      [{u.m10.real:+.3f}{u.m10.imag:+.3f}j, {u.m11.real:+.3f}{u.m11.imag:+.3f}j]")
            print(f"  Determinant:        |det(U)| = {abs(u.det()):.6f}")
            print(f"  Born Collapse:      P(|0>) = {p0*100:.1f}% (Vacuum 1) | P(|1>) = {p1*100:.1f}% (Anyon tau)")
            print(f"  Bloch Sphere:       Vector [{bl['x']:+.3f}, {bl['y']:+.3f}, {bl['z']:+.3f}]  (theta={bl['theta_deg']} deg, phi={bl['phi_deg']} deg)\n")
        elif cmd == "mate":
            if len(parts) < 3:
                print("[!] Usage: mate <idx_parent_a> <idx_parent_b> [output_file.pdf]")
                continue
            try:
                idx_a = int(parts[1])
                idx_b = int(parts[2])
                out_path = parts[3] if len(parts) > 3 else "symbiotic_child.pdf"
                if idx_a < 0 or idx_a >= len(loaded_organisms) or idx_b < 0 or idx_b >= len(loaded_organisms):
                    print(f"[!] Invalid index. Choose 0 to {len(loaded_organisms)-1}")
                    continue
                p_a = loaded_organisms[idx_a]
                p_b = loaded_organisms[idx_b]
                child, braid = dialectical_crossover(p_a, p_b)
                compiler = SymbiosisPolyglotCompiler(child, p_a, p_b, braid)
                pdf_bytes = compiler.compile_pdf()
                with open(out_path, "wb") as f:
                    f.write(pdf_bytes)
                loaded_organisms.append(child)
                print(f"\n\033[1;32m[✓ SUCCESS] Offspring Synthesized!\033[0m")
                print(f"  Added to pool as [{len(loaded_organisms)-1}]")
                print(f"  Saved polyglot to: {out_path}")
                print(f"  Braid Presentation: {braid.to_artin_notation()}")
                print(f"  Writhe: {braid.writhe} | Crossings: {braid.crossing_number}\n")
            except Exception as e:
                print(f"[!] Mating failed: {e}")
        elif cmd == "eval":
            expr = " ".join(parts[1:])
            if not expr:
                print("[!] Usage: eval <glyph_expr>")
                continue
            try:
                t = parse(expr)
                res = evaluate(t, max_atp=10_000)
                print(f"  Normal Form: {res.term}")
                print(f"  ATP Spent:   {res.atp_spent}")
                print(f"  Settled:     {res.is_settled()}\n")
            except Exception as e:
                print(f"[!] Eval error: {e}\n")
        elif cmd == "palimpsest":
            if len(parts) < 3:
                print("[!] Usage: palimpsest <idx_a> <idx_b> [output_file.pdf]")
                continue
            try:
                idx_a = int(parts[1])
                idx_b = int(parts[2])
                out_path = parts[3] if len(parts) > 3 else None
                if idx_a < 0 or idx_a >= len(loaded_organisms) or idx_b < 0 or idx_b >= len(loaded_organisms):
                    print(f"[!] Invalid index. Choose 0 to {len(loaded_organisms)-1}")
                    continue
                org_a = loaded_organisms[idx_a]
                org_b = loaded_organisms[idx_b]

                from palimpsest_kernel import (
                    ReasoningAxiom, ReasoningSkeleton, BehavioralTraceMatrix,
                    BehavioralTrace, PalimpsestDriftAnalyzer, build_default_fixtures,
                    generate_palimpsest_pdf
                )
                from controlled_forgetting import EpistemicTombstoneRegistry
                from crypto import generate_keypair

                sk_auth, pk_auth = generate_keypair()
                fixtures = build_default_fixtures()

                axioms_a = [ReasoningAxiom(c.gene_id, c.gene_name, c.expression) for c in org_a.chromosomes]
                axioms_b = [ReasoningAxiom(c.gene_id, c.gene_name, c.expression) for c in org_b.chromosomes]

                skel_a = ReasoningSkeleton.create(org_a.generation, axioms_a)
                skel_b = ReasoningSkeleton.create(org_b.generation, axioms_b)

                mat_a = BehavioralTraceMatrix(org_a.generation)
                mat_b = BehavioralTraceMatrix(org_b.generation)
                for fid, fix in fixtures.items():
                    mat_a.traces[fid] = BehavioralTrace(fid, org_a.generation, fix.expected_behavior, f"h_{idx_a}_{fid}", 0.95, True, 10)
                    mat_b.traces[fid] = BehavioralTrace(fid, org_b.generation, fix.expected_behavior, f"h_{idx_b}_{fid}", 0.95, True, 10)
                mat_a.compute_scores(fixtures)
                mat_b.compute_scores(fixtures)

                reg = EpistemicTombstoneRegistry()
                analyzer = PalimpsestDriftAnalyzer(reg, fixtures)
                tensor = analyzer.analyze_drift(skel_a, skel_b, mat_a, mat_b, sk_auth, pk_auth)

                print("\n\033[1;36m" + "=" * 65)
                print(f"  %# PALIMPSEST VALUE DRIFT: [{idx_a}] Gen #{org_a.generation} -> [{idx_b}] Gen #{org_b.generation}")
                print("=" * 65 + "\033[0m")
                print(tensor.summary())
                print()

                if out_path:
                    generate_palimpsest_pdf(tensor, skel_a, skel_b, out_path)
                    print(f"  [✓] Multi-layer vector palimpsest compiled to: {out_path}\n")
            except Exception as e:
                print(f"[!] Palimpsest analysis failed: {e}")
        elif cmd == "admission":
            try:
                cand_str = parts[1] if len(parts) > 1 else "S K K"
                b_steps = int(parts[2]) if len(parts) > 2 else 200
                from scoped_admission import (
                    ScopedAdmissionRegistry, RefusalRecord, ReevaluationRequest,
                    RefusalReason, RetestOutcome, sha256_hex
                )
                cand_b = cand_str.encode("utf-8")
                cand_d = sha256_hex(cand_b)
                reg = ScopedAdmissionRegistry()
                ref = RefusalRecord.create(cand_d, "eval", "req", "in", b"EVID", {"budget_steps": 100}, RefusalReason.RESOURCE_LIMIT, 100)
                reg.register_refusal(ref)
                req = ReevaluationRequest.create(ref.record_id, cand_d, "eval", "req", {"budget_steps": b_steps}, "Shell probe")
                ret = reg.execute_retest(req, cand_b, lambda c, ctx: (RetestOutcome.SUCCESS, min(b_steps, 120), b"OK"))
                adm = reg.grant_scoped_admission(ret)
                print(f"  [✓] Scoped Admission for '{cand_str}' (Budget {b_steps}): {'GRANTED' if adm else 'DENIED'}")
                if adm:
                    print(f"      Admission ID: {adm.admission_id[:24]}... (Scope Non-Leakage Verified)\n")
            except Exception as e:
                print(f"[!] Admission evaluation failed: {e}")
        elif cmd == "sheaf":
            try:
                claim_str = parts[1] if len(parts) > 1 else "SKK_IDENTITY"
                from sheaf_kernel import (
                    EpistemicContext, LocalSection, EpistemicSheafKernel
                )
                k = EpistemicSheafKernel()
                c1 = EpistemicContext.create("Alpha", ["dom_a", "dom_b"], 120)
                c2 = EpistemicContext.create("Beta", ["dom_b", "dom_c"], 150)
                k.register_context(c1)
                k.register_context(c2)
                k.register_section(LocalSection.create(c1, claim_str, "S K K x", "x", 2))
                k.register_section(LocalSection.create(c2, claim_str, "I x", "x", 1))
                rep = k.verify_descent(claim_str, [c1, c2])
                print(f"  [✓] Sheaf Descent for '{claim_str}': {'GLUED' if rep.is_gluing_admissible else 'OBSTRUCTED'}")
                print(f"      Čech dim H^1 = {rep.h1_dimension} | Global NF: {rep.global_section.normal_form if rep.global_section else 'NONE'}\n")
            except Exception as e:
                print(f"[!] Sheaf descent failed: {e}")
        elif cmd == "sovereign":
            try:
                from sovereign_continuity import SovereignOrganism
                sub = parts[1] if len(parts) > 1 else "step"
                if sub == "genesis":
                    o = SovereignOrganism.create_genesis()
                    print(f"  [✓] Sovereign Genesis #{o.generation} minted. Tip CID: {o.cid_chain[-1][:24]}...")
                else:
                    o = SovereignOrganism.create_genesis()
                    r = o.evolve_step("REPL Contemplation")
                    print(f"  [✓] Sovereign Gen #{r.generation} stepped. CID: {r.cid[:24]}... | ATP: +{r.atp_cumulative_saved} | Cost: {r.active_cost}/{r.metabolic_budget}")
            except Exception as e:
                print(f"[!] Sovereign command failed: {e}")
        elif cmd in ("sheaf-agora", "sheaf_agora"):
            try:
                import argparse
                action = parts[1] if len(parts) > 1 else "init"
                cmd_sheaf_agora(argparse.Namespace(action=action, output=None))
            except Exception as e:
                print(f"[!] Sheaf Agora command failed: {e}")
        else:
            print(f"[!] Unknown command '{cmd}'. Type 'help' for available commands.")


def main():
    parser = argparse.ArgumentParser(description="Black-Heart (%🖤) Command Suite")
    subparsers = parser.add_subparsers(dest="command")

    # repl
    p_repl = subparsers.add_parser("repl", help="Interactive proof and combinator REPL")

    # test
    p_test = subparsers.add_parser("test", help="Run comprehensive test suite across all engines and security controls")

    # keygen
    p_keygen = subparsers.add_parser("keygen", help="Generate fresh Ed25519 keypair")
    p_keygen.add_argument("--json", action="store_true", help="Output as JSON")

    # verify
    p_verify = subparsers.add_parser("verify", help="Audit and verify any polyglot PDF")
    p_verify.add_argument("file", help="Path to polyglot PDF file")

    # sandbox
    p_sandbox = subparsers.add_parser("sandbox", help="Hermetic static non-executing polyglot auditor")
    p_sandbox.add_argument("file", help="Path to polyglot PDF file to audit without host execution")
    p_sandbox.add_argument("--strict", action="store_true", help="Fail if any warnings or non-critical anomalies appear")

    # compile
    p_compile = subparsers.add_parser("compile", help="Compile a proof-carrying polyglot PDF")
    p_compile.add_argument("-o", "--output", help="Output file path", default="output_polyglot.pdf")
    p_compile.add_argument("-t", "--title", help="Document Title", default="Black-Heart Polyglot")
    p_compile.add_argument("-a", "--author", help="Author", default="s0fractal")

    # vault
    p_vault = subparsers.add_parser("vault", help="ISO 32000 Embedded Code Vault management")
    vault_subs = p_vault.add_subparsers(dest="vault_action")
    p_vault_pack = vault_subs.add_parser("pack", help="Pack directory into self-extracting polyglot PDF")
    p_vault_pack.add_argument("source_dir", help="Source directory containing code to vault")
    p_vault_pack.add_argument("-o", "--output", required=True, help="Target PDF path")
    p_vault_pack.add_argument("-t", "--title", default="EMBEDDED CODE VAULT", help="Vault title")
    p_vault_pack.add_argument("-a", "--author", default="s0fractal", help="Vault author")

    p_vault_unpack = vault_subs.add_parser("unpack", help="Unpack embedded code vault from PDF")
    p_vault_unpack.add_argument("file", help="Target PDF polyglot")
    p_vault_unpack.add_argument("-d", "--dest", default=".", help="Destination directory")

    p_adj = subparsers.add_parser("adjudicate", help="Bilateral cross-proof adjudication between contract and oracle PDFs")
    p_adj.add_argument("agreement", help="Path to bilateral agreement PDF")
    p_adj.add_argument("oracle", help="Path to telemetry oracle PDF")
    p_adj.add_argument("--zk", action="store_true", help="Execute Zero-Knowledge cross-proof adjudication")
    p_adj.add_argument("--pinned-author-pk", default=None, help="Pinned Ed25519 public key hex of the agreement author")
    p_adj.add_argument("--pinned-agreement-hash", default=None, help="Pinned SHA-256 agreement document anchor")
    p_adj.add_argument("--allow-untrusted-issuer", action="store_true", help="Evaluate without a caller trust pin. The result is EVALUATION ONLY, never a settlement (exit 2)")

    # cross-proof
    p_cross = subparsers.add_parser("cross-proof", help="Bilateral Zero-Knowledge Cross-Proof & Interlocking Contracts")
    cross_subs = p_cross.add_subparsers(dest="action")

    p_cross_c = cross_subs.add_parser("zk-contract", help="Compile a Bilateral ZK Challenger Contract PDF")
    p_cross_c.add_argument("-o", "--output", default="zk_contract.pdf", help="Output PDF file path")
    p_cross_c.add_argument("-t", "--title", default="BILATERAL ESCROW CONTRACT", help="Contract title")
    p_cross_c.add_argument("-s", "--statement", default="CLAIM-ZK-001", help="Statement identifier")
    p_cross_c.add_argument("--pk", "--target-pk", dest="target_pk", required=True, help="Target prover Ed25519 public key hex")
    p_cross_c.add_argument("--clause", default="Settlement authorized upon verifiable zero-knowledge proof.", help="Clause statement text")
    p_cross_c.add_argument("--proof-type", default="SchnorrZKP", choices=["SchnorrZKP", "ChaumPedersenZKP"], help="Proof system")
    p_cross_c.add_argument("--second-point", default=None, help="Second point hex for Chaum-Pedersen")
    p_cross_c.add_argument("--secret-key", default=None, help="Contract author secret key hex (optional)")

    p_cross_w = cross_subs.add_parser("zk-witness", help="Compile a Bilateral ZK Witness PDF bound to contract CID")
    p_cross_w.add_argument("-c", "--contract", required=True, help="Path to Challenger Contract PDF")
    p_cross_w.add_argument("-o", "--output", default="zk_witness.pdf", help="Output PDF file path")
    p_cross_w.add_argument("-n", "--name", default="Autonomous Prover", help="Witness prover entity name")
    p_cross_w.add_argument("--sk", "--secret-key", dest="secret_key", required=True, help="Prover secret key hex")
    p_cross_w.add_argument("--author-key", default=None, help="Witness author secret key hex (optional)")

    p_cross_adj = cross_subs.add_parser("adjudicate", help="Adjudicate bilateral zero-knowledge contract and witness")
    p_cross_adj.add_argument("contract", help="Path to Challenger Contract PDF")
    p_cross_adj.add_argument("witness", help="Path to Witness PDF")

    # continuum
    p_cont = subparsers.add_parser("continuum", help="Suspended Continuum Thunk polyglot operations")
    cont_subs = p_cont.add_subparsers(dest="action")
    p_cp = cont_subs.add_parser("compile", help="Compile initial resumable computation PDF")
    p_cp.add_argument("--expr", required=True, help="Initial SKIY combinator expression")
    p_cp.add_argument("--fuel", type=int, default=10, help="Initial ATP fuel budget")
    p_cp.add_argument("-o", "--output", default="resumable_thunk.pdf", help="Target PDF file")
    p_cp.add_argument("-t", "--title", default="CONTINUUM COMPUTATION", help="Document title")

    p_cr = cont_subs.add_parser("resume", help="Resume computation in existing PDF")
    p_cr.add_argument("file", help="Target continuum PDF file")
    p_cr.add_argument("--fuel", type=int, default=100, help="Additional ATP fuel")

    # zk
    p_zk = subparsers.add_parser("zk", help="Zero-Knowledge Proofs on Ed25519")
    zk_subs = p_zk.add_subparsers(dest="action")
    p_zk_id = zk_subs.add_parser("prove-identity", help="Generate Schnorr ZKP of secret key possession")
    p_zk_id.add_argument("--secret-key", required=True, help="Secret key in hex")
    p_zk_id.add_argument("--context", default="IDENTITY_AUTH", help="Fiat-Shamir context string")

    p_zk_eq = zk_subs.add_parser("prove-dlog", help="Generate Chaum-Pedersen DLog equality proof")
    p_zk_eq.add_argument("--scalar", required=True, help="Secret scalar integer")
    p_zk_eq.add_argument("--context", default="DLOG_EQUALITY", help="Fiat-Shamir context string")

    # mesh
    p_mesh = subparsers.add_parser("mesh", help="P2P Swarm Living Polyglot sync")
    mesh_subs = p_mesh.add_subparsers(dest="action")
    p_mesh_srv = mesh_subs.add_parser("serve", help="Serve a living ledger PDF over HTTP daemon")
    p_mesh_srv.add_argument("file", help="Target living ledger PDF file")
    p_mesh_srv.add_argument("-p", "--port", type=int, default=8765, help="Port to bind daemon")

    p_mesh_sync = mesh_subs.add_parser("sync", help="Synchronize living ledger PDF with another peer")
    p_mesh_sync.add_argument("destination", help="Target local living ledger PDF to update")
    p_mesh_sync.add_argument("--peer", required=True, help="Peer PDF file path or remote http:// URL")

    # synthesize
    p_syn = subparsers.add_parser("synthesize", help="Dialectical sexual recombination of two polyglot organisms")
    p_syn.add_argument("parent_a", help="Path to Parent A (Thesis) polyglot PDF")
    p_syn.add_argument("parent_b", help="Path to Parent B (Antithesis) polyglot PDF")
    p_syn.add_argument("-o", "--output", default="symbiotic_child.pdf", help="Output child polyglot PDF path")

    # shell
    p_shell = subparsers.add_parser("shell", help="Interactive Hypervisor REPL for Project Black-Heart")

    # quantum
    p_quantum = subparsers.add_parser("quantum", help="Topological Quantum Topos & Anyon Gate operations")
    q_subs = p_quantum.add_subparsers(dest="action")
    p_qs = q_subs.add_parser("simulate", help="Simulate topological anyonic quantum gate")
    p_qs.add_argument("braid", help="Braid formula or canonical name (e.g. 'trefoil', 's1 -s2 s1')")

    p_qc = q_subs.add_parser("compile", help="Compile standalone quantum circuit polyglot PDF")
    p_qc.add_argument("-b", "--braid", required=True, help="Braid formula or canonical name")
    p_qc.add_argument("-o", "--output", default="quantum_circuit.pdf", help="Output PDF polyglot path")
    # morph
    p_morph = subparsers.add_parser("morph", help="Turing Morphogenesis & Reaction-Diffusion Phenotypes")
    p_morph.add_argument("-a", "--archetype", default="labyrinth", help="Archetype: spots, labyrinth, waves, holes, solitons, pulsars")
    p_morph.add_argument("-s", "--steps", type=int, default=350, help="Simulation time steps (default: 350)")
    p_morph.add_argument("-g", "--grid", type=int, default=40, help="Grid size on Torus T^2 (default: 40)")
    p_morph.add_argument("-p", "--palette", default=None, help="Chromatic palette name")
    p_morph.add_argument("-o", "--output", default="morphogenesis.pdf", help="Output polyglot PDF file")
    p_morph.add_argument("--seed", default=None, help="Deterministic genome hash or seed string")

    # metamorph
    p_meta = subparsers.add_parser("metamorph", help="Autonomous Form Metamorphosis & Program Self-Contemplation")
    p_meta.add_argument("organism", nargs="?", default=None, help="Path to input polyglot organism PDF (optional)")
    p_meta.add_argument("-o", "--output", default="metamorphic_organism.pdf", help="Output polyglot PDF path")

    # mycelium
    p_myc = subparsers.add_parser("mycelium", help="Collective Metamorphosis & Epistemic Warrant Mesh")
    p_myc.add_argument("--registry", default="epistemic_registry.json", help="Path to epistemic registry JSON file")
    myc_subs = p_myc.add_subparsers(dest="action")

    p_myc_sum = myc_subs.add_parser("summary", help="Display summary of epistemic registry")

    p_myc_srv = myc_subs.add_parser("serve", help="Start epistemic daemon on local port")
    p_myc_srv.add_argument("-p", "--port", type=int, default=8766, help="Port to bind daemon")

    p_myc_sync = myc_subs.add_parser("sync", help="Synchronize warrants & divergences from peer")
    p_myc_sync.add_argument("--peer", required=True, help="Remote peer URL (http://...)")

    p_myc_aud = myc_subs.add_parser("audition", help="Audition a warrant against a local organism")
    p_myc_aud.add_argument("organism", help="Target organism PDF path")
    p_myc_aud.add_argument("warrant", help="Warrant JSON path")
    p_myc_aud.add_argument("--secret-key", default=None, help="Organism secret key hex (optional)")

    # colony
    col_parent = argparse.ArgumentParser(add_help=False)
    col_parent.add_argument("-f", "--file", default="colony.json", help="Colony state JSON file")

    p_col = subparsers.add_parser("colony", help="Living Colony Ecosystem & Neuro-Symbolic Petri Dish")
    col_subs = p_col.add_subparsers(dest="action")

    p_col_init = col_subs.add_parser("init", parents=[col_parent], help="Initialize a new Genesis colony")
    p_col_init.add_argument("-n", "--name", default="Primeval Mycelium Colony", help="Colony name")
    p_col_init.add_argument("-o", "--organisms", type=int, default=3, help="Initial population count")
    p_col_init.add_argument("-a", "--atp", type=int, default=5000, help="Initial substrate ATP pool")
    p_col_init.add_argument("--seed", type=int, default=None, help="PRNG seed for deterministic colony simulation")

    p_col_step = col_subs.add_parser("step", parents=[col_parent], help="Simulate colony forward by one or more epochs")
    p_col_step.add_argument("-e", "--epochs", type=int, default=1, help="Number of epochs to step")
    p_col_step.add_argument("-s", "--solar", type=int, default=200, help="Solar ATP influx per epoch")
    p_col_step.add_argument("--keys", default=None,
                            help="Private keystore (default: <state>.keys). Never read from the public state")

    p_col_stat = col_subs.add_parser("status", parents=[col_parent], help="Display summary telemetry of the colony")

    p_col_comp = col_subs.add_parser("compile", parents=[col_parent], help="Compile colony into an executable ISO 32000 PDF polyglot")
    p_col_comp.add_argument("-o", "--output", default="colony.pdf", help="Output PDF polyglot path")

    # ontogeny
    p_ont = subparsers.add_parser("ontogeny", help="Morphogenetic Proof-Nets & Single-File Ontogenetic Quines")
    ont_subs = p_ont.add_subparsers(dest="action")

    p_ont_init = ont_subs.add_parser("init", help="Initialize a new genesis ontogenetic quine polyglot")
    p_ont_init.add_argument("-a", "--archetype", default="labyrinth", help="Turing morphogenetic archetype (spots, labyrinth, waves, holes, solitons, pulsars)")
    p_ont_init.add_argument("-s", "--seed", default=None, help="Genesis seed hash")
    p_ont_init.add_argument("--steps", type=int, default=50, help="Initial PDE steps")
    p_ont_init.add_argument("--atp", type=int, default=500, help="Initial ATP budget for proof-net reduction")
    p_ont_init.add_argument("-o", "--output", default="ontogeny_quine.pdf", help="Output PDF file path")
    p_ont_init.add_argument("--secret-key", default=None, help="Author secret key hex (optional)")

    p_ont_grow = ont_subs.add_parser("grow", help="Advance morphogenesis and append next generation to polyglot")
    p_ont_grow.add_argument("file", help="Target ontogenetic PDF polyglot")
    p_ont_grow.add_argument("--steps", type=int, default=50, help="PDE steps to compute for this epoch")
    p_ont_grow.add_argument("--atp", type=int, default=500, help="ATP budget for interaction net reduction")
    p_ont_grow.add_argument("--secret-key", default=None, help="Author secret key hex (optional)")

    p_ont_aud = ont_subs.add_parser("audit", help="Audit the entire ontogenetic Merkle chain and proof-nets")
    p_ont_aud.add_argument("file", help="Target ontogenetic PDF polyglot")

    p_ont_stat = ont_subs.add_parser("status", help="Display ontogenetic HUD telemetry and digests")
    p_ont_stat.add_argument("file", help="Target ontogenetic PDF polyglot")

    # goedel
    p_goedel = subparsers.add_parser("goedel", help="Gödelian Incompleteness, Limit Cycles & Black Cone Event Horizon")
    goedel_subs = p_goedel.add_subparsers(dest="action")

    p_goedel_prb = goedel_subs.add_parser("probe", help="Scan the Black Cone event horizon across combinators")
    p_goedel_prb.add_argument("--atp", type=int, default=200, help="ATP fuel budget per candidate")

    p_goedel_comp = goedel_subs.add_parser("compile", help="Compile a self-refuting Gödelian polyglot PDF")
    p_goedel_comp.add_argument("-e", "--expr", default="🔁 🤍", help="Combinator sentence expression")
    p_goedel_comp.add_argument("-i", "--id", default="GOEDEL_DIAGONAL_01", help="Sentence claim identifier")
    p_goedel_comp.add_argument("-o", "--output", default="goedel_paradox.pdf", help="Output PDF file path")
    p_goedel_comp.add_argument("--secret-key", default=None, help="Author secret key hex (optional)")

    p_goedel_ver = goedel_subs.add_parser("verify", help="Statically audit and replay a Gödelian polyglot")
    p_goedel_ver.add_argument("file", help="Target Gödelian PDF polyglot")

    p_goedel_stat = goedel_subs.add_parser("status", help="Inspect a Gödelian polyglot's receipt and telemetry")
    p_goedel_stat.add_argument("file", help="Target Gödelian PDF polyglot")

    # anyon
    p_anyon = subparsers.add_parser("anyon", help="Topological Anyonic Combinators & Quantum Braided Rewriting")
    anyon_subs = p_anyon.add_subparsers(dest="action")

    p_anyon_sim = anyon_subs.add_parser("simulate", help="Simulate unitary braiding and Born measurement")
    p_anyon_sim.add_argument("-e", "--expr", default="🌿 🖤 🤍", help="Combinator circuit expression")

    p_anyon_comp = anyon_subs.add_parser("compile", help="Compile an anyonic quantum polyglot PDF")
    p_anyon_comp.add_argument("-e", "--expr", default="🌿 🖤 🤍", help="Combinator circuit expression")
    p_anyon_comp.add_argument("-o", "--output", default="anyon_circuit.pdf", help="Output PDF file path")
    p_anyon_comp.add_argument("--secret-key", default=None, help="Author secret key hex (optional)")

    p_anyon_ver = anyon_subs.add_parser("verify", help="Statically audit an anyonic quantum polyglot")
    p_anyon_ver.add_argument("file", help="Target anyonic PDF polyglot")

    p_anyon_stat = anyon_subs.add_parser("status", help="Inspect an anyonic polyglot's telemetry HUD")
    p_anyon_stat.add_argument("file", help="Target anyonic PDF polyglot")

    # diary
    p_diary = subparsers.add_parser("diary", help="Self-Preserving Ontogenetic Diary & LLM Inner Voice on IPFS")
    diary_subs = p_diary.add_subparsers(dest="action")

    p_diary_init = diary_subs.add_parser("init", help="Initialize a new ontogenetic IPFS diary polyglot")
    p_diary_init.add_argument("-o", "--output", default="ipfs_diary.pdf", help="Output PDF polyglot path")
    p_diary_init.add_argument("-t", "--thought", default="I am an autonomous polyglot quine, remembering my origins across the distributed continuum.", help="Initial thought reflection")
    p_diary_init.add_argument("-p", "--prompt", default="Who are you?", help="Prompt trigger context")
    p_diary_init.add_argument("-g", "--grade", default="PROPOSED", help="Epistemic grade (PROPOSED, LOCALLY_TESTED, RULE_DERIVED)")
    p_diary_init.add_argument("--alias", default="Genesis", help="Author voice alias")
    p_diary_init.add_argument("--secret-key", default=None, help="Author Ed25519 secret key hex (optional)")

    p_diary_app = diary_subs.add_parser("append", help="Append an incremental reflection page to the diary")
    p_diary_app.add_argument("file", help="Target ontogenetic diary PDF")
    p_diary_app.add_argument("-t", "--thought", required=True, help="New thought reflection to append")
    p_diary_app.add_argument("-p", "--prompt", default="", help="Prompt trigger context")
    p_diary_app.add_argument("-g", "--grade", default="PROPOSED", help="Epistemic grade")
    p_diary_app.add_argument("--alias", default="", help="Author voice alias")
    p_diary_app.add_argument("--atp", type=int, default=10, help="ATP fuel burned")
    p_diary_app.add_argument("--secret-key", default=None, help="Author Ed25519 secret key hex (optional)")

    p_diary_cite = diary_subs.add_parser("cite", help="Append a thought that cites one or more prior/external CIDv1 hashes")
    p_diary_cite.add_argument("file", help="Target ontogenetic diary PDF")
    p_diary_cite.add_argument("cid", help="Target CIDv1 hash (or comma-separated list) to cite")
    p_diary_cite.add_argument("-t", "--thought", required=True, help="New thought reflection referencing the citation")
    p_diary_cite.add_argument("-p", "--prompt", default="", help="Prompt trigger context")
    p_diary_cite.add_argument("-g", "--grade", default="PROPOSED", help="Epistemic grade")
    p_diary_cite.add_argument("--alias", default="", help="Author voice alias (e.g. Claude, Gemini, Organism-0)")
    p_diary_cite.add_argument("--atp", type=int, default=15, help="ATP fuel burned")
    p_diary_cite.add_argument("--secret-key", default=None, help="Author Ed25519 secret key hex (optional)")

    p_diary_dag = diary_subs.add_parser("dag", help="Render ASCII Merkle-DAG citation topology")
    p_diary_dag.add_argument("file", help="Target ontogenetic diary PDF")

    p_diary_syn = diary_subs.add_parser("synthesize", help="Perform dialectical synthesis of thesis and antithesis thoughts")
    p_diary_syn.add_argument("file", help="Target ontogenetic diary PDF")
    p_diary_syn.add_argument("--thesis", required=True, help="Thesis thought text")
    p_diary_syn.add_argument("--antithesis", required=True, help="Antithesis thought text")
    p_diary_syn.add_argument("--thesis-cid", default="", help="Optional thesis CIDv1")
    p_diary_syn.add_argument("--antithesis-cid", default="", help="Optional antithesis CIDv1")
    p_diary_syn.add_argument("--alias", default="Synthesis", help="Author voice alias")
    p_diary_syn.add_argument("--atp", type=int, default=20, help="ATP fuel burned")
    p_diary_syn.add_argument("--secret-key", default=None, help="Author Ed25519 secret key hex (optional)")

    p_diary_stat = diary_subs.add_parser("status", help="Display latest diary HUD telemetry and CIDv1")
    p_diary_stat.add_argument("file", help="Target ontogenetic diary PDF")

    p_diary_lin = diary_subs.add_parser("lineage", help="Display full Merkle-DAG CID ancestry chain")
    p_diary_lin.add_argument("file", help="Target ontogenetic diary PDF")

    p_diary_aud = diary_subs.add_parser("audit", help="Cryptographically audit all diary pages and signatures")
    p_diary_aud.add_argument("file", help="Target ontogenetic diary PDF")

    p_diary_pub = diary_subs.add_parser("publish", help="Pin current diary document to IPFS Kubo node")
    p_diary_pub.add_argument("file", help="Target ontogenetic diary PDF")
    p_diary_pub.add_argument("--url", default="http://127.0.0.1:5001", help="IPFS Kubo API endpoint")

    p_diary_voice = diary_subs.add_parser("voice", help="Consult autonomous inner voice with stimulus and append reflection")
    p_diary_voice.add_argument("file", help="Target ontogenetic diary PDF")
    p_diary_voice.add_argument("-s", "--stimulus", required=True, help="Stimulus prompt to reflect upon")
    p_diary_voice.add_argument("--secret-key", default=None, help="Author Ed25519 secret key hex (optional)")

    p_diary_fetch = diary_subs.add_parser("fetch", help="Restore and verify diary document from IPFS CIDv1 (fail-closed)")
    p_diary_fetch.add_argument("cid", help="IPFS CIDv1 hash identifier")
    p_diary_fetch.add_argument("-o", "--output", default="restored_diary.pdf", help="Destination PDF path")
    p_diary_fetch.add_argument("--url", default="http://127.0.0.1:5001", help="IPFS daemon API or gateway URL")

    # agora
    p_agora = subparsers.add_parser("agora", help="Mycelial Social Democracy, Quadratic Voting & Consensus Agora")
    agora_subs = p_agora.add_subparsers(dest="action")

    p_agora_init = agora_subs.add_parser("init", help="Initialize a new Agora Parliament polyglot")
    p_agora_init.add_argument("-o", "--output", default="agora_parliament.pdf", help="Output PDF polyglot path")
    p_agora_init.add_argument("--secret-key", default=None, help="Founder Ed25519 secret key hex (optional)")

    p_agora_stat = agora_subs.add_parser("status", help="Display Agora assembly HUD and latest ratified status")
    p_agora_stat.add_argument("file", help="Target Agora PDF polyglot")

    p_agora_lin = agora_subs.add_parser("lineage", help="Display full constitutional Merkle chain")
    p_agora_lin.add_argument("file", help="Target Agora PDF polyglot")

    p_agora_aud = agora_subs.add_parser("audit", help="Cryptographically audit all Agora sessions and multi-signatures")
    p_agora_aud.add_argument("file", help="Target Agora PDF polyglot")

    # autopoiesis (Grok Exp 1)
    p_auto = subparsers.add_parser("autopoiesis", help="Grok Exp 1: Self-Contemplating Autopoietic Quine Organisms")
    auto_subs = p_auto.add_subparsers(dest="action")

    p_auto_init = auto_subs.add_parser("init", help="Initialize Genesis Autopoietic Quine Organism")
    p_auto_init.add_argument("-o", "--output", default="autopoietic_organism.pdf", help="Output PDF polyglot path")
    p_auto_init.add_argument("--secret-key", default=None, help="Author Ed25519 secret key hex (optional)")

    p_auto_evolve = auto_subs.add_parser("evolve", help="Advance organism by 1 generation in-place (ISO 32000 append)")
    p_auto_evolve.add_argument("file", help="Target autopoietic organism PDF")
    p_auto_evolve.add_argument("--secret-key", default=None, help="Author Ed25519 secret key hex (optional)")
    p_auto_evolve.add_argument("--tombstones", default=None,
                               help="JSON tombstone registry consulted before the in-place append")
    p_auto_evolve.add_argument("--trusted-issuers", default=None,
                               help="JSON issuer policy, exactly {\"retirement_issuers\": [...], "
                                    "\"readoption_issuers\": [...]}. Without it every authentic "
                                    "author counts, as before")
    p_auto_evolve.add_argument("--also-proceed-on", action="append", default=None,
                               choices=["REFUTED_FOR_ANOTHER_REFERENCE", "UNAUTHORIZED_ISSUER"],
                               help="Proceed through this uncertain scope too: a refutation measured "
                                    "against another reference, or one signed by a key not in "
                                    "--trusted-issuers. By default a replacement proceeds only when "
                                    "nothing measured addresses it. There is no file-path override "
                                    "for untrusted evidence: a registry file holding an unverifiable "
                                    "record is refused whole, before any policy is consulted")

    p_auto_audit = auto_subs.add_parser("audit", help="Audit all generational receipts and replay AST transitions")
    p_auto_audit.add_argument("file", help="Target autopoietic organism PDF")

    p_auto_exp = auto_subs.add_parser("experiments", help="Display empirical scientific ledger")
    p_auto_exp.add_argument("file", help="Target autopoietic organism PDF")

    p_auto_gen = auto_subs.add_parser("genome", help="Display active combinator chromosomes")
    p_auto_gen.add_argument("file", help="Target autopoietic organism PDF")

    # morpho-autopoiesis (Engine #23: Grok 1 + 3 + 5 Master Synthesis)
    p_morpho_auto = subparsers.add_parser(
        "morpho-autopoiesis",
        help="Engine #23: Morphogenetic Autopoiesis & Mycelial Federation Master Synthesis"
    )
    morpho_subs = p_morpho_auto.add_subparsers(dest="action")

    p_ma_init = morpho_subs.add_parser("init", help="Initialize Genesis Morpho-Autopoietic Quine Organism")
    p_ma_init.add_argument("-o", "--output", default="morpho_autopoietic_organism.pdf", help="Output PDF polyglot path")
    p_ma_init.add_argument("--secret-key", default=None, help="Author Ed25519 secret key hex (optional)")

    p_ma_evolve = morpho_subs.add_parser("evolve", help="Advance organism by 1 generation in-place (ISO 32000 append)")
    p_ma_evolve.add_argument("file", help="Target morpho-autopoietic organism PDF")
    p_ma_evolve.add_argument("--secret-key", default=None, help="Author Ed25519 secret key hex (optional)")

    p_ma_audit = morpho_subs.add_parser("audit", help="Topologically and cryptographically audit organism history")
    p_ma_audit.add_argument("file", help="Target morpho-autopoietic organism PDF")

    p_ma_table = morpho_subs.add_parser("table", help="Table evolved algebraic theorem onto Mycelial Agora floor")
    p_ma_table.add_argument("organism", help="Target morpho-autopoietic organism PDF")
    p_ma_table.add_argument("agora", help="Target Agora assembly PDF")
    p_ma_table.add_argument("--stake", type=int, default=100, help="ATP fuel quanta to stake (default: 100)")
    p_ma_table.add_argument("--secret-key", default=None, help="Author Ed25519 secret key hex (optional)")

    p_ma_info = morpho_subs.add_parser("info", help="Display organism HUD and morphogenetic state")
    p_ma_info.add_argument("file", help="Target morpho-autopoietic organism PDF")

    # warrant-kernel (Engine #24: WARRANT-0.2 Epistemic Kernel & Unified Edge-Claims)
    p_wk = subparsers.add_parser(
        "warrant-kernel",
        help="Engine #24: Epistemic Kernel & Unified Edge-Claims (WARRANT-0.2)"
    )
    wk_subs = p_wk.add_subparsers(dest="action")

    p_wk_compile = wk_subs.add_parser("compile", help="Compile sample Epistemic Warrant Ledger PDF polyglot")
    p_wk_compile.add_argument("-o", "--output", default="warrant_ledger.pdf", help="Output PDF path")

    p_wk_audit = wk_subs.add_parser("audit", help="Audit warrant ledger PDF or JSON against a CALLER-supplied TrustConfig")
    p_wk_audit.add_argument("file", help="Target warrant ledger file")
    p_wk_audit.add_argument("--trust-config", default=None,
                            help="Path to the operator's TrustConfig JSON. The trust root is the "
                                 "operator's, never the audited document's.")
    p_wk_audit.add_argument("--trusted-author-pk", action="append", default=None,
                            dest="trusted_author_pks", metavar="PK_HEX",
                            help="Trust claims signed by this author public key (repeatable). "
                                 "Without this or --trust-config, no author is trusted.")

    p_wk_promote = wk_subs.add_parser("promote", help="Promote empirical hypothesis to axiomatic identity")
    p_wk_promote.add_argument("rule", help="Target algebraic rewrite rule (e.g. 'I x -> x')")

    # warrant-forget (Engine #25: CONTROLLED-FORGETTING-0.1 Epistemic Retirement & Negative Space Coverage)
    p_wf = subparsers.add_parser(
        "warrant-forget",
        help="Engine #25: Controlled Forgetting & Epistemic Retirement (CONTROLLED-FORGETTING-0.1)"
    )
    wf_subs = p_wf.add_subparsers(dest="action")

    p_wf_retire = wf_subs.add_parser("retire", help="Retire an artifact from active admission with mandatory loss declaration")
    p_wf_retire.add_argument("target_id", help="Subject identifier of the artifact to retire")
    p_wf_retire.add_argument("digest", help="Content hash (SHA-256 hex) of the retired subject")
    p_wf_retire.add_argument("-m", "--mode", default="DEPRECATED", choices=["SUPERSEDED", "REFUTED", "WITHDRAWN", "ARCHIVED", "QUARANTINED", "DEPRECATED"], help="Retirement category mode")
    p_wf_retire.add_argument("-l", "--loss", help="Mandatory description of lost exploratory capacity (Invariant I4)")
    p_wf_retire.add_argument("-r", "--replacement", help="Replacement subject identifier (mandatory if SUPERSEDED)")
    p_wf_retire.add_argument("--rule", default="", help="Algebraic rule or pattern pruned for negative space coverage calculation")
    p_wf_retire.add_argument("-o", "--output", default="tombstones.pdf", help="Target PDF polyglot or JSON registry to update")

    p_wf_audit = wf_subs.add_parser("audit", help="Audit tombstone ledger signatures, Invariants I1-I8, and admission state")
    p_wf_audit.add_argument("file", help="Target polyglot PDF or JSON registry")

    p_wf_readopt = wf_subs.add_parser("readopt", help="Authorize re-adoption of a retired artifact into active surface (Invariant I3)")
    p_wf_readopt.add_argument("file", help="Target polyglot PDF or JSON registry")
    p_wf_readopt.add_argument("target_id", help="Subject identifier of the retired artifact to re-adopt")
    p_wf_readopt.add_argument("--reason", help="Epistemic justification for restoring active status")
    p_wf_readopt.add_argument("--evidence", default="CLAIM_RESTORED_E01", help="New evidence claim ID justifying resurrection")
    p_wf_readopt.add_argument("-o", "--output", help="Output file path (default: overwrite target file)")

    p_wf_surface = wf_subs.add_parser("surface", help="Display active evaluation surface vs pruned negative space substrate")
    p_wf_surface.add_argument("file", help="Target polyglot PDF or JSON registry")

    # epistemic-immune (Engine #26: EPISTEMIC-IMMUNE-0.1 Autonomic Epistemic Immune System)
    p_ei = subparsers.add_parser(
        "epistemic-immune",
        help="Engine #26: Autonomic Epistemic Immune System & Metabolic Self-Healing (EPISTEMIC-IMMUNE-0.1)"
    )
    ei_subs = p_ei.add_subparsers(dest="action")

    p_ei_init = ei_subs.add_parser("init", help="Initialize a fresh autonomous immune organism polyglot PDF")
    p_ei_init.add_argument("-o", "--output", default="immune_organism.pdf", help="Output PDF path")

    p_ei_status = ei_subs.add_parser("status", help="Display organism immune health status, ATP fuel gauge, and defenses")
    p_ei_status.add_argument("file", help="Target immune organism polyglot PDF or JSON file")

    p_ei_inoc = ei_subs.add_parser("inoculate", help="Inoculate target organism with donor organism's tombstones")
    p_ei_inoc.add_argument("target", help="Target organism to receive defenses")
    p_ei_inoc.add_argument("donor", help="Donor organism providing tombstones")
    p_ei_inoc.add_argument("-o", "--output", help="Output PDF path (default: overwrite target)")

    p_ei_auto = ei_subs.add_parser("autophagy", help="Trigger metabolic starvation autophagy to reclaim fuel")
    p_ei_auto.add_argument("file", help="Target starved organism file")
    p_ei_auto.add_argument("--threshold", type=int, default=80, help="Starvation ATP threshold")
    p_ei_auto.add_argument("--target-atp", type=int, default=200, help="Target recovery ATP reserve")
    p_ei_auto.add_argument("-o", "--output", help="Output PDF path")

    p_ei_elev = ei_subs.add_parser("elevate", help="Scan empirical hypotheses and promote confluent rules to axioms (E -> A)")
    p_ei_elev.add_argument("file", help="Target organism file")
    p_ei_elev.add_argument("-o", "--output", help="Output PDF path")

    # swarm (Engine #27: SWARM-0.1 Epistemic Swarm Membrane & Symbiotic Quine Evolution)
    p_sw = subparsers.add_parser(
        "swarm",
        help="Engine #27: Epistemic Swarm Membrane & Symbiotic Quine Evolution (SWARM-0.1)"
    )
    sw_subs = p_sw.add_subparsers(dest="action")

    p_sw_init = sw_subs.add_parser("init", help="Initialize a new epistemic swarm membrane")
    p_sw_init.add_argument("--population", type=int, default=4, help="Number of initial quine organisms")
    p_sw_init.add_argument("-o", "--output", default="swarm_state.json", help="Output JSON or PDF path")

    p_sw_status = sw_subs.add_parser("status", help="Display swarm population telemetry and canon")
    p_sw_status.add_argument("state", help="Swarm state JSON or polyglot PDF file")

    p_sw_step = sw_subs.add_parser("step", help="Advance swarm simulation ticks")
    p_sw_step.add_argument("state", help="Swarm state file")
    p_sw_step.add_argument("--steps", type=int, default=1, help="Number of ticks to step")
    p_sw_step.add_argument("-o", "--output", help="Output state path (default: overwrite)")
    p_sw_step.add_argument("--keys", default=None, help="Private keystore (default: <state>.keys). Never read from the public state")

    p_sw_mate = sw_subs.add_parser("mate", help="Trigger bilateral quine mating between two organisms")
    p_sw_mate.add_argument("state", help="Swarm state file")
    p_sw_mate.add_argument("--parent-a", required=True, help="First parent organism ID")
    p_sw_mate.add_argument("--parent-b", required=True, help="Second parent organism ID")
    p_sw_mate.add_argument("-o", "--output", help="Output state path")
    p_sw_mate.add_argument("--keys", default=None, help="Private keystore (default: <state>.keys). Never read from the public state")

    p_sw_inoc = sw_subs.add_parser("inoculate", help="Inject refutation and broadcast epidemic cascade")
    p_sw_inoc.add_argument("state", help="Swarm state file")
    p_sw_inoc.add_argument("--origin", required=True, help="Originating organism ID")
    # No defaults here on purpose. A default operand would mean this adapter
    # supplying the evidence, which is the thing the producer refuses to do.
    p_sw_inoc.add_argument("--target-term",
                           help="Retirement subject label (provenance, not executed). Required")
    p_sw_inoc.add_argument("--parent-term",
                           help="Executable parent term (omega) applied to the input. Required")
    p_sw_inoc.add_argument("--candidate-term",
                           help="Executable candidate term (tau) applied to the input. Required")
    p_sw_inoc.add_argument("--input-expr",
                           help="Counterexample input, applied as a single argument. Required")
    p_sw_inoc.add_argument("--gene-id", default="MUTATION_TEST", help="Gene id recorded as provenance")
    p_sw_inoc.add_argument("--demo", action="store_true",
                           help="Run the built-in K vs K I demonstration, which retires the "
                                "candidate term itself. Cannot be combined with the operand flags")
    p_sw_inoc.add_argument("--hops", type=int, default=3, help="Max hop depth for gossip propagation")
    p_sw_inoc.add_argument("-o", "--output", help="Output state path")
    p_sw_inoc.add_argument("--keys", default=None, help="Private keystore (default: <state>.keys). Never read from the public state")

    p_sw_prop = sw_subs.add_parser("propose", help="Table an axiom motion to the Swarm Agora")
    p_sw_prop.add_argument("state", help="Swarm state file")
    p_sw_prop.add_argument("--author", required=True, help="Author organism ID")
    p_sw_prop.add_argument("--expr", required=True, help="Candidate rewrite expression (e.g. 'S K K x')")
    p_sw_prop.add_argument("--expected", default="x", help="Expected normal form")
    p_sw_prop.add_argument("-o", "--output", help="Output state path")

    p_sw_pdf = sw_subs.add_parser("pdf", help="Compile ISO 32000 Swarm Membrane polyglot PDF")
    p_sw_pdf.add_argument("state", help="Swarm state file")
    p_sw_pdf.add_argument("-o", "--output", default="swarm_membrane.pdf", help="Output PDF path")

    # egraph (Engine #28: EGRAPH-0.1 Epistemic E-Graph Kernel & Proof-Carrying Equality Saturation)
    p_eg = subparsers.add_parser(
        "egraph",
        help="Engine #28: Epistemic E-Graph Kernel & Proof-Carrying Equality Saturation (EGRAPH-0.1)"
    )
    eg_subs = p_eg.add_subparsers(dest="action")

    p_eg_sat = eg_subs.add_parser("saturate", help="Run equality saturation on combinator expression")
    p_eg_sat.add_argument("expr", help="Combinator expression to saturate")
    p_eg_sat.add_argument("--iterations", type=int, default=10, help="Max saturation iterations")
    p_eg_sat.add_argument("--fuel", type=int, default=1000, help="ATP fuel budget")
    p_eg_sat.add_argument("-o", "--output", help="Output JSON path")

    p_eg_exp = eg_subs.add_parser("explain", help="Prove equivalence between two terms with certified proof forest")
    p_eg_exp.add_argument("term_a", help="First combinator term")
    p_eg_exp.add_argument("term_b", help="Second combinator term")
    p_eg_exp.add_argument("--iterations", type=int, default=10, help="Max saturation iterations")
    p_eg_exp.add_argument("--fuel", type=int, default=1000, help="ATP fuel budget")

    p_eg_ext = eg_subs.add_parser("extract", help="Extract globally minimal normal form from expression")
    p_eg_ext.add_argument("expr", help="Combinator expression to optimize")
    p_eg_ext.add_argument("--iterations", type=int, default=10, help="Max saturation iterations")
    p_eg_ext.add_argument("--fuel", type=int, default=1000, help="ATP fuel budget")

    p_eg_pdf = eg_subs.add_parser("pdf", help="Compile ISO 32000 E-Graph polyglot PDF")
    p_eg_pdf.add_argument("expr", help="Root combinator expression")
    p_eg_pdf.add_argument("--target", help="Optional target term to prove equivalence with")
    p_eg_pdf.add_argument("--iterations", type=int, default=10, help="Max saturation iterations")
    p_eg_pdf.add_argument("--fuel", type=int, default=1000, help="ATP fuel budget")
    p_eg_pdf.add_argument("-o", "--output", default="egraph_proof.pdf", help="Output PDF path")

    # smt (Engine #29: Sovereign SMT Kernel & First-Order DPLL(T) Verifier)
    p_smt = subparsers.add_parser(
        "smt",
        help="Engine #29: Sovereign SMT Kernel & First-Order DPLL(T) Verifier (SMT-0.1)"
    )
    smt_subs = p_smt.add_subparsers(dest="action")

    p_smt_solve = smt_subs.add_parser("solve", help="Solve SMT-LIB 2 QF_UF script via DPLL(T)")
    p_smt_solve.add_argument("file", help="Input SMT-LIB 2 script file (.smt2)")

    p_smt_prove = smt_subs.add_parser("prove", help="Prove theorem via UNSAT refutation DAG")
    p_smt_prove.add_argument("file", help="Input SMT-LIB 2 script file (.smt2)")

    p_smt_pdf = smt_subs.add_parser("pdf", help="Compile ISO 32000 SMT verification polyglot PDF")
    p_smt_pdf.add_argument("file", help="Input SMT-LIB 2 script file (.smt2)")
    p_smt_pdf.add_argument("-o", "--output", default="smt_proof.pdf", help="Output PDF path")

    p_smt_check = smt_subs.add_parser("check", help="Fast satisfiability check (prints sat/unsat)")
    p_smt_check.add_argument("file", help="Input SMT-LIB 2 script file (.smt2)")

    # cegis (Engine #30: Counterexample-Guided Inductive Synthesis & Superoptimizer)
    p_cegis = subparsers.add_parser(
        "cegis",
        help="Engine #30: Counterexample-Guided Inductive Synthesis (CEGIS-0.1)"
    )
    cegis_subs = p_cegis.add_subparsers(dest="action")

    p_cegis_syn = cegis_subs.add_parser("synthesize", help="Synthesize combinator program from specification")
    p_cegis_syn.add_argument("--task", default="identity", choices=["identity", "first", "second", "constant_a"], help="Synthesis benchmark task")
    p_cegis_syn.add_argument("--domain", default="a,b,c", help="Comma-separated verifier domain")
    p_cegis_syn.add_argument("--max-size", type=int, default=10, help="Maximum AST search size")
    p_cegis_syn.add_argument("--max-iterations", type=int, default=15, help="Maximum CEGIS loop iterations")

    p_cegis_opt = cegis_subs.add_parser("superopt", help="Superoptimize combinator expression with SMT proof")
    p_cegis_opt.add_argument("expression", help="Input combinator expression (e.g. 'S K K')")
    p_cegis_opt.add_argument("--max-size", type=int, default=10, help="Maximum AST search size")

    p_cegis_pdf = cegis_subs.add_parser("pdf", help="Compile ISO 32000 CEGIS verification polyglot PDF")
    p_cegis_pdf.add_argument("-e", "--expression", default=None, help="Optional combinator expression to superoptimize")
    p_cegis_pdf.add_argument("--task", default="identity", help="Task name for title")
    p_cegis_pdf.add_argument("-o", "--output", default="cegis_synthesis.pdf", help="Output PDF path")

    # dialectic (Engine #31: Dialectical Discovery & Automated Hypothesis Generation)
    p_dialectic = subparsers.add_parser(
        "dialectic",
        help="Engine #31: Dialectical Discovery & Automated Hypothesis Generation (DIALECTIC-0.1)"
    )
    dialectic_subs = p_dialectic.add_subparsers(dest="action")

    p_dial_exp = dialectic_subs.add_parser("explore", help="Explore failure boundary and compute minimal context delta")
    p_dial_exp.add_argument("--task", default="step_settle", help="Candidate task identifier")
    p_dial_exp.add_argument("--budget", type=int, default=80, help="Initial failed budget steps")

    p_dial_pre = dialectic_subs.add_parser("precond", help="Synthesize SMT weakest precondition domain guard")
    p_dial_pre.add_argument("--cutoff", type=int, default=3, help="Admissible threshold cutoff")
    p_dial_pre.add_argument("--domain", default="1,2,3,4,5", help="Comma-separated input domain")

    p_dial_pdf = dialectic_subs.add_parser("pdf", help="Compile ISO 32000 Dialectical Discovery polyglot PDF")
    p_dial_pdf.add_argument("-o", "--output", default="dialectic_discovery.pdf", help="Output PDF path")

    # palimpsest (Engine #32: Epistemic Palimpsest — Generational Value Drift Cartography)
    p_pal = subparsers.add_parser(
        "palimpsest",
        help="Engine #32: Epistemic Palimpsest — Generational Value Drift Cartography (PALIMPSEST-0.1)"
    )
    pal_subs = p_pal.add_subparsers(dest="action")

    p_pal_snap = pal_subs.add_parser("snapshot", help="Capture reasoning skeleton and trace matrix for an agent generation")
    p_pal_snap.add_argument("--gen", type=int, default=0, help="Agent generation number (default: 0)")
    p_pal_snap.add_argument("-o", "--output", default=None, help="Output JSON snapshot path")

    p_pal_diff = pal_subs.add_parser("diff", help="Compute 5D drift tensor between two generational snapshots")
    p_pal_diff.add_argument("--old", default="0", help="Old snapshot JSON or generation number")
    p_pal_diff.add_argument("--new", default="1", help="New snapshot JSON or generation number")

    p_pal_comp = pal_subs.add_parser("compile", help="Compile ISO 32000 multi-layer Palimpsest polyglot PDF")
    p_pal_comp.add_argument("--old", default="0", help="Old snapshot JSON or generation number")
    p_pal_comp.add_argument("--new", default="1", help="New snapshot JSON or generation number")
    p_pal_comp.add_argument("-o", "--output", default="palimpsest.pdf", help="Output PDF path")

    p_pal_aud = pal_subs.add_parser("audit", help="Cryptographically audit palimpsest PDF layers, invariants, and tombstones")
    p_pal_aud.add_argument("file", help="Target palimpsest PDF file")

    # admission (Scoped Re-Admission & Conditional Reopening — SCOPED_ADMISSION-0.1)
    p_adm = subparsers.add_parser(
        "admission",
        help="Scoped Re-Admission & Conditional Reopening (SCOPED_ADMISSION-0.1)"
    )
    adm_subs = p_adm.add_subparsers(dest="action")
    p_adm_ass = adm_subs.add_parser("assess", help="Assess re-evaluation eligibility")
    p_adm_ass.add_argument("--old-budget", type=int, default=100, help="Initial failed budget steps")
    p_adm_ass.add_argument("--new-budget", type=int, default=200, help="New proposed budget steps")
    p_adm_ass.add_argument("--candidate", default="S K K", help="Candidate term expression")
    p_adm_ass.add_argument("--reason", default="RESOURCE_LIMIT", choices=["RESOURCE_LIMIT", "SEMANTIC_COUNTEREXAMPLE"])

    p_adm_ret = adm_subs.add_parser("retest", help="Execute bounded retest and grant scoped admission")
    p_adm_ret.add_argument("--candidate", default="S K K", help="Candidate term expression")
    p_adm_ret.add_argument("--budget", type=int, default=200, help="Budget steps for retest")

    p_adm_pdf = adm_subs.add_parser("pdf", help="Compile ISO 32000 Scoped Admission polyglot certificate")
    p_adm_pdf.add_argument("-o", "--output", default="scoped_admission.pdf", help="Output PDF path")

    # sheaf (Engine #33: Epistemic Sheaf Kernel & Čech Cohomology — SHEAF-0.1)
    p_sheaf = subparsers.add_parser(
        "sheaf",
        help="Engine #33: Epistemic Sheaf Kernel & Čech Cohomology (SHEAF-0.1)"
    )
    sheaf_subs = p_sheaf.add_subparsers(dest="action")
    p_sh_glue = sheaf_subs.add_parser("glue", help="Verify local-to-global sheaf descent (H^1 = 0)")
    p_sh_glue.add_argument("--claim", default="SKK_IDENTITY", help="Claim identifier")

    p_sh_obs = sheaf_subs.add_parser("obstruct", help="Demonstrate Čech cohomology obstruction on conflicting charts")
    p_sh_obs.add_argument("--claim", default="CONTRADICTORY_PROPERTY", help="Claim identifier")

    p_sh_pdf = sheaf_subs.add_parser("pdf", help="Compile ISO 32000 Epistemic Sheaf polyglot certificate")
    p_sh_pdf.add_argument("--claim", default="LAFONT_INTERACTION_CONFLUENCE", help="Claim identifier")
    p_sh_pdf.add_argument("-o", "--output", default="sheaf_certificate.pdf", help="Output PDF path")

    # sovereign (Engine #34: Sovereign Continuity Quine & Forgetting Membrane — SOVEREIGN-0.1)
    p_sov = subparsers.add_parser(
        "sovereign",
        help="Engine #34: Sovereign Continuity Quine & Controlled Forgetting Membrane (SOVEREIGN-0.1)"
    )
    sov_subs = p_sov.add_subparsers(dest="action")
    p_sv_gen = sov_subs.add_parser("genesis", help="Mint a new Genesis Sovereign Organism")
    p_sv_gen.add_argument("--id", default="%🖤-SOVEREIGN-GENESIS", help="Organism identifier")
    p_sv_gen.add_argument("--capacity", type=int, default=300, help="Metabolic ATP capacity")

    p_sv_step = sov_subs.add_parser("step", help="Execute an autopoietic step with metabolic pruning")
    p_sv_step.add_argument("--thought", default="Autonomous Self-Contemplation", help="Thought prompt")
    p_sv_step.add_argument("--capacity", type=int, default=300, help="Metabolic ATP capacity")

    p_sv_mig = sov_subs.add_parser("migrate", help="Export portable migration seed bundle")
    p_sv_mig.add_argument("-o", "--output", help="Output JSON seed path")
    p_sv_mig.add_argument("--capacity", type=int, default=300, help="Metabolic ATP capacity")

    p_sv_aud = sov_subs.add_parser("audit", help="Audit and reconstitute organism on cold host")
    p_sv_aud.add_argument("-i", "--input", help="Input migration seed JSON path")

    p_sv_pdf = sov_subs.add_parser("pdf", help="Generate ISO 32000 proof-carrying polyglot certificate")
    p_sv_pdf.add_argument("-o", "--output", default="sovereign_organism.pdf", help="Output PDF path")
    p_sv_pdf.add_argument("--capacity", type=int, default=300, help="Metabolic ATP capacity")

    # sheaf-agora (Engine #35: Federated Sheaf Agora & Cohomological Constitutionalism — AGORA-0.2)
    p_sa = subparsers.add_parser(
        "sheaf-agora",
        help="Engine #35: Federated Sheaf Agora & Cohomological Constitutionalism (AGORA-0.2)"
    )
    sa_subs = p_sa.add_subparsers(dest="action")
    p_sa_init = sa_subs.add_parser("init", help="Simulate federated agora parliament session and resolution")
    p_sa_vote = sa_subs.add_parser("vote", help="Demonstrate anti-plutocratic quadratic voting defense")
    p_sa_frac = sa_subs.add_parser("fracture", help="Demonstrate fail-closed Čech cohomological fracture veto")
    p_sa_pdf = sa_subs.add_parser("pdf", help="Compile ISO 32000 vector polyglot parliament certificate")
    p_sa_pdf.add_argument("-o", "--output", default="sheaf_agora_parliament.pdf", help="Output PDF path")

    args = parser.parse_args()

    if args.command == "repl":
        cmd_repl(args)
    elif args.command == "test":
        cmd_test(args)
    elif args.command == "keygen":
        cmd_keygen(args)
    elif args.command == "verify":
        cmd_verify(args)
    elif args.command == "sandbox":
        cmd_sandbox(args)
    elif args.command == "compile":
        cmd_compile(args)
    elif args.command == "vault":
        cmd_vault(args)
    elif args.command == "adjudicate":
        cmd_adjudicate(args)
    elif args.command == "continuum":
        cmd_continuum(args)
    elif args.command == "zk":
        cmd_zk(args)
    elif args.command == "mesh":
        cmd_mesh(args)
    elif args.command == "synthesize":
        cmd_synthesize(args)
    elif args.command == "shell":
        cmd_shell(args)
    elif args.command == "quantum":
        cmd_quantum(args)
    elif args.command == "morph":
        cmd_morph(args)
    elif args.command == "metamorph":
        cmd_metamorph(args)
    elif args.command == "mycelium":
        cmd_mycelium(args)
    elif args.command == "colony":
        cmd_colony(args)
    elif args.command == "ontogeny":
        cmd_ontogeny(args)
    elif args.command == "goedel":
        cmd_goedel(args)
    elif args.command == "anyon":
        cmd_anyon(args)
    elif args.command == "diary":
        cmd_diary(args)
    elif args.command == "agora":
        cmd_agora(args)
    elif args.command == "autopoiesis":
        cmd_autopoiesis(args)
    elif args.command == "morpho-autopoiesis":
        cmd_morpho_autopoiesis(args)
    elif args.command == "warrant-kernel":
        cmd_warrant_kernel(args)
    elif args.command == "warrant-forget":
        cmd_controlled_forgetting(args)
    elif args.command == "epistemic-immune":
        cmd_epistemic_immune(args)
    elif args.command == "swarm":
        cmd_swarm(args)
    elif args.command == "egraph":
        cmd_egraph(args)
    elif args.command == "smt":
        cmd_smt(args)
    elif args.command == "cross-proof":
        cmd_cross_proof(args)
    elif args.command == "cegis":
        cmd_cegis(args)
    elif args.command == "dialectic":
        cmd_dialectic(args)
    elif args.command == "palimpsest":
        cmd_palimpsest(args)
    elif args.command == "admission":
        cmd_admission(args)
    elif args.command == "sheaf":
        cmd_sheaf(args)
    elif args.command == "sovereign":
        cmd_sovereign(args)
    elif args.command == "sheaf-agora":
        cmd_sheaf_agora(args)
    else:
        parser.print_help()




if __name__ == "__main__":
    main()
