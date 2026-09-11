# Key custody: public export, private recovery

Written for S5a, 2026-09-11. The single-document sidecar's extension was
renamed from `.key` to 🔑 afterward; nothing else in this file changed.

## The split

A **public export** is anything made to be shared: an organism, colony or
swarm PDF, a colony or swarm JSON state, a metamorphic or autopoietic document,
a vault. It carries public keys and signatures. It never carries a secret key.

**Private recovery** is what continuing one of those needs: the secret key of
whoever signs next. It lives only in its own file, written by
`keystore.write_private_file`. That function:

- creates an exclusive temporary file, mode 0600, under an unpredictable name in the same directory;
- writes it through that file's own descriptor;
- atomically replaces the target, and only if the target is a regular file.

A link or anything else at the path is refused and left untouched. The files:

| export | private key source for continuing it |
|---|---|
| organism PDF (`PolyglotOrganismCompiler.compile`) | `<file>.pdf🔑`, `--secret-key HEX`, or `BLACK_HEART_SECRET_KEY` |
| autopoiesis and morpho-autopoiesis PDFs | `<file>.pdf🔑` (already so before S5a) |
| colony state (`cli.py colony`) | `--keys PATH`, else `<state>.keys` |
| swarm state (`cli.py swarm`) | `--keys PATH`, else `<state>.keys` |

The single-document sidecar's suffix is `keystore.PRIVATE_KEY_SUFFIX`, 🔑
(U+1F511) — before this it was `.key`. `secret_material_reasons` (the vault
detector, below) still recognizes a plain `.key` file too, so a sidecar
written by a checkout from before this rename is still refused when packing a
vault; nothing in this repository writes `.key` going forward. This is
unrelated to `.keys` (no rename): that suffix names a *keystore*, a JSON
registry of several keys indexed by the public key each derives, used by
colony and swarm states — conceptually a different thing from one document's
own single key.

`<state>.keys` is a keystore (`keystore.py`, profile
`black-heart.keystore.v1`): secret keys indexed by the public key each derives,
loaded strictly, so an entry holding another key's secret is refused.

## Migrating a sidecar written before the 🔑 rename

The rename is a deliberate, one-directional compatibility break. It is a
**read** break — not key loss, and not a signature migration. Nothing about a
key's bytes, a document's bytes, or any signature changes.

- `keystore.secret_material_reasons` still recognizes a legacy `.key` file, so
  a vault still refuses to pack one.
- **No reader discovers `.key` any more.** `autopoiesis` and
  `morpho_autopoiesis` resolve a key from an explicit argument, then
  `<file>🔑`, then `BLACK_HEART_SECRET_KEY`. With only a `.key` beside the
  document, both refuse by name and leave the document byte-identical.

There is no automatic fallback, on purpose: reading either name would make
"which key signed this" depend on which of two files happened to exist, and a
stale `.key` left beside a current 🔑 would be an ambiguity resolved silently.

To migrate, rename the sidecar. Do not regenerate a key, and do not rewrite the
signed document:

```bash
mv -n -- "organism.pdf.key" "organism.pdf🔑"
```

`mv` preserves the mode, so 0600 carries over — confirm with `ls -l`. `-n`
refuses rather than overwriting: if the destination already exists, both files
are left alone. Resolve that by hand, because the two may hold different keys;
the public key a secret derives is the only safe way to tell which document a
stray sidecar belongs to. Never overwrite one sidecar with another to make a
rename succeed.

**Already-generated standalone runners keep the old convention.** An organism
PDF carries its own embedded runner, and that runner's key lookup is fixed at
the moment the document was compiled; changing host code does not rewrite
bytes that were already emitted. Measured: a document compiled from `413f1ce`,
the commit before this rename, embeds `target_path + ".key"` and no `🔑` at
all. Such a document keeps working with its original `.key` sidecar;
recompiling it from current code produces a runner that looks for `🔑`. Each
is self-consistent — do not rename the sidecar next to an old runner and then
expect that runner to find it.

Documents older than S5a embed an earlier runner that resolves no sidecar at
all: `examples/organism_gen0.pdf` contains neither name. This rename does not
affect them in either direction.

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
  key material, naming it: a `🔑`, legacy `.key`, or `.keys` file, a keystore, a
  named secret field, a secret next to the public key it derives, or more
  distinct 64-hex strings than the pair scan checks (512), because a file that
  was not scanned cannot be cleared. Each member is read once, and those exact
  bytes are both checked and archived. A vault is a public reproducibility
  archive, not a secret store. The detector covers these declared patterns. It
  is not a guarantee against every encoding of a secret.
- **Writing a key through a planted link.** A link at a keystore or `🔑`
  path is refused, and whatever it points to is left unchanged.

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

Two files are not one transaction. The organism, autopoiesis and
morpho-autopoiesis writers write the key before the document, so a refused key
path leaves an existing document unchanged and creates no new one. If writing
the document fails after the key was written, nothing rolls back.
