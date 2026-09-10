"""The 28 competency tests, and how each one is answered.

``load_definitions()`` reads the five CSVs in this folder, so the issue text
stays owned by them rather than being copied here. ``COVERAGE`` adds, per
test, how it is checked and what evidence proves it: the check ids that must
appear, and which run they must appear in.

Coverage kinds:

    registry        a check shipped in the suite's own registry
    project-check   a project-local SPARQL check in checks/sparql/competency/
    suite-module    a suite module with no registry id (pattern-consistency,
                    version-diff, rename detection)
    harness         Python in this folder -- review_aids.py / mapping_integrity.py,
                    for questions that span two graphs or two artefacts
    extension-only  declared in registry.json, implemented only in the VS Code
                    extension; the CLI cannot report it
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

HERE = Path(__file__).resolve().parent

DEFINITION_FILES = {
    "cross-artifact consistency": "cross-artifact_consistency.csv",
    "completeness": "completeness.csv",
    "TARQL and mapping integrity": "tarql_and_mapping_integrity.csv",
    "magnitudes, values and units": "magnitudes_values_units.csv",
    "review aids": "review_aids.csv",
}


@dataclass(frozen=True)
class Definition:
    number: int
    category: str
    issue: str
    summary: str


@dataclass(frozen=True)
class Coverage:
    number: int
    kind: str
    """How to run it -- the command or call a person repeats."""
    how: str
    """(run key, check id) pairs that must be present for the test to pass."""
    evidence: Sequence[tuple] = field(default_factory=tuple)
    """Fixture files the seeded defect lives in."""
    fixtures: Sequence[str] = field(default_factory=tuple)
    notes: Optional[str] = None


def _clean(text: str) -> str:
    """Normalise a field read from the CSVs.

    They arrived spacing many words with U+00A0 NO-BREAK SPACE. Those have
    since been converted to ordinary spaces in the files themselves -- 122 of
    them -- because a tool that strips rather than converts them welds words
    together into text that still parses and still reads like prose
    ("ontology.Identify"), which happened here once already. The replace
    below is kept as a safeguard for anything re-imported from the same
    source, and is a no-op on the files as they now stand.
    """
    return text.replace(chr(0xA0), " ").strip()


def load_definitions() -> Dict[int, Definition]:
    """Read the issue/summary text from the five source CSVs."""
    out: Dict[int, Definition] = {}
    for category, filename in DEFINITION_FILES.items():
        with (HERE / filename).open(encoding="utf-8-sig", newline="") as handle:
            for record in csv.reader(handle):
                if not record or not record[0].strip().isdigit():
                    continue
                number = int(record[0].strip())
                issue = _clean(record[1]) if len(record) > 1 else ""
                summary = _clean(record[2]) if len(record) > 2 else ""
                out[number] = Definition(number, category, issue, summary)
    return out


COVERAGE: List[Coverage] = [
    Coverage(
        number=1, kind="registry + suite-module",
        how="ontology-quality-suite sketch --queries fixtures/model/queries --file-pattern '**/*.rq'\n"
            "ontology-quality-suite pattern-consistency --queries ... --ontology ... --taxonomy ...",
        evidence=(("sketch", "TQL-001"),),
        fixtures=("queries/assets/sites.rq", "queries/readings/readings.rq"),
        notes="TQL-001 compares BIND skeletons, so the same template fed by differently-named "
              "columns is not reported and a one-character divergence is. Namespace-level drift "
              "between a query's PREFIX block and the ontology is the prefix-alignment half of "
              "the same command.",
    ),
    Coverage(
        number=2, kind="project-check",
        how="CMP-002 over ontology + output data merged.",
        evidence=(("project-output", "CMP-002", "asset-A1"),),
        fixtures=("queries/assets/legacy_assets.rq",),
        notes="TQL-001 answers the query-text half of this question. CMP-002 answers it of the "
              "real output, where a collision built from differently-named columns still shows.",
    ),
    Coverage(
        number=3, kind="suite-module",
        how="ontology-quality-suite consistency --old water-v1.ttl --new water-v2.ttl --queries ...",
        evidence=(("consistency", "rename-detected", "PumpStation"),
                  ("consistency", "undeclared-term", "PumpStation")),
        fixtures=("ontology/water-v2.ttl", "queries/assets/assets.rq"),
        notes="Rename detection pairs the removed and added terms, and the repair layer emits the "
              "substitution as a reviewable .patch against the query file.",
    ),
    Coverage(
        number=4, kind="suite-module",
        how="ontology-quality-suite pattern-consistency --queries ... --ontology ... --taxonomy ... "
            "--output-data <triplified output>",
        evidence=(("pattern-consistency", "taxonomy-reference", "Resevoir"),
                  ("pattern-consistency", "taxonomy-membership", "Culvert")),
        fixtures=("queries/assets/legacy_assets.rq", "queries/assets/assets.rq", "csv/assets.csv"),
        notes="Two mechanisms, because a hard-coded reference and a per-row one are not findable "
              "the same way: the first is literal text in the query, the second only exists once "
              "the mapping has run.",
    ),
    Coverage(
        number=5, kind="registry + harness",
        how="TQL-001 across both domain folders, then review_aids.compare_predicates between the "
            "two domains' outputs.",
        evidence=(("sketch", "TQL-001"),),
        fixtures=("queries/assets/sites.rq", "queries/readings/readings.rq"),
        notes="The shared concept here is :Site. The assets domain mints its IRI one way and the "
              "readings domain another, so the two domains' data never joins.",
    ),
    Coverage(
        number=6, kind="suite-module + registry",
        how="ontology-quality-suite consistency --old ... --new ... --queries ...; and "
            "sketch --ontology water-v2.ttl for the CNF-001/002 view.",
        evidence=(("consistency", "undeclared-term", "PumpStation"),
                  ("sketch-v2", "CNF-001", "PumpStation"), ("sketch-v2", "CNF-002", "hasFlowRate")),
        fixtures=("queries/assets/assets.rq", "ontology/water-v2.ttl"),
    ),
    Coverage(
        number=7, kind="suite-module",
        how="ontology-quality-suite version-diff old new, run once per artefact pair, then compare "
            "the bump each reports.",
        evidence=(("version-diff", "major"),),
        fixtures=("ontology/water-v1.ttl", "ontology/water-v2.ttl"),
        notes="The ontology moved to 2.0.0 and the mappings did not move at all. Change is "
              "detected per artefact; noticing that only one artefact moved is the orchestration "
              "this harness adds.",
    ),
    Coverage(
        number=8, kind="registry",
        how="ontology-quality-suite checks --ontology fixtures/completeness/incomplete-model.ttl",
        evidence=(("completeness", "QUA-010"),),
        fixtures=("completeness/incomplete-model.ttl",),
        notes="QUA-010 asks for skos:definition specifically. STR-004 asks a different question -- "
              "whether the class is formally defined by an axiom -- and a term can satisfy one and "
              "fail the other.",
    ),
    Coverage(
        number=9, kind="project-check",
        how="CMP-009 over the ontology; STR-004 covers the weaker 'no defining axiom at all' case.",
        evidence=(("completeness", "CMP-009"), ("completeness", "STR-004")),
        fixtures=("completeness/incomplete-model.ttl",),
        notes="Imported vocabularies are excluded by namespace, which is the one line to edit per "
              "project.",
    ),
    Coverage(
        number=10, kind="registry",
        how="ontology-quality-suite checks --ontology fixtures/completeness/incomplete-model.ttl",
        evidence=(("completeness", "QUA-004", "Coupling"), ("completeness", "QUA-009", "Valve")),
        fixtures=("completeness/incomplete-model.ttl",),
        notes="QUA-004 accepts skos:prefLabel or rdfs:label; QUA-009 is the stricter form that "
              "requires a prefLabel specifically.",
    ),
    Coverage(
        number=11, kind="registry",
        how="ontology-quality-suite checks --ontology fixtures/completeness/incomplete-model.ttl",
        evidence=(("completeness", "QUA-009", "Pipe"),),
        fixtures=("completeness/incomplete-model.ttl",),
        notes="Per language, not one overall: the fixture's Welsh prefLabel is correct SKOS and is "
              "not reported. The two English ones are.",
    ),
    Coverage(
        number=12, kind="project-check",
        how="CMP-012 over the CONSTRUCT-template sketch graph (out/sketch/sketch.ttl).",
        evidence=(("project-sketch", "CMP-012"),),
        fixtures=("queries/assets/assets.rq",),
    ),
    Coverage(
        number=13, kind="registry + project-check",
        how="CNF-005 for classes (data stage), CMP-013 for properties.",
        evidence=(("data", "CNF-005"), ("project-output", "CMP-013")),
        fixtures=("ontology/water-v1.ttl",),
        notes="Both are Info: a term outside a given batch's scope is legitimately unused, and only "
              "a reviewer can separate that from a mapping nobody wrote.",
    ),
    Coverage(
        number=14, kind="registry",
        how="ontology-quality-suite sketch --queries fixtures/model/queries --file-pattern '**/*.rq'",
        evidence=(("sketch", "TQL-002"), ("sketch", "TQL-003")),
        fixtures=("queries/readings/readings.rq", "queries/readings/draft_alarms.rq"),
        notes="Split by naming convention rather than by severity guesswork: a ?x_IRI variable is "
              "built rather than read, so an unbound one is a Violation; anything else is probably "
              "a CSV column and is Info.",
    ),
    Coverage(
        number=15, kind="harness",
        how="mapping_integrity.check_mapping_output_coverage(sketch, output) -- every (class, "
            "predicate) pair the CONSTRUCT templates define, counted in the real output.",
        evidence=(("mapping-integrity", "MAP-015"),),
        fixtures=("queries/readings/readings.rq", "csv/readings.csv"),
        notes="Predicate-level comparison is not enough: gist:hasUnitOfMeasure is present in the "
              "output on pressures and absent on every flow, so only the pair (class, predicate) "
              "shows the loss.",
    ),
    Coverage(
        number=16, kind="harness",
        how="mapping_integrity.check_source_target_population(csv, output-per-file, class).",
        evidence=(("mapping-integrity", "MAP-016"),),
        fixtures=("queries/readings/readings.rq", "csv/readings.csv"),
        notes="Counted per output file rather than over the merged graph, so one mapping's collapse "
              "is not masked by another mapping's entities of the same class.",
    ),
    Coverage(
        number=17, kind="project-check",
        how="CMP-017 over the output; the required (class, property) pairs are a VALUES table in "
            "the check.",
        evidence=(("project-output", "CMP-017", "asset-A3"),),
        fixtures=("queries/assets/assets.rq", "csv/assets.csv"),
    ),
    Coverage(
        number=18, kind="project-check",
        how="CMP-018 over the output.",
        evidence=(("project-output", "CMP-018"),),
        fixtures=("queries/assets/legacy_assets.rq",),
        notes="pattern-consistency --dot renders the same question as a picture: the CONSTRUCT "
              "template coloured by which parts are verified against the model.",
    ),
    Coverage(
        number=19, kind="project-check",
        how="CMP-019 over the output.",
        evidence=(("project-output", "CMP-019", "pressure-S2"),),
        fixtures=("queries/readings/readings.rq", "csv/readings.csv"),
    ),
    Coverage(
        number=20, kind="registry",
        how="ontology-quality-suite data <output> --ontology water-v1.ttl",
        evidence=(("data", "DAT-004"),),
        fixtures=("queries/readings/readings.rq",),
        notes="DAT-004 is pinned to gist's exact namespace and to gist:hasUnitOfMeasure. A graph on "
              "a pre-gist-12 vocabulary is not checked rather than checked and found wanting.",
    ),
    Coverage(
        number=21, kind="project-check",
        how="CMP-021 over the output; the allowed (magnitude class, unit) pairs are a VALUES table "
            "in the check.",
        evidence=(("project-output", "CMP-021"),),
        fixtures=("queries/readings/readings.rq", "ontology/units.ttl"),
    ),
    Coverage(
        number=22, kind="registry",
        how="sketch for TQL-005, then data for the range violation the lost datatype causes.",
        evidence=(("sketch", "TQL-005"), ("data", "CNF-004")),
        fixtures=("queries/readings/readings.rq",),
        notes="TQL-005 catches it in the query, before the pipeline runs. CNF-004 catches the "
              "consequence in the output. DAT-001 catches the third form -- a lexical form invalid "
              "for the datatype it does carry.",
    ),
    Coverage(
        number=23, kind="harness",
        how="review_aids.compare_prefixes(baseline, candidate)",
        evidence=(("review-aids", "RVW-023"),),
        fixtures=("outputs/baseline.ttl", "outputs/candidate.ttl"),
    ),
    Coverage(
        number=24, kind="harness",
        how="review_aids.compare_predicates(baseline, candidate)",
        evidence=(("review-aids", "RVW-024"),),
        fixtures=("outputs/baseline.ttl", "outputs/candidate.ttl"),
    ),
    Coverage(
        number=25, kind="harness",
        how="review_aids.compare_class_populations(baseline, candidate)",
        evidence=(("review-aids", "RVW-025"),),
        fixtures=("outputs/baseline.ttl", "outputs/candidate.ttl"),
    ),
    Coverage(
        number=26, kind="harness",
        how="review_aids.compare_subject_values(baseline, candidate)",
        evidence=(("review-aids", "RVW-026"),),
        fixtures=("outputs/baseline.ttl", "outputs/candidate.ttl"),
    ),
    Coverage(
        number=27, kind="harness",
        how="review_aids.normalise, applied by CT-24 and CT-26 before comparing; reported as "
            "RVW-027, the list of differences it suppressed.",
        evidence=(("review-aids", "RVW-027"),),
        fixtures=("outputs/baseline.ttl", "outputs/candidate.ttl"),
        notes="Reported as a finding even when it suppresses nothing, so a reviewer can see the "
              "normalisation ran rather than inferring it from an absence.",
    ),
    Coverage(
        number=28, kind="harness",
        how="review_aids.compare_identifiers(baseline, candidate, identity_predicate=skos:notation)",
        evidence=(("review-aids", "RVW-028"),),
        fixtures=("outputs/baseline.ttl", "outputs/candidate.ttl"),
        notes="Needs a business key to align on. Without one, a renamed subject is indistinguishable "
              "from a deletion plus an insertion.",
    ),
]

COVERAGE_BY_NUMBER = {c.number: c for c in COVERAGE}

# Registry ids the CLI declares but does not implement -- see docs/CHECKS.md,
# "Not available in the CLI". Relevant to the competency tests as the answer
# to "what can this dataset not tell me?", and covered by fixtures/vsix/.
EXTENSION_ONLY_CHECKS = {
    "REA-005": "Individual both owl:sameAs and owl:differentFrom the same node",
    "REA-006": "Reasoner-derived contradiction (unclassified)",
    "VOC-001": "Undeclared term referenced by an axiom",
}
