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

# The suite can run its SHACL shapes through pyshacl (the default) or through
# the `shacl` package installed by its optional native-shacl extra. Suite
# 0.14.4 pinned that package to <0.4 because 0.3.0 changed the default meaning
# of sh:conforms, which is exactly the kind of change a parity test should
# notice, so tests/test_detection.py runs both formulations over every fixture
# whose stage accepts an --engine and compares what they report.
NATIVE_ENGINE = "native+sparql"
ENGINE_STAGES = ("checks", "data")


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
        # Severity ceiling: tightened from Warning. The control's whole job is that a
        # correct ontology produces nothing but Info, and a Warning ceiling let one through
        # unnoticed.
        max_severity="Info",
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
        # False-positive guard: its header is complete, its literals are well formed and it
        # declares no disjointness -- only the two misspelled IRIs are wrong.
        forbidden=("QUA-005", "DAT-001", "LOG-001"),
    ),
    Fixture(
        name="03-disjoint-classes",
        stage="data",
        ontology="03-disjoint-classes/ontology.ttl",
        data="03-disjoint-classes/data.ttl",
        seeded_errors="class disjoint with its own superclass; individual typed with two disjoint classes",
        expected=("LOG-001", "REA-001"),
        dl_only=("REA-020",),
        # False-positive guard: the contradiction is logical; nothing here is misspelled,
        # badly named or missing metadata.
        forbidden=("DAT-001", "STY-001", "QUA-005"),
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
        # False-positive guard: the same ontology with no data at all. REA-001 needs an
        # individual and the CNF-* layer needs a data graph, so either firing would mean
        # data came from somewhere.
        forbidden=("REA-001", "CNF-001", "CNF-002"),
    ),
    Fixture(
        name="04-property-axioms",
        stage="data",
        ontology="04-property-axioms/ontology.ttl",
        data="04-property-axioms/data.ttl",
        seeded_errors="functional property with two values; two inverses; self-inverse; symmetric and transitive properties with domain != range",
        expected=("LOG-002", "LOG-004", "LOG-005", "LOG-006", "LOG-007"),
        # False-positive guard: odd axioms, but consistent ones. An external reasoner
        # calling this ontology inconsistent, or a class unsatisfiable, would be wrong.
        forbidden=("REA-020", "REA-021", "DAT-001"),
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
        # False-positive guard: no functional property, nothing unsatisfiable and no
        # ill-formed literal -- the seeded errors are asymmetry and irreflexivity.
        forbidden=("LOG-002", "REA-004", "DAT-001"),
    ),
    Fixture(
        name="06-datatype-conformance",
        stage="data",
        ontology="06-datatype-conformance/ontology.ttl",
        data="06-datatype-conformance/data.ttl",
        seeded_errors="ill-formed xsd:date/integer/boolean literals; rdfs:domain and rdfs:range violations",
        # REA-022 is deliberately not here, and the reason is worth keeping.
        # It does fire on this fixture, reproducibly and on any machine: the
        # seeded ill-formed literals defeat owlready2's RDF/XML parser --
        # int("twelve") -- before HermiT is ever reached, so the suite reports
        # "external DL reasoner could not be run". That is a *consequence* of
        # the seeded defect, not a detection of it, and `expected` means "these
        # must trigger". Listing it there also broke the fast path documented in
        # COMMANDS.md: under OWL2_TEST_REASONER=owlrl-only the reasoner is never
        # attempted, so REA-022 cannot appear and the fixture failed.
        #
        # It cannot move to `dl_only` either, since `dl_reasoner_ran()` is
        # defined as REA-022 being absent, so the assertion would skip itself.
        # Both halves are pinned as their own tests instead:
        # test_datatype_errors_are_found_whatever_the_reasoner, and
        # test_ill_formed_literals_defeat_the_external_reasoner.
        expected=("DAT-001", "CNF-003", "CNF-004"),
        # False-positive guard: every term it uses is declared; the defects are in the
        # literals.
        forbidden=("STR-001", "STR-002", "LOG-001"),
    ),
    Fixture(
        name="07-naming-style",
        stage="checks",
        ontology="07-naming-style/ontology.ttl",
        seeded_errors="snake_case class, hyphenated class, Upper_Snake property, untagged label, prefLabel drifted from local name, deprecated term still used",
        expected=("STY-001", "STY-002", "STY-003", "STY-004", "STY-005", "QUA-001", "QUA-003"),
        # False-positive guard: every term it uses, including skos:prefLabel, is declared
        # locally. STR-002 is here by history: it fired on this fixture's prefLabel until
        # 0.6.0 (README, 'Issues found' #2), which is what a guard is for.
        forbidden=("STR-001", "STR-002", "CNF-001"),
        # Severity ceiling: the sharpest one in the table, because this is the fixture the
        # pre-0.6.0 severity defect actually fired on -- pyshacl reported STY-001 and
        # STY-003 as Violations, so a class named person_record failed a CI gate as hard
        # as a logical contradiction (README, 'Issues found' #1). Naming and documentation
        # are advice.
        max_severity="Warning",
    ),
    Fixture(
        name="08a-no-version-metadata",
        stage="checks",
        ontology="08-metadata/no-version-metadata.ttl",
        seeded_errors="ontology header with no version/title metadata, no owl:versionIRI, http:// IRI",
        expected=("QUA-002", "QUA-007", "QUA-008"),
        # False-positive guard: it has an ontology IRI and does not reuse it as the concept
        # namespace. Missing metadata is advice, never a gate.
        forbidden=("QUA-005", "QUA-006"),
        # Severity ceiling: it has an ontology IRI and does not reuse it as the concept
        # namespace. Missing metadata is advice, never a gate.
        max_severity="Warning",
    ),
    Fixture(
        name="08b-no-ontology-header",
        stage="checks",
        ontology="08-metadata/no-ontology-header.ttl",
        seeded_errors="no owl:Ontology declaration at all",
        expected=("QUA-005",),
        # False-positive guard: with no owl:Ontology node there is no version, versionIRI or
        # IRI scheme to have an opinion about, so reporting one would mean the check had
        # invented its subject.
        forbidden=("QUA-002", "QUA-007", "QUA-008"),
        # Severity ceiling: with no owl:Ontology node there is no version, versionIRI or IRI
        # scheme to have an opinion about, so reporting one would mean the check had
        # invented its subject.
        max_severity="Warning",
    ),
    Fixture(
        name="08c-ontology-iri-reused",
        stage="checks",
        ontology="08-metadata/ontology-iri-reused.ttl",
        seeded_errors="ontology IRI reused verbatim as the concept namespace IRI",
        expected=("QUA-006",),
        # False-positive guard: its header is complete apart from the one defect, the reused
        # namespace.
        forbidden=("QUA-002", "QUA-005", "QUA-007"),
        # Severity ceiling: its header is complete apart from the one defect, the reused
        # namespace.
        max_severity="Warning",
    ),
    Fixture(
        name="09-profile-violations",
        stage="ontology",
        ontology="09-profile-violations/ontology.ttl",
        seeded_errors="unionOf, complementOf, allValuesFrom, minCardinality 4, transitive and functional properties",
        expected=("REA-010", "REA-011", "REA-012"),
        profiles=("EL", "QL", "RL"),
        # False-positive guard: exceeding a profile is not an inconsistency. If this ever
        # fails a build, the suite has started treating OWL2 DL as an error.
        forbidden=("REA-020", "REA-021", "LOG-001"),
        # Severity ceiling: exceeding a profile is not an inconsistency. If this ever fails
        # a build, the suite has started treating OWL2 DL as an error.
        max_severity="Info",
    ),
    Fixture(
        name="11-schema-gaps",
        stage="data",
        ontology="11-schema-gaps/ontology.ttl",
        data="11-schema-gaps/data.ttl",
        seeded_errors="redundant equivalentClass+subClassOf; property with no domain or range; "
                      "domain and range IRIs never declared; an untyped subject and an "
                      "untyped, never-declared object",
        expected=("LOG-003", "STR-003", "STR-005", "STR-006", "STR-008", "STR-009",
                  "DAT-002"),
        # False-positive guard: gaps in the schema, not contradictions in it.
        forbidden=("REA-004", "LOG-001", "DAT-001"),
    ),
    Fixture(
        # Back on the `data` stage since suite 0.14.3 fixed the crash this
        # fixture's language-tagged literals used to cause (README.md, "Issues
        # found" #5). The tagged :note value is now reported as the CNF-004
        # range violation it is -- rdf:langString does not satisfy xsd:string.
        name="12-literal-volume",
        stage="data",
        ontology="12-literal-volume/ontology.ttl",
        data="12-literal-volume/data.ttl",
        seeded_errors="60 values on one subject-predicate pair; the same lexical form twice under "
                      "two language tags",
        expected=("EFF-003", "DAT-003", "CNF-004"),
        # False-positive guard: its names follow the conventions; the defects are volume and
        # duplication.
        forbidden=("STY-001", "STY-002", "LOG-001"),
    ),
    Fixture(
        name="13-unsatisfiable-class",
        stage="data",
        ontology="13-unsatisfiable-class/ontology.ttl",
        data="13-unsatisfiable-class/data.ttl",
        seeded_errors="an individual typed with a class declared rdfs:subClassOf owl:Nothing",
        expected=("REA-004",),
        dl_only=("REA-020",),
        # False-positive guard: the class is subClassOf owl:Nothing, not disjoint with an
        # ancestor, and no individual is in two disjoint classes. Telling those three apart
        # is what the fixture is for.
        forbidden=("LOG-001", "REA-001"),
    ),
    Fixture(
        name="10-efficiency",
        stage="checks",
        ontology="10-efficiency/ontology.ttl",
        seeded_errors="6-hop subClassOf chain; blank nodes over 20% of all graph nodes",
        expected=("EFF-001", "EFF-002"),
        # False-positive guard: shape advice about an ontology with no data attached.
        # Efficiency findings must not gate a build, which is what the ceiling pins.
        forbidden=("LOG-001", "DAT-001", "CNF-001"),
        # Severity ceiling: shape advice about an ontology with no data attached. Efficiency
        # findings must not gate a build, which is what the ceiling pins.
        max_severity="Warning",
    ),
]

