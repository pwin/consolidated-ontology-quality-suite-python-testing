# CT-19 — Magnitude missing a numeric value

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `ontologies/model.ttl` | the gist magnitude pattern, declared locally |
| `data/output.ttl` | two magnitudes, one with a number and one without |
| `checks/CMP-019.rq` | the check, carried by this folder |
| `checks/registry.json` | its id, title and severity |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

| | Node | `gist:numericValue` | `gist:hasUnitOfMeasure` | Expected |
|---|---|---|---|---|
| **error** | `flow-S2` | **none** | `:LitrePerSecond` | **reported** |
| **control** | `flow-S1` | `120.5` | `:LitrePerSecond` | **silent** |

The mirror of CT-20. That one has a number and no unit; this has a unit
and no number. Both are magnitudes that survive every structural check —
correctly typed, correctly linked — and mean nothing.

This one is the more deceptive of the two, because it counts. A report of
"how many readings did we load" finds it present and correct.

## What the run should report

| Check | Focus | Why |
|---|---|---|
| `CMP-019` | `flow-S2` | **the point of the fixture** |

`run.sh` fails if `CMP-019` is missing for `flow-S2`, if it appears
for `flow-S1`, or if anything else is reported at all.

## What was left out, and why

- a magnitude missing its unit, which is CT-20
- any unit that is wrong for the quantity, which is CT-21
