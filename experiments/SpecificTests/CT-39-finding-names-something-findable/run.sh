#!/usr/bin/env bash
#
# CT-39 -- A finding names something a reader can find
#
# The only folder on the board whose assertion is about the *message* rather
# than about which check fired. Both cases here are meant to be reported, and
# what separates them is whether the message survives:
#
#   error case  untagged label on a blank node -> reported, and readable
#   control     untagged label on an IRI       -> reported, and readable
#
#   ./run.sh            run it
#   ./run.sh --show     run it and print every finding, not just the verdict
#
# Why a folder for this. STY-003 built its message with STR(?e), and SPARQL
# 1.1 17.4.2.5 defines STR() for literals and IRIs only -- so STR() of a blank
# node is a type error, CONCAT errors, BIND leaves the message variable
# unbound, and a CONSTRUCT template drops the triple whose object is unbound.
# The check went on firing, at the right count and the right severity, with no
# message at all for 60 of 65 findings on the suite's own stress fixture. Every
# other kind of assertion on this board would have passed, and did: the defect
# reached users through the VS Code extension, which runs the same queries
# through oxigraph. The extension runs the shapes too, through shacl-wasm-node,
# but its merge does not fill a missing message from the other arm -- so the
# measured result there was three rows for two findings, the blank-node one
# twice, with the surviving message naming an internal label. See the README.
#
# EFF-001 had it too, found by the same assertion once it existed.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/out"

EXPECTED="STY-003"
ERROR_CASE="blank node"
CONTROL="#Chassis"

# Findings that are correct here and are not the point. Empty is the goal: a
# folder that seeds one defect should report one finding, and anything that
# needs adding here is a claim the suite reports something about data nobody
# wrote.
ALLOWED=""

SUITE=${SUITE:-"uv run --project $HERE/../../.. ontology-quality-suite"}

rm -rf "$OUT"
mkdir -p "$OUT"

# --engine sparql, and that is the whole point of the folder rather than a
# detail of it. With both formulations running, checks/merge.py fills a missing
# message from whichever source still has one, so the portable layer can stop
# producing messages entirely and nothing downstream notices. The extension
# runs the portable layer alone, so this is also the configuration that matches
# where the defect shipped.
# shellcheck disable=SC2086
$SUITE checks \
  --ontology "$HERE/ontologies/model.ttl" \
  --engine sparql \
  --out-dir "$OUT" \
  --reports minimal \
  --fail-on never

RESULTS="$OUT/full_results.csv"
if [ ! -f "$RESULTS" ]; then
  echo "CT-39: FAIL -- the run wrote no $RESULTS" >&2
  exit 1
fi

if [ "${1:-}" = "--show" ]; then
  echo
  echo "--- every finding ---"
  cut -d, -f1,5,8 "$RESULTS"
fi

echo
STATUS=0

# The rows for the check under test, as whole CSV records so the message column
# travels with them.
ROWS=$(grep "^$EXPECTED," "$RESULTS" || true)
COUNT=$(printf '%s' "$ROWS" | grep -c . || true)

if [ "$COUNT" -ne 2 ]; then
  echo "CT-39: FAIL -- expected 2 $EXPECTED findings (one blank-node, one IRI), got $COUNT" >&2
  STATUS=1
else
  echo "CT-39: $EXPECTED reported twice -- once for the anonymous restriction, once for :Chassis."
fi

# 1. Every finding carries a message. A CONSTRUCT template drops a triple whose
#    variable is unbound, so an expression that errors for some rows removes the
#    message for exactly those rows and leaves the rest looking healthy.
EMPTY=0
while IFS= read -r row; do
  [ -n "$row" ] || continue
  MSG=$(printf '%s' "$row" | cut -d, -f8 | tr -d '" ')
  if [ -z "$MSG" ]; then
    EMPTY=$((EMPTY + 1))
  fi
done <<< "$ROWS"
if [ "$EMPTY" -gt 0 ]; then
  echo "CT-39: FAIL -- $EMPTY $EXPECTED finding(s) carry no message." >&2
  echo "      STR() of a blank node is a type error; write IF(isBlank(?x), \"[a blank node]\", STR(?x))." >&2
  STATUS=1
else
  echo "CT-39: every $EXPECTED finding carries a message."
fi

# 2. No message names an internal blank node identifier. Those differ between
#    runs and between engines, so a report built from them is not reproducible
#    -- and to a reader they name nothing at all. This is the half that
#    COALESCE(STR(?x), ...) does not fix: rdflib returns the identifier rather
#    than erroring, so the message stays present and stays useless.
#    Field 8 only, not the whole row: the focus_node column *is* the blank
#    node's identifier and has nowhere else to point, which is legitimate. It is
#    the prose a person reads that must not be built out of it. Scanning the row
#    reported the focus node and failed a run whose message was already right.
MESSAGES=$(printf '%s' "$ROWS" | cut -d, -f8)
if printf '%s' "$MESSAGES" | grep -Eq '[0-9a-f]{24,}'; then
  echo "CT-39: FAIL -- a message names an internal blank node identifier:" >&2
  printf '%s' "$MESSAGES" | grep -Eo '[0-9a-f]{24,}' | sed 's/^/  /' >&2
  STATUS=1
else
  echo "CT-39: no message names an internal blank node identifier."
fi

# 3. The control still reads correctly. Whatever the blank-node branch does, an
#    IRI focus node must still be named in full.
if printf '%s' "$ROWS" | grep -q "$CONTROL"; then
  echo "CT-39: the control names $CONTROL in full."
else
  echo "CT-39: FAIL -- the control's message does not name $CONTROL" >&2
  STATUS=1
fi

REPORTED=$(tail -n +2 "$RESULTS" | cut -d, -f1 | sort -u)
UNEXPECTED=$(echo "$REPORTED" | grep -vx "$EXPECTED" | grep -vxF "$(echo "$ALLOWED" | tr ' ' '
')" || true)
if [ -n "$UNEXPECTED" ]; then
  echo "CT-39: FAIL -- findings nobody chose:" >&2
  echo "$UNEXPECTED" | sed 's/^/  /' >&2
  STATUS=1
fi

if [ "$STATUS" -eq 0 ]; then
  echo "CT-39: PASS"
  echo "      Findings: $OUT/findings.txt"
fi
exit "$STATUS"
