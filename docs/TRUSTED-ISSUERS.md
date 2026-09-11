# Trusted issuers for scoped refutation

Consequence table fixed before implementation. This file was committed on its
own, ahead of the code that implements it; `git log` on this path shows the
order.

## Question

`ResurrectionDefense.refuted_for` authenticates each registry record for its
slot: subject, body domain and signature. It does not ask who signed. Any key
that signs a well-formed record is honoured, so the only thing standing between
a stranger and a prohibition is that the stranger has a key. And a stranger's
signed readoption lifts a refutation exactly as well as its author's would.

This package lets a caller say which keys may issue retirements and which may
issue readoptions, and fixes, before any code, what each combination does.

## Terms

- **Authentic**: the record is admissible for its slot (subject, domain,
  signature). Unchanged from today, and still checked first.
- **Trusted issuer**: the record's `author_pk_hex` is in the caller's list for
  that kind of record. A signature binds a record to a key. The list is what
  gives that key authority. Neither stands in for the other.
- **Foreign**: authentic, but signed by a key the caller did not list.

## Consequences

"Pair" means the candidate offered in place of this reference. The policy is
the caller's `RefutationAdmissionPolicy`; "default" is its default, which
proceeds only on `NO_MEASURED_REFUTATION`.

| # | registry holds, for the pair | issuer policy | scope reported | prohibits | default outcome | can the caller opt in to proceed |
|---|---|---|---|---|---|---|
| C1 | a retirement | none given | `REFUTED_FOR_REFERENCE` | yes | refuse | no |
| C2 | a retirement by a trusted key | given | `REFUTED_FOR_REFERENCE` | yes | refuse | no |
| C3 | the same retirement by a foreign key | given | `UNAUTHORIZED_ISSUER` | no | refuse, as uncertainty | yes |
| C4 | a trusted retirement and a trusted readoption of it | given | `NO_MEASURED_REFUTATION` | no | proceed | — |
| C5 | a trusted retirement and a foreign readoption of it | given | `REFUTED_FOR_REFERENCE` | yes | refuse | no |
| C6 | a trusted retirement and a foreign retirement | given | `REFUTED_FOR_REFERENCE` | yes | refuse | no |
| C7 | a record signed by one key claiming another's `author_pk_hex` | given or not | `UNTRUSTED_EVIDENCE` | no | refuse, as uncertainty | yes, API only |
| C8 | nothing | given | `NO_MEASURED_REFUTATION` | no | proceed | — |

C1 is today's behaviour, kept exactly. Without an issuer policy every authentic
author counts as trusted.

C2 against C3 is the point of the package: the same signed assertion has two
different, predefined consequences depending only on who signed it.

C5 is the attack this closes. A stranger's readoption cannot lift a trusted
refutation. The foreign readoption is reported, not silently dropped.

C7 is not an issuer question at all. A record whose signature does not verify
under the key it names fails authentication before the issuer list is
consulted, so no one can borrow a trusted key's name.

## Precedence

When several records concern the pair, the report is the first that applies:

1. a trusted, authentic retirement, not lifted by a trusted readoption:
   `REFUTED_FOR_REFERENCE`;
2. any record that cannot be authenticated: `UNTRUSTED_EVIDENCE`;
3. an authentic retirement of the pair by a foreign key: `UNAUTHORIZED_ISSUER`;
4. a trusted refutation of the candidate against another reference:
   `REFUTED_FOR_ANOTHER_REFERENCE`;
5. otherwise `NO_MEASURED_REFUTATION`.

In every case, including when rule 1 decides, the report names the foreign
retirements of the pair and the foreign readoptions it ignored. A foreign
retirement of the candidate against some other reference is not evidence of
anything here and is not reported as `REFUTED_FOR_ANOTHER_REFERENCE`.

## A trade-off for the reviewer to decide

C3 defaults to refuse. That keeps the rule already in force, "not proven
prohibited is not permitted", and the operator can pass
`--also-proceed-on UNAUTHORIZED_ISSUER`. The cost is real: with the default, any
key holder can halt evolution of a pair by signing a refutation of it. The
other choice, defaulting C3 to proceed, removes that lever but lets a foreign
assertion be silently outvoted by the absence of a trusted one. I chose
refusal because it is reversible by an explicit flag and the other is not
visible at all. The choice is stated here so it can be reversed on purpose.

## What this does not decide

- Where the list of trusted keys comes from, or who maintains it. The caller
  supplies it.
- Key rotation, revocation or expiry.
- Whether a trusted issuer was right.
- Anything about the embedded runner, which passes no registry.
