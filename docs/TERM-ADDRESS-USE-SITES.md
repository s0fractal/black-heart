# Term addressing — use-site ledger (S3d)

Measured at `f98ee5e`, before the change in this branch. The question per site is
what it can be handed: text that went through `parse`, an AST built directly, or
an artifact recovered from bytes.

`glyph.canonical_bytes` writes a variable as `$name` and an application as
`(left right)`. That determines the term only while no name contains a space or
a `$`, because otherwise the split between siblings can move:

```
App(Var('a'), Var('b $c'))   ->  ($a $b $c)
App(Var('a $b'), Var('c'))   ->  ($a $b $c)      # different terms, one address
```

`parse` cannot produce such a name — it tokenizes `$` on its own — so **text is
inside the unambiguous domain**. `Var` and `App` are public constructors and do
not restrict anything, so any site that accepts an AST is exposed.

## Measured consequences

| Site | Input | Consequence, measured |
|---|---|---|
| `SporeStore.forward` cache key | AST | `forward(B)` returned **A's normal form** with `cached=True`; B was never evaluated |
| `SporeStore.audit` receipt | AST | `audit(B, receipt_for_A)` returned `True, "AUDIT_VERIFIED_HONEST"`: a receipt certified a term it was not about |

## Structural exposure, not demonstrated

Listed because the encoding reaches them, **not** because an exploit was shown.
Each would need its own reproduction before being called a defect.

| Site | Input | Note |
|---|---|---|
| `goedel.evaluate_with_cycle_detection` history | AST | keyed by `term_hash`; two colliding terms in one reduction would read as a repeat, i.e. a false limit cycle. No reduction sequence producing a collision was constructed |
| `epistemic_swarm` gene/tombstone matching | parsed text | `glyph.parse(c.expression)` — inside the unambiguous domain |
| `metamorphosis.FrozenEvaluator.fixtures_fingerprint` | AST, built in code | joins `canonical_bytes` with `:`; the fixtures are combinators, inside the domain in practice |
| `EvalResult.hash` in badges and printed receipts | AST | display and settlement text |

## Not this encoding

| Site | Uses |
|---|---|
| `warrant_kernel.GroundedWitness.expected_hash` | a term address **stored in a signed claim**, but produced from `term_expr` through `parse`, so inside the unambiguous domain. Left on the legacy digest deliberately: changing it would invalidate signed history |
| `mycelium` normal-form registry | its own `sha256` over expression **strings**, not `canonical_bytes` |
| `autopoiesis`, `morpho_autopoiesis`, `goedel` record signing | each has its own `canonical_bytes_for_signing` over record fields |

## What changed in this branch

- `glyph.term_address(term)` returns `glyph.term.v2:<hex>` under a prefix-free
  encoding: every node tagged, every leaf length-prefixed.
- `glyph.term_hash` stays, documented as legacy and unambiguous only inside
  `in_legacy_address_domain`, which is now checkable rather than assumed.
- `SporeStore` keys and receipts use the qualified address. A receipt carrying a
  bare legacy digest is **refused by profile**, not reinterpreted.

## What remains unverifiable, and in what sense

An earlier version of this file said "there is no migration that could rescue"
a legacy receipt. That was broader than anything measured. Three different
statements were being run together, and they are not the same:

1. **Policy refusal.** `SporeStore.audit` rejects every bare-digest receipt
   today. That is a decision made here, not a fact about the receipt.
2. **Ambiguity over unrestricted ASTs.** A bare digest does not identify one
   term *when the term could be any AST*, because two terms can share it.
3. **Impossibility of any historical verification.** Not established. A legacy
   receipt whose term is known to be inside an explicitly specified old domain
   could be replayed there with its original meaning. That would be a separate,
   independently specified legacy verifier, and it would not make such a
   receipt valid under `glyph.term.v2`.

So: legacy receipts are refused here, by policy, and no legacy-to-v2 conversion
exists. Whether a restricted legacy verifier is worth building is open.

Nothing on disk is affected, because `SporeStore` has no persistence — checked,
not assumed. Signed artifacts are untouched.

## S3d-2: what moved, and what deliberately did not

| Site | Decision |
|---|---|
| `goedel` cycle history | **migrated** to `term_address`. An internal key, never persisted or signed; two terms sharing a legacy address would have read as a repeat, i.e. a limit cycle that did not happen |
| `epistemic_swarm` gene/tombstone lookup | **migrated**. Measured while doing it: every production caller of `retire()` keys a tombstone by a rule name, a claim id or a gene id, so this lookup cannot match a term address under either profile. The ambiguous address is gone from a comparison that appears already ineffective; no live check is claimed to be repaired |
| `metamorphosis.fixtures_fingerprint` | **kept legacy**. It is embedded in signed mycelium warrants through `autopoiesis`, and persistent signed operands stay unchanged |
| `warrant_kernel.GroundedWitness.expected_hash` | **kept legacy**, by decision: inside signed claims, input is parsed text |

`in_legacy_address_domain` specifies a **sufficient restricted domain**, not
uniqueness against arbitrary ASTs. It excludes `$`, space, `(` and `)` from
leaves and admits Unicode and punctuation outside that set. The parenthesis
exclusion is conservative; its independent necessity was not demonstrated.

A term passing this predicate can still collide with a term outside the domain:
`Var("a")` and the excluded `Comb("$a")` share legacy bytes. A legacy consumer
must establish the domain of both stored and queried operands; validating only
the new query does not make an unrestricted historical store unambiguous.

`parse("$")` gives `Var("$")`, which this sufficient check excludes. Its
unrestricted-AST collision partner is `Comb("$$")`, also excluded. This is not a
collision between parser-produced terms, and does not justify rejecting all
parser outputs containing a standalone `$`.
