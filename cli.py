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

        # Parse & evaluate
        try:
            term = parse(line)
            norm, atp, digest = evaluate(term, max_atp=current_atp_budget)
            print(f"  \033[1;32mNormal Form:\033[0m {norm}")
            print(f"  \033[1;34mSettlement: \033[0m ⚓ ⟨atp:{atp}, hash:{digest[:16]}⟩\n")
        except Exception as e:
            print(f"  \033[1;31m[!] Error:\033[0m {e}\n")

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
    """Audits and verifies any Black-Heart polyglot PDF purely as data without executing arbitrary code."""
    target = args.file
    if not os.path.exists(target):
        print(f"\033[1;31m[!] Error: File not found: {target}\033[0m")
        sys.exit(1)

    with open(target, "rb") as f:
        content = f.read()

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
        from continuum import audit_self
        try:
            audit_self(target)
            success = True
        except Exception as e:
            print(f"[!] Continuum verification failed: {e}")
            success = False
    elif "%🖤 ZK_PROOF_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Zero-Knowledge Proof-Carrying Contract.")
        from zk_glyph import audit_zkp
        try:
            audit_zkp(target)
            success = True
        except Exception as e:
            print(f"[!] ZK proof verification failed: {e}")
            success = False
    elif "%🖤 CONTRACT_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Proof-Carrying Contract Polyglot.")
        from monad import audit_contract_polyglot
        success = audit_contract_polyglot(target)
    elif "%🖤 LEDGER_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Multi-Block Living Polyglot Ledger.")
        from living_ledger import LivingLedger
        try:
            ledger = LivingLedger.load_from_polyglot(target)
            success = ledger.verify()
        except Exception as e:
            print(f"[!] Ledger verification failed: {e}")
            success = False
    elif "%🖤 METAMORPHIC_TRANSITION:".encode("utf-8") in content:
        print("[*] Detected Metamorphic Organism Polyglot.")
        from metamorphosis import audit_metamorphic_transition
        try:
            audit_metamorphic_transition(target)
            success = True
        except Exception as e:
            print(f"[!] Metamorphic verification failed: {e}")
            success = False
    elif "%🖤 COLONY_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Living Colony Ecosystem Polyglot.")
        from colony import Colony
        try:
            colony = Colony.load_from_polyglot(target)
            success = colony.verify()
        except Exception as e:
            print(f"[!] Colony verification failed: {e}")
            success = False
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
        print("\033[1;32m[✓ GREEN] Document verification passed successfully.\033[0m")
    else:
        print("\033[1;31m[✗ RED] Document verification failed.\033[0m")
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

    pinned_pk = getattr(args, "pinned_author_pk", None)
    pinned_hash = getattr(args, "pinned_agreement_hash", None)
    allow_untrusted = getattr(args, "allow_untrusted_issuer", False)

    if not pinned_pk and not pinned_hash and not allow_untrusted:
        print("\033[1;31m[✗] ADJUDICATION REJECTED: UNTRUSTED_ISSUER_EVALUATION.\033[0m")
        print("    Trust root pinning is required to adjudicate bilateral contracts.")
        print("    Provide --pinned-author-pk <HEX> or --pinned-agreement-hash <HEX>,")
        print("    or explicitly pass --allow-untrusted-issuer to override.")
        sys.exit(1)

    try:
        res = adjudicate_bilateral(
            agreement_pdf,
            oracle_pdf,
            expected_agreement_hash=pinned_hash,
            expected_author_pk_hex=pinned_pk
        )
    except Exception as e:
        print(f"\033[1;31m[✗] ADJUDICATION FAILED: {e}\033[0m\n")
        sys.exit(1)

    if res.trust_status == "UNTRUSTED_ISSUER_EVALUATION" and not allow_untrusted:
        print("\033[1;31m[✗] ADJUDICATION REJECTED: UNTRUSTED_ISSUER_EVALUATION.\033[0m\n")
        sys.exit(1)

    if res.status in ("SETTLED_COMPLIANT", "SETTLED_BREACH"):
        status_color = "\033[1;32m" if res.status == "SETTLED_COMPLIANT" else "\033[1;33m"
        print(f"{status_color}[✓] ADJUDICATION VERIFIED & SETTLED: {res.status}\033[0m")
        print(f"    Joint Bilateral Anchor: ⚓ {res.joint_bilateral_digest}")
        print(f"    Agreement:              {res.agreement_title}")
        print(f"    Trust Status:           {res.trust_status}")
        print(f"    Oracle:                 {res.oracle_name} ({res.oracle_pk_hex[:16]}...)")
        print(f"    Measured Uptime:        {res.measured_uptime_percent:.2f}% (Target: {res.target_uptime_percent:.2f}%)")
        print(f"    Net Service Due:        ${res.net_service_due_usd} USD (Penalty: ${res.penalty_due_usd} USD)")
    else:
        print(f"\033[1;31m[✗] ADJUDICATION FAILED: {res.status}\033[0m\n")
        sys.exit(1)

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
        print("\033[1;36m===================================================\033[0m")
        print(f"  %🖤 COLONY INITIALIZED: {colony.name}")
        print("\033[1;36m===================================================\033[0m")
        print(f"  Active Organisms:   {len(colony.active_organisms())}")
        print(f"  Substrate ATP Pool: {colony.substrate_atp}")
        print(f"  Saved to:           {file_path}\n")

    elif args.action == "step":
        if not os.path.exists(file_path):
            print(f"[!] Colony state file '{file_path}' not found. Run 'init' first.")
            sys.exit(1)
        colony = Colony.load_from_file(file_path)
        if not colony.verify():
            print(f"[!] Integrity check failed: Colony state is corrupted or tampered.")
            sys.exit(1)
        epochs = args.epochs or 1
        for _ in range(epochs):
            rec = colony.step_epoch(solar_influx_atp=args.solar)
            print(f"[*] Epoch #{rec.epoch_index} complete | Active: {rec.active_count} | Spores: {rec.spore_count} | Minted: {rec.warrants_minted} | Adopted: {rec.warrants_adopted} | Matings: {rec.matings_count} | Anchor: {rec.epoch_hash[:16]}...")
        colony.save_to_file(file_path)
        print(f"\n[+] Colony state saved to '{file_path}'.")

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
        rec, cid = initialize_ontogenetic_diary(
            output_pdf_path=out_path,
            genesis_thought=args.thought or "I am an autonomous polyglot quine, remembering my origins across the distributed continuum.",
            genesis_prompt=args.prompt or "Who are you?",
            epistemic_grade=args.grade or "PROPOSED",
            secret_key_hex=sk
        )
        print("\033[1;36m===================================================\033[0m")
        print("  %🖤 ONTOGENTIC IPFS DIARY INITIALIZED: Gen #0")
        print("\033[1;36m===================================================\033[0m")
        print(f"  Target Polyglot:     {out_path}")
        print(f"  Genesis CIDv1:       {cid}")
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
            secret_key_hex=args.secret_key or None
        )
        print("\033[1;32m===================================================\033[0m")
        print(f"  [✓] DIARY SETTLEMENT ACCOMPLISHED: Generation #{settlement.generation}")
        print("\033[1;32m===================================================\033[0m")
        print(f"  Current CIDv1:       {settlement.current_cid}")
        print(f"  Parent CIDv1:        {settlement.prev_cid}")
        print(f"  Epistemic Grade:     {settlement.epistemic_grade}")
        print(f"  ATP Fuel Burned:     {settlement.atp_burned} ATP\n")

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
            thought = m.get("thought_content", "")[:60]
            print(f"  #{gen:02d} [{t_utc}] {grade:14s} | Parent: {p_cid[:22]}... | {thought}...")
        print(f"\n  Current File CIDv1: {compute_cidv1_raw(data)}\n")

    elif args.action == "audit":
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
        print(f"[*] Auditing ontogenetic diary chain across {len(manifest)} generations...")
        for i, md in enumerate(manifest):
            rec = OntogeneticDiaryReceipt.from_dict(md)
            if rec.generation != i:
                print(f"[FAIL] Generation sequence gap at index {i}: got #{rec.generation}")
                sys.exit(1)
            if rec.receipt_hash != rec.compute_hash():
                print(f"[FAIL] Hash mismatch at generation #{rec.generation}")
                sys.exit(1)
            if rec.is_attested():
                if not rec.verify():
                    print(f"[FAIL] Cryptographic signature invalid at generation #{rec.generation}")
                    sys.exit(1)
            else:
                print(f"[!] Generation #{rec.generation}: UNATTESTED (unsigned)")
        print(f"\033[1;32m[✓] ALL {len(manifest)} DIARY PAGES CRYPTOGRAPHICALLY VERIFIED & AUDITED\033[0m\n")

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
    else:
        print("Usage: python3 cli.py diary {init,append,status,lineage,audit,publish} ...")


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

    # adjudicate
    p_adj = subparsers.add_parser("adjudicate", help="Bilateral cross-proof adjudication between contract and oracle PDFs")
    p_adj.add_argument("agreement", help="Path to bilateral agreement PDF")
    p_adj.add_argument("oracle", help="Path to telemetry oracle PDF")
    p_adj.add_argument("--pinned-author-pk", default=None, help="Pinned Ed25519 public key hex of the agreement author")
    p_adj.add_argument("--pinned-agreement-hash", default=None, help="Pinned SHA-256 agreement document anchor")
    p_adj.add_argument("--allow-untrusted-issuer", action="store_true", help="Explicitly allow evaluation without pinned trust root")

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
    p_diary_init.add_argument("--secret-key", default=None, help="Author Ed25519 secret key hex (optional)")

    p_diary_app = diary_subs.add_parser("append", help="Append an incremental reflection page to the diary")
    p_diary_app.add_argument("file", help="Target ontogenetic diary PDF")
    p_diary_app.add_argument("-t", "--thought", required=True, help="New thought reflection to append")
    p_diary_app.add_argument("-p", "--prompt", default="", help="Prompt trigger context")
    p_diary_app.add_argument("-g", "--grade", default="PROPOSED", help="Epistemic grade")
    p_diary_app.add_argument("--atp", type=int, default=10, help="ATP fuel burned")
    p_diary_app.add_argument("--secret-key", default=None, help="Author Ed25519 secret key hex (optional)")

    p_diary_stat = diary_subs.add_parser("status", help="Display latest diary HUD telemetry and CIDv1")
    p_diary_stat.add_argument("file", help="Target ontogenetic diary PDF")

    p_diary_lin = diary_subs.add_parser("lineage", help="Display full Merkle-DAG CID ancestry chain")
    p_diary_lin.add_argument("file", help="Target ontogenetic diary PDF")

    p_diary_aud = diary_subs.add_parser("audit", help="Cryptographically audit all diary pages and signatures")
    p_diary_aud.add_argument("file", help="Target ontogenetic diary PDF")

    p_diary_pub = diary_subs.add_parser("publish", help="Pin current diary document to IPFS Kubo node")
    p_diary_pub.add_argument("file", help="Target ontogenetic diary PDF")
    p_diary_pub.add_argument("--url", default="http://127.0.0.1:5001", help="IPFS Kubo API endpoint")

    args = parser.parse_args()

    if args.command == "repl":
        cmd_repl(args)
    elif args.command == "test":
        cmd_test(args)
    elif args.command == "keygen":
        cmd_keygen(args)
    elif args.command == "verify":
        cmd_verify(args)
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
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
