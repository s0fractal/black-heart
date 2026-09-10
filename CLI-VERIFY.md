# Host-side verification repair

`python3 cli.py verify artifact.pdf` reads metadata and invokes repository
library checks. It does not execute the PDF's embedded Python or import from
an embedded `source_dir`. The runtime and this checkout remain trusted inputs.
This change is independent of WRT-012; it adds no witness or adoption authority.

Repaired routes and their scope:

| Route | Checked |
| --- | --- |
| Claim PDF | Named claim fields emitted by the compiler; bounded combinator results |
| Contract | Existing dual-spine/hash auditor, using the current EvalResult API |
| Continuum | Checkpoint hashes/signatures, signer continuity, links and bounded computation replay |
| ZK | Supplied Schnorr and Chaum-Pedersen proof equations; empty proof lists refuse |
| Ledger | Height/link/hash/signature checks, chain tip/count and combinator claims |
| Metamorphosis | Reconstructed organism hashes and existing transition replay; embedded source_dir ignored |
| Colony | Declared epoch links only; no recomputation of epoch hashes, no signature claim |

Keys declared inside artifacts do not establish externally trusted identities.
An empty colony history does not obtain a vacuous link-check success. A vault
marker without executable claims no longer passes the claim auditor. Unsupported
or malformed metadata refuses with exit 1 rather than leaking an import traceback.
Existing routes for other engines remain; this is not a new audit of every engine.
Input files are limited to 16 MiB by CLI dispatch; there is no process isolation
or general hostile-concurrent-filesystem guarantee. Parsing and library evaluation
have their existing runtime bounds; this is not a universal resource sandbox.

CEGIS constructor syntax is interpreted through a bounded, closed AST grammar
(App, Comb, Var, K/I/S/Y); supplied Python expressions are never evaluated.
Existing glyph syntax remains supported. Constructor depth, size, argument names
and string lengths are bounded.

Validation: `python3 -B -m unittest test_cli_verify -v` compiles fresh artifacts
for all seven repaired routes and checks both positive and altered-artifact cases.
It also tests malformed metadata, embedded runner text and a Python-injection
payload with an observable file-writing side effect that must not occur. The
unified suite includes these 11 tests. Local result on this branch: 368/368.
