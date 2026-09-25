#!/usr/bin/env bash
#
# CT-22 -- Numeric datatype or conversion error
#
# The data carries both halves, so the run tests whether the check
# discriminates rather than merely fires:
#
#   error case  ?flow_DT      _DT suffix, never given a datatype -> reported
#   control     ?pressure_DT  _DT suffix, STRDT to xsd:decimal   -> silent
#
#   ./run.sh            run it
#   ./run.sh --show     run it and print every finding, not just the verdict
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/out"

EXPECTED="TQL-005"
ERROR_CASE="flow_DT"
CONTROL="pressure_DT"

# Findings that are correct here and are not the point. Empty is the goal: a
# folder that seeds one defect should report one finding, and anything that
# needs adding here is a claim the suite reports something about data nobody
# wrote.
ALLOWED=""

SUITE=${SUITE:-"uv run --project $HERE/../../.. ontology-quality-suite"}

rm -rf "$OUT"
mkdir -p "$OUT"

# `sketch` reads the query text. No CSVs and no triplifying: the question is
# answerable before the mapping has ever run.
# shellcheck disable=SC2086
$SUITE sketch \
  --queries "$HERE/queries" \
  --ontology "$HERE/ontologies/model.ttl" \
  --out-dir "$OUT" \
  --reports minimal \
  --fail-on never

RESULTS="$OUT/full_results.csv"
if [ ! -f "$RESULTS" ]; then
  echo "CT-22: FAIL -- the run wrote no $RESULTS" >&2
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
  echo "CT-22: $EXPECTED reported for $ERROR_CASE -- the name promises a datatype and the expression never gives one."
else
  echo "CT-22: FAIL -- $EXPECTED was not reported for $ERROR_CASE" >&2
  STATUS=1
fi

if grep "^$EXPECTED," "$RESULTS" | grep -q "$CONTROL"; then
  echo "CT-22: FAIL -- $EXPECTED was also reported for $CONTROL, which is correct." >&2
  STATUS=1
else
  echo "CT-22: $CONTROL not reported -- it is typed with STRDT, as its name promises."
fi

REPORTED=$(tail -n +2 "$RESULTS" | cut -d, -f1 | sort -u)
UNEXPECTED=$(echo "$REPORTED" | grep -vx "$EXPECTED" | grep -vxF "$(echo "$ALLOWED" | tr ' ' '
')" || true)
if [ -n "$UNEXPECTED" ]; then
  echo "CT-22: FAIL -- findings nobody chose:" >&2
  echo "$UNEXPECTED" | sed 's/^/  /' >&2
  STATUS=1
fi

if [ "$STATUS" -eq 0 ]; then
  echo "CT-22: PASS"
  echo "      Findings: $OUT/findings.txt"
fi
exit "$STATUS"
