#!/usr/bin/env bash
#
# CT-20 -- Magnitude missing a unit of measure
#
# The data carries both halves, so the run tests whether the check
# discriminates rather than merely fires:
#
#   error case  flow-S2  a number with no unit -> reported
#   control     flow-S1  a number and its unit  -> silent
#
#   ./run.sh            run it
#   ./run.sh --show     run it and print every finding, not just the verdict
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/out"

EXPECTED="DAT-004"
ERROR_CASE="flow-S2"
CONTROL="flow-S1"

# Findings that are correct here and are not the point. Empty is the goal: a
# folder that seeds one defect should report one finding, and anything that
# needs adding here is a claim the suite reports something about data nobody
# wrote.
ALLOWED="STR-004"

SUITE=${SUITE:-"uv run --project $HERE/../../.. ontology-quality-suite"}

rm -rf "$OUT"
mkdir -p "$OUT"

# `data` is the full pass -- the registry checks, the ontology-vs-data
# conformance layer, and reasoning. owlrl-only because nothing here needs a
# DL reasoner and it keeps the run to a second.
# shellcheck disable=SC2086
$SUITE data "$HERE/data/output.ttl" \
  --ontology "$HERE/ontologies/model.ttl" \
  --reasoner owlrl-only \
  --out-dir "$OUT" \
  --reports minimal \
  --fail-on never

RESULTS="$OUT/full_results.csv"
if [ ! -f "$RESULTS" ]; then
  echo "CT-20: FAIL -- the run wrote no $RESULTS" >&2
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
  echo "CT-20: $EXPECTED reported for $ERROR_CASE -- it carries a number and no unit, so nothing can say 47 of what."
else
  echo "CT-20: FAIL -- $EXPECTED was not reported for $ERROR_CASE" >&2
  STATUS=1
fi

if grep "^$EXPECTED," "$RESULTS" | grep -q "$CONTROL"; then
  echo "CT-20: FAIL -- $EXPECTED was also reported for $CONTROL, which is correct." >&2
  STATUS=1
else
  echo "CT-20: $CONTROL not reported -- it carries its unit."
fi

REPORTED=$(tail -n +2 "$RESULTS" | cut -d, -f1 | sort -u)
UNEXPECTED=$(echo "$REPORTED" | grep -vx "$EXPECTED" | grep -vxF "$(echo "$ALLOWED" | tr ' ' '
')" || true)
if [ -n "$UNEXPECTED" ]; then
  echo "CT-20: FAIL -- findings nobody chose:" >&2
  echo "$UNEXPECTED" | sed 's/^/  /' >&2
  STATUS=1
fi

if [ "$STATUS" -eq 0 ]; then
  echo "CT-20: PASS"
  echo "      Findings: $OUT/findings.txt"
fi
exit "$STATUS"
