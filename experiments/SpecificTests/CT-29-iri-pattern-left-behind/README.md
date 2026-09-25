# CT-29 — IRI construction pattern not updated after a concept moved namespace

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `ontologies/core.ttl` | the shared model, and the only file that knows `:Site` moved |
| `queries/assets.rq` | the mapping, minting one moved concept and one that stayed |
| `checks/CMP-029.rq` | the check, joining the BIND facts, the sketch and the core model |
| `checks/registry.json` | its id, title and severity |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

| | Variable | Minted under | Agreed base | Expected |
|---|---|---|---|---|
| **error** | `?site_IRI` | `…/water/data/site-` | `…/core/data/site-` | **reported** |
| **control** | `?asset_IRI` | `…/water/data/asset-` | none — never moved | **silent** |

Nothing that reads one artefact can see this. The query is valid SPARQL,
builds a well-formed IRI, and is correct against the water model, which still
declares `:Site`. Only `core.ttl` knows the concept moved and took its agreed
base with it, and only the BIND facts know what the mapping actually
CONCATs.

So the check is the join of three files, which is why it needs the merge step
rather than a single stage.

## What the run should report

| Check | Focus | Why |
|---|---|---|
| `CMP-029` | `site_IRI` | **the point of the fixture** |

`run.sh` fails if `CMP-029` is missing for `site_IRI`, if it appears
for `asset_IRI`, or if anything else is reported at all.

## What was left out, and why

- the water model itself. It would say `:Site` is fine, which is exactly the
  reading that lets this defect through
