# CT-12 — Labels or definitions declared in TARQL rather than the source model

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `ontologies/declarations.ttl` | what each term is, and deliberately not what it is called |
| `queries/assets.rq` | the mapping, naming one term it should not and one it should |
| `checks/CMP-012.rq` | the check, carried by this folder |
| `checks/registry.json` | its id, title and severity |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

| | Term | Named by | Expected |
|---|---|---|---|
| **error** | `vocab:Reservoir` | the mapping, though the taxonomy owns it | **reported** |
| **control** | `?asset_IRI` | the mapping, which owns its per-row entities | **silent** |

The distinction is ownership, not syntax. Both triples in the template
state a `skos:prefLabel`; one is about a term the taxonomy declares and one
is about a row the mapping itself creates. The second is the mapping's job.

The declarations file carries no labels of its own, and that is what makes
the question answerable: merge the model's own labels into the same graph and
every correctly-labelled term looks exactly like a term the mapping
labelled.

## What the run should report

| Check | Focus | Why |
|---|---|---|
| `CMP-012` | `Reservoir` | **the point of the fixture** |

`run.sh` fails if `CMP-012` is missing for `Reservoir`, if it appears
for `asset_IRI`, or if anything else is reported at all.

## What was left out, and why

- the model's labels, for the reason above
- a definition as well as a label, which would make the same point twice
