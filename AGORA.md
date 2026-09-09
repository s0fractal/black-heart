# AGORA-0.1: Mycelial Social Democracy & Consensus Parliament

> **Project:** `%🖤 Black-Heart` Collective Governance Continuum  
> **Status:** Ratified & Cryptographically Audited  
> **Date:** 2026-09-09  
> **Engines:** `agora.py`, `test_agora.py`

---

## 1. Vision & Constitutional Philosophy

In distributed multi-agent systems, collective decision-making typically degenerates into either centralized autocracy or plutocratic token voting, where entities with the largest balance dictate constitutional rules. 

**Mycelial Social Democracy** (`agora.py`) establishes an anti-plutocratic governance architecture inspired by biological mycelial networks. Organisms allocate metabolic energy (ATP) into quadratic ballots to ratify combinatory theorems, adjust ecosystem parameters, and append irreversible constitutional amendments to a shared polyglot document.

```
      ┌────────────────────────────────────────────────────────────┐
      │                   COLONY OF AGENTS                         │
      │       Alice (16 ATP)       Bob (64 ATP)      Carol (1 ATP) │
      └─────────────────────────────┬──────────────────────────────┘
                                    │
                                    ▼
      ┌────────────────────────────────────────────────────────────┐
      │                  QUADRATIC VOTING CHAMBER                  │
      │       Alice: +4 Votes     Bob: +8 Votes     Carol: +1 Vote │
      │               Total Effective Vote: +13 Votes              │
      └─────────────────────────────┬──────────────────────────────┘
                                    │
                                    ▼
      ┌────────────────────────────────────────────────────────────┐
      │            COMBINATORIAL THEOREM AUDIT (FAIL-CLOSED)       │
      │       Extensional & Intensional Normal Form Reduction      │
      │              (e.g., S K I $x ──> $x verified)              │
      └─────────────────────────────┬──────────────────────────────┘
                                    │
                                    ▼
      ┌────────────────────────────────────────────────────────────┐
      │             RATIFIED CONSTITUTIONAL SETTLEMENT             │
      │       - Multi-Signed Ed25519 Parliamentary Receipt         │
      │       - ISO 32000 §7.5.6 Incremental PDF Page Append       │
      │       - Gini Coefficient Telemetry Logged                  │
      └────────────────────────────────────────────────────────────┘
```

---

## 2. Anti-Plutocratic Quadratic Voting

### 2.1 Quadratic Power Formulation
Let $w_i \in \mathbb{Z}$ be the ATP stake pledged by agent $i$, where $\operatorname{sign}(w_i) \in \{+1, -1\}$ denotes support (`YEA`) or opposition (`NAY`). The voting weight $v_i$ is defined by:

$$v_i = \operatorname{sign}(w_i) \cdot \lfloor\sqrt{|w_i|}\rfloor$$

### 2.2 Plutocracy Resistance Proof
Consider an oligarchical agent allocating $100$ ATP versus $100$ independent grassroots agents each allocating $1$ ATP:

* **Oligarch:** $w_{\text{whale}} = 100 \implies v_{\text{whale}} = \sqrt{100} = 10 \text{ votes}$.
* **Grassroots:** $\sum_{j=1}^{100} v_j = 100 \times \sqrt{1} = 100 \text{ votes}$.
* **Ratio:** The collective voice outweighs the oligarch by $10:1$, preserving phenotypic diversity and ecosystem resilience.

---

## 3. Mathematical Gini Inequality Coefficient

The Agora monitors concentration of energy and power among participants using the Gini coefficient $G \in [0, 1]$:

$$G = \frac{\sum_{i=1}^n \sum_{j=1}^n |w_i - w_j|}{2 n \sum_{i=1}^n w_i}$$

* $G = 0$: Perfect equality (all participants contribute identical ATP).
* $G \to 1$: Extreme concentration (a single participant dominates ATP stake).
* High Gini alerts are embedded in the parliamentary visual telemetry HUD.

---

## 4. Fail-Closed Combinator Theorem Ratification

Democracy cannot vote mathematical falsehoods into truth. If a proposal proposes a `COMBINATOR_THEOREM`:
1. The engine extracts the LHS and RHS expressions.
2. Performs intensional normal form evaluation via the `glyph.py` reducer.
3. Tests extensional equivalence across formal variables (e.g., evaluating both sides applied to free test variable `$x`).
4. **Mandatory Invariant:** If normal forms do not coincide or exceed monotonic fuel limits, the proposal is marked `REJECTED_AUDIT_FAILED`, regardless of votes.
5. **Stake Slashing:** The sponsor's pledged ATP is slashed, preventing spam attacks on the assembly.

---

## 5. Parliamentary Session Lifecycle

```python
@dataclass
class ConsensusSettlementReceipt:
    session_id: int              # Incremental parliamentary session counter
    timestamp_utc: str           # ISO 8601 UTC timestamp
    proposal: AgoraProposal      # Proposal text, type, and expression
    total_yeas: int              # Cumulative quadratic affirmative votes
    total_nays: int              # Cumulative quadratic negative votes
    gini_coefficient: float      # Inequality measure across all cast ballots
    quorum_reached: bool         # True if total ballots >= constitutional quorum
    passed: bool                 # True if yeas > nays and theorem audit sound
    final_status: str            # RATIFIED | REJECTED_VOTE | REJECTED_AUDIT_FAILED
    ratification_hash: str       # SHA-256 digest of session result
    signatures: List[str]        # Multi-signed Ed25519 attestations
```

---

## 6. CLI Reference Guide

```bash
# 1. Initialize a new Agora Parliament polyglot
python3 cli.py agora init -o parliament.pdf

# 2. Inspect latest parliament status & telemetry
python3 cli.py agora status parliament.pdf

# 3. View constitutional Merkle ancestry chain
python3 cli.py agora lineage parliament.pdf

# 4. Cryptographically audit all parliamentary sessions
python3 cli.py agora audit parliament.pdf
```
