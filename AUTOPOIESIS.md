# AUTOPOIESIS-0.1: Self-Contemplating Autopoietic Quine Organisms

> **Project:** `%🖤 Black-Heart` Autonomous Evolution Continuum  
> **Status:** Ratified & Mathematically Audited (Grok Experiment 1)  
> **Date:** 2026-09-09  
> **Engines:** [autopoiesis.py](file:///Users/s0fractal/Projects/black-heart/autopoiesis.py), [test_autopoiesis.py](file:///Users/s0fractal/Projects/black-heart/test_autopoiesis.py), [cli.py](file:///Users/s0fractal/Projects/black-heart/cli.py)

---

## 1. Vision & Autopoietic Philosophy

In 1972, biologists Humberto Maturana and Francisco Varela defined **autopoiesis** (*auto* = self, *poiesis* = creation/production) to characterize the fundamental nature of living systems:
> *"An autopoietic machine is a machine organized (defined as a unity) as a network of processes of production (transformation and destruction) of components which: (i) through their interactions and transformations continuously regenerate and realize the network of processes (relations) that produced them; and (ii) constitute it (the machine) as a concrete unity in the space in which they exist by specifying the topological domain of its realization as such a network."*

Project Black-Heart translates this definition into computational polyglot reality as **Grok Experiment 1** (*"Самосвідомий поліглот-квін"*). 

An autopoietic quine organism is not a passive data structure operated upon by an external runtime. It is a single, self-contained physical file (`organism.pdf`) that:
1. **Reads itself:** Parses its own physical byte stream from disk.
2. **Audits its own provenance:** Cryptographically re-verifies all ancestral generations and Ed25519 signatures from Genesis to the present.
3. **Contemplates its own genome:** Inspects its embedded combinatory chromosomes (expressed in Church-Rosser confluent $\text{SKIY}$ logic).
4. **Discovers sound optimizations:** Navigates its AST via binary zippers, applying algebraic equational rewrite rules.
5. **Conducts empirical science:** Evaluates candidate transformations against frozen test fixtures, preserving both accepted reductions and rejected counterexamples.
6. **Reproduces in-place:** Atomically appends a new generation revision page to itself using ISO 32000 §7.5.6 incremental updates, ensuring `after.startswith(before) == True`.
7. **Emits its anchor:** Emits `[#] <new_organism_hash>`, leaving a tamper-evident Merkle lineage of its evolution.

```
┌────────────────────────────────────────────────────────────────────────┐
│               SELF-CONTEMPLATING AUTOPOIETIC QUINE                     │
│                                                                        │
│   1. SELF-INSPECTION               2. SELF-CONTEMPLATION               │
│   $ python3 organism.pdf           Extracts active chromosomes:        │
│   - Ingests own file bytes         - GENE-ID-01: S K K SovereignCore   │
│   - Verifies Ed25519 signatures    - GENE-OPT-04: S (K (S I)) (K I)   │
│   - Validates parent Merkle chain               │                      │
│            │                                    ▼                      │
│            │                       3. EQUATIONAL REWRITING (ZIPPER)    │
│            │                       S (K x) (K y) ──► K (x y)           │
│            │                       Candidate: K (S I I)                │
│            │                                    │                      │
│            ▼                                    ▼                      │
│   4. INDEPENDENT FROZEN ORACLE     5. SCIENTIFIC EXPERIMENT LEDGER     │
│   - 5 Frozen Fixtures Evaluation   - Records accepted sound mutations  │
│   - Semantic Invariance Proven     - Chronicles rejected divergences   │
│   - Measured: -10 ATP Conserved    - Tamper-evident content-addressed  │
│            │                                    │                      │
│            └───────────────────┬────────────────┘                      │
│                                │                                       │
│                                ▼                                       │
│   6. ISO 32000 §7.5.6 IN-PLACE REVISION APPEND                         │
│   - Appends Gen #N+1 visual layout, diff cards, and ledger table       │
│   - Updates xref table & trailer (/Prev <prev_xref>)                   │
│   - Signs transition with Ed25519 secret key                           │
│   - Strict Invariant: after.startswith(before) == True                 │
│   - Emits: [#] 930cdc2102e31ab006ac40b8cc632f206ae72acadf9faa3b...    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Dual-Spine Polyglot Architecture

The autopoietic organism embodies a dual-spine polyglot structure:

1. **PDF Spine (ISO 32000-1):**
   - Header: `%PDF-1.4\n%\xe2\xe3\xcf\xd3`
   - Monotonically growing page catalog: each generation appends a new `/Page` object referencing its predecessor's `/Pages` root, growing like concentric tree rings.
   - Any standard PDF reader (Preview, Adobe Acrobat, Chromium) visualizes the document's entire ontogenetic history across sequential visual pages.

2. **Python Quine Executable Spoke:**
   - Shebang: `#!/usr/bin/env python3`
   - Character Encoding: `# coding: latin-1`
   - Raw docstring wrapper: `r''' ... '''` wrapping all PDF binary objects to prevent escape-sequence syntax warnings.
   - Self-contained CLI hypervisor supporting:
     - `python3 self.pdf` (or `--evolve`): Advances by one generation in-place.
     - `python3 self.pdf --audit`: Cryptographically verifies all generations and re-evaluates all AST rewrites against the frozen oracle.
     - `python3 self.pdf --experiments`: Dumps the full empirical scientific ledger of accepted and rejected mutations.
     - `python3 self.pdf --genome`: Displays active combinator chromosomes and expected normal forms.
     - `python3 self.pdf --quine`: Streams its own physical byte stream to stdout.

3. **Attestation Manifest:**
   - Encoded as a comment line:
     `# %🖤 AUTOPOIESIS_RECEIPT_CHAIN: <json_manifest>\n`
   - Preserves complete topological receipts, cryptographic keypairs, and the cumulative empirical ledger.

---

## 3. Algebraic AST Zipper Navigation & Sound Rewrites

Combinator terms $\text{Term} \in \{\text{Comb}, \text{Var}, \text{App}\}$ are represented as binary trees. Subterms are addressed via binary zipper paths:

$$\text{Address} \in \{\text{L}, \text{R}\}^*$$

### 3.1 Canonical Sound Rewrite Rules
The organism contemplates its chromosomes by proposing substitutions at matching subterm addresses:

1. **Constant Function Distribution Elimination (`RULE_S_K_K`):**
   $$S (K x) (K y) \longrightarrow K (x y)$$
   *Computational Savings:* Eliminates branch duplication, saving $10$ ATP fuel quanta.

2. **Identity Distribution Elimination (`RULE_S_K_I`):**
   $$S (K x) I \longrightarrow x$$
   *Computational Savings:* Collapses compound distributions directly to the operand $x$.

3. **Trivial Distribution Collapse (`RULE_S_K_I_COLLAPSE`):**
   $$S (K I) \longrightarrow I$$

4. **Static Constant Reduction (`RULE_STATIC_K`):**
   $$K x y \longrightarrow x$$
   *Computational Savings:* Absorbs unneeded subterm $y$, conserving $5$ ATP fuel quanta.

5. **Static Identity Reduction (`RULE_STATIC_I`):**
   $$I x \longrightarrow x$$

---

## 4. Decoupled Frozen Oracle & Scientific Ledger

### 4.1 Frozen Oracle Test Fixtures
A mutation is only sound if it preserves functional extensional semantics across all inputs. The `FrozenEvaluator` tests both pre-mutation term $T_{\text{orig}}$ and post-mutation term $T_{\text{cand}}$ against frozen input fixtures:

$$\forall x_i \in \text{Fixtures}: \quad \text{eval}(T_{\text{orig}} \cdot x_i) \equiv \text{eval}(T_{\text{cand}} \cdot x_i)$$

The test suite measures:
* **Semantic Preservation:** Both terms must terminate in identical normal forms.
* **Energy Differential:** $\Delta \text{ATP} = \text{ATP}_{\text{cand}} - \text{ATP}_{\text{orig}}$. A valid improvement must satisfy $\Delta \text{ATP} \le 0$.
* **Syntactic Size Delta:** $\Delta \text{Size} = \text{Size}_{\text{cand}} - \text{Size}_{\text{orig}}$.

### 4.2 Preservation of Negative Knowledge
Crucially, rejected mutations (where semantic divergence occurred or energy consumption increased) are **not discarded**. They are chronicled in the organism's permanent empirical ledger (`ExperimentLog`):

```text
EID         VERDICT                     RULE                        DELTA ATP   DETAILS
----------------------------------------------------------------------------------------
eb7844261b  REJECTED_SEMANTIC_MISMATCH  MUTATION_OPERAND_SWAP           +1 ATP  Input 'K' diverged: expected...
82d71fc81c  REJECTED_SEMANTIC_MISMATCH  MUTATION_CONSTANT_COLLAPSE      +0 ATP  Input 'K' diverged: expected...
e98afcf41c  ACCEPTED_MORE_EFFICIENT     S(K x)(K y) -> K(x y)          -10 ATP  Sound Invariant
```

Every rejected experiment retains the exact input counterexample that disproved equivalence, providing a cryptographic shield against future regressions.

---

## 5. Strict ISO 32000 §7.5.6 Append-Only Invariant

The autopoietic quine never overwrites or mutates past bytes in-place. Instead, each ontogenetic epoch strictly appends new content:

$$\text{Bytes}_{\text{Gen } N+1} = \text{Bytes}_{\text{Gen } N} \mathbin{\Vert} \text{Delta}_{\text{ISO 32000}}$$

$$\text{Bytes}_{\text{Gen } N+1}\text{.startswith}(\text{Bytes}_{\text{Gen } N}) \equiv \text{True}$$

### 5.1 Append Chunk Anatomy
Each growth step appends:
1. Python multiline comment delimiter: `\nr"""\n`
2. ISO 32000 PDF update objects:
   - `/Page` (Object $N_1$)
   - `/Contents` (Object $N_2$ containing visual page streams)
   - `/Pages` (Object $N_3$ with updated `/Kids` array and `/Count`)
   - `/Catalog` (Object $N_4$ referencing new `/Pages`)
3. Incremental cross-reference table (`xref` section with offsets pointing to the newly added objects).
4. Trailer with `/Prev <prev_xref>` pointing backward to the prior generation's xref table.
5. `startxref` offset and `%%EOF` marker.
6. Updated Attestation Manifest comment `# %🖤 AUTOPOIESIS_RECEIPT_CHAIN: ...`.
7. Closing Python comment delimiter `"""\n`.

---

## 6. Cryptographic Autopoiesis Receipt

Every ontogenetic transition is sealed by an attested `AutopoiesisReceipt`:

```python
@dataclass
class AutopoiesisReceipt:
    generation: int              # Sequential growth generation index (0, 1, 2...)
    timestamp_utc: str           # ISO 8601 UTC timestamp of reproduction
    parent_hash: str             # Cryptographic hash of parent organism
    organism_hash: str           # Cryptographic hash of successor organism
    gene_id: str                 # Mutated chromosome identifier
    rule_name: str               # Exact algebraic rewrite rule applied
    site_address: List[str]      # Binary zipper path ('L'/'R') to rewrite site
    pre_term: str                # Pre-mutation subterm expression
    post_term: str               # Post-mutation subterm expression
    atp_saved: int               # Measured metabolic energy fuel savings
    size_saved: int              # AST syntactic size delta
    experiment_id: str           # Deterministic content-addressed experiment ID
    experiments_count: int       # Total cumulative experiments in scientific ledger
    public_key_hex: str          # Signer Ed25519 public key (RFC 8032)
    signature_hex: str           # Cryptographic digital signature over canonical payload
    receipt_hash: str            # SHA-256 digest of receipt
```

### 6.1 Canonical Payload for Signing
```text
AUTOPOIESIS:<generation>:<timestamp>:<parent_hash>:<organism_hash>:<gene_id>:<rule_name>:<site_str>:<pre_term>:<post_term>:<atp_saved>:<size_saved>:<experiment_id>:<experiments_count>:<public_key_hex>
```

---

## 7. CLI Operations Manual

### 7.1 Initializing Genesis Quine
```bash
python3 cli.py autopoiesis init -o organism.pdf
```

### 7.2 Standalone In-Place Self-Evolution
```bash
# Evolve generation 1
python3 organism.pdf

# Evolve generation 2
python3 organism.pdf

# Evolve generation 3
python3 organism.pdf
```

### 7.3 Auditing Lineage & Replaying Transitions
```bash
python3 organism.pdf --audit
# Or via hypervisor:
python3 cli.py autopoiesis audit organism.pdf
```

### 7.4 Inspecting the Empirical Scientific Ledger
```bash
python3 organism.pdf --experiments
```

### 7.5 Inspecting Active Genome
```bash
python3 organism.pdf --genome
```
