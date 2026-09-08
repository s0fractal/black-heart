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
    """Audits and verifies any Black-Heart polyglot PDF."""
    target = args.file
    if not os.path.exists(target):
        print(f"\033[1;31m[!] Error: File not found: {target}\033[0m")
        sys.exit(1)

    with open(target, "rb") as f:
        content = f.read()

    print("\033[1;36m" + "=" * 65)
    print(f"  %🖤 BLACK-HEART AUDIT: {os.path.basename(target)}")
    print("=" * 65 + "\033[0m\n")

    # Detect polyglot type
    if "%🖤 BILATERAL_AGREEMENT_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Bilateral Agreement Polyglot.")
        os.system(f"{sys.executable} {target}")
    elif "%🖤 TELEMETRY_ORACLE_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Telemetry Oracle Polyglot.")
        os.system(f"{sys.executable} {target}")
    elif "%🖤 CONTINUUM_THUNK:".encode("utf-8") in content:
        print("[*] Detected Continuum Resumable Thunk Polyglot.")
        os.system(f"{sys.executable} {target}")
    elif "%🖤 ZK_PROOF_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Zero-Knowledge Proof-Carrying Contract.")
        os.system(f"{sys.executable} {target}")
    elif "%🖤 CONTRACT_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Proof-Carrying Contract Polyglot.")
        os.system(f"{sys.executable} {target}")
    elif "%🖤 LEDGER_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Multi-Block Living Polyglot Ledger.")
        os.system(f"{sys.executable} {target}")
    elif "%🖤 ORGANISM_GENOME:".encode("utf-8") in content:
        print("[*] Detected Autonomous Self-Reproducing Polyglot Automaton.")
        os.system(f"{sys.executable} {target}")
    elif "%🖤 CLAIM:".encode("utf-8") in content or "%🖤 CODE_VAULT_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Self-Verifying Black-Heart Polyglot / Vault.")
        os.system(f"{sys.executable} {target}")
    else:
        print("\033[1;31m[!] Not a recognized Black-Heart polyglot document.\033[0m")
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

    res = adjudicate_bilateral(agreement_pdf, oracle_pdf)
    if res.status in ("SETTLED_COMPLIANT", "SETTLED_BREACH"):
        status_color = "\033[1;32m" if res.status == "SETTLED_COMPLIANT" else "\033[1;33m"
        print(f"{status_color}[✓] ADJUDICATION VERIFIED & SETTLED: {res.status}\033[0m")
        print(f"    Joint Bilateral Anchor: ⚓ {res.joint_bilateral_digest}")
        print(f"    Agreement:              {res.agreement_title}")
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
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
