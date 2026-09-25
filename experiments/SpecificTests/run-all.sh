#!/usr/bin/env bash
#
# Every competency test in this folder, as one red/green board.
#
#   ./run-all.sh                     run them all
#   ./run-all.sh CT-01 CT-07         run the ones whose folder name matches
#   ./run-all.sh --csv               machine-readable, for CI to keep
#   SUITE=ontology-quality-suite ./run-all.sh    run against an installed suite
#
# Each folder answers one competency question about one defect, with a
# control beside it, and exits 0 or 1. That is what makes the board worth
# reading: a red row names the capability that stopped working, rather than
# telling you that something in a 38-test worked example moved and leaving
# you to find out what.
#
# Exit code is the board's: 0 only if every test is green, so this is
# directly usable as a CI step.
#
set -uo pipefail          # not -e: a red test must not stop the board

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CSV=""
PATTERNS=()
for arg in "$@"; do
  case "$arg" in
    --csv) CSV=1 ;;
    *) PATTERNS+=("$arg") ;;
  esac
done

matches() {
  [ ${#PATTERNS[@]} -eq 0 ] && return 0
  for p in "${PATTERNS[@]}"; do
    case "$(basename "$1")" in *"$p"*) return 0 ;; esac
  done
  return 1
}

PASSED=0
FAILED=0
ROWS=()

for dir in "$HERE"/CT-*/; do
  [ -x "$dir/run.sh" ] || continue
  matches "$dir" || continue
  NAME="$(basename "$dir")"

  OUTPUT=$("$dir/run.sh" 2>&1)
  CODE=$?

  # The line the folder's own script chose as its verdict -- each one names
  # what was reported and about what, so the board says which capability
  # broke rather than only that something did.
  #
  # "PASS" and the trailing file paths are the script talking to a person at
  # its own prompt; the board has its own STATUS column and its own room, so
  # they are dropped here rather than repeated.
  REASON=$(echo "$OUTPUT" \
    | grep -E "^CT-[0-9A-Za-z]+: " \
    | grep -vE "^CT-[0-9A-Za-z]+: (PASS|Report:|Findings:)" \
    | head -1 | sed 's/^[^:]*: //')
  [ -n "$REASON" ] || REASON=$(echo "$OUTPUT" | tail -1)

  if [ "$CODE" -eq 0 ]; then
    PASSED=$((PASSED + 1))
    ROWS+=("PASS|$NAME|$REASON")
  else
    FAILED=$((FAILED + 1))
    ROWS+=("FAIL|$NAME|$REASON")
  fi
done

if [ -n "$CSV" ]; then
  echo "status,test,detail"
  for row in "${ROWS[@]}"; do
    IFS='|' read -r status name reason <<< "$row"
    printf '%s,%s,"%s"\n' "$status" "$name" "$(echo "$reason" | sed 's/"/""/g')"
  done
else
  printf '%-6s %-34s %s\n' "STATUS" "TEST" "DETAIL"
  for row in "${ROWS[@]}"; do
    IFS='|' read -r status name reason <<< "$row"
    printf '%-6s %-34s %s\n' "$status" "$name" "$(echo "$reason" | cut -c1-90)"
  done
  echo
  echo "$PASSED green, $FAILED red"
fi

[ "$FAILED" -eq 0 ]
