# CT-5 — Core concepts used inconsistently across domains

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `ontologies/model.ttl` | the two shared classes, declared |
| `queries/assets.rq` | one domain's mapping |
| `queries/readings.rq` | the other's -- agreeing about one concept and not the other |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

| | Concept | assets.rq | readings.rq | Expected |
|---|---|---|---|---|
| **error** | `:Site` | `CONCAT("…/site-", ?siteid)` | `CONCAT("…/site-", UCASE(?siteid))` | **reported** |
| **control** | `:Asset` | `CONCAT("…/asset-", ?assetid)` | identical | **silent** |

This is CT-1's check asked of a different situation. CT-1 is one
concept minted two ways; this is a concept *shared between domains* minted
two ways, which is how it happens in practice: two teams, two files, each
correct on its own, and a join that silently returns nothing.

Whether that deserves a separate competency test is a fair question — the
check and the failure are the same, and only the story differs.

## What the run should report

| Check | Focus | Why |
|---|---|---|
| `TQL-001` | `site_IRI` | **the point of the fixture** |

`run.sh` fails if `TQL-001` is missing for `site_IRI`, if it appears
for `asset_IRI`, or if anything else is reported at all.

## What was left out, and why

- CSV columns and triplifying — the disagreement is in the query text, and
  waiting for data to prove it is waiting for the cost to be paid
- any second inconsistency
