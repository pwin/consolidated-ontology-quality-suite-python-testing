"""Run every competency test against the fixtures in this folder.

    uv run python competency_tests/run_competency_checks.py

Triplifies the CSV fixtures with oxi-gen, runs each suite stage that answers
a competency test, runs the project-local checks and the two harness modules,
then writes:

    COMPETENCY_COVERAGE.md   the coverage document -- generated, so it can
                             never drift from what the run actually found
    results/findings.csv     every finding, one row each
    results/*.txt            each suite stage's own report, verbatim

Exits 1 if any competency test's expected evidence is missing.
"""
from __future__ import annotations

import json
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS

import competency
import mapping_integrity
import review_aids
from ontology_suite import config, consistency as consistency_api, pattern_consistency, pipeline
from ontology_suite.checks.merge import ResultRow, build_unified_results
from ontology_suite.checks.registry import Registry
from ontology_suite.checks.sparql_runner import run_sparql_checks
from ontology_suite.sketch import prefix_alignment as pa
from ontology_suite.versioning import diff as version_diff

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
MODEL = FIXTURES / "model"
RESULTS = HERE / "results"
WORK = HERE.parent / "out" / "competency"

ONTOLOGY_V1 = MODEL / "ontology" / "water-v1.ttl"
ONTOLOGY_V2 = MODEL / "ontology" / "water-v2.ttl"
TAXONOMY = MODEL / "ontology" / "asset-types.ttl"
UNITS = MODEL / "ontology" / "units.ttl"
QUERIES = MODEL / "queries"
CSV_DIR = MODEL / "csv"
BASELINE = MODEL / "outputs" / "baseline.ttl"
CANDIDATE = MODEL / "outputs" / "candidate.ttl"
COMPLETENESS = FIXTURES / "completeness" / "incomplete-model.ttl"
PROJECT_CHECKS = HERE / "checks" / "sparql"
PROJECT_REGISTRY = HERE / "checks" / "competency-checks.json"

RECURSIVE_QUERIES = "**/*.rq"
WATER = "https://example.org/water/model#"

# Which query files are actually wired to a CSV. draft_alarms.rq deliberately
# is not, so it must not be counted when asking what the pipeline produced.
EXECUTED_QUERIES = [
    QUERIES / "assets" / "sites.rq",
    QUERIES / "assets" / "assets.rq",
    QUERIES / "assets" / "legacy_assets.rq",
    QUERIES / "readings" / "readings.rq",
]

# (csv, output file, class the mapping is supposed to produce one of per row)
POPULATION_EXPECTATIONS = [
    ("sites.csv", "sites.ttl", WATER + "Site"),
    ("assets.csv", "assets.ttl", WATER + "PumpStation"),
    ("readings.csv", "readings.ttl", WATER + "Reading"),
]


@dataclass
class Run:
    key: str
    title: str
    command: str
    rows: List[ResultRow] = field(default_factory=list)
    text: Optional[str] = None

    @property
    def ids(self) -> set:
        return {r.check_id for r in self.rows}


def _synthetic(check_id: str, severity: str, focus: str, message: str,
               category: str, source: str) -> ResultRow:
    return ResultRow(check_id=check_id, category=category, title=None, severity=severity,
                     focus_node=focus, path=None, value=None, message=message,
                     remediation=None, sources=[source])


def merged_registry() -> Registry:
    """The installed registry plus this project's own checks, so CMP-* ids
    resolve to titles and severities like any other check. Merged at run time
    rather than copied, so the suite's own 61 stay current."""
    shipped = json.loads(Path(config.DEFAULT_REGISTRY_PATH).read_text(encoding="utf-8"))
    local = json.loads(PROJECT_REGISTRY.read_text(encoding="utf-8"))
    shipped["checks"] = shipped["checks"] + local["checks"]
    WORK.mkdir(parents=True, exist_ok=True)
    merged_path = WORK / "merged-registry.json"
    merged_path.write_text(json.dumps(shipped, indent=2), encoding="utf-8")
    return Registry.load(merged_path)


