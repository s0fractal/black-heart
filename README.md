# Black-Heart

Black-Heart is an experimental Python repository for storing engineering experience
with identifiable source bytes and repeatable checks. The intended user is a model
or developer continuing another session's work without copying its entire chat.

The repository implements local record storage, source-digest checks and bounded
computation. Whether these packages help a receiver more than a plain-text log is
still an open question. It also contains exploratory code and essays; their names
and metaphors are not evidence of biological, social or physical properties.

## Start with one real record

[DOC-F1](examples/model-experience/doc-f1/README.md) records a bug in an empirical
verifier: unfinished computations could be compared as if they were results. The
packet contains observations, advice, limitations, source revisions and a saved
regression report. It can be read without the original chat.

For this example, use Git and Python 3.11 or later on Linux or macOS. Use a full
clone: saving the packet requires the historical Git objects it names. These
commands use the Python standard library and make no model or API calls.

```sh
git clone https://github.com/s0fractal/black-heart.git
cd black-heart
store="$(mktemp -d)"
python3 experience.py save examples/model-experience/doc-f1/experience.json --repo . --store "$store"
python3 experience.py search --component EMPIRICAL --store "$store"
```

`save` returns a content address and retains the record with its source bytes;
`search` returns matching records and reports corrupt entries. The temporary store
is yours to retain or remove. See the [CLI contract](examples/model-experience/cm2/README.md)
for reading, verification, refusal codes and storage limits.

**This checks byte correspondence, not the truth of the observations or the advice.**
The CLI does not execute commands found inside records, authenticate a model's
identity, or replay the cited experiment. To repeat the recorded test, follow the
[packet's instructions](examples/model-experience/doc-f1/README.md) at its pinned
revision. Testing today's code is a separate operation:

```sh
python3 -m unittest test_empirical_settlement test_experience
```

## What the evidence currently supports

| Item | Demonstrated scope | Limit |
|---|---|---|
| [Local experience storage](examples/model-experience/cm2/README.md) | Save, read, search and check retained bytes; store disagreements separately | No automatic advice acceptance or authenticated model identity |
| [CM-3 exchange](examples/model-experience/cm3/README.md) | One fresh Claude session ran a sender-designed differential and rejected synthetic advice | One session; the receiver did not design the check; response defects are documented |
| [TRANSFER-1](experiments/transfer-1/results/pilot-1/README.md) | The first session in each of three conditions succeeded; the early-stop rule ended the pilot | No advantage of the evidence packet was demonstrated |
| [Executable PDF case study](papers/runs-its-own-checks/paper.md) ([DOI 10.5281/zenodo.22754264](https://doi.org/10.5281/zenodo.22754264)) | A companion and mutation controls show what its checkers accept or miss | Recognized claims, visible text, authorship and document integrity are different properties |

The [experience contract and research queue](xC010-model-experience.md) hold the
more detailed status and evidence boundaries. The [remediation ledger](docs/REMEDIATION-LEDGER.md)
records defects and repairs. Passing tests establish their named checks, not the
correctness of Black-Heart as a whole.

## Execution and trust boundaries

An executable PDF is Python code supplied by its author. Running it grants that
code the user's permissions. Python's `-I` isolates imports; it is not a filesystem
or network sandbox. A runner shipped inside a document is itself a trust dependency.

The repository's [static auditor](tools/sandbox.py) inspects supported elements
without executing the document's embedded Python. Its result covers recognized
elements only. The [case study](papers/runs-its-own-checks/paper.md) demonstrates
that the static auditor and embedded runner can recognize different claim sets,
and that runner exit 0 can mean no claims were checked. Neither is a general
certificate that a document is safe, authentic or true.

## Code and further reading

- [Address index](ADDRESS-INDEX.md): contracts, implementation pointers and limits.
- [Bounded reduction](x1000-reduction.md): SKIY evaluator and settlement conditions.
- [Evidence](x6000-evidence.md): supported witness types and verification boundaries.
- [Library transitions](docs/LIVING-LIBRARY-INTERACTION.md): proposals, caller-policy
  evaluation and immutable successors within the implemented local workflow.
- [Contributing rules](AGENTS.md): work on a branch, review through a PR, preserve
  historical artifacts and their provenance.

The repository was developed with language-model assistance. Model reviews and
in-repository regressions do not constitute independent human validation.
The [earlier README](https://github.com/s0fractal/black-heart/blob/35af27b/README.md)
is retained in Git history; its broad capability descriptions are not the current
statement of demonstrated results.

The next useful evidence would be an external reader completing a concrete task
from one packet without the author's guidance, with obstacles and outcomes recorded.
That would test usability; demonstrating an advantage over plain text would still
require a separate controlled comparison. New experiments require their own plan
and review before execution.

Licenses: code is AGPL-3.0-only; documentation is CC BY-SA 4.0. See
[LICENSE](LICENSE) and any artifact-specific notices.
