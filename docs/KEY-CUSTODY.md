# Key custody: public export, private recovery

Written for S5a, 2026-09-11.

## The split

A **public export** is anything made to be shared: an organism, colony or
swarm PDF, a colony or swarm JSON state, a metamorphic or autopoietic document,
a vault. It carries public keys and signatures. It never carries a secret key.

**Private recovery** is what continuing one of those needs: the secret key of
whoever signs next. It lives only in its own file, created with mode 0600:

| export | private key source for continuing it |
|---|---|
| organism PDF (`PolyglotOrganismCompiler.compile`) | `<file>.pdf.key`, `--secret-key HEX`, or `BLACK_HEART_SECRET_KEY` |
| autopoiesis and morpho-autopoiesis PDFs | `<file>.pdf.key` (already so before S5a) |
| colony state (`cli.py colony`) | `--keys PATH`, else `<state>.keys` |
| swarm state (`cli.py swarm`) | `--keys PATH`, else `<state>.keys` |

`<state>.keys` is a keystore (`keystore.py`, profile
`black-heart.keystore.v1`): secret keys indexed by the public key each derives,
loaded strictly, so an entry holding another key's secret is refused.

## What does not need a private key

Verifying anything. A loaded organism, colony or swarm has no secret key and
still verifies: genome hashes, public keys, ledger and tombstone signatures, and
the embedded runners' `--status` and `--audit`.

## What is refused

- **Continuing without a key source.** `colony step`, `swarm step`, `mate` and
  `inoculate`, and an organism's `--reproduce`, stop with a named refusal before
  anything is written. Two silent fallbacks are gone: organisms signing with
  the all-zero key, and the colony ledger signing with a freshly generated key
  unrelated to the colony.
- **A key that does not belong.** `--reproduce` checks that the key derives the
  organism's public key.
- **Packing secrets into a vault.** `vault.pack_files_to_vault`, and so
  `cli.py vault pack` and `symbiosis`, refuse any member that looks like private
  key material, naming it: a `.key` or `.keys` file, a keystore, a named secret
  field, or a secret next to the public key it derives. A vault is a public
  reproducibility archive, not a secret store.

## Historical artifacts

They are not rewritten.

- `examples/organism_gen0.pdf` embeds a real secret key next to its public key.
  It has been public in this repository, so **that key is burned**: treat it as
  known to everyone. The loader no longer reads a secret from any document, so
  the key is not used to sign anything, and `document_carries_secret_key`
  reports the exposure.
- Colony and swarm states written before S5a embed their secrets too. Those keys
  are exposed wherever the files went. Loading such a state reads only public
  keys; continuing it needs a keystore the operator creates on purpose, for
  example with `Keystore.from_legacy_secrets`, knowing the keys are exposed.
- `examples/metamorphic_organism.pdf` and `examples/resumable_computation.pdf`
  mention `secret_key_hex` only in their runner code and hold no key.

## What this does not decide

Where a keystore lives beyond the file next to the state, who may hold it, or
how keys rotate or are revoked. Nothing here re-secures a key already published.