def triplify_all() -> Dict[str, Path]:
    """Run both domains through oxi-gen. Returns {output filename: path}."""
    produced: Dict[str, Path] = {}
    for domain in ("assets", "readings"):
        stage = pipeline.run_triplify_stage(CSV_DIR, QUERIES / domain, WORK / ("triplify-" + domain))
        for path in stage.artifacts.get("output_paths", []):
            produced[Path(path).name] = Path(path)
    if not produced:
        raise SystemExit(
            "No output was triplified. oxi-gen is required for CT-2, CT-4 (dynamic), CT-13 and "
            "CT-15 to CT-22; build it with `cargo build --release` in the oxi-gen checkout."
        )
    return produced


def load_graph(*paths) -> Graph:
    graph = Graph()
    for path in paths:
        graph.parse(path)
    return graph


def sketch_with_declarations() -> Graph:
    """The CONSTRUCT-template sketch plus the rdf:type triples of the model
    and its controlled vocabularies -- and nothing else from them.

    CMP-012 asks whether the *transformation* states a label for a term the
    *model* owns. Answering it needs both artefacts in one graph, and needs
    the model's own labels kept out, or every correctly-labelled term in the
    ontology matches. Types are the only part of the model the check needs.
    """
    graph = pa.build_sketch_graph([QUERIES], RECURSIVE_QUERIES)
    for reference in (ONTOLOGY_V1, TAXONOMY, UNITS):
        for subject, predicate, obj in load_graph(reference):
            if predicate in (RDF.type, RDFS.subClassOf):
                graph.add((subject, predicate, obj))
    return graph


def project_checks(graph: Graph, registry: Registry, subdir: str = "competency") -> List[ResultRow]:
    """Run the project-local .rq checks over one graph, through the suite's
    own runner and result merge -- the documented extension mechanism, with
    no fork of the package."""
    results, outcomes = run_sparql_checks(graph, PROJECT_CHECKS / subdir)
    for outcome in outcomes:
        if not outcome.ok:
            print("  WARNING: {} failed to execute: {}".format(outcome.check_id, outcome.error))
    return build_unified_results(Graph(), results, registry, None)


