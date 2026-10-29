#!/usr/bin/env bash
# Evaluate one ontology four ways: the defaults, then each stage of the
# policy repo's file. Then print the comparison.
#
#   bash examples/severity-policy/work-folder/compare.sh
#
# Run it from anywhere: every path below is derived from this file. Unlike
# validate.sh this never fails the build -- it is here to show the difference
# between the readings, so it uses --fail-on never and compares afterwards.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
POLICY="$HERE/../policy-repo/severities.json"

cd "$REPO"

if ! uv run ontology-quality-suite checks --help 2>&1 | grep -q -- "--severity-policy"; then
  echo "This example needs --severity-policy, which the installed suite does"
  echo "not have. It is not in a release yet -- it is on the suite repo's"
  echo "'severity-policy' branch. See the README's 'What this needs'."
  exit 1
fi

run() {
  local name="$1"; shift
  echo "== $name"
  uv run ontology-quality-suite checks \
    --ontology "$HERE/myOntology.ttl" \
    --out-dir "$HERE/out/$name" \
    --engine both \
    --own-namespace https://example.org/mine \
    --fail-on never \
    "$@" 2>&1 | grep -E "Severity policy|^  [A-Z]{3}-|Findings:"
  echo
}

# The baseline. No policy flag at all -- this is what the checks say.
run defaults

# The same checks, three readings. Nothing is copied or rewritten between
# these runs; only the stage name changes.
for stage in sketch draft release; do
  run "$stage" --severity-policy "$POLICY" --stringency "$stage"
done

uv run python "$HERE/compare.py"
