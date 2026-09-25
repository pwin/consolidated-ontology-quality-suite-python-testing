# CT-30 — The same entity generated twice under two identifiers

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `ontologies/model.ttl` | the class and the property the project treats as its business key |
| `data/output.ttl` | three sites, two of which are the same site |
| `checks/CMP-030.rq` | the check, with the project rule in its VALUES table |
| `checks/registry.json` | its id, title and severity |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

| | Nodes | `:siteName` | Expected |
|---|---|---|---|
| **error** | `site-S1`, `site-S4` | both `"Northgate"` | **reported once** |
| **control** | `site-S2` | `"Eastbrook"` | **silent** |

The mirror of CT-2. That is one IRI standing for two things; this is two
IRIs standing for one. Neither is visible to a check that reads identifiers,
because both nodes are well formed and complete — the only evidence is the
value a person would use to recognise the thing.

Reported once rather than twice: a duplicate is one problem, and a check that
reported the pair from both ends would double every count in a report.

## What the run should report

| Check | Focus | Why |
|---|---|---|
| `CMP-030` | `site-S1` | **the point of the fixture** |

`run.sh` fails if `CMP-030` is missing for `site-S1`, if it appears
for `site-S2`, or if anything else is reported at all.

## What was left out, and why

- `owl:sameAs` between the two, which would make it a modelling decision
  rather than a duplicate
- a third copy, which would test the pairing arithmetic rather than the
  question
