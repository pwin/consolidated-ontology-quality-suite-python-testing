# CT-2 — Same IRI used for different concepts

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `ontologies/model.ttl` | the two unrelated classes |
| `data/output.ttl` | the graph the mappings produced -- one collision, one clean node |
| `checks/CMP-002.rq` | the check, carried by this folder |
| `checks/registry.json` | its id, title and severity |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

| | Node | Types | Expected |
|---|---|---|---|
| **error** | `node-A1` | `:Site`, `:Reading` | **reported** |
| **control** | `site-S2` | `:Site` | **silent** |

A collision like this is invisible in the query text when the two
mappings build the identifier from differently-named columns: each `BIND`
reads fine, and only the output shows one IRI wearing two hats. So the
question has to be asked of the graph.

The check excludes `owl:NamedIndividual`, `owl:Thing` and `rdfs:Resource`,
and any pair where one class is a subclass of the other — a thing being both
a `:Site` and a `:PumpingStation` is a hierarchy, not a collision.

## What the run should report

| Check | Focus | Why |
|---|---|---|
| `CMP-002` | `node-A1` | **the point of the fixture** |

`run.sh` fails if `CMP-002` is missing for `node-A1`, if it appears
for `site-S2`, or if anything else is reported at all.

## What was left out, and why

- a subclass pair, which would be correct and would make the exclusion
  above look like a failure to detect something
- any second collision
