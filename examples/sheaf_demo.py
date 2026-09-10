#!/usr/bin/env python3
# coding: utf-8
"""
examples/sheaf_demo.py — Live Demonstration of Engine #33: Epistemic Sheaf Kernel (SHEAF-0.1).
Part of Project Black-Heart (%🖤).
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sheaf_kernel import (
    EpistemicContext, LocalSection, SectionStatus,
    EpistemicSheafKernel, generate_sheaf_pdf
)


def run_demo():
    print("\033[1;36m" + "=" * 65)
    print("  %🖤 BLACK-HEART ENGINE #33: EPISTEMIC SHEAF KERNEL (SHEAF-0.1)")
    print("=" * 65 + "\033[0m\n")

    kernel = EpistemicSheafKernel()

    # Define 3 overlapping open charts
    ctx_1 = EpistemicContext.create("Chart_Alpha", ["pure_ski", "linear_logic"], 120, ["INV_DETERMINISTIC"])
    ctx_2 = EpistemicContext.create("Chart_Beta", ["linear_logic", "interaction_nets"], 150, ["INV_DETERMINISTIC"])
    ctx_3 = EpistemicContext.create("Chart_Gamma", ["pure_ski", "interaction_nets"], 180, ["INV_DETERMINISTIC"])

    kernel.register_context(ctx_1)
    kernel.register_context(ctx_2)
    kernel.register_context(ctx_3)

    claim = "LAFONT_INTERACTION_CONFLUENCE"
    sec_1 = LocalSection.create(ctx_1, claim, "S K K (K I)", "K I", 2)
    sec_2 = LocalSection.create(ctx_2, claim, "I (K I)", "K I", 1)
    sec_3 = LocalSection.create(ctx_3, claim, "S K K (I (K I))", "K I", 3)

    kernel.register_section(sec_1)
    kernel.register_section(sec_2)
    kernel.register_section(sec_3)

    print("[+] Registered 3 Overlapping Epistemic Charts:")
    print(f"    1. {ctx_1.name} (Domains: {ctx_1.domains}, Budget: {ctx_1.budget_ceiling})")
    print(f"    2. {ctx_2.name} (Domains: {ctx_2.domains}, Budget: {ctx_2.budget_ceiling})")
    print(f"    3. {ctx_3.name} (Domains: {ctx_3.domains}, Budget: {ctx_3.budget_ceiling})\n")

    print(f"[+] Verifying Sheaf Descent for Claim '{claim}'...")
    cover = [ctx_1, ctx_2, ctx_3]
    report = kernel.verify_descent(claim, cover)

    print(f"    Gluing Admissible: \033[1;32m{report.is_gluing_admissible}\033[0m")
    print(f"    Čech dim H^1:      {report.h1_dimension} (Zero epistemic twist)")
    print(f"    Cocycles Audited:  {len(report.cocycles)} pairwise intersections")
    for coc in report.cocycles:
        print(f"      - {coc.context_i} ^ {coc.context_j}: {'MATCH (0)' if coc.is_zero else 'DISCREPANCY'}")

    if report.global_section:
        print(f"\n[✓] Synthesized Unique Global Section:")
        print(f"    Global Section ID: {report.global_section.section_id[:24]}...")
        print(f"    Normal Form:       {report.global_section.normal_form}")
        print(f"    Status:            {report.global_section.status.value}\n")

    out_pdf = "examples/sheaf_certificate.pdf"
    os.makedirs("examples", exist_ok=True)
    generate_sheaf_pdf(report, out_pdf)
    print(f"[✓] Polyglot Sheaf Certificate compiled to: {out_pdf}")
    print(f"    Run standalone audit: python3 {out_pdf}\n")


if __name__ == "__main__":
    run_demo()
