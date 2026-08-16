"""Why is `"yes"^^xsd:boolean` not reported by DAT-001?

Fixture 06 seeds three ill-formed literals -- an xsd:date, an xsd:integer and
an xsd:boolean -- but DAT-001 ("literal lexical form invalid for its
datatype") only reports two of them.

DAT-001 tests the lexical form with a regex: `?dt = xsd:boolean &&
!REGEX(STR(?lit), "^(true|false|1|0)$")`. That works for date and integer,
where rdflib keeps the original lexical form and just leaves `.value` None.
For xsd:boolean, rdflib *rewrites* the lexical form to "false" while flagging
the literal `ill_typed=True` -- so by the time the check runs, the invalid
lexical form no longer exists in the graph and the regex can never fail.

FIXED UPSTREAM in ontology-quality-suite 0.6.0 (commit 2f4950c), which added
`checks/literal_typing.py`: a Python-side pass over the loaded graph using
`rdflib.term.Literal.ill_typed`, supplementing both portable formulations.
Fixture 06 now reports DAT-001 three times instead of two, with the extra
finding attributed to source `literal-typing`.

What this probe still shows is *why* the SPARQL/SHACL formulations alone
cannot see it -- the invalid lexical form is gone before any query runs -- so
the regex branch below still matches nothing even on a fixed suite.

    uv run python experiments/illtyped_boolean_probe.py
"""
from __future__ import annotations

from pathlib import Path

from rdflib import Graph, Literal

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "ontologies" / "06-datatype-conformance" / "data.ttl"

DAT_001_BOOLEAN_BRANCH = """
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?s ?lit WHERE {
  ?s ?p ?lit .
  FILTER(isLiteral(?lit))
  BIND(DATATYPE(?lit) AS ?dt)
  FILTER(?dt = xsd:boolean && !REGEX(STR(?lit), "^(true|false|1|0)$"))
}
"""


def main() -> None:
    graph = Graph().parse(DATA, format="turtle")

    print(f"{DATA.name}: literals as authored vs. as stored by rdflib\n")
    print(f"  {'predicate':12} {'authored':14} {'stored lexical':16} {'.value':8} ill_typed")
    authored = {"headcount": "twelve", "isActive": "yes", "birthDate": "31-12-1990 / 1990-01-01"}
    for _s, p, o in sorted(graph, key=lambda t: str(t[1])):
        if not isinstance(o, Literal) or o.datatype is None:
            continue
        local = str(p).rsplit("#", 1)[-1]
        print(f"  {local:12} {authored.get(local, ''):14} {str(o)!r:16} {str(o.value):8} {o.ill_typed}")

    hits = list(graph.query(DAT_001_BOOLEAN_BRANCH))
    print(f"\nDAT-001 boolean branch matches: {len(hits)}  (the seeded 'yes' is invisible to it)")

    ill = [(s, p, o) for s, p, o in graph if isinstance(o, Literal) and o.ill_typed]
    print(f"Literals rdflib itself flags as ill_typed: {len(ill)}")
    for _s, p, o in ill:
        print(f"    {str(p).rsplit('#', 1)[-1]:12} {o!r}")


if __name__ == "__main__":
    main()
