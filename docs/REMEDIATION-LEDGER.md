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
| §3 REPL tuple-unpacks `EvalResult` | `cli.py` REPL | driven as a process: every expression printed `cannot unpack non-iterable EvalResult object` | **BEHAVIOR_FIXED** (S2b) | — |
| §2 Church numerals collapse | `glyph.church_numeral` | probe: n=0..5 all reduced to `x`; the builder applied the SKI successor to `I` | **BEHAVIOR_FIXED** (S2a) | — |
| §4 retirement body/id/signature unbound | `controlled_forgetting.py` `verify_signature`, `from_dict`; use sites in `epistemic_immune.HorizontalInoculation.inoculate`, `epistemic_swarm.SwarmInoculationCascade.broadcast_tombstone`, `EpistemicTombstoneRegistry.from_dict`/`is_admitted` | probe: changed `mode`+`atp_gas_recovered` under the same id → `changed_id_matches_body: false`, `changed_signature_valid: true` | **OPEN — this package** | **S1** |
| Embedded polyglot runner cannot evaluate a claim | `polyglot.py` runner template | generated document: `'tuple' object has no attribute 'term'`, every claim reported failed. Introduced by `579150f` applying the host-side fix to a template whose own engine returns a tuple | **BEHAVIOR_FIXED** (S2b) — the API mismatch only; the runner's separate engine and its trust story stay open | S7/S8 |
| §6 UNSAT certificate is a DAG shape check | `smt_kernel` | probe: a certificate for the satisfiable formula `{p}` accepted; invented axioms accepted | **BEHAVIOR_FIXED** for the checker and the credit gate (`check_resolution_refutation`, Grade A elevation); **CLAIM_NARROWED** for the old name, now `check_proof_dag_structure` | S3a |
| Formal credit taken from an unbound proof | `dialectic_kernel` producer and `elevate_triad_to_warrant` | shape, then a set flag, then a receipt whose subject label the same caller could retarget with `dataclasses.replace`; and a subject digest that omitted the guard and the delta | **BEHAVIOR_FIXED**: Grade A needs a `FormalCreditBinding` supplied by the caller and never rebuilt from the report, plus a v2 subject digest covering every operand the credit spends | S3a |
| Whether the CNF encodes the theorem, and whether the caller may say so | the `FormalCreditBinding` boundary | not a defect: an assertion that is now attributable and refusable instead of implicit | **OPEN by design** — named at the boundary, decided outside this module | — |
| CDCL emits proof objects that are not resolution derivations | `smt_kernel.CDCLSolver.add_clause` call sites; `pivot_vars` never populated | learned nodes carry one antecedent and no pivot, so the step checker refuses them | **OPEN** — named, not fixed | S3a-2 |
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
