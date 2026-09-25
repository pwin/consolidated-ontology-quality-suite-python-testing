#!/usr/bin/env bash
#
# CT-3 -- IRI construction pattern not updated following a model change.
#
# The fault exists in no single file. model-v2.ttl is a correct ontology,
# assets.rq is a correct query, and only read against each other is anything
# wrong. That is why the command takes both versions and the queries at once.
#
#   error case  :PumpStation  renamed in 2.0.0, still built by the mapping -> reported
#   control     :Site         unchanged, still built by the mapping        -> silent
#
#   ./run.sh            run it
#   ./run.sh --show     run it and print the whole report
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/out"

ERROR_CASE="PumpStation"
CONTROL="Site"

SUITE=${SUITE:-"uv run --project $HERE/../../.. ontology-quality-suite"}

rm -rf "$OUT"
mkdir -p "$OUT"

# `consistency` is the only stage that takes two ontology versions. It writes
# consistency.txt rather than the findings.txt/full_results.csv pair, so this
# folder reads that instead and --reports does not apply.
#
# No --apply-repairs: the run writes the suggested rename as a .patch under
# out/repairs and leaves the query alone. A fixture that repaired itself
# would pass once.
# shellcheck disable=SC2086
$SUITE consistency \
  --old "$HERE/ontologies/model-v1.ttl" \
  --new "$HERE/ontologies/model-v2.ttl" \
  --queries "$HERE/queries" \
  --out-dir "$OUT" > "$OUT/run.log" 2>&1 || true

REPORT="$OUT/consistency.txt"
if [ ! -f "$REPORT" ]; then
  echo "CT-3: FAIL -- the run wrote no $REPORT" >&2
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

# 1. the mapping builds a class the current model does not declare
if grep -q "undeclared_class.*$ERROR_CASE" "$REPORT"; then
  echo "CT-3: :$ERROR_CASE reported as undeclared -- 2.0.0 renamed it and the"
  echo "      mapping still builds it, so every row it writes names a class the"
  echo "      current model does not have."
else
  echo "CT-3: FAIL -- no undeclared_class finding for :$ERROR_CASE" >&2
  STATUS=1
fi

# 2. the rename is recognised as a rename, not just as a loss
if grep -q "rename_iri" "$REPORT" && grep -q "$ERROR_CASE -> .*Pumping" "$REPORT"; then
  echo "CT-3: the rename is paired -- the report names the term to move to, so"
  echo "      the fix is a substitution rather than a search."
else
  echo "CT-3: FAIL -- the removed and added terms were not paired as a rename" >&2
  STATUS=1
fi

# 3. the control is left alone
if grep -q "undeclared_class.*#$CONTROL\b" "$REPORT"; then
  echo "CT-3: FAIL -- :$CONTROL was reported too, and it is unchanged in 2.0.0." >&2
  STATUS=1
else
  echo "CT-3: :$CONTROL not reported -- unchanged across both versions, and the"
  echo "      run leaves it alone."
fi

# 4. nothing about prefixes: both files use the same `:`
if grep -q "misalignment" "$REPORT"; then
  echo "CT-3: FAIL -- a prefix misalignment was reported. The ontology and the" >&2
  echo "      query bind : to the same namespace; needs suite 0.21.0." >&2
  STATUS=1
fi

if [ "$STATUS" -eq 0 ]; then
  echo "CT-3: PASS"
  echo "      Report: $REPORT"
fi
exit "$STATUS"
