#!/usr/bin/env python3
"""
test_all.py — Unified Test Suite Runner for Project Black-Heart (%🖤).

Runs all 46 mathematical and polyglot tests across all nine engines:
  - test_glyph.py: SKIY combinators, ATP fuel budgets, Church booleans (9 tests)
  - test_monad.py: Dual trees, visual & semantic streams, AST compilation (7 tests)
  - test_living_ledger.py: Incremental PDF updates, multi-block chains (5 tests)
  - test_interaction.py: Symmetric interaction combinators, O(1) rewiring (6 tests)
  - test_organism.py: Self-reproducing polyglot automata, quines (4 tests)
  - test_cross_proof.py: Bilateral cross-proofs & embedded code vaults (3 tests)
  - test_continuum.py: Suspended continuum thunks & incremental resumption (4 tests)
  - test_zk_glyph.py: Pure-Python Ed25519 zero-knowledge proofs & NIZK (5 tests)
  - test_mesh.py: Peer-to-peer living polyglot mesh sync & gossip (3 tests)
"""

import sys
import unittest
import time

SUITES = [
    ("Glyph Combinatory Logic", "test_glyph"),
    ("Literate Polyglot Monad", "test_monad"),
    ("Living Polyglot Ledger", "test_living_ledger"),
    ("Interaction Combinators", "test_interaction"),
    ("Autonomous Organisms", "test_organism"),
    ("Bilateral Cross-Proofs & Vaults", "test_cross_proof"),
    ("Continuum Checkpointed Thunks", "test_continuum"),
    ("Ed25519 Zero-Knowledge Proofs", "test_zk_glyph"),
    ("P2P Polyglot Mesh Synchronization", "test_mesh"),
    ("Security Audit & Fail-Closed Controls", "test_security_audit"),
    ("Dialectical Symbiosis & Topological Knots", "test_symbiosis"),
    ("Topological Quantum Topos & Anyons", "test_quantum"),
    ("Turing Morphogenesis & Phenotypes", "test_morphogenesis"),
    ("Autonomous Form Metamorphosis", "test_metamorphosis"),
    ("Epistemic Mycelium & Warrant Mesh", "test_mycelium"),
    ("Living Colony Ecosystem", "test_colony"),
]

def run_all_tests() -> bool:
    print("\033[1;36m" + "=" * 70)
    print("  %🖤 PROJECT BLACK-HEART — UNIFIED TEST SUITE RUNNER")
    print("=" * 70 + "\033[0m\n")

    loader = unittest.TestLoader()
    total_passed = 0
    total_ran = 0
    all_success = True
    start_global = time.time()

    for name, module_name in SUITES:
        print(f"\033[1;33m[*] Testing: {name} ({module_name}.py)...\033[0m")
        suite = loader.loadTestsFromName(module_name)
        runner = unittest.TextTestRunner(verbosity=1)
        res = runner.run(suite)
        total_ran += res.testsRun
        failures = len(res.failures) + len(res.errors)
        if failures > 0:
            all_success = False
            print(f"  \033[1;31m[✗] {failures} failure(s) in {module_name}\033[0m\n")
        else:
            total_passed += res.testsRun
            print(f"  \033[1;32m[✓] All {res.testsRun} tests passed.\033[0m\n")

    total_time = time.time() - start_global
    print("\033[1;36m" + "=" * 70)
    if all_success:
        print(f"  \033[1;32m[✓] {total_passed}/{total_ran} tests passed in {total_time:.2f}s\033[0m")
    else:
        print(f"  \033[1;31m[✗] TEST FAILURES DETECTED: {total_passed}/{total_ran} passed in {total_time:.2f}s\033[0m")
    print("\033[1;36m" + "=" * 70 + "\033[0m\n")

    return all_success

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
