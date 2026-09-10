"""Source-to-output mapping integrity -- competency tests CT-15 and CT-16.

Both compare a mapping's *intent* with what it actually produced, so both
need two artefacts and neither can be a registry check over one graph.

    CT-15  check_mapping_output_coverage   a defined mapping produces no values
    CT-16  check_source_target_population  source records vs generated entities

CT-15 works from the CONSTRUCT-template sketch the suite already builds
(``sketch.prefix_alignment.build_sketch_graph``): every (class, predicate)
pair the templates promise, counted against the real output. Comparing
predicate *sets* alone is not enough -- in the worked example
``gist:hasUnitOfMeasure`` is present in the output on every pressure and
absent from every flow, so the predicate looks used and one class's mapping
has silently produced nothing.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from ontology_suite.checks.merge import ResultRow
from ontology_suite.sketch.tarql_visualiser import DEFAULT_BASE, scratch_namespace

# The sketch's own legend predicates describe the query file, not the data it
# builds, so they are not part of any mapping's promise.
SKETCH_LEGEND = ("isRepresentedBy", "hasAmbiguousPrefix")


def _row(check_id: str, severity: str, focus: str, message: str,
         path: Optional[str] = None, value: Optional[str] = None) -> ResultRow:
    return ResultRow(
        check_id=check_id, category="mapping-integrity", title=None, severity=severity,
        focus_node=focus, path=path, value=value, message=message,
        remediation=None, sources=["mapping-integrity"],
    )


def template_pairs(sketch: Graph) -> Set[Tuple[URIRef, URIRef]]:
    """Every (class, predicate) pair the CONSTRUCT templates assert."""
    types: Dict[object, Set[URIRef]] = defaultdict(set)
    for subject, cls in sketch.subject_objects(RDF.type):
        if isinstance(cls, URIRef):
            types[subject].add(cls)

    pairs: Set[Tuple[URIRef, URIRef]] = set()
    for subject, predicate, _obj in sketch:
        if predicate == RDF.type or not isinstance(predicate, URIRef):
            continue
        if any(str(predicate).endswith(name) for name in SKETCH_LEGEND):
            continue
        for cls in types.get(subject, ()):
            pairs.add((cls, predicate))
    return pairs


def check_mapping_output_coverage(sketch: Graph, output: Graph) -> List[ResultRow]:
    """CT-15: a mapping that is defined and yields nothing."""
    rows: List[ResultRow] = []
    for cls, predicate in sorted(template_pairs(sketch), key=lambda pair: (str(pair[0]), str(pair[1]))):
        instances = set(output.subjects(RDF.type, cls))
        if not instances:
            rows.append(_row(
                "MAP-015", "Warning", str(cls), path=str(predicate),
                message="The transformation defines {} on {}, and the output contains no {} at "
                        "all.".format(predicate, cls, cls)))
            continue
        carrying = {s for s in instances if (s, predicate, None) in output}
        if not carrying:
            rows.append(_row(
                "MAP-015", "Violation", str(cls), path=str(predicate),
                value="0/{}".format(len(instances)),
                message="The transformation defines {} on {}, but none of the {} {}(s) in the output "
                        "carries it. Every triple for this mapping was dropped.".format(
                            predicate, cls, len(instances), cls)))
    return rows


def csv_row_count(csv_path) -> int:
    with Path(csv_path).open(encoding="utf-8-sig", newline="") as handle:
        return max(0, sum(1 for record in csv.reader(handle) if any(field.strip() for field in record)) - 1)


def check_source_target_population(csv_path, output: Graph, entity_class: URIRef,
                                   expected_filtered: int = 0) -> List[ResultRow]:
    """CT-16: source records in, entities out.

    ``expected_filtered`` is the project's explicit filtering rule -- rows the
    mapping is *supposed* to drop. Without somewhere to state it, every
    legitimately filtered row reads as a defect and the check gets muted.
    """
    rows_in = csv_row_count(csv_path)
    expected = rows_in - expected_filtered
    produced = len(set(output.subjects(RDF.type, entity_class)))
    if produced == expected:
        return []
    return [_row(
        "MAP-016", "Violation", str(entity_class),
        value="{} -> {}".format(expected, produced),
        message="{} has {} data row(s) and, after {} explicitly filtered, {} {} entit(y/ies) were "
                "expected; the output has {}. Rows are being merged onto a shared IRI or dropped "
                "entirely.".format(Path(csv_path).name, rows_in, expected_filtered, expected,
                                   entity_class, produced))]


def main(argv=None) -> int:
    """Command-line entry point, so CT-15 and CT-16 can be reproduced without
    running the whole competency harness.

        uv run python competency_tests/mapping_integrity.py \
            --queries competency_tests/fixtures/model/queries \
            --output competency_tests/results/triplified \
            --population competency_tests/fixtures/model/csv/readings.csv \
                         competency_tests/results/triplified/readings.ttl \
                         https://example.org/water/model#Reading
    """
    import argparse

    from ontology_suite.sketch import prefix_alignment as pa

    parser = argparse.ArgumentParser(
        description="Compare a mapping's intent with its real output -- CT-15 and CT-16.")
    parser.add_argument("--queries", action="append", required=True,
                        help="a query file or folder (repeatable). Pass only the queries that were "
                             "actually run: a draft mapping wired to no CSV would otherwise report "
                             "every pair it defines as producing nothing.")
    parser.add_argument("--output", action="append", required=True,
                        help="a triplified output file or folder (repeatable)")
    parser.add_argument("--file-pattern", default="**/*.rq")
    parser.add_argument("--population", nargs=3, action="append", default=[],
                        metavar=("CSV", "OUTPUT_FILE", "CLASS_IRI"),
                        help="a CT-16 source-to-target check (repeatable)")
    parser.add_argument("--filtered", type=int, default=0,
                        help="rows the mapping is expected to drop, per --population check")
    args = parser.parse_args(argv)

    sketch = pa.build_sketch_graph(args.queries, args.file_pattern)
    output = Graph()
    for path in args.output:
        for resolved in sorted(Path(path).rglob("*.ttl")) if Path(path).is_dir() else [Path(path)]:
            output.parse(resolved)

    rows = check_mapping_output_coverage(sketch, output)
    for csv_path, output_file, class_iri in args.population:
        rows += check_source_target_population(
            csv_path, Graph().parse(output_file), URIRef(class_iri), args.filtered)

    for row in rows:
        print("{:<8} {:<9} {}".format(row.check_id, row.severity, row.message))
    print("\n{} finding(s) across CT-15 and CT-16.".format(len(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
