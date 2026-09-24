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


ENGINE_FIXTURE_NAMES = [f.name for f in FIXTURES if f.stage in detect.ENGINE_STAGES]


@pytest.mark.parametrize("name", ENGINE_FIXTURE_NAMES)
def test_native_shacl_engine_reports_what_pyshacl_does(name):
    """The two SHACL implementations report the same checks at the same
    severities.

    `--engine native` runs the registry's shapes through the `shacl` package
    instead of pyshacl. The shapes, the registry and the fixture are identical
    across the two runs, so any difference is the implementation's -- which is
    a live risk rather than a hypothetical one: suite 0.14.4 pinned that
    package to <0.4 because 0.3.0 changed the default meaning of sh:conforms.

    Skipped when the optional extra is absent. Both sides hold the reasoner at
    owlrl-only: REA-* findings come from the reasoning layer, not from either
    SHACL engine, and pinning it keeps the comparison to the one variable (and
    the run fast enough to double).
    """
    pytest.importorskip(
        "shacl", reason="the suite's native-shacl extra is not installed")
    baseline = run_fixture(name, engine="both", reasoner="owlrl-only")
    native = run_fixture(name, engine=detect.NATIVE_ENGINE, reasoner="owlrl-only")

    only_pyshacl = sorted(ids_of(baseline) - ids_of(native))
    only_native = sorted(ids_of(native) - ids_of(baseline))
    assert not only_pyshacl and not only_native, (
        f"{name}: engines disagree -- pyshacl only: {only_pyshacl}, "
        f"native only: {only_native}")

    mismatches = detect.severity_mismatches(native)
    assert not mismatches, (
        f"{name}: native engine severity differs from the registry default: "
        + "; ".join(f"{cid} registry={default} reported={got} via {src}"
                    for cid, default, got, src in mismatches))


def test_every_fixture_file_exists():
    for fx in FIXTURES:
        assert fx.ontology_path.is_file(), f"{fx.name}: missing {fx.ontology_path}"
        if fx.data:
            assert fx.data_path.is_file(), f"{fx.name}: missing {fx.data_path}"


@pytest.mark.parametrize("reasoner", ["auto", "owlrl-only"])
def test_datatype_errors_are_found_whatever_the_reasoner(reasoner):
    """06's seeded errors are ill-formed literals and domain/range violations.
    Not one of them needs a DL reasoner, so the same ids must be reported with
    or without one.

    This replaces an expectation of `REA-022` on that fixture. REA-022 means
    "external DL reasoner unavailable", so expecting it asserted something
    about the machine rather than about the ontology: it passed here only
    because this checkout has no working HermiT, failed under the fast path
    documented in COMMANDS.md, and would fail for anyone who installed Java.
    """
    rows = detect.run_fixture("06-datatype-conformance", engine="both", reasoner=reasoner)
    missing = {"DAT-001", "CNF-003", "CNF-004"} - ids_of(rows)
    assert not missing, f"reasoner={reasoner}: suite did not report {sorted(missing)}"


def test_ill_formed_literals_defeat_the_external_reasoner():
    """06's seeded literals stop the DL reasoner before HermiT is reached.

    `int("twelve")` raises inside owlready2's RDF/XML parser, so the suite
    reports REA-022 ("external DL reasoner could not be run") with the parse
    error in its message. Reproducible on any machine with a working reasoner
    -- fixture 13 gets REA-020 out of the same installation -- and it is why
    REA-022 is not one of 06's `expected` ids: it is what the defect *does* to
    the toolchain, not the suite detecting the defect.

    Pinned because it is the kind of interaction that otherwise gets
    rediscovered as a mystery: a check reporting its own unavailability looks
    like a broken environment until you notice which fixture provokes it.
    """
    if detect.REASONER in ("owlrl-only", "none"):
        pytest.skip("the external reasoner is not attempted, so it cannot report on itself")

    rows = detect.run_fixture("06-datatype-conformance", engine="both", reasoner="auto")
    unavailable = [r for r in rows if r.check_id == "REA-022"]
    assert unavailable, "expected REA-022 -- the ill-formed literals should stop owlready2"
    assert "could not be run" in unavailable[0].message

    # The same installation reasons successfully over a fixture whose literals
    # are well formed, which is what makes this the fixture's fault rather than
    # the machine's.
    healthy = detect.ids_of(detect.run_fixture("13-unsatisfiable-class", engine="both", reasoner="auto"))
    assert "REA-020" in healthy, "the reasoner must work elsewhere for this test to mean anything"
