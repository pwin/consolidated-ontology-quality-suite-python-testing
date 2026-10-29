#!/usr/bin/env bash
# Folder A's validation run: the suite's own checks and Folder B's house
# rules, in one pass, over Folder A's model and data.
#
#   bash examples/cross-folder-checks/folder-a-fleet-project/validate.sh
#
# Exits non-zero if anything reaches Violation, so it works unchanged as a CI
# gate. Run it from anywhere: every path below is derived from this file.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"

cd "$REPO"

echo "== step 1: assemble what the run needs from Folders B and C"
# Must come first: ontology-suite.yml points --registry and --shapes at the
# files this writes. Cheap and idempotent, so it belongs in the run rather
# than in a setup step someone can forget.
uv run python "$HERE/prepare_checks.py"

echo
echo "== step 2: validate Folder A with all three sets of checks"
# --config takes the path; everything inside it resolves against it.
uv run python gate.py --config "$HERE/ontology-suite.yml"