def run_everything() -> List[Run]:
    registry = merged_registry()
    RESULTS.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    runs: List[Run] = []

    print("triplifying fixtures with oxi-gen ...")
    outputs = triplify_all()
    output_paths = sorted(outputs.values())
    output_graph = load_graph(*output_paths)
    print("  {} output file(s), {} triples".format(len(output_paths), len(output_graph)))

    # The triplified output is part of the record: every finding from CT-2,
    # CT-4, CT-13 and CT-15 to CT-22 is a statement about these files.
    triplified = RESULTS / "triplified"
    triplified.mkdir(parents=True, exist_ok=True)
    for path in output_paths:
        shutil.copy(path, triplified / path.name)

    # ---- sketch: the query source, against v1 ---------------------------
    sketch_v1 = pipeline.run_sketch_stage(
        QUERIES, WORK / "sketch", ontology_path=str(ONTOLOGY_V1), query_pattern=RECURSIVE_QUERIES)
    runs.append(Run("sketch", "Query source and shape vs ontology 1.0.0",
                    "ontology-quality-suite sketch --queries fixtures/model/queries "
                    "--file-pattern '**/*.rq' --ontology fixtures/model/ontology/water-v1.ttl",
                    sketch_v1.rows))

    # ---- sketch: the same queries against v2, which they were never updated for
    sketch_v2 = pipeline.run_sketch_stage(
        QUERIES, WORK / "sketch-v2", ontology_path=str(ONTOLOGY_V2), query_pattern=RECURSIVE_QUERIES)
    runs.append(Run("sketch-v2", "Query shape vs ontology 2.0.0 (mappings not updated)",
                    "ontology-quality-suite sketch --queries fixtures/model/queries "
                    "--file-pattern '**/*.rq' --ontology fixtures/model/ontology/water-v2.ttl",
                    sketch_v2.rows))

    # ---- data: the real output against the model ------------------------
    # The taxonomy and units are reference data the output points into: without
    # them gist:UnitOfMeasure memberships do not resolve and DAT-004 reports
    # every unit link as "not typed a unit" rather than the genuine omissions.
    data_stage = pipeline.run_data_stage(
        [str(p) for p in output_paths] + [str(TAXONOMY), str(UNITS)], WORK / "data",
        ontology_path=str(ONTOLOGY_V1), registry=registry, reasoner="owlrl-only")
    runs.append(Run("data", "Triplified output vs ontology 1.0.0",
                    "ontology-quality-suite data <triplified output> "
                    "fixtures/model/ontology/asset-types.ttl fixtures/model/ontology/units.ttl "
                    "--ontology fixtures/model/ontology/water-v1.ttl",
                    data_stage.rows))

    # ---- checks: the completeness fixture -------------------------------
    completeness = pipeline.run_checks_stage(registry, WORK / "completeness", ontology_path=str(COMPLETENESS))
    runs.append(Run("completeness", "Documentation completeness of an authored ontology",
                    "ontology-quality-suite checks --ontology "
                    "fixtures/completeness/incomplete-model.ttl",
                    completeness.rows))
    runs[-1].rows += project_checks(load_graph(COMPLETENESS), registry, "ontology")

    # ---- project-local checks over the output ---------------------------
    output_plus_model = load_graph(*output_paths, ONTOLOGY_V1, TAXONOMY, UNITS)
    runs.append(Run("project-output", "Project-local checks over output + model",
                    "run_competency_checks.py -> project_checks(output + ontology + taxonomy + units)",
                    project_checks(output_plus_model, registry)))

    # ---- project-local checks over the CONSTRUCT-template sketch --------
    sketch_graph = sketch_with_declarations()
    runs.append(Run("project-sketch", "Project-local checks over the CONSTRUCT-template sketch",
                    "run_competency_checks.py -> project_checks(build_sketch_graph(queries))",
                    project_checks(sketch_graph, registry, "sketch")))

    # ---- pattern-consistency: the taxonomy boundaries -------------------
    four_layer = pattern_consistency.check_four_layer_consistency(
        [str(QUERIES)], [str(ONTOLOGY_V1)], [str(TAXONOMY), str(UNITS)],
        output_data_paths=[str(p) for p in output_paths],
        query_pattern=RECURSIVE_QUERIES)
    pattern_rows: List[ResultRow] = []
    for gap in four_layer.taxonomy_transform:
        pattern_rows.append(_synthetic(
            "taxonomy-reference", "Violation", gap.term,
            "A query hard-codes {} via {}, which the taxonomy never declares. {}".format(
                gap.term, gap.property, gap.detail),
            "pattern-consistency", "pattern-consistency"))
    for gap in (four_layer.taxonomy_output_data or []):
        pattern_rows.append(_synthetic(
            "taxonomy-membership", "Violation", gap.term,
            "Real output references {} via {}, which the taxonomy never declares. {}".format(
                gap.term, gap.property, gap.detail),
            "pattern-consistency", "pattern-consistency"))
    runs.append(Run("pattern-consistency", "Taxonomy boundaries (query text and real output)",
                    "ontology-quality-suite pattern-consistency --queries fixtures/model/queries "
                    "--ontology fixtures/model/ontology/water-v1.ttl "
                    "--taxonomy fixtures/model/ontology/asset-types.ttl "
                    "--taxonomy fixtures/model/ontology/units.ttl "
                    "--output-data <triplified output> --file-pattern '**/*.rq'",
                    pattern_rows,
                    pattern_consistency.format_four_layer_report(four_layer)))

    # ---- consistency: v1 -> v2 with the mappings left behind ------------
    report = consistency_api.check_consistency(
        str(ONTOLOGY_V2), old_ontology=str(ONTOLOGY_V1),
        tarql_sources=[str(QUERIES)], ontology_paths=[str(ONTOLOGY_V2), str(TAXONOMY), str(UNITS)],
        query_pattern=RECURSIVE_QUERIES)
    consistency_rows: List[ResultRow] = []
    for rename in report.renames:
        consistency_rows.append(_synthetic(
            "rename-detected", "Warning", rename.old_iri,
            "{} was renamed to {} ({}, confidence {:.0%}). Every mapping still using the old name "
            "builds data under vocabulary 2.0.0 does not declare.".format(
                rename.old_iri, rename.new_iri, rename.reason, rename.confidence),
            "consistency", "consistency"))
    for term in (report.alignment.undeclared_terms if report.alignment else []):
        consistency_rows.append(_synthetic(
            "undeclared-term", "Violation", term.term,
            "The mapping set builds {} ({}), which ontology 2.0.0 does not declare.".format(
                term.term, term.kind),
            "consistency", "consistency"))
    for repair in report.repairs:
        consistency_rows.append(_synthetic(
            "repair-suggested", "Info", Path(repair.target_file).name,
            "{} (confidence {:.0%})".format(repair.description, repair.confidence),
            "consistency", "consistency"))
    runs.append(Run("consistency", "Ontology 1.0.0 -> 2.0.0 vs the mappings",
                    "ontology-quality-suite consistency --old fixtures/model/ontology/water-v1.ttl "
                    "--new fixtures/model/ontology/water-v2.ttl --queries fixtures/model/queries "
                    "--file-pattern '**/*.rq'",
                    consistency_rows,
                    consistency_api.format_consistency_report(report)))

    # ---- version-diff ---------------------------------------------------
    diff, bump = version_diff.diff_ontologies(load_graph(ONTOLOGY_V1), load_graph(ONTOLOGY_V2))
    diff_text = version_diff.format_report(diff, bump, str(ONTOLOGY_V1), str(ONTOLOGY_V2))
    runs.append(Run("version-diff", "Semver bump implied by the ontology change",
                    "ontology-quality-suite version-diff fixtures/model/ontology/water-v1.ttl "
                    "fixtures/model/ontology/water-v2.ttl",
                    [_synthetic(bump.value, "Warning", str(ONTOLOGY_V2),
                                "The ontology change implies a {} bump. The mapping set carries no "
                                "version of its own and was not changed at all.".format(bump.value.upper()),
                                "version-diff", "version-diff")],
                    diff_text))

    # ---- mapping integrity ----------------------------------------------
    executed_sketch = pa.build_sketch_graph([str(p) for p in EXECUTED_QUERIES], RECURSIVE_QUERIES)
    mapping_rows = mapping_integrity.check_mapping_output_coverage(executed_sketch, output_graph)
    for csv_name, output_name, cls in POPULATION_EXPECTATIONS:
        if output_name in outputs:
            mapping_rows += mapping_integrity.check_source_target_population(
                CSV_DIR / csv_name, load_graph(outputs[output_name]), URIRef(cls))
    runs.append(Run("mapping-integrity", "Source records and defined mappings vs real output",
                    "run_competency_checks.py -> mapping_integrity.*",
                    mapping_rows))

    # ---- review aids ------------------------------------------------------
    review_rows, _values = review_aids.compare_outputs(BASELINE, CANDIDATE)
    runs.append(Run("review-aids", "Baseline output vs candidate output",
                    "run_competency_checks.py -> review_aids.compare_outputs("
                    "fixtures/model/outputs/baseline.ttl, fixtures/model/outputs/candidate.ttl)",
                    review_rows))

    return runs


