"""CT-15 and CT-16 -- what the mapping promised against what it produced.

Two questions, one folder, because both compare the same three things: the
CONSTRUCT templates, the source rows, and the output graph. Neither is
answerable from any one of them.

    CT-15  a (class, predicate) pair the templates define that no instance
           of that class carries in the output
    CT-16  source records in, entities out -- and whether the difference was
           intended

Self-contained: rdflib, the suite's sketch helpers, and the standard library.
Every finding names the files it compared, because "the mapping and the
output disagree" is not actionable until a reader knows which mapping.

    python integrity.py --queries queries --output data/output.ttl \\
        --population csv/readings.csv data/output.ttl \\
        https://example.org/water/model#Reading
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from ontology_suite.sketch import prefix_alignment as pa


def defined_pairs(queries: Path):
    """(class, predicate) pairs the CONSTRUCT templates promise, per file."""
    dataset = pa.build_sketch_dataset([queries], "*.rq")
    pairs = defaultdict(set)
    for graph in dataset.graphs():
        name = str(graph.identifier).rsplit("/", 1)[-1]
        if not name.endswith(".rq"):
            continue
        for subject, _p, cls in graph.triples((None, RDF.type, None)):
            if not isinstance(cls, URIRef):
                continue
            for _s, predicate, _o in graph.triples((subject, None, None)):
                if predicate != RDF.type:
                    pairs[(cls, predicate)].add(name)
    return pairs


def unfilled_pairs(queries: Path, output: Path):
    """CT-15: promised by a template, carried by nothing in the output."""
    graph = Graph()
    graph.parse(output)
    out = []
    for (cls, predicate), sources in sorted(defined_pairs(queries).items(), key=lambda kv: str(kv[0])):
        instances = set(graph.subjects(RDF.type, cls))
        if not instances:
            continue
        if not any((s, predicate, None) in graph for s in instances):
            out.append(("CT-15", "MAP-015",
                        "%s defines %s on %s and no instance of that class carries it in %s"
                        % (", ".join(sorted(sources)), predicate, cls, output.name),
                        sorted(sources) + [output.name]))
    return out


def population(source_csv: Path, output: Path, cls: str, expected_dropped: int):
    """CT-16: source rows in, entities out, against what was intended."""
    with source_csv.open(encoding="utf-8-sig", newline="") as handle:
        rows = sum(1 for _ in csv.DictReader(handle))
    graph = Graph()
    graph.parse(output)
    entities = len(set(graph.subjects(RDF.type, URIRef(cls))))
    dropped = rows - entities
    if dropped == expected_dropped:
        return []
    return [("CT-16", "MAP-016",
             "%d row(s) in %s produced %d %s entities in %s -- %d lost, and the mapping's "
             "filtering rule accounts for %d"
             % (rows, source_csv.name, entities, cls.rsplit("#", 1)[-1], output.name,
                dropped, expected_dropped),
             [source_csv.name, output.name])]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--queries", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--population", nargs=3, metavar=("CSV", "OUTPUT", "CLASS"))
    parser.add_argument("--expected-dropped", type=int, default=0,
                        help="rows the mapping is known to filter out; anything beyond it is a loss")
    args = parser.parse_args(argv)

    findings = unfilled_pairs(args.queries, args.output)
    if args.population:
        source_csv, output, cls = args.population
        findings += population(Path(source_csv), Path(output), cls, args.expected_dropped)

    for ct, check, detail, files in findings:
        print("%-6s %-8s %s" % (ct, check, detail))
        print("%14s in: %s" % ("", ", ".join(dict.fromkeys(files))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
