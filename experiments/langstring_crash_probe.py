"""Why did `ontology-quality-suite data` crash on a language-tagged literal?

FIXED UPSTREAM in ontology-quality-suite 0.14.3. Against 0.14.2 and earlier
this probe reproduced the crash; against >= 0.14.3 it is a regression check --
both rows below should report, neither should raise.

Found while adding a fixture for DAT-003 ("duplicate literal values"), which
needs two literals carrying the same lexical form -- the natural way to build
one being the same text under two language tags.

`dataquality/data_quality.py::check_conformance` computes the effective
datatype of a literal value like this:

    actual = o.datatype or (RDFS.langString if o.language else XSD.string)

`langString` is not an RDFS term. RDF 1.1 puts it in the RDF namespace --
`rdf:langString` -- and rdflib's `RDFS` is a closed `DefinedNamespace`, so the
attribute access raises rather than returning a wrong-but-harmless IRI:

    AttributeError: term 'langString' not in namespace
    'http://www.w3.org/2000/01/rdf-schema#'

It is a crash, not a misreported finding: the whole `data` stage stops, and
with it every other check that run would have made.

Three conditions have to coincide, and all three are ordinary:

    1. a property whose rdfs:range names an XSD datatype (and is not
       rdfs:Literal, which short-circuits above this line),
    2. a language-tagged value for that property in the data,
    3. any stage that calls check_conformance -- `data`, `sketch --ontology`,
       or `run`.

`rdfs:range xsd:string` with a `"..."@en` value is the everyday case.

    uv run python experiments/langstring_crash_probe.py
"""
from __future__ import annotations

from rdflib import Graph

from ontology_suite.dataquality import data_quality

ONTOLOGY = """
@prefix :    <https://example.org/probe#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

:Widget a owl:Class .
:note a owl:DatatypeProperty ;
    rdfs:domain :Widget ;
    rdfs:range  xsd:string .
"""

TAGGED = """
@prefix : <https://example.org/probe#> .
:widget-1 a :Widget ; :note "Checked"@en .
"""

UNTAGGED = """
@prefix : <https://example.org/probe#> .
:widget-1 a :Widget ; :note "Checked" .
"""


def attempt(label: str, data_turtle: str) -> None:
    declarations = data_quality.ontology_declarations(Graph().parse(data=ONTOLOGY, format="turtle"))
    data = Graph().parse(data=data_turtle, format="turtle")
    try:
        conformance = data_quality.check_conformance(declarations, data)
    except AttributeError as exc:
        print("  {:<28} CRASH  AttributeError: {}".format(label, exc))
        return
    violations = sum(len(v) for v in conformance["range_violations"].values())
    print("  {:<28} ok     {} range violation(s)".format(label, violations))


def main() -> None:
    print("check_conformance against :note, whose rdfs:range is xsd:string\n")
    attempt('"Checked" (untagged)', UNTAGGED)
    attempt('"Checked"@en (tagged)', TAGGED)
    print()
    print("Fixed in 0.14.3, in one word: RDF.langString, which that module already")
    print("imports. The correct value also changes the answer rather than merely")
    print("unblocking it -- a langString is not an xsd:string, so the tagged literal")
    print("is a genuine CNF-004 range violation and is now reported as one. Declare")
    print("the range rdfs:Literal if tagged values are what you intend.")


if __name__ == "__main__":
    main()
