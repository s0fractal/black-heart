# Living library: proposals, decisions, and immutable PDF successors

Date: 2026-09-13. Status: **selected direction and task brief, not implemented**.
Source inspection: `91312d9f5a974b7dede0c700538188c2ef802f6e`.

The owner's next objective is a useful local interaction loop, not immediate
publication. A reader should be able to propose a claim to a particular PDF,
receive a bounded decision, and inspect the path to a successor. A later
versioned release should preserve that path, not merely a changelog.

Public OTS stamping and Zenodo publication are deferred. This choice does not
cancel R2 or R3; neither is a prerequisite for implementing local interaction.
Do not keep proposing stamping as the automatic next task. No network service,
domain, public submission, or publication is authorized by this brief.

## What the code already provides

This inventory is a source reading, not a new security audit or runtime result.

| Existing surface | Actual role | Missing for this interaction |
|---|---|---|
| `polyglot.PolyglotDocument.add_claim` | Adds an expression/expected-result record to a document builder in memory | Not a submitted `EdgeClaim`, not admission to an existing PDF, no proposal decision |
| `warrant_kernel.EdgeClaim`, `GroundedWitness`, `WarrantVerifier.audit_claim` | Signed claim transport and scoped PASS / FAIL / UNVERIFIED evaluation | Claim validity is not authorization to change a particular PDF |
| `cli.py cmd_warrant_kernel`, `warrant-kernel compile/audit/promote` | Demo compilation, host audit under caller policy, promotion path | No external proposal intake or immutable successor workflow |
| `generate_warrant_ledger_pdf` | Serializes claims and renders a PDF with an embedded runner | Does not bind a proposal/decision to the exact parent and final output bytes |
| `living_ledger.LivingLedger.append_block`, `compile` | Signed block collection and PDF rendering | Not this typed proposal/admission protocol; loading a manifest is not admission |
| `autopoiesis.evolve_autopoietic_organism`, `check_palimpsest_guard` | Existing evolutionary path, scoped guard and in-place evolution | Broader biological/economic semantics, not the minimal library claim operation |
| `experiments/EXP-LIB-001/run.py` | Fixed three-event experiment, replay, saved-package reader, separate R2 result | `build_journal` chooses C1/C2/C3 itself; no user-submitted next event |

Important adapter boundary: the warrant-ledger embedded runner still reads its
own manifest's trust configuration and imports host code. Its behavior is not
the host CLI's caller-policy audit contract. The new path must **read PDF bytes
as data**, never execute an input PDF or delegate authority to its embedded
runner. Reusing a renderer requires inspecting its actual output path; do not
inherit its "trustless" or full-document verification wording.

An `EdgeClaim.parent_hash` or `successor_hash` is not automatically a PDF byte
hash. Existing claims use those fields in other domains, including term hashes.
Keep document addressing in a separately versioned envelope; preserve existing
signed claim bytes. Do not rename a term address into a document address.

## The first behavior we want

Start with **adding a supported, bounded claim to a library state**, not changing
the PDF's executable code or synthesizing a new evaluator. Use signed Grade G
grounded claims for the first slice: a settled match, a settled mismatch, and an
exhausted budget already have distinct outcomes in the host verifier. This is
an intentionally small admission policy, not a new universal proof system.

Conceptual CLI vocabulary, **not existing commands or a frozen syntax**:

1. `inspect`: identify the exact input PDF and the supported manifest profile.
2. `add-claim`: create a proposal targeting those exact bytes; do not admit it.
3. `evaluate`: reproduce evidence under externally selected policy and budget.
4. `apply`: revalidate admission and produce a distinct successor artifact.
5. `explain-transition`: verify and display proposal, decision and exact change.

The first supported input is one explicitly defined warrant-ledger PDF profile,
not arbitrary PDFs or every Black-Heart engine. Define an unambiguous envelope
and size limits before implementing its parser. Duplicate manifests, duplicate
JSON keys, unsupported versions, missing fields and wrong types must have named
outcomes; a missing claim collection must not silently become an empty one.

The PDF is "almost a subject" operationally: it has an address, a history and
an advertised set of operations. The trusted host CLI enacts those operations
under caller authority. Advertising a policy in the document does not authorize
it. A signing key identifies a signer, not a person or an independent voter.

## Bindings and state semantics

- A proposal binds the exact parent PDF digest, operation/profile, signed claim
  bytes, and proposer identity. Distinguish claim author from proposer. Names
  and paths are locators, not identities. No unsigned retargetable wrapper.
- The caller supplies the expected parent digest and policy. Evidence
  verification, admission policy, and authority to write a successor are
  separate checks. Policy permits specified operations/grades/authors and has
  a bounded evaluator budget. No embedded trust-all fallback.
- A decision binds proposal identity, parent digest, policy digest, evaluator
  profile/version, actual budget and scoped evidence result. A saved decision
  is a report, not an unchecked grant that `apply` can retarget or flip to PASS.
- PASS means the named evidence check passed. Admission additionally requires
  the selected policy. FAIL is a checked negative; UNVERIFIED is no verdict.
  Policy refusal is not a mathematical refutation. Errors do not become any
  kind of positive result.
- Rejected or unverified proposals can retain separate decision records for
  explanation. They create no admitted claim, successor, ATP payment or tombstone.
- An accepted addition preserves the parent's admitted claim records and adds
  exactly the proposed claim once. No automatic promotion, re-signing of old
  claims, deletion of contradictions, or reinterpretation of their scope.
