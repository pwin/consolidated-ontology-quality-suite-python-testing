"""The 28 competency tests, as pass/fail assertions.

One suite run backs the whole module: triplifying the fixtures and running
every stage takes about a minute, and every test here asks a question of the
same findings.
"""
from __future__ import annotations

import pytest

import competency
import run_competency_checks as runner


@pytest.fixture(scope="module")
def evaluated():
    runs = runner.run_everything()
    return {"runs": {run.key: run for run in runs}, "results": runner.evaluate(runs)}


@pytest.mark.parametrize("number", sorted(competency.COVERAGE_BY_NUMBER))
def test_competency_test_is_evidenced(evaluated, number):
    """Each competency test's seeded defect is reported by the check that
    covers it, in the run that covers it."""
    definition, cover, observed, missing = next(
        entry for entry in evaluated["results"] if entry[0].number == number)
    assert not missing, (
        "CT-{} ({}) has no evidence for {}\n  covered by: {}\n  seeded in: {}".format(
            number, definition.issue,
            ", ".join("{} in run {}".format(check_id, run_key) for run_key, check_id in missing),
            cover.kind, ", ".join(cover.fixtures)))
    assert observed


def test_every_definition_has_coverage():
    """No competency test is silently left out of the coverage table."""
    definitions = competency.load_definitions()
    assert set(definitions) == set(competency.COVERAGE_BY_NUMBER)
    assert sorted(definitions) == list(range(1, 29))


def test_project_checks_all_execute(evaluated):
    """A project-local .rq that fails to parse reports nothing and would look
    exactly like a clean result."""
    for run_key in ("project-output", "project-sketch", "completeness"):
        assert run_key in evaluated["runs"]
    reported = set()
    for run in evaluated["runs"].values():
        reported |= {row.check_id for row in run.rows}
    declared = {check["id"] for check in
                __import__("json").loads(runner.PROJECT_REGISTRY.read_text(encoding="utf-8"))["checks"]}
    silent = sorted(declared - reported)
    assert not silent, "project-local checks that produced nothing at all: {}".format(silent)


def test_extension_only_checks_are_not_reported_by_the_cli(evaluated):
    """The three extension-only ids stay absent from every CLI run. If one
    starts appearing, the Python package has grown an implementation and the
    VS Code section of the coverage document is out of date."""
    reported = set()
    for run in evaluated["runs"].values():
        reported |= {row.check_id for row in run.rows}
    unexpected = sorted(set(competency.EXTENSION_ONLY_CHECKS) & reported)
    assert not unexpected, (
        "{} now reported by the CLI -- update COMPETENCY_COVERAGE.md's extension-only "
        "section".format(unexpected))
