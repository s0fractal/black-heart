# A PDF That Runs Its Own Checks

Short experience report (5 pages) with three claims, each at the strength of its evidence:
what a self-running PDF companion checks and does not check (measured), the
"suspended taken as settled" defect class (reported, regression tests executed), and one
receiver session that rejected false advice (reported, byte correspondence executed).

- `paper.md` → `paper.pdf` via `build.sh` (pandoc 3.11, tectonic 0.17.0, DejaVu fonts,
  `SOURCE_DATE_EPOCH=1789344000`; two consecutive builds byte-identical).
- `measure.py` → `measurements/` (companion polyglot + receipt). Measured at commit `1981386`;
  no model calls. Reproduce into a new directory: `python3 -B measure.py ~/new-dir`.
- `measurements/companion.pdf` runs with `python3 -I companion.pdf`. It checks three
  combinator reductions and nothing else; see §2.3 of the paper for the controls.
- `zenodo.json` is the proposed record metadata. **Not deposited.** Deposit is an owner act
  after review of the exact head.

Paper text: CC BY-SA 4.0. `measure.py` and the companion polyglot (which embeds executable
runner code): AGPL-3.0-only. See the repository `LICENSE`.
