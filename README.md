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

## 4. License

* **Code (`glyph.py`, `polyglot.py`, tests):** AGPL-3.0-only
* **Texts & Polyglot artifacts:** CC BY-SA 4.0