- Preserve the parent file byte-for-byte. Derive the successor's byte address
  after rendering. Do not embed a whole-file hash into the file it hashes.
  A detached transition receipt can bind the final parent/output byte digests
  and decision; identify the receipt's authorized issuer independently.
- Repeating the same application must not add another claim or silently
  overwrite another output. Check the current parent and policy again at the
  point of use. Test failure followed by retry and an intervening state change.
- Multiple files are not automatically a transaction. Before LI-3 lands,
  specify staging, publication, failure recovery and how readers distinguish a
  prepared artifact from a completed transition. Do not claim rollback merely
  because writes were reordered.
- Verification of received transition artifacts must not regenerate them.
  Regeneration/reproducibility is a separate result, as in the frozen package.

## Work selected for Claude

These are sequential reviewable PRs, not parallel implementations. CLI names
below are provisional. No new engine number is needed.

### LI-1 — proposal intake for one PDF profile (start here)

Deliver `inspect` and `add-claim` as a small local CLI/API path. The input is an
existing supported PDF plus an explicit signed claim; output is a proposal
artifact only. Begin the PR with a short schema/CLI contract and an inventory
of every parser/writer actually used. The first implementation should require
an externally supplied expected parent byte digest and authenticate the
proposal envelope; do not invent the claim, subject or proposer in a demo
fallback. Demo fixtures are explicit test inputs.

Suggested new module: `library_interaction.py`; thin routing in `cli.py`;
`test_library_interaction.py` registered in `test_all.py`. Add normative format
details in a companion document when fixed. Inspect adjacent code to reuse
primitives, but do not rewrite all legacy PDF readers in this PR.

Acceptance: a real CLI subprocess creates a parseable, parent-bound proposal
from a supplied claim; a second parent cannot consume it as its own. Missing,
malformed or duplicate manifests, invalid claim/envelope signatures, wrong
parent pin and unsupported operation/profile are named refusals. Input PDF,
key files and pre-existing output remain byte-identical on refusal. Do not
execute input PDF code. A well-formed proposal with unverified mathematics is
still only a proposal: intake must not print "accepted claim".

Review LI-1 before starting LI-2. No renderer or successor is required yet.

### LI-2 — evidence evaluation and an attributed admission decision

Use the actual `WarrantVerifier` with caller-selected policy. First supported
grade is G; other grades are named unsupported operations until selected.
Keep replay verdict and admission outcome distinct in the result. Caller
policy must require the relevant signature checks; no implicit no-signature
or trust-all configuration. Produce a decision artifact without state effects.

Acceptance: settled match passes evidence and can be admitted under the named
policy; settled mismatch fails; suspension remains UNVERIFIED. The same claim
under a policy that does not authorize its author cannot be admitted. Mutating
the proposal target, claim, policy or cached verdict cannot transfer a decision
to another subject. Rejected attempts preserve state. Both CLI and direct API
must exercise the same authoritative check, without adapter defaults.

### LI-3 — immutable successor and a readable, replayable transition

Only after LI-2 review, implement `apply` and `explain-transition`. Inspect the
chosen renderer and manifest transport before reuse; prefer a data-only PDF
output profile for this path, with host CLI instructions rather than an
embedded self-auditor. Any changes needed there belong in this scoped PR and
must be called out, not assumed safe because another engine passed tests.

Acceptance: one real parent PDF plus one authorized claim yields one new PDF
and a transition receipt. A fresh verifier given the exact parent, successor,
proposal, decision/receipt and caller pins can confirm that the old claims
remain and precisely the proposed claim was added. Altering any of those
artifacts is detected for the property it purports to establish. Inspection
must show grade/scope, admitted versus merely proposed claims, and the reason
for refusal or acceptance without labeling the whole PDF universally true.

Test output-write failure, existing output, retry, two different proposals
against the same parent, and a stale parent. Do not call divergent children a
global conflict that requires electing one newest state. Run subprocess tests
through the real CLI and at least one saved-artifact substitution followed by
the next operation; assert exact state effects, not only exit codes.

## Completion and what stays out of scope

The local milestone is one user-supplied proposal reaching a verified successor
or a named non-success, with the parent preserved and the path inspectable.
This is necessary for the intended *interactive* living library; a static
knowledge graph would not require self-change. It is not evidence of subjective
agency or proof that every statement in a document is true.

Keep OTS, Zenodo, hosting, gossip, quorum, rewards, autonomous synthesis,
organization/persona secrets and executable self-modification out of LI-1–3.
Retain the six scan residuals and other ledger entries; no new closure is
claimed. Reassess them if the selected implementation actually imports their
paths. Counterexample/refinement operations and conflict-driven proposal
generation are later slices, not implicit consequences of adding a claim.

Preserve `experiments/EXP-LIB-001/README.md` (pre-registration), `r2-anchor/`
frozen bytes and historical signatures. Do not extend its fixed three-event
journal by silently changing `build_journal`. Give the interaction protocol a
separate versioned format. Later releases can publish parent/successor and
transition evidence together; release numbering and timestamps do not replace
that evidence or authorize its claims.

Related: [EXP-LIB-001](EXP-LIB-001.md), [R2 profile](EXP-LIB-001-R2.md),
[conflict as an action prompt](CONFLICT-AS-ACTION-VECTOR.md),
[Persona proposal](../PERSONA.md), [remediation ledger](REMEDIATION-LEDGER.md).
