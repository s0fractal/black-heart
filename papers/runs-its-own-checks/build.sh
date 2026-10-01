#!/bin/sh
# Build paper.pdf from paper.md. Toolchain versions are enforced: another version is a
# different artifact. The companion polyglot is not built here; it is the retained output
# of measure.py (measurements/companion.pdf), whose bytes a rebuild must reproduce.
set -e
cd "$(dirname "$0")"
pandoc --version | head -1 | grep -qx "pandoc 3.11" \
  || { echo "build.sh: need pandoc 3.11, have: $(pandoc --version | head -1)" >&2; exit 1; }
tectonic --version | grep -qx "Tectonic 0.17.0" \
  || { echo "build.sh: need Tectonic 0.17.0, have: $(tectonic --version)" >&2; exit 1; }
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1789344000}"   # 2026-09-14T00:00:00Z, the paper date
pandoc paper.md -o paper.pdf \
  --citeproc --bibliography=references.bib --pdf-engine=tectonic \
  -V geometry:margin=1in -V fontsize=10pt -V colorlinks=true -V linkcolor=blue -V urlcolor=blue \
  -V mainfont=DejaVuSerif.ttf -V monofont=DejaVuSansMono.ttf
echo "built: paper.pdf"