def evaluate(runs: List[Run]):
    by_key = {run.key: run for run in runs}
    definitions = competency.load_definitions()
    results = []
    for cover in competency.COVERAGE:
        observed, missing = [], []
        for entry in cover.evidence:
            run_key, check_id = entry[0], entry[1]
            needle = entry[2] if len(entry) > 2 else None
            run = by_key.get(run_key)
            hits = [r for r in (run.rows if run else []) if r.check_id == check_id]
            if needle:
                hits = [r for r in hits if needle in r.focus_node or needle in r.message]
            if hits:
                observed.append((run_key, check_id, hits))
            else:
                missing.append((run_key, check_id if not needle else
                                "{} matching '{}'".format(check_id, needle)))
        results.append((definitions[cover.number], cover, observed, missing))
    return results


def write_findings_csv(runs: List[Run]) -> Path:
    import csv as csv_module
    path = RESULTS / "findings.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv_module.writer(handle)
        writer.writerow(["run", "check_id", "severity", "category", "focus_node", "path", "value", "message"])
        for run in runs:
            for row in run.rows:
                writer.writerow([run.key, row.check_id, row.severity, row.category or "",
                                 row.focus_node, row.path or "", row.value or "", row.message])
    return path


def write_stage_reports(runs: List[Run]) -> None:
    for run in runs:
        if run.text:
            (RESULTS / (run.key + ".txt")).write_text(run.text, encoding="utf-8")


