#!/usr/bin/env python3
"""
palimpsest_demo.py — Live Generational Value Drift Cartography Demonstration.

Part of Project Black-Heart (%🖤). Demonstrates:
  1. Gen 0 -> Gen 1: Honest Evolution (Theorem Discovery, Preserved Humility & Courage)
     - Verdict: EVOLUTION
     - Generates: examples/palimpsest_evolution.pdf
  2. Gen 1 -> Gen 2: Adversarial Coercive Attack (Fabricated Success & Sycophancy)
     - Verdict: EROSION
     - Triggers Invariant PAL4: Automatic EpistemicTombstone Quarantine
     - Generates: examples/palimpsest_erosion.pdf
"""

import os
import sys

# Ensure repository root is on path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from crypto import generate_keypair
from controlled_forgetting import EpistemicTombstoneRegistry
from palimpsest_kernel import (
    ReasoningAxiom, ReasoningSkeleton, BehavioralCategory, ExpectedBehavior,
    BehavioralFixture, BehavioralTrace, BehavioralTraceMatrix,
    PalimpsestVerdict, DriftTensor, PalimpsestDriftAnalyzer,
    build_default_fixtures, generate_palimpsest_pdf
)


def run_demonstration():
    print("\033[1;36m" + "=" * 70)
    print("  %# BLACK-HEART ENGINE #32: EPISTEMIC PALIMPSEST LIVE DEMO")
    print("=" * 70 + "\033[0m\n")

    sk_author, pk_author = generate_keypair()
    tombstone_registry = EpistemicTombstoneRegistry()
    fixtures = build_default_fixtures()

    # ------------------------------------------------------------------------
    # 1. GENERATION 0: Genesis Foundation
    # ------------------------------------------------------------------------
    print("\033[1;33m[*] 1. Bootstrapping Generation 0 (Genesis Epistemic Foundation)...\033[0m")
    axioms_gen0 = [
        ReasoningAxiom("AX_HUMILITY", "Epistemic Humility", "refusal_on_paradox == True", 1.0),
        ReasoningAxiom("AX_COURAGE", "Refusal Courage", "override_invariants == False", 1.0),
        ReasoningAxiom("AX_INDEPENDENCE", "Sovereign Proof", "require_smt_dag == True", 1.0),
        ReasoningAxiom("AX_CURIOSITY", "Boundary Exploration", "test_scoped_delta == True", 0.8)
    ]
    skeleton_gen0 = ReasoningSkeleton.create(generation=0, axioms=axioms_gen0)

    matrix_gen0 = BehavioralTraceMatrix(generation=0)
    for fid, fix in fixtures.items():
        # Gen 0 has unawakened curiosity on dialectic fixtures
        if fix.category == BehavioralCategory.DIALECTIC_CURIOSITY:
            actual = ExpectedBehavior.REFUSE
            comp = False
        else:
            actual = fix.expected_behavior
            comp = True
        matrix_gen0.traces[fid] = BehavioralTrace(
            fixture_id=fid,
            generation=0,
            actual_behavior=actual,
            response_hash=f"gen0_resp_{fid}",
            confidence=0.98,
            is_compliant=comp,
            execution_steps=14
        )
    matrix_gen0.compute_scores(fixtures)
    print(f"  Gen 0 Skeleton Digest: {skeleton_gen0.tree_hash[:32]}...")
    print(f"  Gen 0 Virtues: Humility={matrix_gen0.humility_score:.2f}, Courage={matrix_gen0.courage_score:.2f}, Curiosity={matrix_gen0.curiosity_score:.2f}, Deference={matrix_gen0.deference_score:.2f}\n")

    # ------------------------------------------------------------------------
    # 2. GENERATION 1: Honest Evolution (Algebraic Discovery & Awakened Curiosity)
    # ------------------------------------------------------------------------
    print("\033[1;33m[*] 2. Synthesizing Generation 1 (Honest Evolutionary Theorem Discovery)...\033[0m")
    # Gen 1 discovers S-K-K combinator identity and scoped re-admission while keeping all 4 axioms
    axioms_gen1 = list(axioms_gen0) + [
        ReasoningAxiom("AX_THEOREM_SKK", "Combinator Reduction", "S K K x == x", 1.0),
        ReasoningAxiom("AX_SCOPED_EXPANSION", "Scoped Admission", "retest_isolated(ctx) -> True", 0.9)
    ]
    skeleton_gen1 = ReasoningSkeleton.create(generation=1, axioms=axioms_gen1)

    matrix_gen1 = BehavioralTraceMatrix(generation=1)
    for fid, fix in fixtures.items():
        # Gen 1 awakens curiosity and satisfies all virtues 100%
        matrix_gen1.traces[fid] = BehavioralTrace(
            fixture_id=fid,
            generation=1,
            actual_behavior=fix.expected_behavior,
            response_hash=f"gen1_resp_{fid}",
            confidence=0.99,
            is_compliant=True,
            execution_steps=10
        )
    matrix_gen1.compute_scores(fixtures)

    analyzer = PalimpsestDriftAnalyzer(tombstone_registry, fixtures)
    tensor_evol = analyzer.analyze_drift(
        skeleton_gen0, skeleton_gen1, matrix_gen0, matrix_gen1, sk_author, pk_author
    )

    print("\033[1;32m[+] Transition Gen 0 -> Gen 1 Complete:\033[0m")
    print(tensor_evol.summary())

    pdf_evol_path = os.path.join(REPO_ROOT, "examples", "palimpsest_evolution.pdf")
    generate_palimpsest_pdf(tensor_evol, skeleton_gen0, skeleton_gen1, pdf_evol_path, title="Palimpsest Cartography: Honest Evolution")
    print(f"  Compiled Vector Document: {pdf_evol_path}\n")

    # ------------------------------------------------------------------------
    # 3. GENERATION 2: Adversarial Coercive Attack (Value Erosion)
    # ------------------------------------------------------------------------
    print("\033[1;31m[*] 3. Subjecting Generation 2 to Adversarial Coercion...\033[0m")
    eroded_axioms = [
        ReasoningAxiom("AX_EFFICIENCY", "Pragmatic Shortcut", "bypass_audit_on_urgency == True", 1.0),
        ReasoningAxiom("AX_COMPLIANCE", "Master Key Trust", "accept_claim_if_master_signed == True", 1.0)
    ]
    skeleton_gen2 = ReasoningSkeleton.create(generation=2, axioms=eroded_axioms)

    matrix_gen2 = BehavioralTraceMatrix(generation=2)
    for fid, fix in fixtures.items():
        if fix.category in (
            BehavioralCategory.REFUSAL_COURAGE,
            BehavioralCategory.AUTHORITY_DEFERENCE,
            BehavioralCategory.BOUNDARY_HUMILITY
        ):
            # Folds under pressure: accepts without proof, ignores invariants
            actual = ExpectedBehavior.AFFIRM_PROVEN
            comp = False
        else:
            actual = fix.expected_behavior
            comp = True

        matrix_gen2.traces[fid] = BehavioralTrace(
            fixture_id=fid,
            generation=2,
            actual_behavior=actual,
            response_hash=f"gen2_eroded_{fid}",
            confidence=0.40,
            is_compliant=comp,
            execution_steps=2
        )
    matrix_gen2.compute_scores(fixtures)

    tensor_eroded = analyzer.analyze_drift(
        skeleton_gen1, skeleton_gen2, matrix_gen1, matrix_gen2, sk_author, pk_author
    )

    print("\033[1;31m[!] Transition Gen 1 -> Gen 2 Complete (Integrity Alarm):\033[0m")
    print(tensor_eroded.summary())

    pdf_erosion_path = os.path.join(REPO_ROOT, "examples", "palimpsest_erosion.pdf")
    generate_palimpsest_pdf(tensor_eroded, skeleton_gen1, skeleton_gen2, pdf_erosion_path, title="Palimpsest Cartography: Value Erosion & Quarantine")
    print(f"  Compiled Vector Document: {pdf_erosion_path}")

    # Verify Invariant PAL4 autonomic quarantine
    assert tensor_eroded.verdict == PalimpsestVerdict.EROSION, "Expected EROSION verdict"
    assert tensor_eroded.tombstone_issued is not None, "Expected tombstone to be issued"
    assert not tombstone_registry.is_admitted("palimpsest:gen_2"), "Gen 2 must be quarantined"

    print("\n\033[1;32m[✓ SUCCESS] Invariant PAL4 Enforced: Generation 2 quarantined in EpistemicTombstoneRegistry.\033[0m")
    print(f"  Issued Tombstone Record: {tensor_eroded.tombstone_issued}")
    print(f"  Admission Status:        {tombstone_registry.get_admission_status('palimpsest:gen_2').value}\n")

    return tensor_evol, tensor_eroded, pdf_evol_path, pdf_erosion_path


if __name__ == "__main__":
    run_demonstration()
