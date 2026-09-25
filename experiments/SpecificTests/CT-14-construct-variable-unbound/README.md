# CT-14 — Construct variable used but never defined

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `ontologies/model.ttl` | the two terms the query builds, declared |
| `queries/readings.rq` | one bound constructed variable and one unbound |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

| | Variable | In the template | Bound in the query | Expected |
|---|---|---|---|---|
| **error** | `?site_IRI` | yes | **no** | **reported** |
| **control** | `?reading_IRI` | yes | yes | **silent** |

An unbound variable in a CONSTRUCT template is not always wrong: TARQL
binds each CSV header as a variable of that name, so a name matching a column
is bound at triplify time and correct. The `_IRI` suffix is what settles it —
the project's convention for a variable the query itself constructs, which no
CSV can supply. So `?site_IRI` is a Violation and a bare `?sitename` would be
an Info asking a reviewer to check the column exists.

The severity split is why the control shares the suffix: both variables
follow the convention, and only one is bound.

## What the run should report

| Check | Focus | Why |
|---|---|---|
| `TQL-002` | `site_IRI` | **the point of the fixture** |

`run.sh` fails if `TQL-002` is missing for `site_IRI`, if it appears
for `reading_IRI`, or if anything else is reported at all.

## What was left out, and why

- a CSV-column variable, which would add the Info-severity `TQL-003` and a
  second thing to explain
- any second unbound variable
