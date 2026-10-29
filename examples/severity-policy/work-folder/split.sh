#!/usr/bin/env bash
# One file per stringency, instead of one file with three stages.
#
#   bash examples/severity-policy/work-folder/split.sh
#
# Runs each of policy-repo/severities-{sketch,draft,release}.json, runs the
# matching stage of the nested severities-by-stage.json, and compares the two
# readings finding by finding. They are the same policy written two ways, and
# the point of this script is that the reports prove it rather than the README
# asserting it.
#
# It ends with the one thing the split arrangement gains: because each file
# names its stage, wiring the wrong file to a gate is refused instead of
# quietly applying the wrong reading.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
POLICY="$HERE/../policy-repo"

cd "$REPO"

if ! uv run ontology-quality-suite checks --help 2>&1 | grep -q -- "--severity-policy"; then
  echo "This example needs --severity-policy, which the installed suite does"
  echo "not have. It arrived in suite 0.25.0; this install is older."
  exit 1
fi

run() {
  local out="$1" quiet="$2"; shift 2
  uv run ontology-quality-suite checks \
    --ontology "$HERE/myOntology.ttl" \
    --out-dir "$HERE/out/$out" \
    --engine both \
    --own-namespace https://example.org/mine \
    --fail-on never \
    "$@" 2>&1 | if [ "$quiet" = quiet ]; then cat > /dev/null; else
      grep -E "Severity policy|^  [A-Z]{3}-|Findings:"
    fi
}

# Both arrangements of the same policy, per stage. Only the file differs.
same_rows() {
  uv run python - "$1" "$2" <<'PY'
import csv, sys

def rows(path):
    """Every finding, reduced to what a severity policy can change.

    Paths and timings differ between two runs and are not part of the
    reading, so they are left out; declared_severity is in, because a
    policy that moved a finding has to say so there.
    """
    with open(path, encoding="utf-8") as handle:
        return sorted(
            (r["check_id"], r["focus_node"], r["severity"], r["declared_severity"])
            for r in csv.DictReader(handle)
        )

first, second = (rows(path) for path in sys.argv[1:3])
print("identical" if first == second else "DIFFERENT")
sys.exit(0 if first == second else 1)
PY
}

status=0
for stage in sketch draft release; do
  echo "== $stage, from severities-$stage.json"
  run "split-$stage" loud \
    --severity-policy "$POLICY/severities-$stage.json" --stringency "$stage"
  run "nested-$stage" quiet \
    --severity-policy "$POLICY/severities-by-stage.json" --stringency "$stage"
  verdict="$(same_rows "$HERE/out/nested-$stage/full_results.csv" \
                       "$HERE/out/split-$stage/full_results.csv")" || status=1
  echo "   vs the nested file's '$stage' stage: $verdict"
  echo
done

# The split arrangement's one real advantage. The sketch file holds a stage
# called 'sketch' and nothing else, so a release gate pointed at it cannot
# run at all -- whereas a flat, unnamed file would have applied the sketch
# reading and exited 0.
echo "== the wrong file, wired to a release gate"
uv run ontology-quality-suite checks \
  --ontology "$HERE/myOntology.ttl" --out-dir "$HERE/out/scratch" \
  --engine both --own-namespace https://example.org/mine --fail-on never \
  --severity-policy "$POLICY/severities-sketch.json" --stringency release 2>&1 | tail -1
echo "   (exit 2, nothing written)"
echo

[ "$status" -eq 0 ] && echo "Both arrangements agree on every finding, at every stage."
exit "$status"
