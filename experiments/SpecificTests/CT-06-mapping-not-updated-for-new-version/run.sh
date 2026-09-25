#!/usr/bin/env bash
#
# CT-6 -- Ontology changes not propagated to TARQL mappings
#
# The data carries both halves, so the run tests whether the check
# discriminates rather than merely fires:
#
#   error case  :PumpStation     built by the mapping, absent from 2.0.0 -> reported
#   control     :Site            built, and still declared               -> silent
#
#   ./run.sh            run it
#   ./run.sh --show     run it and print every finding, not just the verdict
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/out"

EXPECTED="CNF-001"
ERROR_CASE="PumpStation"
CONTROL="#Site>"

# Findings that are correct here and are not the point. Empty is the goal: a
# folder that seeds one defect should report one finding, and anything that
# needs adding here is a claim the suite reports something about data nobody
# wrote.
ALLOWED="CNF-005"

SUITE=${SUITE:-"uv run --project $HERE/../../.. ontology-quality-suite"}

rm -rf "$OUT"
mkdir -p "$OUT"

# The sketch is diffed against 2.0.0's declarations, so the question is
# asked of the query text and the current model -- no data, no triplifying,
# and an answer before the next run writes a row.
# shellcheck disable=SC2086
$SUITE sketch \
  --queries "$HERE/queries" \
  --ontology "$HERE/ontologies/model-v2.ttl" \
  --out-dir "$OUT" \
  --reports minimal \
  --fail-on never

RESULTS="$OUT/full_results.csv"
if [ ! -f "$RESULTS" ]; then
  echo "CT-6: FAIL -- the run wrote no $RESULTS" >&2
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
  echo "CT-6: $EXPECTED reported for $ERROR_CASE -- the mapping builds a class 2.0.0 does not declare."
else
  echo "CT-6: FAIL -- $EXPECTED was not reported for $ERROR_CASE" >&2
  STATUS=1
fi

if grep "^$EXPECTED," "$RESULTS" | grep -q "$CONTROL"; then
  echo "CT-6: FAIL -- $EXPECTED was also reported for $CONTROL, which is correct." >&2
  STATUS=1
else
  echo "CT-6: $CONTROL not reported -- it is declared in 2.0.0 and the mapping still builds it."
fi

REPORTED=$(tail -n +2 "$RESULTS" | cut -d, -f1 | sort -u)
UNEXPECTED=$(echo "$REPORTED" | grep -vx "$EXPECTED" | grep -vxF "$(echo "$ALLOWED" | tr ' ' '
')" || true)
if [ -n "$UNEXPECTED" ]; then
  echo "CT-6: FAIL -- findings nobody chose:" >&2
  echo "$UNEXPECTED" | sed 's/^/  /' >&2
  STATUS=1
fi

if [ "$STATUS" -eq 0 ]; then
  echo "CT-6: PASS"
  echo "      Findings: $OUT/findings.txt"
fi
exit "$STATUS"
