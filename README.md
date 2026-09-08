# Project Black-Heart (%🖤)

> **"A paper should not just assert its truth. A paper should execute its own proof."**

**Black-Heart** is an experimental laboratory for:
1. **Glyph Combinatory Logic (`glyph.py`):** Pure SKIY calculus defined on UTF-8 glyphs (`🖤`, `🤍`, `🌿`, `🔁`, `⚓`) with deterministic ATP budgets and content-addressed normal form hashing.
2. **Self-Executing Proof-Carrying PDF Polyglots (`polyglot.py`, `monad.py`):** Compilers producing files that are simultaneously **100% valid ISO 32000 PDF documents** (rendering in macOS Preview, Chrome, Acrobat) and **100% valid executable Python scripts** (`python3 document.pdf`).
3. **Living Ledgers & Consensus Chains (`living_ledger.py`, `mesh.py`):** Append-only ISO 32000 incremental update chains with cryptographic settlement seals and peer-to-peer gossip mesh synchronization.
4. **Sovereign Pure-Python Cryptography (`crypto.py`, `zk_glyph.py`):** Strict RFC 8032 Ed25519 signatures, zero-knowledge proofs (Schnorr & Chaum-Pedersen DLog), and non-malleable fail-closed decoding.
5. **Symmetric Interaction Combinators (`interaction.py`, `vector_net.py`):** Optimal graph-rewriting evaluation nets with vector PostScript geometry generation.
6. **Autonomous Organisms & Symbiosis (`organism.py`, `symbiosis.py`):** Self-reproducing quine polyglots, Artin braid group recombination, and safe lineage amalgamation.
7. **Topological Quantum Topos (`quantum.py`):** Universal $B_3$ braid profile, non-Abelian Fibonacci anyons, Born measurement collapse, and standalone unitary invariance auditing.
8. **Turing Morphogenesis (`morphogenesis.py`):** Gray-Scott reaction-diffusion PDEs on $\mathbb{T}^2$, 256-bit coprime entropy folding, and native vector contour rendering.
9. **Form Metamorphosis & Self-Contemplation (`metamorphosis.py`):** Binary AST zipper rewriting, frozen invariant oracle evaluation, empirical experiment ledgers, and tamper-evident transition replay receipts.

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

## 6. Zero-Dependency Ed25519 Cryptography (`crypto.py`)

To ensure complete self-containment without supply chain risks or platform-specific binaries, **Black-Heart** includes a pure-Python implementation of **RFC 8032 Ed25519**:
* **Pure Integer Arithmetic:** Operates directly over the prime field $\mathbb{F}_{2^{255}-19}$ and twisted Edwards curve $-x^2 + y^2 = 1 - \frac{121665}{121666} x^2 y^2$.
* **Zero Dependencies:** Requires only Python's built-in `hashlib.sha512` and `os.urandom`.
* **Tamper-Evident Seals:** Provides `CryptographicSeal` to bind public keys, digital signatures, and content digests into document manifests.

---

## 7. Native PDF Vector Proof Nets (`vector_net.py`)

Rather than treating documents as plain text with comments, `vector_net.py` compiles SKIY combinatory reduction expressions directly into **PostScript 2D vector graphics streams**:
* **Visual Semantics:**
  - `🖤` (K / Black Cone): Obsidian filled circle with golden border and branch absorption mark.
  - `🤍` (I / White Cone): Pearl circle with through-flow wire.
  - `🌿` (S / Spore): Emerald green node with mycelial branching wires.
  - `🔁` (Y / Fixpoint): Royal indigo loop.
  - `@` (App): Slate application junction ring.
* **Vector Proof Cards:** Renders reduction steps $\text{LHS} \xrightarrow{\text{ATP}} \text{RHS}$ using native PDF operators (`m`, `l`, `c`, `re`, `B`, `S`).

---

## 8. The Living Polyglot Ledger (`living_ledger.py`)

