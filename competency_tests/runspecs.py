"""How each competency-test run is reproduced from a shell.

``competency.py`` says *what* the 28 tests are and which check answers each.
This says *how to run* the pass that produces it: one entry per run key, with
a command that works as-is from the repo root.

Kept separate so both generated documents -- COMPETENCY_COVERAGE.md and
COMPETENCY_CHECK_MATRIX.md -- and the harness itself read the same strings,
rather than the harness holding commands inline that the documents then
paraphrase.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

MODEL = "competency_tests/fixtures/model"
OUTPUT = "competency_tests/results/triplified"
REGISTRY = "competency_tests/results/merged-registry.json"
HARNESS = "uv run python competency_tests/run_competency_checks.py"


@dataclass(frozen=True)
class RunSpec:
    """One pass over the fixtures, and the command that reproduces it.

    ``command`` runs as-is from the repo root. ``project_command`` is the
    variant that runs this repo's own CMP-* checks instead of the shipped
    registry -- the same stage, pointed at ``checks/sparql/`` and the merged
    registry -- and is what a CMP-* row in the matrix quotes. A run with
    neither has no single-command form, and ``note`` says why.
    """
    key: str
    title: str
    command: str = ""
    project_command: str = ""
    note: str = ""


RUNS: Dict[str, RunSpec] = {
    "sketch": RunSpec(
        key="sketch",
        title="Query source and shape vs ontology 1.0.0",
        command=f'''uv run ontology-quality-suite sketch \\
  --queries {MODEL}/queries --file-pattern "**/*.rq" \\
  --ontology {MODEL}/ontology/water-v1.ttl \\
  --out-dir out/ct/sketch''',
    ),
    "sketch-v2": RunSpec(
        key="sketch-v2",
        title="Query shape vs ontology 2.0.0, which the mappings were never updated for",
        command=f'''uv run ontology-quality-suite sketch \\
  --queries {MODEL}/queries --file-pattern "**/*.rq" \\
  --ontology {MODEL}/ontology/water-v2.ttl \\
  --out-dir out/ct/sketch-v2''',
    ),
    "data": RunSpec(
        key="data",
        title="Triplified output vs ontology 1.0.0",
        command=f'''uv run ontology-quality-suite data \\
  {OUTPUT} \\
  {MODEL}/ontology/asset-types.ttl {MODEL}/ontology/units.ttl \\
  --ontology {MODEL}/ontology/water-v1.ttl \\
  --reasoner owlrl-only --out-dir out/ct/data''',
    ),
    "completeness": RunSpec(
        key="completeness",
        title="Documentation completeness of an authored ontology",
        command='''uv run ontology-quality-suite checks \\
  --ontology competency_tests/fixtures/completeness/incomplete-model.ttl \\
  --out-dir out/ct/completeness''',
        project_command=f'''uv run ontology-quality-suite checks \\
  --ontology competency_tests/fixtures/completeness/incomplete-model.ttl \\
  --registry {REGISTRY} \\
  --sparql competency_tests/checks/sparql/ontology \\
  --out-dir out/ct/completeness-cmp''',
    ),
    "project-output": RunSpec(
        key="project-output",
        title="Project-local checks over output + model",
        project_command=f'''uv run ontology-quality-suite data \\
  {OUTPUT} \\
  {MODEL}/ontology/asset-types.ttl {MODEL}/ontology/units.ttl \\
  --ontology {MODEL}/ontology/water-v1.ttl \\
  --registry {REGISTRY} \\
  --sparql competency_tests/checks/sparql/competency \\
  --reasoner owlrl-only --out-dir out/ct/project-output''',
    ),
    "project-sketch": RunSpec(
        key="project-sketch",
        title="Project-local checks over the CONSTRUCT-template sketch",
        note="No single-command form. CMP-012 needs the sketch graph merged with the model's "
             "rdf:type and rdfs:subClassOf triples *only*, and the CLI's --ontology takes whole "
             "files: merging the model entire makes every term the ontology correctly labels "
             "match. Run the harness.",
    ),
    "pattern-consistency": RunSpec(
        key="pattern-consistency",
        title="Taxonomy boundaries, in query text and in real output",
        command=f'''uv run ontology-quality-suite pattern-consistency \\
  --queries {MODEL}/queries \\
  --ontology {MODEL}/ontology/water-v1.ttl \\
  --taxonomy {MODEL}/ontology/asset-types.ttl \\
  --taxonomy {MODEL}/ontology/units.ttl \\
  --output-data {OUTPUT} \\
  --file-pattern "**/*.rq" --out-dir out/ct/pattern-consistency''',
    ),
    "consistency": RunSpec(
        key="consistency",
        title="Ontology 1.0.0 -> 2.0.0 vs the mappings",
        command=f'''uv run ontology-quality-suite consistency \\
  --old {MODEL}/ontology/water-v1.ttl \\
  --new {MODEL}/ontology/water-v2.ttl \\
  --queries {MODEL}/queries \\
  --file-pattern "**/*.rq" --out-dir out/ct/consistency''',
    ),
    "version-diff": RunSpec(
        key="version-diff",
        title="Semver bump implied by the ontology change",
        command=f'''uv run ontology-quality-suite version-diff \\
  {MODEL}/ontology/water-v1.ttl \\
  {MODEL}/ontology/water-v2.ttl \\
  --out-dir out/ct/version-diff''',
    ),
    "mapping-integrity": RunSpec(
        key="mapping-integrity",
        title="Source records and defined mappings vs real output",
        command=f'''uv run python competency_tests/mapping_integrity.py \\
  --queries {MODEL}/queries/assets \\
  --queries {MODEL}/queries/readings/readings.rq \\
  --output {OUTPUT} \\
  --population {MODEL}/csv/readings.csv \\
               {OUTPUT}/readings.ttl \\
               https://example.org/water/model#Reading''',
    ),
    "review-aids": RunSpec(
        key="review-aids",
        title="Baseline output vs candidate output",
        command=f'''uv run python competency_tests/review_aids.py \\
  {MODEL}/outputs/baseline.ttl \\
  {MODEL}/outputs/candidate.ttl''',
    ),
}


def command_for(run_key: str, check_id: str) -> Tuple[str, str]:
    """``(command, note)`` for one evidence pair.

    A CMP-* check quotes its run's ``project_command`` -- the same stage
    pointed at this repo's checks -- and everything else the plain command.
    """
    spec = RUNS.get(run_key)
    if spec is None:
        return "", ""
    if check_id.startswith("CMP-") and spec.project_command:
        return spec.project_command, spec.note
    return spec.command or spec.project_command, spec.note


# Evidence ids that are not registry checks: structured output of a suite
# module, or of this repo's own harness. Described here so the matrix can say
# what they are rather than leaving the row blank.
NON_REGISTRY_EVIDENCE: Dict[str, Tuple[str, str, str]] = {
    "rename-detected": (
        "consistency", "Warning",
        "A term removed in the new ontology paired with one added, by rename detection -- an "
        "explicit dcterms:isReplacedBy / owl:equivalentClass annotation at full confidence, or "
        "local-name similarity below it."),
    "undeclared-term": (
        "consistency", "Violation",
        "A class or property the mapping set builds that the new ontology does not declare "
        "(sketch.prefix_alignment)."),
    "repair-suggested": (
        "consistency", "Info",
        "A concrete unified diff against the query file that would fix a misalignment -- "
        "reviewable as a .patch, or applied with --apply-repairs."),
    "taxonomy-reference": (
        "pattern-consistency", "Violation",
        "A controlled-vocabulary IRI hard-coded in a CONSTRUCT template that the taxonomy never "
        "declares. Query text only."),
    "taxonomy-membership": (
        "pattern-consistency", "Violation",
        "A taxonomy IRI in real triplified output that the taxonomy never declares -- the per-row "
        "case no reading of the query text can find."),
    "major": (
        "version-diff", "Warning",
        "The semver bump the ontology change implies, compared against whether the dependent "
        "artefacts moved at all."),
    "MAP-015": (
        "mapping-integrity", "Violation",
        "A (class, predicate) pair the CONSTRUCT templates define that no instance of that class "
        "carries in the output."),
    "MAP-016": (
        "mapping-integrity", "Violation",
        "Source records in vs entities out, after the project's explicit filtering rule."),
    "RVW-023": ("review-aids", "Info / Warning",
                "Prefix and namespace declarations that differ between two outputs."),
    "RVW-024": ("review-aids", "Warning / Info",
                "Predicate usage that differs between two outputs."),
    "RVW-025": ("review-aids", "Warning / Info",
                "Class populations that differ between two outputs."),
    "RVW-026": ("review-aids", "Warning",
                "A shared subject-predicate pair whose object value or relationship target changed."),
    "RVW-027": ("review-aids", "Info",
                "Representation-only differences suppressed by normalisation before comparing -- "
                "reported even when it suppresses nothing, so the pass is visible."),
    "RVW-028": ("review-aids", "Violation / Info",
                "A business key whose subject IRI is not the same in both outputs."),
}
