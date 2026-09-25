#!/usr/bin/env bash
#
# CT-15 and CT-16 -- what the mapping promised against what it produced.
#
# One folder for two competency tests, because both compare the same three
# things: the CONSTRUCT templates, the source rows, and the output graph.
#
#   CT-15  :pressureValue is defined by the template and carried by nothing
#   CT-16  four source rows became two entities
#
# The control is :flowValue, defined by the same template and present on
# every entity -- so a check that reported both would be saying only that the
# template mentions properties.
#
#   ./run.sh            the verdicts
#   ./run.sh --show     the verdicts plus every finding, with its files
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/out"

PYTHON=${PYTHON:-"uv run --project $HERE/../../.. python"}

rm -rf "$OUT"
mkdir -p "$OUT"

# --expected-dropped 0: this mapping is not supposed to filter anything. A
# project that drops rows on purpose sets it to the number it intends, so the
# check reports the difference between the loss and the intention rather than
# the loss alone.
# shellcheck disable=SC2086
$PYTHON "$HERE/integrity.py" \
  --queries "$HERE/queries" \
  --output "$HERE/data/output.ttl" \
  --population "$HERE/csv/readings.csv" "$HERE/data/output.ttl" \
    "https://example.org/water/model#Reading" \
  --expected-dropped 0 > "$OUT/findings.txt" 2>&1

if [ "${1:-}" = "--show" ]; then
  echo
  echo "--- every finding ---"
  cat "$OUT/findings.txt"
fi

echo
STATUS=0

if grep "^CT-15" "$OUT/findings.txt" | grep -q "pressureValue"; then
  echo "CT-15: a property the template defines and no entity carries -- the mapping"
  echo "       promises it and no source column feeds it."
else
  echo "CT-15: FAIL -- nothing reported about pressureValue" >&2
  STATUS=1
fi

if grep "^CT-15" "$OUT/findings.txt" | grep -q "flowValue"; then
  echo "CT-15: FAIL -- flowValue was reported, and every entity carries it" >&2
  STATUS=1
fi

if grep "^CT-16" "$OUT/findings.txt" | grep -q "4 row"; then
  echo "CT-16: four source rows became two entities -- the IRI is built from the"
  echo "       site alone, so each site's readings collapse onto one."
else
  echo "CT-16: FAIL -- the population mismatch was not reported" >&2
  STATUS=1
fi

echo
if [ "$STATUS" -eq 0 ]; then
  echo "CT-15,16: PASS -- 2 of 2"
  echo "      Findings: $OUT/findings.txt"
fi
exit "$STATUS"
