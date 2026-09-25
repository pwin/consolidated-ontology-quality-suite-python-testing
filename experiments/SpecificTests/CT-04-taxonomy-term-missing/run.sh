#!/usr/bin/env bash
#
# CT-4 -- taxonomy/ontology concepts referenced by TARQL do not exist.
#
#   error case  vocab:Resevoir  hard-coded in the template, absent from the taxonomy -> reported
#   control     vocab:Borehole  hard-coded, and declared                             -> silent
#
#   ./run.sh            run it
#   ./run.sh --show     run it and print the whole report
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/out"

ERROR_CASE="Resevoir"
CONTROL="Borehole"

SUITE=${SUITE:-"uv run --project $HERE/../../.. ontology-quality-suite"}

rm -rf "$OUT"
mkdir -p "$OUT"

# The taxonomy is passed twice, and deliberately. --taxonomy is what makes it
# the authority for controlled-vocabulary terms; --ontology is what puts its
# namespace in the set the prefix layer compares query prefixes against.
# Without the second, a query using the taxonomy's own prefix is reported as
# using a namespace nothing declares -- true of the ontology set as given,
# and not what anyone means.
#
# pattern-consistency writes pattern-consistency.txt rather than the
# findings.txt/full_results.csv pair, so --reports does not apply here.
# shellcheck disable=SC2086
$SUITE pattern-consistency \
  --queries "$HERE/queries" \
  --ontology "$HERE/ontologies/model.ttl" \
  --ontology "$HERE/ontologies/asset-types.ttl" \
  --taxonomy "$HERE/ontologies/asset-types.ttl" \
  --out-dir "$OUT" > "$OUT/run.log" 2>&1 || true

REPORT="$OUT/pattern-consistency.txt"
if [ ! -f "$REPORT" ]; then
  echo "CT-4: FAIL -- the run wrote no $REPORT" >&2
  cat "$OUT/run.log" >&2
  exit 1
fi

if [ "${1:-}" = "--show" ]; then
  echo
  echo "--- the report ---"
  cat "$REPORT"
fi

echo
STATUS=0

if grep -q "undeclared_taxonomy_reference.*$ERROR_CASE" "$REPORT"; then
  echo "CT-4: vocab:$ERROR_CASE reported -- the template hard-codes a term the taxonomy"
  echo "      does not declare, so every asset it classifies points at nothing."
else
  echo "CT-4: FAIL -- no undeclared taxonomy reference for vocab:$ERROR_CASE" >&2
  STATUS=1
fi

if grep -q "undeclared_taxonomy_reference.*$CONTROL" "$REPORT"; then
  echo "CT-4: FAIL -- vocab:$CONTROL was reported too, and the taxonomy declares it." >&2
  STATUS=1
else
  echo "CT-4: vocab:$CONTROL not reported -- spelled as the taxonomy spells it."
fi

if grep -q "misalignment" "$REPORT"; then
  echo "CT-4: FAIL -- a prefix misalignment was reported; the taxonomy is in the" >&2
  echo "      ontology set, so its namespace is declared." >&2
  STATUS=1
fi

if [ "$STATUS" -eq 0 ]; then
  echo "CT-4: PASS"
  echo "      Report: $REPORT"
fi
exit "$STATUS"
