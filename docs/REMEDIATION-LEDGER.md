# Remediation ledger — S0

Base: `origin/main` = `1d1908f`. Probe rerun here: `python3 -B ../black-heart-remediation-2026-09-11/baseline_probe.py .`
reproduces Codex's three observations at this HEAD (they were first recorded at `ce05d3e`).

The source review (`BLACK-HEART-STUDY-2026-09-10.md`) describes HEAD `1bf7ad3` and is historical.
This table says what is true **now**, per finding. It is a navigation aid, not an audit: a row marked
OPEN means "reproduced or read in the current source", and a row marked CLOSED names the change that
closed it. Nothing here is a claim about findings that were never re-probed.

| Study finding | Current source / use site | Repro at `1d1908f` | Disposition | Package |
|---|---|---|---|---|
| §3 `cli.py verify` broken on seven routes | `cli.py` verify dispatch | `test_cli_verify.py` 11/11 incl. corrupted artifacts | **ALREADY_FIXED** (PR #1, `816d36b`) | — |
| §5 `cegis_kernel.parse_term` `eval()` RCE | `cegis_kernel.py` bounded AST parser | injection case inside the same 11/11 | **ALREADY_FIXED** (PR #1) | — |
| §3 REPL tuple-unpacks `EvalResult` | `cli.py:81` `norm, atp, digest = evaluate(...)` | read in source; REPL not driven this pass | **OPEN** | S2b |
| §2 Church numerals collapse | `glyph.church_numeral` | probe: n=0..3 all reduce to `x` | **OPEN** | S2a |
| §4 retirement body/id/signature unbound | `controlled_forgetting.py` `verify_signature`, `from_dict`; use sites in `epistemic_immune.HorizontalInoculation.inoculate`, `epistemic_swarm.SwarmInoculationCascade.broadcast_tombstone`, `EpistemicTombstoneRegistry.from_dict`/`is_admitted` | probe: changed `mode`+`atp_gas_recovered` under the same id → `changed_id_matches_body: false`, `changed_signature_valid: true` | **OPEN — this package** | **S1** |
| §6 UNSAT certificate is a DAG shape check | `smt_kernel.verify_unsat_certificate` | probe: `{1:[1,2] input; 2:[] learned←[1]}` accepted | **OPEN** | S3a |
| §6 CEGIS SMT query independent of operands | `cegis_kernel.py:449-450` both sides equated to one `eval x` | read in source; not re-probed behaviourally | **OPEN** | S3b |
| §6 `smt_refute_tombstone` quarantines anything | `smt_kernel.py` | not re-probed this pass | **OPEN** | S3c |
| §6 sheaf dead branch | `sheaf_kernel.py:377` compares `status.value == "NORMAL_FORM"` (never produced) inside `except: pass` | read in source; behavioural probe deferred | **OPEN** | S4a |
| §6 warrant COUNTEREXAMPLE passes on exception | `warrant_kernel.py` | not re-probed this pass | **OPEN** | S4b |
| §6 `mycelium.verify_rewrite_rule` returns True for `MUTATION_*` | `mycelium.py:88-89` | read in source | **OPEN** | S4c |
| §6 e-graph fabricates an explanation step | `egraph_kernel.py` | not re-probed this pass | **OPEN** | S4d |
| §4 secret keys inside public artifacts | `organism.py:347` writes `secret_key_hex` into the manifest; colony/swarm exports not re-scanned | read in source; full export scan not done | **OPEN** | S5a |
| §4 self-pinned adjudication trust | `cross_proof.py`, `cli.py adjudicate` | not re-probed this pass | **OPEN** | S5b |
| §6/§7 receipts, votes, runners, PDF byte history, math names | many | not re-probed this pass | **OPEN, unscoped here** | S6–S8 |
| §0 README counts (200 tests / 22 engines) | `README.md` | not touched by design | **DEFERRED** | S9 |

Two notes kept deliberately:

- PR #2 added an **opt-in local verification cache** (`tools/VERIFY-CACHE.md`). It is a local
  performance store, not an attestation, and it does not replace a fresh check of a release.
- The local development checkout also carries unpublished continuation experiments. They are not
  part of this remediation line and are not carried into remediation PRs.