FIXTURES_BY_NAME = {f.name: f for f in FIXTURES}


@lru_cache(maxsize=1)
def _registry() -> Registry:
    return Registry.load(config.DEFAULT_REGISTRY_PATH)


@lru_cache(maxsize=None)
def run_fixture(name: str, engine: str = "both", reasoner: Optional[str] = None) -> tuple:
    """Run one fixture through its stage and return its findings.

    Cached, so a pytest run that asserts several things about the same
    fixture only pays for one suite pass.

    ``engine`` picks the formulation of the registry-driven suite: the default
    ``both`` is pyshacl plus the portable SPARQL layer, and ``native+sparql``
    swaps pyshacl for the `shacl` package the suite's ``native-shacl`` extra
    installs. ``reasoner`` overrides the module default, which the engine
    comparison uses to hold the reasoner fixed -- it is not the variable under
    test, and HermiT is slow enough to matter when every fixture runs twice.
    The ``ontology`` stage takes neither: it has no SHACL formulation to swap.
    """
    fx = FIXTURES_BY_NAME[name]
    reasoner = reasoner or REASONER
    suffix = "" if (engine == "both" and reasoner == REASONER) else "-{}-{}".format(
        engine.replace("+", "-"), reasoner)
    out_dir = OUT_DIR / (name + suffix)
    registry = _registry()

    if fx.stage == "data":
        stage = pipeline.run_data_stage(
            [str(fx.data_path)], out_dir,
            ontology_path=str(fx.ontology_path), registry=registry, reasoner=reasoner,
            engine=engine,
        )
    elif fx.stage == "checks":
        stage = pipeline.run_checks_stage(
            registry, out_dir, ontology_path=str(fx.ontology_path),
            data_path=str(fx.data_path) if fx.data else None, engine=engine)
    elif fx.stage == "ontology":
        stage = pipeline.run_ontology_stage(
            str(fx.ontology_path), out_dir,
            registry=registry, reasoner=reasoner, profiles=tuple(fx.profiles),
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