Using **ISO 32000-1 §7.5.6 (Incremental Updates)**, `living_ledger.py` implements an append-only verifiable ledger file:
* **The Living Document:** A single file `living_ledger.pdf` starts with Genesis (Block 0) and grows across time as network participants append signed transactions and proof nets.
* **Dual Nature:**
  - **In Preview / Acrobat:** Renders as an authentic multi-page ledger with vector proof net diagrams, timestamps, and Ed25519 cryptographic seals on each page.
  - **In Python:** Run `python3 living_ledger.pdf` to audit the entire hash chain from Genesis to tip and verify all Ed25519 signatures.

### Quickstart: Compile & Audit Living Ledger
```bash
# 1. Compile multi-block living ledger:
python3 examples/living_ledger_demo.py

# 2. View as visual document:
open examples/living_ledger.pdf

# 3. Audit directly as executable code:
python3 examples/living_ledger.pdf
```

---

## 9. Symmetric Interaction Combinators (`interaction.py`)

In 1990, Yves Lafont discovered that universal Turing-complete computation requires only three symmetric 2-port / 1-principal agents interacting via local graph rewiring:
* **Construct / Seed (`🌱` / $\gamma$):** Pairs data structures.
* **Duplicate / Clone (`👥` / $\delta$):** Distributes signals and clones environments.
* **Erase / Void (`🕳️` / $\epsilon$):** Absorbs signals and frees resources.

### Key Invariants:
* **Strictly Constant-Time:** Every graph rewiring step takes $O(1)$ time and burns exactly 1 ATP.
* **No Variable Capture:** Completely eliminates $\alpha$-conversion, de Bruijn indices, and global environments.
* **Annihilation ($\alpha \bowtie \alpha$), Commutation ($\gamma \bowtie \delta$), and Erasure ($\alpha \bowtie \epsilon$).**