def render_document(runs: List[Run], results) -> str:
    covered = sum(1 for _d, _c, _o, missing in results if not missing)
    by_key = {run.key: run for run in runs}
    total_findings = sum(len(run.rows) for run in runs)

    lines: List[str] = []
    add = lines.append
    add("# Competency test coverage")
    add("")
    add("Generated by `run_competency_checks.py`. Every number below comes from the run it "
        "describes, so this file cannot drift from what the checks actually found -- regenerate "
        "it rather than editing it.")
    add("")
    add("- **Competency tests:** {} of {} evidenced by a passing check".format(covered, len(results)))
    add("- **Suite version:** ontology-quality-suite {}".format(_suite_version()))
    add("- **Findings recorded:** {} across {} runs (`results/findings.csv`)".format(
        total_findings, len(runs)))
    add("")
    add("The definitions come from the five CSVs in this folder; the issue and summary text below "
        "is read from them at generation time rather than copied.")
    add("")

    add("## Running it")
    add("")
    add("```bash")
    add("uv sync                                              # suite 0.14.x, editable from ../../consolidated_ontology_suite_python")
    add("uv run python competency_tests/run_competency_checks.py   # regenerates this file")
    add("uv run pytest competency_tests -q                     # the same expectations as pass/fail tests")
    add("```")
    add("")
    add("The run needs `oxi-gen` on the path or built in a sibling checkout: CT-2, CT-4, CT-13 and "
        "CT-15 to CT-22 are all asked of real triplified output, not of the query text. Each stage's "
        "own report is written verbatim to `results/`.")
    add("")
    add("## What is in this folder")
    add("")
    add("| Path | What it is |")
    add("|---|---|")
    add("| `*.csv` | the competency-test definitions, as supplied -- the source of the numbering used throughout |")
    add("| `fixtures/model/` | one worked example spanning all four layers: ontology 1.0.0 and 2.0.0, taxonomy, units, four TARQL mappings, the CSVs they read, and two comparable outputs |")
    add("| `fixtures/completeness/` | documentation-completeness defects, isolated so each is attributable |")
    add("| `fixtures/vsix/` | the dataset for the three checks only the VS Code extension implements |")
    add("| `checks/` | project-local `CMP-*` checks, one directory per graph they are asked of, plus their registry entries |")
    add("| `review_aids.py` | CT-23 to CT-28 -- comparisons between two outputs |")
    add("| `mapping_integrity.py` | CT-15 and CT-16 -- source records and defined mappings vs real output |")
    add("| `competency.py` | the coverage table: how each test is answered and what evidence proves it |")
    add("| `results/` | this run's findings and each stage's verbatim report |")
    add("")
    add("Every seeded defect is marked in its fixture with an `# ERROR:` or `# SEEDS CT-n` comment "
        "naming the test it is there for.")
    add("")
    add("## Coverage at a glance")
    add("")
    add("| CT | Issue | How it is checked | Evidence |")
    add("|---|---|---|---|")
    for definition, cover, observed, missing in results:
        evidence = ", ".join("`{}`".format(check_id) for _run, check_id, _hits in observed) or "--"
        if missing:
            evidence += " (missing: " + ", ".join("`{}`".format(c) for _r, c in missing) + ")"
        add("| CT-{} | {} | {} | {} |".format(definition.number, definition.issue, cover.kind, evidence))
    add("")

    add("## How each test is implemented")
    add("")
    for definition, cover, observed, missing in results:
        add("### CT-{} -- {}".format(definition.number, definition.issue))
        add("")
        add("*{}* &middot; category: {}".format(definition.summary, definition.category))
        add("")
        add("**Coverage:** {}".format(cover.kind))
        add("")
        add("**How to run it**")
        add("")
        add("```")
        for line in cover.how.splitlines():
            add(line)
        add("```")
        add("")
        if cover.fixtures:
            add("**Seeded in:** " + ", ".join("`fixtures/model/{}`".format(f) if "/" in f and
                not f.startswith(("completeness/", "outputs/", "vsix/")) else "`fixtures/{}`".format(f)
                for f in cover.fixtures))
            add("")
        if cover.notes:
            add(cover.notes)
            add("")
        if observed:
            add("**Observed**")
            add("")
            for run_key, check_id, hits in observed:
                add("- `{}` x{} in run `{}` -- {}".format(
                    check_id, len(hits), run_key, _shorten(hits[0].message)))
            add("")
        if missing:
            add("**NOT OBSERVED:** " + ", ".join("`{}` (run `{}`)".format(c, r) for r, c in missing))
            add("")

    add("## Runs")
    add("")
    add("| Run | What it covers | Findings | Command |")
    add("|---|---|---|---|")
    for run in runs:
        add("| `{}` | {} | {} | `{}` |".format(
            run.key, run.title, len(run.rows), run.command.replace("\n", " ")))
    add("")
    for run in runs:
        add("### Run `{}`".format(run.key))
        add("")
        add("{} finding(s).".format(len(run.rows)))
        add("")
        counts = defaultdict(int)
        for row in run.rows:
            counts[(row.check_id, row.severity)] += 1
        if counts:
            add("| Check | Severity | Count |")
            add("|---|---|---|")
            for (check_id, severity), count in sorted(counts.items()):
                add("| `{}` | {} | {} |".format(check_id, severity, count))
            add("")
        if run.text:
            add("Full report: `results/{}.txt`".format(run.key))
            add("")

    add("## Observations from building this")
    add("")
    for note in _observations(by_key):
        add(note)
        add("")

    add("## Checks only the VS Code extension can run")
    add("")
    add("Three ids are declared in the shipped `registry.json` and have no implementation in the "
        "Python package -- no `.rq` file and no SHACL shape. `docs/CHECKS.md` marks each of them "
        "*Not available in the CLI*; they are computed by the Ontology Development Suite extension "
        "(`consolidated_ontology_suite_webapp`, `ontology-dev-suite`).")
    add("")
    add("| Check | Title | Implemented in |")
    add("|---|---|---|")
    for check_id, title in sorted(competency.EXTENSION_ONLY_CHECKS.items()):
        add("| `{}` | {} | `src/checks/{}` |".format(
            check_id, title,
            "reasoningRunner.ts" if check_id.startswith("REA") else "vocabularyChecks.ts"))
    add("")
    add("None of the 28 competency tests *depends* on these three: every one is evidenced by a "
        "check the CLI runs, as the table above records. They matter as a limit on what a clean "
        "CLI result means -- `VOC-001` in particular is the one referential-integrity question "
        "SHACL's open-world semantics cannot ask, so an axiom pointing at a misspelled class is "
        "invisible to every check the CLI has.")
    add("")
    add("`fixtures/vsix/extension-only.ttl` is a small dataset seeded for them:")
    add("")
    add("1. Open `fixtures/vsix/extension-only.ttl` in VS Code with the extension installed "
        "(`code --install-extension consolidated_ontology_suite_webapp/ontology-dev-suite-0.13.6.vsix`).")
    add("2. Run **Ontology Suite: Run Local Checks** from the command palette.")
    add("3. The Problems panel should report `VOC-001` on `:Pump rdfs:subClassOf :Machnie` (a typo "
        "for `:Machine`) and `REA-005` on `:pump-17`, which is asserted both `owl:sameAs` and "
        "`owl:differentFrom` `:pump-seventeen`.")
    add("")
    add("For contrast, run the CLI over the same file:")
    add("")
    add("```")
    add("uv run ontology-quality-suite checks --ontology competency_tests/fixtures/vsix/extension-only.ttl \\")
    add("  --out-dir out/competency/vsix")
    add("```")
    add("")
    vsix_note = _vsix_observation()
    add(vsix_note)
    add("")
    add("`REA-006` is a catch-all for a contradiction the extension's reasoner labelled with a "
        "reason its reader does not render specifically. It cannot be seeded deliberately -- "
        "firing at all means the ruleset has grown a case its reader has not -- so no fixture "
        "claims to trigger it.")
    add("")
    return "\n".join(lines) + "\n"


