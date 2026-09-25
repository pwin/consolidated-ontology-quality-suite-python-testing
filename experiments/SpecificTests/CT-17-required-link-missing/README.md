# CT-17 — Required object property missing from a generated entity

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `ontologies/model.ttl` | the classes and the link, with no cardinality axiom |
| `data/output.ttl` | two pump stations, one linked and one not |
| `checks/CMP-017.rq` | the check, with the project rule in its VALUES table |
| `checks/registry.json` | its id, title and severity |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

| | Entity | Class | `:atSite` | Expected |
|---|---|---|---|---|
| **error** | `asset-A2` | `:PumpStation` | **none** | **reported** |
| **control** | `asset-A1` | `:PumpStation` | `site-S1` | **silent** |

The ontology says `:atSite` has domain `:PumpStation` and range `:Site`.
It does not say every pump station must have one — that rule lives in the
mapping specification, where most cardinality rules live long before anyone
writes them into the TBox. So no registry check reports this, and the
project carries its own.

The failure is quiet by construction: one empty cell in one source row leaves
one variable unbound, and SPARQL drops just the triples that use it. The
entity is still built, still typed, still labelled — and missing the link
that made it useful.

## What the run should report

| Check | Focus | Why |
|---|---|---|
| `CMP-017` | `asset-A2` | **the point of the fixture** |

`run.sh` fails if `CMP-017` is missing for `asset-A2`, if it appears
for `asset-A1`, or if anything else is reported at all.

## What was left out, and why

- an `owl:FunctionalProperty` or cardinality axiom, which would move this to
  the reasoner and make the fixture about `LOG-002` instead
- a second entity missing a second link
