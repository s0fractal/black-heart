# LI-2 — evidence evaluation and an attributed admission decision

Date: 2026-09-13. Status: **contract for the LI-2 implementation in this PR.**
Brief: [LIVING-LIBRARY-INTERACTION.md](LIVING-LIBRARY-INTERACTION.md) (§ "LI-2").
Builds on [LI-1](LIBRARY-INTERACTION-LI1.md). Source inspected: `0cea65e`.

LI-2 adds one operation, `evaluate`. It **records a decision and nothing else**:
no successor PDF, no ATP, no reward, no change to the parent, no promotion. That
is LI-3.

## 1. The two quantities are separate

**Evaluation** is what the host verifier found when it replayed the evidence.
**Admission** is what the caller's policy permits. They are different fields of
the decision and are never collapsed:

| evidence | policy | admitted |
|---|---|---|
| `PASS` | permits the operation and grade | `true` |
| `PASS` | does not permit them | `false` |
| `FAIL` | anything | `false` |
| `UNVERIFIED` | anything | `false` |

The status values are the host verifier's own (`VerificationStatus`), used
verbatim and never re-encoded: they are **lowercase** (`pass`, `fail`,
`unverified`) while `EvidenceGrade` values are uppercase. LI-2 reads both from
the enums rather than restating them.

`PASS` means **the named evidence check passed**, not that the claim is true in
general. `FAIL` is a checked negative. `UNVERIFIED` is **no verdict** — a refusal
(budget exhausted, untrusted author, grade not admitted) is not a refutation.
Admission being `false` is a policy outcome, never a mathematical claim.

## 2. Grade G evaluation, through the real verifier

LI-2 calls `warrant_kernel.WarrantVerifier.audit_claim` with the **caller's**
`TrustConfig`. It does not reimplement the evaluator and adds no adapter
defaults. For Grade G that path parses the witness term, reduces it under the
witness's ATP budget, and:

- reduction **settles** and the hash **matches** → `PASS`;
- reduction **settles** and the hash **differs** → `FAIL`;
- reduction **does not settle** within the budget → `UNVERIFIED` (an unsettled
  computation is not a proof; the budget refusal is not a verdict);
- witness budget above the policy limit → `UNVERIFIED`, evaluated no further.

**Grade G is the only supported grade.** Any other grade is a named unsupported
operation until it is selected in a later slice — including in the *policy*: a
policy that admits another grade is refused rather than silently narrowed.

## 3. The caller's policy — `black-heart.library-interaction.policy.v1`

```json
{
  "profile": "black-heart.library-interaction.policy.v1",
  "trust_config": {
    "trusted_author_pks": ["<64 hex>", "..."],
    "admitted_grades": ["GROUNDED"],
    "max_atp_budget": 10000,
    "require_bound_signature": true
  },
  "allowed_operations": ["add-claim"],
  "allowed_grades": ["GROUNDED"]
}
```

The policy is **supplied by the caller** and is never read out of the parent
document, the proposal, or a default. Two configurations are **refused outright**
rather than used, because the brief forbids an implicit no-signature or
trust-all policy:

- `trusted_author_pks` absent or `null` → `POLICY_TRUST_ALL`. In
  `TrustConfig.is_author_trusted`, `None` means *trust everyone*; an **empty
  list is a legitimate deny-all** and is accepted.
- `require_bound_signature` not exactly `true` → `POLICY_NO_SIGNATURE`.

`policy_sha256 = SHA-256(canonical_jcs(policy))` is what the decision binds, so
editing a saved policy invalidates every decision that cited it.

## 4. The decision — `black-heart.library-interaction.decision.v1`

```json
{
  "profile": "black-heart.library-interaction.decision.v1",
  "body": {
    "proposal_id": "...", "parent_pdf_sha256": "...", "policy_sha256": "...",
    "claim_id": "...", "claim_author_pk_hex": "...", "proposer_pk_hex": "...",
    "evaluator": {"profile": "black-heart.li2.grounded-evaluator.v1", "version": "1",
                  "atp_budget_requested": 0, "atp_budget_limit": 0, "atp_spent": 0},
    "evaluation": {"status": "pass|fail|unverified", "grade": "GROUNDED", "reason": "..."},
    "admission": {"admitted": false, "reason": "..."},
    "decider_pk_hex": "..."
  },
  "decision_id": "<sha256 of canonical_jcs(body)>",
  "decision_signature_hex": "<Ed25519 by the decider>"
}
```

