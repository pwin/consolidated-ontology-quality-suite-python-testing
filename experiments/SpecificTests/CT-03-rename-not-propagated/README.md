# CT-3 — IRI construction pattern not updated following a model change

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus the whole report
```

| Path | What it is |
|---|---|
| `ontologies/model-v1.ttl` | the model the mapping was written against |
| `ontologies/model-v2.ttl` | the same model with one class renamed |
| `queries/assets.rq` | the mapping, never updated — carries the fault and the control |
| `out/` | `consistency.txt`, plus `repairs/` holding the suggested patch |

## The two sets

| | Term | v1 | v2 | The mapping builds | Expected |
|---|---|---|---|---|---|
| **error** | pump station | `:PumpStation` | `:PumpingStation` | `:PumpStation` | **reported** |
| **control** | site | `:Site` | `:Site` | `:Site` | **silent** |

## Why this one needs two files

The fault is in none of them. `model-v2.ttl` is a correct ontology.
`assets.rq` is a correct query — valid SPARQL, well-formed IRIs, and correct
against the model it was written for. Only read against each other is
anything wrong, which is why no single-file check finds this and why the
command takes both versions and the queries at once.

What it produces is not merely "a term is missing" but the pairing: the
removed class and the added one are matched, so the report names the term to
move *to*. That is the difference between a substitution and a search.

## What the run should report

- `undeclared_class` for `:PumpStation` — the mapping builds a class 2.0.0
  does not declare
- a `rename_iri` repair pairing `:PumpStation` with `:PumpingStation`, written
  as a `.patch` under `out/repairs`
- a MAJOR version bump, since a class was removed
- nothing whatever about `:Site`

`run.sh` asserts each of those, including that no prefix misalignment is
reported: both files bind `:` to the same namespace, so a finding there would
be false.

That last assertion needs **suite 0.21.0**. Before it, the ontology's own
default namespace was reported as one nothing declares — the loader skipped
`@prefix :` declarations, so the namespace IRI went missing along with the
prefix name, and every mapping using it was told its namespace was unknown.

## What was left out, and why

- `dcterms:title` in either header — an undeclared external property is
  three findings of its own, none of them about renaming
- any second change between the versions. One rename, one control, nothing
  else moved, so the MAJOR bump is attributable too
