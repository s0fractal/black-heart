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

## What remains unverifiable

Any `SporeReceipt` created before this change carries bare digests. It cannot be
verified under the new profile and must be re-derived from its term. There is no
migration that could rescue it: the digest it holds does not identify one term.

Nothing on disk is affected, because `SporeStore` has no persistence — checked,
not assumed. Signed artifacts are untouched.
