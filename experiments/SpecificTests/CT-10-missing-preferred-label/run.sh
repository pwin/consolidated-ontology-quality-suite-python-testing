#!/usr/bin/env bash
#
# CT-10 -- Missing preferred label
#
# The data carries both halves, so the run tests whether the check
# discriminates rather than merely fires:
#
#   error case  :Asset   rdfs:label only, no skos:prefLabel -> reported
#   control     :Site    both                                 -> silent
#
#   ./run.sh            run it
#   ./run.sh --show     run it and print every finding, not just the verdict
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/out"

EXPECTED="QUA-009"
ERROR_CASE="#Asset"
CONTROL="#Site"

# Findings that are correct here and are not the point. Empty is the goal: a
# folder that seeds one defect should report one finding, and anything that
# needs adding here is a claim the suite reports something about data nobody
# wrote.
ALLOWED=""

SUITE=${SUITE:-"uv run --project $HERE/../../.. ontology-quality-suite"}

rm -rf "$OUT"
mkdir -p "$OUT"

# `checks` rather than `data`: the question is about how the ontology is
# written, and no instance data is needed to answer it.
# shellcheck disable=SC2086
$SUITE checks \
  --ontology "$HERE/ontologies/model.ttl" \
  --out-dir "$OUT" \
  --reports minimal \
  --fail-on never

RESULTS="$OUT/full_results.csv"
if [ ! -f "$RESULTS" ]; then
  echo "CT-10: FAIL -- the run wrote no $RESULTS" >&2
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
  echo "CT-10: $EXPECTED reported for $ERROR_CASE -- it has an rdfs:label and no preferred label, so it is missing from everything built from the preferred term."
else
  echo "CT-10: FAIL -- $EXPECTED was not reported for $ERROR_CASE" >&2
  STATUS=1
fi

if grep "^$EXPECTED," "$RESULTS" | grep -q "$CONTROL"; then
  echo "CT-10: FAIL -- $EXPECTED was also reported for $CONTROL, which is correct." >&2
  STATUS=1
else
  echo "CT-10: $CONTROL not reported -- it carries a skos:prefLabel."
fi

REPORTED=$(tail -n +2 "$RESULTS" | cut -d, -f1 | sort -u)
UNEXPECTED=$(echo "$REPORTED" | grep -vx "$EXPECTED" | grep -vxF "$(echo "$ALLOWED" | tr ' ' '
')" || true)
if [ -n "$UNEXPECTED" ]; then
  echo "CT-10: FAIL -- findings nobody chose:" >&2
  echo "$UNEXPECTED" | sed 's/^/  /' >&2
  STATUS=1
fi

if [ "$STATUS" -eq 0 ]; then
  echo "CT-10: PASS"
  echo "      Findings: $OUT/findings.txt"
fi
exit "$STATUS"
