#!/usr/bin/env bash
#
# CT-29 -- IRI construction pattern not updated after a concept moved namespace
#
# The data carries both halves, so the run tests whether the check
# discriminates rather than merely fires:
#
#   error case  ?site_IRI   minted under the superseded base -> reported
#   control     ?asset_IRI  a concept that never moved        -> silent
#
#   ./run.sh            run it
#   ./run.sh --show     run it and print every finding, not just the verdict
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/out"

EXPECTED="CMP-029"
ERROR_CASE="site_IRI"
CONTROL="asset_IRI"

# Findings that are correct here and are not the point. Empty is the goal: a
# folder that seeds one defect should report one finding, and anything that
# needs adding here is a claim the suite reports something about data nobody
# wrote.
ALLOWED=""

SUITE=${SUITE:-"uv run --project $HERE/../../.. ontology-quality-suite"}

rm -rf "$OUT"
mkdir -p "$OUT"

# Two stages. The sketch stage writes what the queries *say* -- sketch.ttl
# for the CONSTRUCT templates, bind-facts.ttl for the BIND expressions and
# PREFIX declarations -- and the second stage asks a check of those files.
#
# --engine sparql keeps the shipped SHACL shapes out. Without it they run
# against this folder's one-entry registry and every finding comes back as
# UNMAPPED: present, unexplained, and impossible to act on.
# shellcheck disable=SC2086
$SUITE sketch \
  --queries "$HERE/queries" \
  --out-dir "$OUT/sketch" \
  --reports minimal \
  --fail-on never

cat "$OUT/sketch/bind-facts.ttl" "$OUT/sketch/sketch.ttl" "$HERE/ontologies/core.ttl" > "$OUT/merged.ttl"

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
  echo "CT-29: FAIL -- the run wrote no $RESULTS" >&2
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
  echo "CT-29: $EXPECTED reported for $ERROR_CASE -- the concept moved to the shared model and the mapping still mints the old base."
else
  echo "CT-29: FAIL -- $EXPECTED was not reported for $ERROR_CASE" >&2
  STATUS=1
fi

if grep "^$EXPECTED," "$RESULTS" | grep -q "$CONTROL"; then
  echo "CT-29: FAIL -- $EXPECTED was also reported for $CONTROL, which is correct." >&2
  STATUS=1
else
  echo "CT-29: $CONTROL not reported -- that concept never moved."
fi

REPORTED=$(tail -n +2 "$RESULTS" | cut -d, -f1 | sort -u)
UNEXPECTED=$(echo "$REPORTED" | grep -vx "$EXPECTED" | grep -vxF "$(echo "$ALLOWED" | tr ' ' '
')" || true)
if [ -n "$UNEXPECTED" ]; then
  echo "CT-29: FAIL -- findings nobody chose:" >&2
  echo "$UNEXPECTED" | sed 's/^/  /' >&2
  STATUS=1
fi

if [ "$STATUS" -eq 0 ]; then
  echo "CT-29: PASS"
  echo "      Findings: $OUT/findings.txt"
fi
exit "$STATUS"
