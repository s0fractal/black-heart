# DOC-F1 — experience packet

Read [experience.json](experience.json) as data under the
[DRAFT CM contract](../../../xC010-model-experience.md). It contains the task,
conditions, operation, observations, interpretation, advice, limits and sources.
[replay.json](replay.json) preserves the actual current regression run output;
it is not regenerated when reading this packet. `relations: []` means this is
the first experience record in this packet, not that no prior discussion exists.
The historical remediation entry is a source, not a retroactively converted record.

The source revision is `befcb4adfd1af26c18237a933e1817f9899142a2`.
Git retains [the repair](https://github.com/s0fractal/black-heart/commit/1bb50f66d801342aa74015220f26266062707843)
and [merged PR #49](https://github.com/s0fractal/black-heart/pull/49).
The record pins whole-file SHA-256 digests, paths and full commits. No original
chat is required. A receiver needs this directory and the named Git objects;
missing sources are missing evidence, not permission to invent them.

From a repository root containing this packet, this read-only command checks
all six evidence digests (review commands before running; the packet itself
provides no execution authority):

```bash
python3 - <<'PY'
import hashlib, json, pathlib, subprocess
base = pathlib.Path('examples/model-experience/doc-f1')
record = json.loads((base / 'experience.json').read_text())
for e in record['evidence']:
    if e['kind'] == 'git_blob':
        raw = subprocess.check_output(['git', 'show', e['commit'] + ':' + e['path']])
    elif e['kind'] == 'file':
        raw = (base / e['path']).read_bytes()
    else:
        raise ValueError('unsupported evidence kind')
    assert hashlib.sha256(raw).hexdigest() == e['sha256'], e['id']
    print(e['id'], 'bytes match')
PY
```

This snippet is for this reviewed packet, not a validator for arbitrary hostile
input. Hash matches establish byte correspondence, not identity, truth or advice
acceptance. To repeat evidence separately, use an isolated checkout of the
pinned revision and `python3 -m unittest -v test_empirical_settlement`.
Compare cases and outcomes with the saved output; do not replace the saved file.
Durations and ephemeral test keys are not expected to reproduce identical bytes.
The record separates the ten rerun tests from historical differential, mutation
and consumer checks that were only read in the ledger. Exception semantics are
explicitly unresolved and were source-read, not runtime-probed in this packet.
