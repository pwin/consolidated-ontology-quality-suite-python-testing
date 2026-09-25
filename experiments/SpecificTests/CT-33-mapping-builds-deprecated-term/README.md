# CT-33 — Mapping still builds a term the model deprecates

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `ontologies/model.ttl` | a deprecated class, its replacement, and a current one |
| `queries/assets.rq` | the mapping, building one of each |
| `checks/CMP-033.rq` | the check, carried by this folder |
| `checks/registry.json` | its id, title and severity |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

| | Class the mapping builds | `owl:deprecated` | Expected |
|---|---|---|---|
| **error** | `:PumpStation` | **true**, replaced by `:PumpingStation` | **reported** |
| **control** | `:Site` | no | **silent** |

`QUA-003` asks this of an ontology and of data. Neither reaches the
mappings — and the mapping is where the use originates: the data is only
deprecated because the transformation that produced it is. Catching it here
is the difference between changing one query and reprocessing a graph.

The deprecation notice lives in the ontology, which is exactly where the
person maintaining the mapping is not looking.

## What the run should report

| Check | Focus | Why |
|---|---|---|
| `CMP-033` | `PumpStation` | **the point of the fixture** |

`run.sh` fails if `CMP-033` is missing for `PumpStation`, if it appears
for `#Site>`, or if anything else is reported at all.

## What was left out, and why

- a deprecated *property* as well, which would make the same point twice
