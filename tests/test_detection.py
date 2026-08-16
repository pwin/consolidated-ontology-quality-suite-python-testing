"""Assert that the suite detects the errors seeded into each fixture."""
from __future__ import annotations

import pytest

import detect
from detect import FIXTURES, dl_reasoner_ran, ids_of, run_fixture, severity_breach

FIXTURE_NAMES = [f.name for f in FIXTURES]


def _rows(name):
    return run_fixture(name)


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_expected_checks_fire(name):
    """Every check id the fixture's seeded errors should trigger does."""
    fx = detect.FIXTURES_BY_NAME[name]
    if not fx.expected:
        pytest.skip(f"{name} has no positive expectations (control fixture)")
    found = ids_of(_rows(name))
    missing = sorted(set(fx.expected) - found)
    assert not missing, (
        f"{name}: suite did not report {missing}\n"
        f"  seeded errors: {fx.seeded_errors}\n"
        f"  reported instead: {sorted(found)}"
    )


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_forbidden_checks_do_not_fire(name):
    """False-positive guard: ids that must not be reported for this fixture."""
    fx = detect.FIXTURES_BY_NAME[name]
    if not fx.forbidden:
        pytest.skip(f"{name} declares no forbidden ids")
    found = ids_of(_rows(name))
    unexpected = sorted(set(fx.forbidden) & found)
    assert not unexpected, f"{name}: false positives reported: {unexpected}"


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_severity_ceiling(name):
    """The clean control must not produce any Violation-severity finding."""
    fx = detect.FIXTURES_BY_NAME[name]
    if not fx.max_severity:
        pytest.skip(f"{name} declares no severity ceiling")
    breaches = severity_breach(_rows(name), fx.max_severity)
    assert not breaches, (
        f"{name}: findings stricter than {fx.max_severity}: "
        + ", ".join(f"{r.check_id} on {r.focus_node} -- {r.message}" for r in breaches)
    )


@pytest.mark.parametrize("name", [f.name for f in FIXTURES if f.dl_only])
def test_dl_reasoner_findings(name):
    """Findings only a full OWL2 DL reasoner can produce -- skipped when the
    optional external reasoner (owlready2 + Java) is unavailable."""
    fx = detect.FIXTURES_BY_NAME[name]
    rows = _rows(name)
    if not dl_reasoner_ran(rows):
        pytest.skip("external DL reasoner unavailable (REA-022 reported)")
    missing = sorted(set(fx.dl_only) - ids_of(rows))
    assert not missing, f"{name}: DL reasoner ran but did not report {missing}"


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_reported_severity_matches_registry(name):
    """Every finding carries the severity registry.json declares for its check,
    whichever engine produced it. Regression guard for the pre-0.6.0 bug where
    pyshacl reported every finding as a Violation."""
    mismatches = detect.severity_mismatches(_rows(name))
    assert not mismatches, (
        f"{name}: reported severity differs from the registry default: "
        + "; ".join(f"{cid} registry={default} reported={got} via {src}"
                    for cid, default, got, src in mismatches)
    )


def test_every_fixture_file_exists():
    for fx in FIXTURES:
        assert fx.ontology_path.is_file(), f"{fx.name}: missing {fx.ontology_path}"
        if fx.data:
            assert fx.data_path.is_file(), f"{fx.name}: missing {fx.data_path}"
