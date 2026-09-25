#!/usr/bin/env bash
#
# CT-8 -- Missing concept definition.
#
# The data carries both halves, so the run tests whether the check
# discriminates rather than merely fires:
#
#   error case  :Asset  named and labelled, with no skos:definition -> reported
#   control     :Site   the same, with one                          -> silent
#
#   ./run.sh            run it
#   ./run.sh --show     run it and print every finding, not just the verdict
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/out"

EXPECTED="QUA-010"
ERROR_CASE="#Asset"
CONTROL="#Site"

# Empty, and meant to stay that way: this folder seeds one defect and the run
# reports one finding. Anything that needs adding here is a claim that the
# suite reports something about data nobody wrote.
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
  echo "CT-8: FAIL -- the run wrote no $RESULTS" >&2
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
  echo "CT-8: $EXPECTED reported for $ERROR_CASE -- the class is named and labelled"
  echo "      but nobody wrote down what it means."
else
  echo "CT-8: FAIL -- $EXPECTED was not reported for $ERROR_CASE" >&2
  STATUS=1
fi

if grep "^$EXPECTED," "$RESULTS" | grep -q "$CONTROL"; then
  echo "CT-8: FAIL -- $EXPECTED was also reported for $CONTROL, which has a definition." >&2
  STATUS=1
else
  echo "CT-8: $CONTROL not reported -- it carries a definition and the check leaves"
  echo "      it alone."
fi

REPORTED=$(tail -n +2 "$RESULTS" | cut -d, -f1 | sort -u)
UNEXPECTED=$(echo "$REPORTED" | grep -vx "$EXPECTED" | grep -vxF "$(echo "$ALLOWED" | tr ' ' '\n')" || true)
if [ -n "$UNEXPECTED" ]; then
  echo "CT-8: FAIL -- findings nobody chose:" >&2
  echo "$UNEXPECTED" | sed 's/^/  /' >&2
  STATUS=1
fi

if [ "$STATUS" -eq 0 ]; then
  echo "CT-8: PASS"
  echo "      Findings: $OUT/findings.txt"
fi
exit "$STATUS"
