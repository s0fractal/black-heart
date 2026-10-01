# Working in Black-Heart

These instructions apply to the entire repository, including documentation,
essays, examples, generated artifacts and experiment records.

## Start with the task

Use [the task routes](ADDRESS-INDEX.md#почати-з-задачі) to select the first code,
regression tests and contract to read. Do not load every floor document for a
local repair; follow actual dependencies and relevant remediation entries.
The routes are starting points, not limits on review or required validation.
Keep experiment status in its owning plan/result rather than copying it into
navigation. Preserve distinctions between current-code tests and historical replay.

## All changes go through a pull request

- Never commit directly on, or push directly to, `main` or `master`.
  “Only documentation”, a conversation transcript, a typo or a solo-author change
  is not an exception.
- Before editing, inspect the branch, working-tree status and relevant repository
  instructions. Treat the main checkout as a read-only integration checkout;
  update it only by fast-forwarding to the remote integration branch.
- Use a dedicated topic branch and preferably a separate Git worktree based on
  the current `origin/main` (or the repository's actual default branch).
- Keep one bounded task per branch and PR. Do not mix unrelated repairs or
  experiments into an existing PR. Independent tasks may use separate worktrees.
- Commit and push the topic branch, then open or update its PR. Explain the
  resulting behavior, validation and remaining limits.
- If edits already exist in the main checkout, preserve them and establish their
  ownership. Move your own changes to a topic branch before committing; never
  discard another operator's work to make the checkout clean.

## Review and merge

- Before merging, verify the current PR head, applicable review, required checks
  and relevant local validation. Report pending or failed checks honestly.
- Merge only within the owner's authorization. Use the exact inspected head:
  `gh pr merge NUMBER --merge --match-head-commit FULL_HEAD_SHA`.
- Preserve ordinary merge history when artifacts reference commits. Do not
  squash or rebase away an evidence, input-freeze or reviewed source commit.
- Never use an admin bypass, force-push an integration branch, disable protection
  or loosen a rule merely to get a change through. Repository policy changes
  require an explicit owner request and a clear account of the change.
- A green CI run is not an independent review. A review acceptance is not proof
  that a merge, experiment or publication occurred; verify and report those
  actions separately.

## Experiments and documentation

- Read the existing corrections in related documents and inspect implementation
  before repeating technical claims. Distinguish metaphor, proposal, implemented
  behavior and measured evidence.
- Follow the experiment's accepted plan and review gates. Plan acceptance alone
  does not authorize bypassing a separate execution-package review.
- Preserve frozen inputs, historical signed bytes and raw observations. Record
  corrections or failed attempts with provenance instead of rewriting history.

## Finish the cycle

- Verify the merged commit and ancestry, then fast-forward a clean main checkout.
- Remove a completed task's worktree and branch only after confirming it has no
  uncommitted or untracked work and its commits are reachable from the remote
  integration branch. Never force-delete a dirty or unmerged worktree.

GitHub enforces the PR requirement for `main` and `master` through the active
`Integration branches require PRs` ruleset, with no configured bypass actors.
A second person's approving review is not required by that server rule; any
additional review requirements of the current task still apply. These written
instructions also cover local commits, which GitHub cannot prevent.

## Small repository hygiene checks

After staging new files, run `python3 tools/absolute_path_check.py --selftest`
and `python3 tools/absolute_path_check.py --base origin/main`. PR CI checks added
line occurrences in tracked UTF-8 text against its exact base commit. Historical
paths in retained records remain unchanged and are not newly certified; binary
files are outside scope. A new exception requires an exact per-file substring
and reason in `tools/path_allowlist.json`. Missing/unreadable inputs refuse the check.

CI also runs pinned lychee 0.24.2 offline on changed Markdown files. Use
`lychee --offline path/to/changed.md` locally. External URLs and unchanged
documents are outside this check. These checks cover paths and local links only;
existing tests and packet verifiers retain responsibility for their own invariants
and digests. No check establishes document truth or author identity.

## Python static analysis

Run `uvx ruff==0.16.7 check .` (or install `ruff==0.16.7` and run
`ruff check .`) before submitting Python changes. `ruff.toml` selects a narrow
correctness set: syntax errors, undefined names/exports/locals, tuple assertions
and conditions, and literal identity comparisons. CI runs the same pinned version.
Do not run automatic fixes or formatting over historical evidence. Static checks
do not inspect Python embedded in string templates or PDFs, execute code, prove
settlement, or replace regression tests. No type checker is enabled by this setup.

## Retired context

The triad ecosystem, TRIAD-1 proposal and retired integration sketch are excluded from default context. Follow `history/TRIAD-RETIREMENT.md`; historical access carries ARCHIVED status and cannot resume plans or re-adopt them. All triad references in frozen experiment records are historical provenance only, with no active import or continuation obligation. This also applies to copies retrieved from old Git revisions.
