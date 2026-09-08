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

BANNER = r"""
  %🖤  PROJECT BLACK-HEART — UNIFIED COMMAND SUITE
  Combinatory Logic • Proof-Carrying Polyglots • Living Ledgers
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
    if "%🖤 CONTRACT_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Proof-Carrying Contract Polyglot.")
        # Execute contract audit runner directly via python
        os.system(f"{sys.executable} {target}")
    elif "%🖤 LEDGER_MANIFEST:".encode("utf-8") in content:
        print("[*] Detected Multi-Block Living Polyglot Ledger.")
        os.system(f"{sys.executable} {target}")
    elif "%🖤 CLAIM:".encode("utf-8") in content:
        print("[*] Detected Standard Black-Heart Polyglot.")
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

def main():
    parser = argparse.ArgumentParser(description="Black-Heart (%🖤) Command Suite")
    subparsers = parser.add_subparsers(dest="command")

    # repl
    p_repl = subparsers.add_parser("repl", help="Interactive proof and combinator REPL")

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

    args = parser.parse_args()

    if args.command == "repl":
        cmd_repl(args)
    elif args.command == "keygen":
        cmd_keygen(args)
    elif args.command == "verify":
        cmd_verify(args)
    elif args.command == "compile":
        cmd_compile(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
