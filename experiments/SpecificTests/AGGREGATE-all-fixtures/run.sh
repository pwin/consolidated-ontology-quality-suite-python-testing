#!/usr/bin/env bash
#
# Every fixture in this folder tree, merged into one project, reported as a
# whole.
#
# The CT folders each answer one question with nothing else in the file. This
# is the opposite and is the point of it: one ontology built from twenty-nine
# files, fifteen mappings and nine output graphs, written at different times
# by different hands, with every seeded defect present at once. That is what
# a real project looks like when the suite is first pointed at it.
#
#   ./run.sh            the summary
#   ./run.sh --detail   the summary plus every finding, one line each
#
# Not a pass/fail test. There is no verdict to give: the answer is the
# report. `run-all.sh` skips this folder for that reason.
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/out"

SUITE=${SUITE:-"uv run --project $HERE/../../.. ontology-quality-suite"}

rm -rf "$OUT"
mkdir -p "$OUT"

# One ontology from all of them. Turtle concatenates: each file carries its
# own @prefix block. Where two fixtures say different things about the same
# term, the merged graph holds both -- which is realistic, and some of what
# is reported below exists only because of it.
cat "$HERE"/ontologies/*.ttl > "$OUT/model.ttl"

# Three passes rather than one, so every finding keeps its identity. A run
# given only this folder's registry reports the suite's own checks as
# UNMAPPED; a run given only the suite's reports the CMP-* ones that way. The
# alternative is merging two registries at run time, which is more machinery
# than a demonstration needs.
#
# 1. the queries, against the merged model
# shellcheck disable=SC2086
$SUITE sketch \
  --queries "$HERE/queries" \
  --ontology "$OUT/model.ttl" \
  --out-dir "$OUT/queries" \
  --reports minimal \
  --fail-on never > "$OUT/queries.log" 2>&1 || true

# 2. the output graphs, against the merged model, with the suite's own checks
# shellcheck disable=SC2086
$SUITE data "$HERE"/data/*.ttl \
  --ontology "$OUT/model.ttl" \
  --reasoner owlrl-only \
  --out-dir "$OUT/builtin" \
  --reports minimal \
  --fail-on never > "$OUT/builtin.log" 2>&1 || true

# 3. the same output, with this project's own checks
# shellcheck disable=SC2086
$SUITE data "$HERE"/data/*.ttl \
  --ontology "$OUT/model.ttl" \
  --registry "$HERE/checks/registry.json" \
  --sparql "$HERE/checks" \
  --engine sparql \
  --reasoner owlrl-only \
  --out-dir "$OUT/project" \
  --reports minimal \
  --fail-on never > "$OUT/project.log" 2>&1 || true

COMBINED="$OUT/all-findings.csv"
head -1 "$OUT/queries/full_results.csv" > "$COMBINED"
for pass in queries builtin project; do
  [ -f "$OUT/$pass/full_results.csv" ] && tail -n +2 "$OUT/$pass/full_results.csv" >> "$COMBINED"
done

TOTAL=$(($(wc -l < "$COMBINED") - 1))
echo
echo "AGGREGATE -- $(ls "$HERE"/ontologies/*.ttl | wc -l) ontology files, \
$(ls "$HERE"/queries/*.rq | wc -l) mappings, $(ls "$HERE"/data/*.ttl | wc -l) output graphs"
echo

for sev in Violation Warning Info; do
  N=$(cut -d, -f1,4 "$COMBINED" | grep -c ",$sev$" || true)
  printf '  %-10s %3d\n' "$sev" "$N"
done
printf '  %-10s %3d\n' "TOTAL" "$TOTAL"
echo

printf '  %-10s %4s  %-28s %s\n' "CHECK" "N" "SUBJECTS" "FILES"
tail -n +2 "$COMBINED" | cut -d, -f1 | sort | uniq -c | sort -rn | while read -r n id; do
  SUBJECTS=$(tail -n +2 "$COMBINED" | awk -F, -v id="$id" '$1==id {print $5}' \
             | sed 's|.*[/#]||' | sort -u | head -3 | paste -sd, -)

  # Which input file each finding is about. The suite reports a focus node,
  # not a path, so this looks the node up -- and the answer is only ever as
  # exact as the node is.
  #
  # A full IRI (a data subject, say <.../site-S1>) appears in the file that
  # wrote it and nowhere else, so that match is the file. A term written as
  # a prefixed name in every file that mentions it (:Site) cannot be located
  # this way at all: in a merged project it genuinely lives in many files,
  # and naming three of them alphabetically would be a guess wearing the
  # clothes of an answer. Those say how many instead.
  FILES=$(tail -n +2 "$COMBINED" | awk -F, -v id="$id" '$1==id {print $5}' | sort -u \
          | while read -r node; do
              case "$node" in http*) ;; *) continue ;; esac
              grep -rlF -- "$node" "$HERE"/ontologies "$HERE"/queries "$HERE"/data 2>/dev/null \
                | sed 's|.*/||' || true
            done | sort -u | head -3 | paste -sd, - || true)
  if [ -z "$FILES" ]; then
    SPREAD=$(tail -n +2 "$COMBINED" | awk -F, -v id="$id" '$1==id {print $5}' | sort -u \
             | while read -r node; do
                 [ -n "$node" ] || continue
                 grep -rl -- "${node##*[/#]}" "$HERE"/ontologies "$HERE"/queries "$HERE"/data \
                   2>/dev/null | sed 's|.*/||' || true
               done | sort -u | wc -l || true)
    FILES="(prefixed name, in $SPREAD files)"
  fi
  printf '  %-10s %4d  %-28s %s\n' "$id" "$n" "$SUBJECTS" "$FILES"
done

if [ "${1:-}" = "--detail" ]; then
  echo
  echo "--- every finding ---"
  tail -n +2 "$COMBINED" | cut -d, -f1,4,5 | sort
fi

echo
echo "  Findings: $COMBINED"
echo "  Per pass: $OUT/{queries,builtin,project}/findings.txt"
