#!/usr/bin/env bash
#
# CT-7 -- Changes not consistently reflected across dependent artefacts.
#
# Two comparisons from one baseline, because the question is not "did
# anything change" but "how much did this change oblige everyone else to
# change":
#
#   error case  1.0.0 -> 2.0.0 breaking     a class removed -> MAJOR
#   control     1.0.0 -> 1.1.0 compatible   a class added   -> MINOR
#
#   ./run.sh            run it
#   ./run.sh --show     run it and print both reports
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/out"

SUITE=${SUITE:-"uv run --project $HERE/../../.. ontology-quality-suite"}

rm -rf "$OUT"
mkdir -p "$OUT"

# version-diff writes diff.txt rather than the findings.txt/full_results.csv
# pair, so --reports does not apply. Two runs, one per comparison.
# shellcheck disable=SC2086
$SUITE version-diff \
  "$HERE/ontologies/model-v1.ttl" \
  "$HERE/ontologies/model-v2-breaking.ttl" \
  --out-dir "$OUT/breaking" > "$OUT/breaking.log" 2>&1 || true

# shellcheck disable=SC2086
$SUITE version-diff \
  "$HERE/ontologies/model-v1.ttl" \
  "$HERE/ontologies/model-v1-1-compatible.ttl" \
  --out-dir "$OUT/compatible" > "$OUT/compatible.log" 2>&1 || true

BREAKING="$OUT/breaking/diff.txt"
COMPATIBLE="$OUT/compatible/diff.txt"
for f in "$BREAKING" "$COMPATIBLE"; do
  if [ ! -f "$f" ]; then
    echo "CT-7: FAIL -- the run wrote no $f" >&2
    cat "$OUT"/*.log >&2
    exit 1
  fi
done

if [ "${1:-}" = "--show" ]; then
  echo
  echo "--- breaking ---"; cat "$BREAKING"
  echo "--- compatible ---"; cat "$COMPATIBLE"
fi

echo
STATUS=0

if grep -qi "version bump: MAJOR" "$BREAKING"; then
  echo "CT-7: MAJOR reported for the breaking change -- a class was removed, so"
  echo "      every mapping, query and document naming it is now wrong."
else
  echo "CT-7: FAIL -- removing a class did not imply a MAJOR bump" >&2
  STATUS=1
fi

if grep -qi "version bump: MAJOR" "$COMPATIBLE"; then
  echo "CT-7: FAIL -- adding a class implied a MAJOR bump, and nothing built" >&2
  echo "      against 1.0.0 can break when a term is added." >&2
  STATUS=1
elif grep -qi "version bump: MINOR" "$COMPATIBLE"; then
  echo "CT-7: MINOR reported for the compatible change -- a class was added and"
  echo "      nothing that existed moved, so no dependent artefact is obliged to."
else
  echo "CT-7: FAIL -- no version bump was suggested for the compatible change" >&2
  STATUS=1
fi

if [ "$STATUS" -eq 0 ]; then
  echo "CT-7: PASS"
  echo "      Reports: $OUT/breaking/diff.txt, $OUT/compatible/diff.txt"
fi
exit "$STATUS"
