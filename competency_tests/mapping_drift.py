"""CT-34 to CT-36 and CT-38 -- drift between an ontology and a *set* of TARQL
mappings.

CT-37 was here too until suite 0.16.0 began publishing each query's PREFIX
table as tq:PrefixBinding; it is checks/sparql/tarql/CMP-037.rq now, and
reads better for it.

Each check here needs something a single merged graph cannot express, which
is why none of them is a `.rq` file like CMP-032 and CMP-033:

  CT-34, CT-35         need to know *which file* said what, which the
                       suite's build_sketch_dataset now answers with a named
                       graph per query file.
  CT-36                needs the ontology's owl:imports closure as distinct
                       from the pile of files handed to the checker.
  CT-38                needs a stored expectation to compare against.

All five are about a mapping *set*. A project with one ontology file and one
query has none of these problems; they appear with the second file, which is
also when nobody is reading every file at once any more.

    uv run python competency_tests/mapping_drift.py \
      --queries competency_tests/fixtures/model/queries \
      --ontology competency_tests/fixtures/model/ontology/water-v1.ttl \
      --integration competency_tests/fixtures/model/ontology/integration.ttl \
      --golden competency_tests/fixtures/model/outputs/golden-assets.ttl \
      --output competency_tests/results/triplified/assets.ttl
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF

from ontology_suite.checks.merge import ResultRow
from ontology_suite.ontologyeval import ontology_evaluation as onteval
from ontology_suite.sketch import bind_analysis
from ontology_suite.sketch import prefix_alignment as pa

HERE = Path(__file__).resolve().parent
QUERY_GLOB = "**/*.rq"


def _row(check_id: str, severity: str, focus: str, message: str,
         path: Optional[str] = None, value: Optional[str] = None) -> ResultRow:
    return ResultRow(
        check_id=check_id, category="competency", title=None, severity=severity,
        focus_node=focus, path=path, value=value, message=message,
        remediation=None, sources=["mapping-drift"],
    )


def query_files(queries_dir: Path) -> List[Path]:
    return sorted(queries_dir.glob(QUERY_GLOB))


def sketch_per_file(queries: Path) -> Dict[str, Graph]:
    """One sketch graph per query file, keyed by file name.

    build_sketch_dataset (suite 0.16.0) puts each file's triples in a named
    graph named after it, which is the fact these checks are built on: the
    merged sketch cannot tell one class built two ways by two files from one
    class built one way. Before that existed this called build_sketch_graph
    once per file and kept its own table.
    """
    dataset = pa.build_sketch_dataset([queries], QUERY_GLOB)
    return {str(graph.identifier).rsplit("/", 1)[-1]: graph
            for graph in dataset.graphs()
            if str(graph.identifier).startswith(str(bind_analysis.TQD))}


# --------------------------------------------------------------------------
# CT-34: one class, different shapes depending on which mapping built it
# --------------------------------------------------------------------------
def compare_class_shapes(sketches: Dict[str, Graph]) -> List[ResultRow]:
    """A class whose instances carry different predicates per source file.

    Not a disagreement any single file can see: each mapping builds a
    perfectly reasonable entity, and only the union is lopsided. The
    consequence lands on whoever queries the result and finds that half the
    sites have a name.
    """
    shapes: Dict[URIRef, Dict[str, Set[URIRef]]] = defaultdict(dict)
    for source, graph in sketches.items():
        for subject, _p, cls in graph.triples((None, RDF.type, None)):
            predicates = {p for _s, p, _o in graph.triples((subject, None, None))
                          if p != RDF.type}
            if isinstance(cls, URIRef):
                shapes[cls].setdefault(source, set()).update(predicates)

    rows: List[ResultRow] = []
    for cls, by_source in sorted(shapes.items(), key=lambda kv: str(kv[0])):
        if len(by_source) < 2:
            continue
        distinct = {frozenset(preds) for preds in by_source.values()}
        if len(distinct) < 2:
            continue
        detail = "; ".join(
            "{} builds it with {}".format(
                source, ", ".join(sorted(str(p).rsplit("#", 1)[-1] for p in preds)) or "no properties")
            for source, preds in sorted(by_source.items()))
        rows.append(_row(
            "CMP-034", "Warning", str(cls),
            "{} is built by more than one mapping and not the same way each time -- {}. "
            "Whoever consumes the result gets instances of one class whose shape depends on "
            "which file happened to make them.".format(str(cls), detail),
            path=None, value=str(len(by_source))))
    return rows


# --------------------------------------------------------------------------
# CT-35: one predicate, different datatypes depending on the mapping
# --------------------------------------------------------------------------
def compare_predicate_datatypes(sketches: Dict[str, Graph],
                                paths: Sequence[Path]) -> List[ResultRow]:
    """A predicate whose value is typed in one mapping and not in another.

    The datatype is not in the sketch: a template's objects are variables, so
    the sketch renders them as terms and the type only exists in the BIND
    that fills them. This therefore reads both -- the template says which
    predicate a variable feeds, the BIND expression says what type it gives
    it -- which is also why it cannot be a SPARQL check over one graph.

    The expression is read for an xsd: term rather than evaluated. A
    STRDT(?x, xsd:decimal) types its value and a CONCAT does not, and the
    difference between the two is the whole finding.
    """
    from ontology_suite.sketch import bind_analysis

    by_predicate: Dict[URIRef, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
    for path in paths:
        report = bind_analysis.analyse([str(path)])
        expressions = {bind.target: bind.expression
                       for query in report.queries for bind in query.binds}
        graph = sketches[path.name]
        for _subject, predicate, obj in graph:
            if predicate == RDF.type or not isinstance(obj, URIRef):
                continue
            variable = str(obj).rsplit("#", 1)[-1].rsplit("/", 1)[-1]
            if variable not in expressions:
                continue
            by_predicate[predicate][path.name].add(_datatype_of(expressions[variable]))

    rows: List[ResultRow] = []
    for predicate, by_source in sorted(by_predicate.items(), key=lambda kv: str(kv[0])):
        seen = {dt for types in by_source.values() for dt in types}
        if len(by_source) < 2 or len(seen) < 2:
            continue
        detail = "; ".join("{} gives it {}".format(source, ", ".join(sorted(types)))
                           for source, types in sorted(by_source.items()))
        rows.append(_row(
            "CMP-035", "Violation", str(predicate),
            "{} is filled with more than one datatype across the mapping set -- {}. One "
            "property whose values will not compare, sort or aggregate against each other, "
            "and no single file looks wrong.".format(str(predicate), detail),
            path=str(predicate), value=", ".join(sorted(seen))))
    return rows


XSD_IN_EXPRESSION = re.compile(r"xsd:([A-Za-z]+)|XMLSchema#([A-Za-z]+)")


def _datatype_of(expression: str) -> str:
    """The datatype a BIND expression gives its value, as written.

    "(untyped)" covers both the plain-string case and anything this cannot
    read: a check that guessed would be worse than one that says the two
    files differ and lets a person look.
    """
    match = XSD_IN_EXPRESSION.search(expression)
    return "xsd:" + (match.group(1) or match.group(2)) if match else "(untyped)"


# --------------------------------------------------------------------------
# CT-36: a term that resolves only because every file was passed by hand
# --------------------------------------------------------------------------
def check_import_closure(sketches: Dict[str, Graph], integration: Path,
                         ontology_files: Sequence[Path],
                         import_dir: Optional[Path] = None) -> List[ResultRow]:
    """Terms the mappings build that the integration ontology cannot reach.

    Two graphs, deliberately built differently: the closure is what
    owl:imports actually pulls in from the integration file, and the pile is
    every ontology file a person listed on the command line. A term in the
    second but not the first passes every check today and breaks for the
    first consumer who loads the ontology the way it says it should be
    loaded.
    """
    closure, report = onteval.resolve_imports(
        str(integration), import_dir=str(import_dir) if import_dir else None)
    pile = Graph()
    for path in ontology_files:
        pile.parse(path)

    declared_in_closure = {s for s in closure.subjects() if isinstance(s, URIRef)}
    declared_in_pile = {s for s in pile.subjects() if isinstance(s, URIRef)}

    used: Dict[URIRef, Set[str]] = defaultdict(set)
    for source, graph in sketches.items():
        for subject, predicate, obj in graph:
            for term in (predicate, obj):
                if isinstance(term, URIRef):
                    used[term].add(source)

    # Grouped by namespace rather than listed per term: one unimported
    # vocabulary is one decision to make, and printing forty terms from it
    # buries the second vocabulary underneath the first.
    unreachable: Dict[str, Set[URIRef]] = defaultdict(set)
    for term in used:
        if term in declared_in_closure or term not in declared_in_pile:
            continue
        unreachable[_namespace(term)].add(term)

    rows: List[ResultRow] = []
    for namespace, terms in sorted(unreachable.items()):
        example = sorted(terms, key=str)[0]
        sources = sorted({source for term in terms for source in used[term]})
        rows.append(_row(
            "CMP-036", "Violation", namespace,
            "The mappings build {} term(s) in <{}> -- {} among them, from {} -- that are declared "
            "in a file passed on the command line but that nothing reachable from {} through "
            "owl:imports declares. Those checks pass because of how they were invoked, not "
            "because the ontology is complete.".format(
                len(terms), namespace, str(example), ", ".join(sources), integration.name),
            path=None, value=str(len(terms))))

    if report.get("unresolved"):
        rows.append(_row(
            "CMP-036", "Info", str(integration),
            "{} declares {} owl:imports that did not resolve ({}), so the closure is smaller than "
            "the ontology claims. A term those files would have declared is indistinguishable "
            "here from one nobody declared.".format(
                integration.name, len(report["unresolved"]),
                ", ".join(sorted(str(u) for u in report["unresolved"])[:3])),
            path=None, value=str(len(report["unresolved"]))))

    for clash in report.get("ambiguous", []):
        rows.append(_row(
            "CMP-036", "Warning", str(clash.get("iri")),
            "More than one file claims the ontology IRI {}, and the closure was built from {}. "
            "Which file wins decides what is declared, so this is a coin toss standing where a "
            "decision should be.".format(clash.get("iri"), clash.get("chosen")),
            path=None, value=str(clash.get("chosen"))))
    return rows


def _namespace(term: URIRef) -> str:
    text = str(term)
    cut = max(text.rfind("#"), text.rfind("/"))
    return text[:cut + 1] if cut >= 0 else text


# --------------------------------------------------------------------------
# CT-38: what the model change actually did to the output
# --------------------------------------------------------------------------
def compare_against_golden(golden: Path, produced: Path) -> List[ResultRow]:
    """Triples the mappings no longer produce, or now produce, against a
    stored expectation.

    The review aids (CT-23 to CT-28) already compare two outputs; nothing
    pointed them at "before and after the model changed", which is the
    comparison a reviewer actually wants at a version bump. A golden file
    turns "the ontology moved and the tests still pass" into a list of what
    moved with it.
    """
    if not golden.is_file() or not produced.is_file():
        return []
    before, after = Graph(), Graph()
    before.parse(golden)
    after.parse(produced)

    lost = sorted(before - after, key=lambda t: (str(t[0]), str(t[1])))
    gained = sorted(after - before, key=lambda t: (str(t[0]), str(t[1])))

    rows: List[ResultRow] = []
    for triples, verb, severity in ((lost, "no longer produces", "Violation"),
                                    (gained, "now produces", "Warning")):
        for subject, predicate, obj in triples:
            rows.append(_row(
                "CMP-038", severity, str(subject),
                "Against {}, the mapping set {} <{}> <{}> {}.".format(
                    golden.name, verb, subject, predicate,
                    obj.n3() if isinstance(obj, Literal) else "<{}>".format(obj)),
                path=str(predicate), value=str(obj)))
    return rows


def run_all(queries: Path, ontology_files: Sequence[Path], integration: Path,
            golden: Optional[Path] = None, produced: Optional[Path] = None,
            import_dir: Optional[Path] = None) -> List[ResultRow]:
    paths = query_files(queries)
    sketches = sketch_per_file(queries)
    rows = compare_class_shapes(sketches)
    rows += compare_predicate_datatypes(sketches, paths)
    rows += check_import_closure(sketches, integration, ontology_files, import_dir)
    if golden and produced:
        rows += compare_against_golden(golden, produced)
    return rows


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--queries", required=True, type=Path)
    parser.add_argument("--ontology", action="append", required=True, type=Path, dest="ontologies")
    parser.add_argument("--integration", required=True, type=Path)
    parser.add_argument("--import-dir", type=Path, default=None)
    parser.add_argument("--golden", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    rows = run_all(args.queries, args.ontologies, args.integration,
                   args.golden, args.output, args.import_dir)
    for row in rows:
        print("{:<9} {:<10} {}".format(row.check_id, row.severity, row.message))
    print("\n{} finding(s).".format(len(rows)))
    return 1 if any(r.severity == "Violation" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
