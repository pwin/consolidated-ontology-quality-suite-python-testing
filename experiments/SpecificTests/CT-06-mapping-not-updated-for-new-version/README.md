# CT-6 — Ontology changes not propagated to TARQL mappings

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `ontologies/model-v2.ttl` | the current model, with the class renamed |
| `queries/assets.rq` | the mapping, written for 1.0.0 -- carrying the fault and the control |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

| | Class the mapping builds | Declared in 2.0.0 | Expected |
|---|---|---|---|
| **error** | `:PumpStation` | **no** — renamed `:PumpingStation` | **reported** |
| **control** | `:Site` | yes | **silent** |

CT-3 asks this of the two ontology versions and gets a *rename*: the
removed and added terms paired, with a repair. This asks it of the query
against the current model alone, and gets an *undeclared class* — no pairing
and no suggestion, because one version cannot know what a term used to be
called.

Both are worth having. This one works when the old version is gone, which is
the usual situation for someone picking up a mapping set they did not
write.

## What the run should report

| Check | Focus | Why |
|---|---|---|
| `CNF-001` | `PumpStation` | **the point of the fixture** |
| `CNF-005` | :PumpingStation | the same story from the other side: 2.0.0's new name is declared and no mapping builds it. A class nothing populates is exactly what a rename leaves behind when only one half is done |

`run.sh` fails if `CNF-001` is missing for `PumpStation`, if it appears
for `#Site>`, or if anything else is reported at all.

## What was left out, and why

- the old version of the ontology, deliberately: with it, this becomes CT-3
- a property renamed as well, which would add CNF-002 and a second thing to
  explain
