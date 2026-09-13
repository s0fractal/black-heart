# CM-4 — local experience skill

**ACTIVE / READY FOR REVIEW.** CM-3 is accepted. This slice chooses
[a skill](../../../.agents/skills/black-heart-experience/SKILL.md) over the existing
CM-2 CLI: the accepted receiver used shell/file tools successfully, and no new
server or transport is required for local save, search and inspection.

The skill maps natural requests to existing operations, keeps source/basis
visible and distinguishes byte verification, replay and advice acceptance.
It requires partial search errors to remain visible and preserves duplicate
records rather than deleting them to make retries succeed. New experience uses
the existing profile; no stake field or automatic advice adoption is added.

The repository skill is the reviewable source. An operator can load that file
explicitly. Any local installation is a separate convenience; this PR does not
establish automatic discovery across agents or change global agent settings.

## Observed interaction

The owner authorized CM-4 and then selected the actual question:
**«Що вже пробували щодо EMPIRICAL і SUSPENDED?»**

The current Codex operator loaded the skill, imported the three repository
examples into a disclosed temporary local store, searched/read them and ran the
saved-exchange verifier. [interaction.json](interaction.json) records that exact
question, commands, raw stdout/stderr, actual checkout state and skill digest.
The report covers the **second local execution**. An earlier execution wrote
`interaction.json` and `saved-check.json`; its report did not capture the intended
before boundary. After correcting the harness, the compiler ran the scenario
again in a new store. Therefore `checkout_before` correctly contains those
pre-existing untracked outputs: it was measured before the first event of the
recorded second execution, not before the initial attempt or the user request.
`recording_chronology` is an explicit post-review operator disclosure. The first
report was replaced before commit and is not separately archived. No timestamps
or complete first-run transcript are reconstructed. Source identity remains
pinned to `da3bb9c` and the full commit recorded in the report.

[answer.md](answer.md) preserves the source-qualified answer;
[experience.json](experience.json) is a new record with seven evidence sources
and a `refines` link to the unchanged receiver response. The answer distinguishes
historical reported measurements from this session's artifact verification and
carries forward both receiver-response qualifications.

[save-check.json](save-check.json) records fresh B1 validation of the amended record:
save → byte-identical read →
search (four records), unchanged predecessors, and `OUTPUT_EXISTS` on retry.
New record address:
`98ad0495024f781f7485e55c8789bbbd157bdb20900ea103f90d27d227839e0d`.
[saved-check.json](saved-check.json) is the offline CM-3 verifier result: no
provider call and no evaluator replay. No OAuth proxy was used.

This is a real user-selected query and current-agent tool path. It is not a
fresh-session, blind, independent or causal evaluation of the skill. The
operator already knew CM-3. Only the retrieval/answer route and subsequent
record retention were exercised; the skill's broader replay route is not
claimed behaviorally validated. The corpus is three imported examples, not
all prior user memory. Temporary store paths in reports are historical and may
expire; committed raw records remain available for reimport.

## Reproduce the data operations

Choose a fresh external store and use the existing CM-2 CLI to save, in order:

1. `examples/model-experience/doc-f1/experience.json`
2. `examples/model-experience/cm3/control.json`
3. `examples/model-experience/cm3/exchange/response.json`
4. `examples/model-experience/cm4/experience.json`

Supply this full local repository as `--repo`. Search with `--component EMPIRICAL`,
and read the fourth address with `--raw` to compare its original bytes. This
reproduces storage/lookup correspondence, not the model's natural-language
interpretation. The [CM-2 commands](../cm2/README.md) and skill specify the CLI.
Keep `da3bb9c` reachable when merging: evidence and the relation target name
that exact source commit. Use a normal merge rather than squash/rebase.

Validation performed: skill-creator's structural validator passed; all 13
`test_experience` tests passed; the actual interaction and roundtrip above
succeeded. No production Python or test runner changes are included. Frozen
CM-3 files and historical records remain unchanged.

## B1 amendment and remaining coverage

The amended interaction digest and experience address replace the pre-review
ones; the old bytes remain in commit `c4a18d2`. Original command outputs and
skill bytes are unchanged. Observation 1 explicitly limits `basis: replayed` to
measured CLI data operations, while evaluator evidence replay remains false.
Authentication is known to be absent and is now stated as unsigned.

Observed agent support is **Codex in this task, with explicit loading of the
repository skill**. Claude Code automatic discovery and execution have not been
configured or tested. No cross-agent automatic-discovery claim is made.

CM-4 remains partial / ACTIVE. The owner-selected retrieval request was tested;
a separate natural-language “save this experience” route and the advice-replay
route still need behavioral trials before claiming full coverage. Record
retention after retrieval is not a substitute for testing the standalone save
request. Component filtering retrieved the full example corpus; task-summary
wording such as “suspended” versus “unsettled” can miss relevant records, so
partial textual matches should be broadened rather than treated as exhaustive.
