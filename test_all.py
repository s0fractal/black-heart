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

import os
import sys
import unittest
import time

# This runner must test the checkout it lives in. Until S9 several engine
# modules prepended a hard-coded absolute checkout path (and the cwd, and a
# parent) to `sys.path` on import, so once any had run, a later import -- a
# TEST module OR one of its dependencies -- could resolve out of another clone.
# This file once reported a green aggregate for a worktree while running another
# checkout's test_mycelium.py against its sources. S9 removed those injections
# (each module now moves only its own directory to the front) AND checks the
# whole closure below, not just the selected suite modules.
#
# The origin check runs at two checkpoints per suite: once before it runs
# (catching residue from a prior suite) and once immediately after (S9-R1: a
# test can import a foreign module only WHILE it runs, and without a post-run
# checkpoint the LAST suite had no check after it at all -- a real foreign
# import there passed silently). This is a checkpoint guarantee, not a trace
# of every import event: a module imported and then removed again by the same
# suite before its run() returns escapes both checkpoints, and an import made
# inside a subprocess a test spawns is invisible to this process's sys.modules
# and is not covered by this guard at all.
_HERE = os.path.dirname(os.path.abspath(__file__))
# Keep this checkout first, and drop any other directory that also holds this
# checkout's modules (a second clone on PYTHONPATH/cwd) so nothing shadows it.
_REPO_MODULES = frozenset(
    os.path.splitext(f)[0] for f in os.listdir(_HERE) if f.endswith(".py")
)
if not (sys.path and sys.path[0] == _HERE):
    sys.path.insert(0, _HERE)


def _foreign_repo_modules() -> list:
    """Every already-imported module that shares a name with a file in this
    checkout but was loaded from somewhere else. This is the dependency-closure
    origin check: it catches an engine pulled from a second checkout, not only
    the suite module names."""
    foreign = []
    for name, module in list(sys.modules.items()):
        base = name.split(".")[0]
        if base not in _REPO_MODULES:
            continue
        path = getattr(module, "__file__", None)
        if path is None:
            continue
        if os.path.dirname(os.path.abspath(path)) != _HERE:
            foreign.append(f"{name} <- {path}")
    return foreign


def _assert_local(module_name: str) -> None:
    # The named suite module itself...
    module = sys.modules.get(module_name)
    path = getattr(module, "__file__", None)
    if path is not None and os.path.dirname(os.path.abspath(path)) != _HERE:
        raise ImportError(
            f"'{module_name}' was loaded from {path}, outside this checkout "
            f"({_HERE}). Some earlier module put another clone ahead on sys.path; "
            "the result of this run would describe neither checkout."
        )
    # ...and its whole dependency closure.
    foreign = _foreign_repo_modules()
    if foreign:
        raise ImportError(
            "Modules from another checkout are on sys.path, so this run would "
            f"describe neither checkout ({_HERE}). Foreign: " + "; ".join(sorted(foreign))
        )

