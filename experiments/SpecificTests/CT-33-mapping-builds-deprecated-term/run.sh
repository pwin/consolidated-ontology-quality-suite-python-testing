#!/usr/bin/env bash
#
# CT-33 -- Mapping still builds a term the model deprecates
#
# The data carries both halves, so the run tests whether the check
# discriminates rather than merely fires:
#
#   error case  :PumpStation  deprecated, still built -> reported
#   control     :Site         current                 -> silent
#
#   ./run.sh            run it
#   ./run.sh --show     run it and print every finding, not just the verdict
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/out"

EXPECTED="CMP-033"
ERROR_CASE="PumpStation"
CONTROL="#Site>"

# Findings that are correct here and are not the point. Empty is the goal: a
# folder that seeds one defect should report one finding, and anything that
# needs adding here is a claim the suite reports something about data nobody
# wrote.
ALLOWED=""

SUITE=${SUITE:-"uv run --project $HERE/../../.. ontology-quality-suite"}

rm -rf "$OUT"
mkdir -p "$OUT"

# Two stages, because the thing being checked is the template rather than
# any graph that exists yet.
#
# The first sketches the queries: every CONSTRUCT template becomes turtle,
# with each variable rendered as a term. The sketch is then concatenated with
# the model -- turtle allows it, each file carrying its own @prefix block --
# and the pair is checked, so "what would this mapping build" becomes a graph
# an ordinary check can be asked of before a CSV has been read.
#
# --registry and --sparql point inside this folder and --engine sparql keeps
# the SHACL shapes out, so the only check that runs is this one. Without the
# engine flag the shipped shapes still fire, and against a one-entry registry
# every finding they produce comes back as UNMAPPED -- present, unexplained,
# and impossible to act on.
# shellcheck disable=SC2086
$SUITE sketch \
  --queries "$HERE/queries" \
  --out-dir "$OUT/sketch" \
  --reports minimal \
  --fail-on never

cat "$OUT/sketch/sketch.ttl" "$HERE/ontologies/model.ttl" > "$OUT/merged.ttl"

# shellcheck disable=SC2086
$SUITE checks \
  --ontology "$OUT/merged.ttl" \
  --registry "$HERE/checks/registry.json" \
  --sparql "$HERE/checks" \
  --engine sparql \
  --out-dir "$OUT" \
  --reports minimal \
  --fail-on never

RESULTS="$OUT/full_results.csv"
if [ ! -f "$RESULTS" ]; then
  echo "CT-33: FAIL -- the run wrote no $RESULTS" >&2
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
  echo "CT-33: $EXPECTED reported for $ERROR_CASE -- the model deprecates it and the mapping builds it anyway."
else
  echo "CT-33: FAIL -- $EXPECTED was not reported for $ERROR_CASE" >&2
  STATUS=1
fi

if grep "^$EXPECTED," "$RESULTS" | grep -q "$CONTROL"; then
  echo "CT-33: FAIL -- $EXPECTED was also reported for $CONTROL, which is correct." >&2
  STATUS=1
else
  echo "CT-33: $CONTROL not reported -- it is a current term."
fi

REPORTED=$(tail -n +2 "$RESULTS" | cut -d, -f1 | sort -u)
UNEXPECTED=$(echo "$REPORTED" | grep -vx "$EXPECTED" | grep -vxF "$(echo "$ALLOWED" | tr ' ' '
')" || true)
if [ -n "$UNEXPECTED" ]; then
  echo "CT-33: FAIL -- findings nobody chose:" >&2
  echo "$UNEXPECTED" | sed 's/^/  /' >&2
  STATUS=1
fi

if [ "$STATUS" -eq 0 ]; then
  echo "CT-33: PASS"
  echo "      Findings: $OUT/findings.txt"
fi
exit "$STATUS"
