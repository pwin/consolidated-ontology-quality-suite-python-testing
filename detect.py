"""Test harness: run the ontology quality suite over the deliberately broken
OWL2 fixtures in ``ontologies/`` and report which registry checks fired.

Each fixture in ``FIXTURES`` pins:

* ``stage``    -- which suite pipeline stage to run it through
                  (``checks`` = registry SHACL+SPARQL suite over the ontology
                  alone, ``data`` = ontology + instance data, which adds the
                  conformance and reasoning layers, ``ontology`` = the
                  as-authored evaluation, which is where OWL2 profile
                  membership is checked),
* ``expected`` -- the registry check ids the seeded errors *must* trigger,
* ``forbidden``-- ids that must NOT trigger (false-positive guards),
* ``dl_only``  -- ids only an external DL reasoner (HermiT via owlready2 +
                  Java) can produce; asserted only when that reasoner
                  actually ran, since it is an optional dependency.

The suite is imported as a library (``ontology_suite.pipeline``) rather than
shelled out to, so findings are compared as structured ``ResultRow`` objects
instead of scraped from a report.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Sequence

from ontology_suite import config, pipeline
from ontology_suite.checks.merge import ResultRow
from ontology_suite.checks.registry import Registry

ROOT = Path(__file__).resolve().parent
ONTOLOGIES = ROOT / "ontologies"
OUT_DIR = ROOT / "out"

# "auto" also runs HermiT through owlready2 when a Java runtime is present;
# OWL2_TEST_REASONER=owlrl-only skips it (faster, and REA-020/021 then go
# unasserted rather than failing).
REASONER = os.environ.get("OWL2_TEST_REASONER", "auto")

SEVERITY_ORDER = {"Violation": 0, "Warning": 1, "Info": 2}


@dataclass(frozen=True)
class Fixture:
    name: str
    stage: str
    ontology: str
    seeded_errors: str
    data: Optional[str] = None
    expected: Sequence[str] = field(default_factory=tuple)
    dl_only: Sequence[str] = field(default_factory=tuple)
    forbidden: Sequence[str] = field(default_factory=tuple)
    max_severity: Optional[str] = None  # strictest severity allowed to appear
    profiles: Sequence[str] = field(default_factory=tuple)

    @property
    def ontology_path(self) -> Path:
        return ONTOLOGIES / self.ontology

    @property
    def data_path(self) -> Optional[Path]:
        return ONTOLOGIES / self.data if self.data else None


FIXTURES: List[Fixture] = [
    Fixture(
        name="01-clean",
        stage="data",
        ontology="01-clean/ontology.ttl",
        data="01-clean/data.ttl",
        seeded_errors="none -- control fixture",
        # Nothing is logically or structurally wrong, so no Violation may be
        # reported. Warnings/Info (e.g. CNF-005 "class never populated") are
        # legitimate advisory output and are allowed.
        max_severity="Warning",
        forbidden=("STR-001", "STR-002", "STR-007", "LOG-001", "LOG-002",
                   "REA-001", "REA-002", "REA-003", "DAT-001",
                   "CNF-003", "CNF-004", "QUA-005"),
    ),
    Fixture(
        name="02-undeclared-terms",
        stage="data",
        ontology="02-undeclared-terms/ontology.ttl",
        data="02-undeclared-terms/data.ttl",
        seeded_errors="misspelled class IRI (:Persson) and property IRI (:hasNmae) in the data",
        expected=("STR-001", "STR-002", "STR-007", "CNF-001", "CNF-002"),
    ),
    Fixture(
        name="03-disjoint-classes",
        stage="data",
        ontology="03-disjoint-classes/ontology.ttl",
        data="03-disjoint-classes/data.ttl",
        seeded_errors="class disjoint with its own superclass; individual typed with two disjoint classes",
        expected=("LOG-001", "REA-001"),
        dl_only=("REA-020",),
    ),
    Fixture(
        name="03b-unsatisfiable-class",
        stage="ontology",
        ontology="03-disjoint-classes/ontology.ttl",
        seeded_errors="same ontology, no data: :Plant is unsatisfiable from the class axioms alone, with no individual asserted into the contradiction",
        expected=("LOG-001",),
        # No individual is asserted into the contradiction here, so only a
        # full DL reasoner can report the class-level unsatisfiability.
        dl_only=("REA-021",),
    ),
    Fixture(
        name="04-property-axioms",
        stage="data",
        ontology="04-property-axioms/ontology.ttl",
        data="04-property-axioms/data.ttl",
        seeded_errors="functional property with two values; two inverses; self-inverse; symmetric and transitive properties with domain != range",
        expected=("LOG-002", "LOG-004", "LOG-005", "LOG-006", "LOG-007"),
    ),
    Fixture(
        name="05-reasoning-violations",
        stage="data",
        ontology="05-reasoning-violations/ontology.ttl",
        data="05-reasoning-violations/data.ttl",
        seeded_errors="asymmetric property asserted both ways; irreflexive property asserted as a self-loop",
        expected=("REA-002", "REA-003"),
        # Both violations also make the graph inconsistent in full OWL2 DL.
        dl_only=("REA-020",),
    ),
    Fixture(
        name="06-datatype-conformance",
        stage="data",
        ontology="06-datatype-conformance/ontology.ttl",
        data="06-datatype-conformance/data.ttl",
        seeded_errors="ill-formed xsd:date/integer/boolean literals; rdfs:domain and rdfs:range violations",
        expected=("DAT-001", "CNF-003", "CNF-004"),
    ),
    Fixture(
        name="07-naming-style",
        stage="checks",
        ontology="07-naming-style/ontology.ttl",
        seeded_errors="snake_case class, hyphenated class, Upper_Snake property, untagged label, deprecated term still used",
        expected=("STY-001", "STY-002", "STY-003", "STY-005", "QUA-001", "QUA-003"),
    ),
    Fixture(
        name="08a-no-version-metadata",
        stage="checks",
        ontology="08-metadata/no-version-metadata.ttl",
        seeded_errors="ontology header with no version/title metadata, no owl:versionIRI, http:// IRI",
        expected=("QUA-002", "QUA-007", "QUA-008"),
        forbidden=("QUA-005",),
    ),
    Fixture(
        name="08b-no-ontology-header",
        stage="checks",
        ontology="08-metadata/no-ontology-header.ttl",
        seeded_errors="no owl:Ontology declaration at all",
        expected=("QUA-005",),
        forbidden=("QUA-002", "QUA-007"),
    ),
    Fixture(
        name="08c-ontology-iri-reused",
        stage="checks",
        ontology="08-metadata/ontology-iri-reused.ttl",
        seeded_errors="ontology IRI reused verbatim as the concept namespace IRI",
        expected=("QUA-006",),
    ),
    Fixture(
        name="09-profile-violations",
        stage="ontology",
        ontology="09-profile-violations/ontology.ttl",
        seeded_errors="unionOf, complementOf, allValuesFrom, minCardinality 4, transitive and functional properties",
        expected=("REA-010", "REA-011", "REA-012"),
        profiles=("EL", "QL", "RL"),
    ),
    Fixture(
        name="10-efficiency",
        stage="checks",
        ontology="10-efficiency/ontology.ttl",
        seeded_errors="6-hop subClassOf chain; blank nodes over 20% of all graph nodes",
        expected=("EFF-001", "EFF-002"),
    ),
]

FIXTURES_BY_NAME = {f.name: f for f in FIXTURES}


@lru_cache(maxsize=1)
def _registry() -> Registry:
    return Registry.load(config.DEFAULT_REGISTRY_PATH)


@lru_cache(maxsize=None)
def run_fixture(name: str) -> tuple:
    """Run one fixture through its stage and return its findings.

    Cached, so a pytest run that asserts several things about the same
    fixture only pays for one suite pass.
    """
    fx = FIXTURES_BY_NAME[name]
    out_dir = OUT_DIR / name
    registry = _registry()

    if fx.stage == "data":
        stage = pipeline.run_data_stage(
            [str(fx.data_path)], out_dir,
            ontology_path=str(fx.ontology_path), registry=registry, reasoner=REASONER,
        )
    elif fx.stage == "checks":
        stage = pipeline.run_checks_stage(registry, out_dir, ontology_path=str(fx.ontology_path))
    elif fx.stage == "ontology":
        stage = pipeline.run_ontology_stage(
            str(fx.ontology_path), out_dir,
            registry=registry, reasoner=REASONER, profiles=tuple(fx.profiles),
        )
    else:  # pragma: no cover - guarded by the fixture table itself
        raise ValueError(f"unknown stage {fx.stage!r} for fixture {name}")

    return tuple(stage.rows)


def severity_mismatches(rows: Sequence[ResultRow]) -> List[tuple]:
    """Findings whose reported severity disagrees with the registry's
    ``default_severity`` for that check.

    Until suite 0.6.0 every pyshacl-sourced row came back ``Violation``
    regardless (see README.md, "Issues found"), so this stays asserted as a
    regression guard."""
    out = []
    for row in rows:
        check = _registry().get(row.check_id)
        if check and row.severity != check.default_severity:
            out.append((row.check_id, check.default_severity, row.severity, "+".join(row.sources)))
    return sorted(set(out))


def check_title(check_id: str) -> str:
    check = _registry().get(check_id)
    return check.title if check else ""


def ids_of(rows: Sequence[ResultRow]) -> set:
    return {r.check_id for r in rows}


def dl_reasoner_ran(rows: Sequence[ResultRow]) -> bool:
    """REA-022 is emitted whenever the external DL reasoner could not run
    (owlready2 missing, no Java, or the reasoner itself erroring out). With
    OWL2_TEST_REASONER=owlrl-only/none it is never even attempted, and no
    REA-022 row is produced either -- so check the setting first."""
    if REASONER in ("owlrl-only", "none"):
        return False
    return "REA-022" not in ids_of(rows)


def severity_breach(rows: Sequence[ResultRow], max_severity: str) -> List[ResultRow]:
    limit = SEVERITY_ORDER[max_severity]
    return [r for r in rows if SEVERITY_ORDER[r.severity] < limit]
