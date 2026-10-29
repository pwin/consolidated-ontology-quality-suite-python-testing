#!/usr/bin/env bash
# Evaluate myOntology.ttl with the severities the policy repo asks for.
#
#   bash examples/severity-policy/work-folder/validate.sh
#
# Exits non-zero if anything reaches Violation, so it works unchanged as a CI
# gate. Run it from anywhere: every path below is derived from this file.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"

cd "$REPO"

echo "== step 1: apply the policy repo's severities to a copy of the checks"
# Must come first: ontology-suite.yml points --registry, --sparql and
# --shapes at what this writes. It re-copies from the installed suite every
# run, so the assembled checks are always this install's -- and it refuses to
# finish if an override did not take or the config would undo it.
uv run python "$HERE/apply_severities.py"

echo
echo "== step 2: evaluate the ontology against them"
uv run python gate.py --config "$HERE/ontology-suite.yml"
