# CT-22 — Numeric datatype or conversion error

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `ontologies/model.ttl` | two decimal-ranged properties |
| `queries/readings.rq` | two variables following the same naming convention, one typed |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

| | Variable | Bound by | Datatype | Expected |
|---|---|---|---|---|
| **error** | `?flow_DT` | `CONCAT(?flow, "")` | **none — a plain string** | **reported** |
| **control** | `?pressure_DT` | `STRDT(?pressure, xsd:decimal)` | `xsd:decimal` | **silent** |

The check reads a naming convention, which is the only thing that makes
the question answerable from the query text alone. `_DT` says the author
meant this variable to carry a datatype; the expression beside it says
whether they did. A variable without the suffix is not reported, because a
plain string may be exactly what was wanted.

The cost of the untyped one is not a wrong number but a string that looks
like one: it sorts as text, fails every numeric comparison silently, and the
`xsd:decimal` range on the property is missed without anything being
malformed.

## What the run should report

| Check | Focus | Why |
|---|---|---|
| `TQL-005` | `flow_DT` | **the point of the fixture** |

`run.sh` fails if `TQL-005` is missing for `flow_DT`, if it appears
for `pressure_DT`, or if anything else is reported at all.

## What was left out, and why

- the data-side half of CT-22, where a range violation becomes `CNF-004`.
  That needs triplified output; this folder asks the question of the query,
  where it can be answered before any data exists
