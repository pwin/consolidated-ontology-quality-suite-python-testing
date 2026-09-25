# CT-31 — A single-valued relationship carrying more than one value

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `ontologies/model.ttl` | the classes and the link, with no functional declaration |
| `data/output.ttl` | two pump stations, one of them in two places |
| `checks/CMP-031.rq` | the check, with the project rule in its VALUES table |
| `checks/registry.json` | its id, title and severity |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

| | Entity | `:atSite` values | Expected |
|---|---|---|---|
| **error** | `asset-A1` | `site-S1`, `site-S2` | **reported** |
| **control** | `asset-A2` | `site-S2` | **silent** |

The mirror of CT-17: that asks whether a required link is present, this
whether there is exactly one.

Deliberately not `LOG-002` territory. The registry's functional-property
check would report this the moment the ontology declared `:atSite` an
`owl:FunctionalProperty` — and it does not, because the cardinality was
agreed in a mapping specification and never written into the TBox. That is
the ordinary state of a working model, and the reason the project carries the
rule itself.

## What the run should report

| Check | Focus | Why |
|---|---|---|
| `CMP-031` | `asset-A1` | **the point of the fixture** |

`run.sh` fails if `CMP-031` is missing for `asset-A1`, if it appears
for `asset-A2`, or if anything else is reported at all.

## What was left out, and why

- `owl:FunctionalProperty` on `:atSite`, which would move this to LOG-002
  and make the fixture about the reasoner
- a third value, which tests the pairing arithmetic rather than the
  question