See formal specification: [INTERACTION.md](file:///Users/s0fractal/Projects/black-heart/INTERACTION.md).

---

## 10. Unified Command Suite & Proof REPL (`cli.py`)

Black-Heart includes a complete command-line toolkit for interactive research and automated polyglot verification:

```bash
# 1. Interactive combinator REPL with live ATP meter:
python3 cli.py repl

# 2. Audit and verify any proof-bearing polyglot PDF:
python3 cli.py verify examples/service_agreement_polyglot.pdf
python3 cli.py verify examples/living_ledger.pdf

# 3. Bilateral Cross-Proof Adjudication between two independent PDFs:
python3 cli.py adjudicate examples/bilateral_agreement.pdf examples/provider_telemetry_oracle.pdf

# 4. Pack & Unpack ISO 32000 Embedded Code Vaults:
python3 cli.py vault pack src_dir/ -o vault.pdf -t "Repository Snapshot"
python3 cli.py vault unpack vault.pdf -d restored_dir/

# 5. Generate fresh RFC 8032 Ed25519 keypairs:
python3 cli.py keygen --json

# 6. Compile a new proof-carrying document:
python3 cli.py compile -t "Autonomous Manifesto" -o manifesto.pdf

# 7. Synthesize offspring via dialectical symbiosis:
python3 cli.py synthesize examples/parent_a.pdf examples/parent_b.pdf -o child.pdf

# 8. Simulate non-Abelian Fibonacci anyon quantum braiding:
python3 cli.py quantum simulate "trefoil"

# 9. Synthesize Turing reaction-diffusion morphogenetic phenotype:
python3 cli.py morph --archetype labyrinth --steps 350 -o labyrinth.pdf

# 10. Contemplate organism form and mint metamorphic successor:
python3 cli.py metamorph examples/organism_gen0.pdf -o successor.pdf
```

---

## 11. Autonomous Self-Replicating Polyglot Organisms (`organism.py`)

Implementing John von Neumann's Theory of Self-Reproducing Automata (1966) directly inside executable ISO 32000 PDF polyglots:
* **Genotype:** Embedded SKIY combinator chromosomes (`%🖤 ORGANISM_GENOME: [...]`).
* **Phenotype:** An authentic visual document displaying the cellular passport, membrane color derived from its Ed25519 identity, and vector proof nets of its chromosomes.
* **Metabolic Selection:** Evaluates chromosome convergence against ATP limits. Only healthy, converging genomes survive to replicate.
* **Quine Reproduction:**
  ```bash
  # 1. Spawn Genesis Organism (Gen #0000):
  python3 examples/genesis_organism.py

  # 2. View organism phenotype in PDF reader:
  open examples/organism_gen0.pdf

  # 3. Trigger autonomous quine-reproduction:
  python3 examples/organism_gen0.pdf --reproduce
  # Outputs: organism_gen0001_<child_hash>.pdf with newly derived Ed25519 keypair and mutations!
  ```

See formal specification: [GENOME.md](file:///Users/s0fractal/Projects/black-heart/GENOME.md).

---

## 12. Bilateral Interlocking Documents (`cross_proof.py`)

Eliminating centralized webhooks and escrow servers:
* **The Dual-Document Problem:** Traditional smart contracts rely on centralized cloud oracles. In Black-Heart, both the agreement (e.g. cloud SLA) and the telemetry oracle are independent self-verifying polyglot PDFs signed by their respective Ed25519 identities.
* **Cross-Adjudication:** Running `cross_proof.py` (or executing `cli.py adjudicate`) allows the agreement PDF to ingest the telemetry oracle PDF, verify its Ed25519 signature against the agreed public key, evaluate combinator SLA equations, and compute deterministic financial adjustments.
* **Joint Witness Anchor:** Produces a cryptographic dual-document digest $\mathcal{H}(D_{\text{agreement}} \mathbin{\Vert} D_{\text{oracle}} \mathbin{\Vert} \text{Resolution})$ ensuring neither party can retroactively substitute claims.

```bash
# 1. Run bilateral settlement demo:
python3 examples/bilateral_settlement_demo.py

# 2. Adjudicate bilateral agreement against telemetry oracle:
python3 cli.py adjudicate examples/bilateral_agreement.pdf examples/provider_telemetry_oracle.pdf
```

See formal specification: [CROSS_PROOF.md](file:///Users/s0fractal/Projects/black-heart/CROSS_PROOF.md).

---

## 13. ISO 32000 Embedded Code Vaults (`vault.py`)

Turning proof-carrying PDF documents into portable, deterministic software vaults:
* **Reproducibility Guarantee:** A paper or specification embeds its entire source tree, tests, and dependencies into an ISO 32000 EmbeddedFiles stream or polyglot binary payload.
* **Self-Extraction:** Executing `python3 paper.pdf --unpack-vault <dir>` or `cli.py vault unpack paper.pdf` unpacks the bit-for-bit identical repository tree with SHA-256 verification.
* **Mathematical Invariance:** The embedded archive is canonicalized with normalized timestamps and permissions for deterministic hashing.

---

---

## 14. Suspended Continuum Computations (`continuum.py`)

Fulfilling [CONTINUUM.md](file:///Users/s0fractal/Projects/black-heart/CONTINUUM.md):
* **Non-Destructive Reduction:** Eliminates "Out of Gas" crashes. When the ATP budget runs out, the computation pauses gracefully into a **Suspended Thunk** with an immutable checkpoint digest.
* **Resumable Polyglot PDFs:** A single ISO 32000 PDF document displays an active ATP fuel gauge and execution progress.
* **Incremental Resumption:** Running `python3 computation.pdf --fuel <N>` evaluates $N$ additional steps, appends an incremental update block (ISO 32000 §7.5.6) with a new page, and updates the checkpoint on disk! When normal form is reached, a final Q.E.D. settlement seal is rendered.

```bash
# Run continuum thunk demo:
python3 examples/continuum_thunk_demo.py

# Resume directly on the PDF:
python3 examples/resumable_computation.pdf --fuel 5000
```

---

## 15. Pure-Python Zero-Knowledge Proofs on Ed25519 (`zk_glyph.py`)

Bringing Non-Interactive Zero-Knowledge Proofs (NIZK) to documents with ZERO external dependencies:
* **Schnorr Identity Proofs:** Proves possession of a sovereign Ed25519 secret key ($P = s \cdot B$) in zero knowledge via Fiat-Shamir heuristics ($R = r \cdot B, \; z = r + e \cdot s$).
* **Chaum-Pedersen DLog Equality:** Proves that two public points across independent generators share the same secret exponent without revealing the exponent ($P_1 = s \cdot G, \; P_2 = s \cdot H$).
* **Confidential Procurement Contracts:** Enables parties to verify credentials, solvency reserves, and compliance thresholds in $< 5\text{ms}$ while keeping underlying data confidential.

```bash
# Run zero-knowledge contract demo:
python3 examples/zk_contract_demo.py

# Audit the ZK contract PDF:
python3 examples/confidential_procurement_contract.pdf
```

---

## 16. P2P Polyglot Mesh Synchronization (`mesh.py`)

Turning Living Polyglot Ledgers into autonomous, gossip-capable network nodes:
* **Decentralized Synchronization:** Multiple instances of a living ledger document synchronize missing blocks over HTTP or local files without central servers or databases.
* **Direct PDF Ingestion:** Received blocks are validated against their Ed25519 signatures and appended directly into the local physical PDF binary file using ISO 32000 §7.5.6.
* **Fork & Byzantine Resistance:** Automatically detects and rejects conflicting chains or forged block signatures.

```bash
# Serve ledger node over HTTP:
python3 cli.py mesh serve my_ledger.pdf --port 8765

# Sync another ledger PDF from peer:
python3 cli.py mesh sync peer_ledger.pdf --peer http://127.0.0.1:8765
```

---

## 17. Dialectical Symbiosis & Topological Knots (`symbiosis.py`)

Realizing the autonomous sexual recombination and evolutionary synthesis of polyglot organisms:
* **Artin Braid Group ($B_n$):** Full algebraic modeling with Artin generators $\sigma_1, \dots, \sigma_{n-1}$, braid relations ($\sigma_i \sigma_{i+1} \sigma_i = \sigma_{i+1} \sigma_i \sigma_{i+1}$), and topological knot invariants (crossing number, writhe, Alexander closure components). Includes canonical knots: Trefoil ($3_1$), Figure-eight ($4_1$), Hopf link ($2_1^2$), and Whitehead link ($5_1^2$).
* **Dialectical Synthesis:** Combines Thesis and Antithesis parent genomes via genetic crossover, generating non-trivial topological braids encoding their lineage.
* **Safe Vault Amalgamation:** Content-addressable deduplication of identical files, and dynamic conflict disambiguation (`lineage_b/{rel}`, `lineage_b_2/{rel}`, etc.) preventing any existing files from either parent from being overwritten.
* **Lineage Provenance Auditor:** Standalone runner verifying child genomic integrity against embedded chromosomes, parent derivation hashes, and chromosome metabolism with honest reporting (`METABOLIC REPLAY & GENOMIC INTEGRITY VERIFIED`).

```bash
# Synthesize offspring from two parent polyglots:
python3 cli.py synthesize examples/parent_a.pdf examples/parent_b.pdf -o child.pdf

# Audit lineage provenance:
python3 child.pdf --lineage
```

---

## 18. Topological Quantum Topos & Fibonacci Anyons (`quantum.py`)

Universal topological quantum computation in the non-Abelian quantum Hall regime with ZERO external dependencies:
* **SU(2)_3 Chern-Simons & Fibonacci Anyons:** Models non-Abelian anyon braiding where quantum gates correspond to topological braids in $B_3$.
* **Strict Single-Qubit Profile:** Restricted strictly to $B_3$ profile ($n \le 3$, generators $\sigma_1, \sigma_2$), raising `UnsupportedBraidProfileError` on higher strands to preserve mathematical group homomorphisms.
* **Born Rule & Bloch Sphere Mapping:** Calculates state vector $|\psi\rangle = \alpha |0\rangle + \beta |1\rangle$, Born measurement collapse probabilities, and 3D Bloch sphere coordinates $(\theta, \phi)$.
* **Rigorous Standalone Quantum Auditor:** Recomputes and verifies all unitary invariants from frozen matrix operands ($U^\dagger U = I$, $\|\det(U)\| = 1$, Born rule $P(0), P(1) \in [0, 1]$, $P(0)+P(1)=1$, Bloch vector), failing closed on invalid matrices.

```bash
# Simulate topological anyonic quantum gate:
python3 cli.py quantum simulate "trefoil"

# Compile standalone quantum circuit polyglot PDF:
python3 cli.py quantum compile -b "trefoil" -o quantum_circuit.pdf

# Audit quantum unitary invariants and projective Born collapse:
python3 quantum_circuit.pdf --audit
python3 quantum_circuit.pdf --measure 1024
```

---

## 19. Turing Morphogenesis & Reaction-Diffusion Phenotypes (`morphogenesis.py`)

Endowing every autonomous polyglot organism with an organic, visual **Morphogenetic Phenotype**:
* **Alan Turing (1952) / Gray-Scott (1983) PDEs:** Solves continuous non-linear reaction-diffusion equations on a discrete 2D toroidal lattice $\mathbb{T}^2$ with guaranteed physical concentration clamping $[0.0, 1.0]$.
* **Six Spontaneous Symmetry-Breaking Archetypes:** Leopard Spots (Pearson $\alpha$), Labyrinthine Gyri (Class $\lambda$), Zebrafish Waves (Class $\theta$), Honeycomb Holes (Class $\gamma$), Soliton Droplets (Class $\delta$), Mitotic Pulsars (Class $\mu$).
* **Full 256-Bit Entropy Folding:** Folds all 256 bits of SHA-256 hashes using coprime 64-bit mixing into perturbation seeds and parameter drift, avoiding XOR cancellation on repetitive bit patterns.
* **Native ISO 32000 Vector PostScript Compilation:** Generates circular vesicle meshes and marching-squares isoline contours directly via PostScript operators inside standalone executable polyglots.

```bash
# Synthesize Turing morphogenesis phenotype PDF:
python3 cli.py morph --archetype labyrinth --steps 350 --grid 40 -o labyrinth.pdf
python3 cli.py morph --archetype spots --palette BIOLUMINESCENT_CYAN -o leopard.pdf

# View PDF and execute embedded simulation:
open labyrinth.pdf
python3 labyrinth.pdf --simulate --steps 300
```

---

## 20. Autonomous Form Metamorphosis & Program Self-Contemplation (`metamorphosis.py`)

Empowering computational organisms to contemplate, inspect, and optimize their own source code:
* **Addressable Program Zipper:** Traverses and mutates subterms via binary tree address paths $\tau \in \{'L', 'R'\}^*$ over pure SKIY combinator trees.
* **Equational Algebraic Rewrites:** Discovers sound simplifications ($S(K x)(K y) \to K(xy)$, $S(K x)I \to x$, $I x \to x$, $K x y \to x$) that save runtime ATP reductions on every invocation.
* **External Invariant Evaluator (`FrozenEvaluator`):** Decoupled test harness with frozen fixtures verifying $100\%$ functional equivalence while measuring energy conservation ($\Delta \text{ATP} < 0$) and syntactic compression ($\Delta \text{Size}$).
* **Scientific Experiment Ledger (`ExperimentLog`):** Preserves both accepted transitions and rejected mutations (divergence counterexamples, neutral mutations) as permanent empirical records.
* **Successor Minting & Replay Auditor:** Successor carries an immutable `MetamorphicTransitionReceipt`. The standalone auditor independently replays the transition from the parent payload and re-runs the oracle, failing closed on forged claims.

```bash
# Contemplate form and synthesize metamorphic successor:
python3 cli.py metamorph [organism.pdf] -o successor.pdf

# Inspect transition passport and energy savings:
python3 successor.pdf --info

# Audit transition replay and oracle invariants:
python3 successor.pdf --audit

# View full positive and negative experiment ledger:
python3 successor.pdf --experiments
```

---

## 21. Comprehensive Test Suite

Run all **114 unit tests** across all **14 engines** with a single command:
```bash
# Unified test runner:
python3 test_all.py

# Or via CLI:
python3 cli.py test

# Or individually:
python3 test_glyph.py          # 9 tests: SKIY reduction, ATP ceilings, Church encoding
python3 test_monad.py          # 7 tests: Dual trees, visual/semantic compilation, AST
python3 test_living_ledger.py  # 5 tests: Incremental PDF updates, multi-block chains
python3 test_interaction.py    # 6 tests: Symmetric interaction combinators, rewiring
python3 test_organism.py       # 4 tests: Self-reproducing polyglot automata, quines
python3 test_cross_proof.py    # 3 tests: Bilateral cross-proofs & embedded code vaults
python3 test_continuum.py      # 4 tests: Suspended continuum thunks & incremental resumption
python3 test_zk_glyph.py       # 5 tests: Pure-Python Ed25519 zero-knowledge proofs & NIZK
python3 test_mesh.py           # 3 tests: Peer-to-peer living polyglot mesh sync & gossip
python3 test_security_audit.py # 44 tests: Adversarial security audit, fail-closed verifiers (G1-G9, R1-R8, N1-N5, F1-F4, H1-H4, J1-J7, K1-K6)
python3 test_symbiosis.py      # 5 tests: Dialectical symbiosis & Artin braid group recombination
python3 test_quantum.py        # 5 tests: Topological quantum computing, Fibonacci anyons, unitary audit
python3 test_morphogenesis.py  # 7 tests: Gray-Scott PDEs, Turing bifurcation, marching squares
python3 test_metamorphosis.py  # 7 tests: Program self-contemplation, frozen evaluator, transition replay
```

---

## 22. Specifications & Theory

* [CONTINUUM.md](file:///Users/s0fractal/Projects/black-heart/CONTINUUM.md) — Suspended Thunks, Neutral Oracles & Merkle-Stream Continuity.
* [MONAD.md](file:///Users/s0fractal/Projects/black-heart/MONAD.md) — The Literate Polyglot Monad, Dual Trees & Proof-Bearing Legal Contracts.
* [INTERACTION.md](file:///Users/s0fractal/Projects/black-heart/INTERACTION.md) — Lafont's Symmetric Interaction Combinators on UTF-8 Glyphs.
* [GENOME.md](file:///Users/s0fractal/Projects/black-heart/GENOME.md) — Autonomous Self-Replicating Polyglot Automata.
* [CROSS_PROOF.md](file:///Users/s0fractal/Projects/black-heart/CROSS_PROOF.md) — Bilateral Interlocking Documents & Embedded Code Vaults.

---

## 23. License

* **Code (`glyph.py`, `polyglot.py`, `monad.py`, `crypto.py`, `vector_net.py`, `living_ledger.py`, `interaction.py`, `organism.py`, `cross_proof.py`, `vault.py`, `continuum.py`, `zk_glyph.py`, `mesh.py`, `symbiosis.py`, `quantum.py`, `morphogenesis.py`, `metamorphosis.py`, `cli.py`, tests):** AGPL-3.0-only
* **Texts & Polyglot artifacts:** CC BY-SA 4.0

