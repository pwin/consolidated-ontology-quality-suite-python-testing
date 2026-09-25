# CT-13 — Unexpected unused ontology terms

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `ontologies/model.ttl` | two classes, one populated and one not |
| `data/output.ttl` | the graph the mappings produced -- two sites, no decommissioned ones |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

| | Class | Declared | Populated in the data | Expected |
|---|---|---|---|---|
| **error** | `:DecommissionedSite` | yes | **no** | **reported** |
| **control** | `:Site` | yes | yes | **silent** |

Neither artefact is wrong by itself. The ontology is entitled to declare
a class, and the data is entitled not to contain one. Only the pair says
something: a concept the model promises and the pipeline never delivers,
which is either a mapping nobody wrote or a retirement nobody finished.

Severity Info, deliberately. An unpopulated class is a question, not a
defect — a seasonal class may be empty in January.

## What the run should report

| Check | Focus | Why |
|---|---|---|
| `CNF-005` | `DecommissionedSite` | **the point of the fixture** |
| `STR-004` | :Site | a class with no superclass and no equivalence axiom is formally undefined. True, and unavoidable in a fixture with two terms and nothing to define them against -- giving it owl:Thing as a parent trades this for an unpopulated owl:Thing instead |

`run.sh` fails if `CNF-005` is missing for `DecommissionedSite`, if it appears
for `#Site>`, or if anything else is reported at all.

## What was left out, and why

- any second unpopulated class, including `owl:Thing`, which is why `:Site`
  is the only thing `:DecommissionedSite` is a subclass of