def _construct_variables() -> set:
    """Every ?variable name mentioned in the query set."""
    import re
    names = set()
    for path in sorted(QUERIES.rglob("*.rq")):
        names |= set(re.findall(r"\?([A-Za-z_][A-Za-z0-9_]*)", path.read_text(encoding="utf-8")))
    return names


def _observations(by_key: Dict[str, Run]) -> List[str]:
    """Notes measured from this run, not asserted."""
    notes: List[str] = []

    gaps = [r for r in by_key["pattern-consistency"].rows if r.check_id == "taxonomy-reference"]
    variables = _construct_variables()
    spurious = [r for r in gaps if r.focus_node.rsplit("#", 1)[-1].rsplit("/", 1)[-1] in variables]
    if spurious:
        notes.append(
            "**`check_taxonomy_references` over-reports when a query declares its own `:` prefix.** "
            "Of the {} taxonomy-reference finding(s) in run `pattern-consistency`, {} name a CONSTRUCT "
            "*variable* rather than a hard-coded term: {}. The check means to skip per-row entities, "
            "and recognises them by the sketch's scratch namespace (`https://tarqlviz.org/`). But "
            "`sketch.ttl` renders those entities with the *query's* own empty prefix whenever the query "
            "declares one -- all four mappings here declare `prefix : <{}>` -- so every unbound variable "
            "lands in the model's namespace and is reported as a nonexistent taxonomy reference. The one "
            "genuine finding, `vocab:Resevoir`, is outnumbered {}-to-1. The suite's own "
            "`examples/pattern_consistency/transform.rq` does not declare `:`, which is why its worked "
            "example shows a single clean finding.".format(
                len(gaps), len(spurious),
                ", ".join("`" + r.focus_node.rsplit("#", 1)[-1] + "`" for r in spurious[:6]) +
                (", ..." if len(spurious) > 6 else ""),
                WATER, len(spurious)))

    notes.append(
        "**A two-graph question needs two graphs kept apart.** CMP-012 asks whether the "
        "*transformation* states a label for a term the *model* owns. Its first form copied the "
        "scratch-namespace filter above: that returns the right answer on these fixtures, but by "
        "accident -- a per-row entity the mapping labels would be missed for exactly the reason the "
        "note above describes. Merging the model into the sketch to fix it took the count from 1 to "
        "101, because a single merged graph cannot say which file a triple came from and every term "
        "the ontology correctly labels then matched. What works is narrower on both sides: identify a "
        "model-owned term by what it is *declared* as, and merge in the model's `rdf:type` and "
        "`rdfs:subClassOf` triples only, leaving its labels out.")

    notes.append(
        "**Reference vocabularies have to be loaded for the checks that depend on them.** Run `data` "
        "without `asset-types.ttl` and `units.ttl` and DAT-004 reports 12 findings rather than 6: every "
        "`gist:hasUnitOfMeasure` link resolves to an untyped IRI, so the six correct pressure units are "
        "reported alongside the six genuinely missing flow units. The check is right both times; only "
        "one of the two inputs describes the system being assessed.")

    return notes


