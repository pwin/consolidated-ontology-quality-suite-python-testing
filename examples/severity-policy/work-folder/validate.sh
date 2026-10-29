#!/usr/bin/env bash
# The same ontology gated two ways, from two committed configs:
#
#   ontology-suite.yml          the defaults -- the severities the checks declare
#   ontology-suite-release.yml  the same checks read at release stringency
#
#   bash examples/severity-policy/work-folder/validate.sh
#
# Each gate exits non-zero when anything reaches its --fail-on, so either
# works unchanged in CI. This script reports both and exits non-zero if
# either did, so it can be run as one step while still showing the contrast.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"

cd "$REPO"

echo "== gate 1: the defaults"
uv run python gate.py --config "$HERE/ontology-suite.yml"
defaults=$?
echo

echo "== gate 2: release stringency"
# Two extra lines in the config, no other difference. No copy of the suite's
# checks is made for this: the policy is applied to the findings.
uv run python gate.py --config "$HERE/ontology-suite-release.yml"
release=$?
echo

echo "defaults gate exit $defaults, release gate exit $release"
[ "$defaults" -eq 0 ] && [ "$release" -eq 0 ] && exit 0
exit 1
