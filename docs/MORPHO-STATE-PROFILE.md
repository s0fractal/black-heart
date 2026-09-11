# Morpho-autopoiesis state profile

Written for S6a (review R2).

A **state profile** is a verification contract: it says which documents an
auditor accepts, not merely which JSON keys a manifest has. The manifest
declares it as `state_profile`.

| profile | auditor guarantee |
|---|---|
| `morpho-autopoiesis.transition-bound.v1` | every measured pair is bound to the genome transition it claims to describe |
| *(absent)* | written before this contract existed — **outside the accepted domain** |

## The break, stated plainly

S6a binds each receipt's measured pair to the real parent→result transition by
replaying the genome backwards through the chain and requiring every receipt's
already-signed `organism_hash` to reconstruct from the genome its own epoch
actually held.

That replay must reconstruct each historical genome **exactly**, which requires
canonical expression spelling all the way back to genesis. `str(parse(x))`
renders glyphs (`"S (K alpha) I"` → `"🌿 (🖤 alpha) 🤍"`), and the round trip is
lossy in the ASCII direction. The previous generator stored a hand-written ASCII
genesis, and no later epoch can retroactively canonicalize that already-signed
state.

**So the accepted domain of existing signed state changed.** Measured against
documents built by the previous generator, at generations 0, 1 and 5:

```
generation 0 previous_audit True current_audit False bytes_unchanged True
generation 1 previous_audit True current_audit False bytes_unchanged True
generation 5 previous_audit True current_audit False bytes_unchanged True
```

These are honest documents. No receipt is forged or malformed. Adding a signed
field was not what created the break, and "no new receipt field" does not imply
"no migration" — an earlier version of this work claimed exactly that, and it
was wrong.

## The policy: refusal, not repair

A document without a supported profile is **refused by name**, and its bytes and
signatures are left exactly as they are.

- `audit_morpho_autopoietic_organism` returns `False`.
- `unsupported_history_reason(path)` returns the named reason and the guidance
  below. `None` is **not a certificate of validity** — it says only that this
  contract has no objection, and it is also what an unreadable document
  returns, since refusing that is the ordinary audit's business.
- `evolve_morpho_autopoietic_organism` raises that reason **before any
  mutation**, so a refused document is never modified — and its owner is told
  their history is unsupported, not that their honest document is "tampered".
  It must of course read the file to find the marker: the guarantee is that
  nothing is written, not that nothing is read.

The replay is **not** weakened to let old artifacts through. Accepting them would
mean accepting a genome the chain cannot reconstruct, which is precisely the hole
R1 closed.

### The profile marker is routing, never trust

Declaring the current profile on an old document does **not** make it pass — the
transition replay still refuses it. Removing the marker from a current document
only earns the refusal above. The marker can never grant acceptance; it only
chooses which named refusal you get instead of an opaque hash mismatch. It is
therefore safe that the marker is not covered by any signature.

## What an owner of an older document can do

There is **no in-place migration**, and none should be attempted. Normalizing
the genesis spelling and re-signing the chain would destroy the attested history
the document exists to carry — a re-signed chain is a new claim wearing an old
document's name.

Two supported options, both honest:

1. **Keep the document as it is.** Verify and continue it with the pinned
   pre-S6a code (`413f1ce`). Historical verification under pinned old semantics
   is a separate question from granting new economy credit under this profile.
2. **Start a new chain** with the current code. This explicitly does **not**
   preserve the old attested history; the old document remains valid under its
   own pinned semantics, and the new chain begins its own.

Only newly created chains are supported by this profile. That is the whole of
the compatibility promise, stated so it cannot be mistaken for a migration.