SUITES = [
    ("Optional trusted-local CLI cache", "test_verify_cached"),
    ("CLI data verification and bounded CEGIS parser", "test_cli_verify"),
    ("Suite Import Isolation: One Checkout, No Tracked Writes", "test_suite_isolation"),
    ("Glyph Combinatory Logic", "test_glyph"),
    ("Term Addressing: Profile Migration", "test_term_address"),
    ("Church Numerals, REPL & Polyglot Runner", "test_church_and_repl"),
    ("Literate Polyglot Monad", "test_monad"),
    ("Living Polyglot Ledger", "test_living_ledger"),
    ("Ledger Peer Injection: No Code From Peer Block Fields", "test_ledger_peer_injection"),
    ("Interaction Combinators", "test_interaction"),
    ("Autonomous Organisms", "test_organism"),
    ("Bilateral Cross-Proofs & Vaults", "test_cross_proof"),
    ("Adjudication Trust: The Caller Pins, Not the Documents", "test_adjudication_trust"),
    ("Continuum Checkpointed Thunks", "test_continuum"),
    ("Ed25519 Zero-Knowledge Proofs", "test_zk_glyph"),
    ("P2P Polyglot Mesh Synchronization", "test_mesh"),
    ("Security Audit & Fail-Closed Controls", "test_security_audit"),
    ("Dialectical Symbiosis & Topological Knots", "test_symbiosis"),
    ("Topological Quantum Topos & Anyons", "test_quantum"),
    ("Turing Morphogenesis & Phenotypes", "test_morphogenesis"),
    ("Autonomous Form Metamorphosis", "test_metamorphosis"),
    ("Epistemic Mycelium & Warrant Mesh", "test_mycelium"),
    ("Rule Identity: What a Tombstone Addresses", "test_rule_identity"),
    ("Refutation Consumer: Autopoiesis Guard", "test_refutation_consumer"),
    ("EXP-001: Refusal, Readoption, Evolution", "test_exp001"),
    ("Trusted Issuers: Who May Refute", "test_trusted_issuers"),
    ("EXP-002: The Issuer as the One Factor", "test_exp002"),
    ("Key Custody: Public Export, Private Recovery", "test_public_export"),
    ("Key Sidecar Extension: .key -> \U0001F511", "test_key_sidecar_extension"),
    ("Living Colony Ecosystem", "test_colony"),
    ("Morphogenetic Proof-Nets & Ontogeny", "test_morpho_net"),
    ("Gödelian Incompleteness & Event Horizon", "test_goedel"),
    ("Anyonic Combinators & Quantum Braids", "test_anyon_glyph"),
    ("IPFS Ontogenetic Quine Diary", "test_ipfs_diary"),
    ("Mycelial Consensus Agora", "test_agora"),
    ("Autopoietic Quine Organisms", "test_autopoiesis"),
    ("Morphogenetic Autopoiesis Master Synthesis", "test_morpho_autopoiesis"),
    ("Morpho-Autopoiesis Economy: ATP Bound to the Receipt Chain", "test_morpho_economy_binding"),
    ("Agora Stake Accounting: The Debit Is a Signed Step", "test_agora_stake_accounting"),
    ("Epistemic Kernel & Unified Edge-Claims", "test_warrant_kernel"),
    ("Warrant Audit: Trust Root From Caller, Not Document", "test_warrant_document_trust"),
    ("Warrant Trust: Deny-All Survives Serialization", "test_warrant_empty_allowlist"),
    ("Warrant Grounded: Suspended Computation Is Not A Proof", "test_warrant_grounded_suspension"),
    ("Sandbox Auditor: SOUND Requires Positive Confirmation", "test_sandbox_fail_closed"),
    ("Counterexample Evidence: Replay Must Match the Witness", "test_counterexample_evidence"),
    ("Controlled Forgetting & Epistemic Retirement", "test_controlled_forgetting"),
    ("Retirement / Re-adoption Body Binding", "test_retirement_binding"),
    ("Autonomic Epistemic Immune System", "test_epistemic_immune"),
    ("Counterexample Producer: Audit Before Effects", "test_counterexample_producer"),
    ("Epistemic Swarm Membrane & Quine Symbiosis", "test_epistemic_swarm"),
    ("Suspended Normal Form: Not A Verified Reduction", "test_polyglot_suspended_nf"),
    ("Epistemic E-Graph Kernel & Equality Saturation", "test_egraph_kernel"),
    ("E-Graph Explanations: Only Steps That Replay", "test_egraph_explanation"),
    ("Sovereign SMT Kernel & First-Order DPLL(T) Verifier", "test_smt_kernel"),
    ("UNSAT Certificate: Structure vs Checked Refutation", "test_unsat_certificate"),
    ("Quarantine: Entailment, not Consistency", "test_quarantine_predicate"),
    ("Counterexample-Guided Inductive Synthesis (CEGIS)", "test_cegis_kernel"),
    ("CEGIS Credit: Operand-Bound Equivalence", "test_cegis_credit"),
    ("Scoped Re-Admission & Conditional Reopening", "test_scoped_admission"),
    ("Dialectical Discovery & Automated Hypothesis Generation", "test_dialectic_kernel"),
    ("Review 12 Remediation & Probe Defenses (f2e05e6)", "test_remediation_f2e05e6"),
    ("Epistemic Palimpsest — Value Drift Cartography", "test_palimpsest_kernel"),
    ("Epistemic Sheaf Kernel & Čech Cohomology", "test_sheaf_kernel"),
    ("Sheaf Local Validity: Only Sections That Hold Are Glued", "test_sheaf_local_validity"),
    ("Embedded Runner Claims: Report, Do Not Overclaim", "test_runner_claims"),
    ("Sovereign Continuity Quine & Forgetting Membrane", "test_sovereign_continuity"),
    ("Federated Sheaf Agora & Cohomological Constitutionalism", "test_sheaf_agora"),
    ("Findings F01–F12 Comprehensive Remediation", "test_sovereign_remediation"),
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

    origin_violation = None
    for name, module_name in SUITES:
        print(f"\033[1;33m[*] Testing: {name} ({module_name}.py)...\033[0m")
        if sys.path[0] != _HERE:
            sys.path.insert(0, _HERE)
        suite = loader.loadTestsFromName(module_name)
        _assert_local(module_name)  # checkpoint 1: catches residue from a prior suite
        runner = unittest.TextTestRunner(verbosity=1)
        res = runner.run(suite)
        total_ran += res.testsRun
        failures = len(res.failures) + len(res.errors)

        # Checkpoint 2: immediately after this suite's run(), not deferred to
        # the next iteration's checkpoint 1 -- there is no next iteration for
        # the last suite. Foreign provenance here overrides a green unittest
        # result: the run would describe neither checkout.
        try:
            _assert_local(module_name)
        except ImportError as e:
            origin_violation = e
            print(f"  \033[1;31m[✗] ORIGIN VIOLATION after {module_name}: {e}\033[0m\n")
            break

        if failures > 0:
            all_success = False
            print(f"  \033[1;31m[✗] {failures} failure(s) in {module_name}\033[0m\n")
        else:
            total_passed += res.testsRun
            print(f"  \033[1;32m[✓] All {res.testsRun} tests passed.\033[0m\n")

    if origin_violation is not None:
        all_success = False

    total_time = time.time() - start_global
    print("\033[1;36m" + "=" * 70)
    if origin_violation is not None:
        print(f"  \033[1;31m[✗] ORIGIN VIOLATION: run stopped, result describes neither checkout\033[0m")
    elif all_success:
        print(f"  \033[1;32m[✓] {total_passed}/{total_ran} tests passed in {total_time:.2f}s\033[0m")
    else:
        print(f"  \033[1;31m[✗] TEST FAILURES DETECTED: {total_passed}/{total_ran} passed in {total_time:.2f}s\033[0m")
    print("\033[1;36m" + "=" * 70 + "\033[0m\n")

    return all_success

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
