# Project Black-Heart (%🖤)

> **"A paper should not just assert its truth. A paper should execute its own proof."**

**Black-Heart** is an experimental laboratory for:
1. **Glyph Combinatory Logic (`glyph.py`):** Pure SKIY calculus defined on UTF-8 glyphs (`🖤`, `🤍`, `🌿`, `🔁`, `⚓`) with deterministic ATP budgets and content-addressed normal form hashing.
2. **Self-Executing Proof-Carrying PDF Polyglots (`polyglot.py`):** A compiler producing files that are simultaneously **100% valid ISO 32000 PDF documents** (rendering in macOS Preview, Chrome, Acrobat) and **100% valid executable Python scripts** (`python3 document.pdf`).

---

## 1. The Genesis of `%🖤`

According to the PDF specification (ISO 32000-1 §7.5.2), the first line is `%PDF-1.x`, and the second line must be a comment (`%`) containing at least four binary characters (bytes $> 127$) to prevent legacy 7-bit ASCII transmission channels from mangling line breaks (`\r\n`).

While most software outputs arbitrary garbage like `%âãÏÓ`, the `WeasyPrint` engine used the UTF-8 encoding of the black heart emoji:
```text
%PDF-1.7
%🖤
```
In UTF-8, `🖤` is encoded as `0xF0 0x9F 0x96 0xA4` (bytes 240, 159, 150, 164) — exactly four binary bytes $> 127$. 

In **Black-Heart**, we turn this comment into the **executable root of the Black Cone**.

---

## 2. The Glyph Combinator Calculus (SKIY)

Instead of bloated natural language keywords, the language operates directly on structural glyphs:

| Glyph | Combinator | Operational Semantics | Conceptual Meaning |
|---|---|---|---|
| **`🖤`** | **K** | $K \; x \; y \;\to\; x$ | **Black Cone / Constant:** Absorbs and drops the second argument. Enforces closure. |
| **`🤍`** | **I** | $I \; x \;\to\; x$ | **White Cone / Identity:** Pure flow of signal without transformation. |
| **`🌿`** | **S** | $S \; x \; y \; z \;\to\; (x \; z)(y \; z)$ | **Spore / Distribution:** Copies environment into branches (mycelial expansion). |
| **`🔁`** | **Y** | $Y \; f \;\to\; f \; (Y \; f)$ | **Fixpoint:** Recurrent time loop / standing wave. |
| **`⚓`** | **Settlement** | `⚓⟨atp: N, hash: H⟩` | **Receipt:** Normal-form content-addressed digest with bounded ATP cost. |

### Derived Primitives:
* **Church TRUE:** `🖤`
* **Church FALSE:** `(🖤 🤍)` ($K \; I$)
* **Boolean Negation:** `🌿 (🖤 (🖤 🤍)) (🖤 🖤)`
* **Identity via Spore:** `🌿 🖤 🖤` (evaluates to identity in 2 ATP steps)
* **Omega (Divergence):** `(🌿 🤍 🤍) (🌿 🤍 🤍)` (caught and terminated by the ATP budget ceiling)

---

## 3. The Self-Executing Polyglot (`polyglot.py`)

A polyglot PDF compiled with `polyglot.py` contains:
1. **The Visual Layer:** Clean PDF text layout, typography, section banners, and claim boxes.
2. **The Semantic Layer:** Embedded `%🖤 CLAIM: id=... | expr=... | expected=...` streams within the PDF comment structure.
3. **The Execution Layer:** An appended standalone Python runtime at the tail of the document.

### Quickstart

#### 1. Run unit tests on the combinator engine:
```bash
python3 test_glyph.py
```

#### 2. Compile an executable polyglot PDF:
```bash
python3 polyglot.py
```
This generates `examples/manifesto_polyglot.pdf` (or `/tmp/manifesto_polyglot.pdf`).

#### 3. View it as a visual PDF:
Open it with your favourite PDF viewer or macOS Preview:
```bash
open examples/manifesto_polyglot.pdf
```

#### 4. Run it as an executable verifier:
Directly invoke Python on the PDF binary:
```bash
python3 examples/manifesto_polyglot.pdf
```

Output:
```text
=================================================================
  %🖤 BLACK-HEART — SELF-EXECUTING PROOF-CARRYING PDF RUNNER
  Target file: manifesto_polyglot.pdf (8398 bytes)
=================================================================

[+] Discovered 3 embedded %🖤 claims. Executing deterministic reductions...

  [CLAIM K-DROP] K-combinator drops the second argument (Constant)
    Input:    🖤 Truth Mirage
    Result:   Truth
    Receipt:  ⚓ SETTLED ⟨atp:1, hash:cc3a062a97bf⟩

  [CLAIM SKK-ID] SKK behaves identically to Identity (White Cone 🤍)
    Input:    🌿 🖤 🖤 Signal
    Result:   Signal
    Receipt:  ⚓ SETTLED ⟨atp:2, hash:1e9806e4227b⟩

  [CLAIM CHURCH-FALSE] Application of Church FALSE returns the right branch
    Input:    (🖤 🤍) Left Right
    Result:   Right
    Receipt:  ⚓ SETTLED ⟨atp:2, hash:883361d5d682⟩

-----------------------------------------------------------------
[⚓ GREEN] ALL 3/3 CLAIMS SETTLED DETERMINISTICALLY (5 ATP burned).
Document integrity & proof verification: 100% SOUND.
```