- The decision **binds** the proposal identity, the parent byte digest, the
  policy digest, the evaluator profile/version, the **actual** budget figures
  and the scoped evidence result — all inside the signed body. Substituting any
  of them changes `decision_id`, which breaks the signature: **a decision cannot
  be transferred to another subject, policy or parent.**
- It is **attributed**: the decider signs it, domain-separated as
  `"bh-li2-decision-v1:" ‖ raw(decision_id)`, distinct from the LI-1 envelope
  and warrant claim domains.
- A saved decision is a **report, not a grant**. `verify_decision` re-derives the
  id and signature and checks the caller's expected proposal/parent/policy pins;
  it never trusts the stated fields.
- **A signature is attribution, not evidence.** Re-signing a body with the same
  key must not launder its content, so the reader validates the **nested**
  content *before using any field*: the evaluator profile and version must be
  supported, every field set must be exact, budgets must be non-negative ints,
  the verdict and grade must be known values, reasons must be strings, and
  `admission.admitted: true` over a non-`pass` verdict is
  `DECISION_INCONSISTENT`. Each is a named refusal; none raises.
- `atp_spent` is recorded **only from an explicit measurement**. `Verdict
  .delta_atp` defaults to `0`, so a branch that never ran a reduction is
  otherwise indistinguishable from one that measured zero; when nothing was
  measured the decision records `atp_spent: null` with
  `atp_spent_measured: false`, and a body claiming an unmeasured `0` is refused.
- Verifying a decision establishes **who sealed it** and that its content is
  well-formed and self-consistent. The result says so explicitly:
  `attribution_verified: true`, `evidence_replayed_by_reader: false`,
  `decider_authority_established: false`. A self-declared signing key is not
  authority; a reader needing either must establish it itself.

## 4bis. Producer and reader agree by construction

Whatever `evaluate` writes, this host's own reader must accept under the
matching pins. That is enforced structurally, not promised: the formed decision
body is passed through **the reader's own `validate_decision_body`** before it
is signed or written, and a body this host would refuse to read is never
emitted (`DECISION_SELF_CHECK_FAILED`). Inputs that would produce such a body
are refused earlier and more precisely — a witness `atp_budget` that is not a
non-negative int is `CLAIM_BUDGET_INVALID`, checked **before** any reduction
runs and before anything is written, so no output file is created.

## 5. Preconditions checked before any evaluation

`evaluate` re-runs the full LI-1 authentication rather than trusting that the
proposal came from this host: the parent PDF is parsed as data, the proposal
envelope and the claim inside it are authenticated, and the proposal must bind
the parent's exact bytes. Only then is evidence replayed.

## 6. CLI

```
python3 cli.py library evaluate --pdf <parent> --proposal <p.json> --policy <pol.json>
                                --decider-key-file <k> --out <decision.json> [--json]
python3 cli.py library inspect --pdf <parent> [--proposal <p>] [--decision <d>]
```

`--policy` is **required**; there is no default policy and no adapter fallback.
The CLI calls the same functions the API exposes. `--out` must not exist. Exit
`0` success, `2` named refusal, `1` unexpected error. A refusal writes nothing
and leaves every input byte-identical.

## 7. Named refusals

`POLICY_UNREADABLE`, `POLICY_TOO_LARGE`, `POLICY_NOT_JSON`,
`POLICY_DUPLICATE_KEYS`, `POLICY_NOT_OBJECT`, `POLICY_UNSUPPORTED_PROFILE`,
`POLICY_FIELD_MISSING`, `POLICY_FIELD_TYPE`, `POLICY_TRUST_ALL`,
`POLICY_NO_SIGNATURE`, `POLICY_UNSUPPORTED_GRADE`,
`POLICY_UNSUPPORTED_OPERATION`, `POLICY_BUDGET_INVALID`,
`CLAIM_BUDGET_INVALID`, `DECISION_SELF_CHECK_FAILED`,
`DECISION_UNSUPPORTED_EVALUATOR`, `DECISION_FIELD_MISSING`,
`DECISION_FIELD_TYPE`, `DECISION_INCONSISTENT`, and the other `DECISION_*`
(parse/profile/id/signature and the proposal, parent and policy pin mismatches),
plus every LI-1 refusal, which still applies first.

## 8. What LI-2 does not do

No successor artifact, no receipt, no ATP or reward, no modification of the
parent, no promotion of grade, no deletion or reinterpretation of existing
claims. A decision with `admitted: true` authorises nothing by itself — LI-3
must re-check the parent and policy at the point of use.
