"""CT-34, CT-35, CT-36, CT-38 -- drift across a *set* of mappings.

Four questions that need something a single merged graph cannot express:

    CT-34  which file built which triple -- one class, two shapes
    CT-35  which file gave a value its datatype -- one property, two types
    CT-36  what the integration ontology can reach, as against what was
           handed to the checker on a command line
    CT-38  what the run produces now, against what was agreed

They are one folder because they read the same mappings and the same
ontologies, and because a project with one mapping has none of these
problems: they appear with the second file, which is also when nobody is
reading every file at once any more.

Self-contained: imports rdflib and the suite's sketch helpers, and nothing
from the repo this sits in. Every finding names the file or files it is
about, because a finding about a *set* is useless without saying which
member.

    python drift.py --queries queries --ontology ontologies/model.ttl \\
        --ontology ontologies/units.ttl --integration ontologies/integration.ttl \\
        --expected expected/readings.ttl --produced out/triplified/readings.ttl
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF

from ontology_suite.ontologyeval import ontology_evaluation as onteval
from ontology_suite.sketch import bind_analysis
from ontology_suite.sketch import prefix_alignment as pa

XSD_IN_EXPRESSION = re.compile(r"xsd:([A-Za-z]+)|XMLSchema#([A-Za-z]+)")


def per_file_sketches(queries: Path):
    """One sketch graph per query file, keyed by file name.

    build_sketch_dataset (suite 0.16.0) puts each file's triples in a named
    graph named after it. Before that existed this meant calling
    build_sketch_graph once per file and keeping the table by hand.
    """
    dataset = pa.build_sketch_dataset([queries], "*.rq")
    return {str(g.identifier).rsplit("/", 1)[-1]: g for g in dataset.graphs()
            if str(g.identifier).startswith(str(bind_analysis.TQD))}


# -- CT-34 ------------------------------------------------------------------
def class_shapes(sketches):
    shapes = defaultdict(dict)
    for source, graph in sketches.items():
        for subject, _p, cls in graph.triples((None, RDF.type, None)):
            if not isinstance(cls, URIRef):
                continue
            predicates = {p for _s, p, _o in graph.triples((subject, None, None)) if p != RDF.type}
            shapes[cls].setdefault(source, set()).update(predicates)

    out = []
    for cls, by_source in sorted(shapes.items(), key=lambda kv: str(kv[0])):
        if len(by_source) < 2 or len({frozenset(v) for v in by_source.values()}) < 2:
            continue
        detail = "; ".join("%s builds it with %s" % (
            source, ", ".join(sorted(str(p).rsplit("#", 1)[-1] for p in preds)) or "no properties")
            for source, preds in sorted(by_source.items()))
        out.append(("CT-34", "CMP-034", "%s -- %s" % (cls, detail), sorted(by_source)))
    return out


# -- CT-35 ------------------------------------------------------------------
def predicate_datatypes(sketches, queries: Path):
    def datatype_of(expression):
        match = XSD_IN_EXPRESSION.search(expression)
        return "xsd:" + (match.group(1) or match.group(2)) if match else "(untyped)"

    by_predicate = defaultdict(lambda: defaultdict(set))
    for path in sorted(queries.glob("*.rq")):
        report = bind_analysis.analyse([str(path)])
        expressions = {b.target: b.expression for q in report.queries for b in q.binds}
        graph = sketches.get(path.name)
        if graph is None:
            continue
        for _s, predicate, obj in graph:
            if predicate == RDF.type or not isinstance(obj, URIRef):
                continue
            variable = str(obj).rsplit("#", 1)[-1].rsplit("/", 1)[-1]
            # A variable with no BIND is a CSV column, which TARQL binds as a
            # plain literal. That is the untyped case, not an absent one --
            # skipping it was why a file that types its value and a file that
            # takes the column straight looked like agreement.
            expression = expressions.get(variable)
            by_predicate[predicate][path.name].add(
                datatype_of(expression) if expression else "(untyped -- a CSV column)")

    out = []
    for predicate, by_source in sorted(by_predicate.items(), key=lambda kv: str(kv[0])):
        seen = {d for types in by_source.values() for d in types}
        if len(by_source) < 2 or len(seen) < 2:
            continue
        detail = "; ".join("%s gives it %s" % (s, ", ".join(sorted(t)))
                           for s, t in sorted(by_source.items()))
        out.append(("CT-35", "CMP-035", "%s -- %s" % (predicate, detail), sorted(by_source)))
    return out


# -- CT-36 ------------------------------------------------------------------
def import_closure(sketches, integration: Path, ontologies, import_dir: Path):
    closure, report = onteval.resolve_imports(str(integration), import_dir=str(import_dir))
    pile = Graph()
    for path in ontologies:
        pile.parse(path)

    in_closure = {s for s in closure.subjects() if isinstance(s, URIRef)}
    in_pile = {s for s in pile.subjects() if isinstance(s, URIRef)}

    used = defaultdict(set)
    for source, graph in sketches.items():
        for _s, p, o in graph:
            for term in (p, o):
                if isinstance(term, URIRef):
                    used[term].add(source)

    unreachable = defaultdict(set)
    for term, sources in used.items():
        if term in in_closure or term not in in_pile:
            continue
        cut = max(str(term).rfind("#"), str(term).rfind("/"))
        unreachable[str(term)[:cut + 1]] |= sources

    out = []
    for namespace, sources in sorted(unreachable.items()):
        declaring = [str(Path(p).name) for p in ontologies
                     if namespace in Path(p).read_text(encoding="utf-8")]
        out.append(("CT-36", "CMP-036",
                    "<%s> is built by %s and declared in %s, but nothing reachable from %s "
                    "through owl:imports declares it"
                    % (namespace, ", ".join(sorted(sources)), ", ".join(declaring) or "no file given",
                       integration.name),
                    sorted(sources) + declaring + [integration.name]))
    for unresolved in sorted(report.get("unresolved", [])):
        out.append(("CT-36", "CMP-036",
                    "%s declares an owl:imports of <%s> that did not resolve, so the closure is "
                    "smaller than the ontology claims" % (integration.name, unresolved),
                    [integration.name]))
    return out


# -- CT-38 ------------------------------------------------------------------
def against_expected(expected: Path, produced: Path):
    if not expected.is_file() or not produced.is_file():
        return [("CT-38", "CMP-038",
                 "no comparison: %s or %s is missing" % (expected.name, produced.name),
                 [expected.name, produced.name])]
    before, after = Graph(), Graph()
    before.parse(expected)
    after.parse(produced)
    out = []
    def render(triple):
        # n3() rather than str(): "1.5" and "1.5"^^xsd:decimal are different
        # triples, and printing both as 1.5 tells a reader nothing changed.
        return " ".join(term.n3() for term in triple)

    for triple in sorted(before - after, key=lambda t: (str(t[0]), str(t[1]))):
        out.append(("CT-38", "CMP-038", "no longer produced: " + render(triple),
                    [expected.name, produced.name]))
    for triple in sorted(after - before, key=lambda t: (str(t[0]), str(t[1]))):
        out.append(("CT-38", "CMP-038", "now produced: " + render(triple),
                    [expected.name, produced.name]))
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--queries", required=True, type=Path)
    parser.add_argument("--ontology", action="append", required=True, type=Path, dest="ontologies")
    parser.add_argument("--integration", required=True, type=Path)
    parser.add_argument("--expected", type=Path, default=None)
    parser.add_argument("--produced", type=Path, default=None)
    args = parser.parse_args(argv)

    sketches = per_file_sketches(args.queries)
    findings = (class_shapes(sketches)
                + predicate_datatypes(sketches, args.queries)
                + import_closure(sketches, args.integration, args.ontologies,
                                 args.integration.parent))
    if args.expected and args.produced:
        findings += against_expected(args.expected, args.produced)

    for ct, check, detail, files in findings:
        print("%-6s %-8s %s" % (ct, check, detail))
        print("%14s in: %s" % ("", ", ".join(dict.fromkeys(files))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