---

## 4. The Literate Polyglot Monad & Dual Trees (`monad.py`)

A fundamental limitation of classical literate programming and smart contracts is **Documentation Drift** and the loss of human context:
* Smart contracts discarded human legal language and judicial jurisdiction.
* Conventional digital signatures (DocuSign, SaaS PDFs) are inert raster images detached from executable rules.

**Black-Heart** resolves this via the **Literate Polyglot Monad** and **Dual-Spine Trees**:
$$\mathcal{M}(A) = \langle S_{\text{comp}}, \; P_{\text{doc}}, \; A \rangle$$

* **Dual-Ended Stream Writing:** Interpreters (Python) read sequentially from byte offset 0 (`head-seeking`), while ISO 32000 PDF readers parse backward from `%%EOF` via `startxref` (`tail-seeking`). Both programs reside in the exact same file without offset collisions.
* **Dual-Spine Trees (`DualTree`):**
  - **Code Spine:** AST / DAG of computable contract rules, predicates, and ATP gas budgets ($H_{\text{code}}$).
  - **Visual Spine:** Document Object Model of the PDF page, legal articles, and typography ($H_{\text{visual}}$).
  - **Joint Merkle Anchor:** $H_{\text{dual}} = \text{SHA-256}(H_{\text{code}} \mathbin{\Vert} H_{\text{visual}})$. Any tampering with text or code breaks the anchor.
* **Anti-Drift Invariant:** Every monadic step ($\gg=$) atomically advances both the computational predicate and the visual presentation page ($\Delta S \iff \Delta P$).

See formal specification: [MONAD.md](file:///Users/s0fractal/Projects/black-heart/MONAD.md).

---

## 5. Self-Verifying Proof-Bearing Contracts

A proof-bearing contract polyglot compiled with `monad.py`:
1. Opens in standard PDF viewers (Preview, Acrobat, Chrome) as an authentic legal agreement.
2. Directly executes in Python: `python3 contract.pdf`.
3. Reads its embedded legal predicates, checks incident evidence logs (aligned with `warrant`), verifies the dual-spine anchor, and prints a deterministic settlement receipt `⚓`.

### Running the Contract Polyglot:

#### 1. Run all unit tests (Glyph Calculus + Monad Laws):
```bash
python3 test_glyph.py
python3 test_monad.py
```

#### 2. Compile and run the Cloud SLA Agreement:
```bash
python3 examples/service_agreement_polyglot.py
python3 examples/service_agreement_polyglot.pdf
```

Output:
```text
======================================================================
  %🖤 BLACK-HEART — SELF-VERIFYING PROOF-BEARING CONTRACT ADJUDICATOR
  Target File: service_agreement_polyglot.pdf (10146 bytes)
======================================================================

[*] Document Title: CLOUD SERVICE LEVEL AGREEMENT & ESCROW PROTOCOL
[*] Jurisdiction:   Ukraine / International Commercial Arbitration
    - PROVIDER: Nebula Hypercloud Infrastructure Ltd. (ed25519:e4f1a8c9b2010874ff)
    - CLIENT: Axiom Financial Technologies Inc. (ed25519:7b03df129c8e541a02)
    - ADJUDICATOR: Autonomous Black-Heart Settlement Arbiter (ed25519:c991823abf1055de77)

[*] Declared Dual-Spine Anchor: cfaf765e73ff29d1f79520b59bfd06a00b8210f1e4b0784848d9c85b130a63d4
[✓ GREEN] Document integrity sound. Dual-spine anchor verified.

[*] ADJUDICATING EVIDENCE LOG:
    [INCIDENT] INC-2026-09-02: Edge Gateway DNS Blackhole (180 min) | Hash: 2cd24f397ca91f0d
    [INCIDENT] INC-2026-09-05: NVMe Storage Fabric Degradation (120 min) | Hash: b651c519a72b61aa

    Total Downtime: 300 minutes (Period: 43200 min)
    Measured Uptime: 99.306% (Target: >=99.5%)
----------------------------------------------------------------------
[⚓ SETTLED: SLA BREACH CONFIRMED]
  Penalty Assessed:   $500 USD (1 x 0.1% brackets below SLA)
  Net Service Due:    $9,500 USD (Base: $10,000 USD)
  Receipt Digest:     ⚓ ⟨atp:42, digest:5ab543d0523ea023⟩
======================================================================
```

---

## 6. Specifications & Theory

* [CONTINUUM.md](file:///Users/s0fractal/Projects/black-heart/CONTINUUM.md) — Suspended Thunks, Neutral Oracles & Merkle-Stream Continuity.
* [MONAD.md](file:///Users/s0fractal/Projects/black-heart/MONAD.md) — The Literate Polyglot Monad, Dual Trees & Proof-Bearing Legal Contracts.

---

## 7. License

* **Code (`glyph.py`, `polyglot.py`, `monad.py`, tests):** AGPL-3.0-only
* **Texts & Polyglot artifacts:** CC BY-SA 4.0
