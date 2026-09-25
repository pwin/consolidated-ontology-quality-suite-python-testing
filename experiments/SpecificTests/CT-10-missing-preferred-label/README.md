# CT-10 — Missing preferred label

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `ontologies/model.ttl` | two classes, identical but for the label under test |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

| | Class | `rdfs:label` | `skos:prefLabel` | Expected |
|---|---|---|---|---|
| **error** | `:Asset` | yes | **no** | **reported** |
| **control** | `:Site` | yes | yes | **silent** |

`rdfs:label` and `skos:prefLabel` are not interchangeable. A term with
only the first looks labelled in a diagram and is missing from every list
built from the preferred term — a glossary, a picklist, a search index.

Which check reports it is the other half of the lesson. `QUA-004` asks for a
preferred label and accepts `rdfs:label` instead, so it stays silent here;
`QUA-009` is the strict form and is the one that fires. A project chooses
which rule it wants, and this fixture is the difference between them.

## What the run should report

| Check | Focus | Why |
|---|---|---|
| `QUA-009` | `#Asset` | **the point of the fixture** |

`run.sh` fails if `QUA-009` is missing for `#Asset`, if it appears
for `#Site`, or if anything else is reported at all.

## What was left out, and why

- `dcterms:title` in the header — an undeclared external property is three
  findings of its own, none about labelling
- any term missing a definition — that is CT-8, and one fault per folder
