#!/usr/bin/env bash
#
# CT-34, CT-35, CT-36, CT-38 -- drift across a set of mappings.
#
# One folder for four competency tests, because all four read the same three
# mappings and the same three ontologies, and because none of them exists in
# a project with one mapping. They appear with the second file.
#
# Each is asserted separately, so a red row names one capability:
#
#   CT-34  one class, two shapes -- :Site with a name in one file, bare in another
#   CT-35  one property, two datatypes -- typed in one mapping, a CSV column in another
#   CT-36  a term reachable only by being named on a command line
#   CT-38  the output moved against what was agreed
#
#   ./run.sh            the verdicts
#   ./run.sh --show     the verdicts plus every finding, with its files
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/out"

PYTHON=${PYTHON:-"uv run --project $HERE/../../.. python"}

mkdir -p "$OUT"
rm -f "$OUT/findings.txt"

# produced/readings.ttl stands in for a triplify run: the graph the mappings
# make today. Kept as a file so the folder runs without oxi-gen, and so the
# comparison against expected/ is the thing under test rather than the
# triplifier.
#
# It lives in produced/ rather than out/ because it is an input. Anything
# under out/ is gitignored, so a fixture kept there survives locally and is
# missing for everyone who clones -- which is a failure that only appears on
# someone else's machine.
# shellcheck disable=SC2086
$PYTHON "$HERE/drift.py" \
  --queries "$HERE/queries" \
  --ontology "$HERE/ontologies/model.ttl" \
  --ontology "$HERE/ontologies/units.ttl" \
  --integration "$HERE/ontologies/integration.ttl" \
  --expected "$HERE/expected/readings.ttl" \
  --produced "$HERE/produced/readings.ttl" > "$OUT/findings.txt" 2>&1

if [ "${1:-}" = "--show" ]; then
  echo
  echo "--- every finding ---"
  cat "$OUT/findings.txt"
fi

echo
STATUS=0
check() {   # ct, what must appear, prose
  if grep -q "^$1 " "$OUT/findings.txt" && grep "^$1 " "$OUT/findings.txt" | grep -q "$2"; then
    echo "$1: $3"
  else
    echo "$1: FAIL -- nothing reported matching '$2'" >&2
    STATUS=1
  fi
}

check "CT-34" "Site"        "one class built two ways -- sites.rq gives it a name, readings.rq gives it nothing"
check "CT-35" "flowValue"   "one property typed in one mapping and taken straight from a column in another"
check "CT-36" "units#"      "a namespace the mappings build and the integration ontology cannot reach"
check "CT-38" "measuredIn"  "the output moved against what was agreed"

# The control: :Reading is built by two files with the same shape in the part
# that matters, and :siteName is typed the same way wherever it appears.
if grep "^CT-35" "$OUT/findings.txt" | grep -q "siteName"; then
  echo "CT-35: FAIL -- siteName was reported, and only one mapping sets it" >&2
  STATUS=1
fi

echo
if [ "$STATUS" -eq 0 ]; then
  echo "CT-34,35,36,38: PASS -- 4 of 4"
  echo "      Findings: $OUT/findings.txt"
fi
exit "$STATUS"
