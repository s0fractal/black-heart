# LI-1 — proposal intake: schema, CLI contract, and parser inventory

Contract date: 2026-09-13. Status: **implemented; LI-1 format and CLI contract.**
Brief: [LIVING-LIBRARY-INTERACTION.md](LIVING-LIBRARY-INTERACTION.md) (§ "LI-1").
Source inspected: `91312d9`.

LI-1 delivers exactly two operations — `inspect` and `add-claim` — over **one**
PDF profile. It produces a **proposal artifact only**. It does not evaluate
evidence, does not decide admission, and writes no successor. Those are LI-2 and
LI-3.

## 1. Inventory: what is actually read and written

Read from source, not from descriptions. LI-1 adds no new PDF *writer*.

| surface | what it actually is | LI-1 use |
|---|---|---|
| `warrant_kernel.generate_warrant_ledger_pdf` | the **writer** that produces the supported parent profile | **not called by LI-1**; read to define the profile below, and used in tests to build fixtures |
| the manifest line it emits | `b"# %\xf0\x9f\x96\xa4 WARRANT_KERNEL_MANIFEST: " + json + b"\n"` | the **only** thing LI-1 parses out of the PDF |
| the embedded Python runner it emits | `data.find(b" WARRANT_KERNEL_MANIFEST: ")`, then `manifest.get("claims", [])`, then `TrustConfig.from_dict(manifest["trust_config"])` | **never executed, never delegated to**; its permissiveness is explicitly *not* inherited (see §3) |
| `warrant_kernel.EdgeClaim.from_dict` / `.verify_signature` / `.compute_claim_id` | claim transport + Ed25519 over `"warrant-sig-v1:" ‖ raw(claim_id)` | used to parse and **authenticate** the supplied claim |
| `warrant_kernel.canonical_jcs` | `json.dumps(sort_keys=True)`-class canonicalisation (bounded, self-contained) | used for the proposal body digest |
| `crypto.sign_hex` / `verify_hex` / `is_valid_public_key` | Ed25519 | used for the proposal envelope signature |
| `polyglot.PolyglotDocument.add_claim` | **builder-only**: appends a `Claim` record to an in-memory document being constructed | **not used** — it cannot address an existing PDF, which is precisely the gap LI-1 fills |
| `WarrantVerifier.audit_claim` | scoped PASS/FAIL/UNVERIFIED evaluation under caller policy | **not called in LI-1** (that is LI-2) |

## 2. The supported parent profile

Measured on a real artifact produced by `generate_warrant_ledger_pdf`, not
assumed:

- The file **does not begin with `%PDF`**. It begins with a Python shebang; in
  the measured sample `%PDF` appeared at offset 300. A reader that anchors on
  `%PDF` at offset 0 is wrong for this profile.
- Because the shebang embeds the **absolute host interpreter path**, these files
  are **not byte-reproducible across hosts**. The parent digest is therefore a
  property of a specific file, which is why LI-1 requires the caller to supply
  the expected digest rather than deriving trust from regeneration.
- The bare substring `" WARRANT_KERNEL_MANIFEST: "` occurs **twice** in an
  honest document: once in the manifest line, and once inside the embedded
  runner's own source (`    marker = b" WARRANT_KERNEL_MANIFEST: "`). Counting
  the bare substring would refuse every genuine document.

**Manifest line (normative for LI-1).** A line that *begins* a line (offset 0 or
immediately after `\n`) with the prefix

```
# %🖤 WARRANT_KERNEL_MANIFEST:<SP>
```

(bytes `23 20 25 F0 9F 96 A4 20 57 41 ... 3A 20`), whose payload runs to the next
`\n`. The payload is UTF-8 JSON. Exactly **one** such line must exist. In the
measured sample this strict form occurred exactly once while the bare substring
occurred twice.

**Line anchoring is a refusal, not a filter.** An occurrence of the strict
prefix that does *not* begin a line is not a manifest line under this contract —
but a reader anchoring differently (the embedded runner uses a bare `find`)
could select it instead. Rather than quietly pick one, LI-1 refuses such a file
as `MANIFEST_AMBIGUOUS`. On an honest document the anchored count and the total
prefix count are equal; when they disagree, no reading is authoritative.

**Manifest object.** `format` (must equal `"WARRANT-0.2"`), `claims` (a list),
`trust_config` (an object). All three are **required**; see §3.

## 3. Permissiveness that LI-1 deliberately does not inherit

The embedded runner is lenient in ways that would silently weaken intake. LI-1
refuses instead:

| runner behaviour | LI-1 behaviour |
|---|---|
| `data.find(marker)` — takes the **first** occurrence, ignores any others | counts strict manifest lines; `0` and `>1` are **distinct named refusals** |
| `manifest.get("claims", [])` — a **missing** claim collection silently becomes empty | `MANIFEST_FIELD_MISSING`: a missing `claims` is a refusal, never an empty list |
| `TrustConfig.from_dict(manifest["trust_config"])` — the document's own advertised policy | reported as an **advertisement only**; LI-1 grants it no authority and makes no decision from it |
| `json.loads` — last duplicate key silently wins | duplicate JSON keys are a named refusal (`MANIFEST_DUPLICATE_KEYS`) |

`EdgeClaim.from_dict` accepts a `claim_id` supplied in the dict and
`__post_init__` recomputes it **only when empty**, so a claim can carry an id
that disagrees with its body — and the signature covers the *stated* id.
`audit_claim` catches this, but LI-1 does not run `audit_claim`, so **LI-1
recomputes the claim id itself** and refuses a mismatch (`CLAIM_ID_MISMATCH`).

