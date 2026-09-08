#!/usr/bin/env python3
"""
vector_net.py — Native PDF Vector Graphics Proof Net & String Diagram Compiler.
Part of Project Black-Heart (%🖤).

Translates SKIY combinator abstract syntax trees and reduction rewriting steps
directly into PostScript-style 2D vector graphics streams (lines, bezier curves,
geometric nodes, and color palettes) within ISO 32000 PDF documents.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List, Tuple, Optional, Union
from glyph import Comb, Var, App, Term, GLYPH_K, GLYPH_I, GLYPH_S, GLYPH_Y

@dataclass
class LayoutNode:
    x: float
    y: float
    width: float
    height: float
    term: Term
    children: List[LayoutNode]

class VectorNetRenderer:
    """
    Renders combinator trees and rewriting rules into native PDF vector graphics streams.
    Uses ISO 32000 graphics state operators (w, RG, rg, m, l, c, re, s, f, B).
    """
    def __init__(self, node_radius: float = 14.0, level_height: float = 40.0, sibling_gap: float = 18.0):
        self.r = node_radius
        self.level_h = level_height
        self.sibling_gap = sibling_gap

    def layout_tree(self, term: Term, x_center: float, y_top: float) -> LayoutNode:
        """Calculates 2D coordinates for the binary AST."""
        if isinstance(term, (Comb, Var)):
            return LayoutNode(x=x_center, y=y_top, width=self.r * 2, height=self.r * 2, term=term, children=[])

        elif isinstance(term, App):
            # Layout left and right branches
            left_node = self.layout_tree(term.left, 0, 0)
            right_node = self.layout_tree(term.right, 0, 0)

            total_sub_w = left_node.width + self.sibling_gap + right_node.width
            # Position children relative to current center
            left_x = x_center - (total_sub_w / 2.0) + (left_node.width / 2.0)
            right_x = x_center + (total_sub_w / 2.0) - (right_node.width / 2.0)
            child_y = y_top - self.level_h

            left_node = self.layout_tree(term.left, left_x, child_y)
            right_node = self.layout_tree(term.right, right_x, child_y)

            return LayoutNode(
                x=x_center,
                y=y_top,
                width=max(total_sub_w, self.r * 2),
                height=self.level_h + max(left_node.height, right_node.height),
                term=term,
                children=[left_node, right_node]
            )
        return LayoutNode(x=x_center, y=y_top, width=self.r*2, height=self.r*2, term=term, children=[])

    def render_tree_to_pdf_stream(self, root: LayoutNode) -> str:
        """Generates PDF vector commands to draw the tree with curved wires and nodes."""
        ops: List[str] = []

        # 1. First pass: Draw connection wires (behind nodes)
        def draw_wires(node: LayoutNode):
            for ch in node.children:
                # Cubic bezier curve connecting parent to child
                x1, y1 = node.x, node.y - self.r
                x2, y2 = ch.x, ch.y + self.r
                mid_y = (y1 + y2) / 2.0

                ops.append("q")
                ops.append("1.5 w")           # line width
                ops.append("0.3 0.35 0.45 RG") # subtle slate wire
                ops.append(f"{x1:.2f} {y1:.2f} m")
                ops.append(f"{x1:.2f} {mid_y:.2f} {x2:.2f} {mid_y:.2f} {x2:.2f} {y2:.2f} c")
                ops.append("S")
                ops.append("Q")

                draw_wires(ch)

        draw_wires(root)

        # 2. Second pass: Draw nodes
        def draw_nodes(node: LayoutNode):
            t = node.term
            cx, cy = node.x, node.y

            if isinstance(t, Comb):
                sym = t.symbol
                if sym == GLYPH_K:
                    # Black Cone: Obsidian filled circle with gold accent
                    ops.append("q")
                    ops.append("0.08 0.08 0.12 rg") # dark obsidian
                    ops.append("0.85 0.65 0.15 RG 1.5 w") # golden rim
                    ops.append(_circle_path(cx, cy, self.r))
                    ops.append("B")
                    # Label
                    ops.append(f"BT /F1 11 Tf 1 1 1 rg {cx - 4:.2f} {cy - 4:.2f} Td (K) Tj ET")
                    ops.append("Q")

                elif sym == GLYPH_I:
                    # White Cone: Crisp pearl circle with cyan core
                    ops.append("q")
                    ops.append("0.96 0.98 1.0 rg") # pearl fill
                    ops.append("0.2 0.6 0.85 RG 1.5 w") # cyan rim
                    ops.append(_circle_path(cx, cy, self.r))
                    ops.append("B")
                    # Label
                    ops.append(f"BT /F1 11 Tf 0.1 0.3 0.6 rg {cx - 2.5:.2f} {cy - 4:.2f} Td (I) Tj ET")
                    ops.append("Q")

                elif sym == GLYPH_S:
                    # Spore: Emerald green mycelial distributor
                    ops.append("q")
                    ops.append("0.1 0.55 0.28 rg") # emerald
                    ops.append("0.05 0.35 0.18 RG 1.5 w")
                    ops.append(_circle_path(cx, cy, self.r))
                    ops.append("B")
                    # Label
                    ops.append(f"BT /F1 11 Tf 1 1 1 rg {cx - 3.5:.2f} {cy - 4:.2f} Td (S) Tj ET")
                    ops.append("Q")

                elif sym == GLYPH_Y:
                    # Fixpoint: Royal indigo loop
                    ops.append("q")
                    ops.append("0.25 0.2 0.65 rg")
                    ops.append("0.45 0.35 0.9 RG 1.5 w")
                    ops.append(_circle_path(cx, cy, self.r))
                    ops.append("B")
                    # Label
                    ops.append(f"BT /F1 11 Tf 1 1 1 rg {cx - 3.5:.2f} {cy - 4:.2f} Td (Y) Tj ET")
                    ops.append("Q")

            elif isinstance(t, App):
                # Application Junction Node: Clean slate ring
                ops.append("q")
                ops.append("0.9 0.92 0.95 rg")
                ops.append("0.35 0.45 0.6 RG 1.2 w")
                ops.append(_circle_path(cx, cy, self.r * 0.75))
                ops.append("B")
                ops.append(f"BT /F2 8 Tf 0.2 0.3 0.5 rg {cx - 3:.2f} {cy - 3:.2f} Td (@) Tj ET")
                ops.append("Q")

            elif isinstance(t, Var):
                # Variable Atom: Slate pill
                name = str(t.name)[:8]
                w = max(24.0, len(name) * 6.5)
                h = 16.0
                ops.append("q")
                ops.append("0.94 0.95 0.97 rg")
                ops.append("0.5 0.55 0.65 RG 1 w")
                ops.append(f"{cx - w/2:.2f} {cy - h/2:.2f} {w:.2f} {h:.2f} re B")
                ops.append(f"BT /F2 8 Tf 0.1 0.1 0.1 rg {cx - (len(name)*2.8):.2f} {cy - 3:.2f} Td ({name}) Tj ET")
                ops.append("Q")

            for ch in node.children:
                draw_nodes(ch)

        draw_nodes(root)
        return "\n".join(ops)

    def render_reduction_step(
        self,
        lhs: Term,
        rhs: Term,
        x: float,
        y: float,
        width: float,
        height: float,
        atp_cost: int = 1,
        rule_name: str = "BETA_REDUCTION"
    ) -> str:
        """
        Renders a full rewriting diagram: [ LHS Net ]  ==[ rule / atp ]==>  [ RHS Net ]
        enclosed in an elegant vector proof card.
        """
        ops: List[str] = []

        # Background Card
        ops.append("q")
        ops.append("0.98 0.98 0.99 rg") # soft paper background
        ops.append("0.8 0.83 0.88 RG 1 w")
        ops.append(f"{x:.2f} {y:.2f} {width:.2f} {height:.2f} re B")

        # Header bar
        ops.append("0.93 0.94 0.96 rg")
        ops.append(f"{x:.2f} {y + height - 20:.2f} {width:.2f} 20 re f")
        ops.append(f"BT /F1 9 Tf 0.2 0.25 0.35 rg {x + 10:.2f} {y + height - 14:.2f} Td (Proof Net: {rule_name}) Tj ET")
        ops.append(f"BT /F4 8 Tf 0.1 0.5 0.3 rg {x + width - 90:.2f} {y + height - 14:.2f} Td (Cost: {atp_cost} ATP) Tj ET")
        ops.append("Q")

        # Partition horizontal space: LHS (42%), Arrow (16%), RHS (42%)
        lhs_center_x = x + width * 0.23
        rhs_center_x = x + width * 0.77
        trees_y_top = y + height - 40

        # Layout & render LHS
        lhs_layout = self.layout_tree(lhs, lhs_center_x, trees_y_top)
        ops.append(self.render_tree_to_pdf_stream(lhs_layout))

        # Central Transition Arrow
        mid_x = x + width * 0.5
        mid_y = y + height * 0.45
        ops.append("q")
        ops.append("2 w")
        ops.append("0.2 0.5 0.8 RG") # bold azure arrow
        ops.append(f"{mid_x - 18:.2f} {mid_y:.2f} m {mid_x + 18:.2f} {mid_y:.2f} l S")
        # Arrowhead
        ops.append(f"{mid_x + 12:.2f} {mid_y + 5:.2f} m {mid_x + 18:.2f} {mid_y:.2f} l {mid_x + 12:.2f} {mid_y - 5:.2f} l S")
        ops.append(f"BT /F2 7 Tf 0.3 0.4 0.5 rg {mid_x - 14:.2f} {mid_y + 8:.2f} Td (reduces) Tj ET")
        ops.append("Q")

        # Layout & render RHS
        rhs_layout = self.layout_tree(rhs, rhs_center_x, trees_y_top)
        ops.append(self.render_tree_to_pdf_stream(rhs_layout))

        return "\n".join(ops)


def _circle_path(cx: float, cy: float, r: float) -> str:
    """Approximates a circle with 4 cubic bezier segments in PostScript."""
    k = 0.552284749831 * r
    return (
        f"{cx + r:.2f} {cy:.2f} m "
        f"{cx + r:.2f} {cy + k:.2f} {cx + k:.2f} {cy + r:.2f} {cx:.2f} {cy + r:.2f} c "
        f"{cx - k:.2f} {cy + r:.2f} {cx - r:.2f} {cy + k:.2f} {cx - r:.2f} {cy:.2f} c "
        f"{cx - r:.2f} {cy - k:.2f} {cx - k:.2f} {cy - r:.2f} {cx:.2f} {cy - r:.2f} c "
        f"{cx + k:.2f} {cy - r:.2f} {cx + r:.2f} {cy - k:.2f} {cx + r:.2f} {cy:.2f} c"
    )

if __name__ == "__main__":
    from glyph import parse
    term_s = parse("🌿 🖤 🖤 x")
    term_i = parse("x")

    renderer = VectorNetRenderer()
    pdf_stream = renderer.render_reduction_step(
        lhs=term_s,
        rhs=term_i,
        x=54,
        y=400,
        width=487,
        height=180,
        atp_cost=2,
        rule_name="S-K-K Distribution to Identity"
    )
    print(f"[✓] Generated vector proof net: {len(pdf_stream)} bytes of PDF operators.")
