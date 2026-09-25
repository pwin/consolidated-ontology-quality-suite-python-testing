# CT-18 — Generated graph uses an unexpected modelling pattern

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `ontologies/model.ttl` | the magnitude pattern and the reading class |
| `data/output.ttl` | two readings, one modelled each way |
| `checks/CMP-018.rq` | the check, with the project rule in its VALUES table |
| `checks/registry.json` | its id, title and severity |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

| | Reading | Where the number sits | Expected |
|---|---|---|---|
| **error** | `reading-R2` | directly on the reading | **reported** |
| **control** | `reading-R1` | on a magnitude node | **silent** |

Nothing here is malformed. The flattened triple is valid RDF, the number
is correct, and every structural check passes. What is lost is the place the
unit was going to go — and by the time someone needs it, the shape is in
production and every consumer has been written against it.

This is the kind of drift that arrives with an older mapping nobody
retired.

## What the run should report

| Check | Focus | Why |
|---|---|---|
| `CMP-018` | `reading-R2` | **the point of the fixture** |
| `CNF-003` | reading-R2 | the same fault seen by a registry check: gist:numericValue has domain gist:Magnitude, and the flattened triple hangs it off a :Reading. Worth knowing that the conformance layer catches this from its own angle -- it reports a domain violation where CMP-018 reports a pattern the project did not agree to |

`run.sh` fails if `CMP-018` is missing for `reading-R2`, if it appears
for `reading-R1`, or if anything else is reported at all.

## What was left out, and why

- a unit on either reading, which would make this CT-20's question
- a second flattened property