## 4. Size limits (checked before parsing)

| input | limit |
|---|---|
| parent PDF | 16 MiB |
| manifest line payload | 4 MiB |
| claim file | 1 MiB |
| proposal file | 4 MiB |

Exceeding a limit is a named refusal; nothing larger is parsed.

## 5. Proposal envelope — `black-heart.library-interaction.proposal.v1`

Document addressing lives in **this** envelope, versioned separately from the
claim. `EdgeClaim.parent_hash` / `successor_hash` are term addresses in another
domain and are **never** reinterpreted as PDF byte addresses.

```json
{
  "profile": "black-heart.library-interaction.proposal.v1",
  "body": {
    "operation": "add-claim",
    "parent_pdf_sha256": "<64 hex>",
    "parent_manifest_format": "WARRANT-0.2",
    "claim": { "claim_id": "...", "body": {...}, "signature_hex": "...", "endorsements": [] },
    "proposer_pk_hex": "<64 hex>"
  },
  "proposal_id": "<sha256 of canonical_jcs(body)>",
  "envelope_signature_hex": "<Ed25519 by proposer>"
}
```

- Everything that could retarget the proposal — the operation, the **parent byte
  digest**, the claim, and the proposer — is inside `body`, which the envelope
  signature covers. There is **no unsigned retargetable wrapper**.
- Envelope signature message is domain-separated and distinct from the claim's:
  `"bh-li1-proposal-v1:" ‖ raw_bytes(proposal_id)`. A claim signature can never
  be replayed as an envelope signature, or the reverse.
- **The claim author and the proposer are different identities.** They may be the
  same key, but the envelope records them separately and never conflates them.
- **The envelope signature authenticates the sealer, not the contents.** A
  receiver of an external envelope must never assume it was produced by this
  `add-claim`, so `verify_proposal` repeats the **same** claim authentication
  that intake performs — structure, recomputed claim id, author signature —
  through one shared function (`authenticate_claim_document`), and validates
  **every** signed body field, including `parent_manifest_format`: a genuine
  signature over an unknown profile does not make that profile supported.
  `claim_authenticated: true` in a result means exactly those three checks; it
  is not evaluation (LI-2) and not admission.
- **No file paths or file names appear in the signed body.** Paths are locators;
  identity is the digest and the key.

## 6. CLI contract

```
python3 cli.py library inspect --pdf <path> [--proposal <path>] [--json]
python3 cli.py library add-claim --pdf <path> --expect-parent-sha256 <hex>
                                 --claim <path> --proposer-key-file <path>
                                 --out <path> [--json]
```

- `--expect-parent-sha256` is **required** and caller-supplied. LI-1 never
  derives the pin from the file it is checking.
- `--proposer-key-file` reads the secret key from a **file**, never from `argv`
  (process listings leak arguments). The key is never echoed.
- `--out` must **not already exist**; a pre-existing output is a refusal and is
  left byte-identical.
- `inspect --proposal` additionally reports whether that proposal is bound to
  that PDF. This is how "a second parent cannot consume it as its own" is
  exercised through the real CLI.
- Exit codes: `0` success, `2` named refusal, `1` unexpected error.

**The input PDF is never executed.** It is opened `"rb"` and scanned as bytes.

## 7. Named refusals

`PARENT_UNREADABLE`, `PARENT_TOO_LARGE`, `PARENT_PIN_MISMATCH`,
`MANIFEST_ABSENT`, `MANIFEST_DUPLICATE`, `MANIFEST_AMBIGUOUS`,
`MANIFEST_UNTERMINATED`,
`MANIFEST_TOO_LARGE`,
`MANIFEST_NOT_JSON`, `MANIFEST_DUPLICATE_KEYS`, `MANIFEST_NOT_OBJECT`,
`MANIFEST_FIELD_MISSING`, `MANIFEST_FIELD_TYPE`, `MANIFEST_UNSUPPORTED_FORMAT`,
`CLAIM_UNREADABLE`, `CLAIM_TOO_LARGE`, `CLAIM_NOT_JSON`,
`CLAIM_DUPLICATE_KEYS`, `CLAIM_MALFORMED`, `CLAIM_ID_MISMATCH`,
`CLAIM_SIGNATURE_INVALID`, `UNSUPPORTED_OPERATION`, `PROPOSER_KEY_UNREADABLE`,
`PROPOSER_KEY_MALFORMED`, `OUTPUT_EXISTS`, `OUTPUT_UNWRITABLE`,
`PROPOSAL_UNSUPPORTED_MANIFEST_FORMAT`, and the other `PROPOSAL_*`
(parse/profile/signature/binding). The envelope reader returns the same
`CLAIM_*` names as intake for the same claim defect — one vocabulary, one
shared check, on both paths.

Every refusal is a named result on stderr/JSON with exit 2. On any refusal the
input PDF, the claim file, the key file and any pre-existing output are left
**byte-identical**.

## 8. What LI-1 does not establish

A proposal is **not** an admission. LI-1 authenticates *who proposed what,
against which exact bytes* — it does **not** check whether the claim's
mathematics holds, and it never prints "accepted claim". A well-formed proposal
carrying false or unverified mathematics is still a well-formed proposal.

Grade is **recorded, not gated**, at intake: the brief assigns first-supported-
grade selection to LI-2, so LI-1 does not pre-empt it.

LI-1 makes no statement about R2/R3, adds nothing to the frozen EXP-LIB-001
package, and closes no scan residual.
