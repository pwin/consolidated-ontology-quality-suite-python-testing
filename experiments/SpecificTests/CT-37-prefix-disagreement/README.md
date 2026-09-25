# CT-37 — Two mappings disagree about what a prefix means

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `queries/assets.rq` | the house style |
| `queries/readings.rq` | internally consistent, and disagreeing with the other file |
| `checks/CMP-037.rq` | the check, a GROUP BY over the published prefix table |
| `checks/registry.json` | its id, title and severity |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

| | Prefix | assets.rq | readings.rq | Expected |
|---|---|---|---|---|
| **error** | `gist:` | `…/gist/` | `…/gist#` | **reported** |
| **control** | `:` | `…/water/model#` | identical | **silent** |

Each file is internally consistent, so nothing per-file fires. What the
term-level checks report downstream is "undeclared term" — naming the file
that happens to be wrong, never the disagreement, and never the other file
holding the other half of it.

The hash-or-slash slip on an external vocabulary is the everyday form. It
survives review because both spellings look right, and the two files are
rarely open at once.

This became a `GROUP BY` in suite 0.16.0, which began publishing each query's
PREFIX table as facts. Before that it was Python, for want of the data rather
than for want of a query.

## What the run should report

| Check | Focus | Why |
|---|---|---|
| `CMP-037` | `prefix/gist` | **the point of the fixture** |

`run.sh` fails if `CMP-037` is missing for `prefix/gist`, if it appears
for `prefix/_empty`, or if anything else is reported at all.

## What was left out, and why

- an ontology, which this question does not need: the disagreement is
  between two mappings and would exist with no model at all
