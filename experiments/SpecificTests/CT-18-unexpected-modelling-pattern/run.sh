#!/usr/bin/env bash
#
# CT-18 -- Generated graph uses an unexpected modelling pattern
#
# The data carries both halves, so the run tests whether the check
# discriminates rather than merely fires:
#
#   error case  reading-R2  the number flattened onto the reading -> reported
#   control     reading-R1  the number on a magnitude node        -> silent
#
#   ./run.sh            run it
#   ./run.sh --show     run it and print every finding, not just the verdict
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/out"

EXPECTED="CMP-018"
ERROR_CASE="reading-R2"
CONTROL="reading-R1"

# Findings that are correct here and are not the point. Empty is the goal: a
# folder that seeds one defect should report one finding, and anything that
# needs adding here is a claim the suite reports something about data nobody
# wrote.
ALLOWED="CNF-003"

SUITE=${SUITE:-"uv run --project $HERE/../../.. ontology-quality-suite"}

rm -rf "$OUT"
mkdir -p "$OUT"

# --registry and --sparql point inside this folder, so the only check that
# runs is the one this folder is about. The suite warns that its own query
# tree was replaced, which is true and is the intent: the built-in checks are
# exercised by the folders whose questions they answer, and running them here
# would report this fixture's deliberate minimalism as findings of its own.
#
# The registry entry is what gives the finding its id, title and severity. A
# check with no entry still runs and reports as UNMAPPED, which the
# assertions below would catch.
# shellcheck disable=SC2086
$SUITE data "$HERE/data/output.ttl" \
  --ontology "$HERE/ontologies/model.ttl" \
  --registry "$HERE/checks/registry.json" \
  --sparql "$HERE/checks" \
  --reasoner owlrl-only \
  --out-dir "$OUT" \
  --reports minimal \
  --fail-on never

RESULTS="$OUT/full_results.csv"
if [ ! -f "$RESULTS" ]; then
  echo "CT-18: FAIL -- the run wrote no $RESULTS" >&2
  exit 1
fi

if [ "${1:-}" = "--show" ]; then
  echo
  echo "--- every finding ---"
  cut -d, -f1,4,5 "$RESULTS"
fi

echo
STATUS=0

if grep "^$EXPECTED," "$RESULTS" | grep -q "$ERROR_CASE"; then
  echo "CT-18: $EXPECTED reported for $ERROR_CASE -- the number is hung straight off the reading, so there is nowhere to put its unit."
else
  echo "CT-18: FAIL -- $EXPECTED was not reported for $ERROR_CASE" >&2
  STATUS=1
fi

if grep "^$EXPECTED," "$RESULTS" | grep -q "$CONTROL"; then
  echo "CT-18: FAIL -- $EXPECTED was also reported for $CONTROL, which is correct." >&2
  STATUS=1
else
  echo "CT-18: $CONTROL not reported -- its number sits on a magnitude node, as the pattern requires."
fi

REPORTED=$(tail -n +2 "$RESULTS" | cut -d, -f1 | sort -u)
UNEXPECTED=$(echo "$REPORTED" | grep -vx "$EXPECTED" | grep -vxF "$(echo "$ALLOWED" | tr ' ' '
')" || true)
if [ -n "$UNEXPECTED" ]; then
  echo "CT-18: FAIL -- findings nobody chose:" >&2
  echo "$UNEXPECTED" | sed 's/^/  /' >&2
  STATUS=1
fi

if [ "$STATUS" -eq 0 ]; then
  echo "CT-18: PASS"
  echo "      Findings: $OUT/findings.txt"
fi
exit "$STATUS"
