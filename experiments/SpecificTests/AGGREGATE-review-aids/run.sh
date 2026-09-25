#!/usr/bin/env bash
#
# CT-23 to CT-28 -- what changed between two comparable outputs.
#
# One folder for six competency tests, because they are six questions about
# one pair of files. They share the data, they share the parse, and a
# reviewer asks them together: the pipeline ran again, what moved?
#
# Each is still asserted separately, so a red row names one capability:
#
#   CT-23  prefix and namespace declarations differ
#   CT-24  predicate usage differs
#   CT-25  class populations differ
#   CT-26  a shared subject's values changed
#   CT-27  representation-only differences were suppressed before comparing
#   CT-28  one business key, two subject IRIs
#
#   ./run.sh            the verdicts
#   ./run.sh --show     the verdicts plus every finding, with its file
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/out"
BASELINE="$HERE/data/baseline.ttl"
CANDIDATE="$HERE/data/candidate.ttl"

# compare.py imports rdflib and nothing from this repo, so any interpreter
# with rdflib runs it. PYTHON is here for the one that has it.
PYTHON=${PYTHON:-"uv run --project $HERE/../../.. python"}

rm -rf "$OUT"
mkdir -p "$OUT"

# shellcheck disable=SC2086
$PYTHON "$HERE/compare.py" "$BASELINE" "$CANDIDATE" > "$OUT/findings.txt" 2>&1

if [ "${1:-}" = "--show" ]; then
  echo
  echo "--- every finding ---"
  cat "$OUT/findings.txt"
fi

echo

STATUS=0
check() {   # ct, what must appear, prose
  if grep -q "^$1 " "$OUT/findings.txt" && grep -A1 "^$1 " "$OUT/findings.txt" | grep -q "$2"; then
    echo "$1: $3"
  else
    echo "$1: FAIL -- nothing reported matching '$2'" >&2
    STATUS=1
  fi
}

check "CT-23" "wt"          "the same namespace under two prefix names -- a textual diff would call every line changed"
check "CT-24" "hasReading"  "a predicate used in one output and not the other"
check "CT-25" "PumpStation" "a class with two instances in one output and one in the other"
check "CT-26" "reportedBy"  "a shared subject whose relationship target moved"
check "CT-27" "suppressed"  "representation-only differences suppressed before comparing"
check "CT-28" "EASTBROOK"   "one business key under two subject IRIs"

# The controls: site-S1 keeps its IRI and its name in both files, so nothing
# may be reported about its identity or its siteName.
if grep -A1 "^CT-28" "$OUT/findings.txt" | grep -q "'S1'"; then
  echo "CT-28: FAIL -- site-S1 was reported, and it is unchanged in both outputs" >&2
  STATUS=1
fi
if grep -q "siteName changed" "$OUT/findings.txt"; then
  echo "CT-26: FAIL -- siteName was reported changed, and both outputs agree about it" >&2
  STATUS=1
fi

echo
if [ "$STATUS" -eq 0 ]; then
  echo "CT-23..28: PASS -- 6 of 6"
  echo "      Findings: $OUT/findings.txt"
fi
exit "$STATUS"
