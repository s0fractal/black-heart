# Deposit manifest — What a Green Check Does Not Establish, v1.0.0

- Repository: https://github.com/s0fractal/black-heart
- Paper commit: `e47252188963bed4b81809e515b5fd7d4cd41c40` (annotated tag `paper-runs-its-own-checks-v1.0.0`), merged into `main` as `35af27b` (PR #69).
- Measurements: commit `30679a4601b1824a8e3132e89464e464927300f3` (code identical to `62e3e80` plus the measurement script), Python 3.14.7, no model calls.
- Build: `papers/runs-its-own-checks/build.sh` — pandoc 3.11, tectonic 0.17.0, DejaVu fonts, `SOURCE_DATE_EPOCH=1789344000`. Rebuilding from the source archive reproduced `paper.pdf` byte for byte.
- Running `companion.pdf` executes Python code with your user permissions; `python3 -I` isolates imports, it is not a sandbox (paper §3.4).
- The source archive has no Git history: `measure.py` records the commit via `git rev-parse`, so run it from a clone at the tag.

| file | sha256 | license |
|---|---|---|
| `paper.pdf` | `b6d1235dd453c3d8c3f8188d0a245d3c034bdd97d3f26f14461da67d21cae794` | CC BY-SA 4.0 |
| `companion.pdf` | `b7a8bab251ff77b1fa10290247a4bef629a1b7762329c0e5a9c72f0f97f2f278` | AGPL-3.0-only (embeds executable runner) |
| `measurements.json` | `6fc0aefd66e308b38d3353b1226c1c1140455cdfb09a68934bc07a3d01313e82` | CC BY-SA 4.0 |
| `paper.md` | `162d5cc20bcf8e60682a51e9608ee8aa0808e1a179afb853f3c48ba0dfa4d330` | CC BY-SA 4.0 |
| `references.bib` | `57bd2c5fc1e346d8d5b24236cfc5f7279f388e4f0d18df2469a576d85fba3bda` | CC BY-SA 4.0 |
| `measure.py` | `ca08cc58f34611f6eb125cdeab68999836f79d6a8ee6ac2b34c233a9b23547bd` | AGPL-3.0-only |
| `black-heart-runs-its-own-checks-v1.0.0-source.tar.gz` | `5b5388d7c4127631291346ae6ce9824a5cf414e632b557ec6bf83c411410079f` | mixed: see LICENSE in archive (code AGPL-3.0-only, docs CC BY-SA 4.0) |

Not peer-reviewed. A frozen artifact, not a venue, endorsement or release of Black-Heart.
