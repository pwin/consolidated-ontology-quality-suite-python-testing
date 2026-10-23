"""Assert that the suite detects the errors seeded into each fixture."""
from __future__ import annotations

import re

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

#: Checks that both formulations find on these fixtures: the registry's SHACL
#: shape and its portable `.rq` twin each report them, and `checks/merge.py`
#: merges the two rows into one carrying `shacl+sparql`.
#:
#: 21 of the registry's 61 checks are written both ways (the shapes under
#: `resources/shapes/`, every one of which also has an `.rq`); the rest are
#: SPARQL only, so there is nothing to cross-validate them against. This set
#: is 20 of those 21 -- all but DAT-004, which no fixture here seeds and which
#: competency_tests/ pins instead. So it is not an arbitrary snapshot: it is
#: every doubly-written check these fixtures reach.
#:
#: Losing one arm is silent. If a shape stops firing, the `.rq` still reports
#: the check, the id still appears, the count is unchanged, and every other
#: assertion in this file passes -- the only trace is a row that used to say
#: `shacl+sparql` and now says `sparql`.
#:
#: A check moving *into* this set is fine and the assertion below allows it.
#: A check leaving it is the regression.
CROSS_VALIDATED = {
    "DAT-001", "DAT-002", "DAT-003",
    "EFF-001", "EFF-002", "EFF-003",
    "LOG-001", "LOG-002", "LOG-003",
    "QUA-001", "QUA-002", "QUA-003", "QUA-009", "QUA-010",
    "STR-001", "STR-002", "STR-003",
    "STY-001", "STY-002", "STY-003",
}

REGISTRY_ARMS = {"shacl", "sparql"}


def test_both_formulations_still_find_what_they_both_used_to():
    """Every check in CROSS_VALIDATED is still reported by both arms.

    What this replaces is worth recording. Until suite 0.22.0 the comparison
    here was `--engine both` against `--engine native+sparql`: pyshacl against
    the `shacl` package, two implementations of SHACL over identical inputs.
    That test cannot exist any more and had stopped meaning anything before it
    was noticed. pyshacl is no longer a runtime dependency of the suite -- it
    is in the suite's own dev group, for its parity tests -- so it is absent
    from an install like this one, and `pipeline.py` now says plainly that
    `both` and `native+sparql` "name the same two engines". The old test
    compared a configuration with itself and passed for that reason.

    The parity worth asserting from here is between the two *formulations*
    rather than two SHACL implementations: the shapes on the `shacl` engine,
    the `.rq` queries on holosdb. The suite cross-validates them against each
    other, which is the thing that quietly breaks.
    """
    found_by_both = set()
    for name in ENGINE_FIXTURE_NAMES:
        for row in run_fixture(name, engine="both", reasoner="owlrl-only"):
            if REGISTRY_ARMS <= set(row.sources):
                found_by_both.add(row.check_id)

    lost = sorted(CROSS_VALIDATED - found_by_both)
    assert not lost, (
        "these checks are no longer reported by both formulations: "
        + ", ".join(lost)
        + ". One arm has stopped firing. The check id still appears in the "
        "report, so nothing else here fails -- look at whether the shape or "
        "the .rq twin is the one that went quiet.")


@pytest.mark.parametrize("name", ENGINE_FIXTURE_NAMES)
def test_each_formulation_agrees_about_severity(name):
    """Neither arm reports a severity the registry does not declare.

    This is the defect these fixtures were built on, kept asserted because it
    was real: until suite 0.6.0 every finding from the SHACL arm came back
    `Violation` whatever the registry said, because the shapes declared
    `sh:severity` on the nested `sh:SPARQLConstraint` rather than on the shape
    node. README.md §1 records the evidence and
    experiments/severity_probe.py is what proved it.

    Asserted per arm rather than on the merged rows: merging two rows for one
    check has to settle on one severity, which would hide an arm that
    disagreed -- exactly the shape of the original bug.
    """
    for engine in ("shacl", "sparql"):
        mismatches = detect.severity_mismatches(
            run_fixture(name, engine=engine, reasoner="owlrl-only"))
        assert not mismatches, (
            f"{name}: --engine {engine} severity differs from the registry: "
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

#: rdflib and pyoxigraph both render a blank node as a long run of hex. Matching
#: the run itself rather than a prefix keeps this independent of which engine
#: produced it -- rdflib writes `n` then 32 hex digits, oxigraph writes its own.
BNODE_LABEL = re.compile(r"[0-9a-f]{24,}")


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_every_finding_carries_a_message(name):
    """A finding a reader cannot act on is barely a finding.

    Asserted under ``--engine sparql`` rather than the default ``both``, and
    that is the whole point: with both formulations running, `checks/merge.py`
    fills a missing message from whichever source has one, so a message the
    portable layer has stopped producing is invisible. STY-003 lost its message
    for every blank-node focus node -- 60 of 65 findings on the suite's own
    stress fixture -- and the check still fired at the right count and the right
    severity, so every other test in this file passed. The extension, which runs
    the portable queries through oxigraph with no SHACL layer to fall back on,
    shipped that gap to users.
    """
    rows = run_fixture(name, engine="sparql")
    empty = sorted(
        {f"{r.check_id} on {r.focus_node}" for r in rows if not (r.message or "").strip()}
    )
    assert not empty, (
        f"{name}: {len(empty)} finding(s) carry no message under --engine sparql\n"
        + "\n".join(f"    {e}" for e in empty[:10])
        + "\n  A CONSTRUCT template drops a triple whose variable is unbound, so an"
        "\n  expression that errors for some rows silently removes the message for"
        "\n  exactly those rows. STR() of a blank node is the usual cause: it is a"
        "\n  type error in SPARQL, so wrap it as IF(isBlank(?x), \"[a blank node]\","
        "\n  STR(?x))."
    )


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_no_message_names_an_internal_blank_node_identifier(name):
    """A message naming a blank node's internal label says nothing a reader can
    use, and says something different on every run.

    Scoped to ``--engine sparql`` because the SHACL twins cannot do better:
    `sh:message "A label on {$this} has no language tag."` substitutes the focus
    node, and SHACL has no conditional form of that substitution, so a
    blank-node focus node always renders as its identifier there. The portable
    SPARQL formulation *can* choose its own wording, so that is where the
    property is worth holding.
    """
    rows = run_fixture(name, engine="sparql")
    leaky = sorted(
        {
            f"{r.check_id}: {r.message[:70]}"
            for r in rows
            if r.message and BNODE_LABEL.search(r.message)
        }
    )
    assert not leaky, (
        f"{name}: {len(leaky)} message(s) name an internal blank node identifier\n"
        + "\n".join(f"    {e}" for e in leaky[:10])
        + "\n  Those identifiers differ between runs and between engines, so a report"
        "\n  built from them is not reproducible. Use IF(isBlank(?x),"
        "\n  \"[a blank node]\", STR(?x)) rather than STR(?x) or"
        "\n  COALESCE(STR(?x), ...) -- COALESCE only helps where STR() errors, and"
        "\n  rdflib returns the identifier instead of erroring."
    )
