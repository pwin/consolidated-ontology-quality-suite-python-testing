# CT-32 — Template asserts a property the class does not have

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `ontologies/model.ttl` | two classes and a property with a declared domain |
| `queries/assets.rq` | one template using the property correctly and one not |
| `checks/CMP-032.rq` | the check, carried by this folder |
| `checks/registry.json` | its id, title and severity |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

| | Variable | Typed as | Carries `:atSite` | Expected |
|---|---|---|---|---|
| **error** | `?other_site_IRI` | `:Site` | yes | **reported** |
| **control** | `?asset_IRI` | `:PumpStation` | yes | **silent** |

The suite already reports this as `CNF-003` — of real output, after the
CSVs are read and the mappings have run. Everything needed to know it earlier
is in the query text: the template says which class it builds and what it
hangs off it, and the ontology says where the property belongs.

This mapping is wired to no CSV, which settles the argument. It will never be
triplified, so a check that waits for output waits forever, and the defect
ships.

## What the run should report

| Check | Focus | Why |
|---|---|---|
| `CMP-032` | `other_site_IRI` | **the point of the fixture** |

`run.sh` fails if `CMP-032` is missing for `other_site_IRI`, if it appears
for `asset_IRI`, or if anything else is reported at all.

## What was left out, and why

- nothing, in the data. The noise in the allowed list is the sketch's own
  placeholder terms, and trimming it would mean trimming the sketch
