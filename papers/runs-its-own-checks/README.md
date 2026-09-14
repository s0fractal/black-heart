# What a Green Check Does Not Establish

Short engineering report on what a green verification result covers: a self-running PDF
companion and nine controls (measured), the "suspended taken as settled" defect class
(reported, regression tests executed), and one receiver session that rejected synthetic
advice (reported, byte correspondence executed).

- `paper.md` → `paper.pdf` via `build.sh` (pandoc 3.11, tectonic 0.17.0, DejaVu fonts,
  `SOURCE_DATE_EPOCH=1789344000`; two consecutive builds byte-identical).
- `measure.py` → `measurements/` (companion polyglot + receipt). Measured at commit `30679a4`;
  no model calls. Reproduce into a new directory: `python3 -B measure.py ~/new-dir`.
- `measurements/companion.pdf` runs with `python3 -I companion.pdf`. It checks three
  combinator reductions and nothing else; see §3.3 of the paper for the nine controls.
- **Published 2026-09-14:** [10.5281/zenodo.22754264](https://doi.org/10.5281/zenodo.22754264)
  (concept 10.5281/zenodo.22754263), from tag `paper-runs-its-own-checks-v1.0.0` = `e472521`.
  Nine files; `deposited-v1.0.0/MANIFEST.md` and `SHA256SUMS` are byte copies of the record's.
  All nine files downloaded from Zenodo after publication matched the local bundle by sha256.
  `zenodo.json` is the metadata used. Do not edit `paper.md` past the tag without a new version.

Paper text: CC BY-SA 4.0. `measure.py` and the companion polyglot (which embeds executable
runner code): AGPL-3.0-only. See the repository `LICENSE`.
