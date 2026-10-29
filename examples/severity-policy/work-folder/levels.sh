#!/usr/bin/env bash
# A second policy, written in the plainest form the loader accepts: one flat
# file per level, a list of one id per object, no stage names anywhere.
#
#   bash examples/severity-policy/work-folder/levels.sh
#
# The three files in policy-repo/levels/ cover the same six structural checks
# at three levels of stringency. Nothing is nested and nothing is shared, so
# each file is readable on its own and the filename is the only name a level
# has -- which is why no --stringency is passed below.
#
# This is the arrangement to copy if a policy file is going to be reviewed by
# someone who does not want to learn a schema first.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
LEVELS="$HERE/../policy-repo/levels"

cd "$REPO"

if ! uv run ontology-quality-suite checks --help 2>&1 | grep -q -- "--severity-policy"; then
  echo "This example needs --severity-policy, which the installed suite does"
  echo "not have. It arrived in suite 0.25.0; this install is older."
  exit 1
fi

run() {
  local name="$1"; shift
  echo "== $name"
  uv run ontology-quality-suite checks \
    --ontology "$HERE/myOntology.ttl" \
    --out-dir "$HERE/out/$name" \
    --engine both \
    --own-namespace https://example.org/mine \
    --fail-on never \
    "$@" 2>&1 | grep -E "Severity policy|^  [A-Z]{3}-|Findings:|WARNING"
  echo
}

# The baseline, so the comparison has something to be a comparison against.
run defaults

# One flag, one file, no stage name. A flat file is read as a single stage, so
# there is nothing to select inside it.
for level in exploring reviewing publishing; do
  run "$level" --severity-policy "$LEVELS/$level.json"
done

# Same comparison table as compare.sh uses -- it takes the run names to put
# beside the defaults, so a second policy needs no second script to read it.
uv run python "$HERE/compare.py" exploring reviewing publishing
