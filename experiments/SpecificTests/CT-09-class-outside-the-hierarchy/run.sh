#!/usr/bin/env bash
#
# CT-9 -- Class has no place in the class hierarchy
#
# The data carries both halves, so the run tests whether the check
# discriminates rather than merely fires:
#
#   error case  :Telemetry  nothing above it, nothing below -> reported
#   control     :Site       a subclass of :PhysicalThing     -> silent
#
#   ./run.sh            run it
#   ./run.sh --show     run it and print every finding, not just the verdict
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/out"

EXPECTED="CMP-009"
ERROR_CASE="Telemetry"
CONTROL="#Site>"

# Findings that are correct here and are not the point. Empty is the goal: a
# folder that seeds one defect should report one finding, and anything that
# needs adding here is a claim the suite reports something about data nobody
# wrote.
ALLOWED=""

SUITE=${SUITE:-"uv run --project $HERE/../../.. ontology-quality-suite"}

rm -rf "$OUT"
mkdir -p "$OUT"

# A project check over the ontology alone -- no data needed, because the
# question is about how the model is put together.
#
# --registry and --sparql point inside this folder, so the only check that
# runs is this one. The suite says its own tree was replaced, which is true
# and intended here.
# shellcheck disable=SC2086
$SUITE checks \
  --ontology "$HERE/ontologies/model.ttl" \
  --registry "$HERE/checks/registry.json" \
  --sparql "$HERE/checks" \
  --out-dir "$OUT" \
  --reports minimal \
  --fail-on never

RESULTS="$OUT/full_results.csv"
if [ ! -f "$RESULTS" ]; then
  echo "CT-9: FAIL -- the run wrote no $RESULTS" >&2
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
  echo "CT-9: $EXPECTED reported for $ERROR_CASE -- nothing is above it and nothing below, so it sits outside the hierarchy."
else
  echo "CT-9: FAIL -- $EXPECTED was not reported for $ERROR_CASE" >&2
  STATUS=1
fi

if grep "^$EXPECTED," "$RESULTS" | grep -q "$CONTROL"; then
  echo "CT-9: FAIL -- $EXPECTED was also reported for $CONTROL, which is correct." >&2
  STATUS=1
else
  echo "CT-9: $CONTROL not reported -- it is a subclass of :PhysicalThing."
fi

REPORTED=$(tail -n +2 "$RESULTS" | cut -d, -f1 | sort -u)
UNEXPECTED=$(echo "$REPORTED" | grep -vx "$EXPECTED" | grep -vxF "$(echo "$ALLOWED" | tr ' ' '
')" || true)
if [ -n "$UNEXPECTED" ]; then
  echo "CT-9: FAIL -- findings nobody chose:" >&2
  echo "$UNEXPECTED" | sed 's/^/  /' >&2
  STATUS=1
fi

if [ "$STATUS" -eq 0 ]; then
  echo "CT-9: PASS"
  echo "      Findings: $OUT/findings.txt"
fi
exit "$STATUS"