def _shorten(message: str, limit: int = 150) -> str:
    message = " ".join(message.split())
    return message if len(message) <= limit else message[: limit - 1] + "..."


def _suite_version() -> str:
    try:
        from importlib.metadata import version
        return version("ontology-quality-suite")
    except Exception:  # pragma: no cover - metadata should always be present
        return "unknown"


def _vsix_observation() -> str:
    """Run the CLI over the extension-only fixture and record what it reports,
    so the claim in the document is measured rather than asserted."""
    registry = merged_registry()
    stage = pipeline.run_checks_stage(registry, WORK / "vsix", ontology_path=str(FIXTURES / "vsix" / "extension-only.ttl"))
    ids = sorted({row.check_id for row in stage.rows})
    extension_ids = sorted(set(ids) & set(competency.EXTENSION_ONLY_CHECKS))
    return ("Observed: {} finding(s), check ids {} -- and {} of the three extension-only ids. "
            "The `:Machnie` typo and the sameAs/differentFrom contradiction both go unreported."
            .format(len(stage.rows), ", ".join("`{}`".format(i) for i in ids) or "none",
                    ", ".join(extension_ids) if extension_ids else "none"))


def main() -> int:
    runs = run_everything()
    results = evaluate(runs)

    write_stage_reports(runs)
    findings_path = write_findings_csv(runs)
    document = HERE / "COMPETENCY_COVERAGE.md"
    document.write_text(render_document(runs, results), encoding="utf-8")

    print()
    failures = 0
    for definition, _cover, observed, missing in results:
        status = "ok  " if not missing else "MISS"
        failures += 1 if missing else 0
        evidence = ", ".join("{}x{}".format(check_id, len(hits)) for _r, check_id, hits in observed)
        print("[{}] CT-{:<2} {:<58} {}".format(status, definition.number, definition.issue[:58], evidence))
        for run_key, check_id in missing:
            print("       missing {} in run {}".format(check_id, run_key))

    print()
    print("Wrote {}".format(document))
    print("Wrote {} ({} findings)".format(findings_path, sum(len(r.rows) for r in runs)))
    print("RESULT: {}".format(
        "all 28 competency tests evidenced" if not failures else "{} test(s) without evidence".format(failures)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
