# CT-20 — Magnitude missing a unit of measure

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `ontologies/model.ttl` | the gist magnitude pattern, declared locally so the fixture runs offline |
| `data/output.ttl` | two flow rates, one with a unit and one without |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

| | Node | `gist:numericValue` | `gist:hasUnitOfMeasure` | Expected |
|---|---|---|---|---|
| **error** | `flow-S2` | `47.0` | **none** | **reported** |
| **control** | `flow-S1` | `120.5` | `:LitrePerSecond` | **silent** |

A magnitude without its unit is not an incomplete record, it is a
meaningless one: 47 of what? The damage is that it does not look broken.
Anything reading `gist:numericValue` will happily average it with the
litres-per-second above and return an answer that is arithmetically perfect
and physically nonsense.

## What the run should report

| Check | Focus | Why |
|---|---|---|
| `DAT-004` | `flow-S2` | **the point of the fixture** |
| `STR-004` | the gist classes | a class with no superclass and no equivalence axiom is formally undefined. These are declared locally so the fixture runs offline, without the gist hierarchy that would define them |

`run.sh` fails if `DAT-004` is missing for `flow-S2`, if it appears
for `flow-S1`, or if anything else is reported at all.

## What was left out, and why

- any unit that is wrong rather than missing — that is CT-21, a different
  question with a different answer
- a magnitude with no number — that is CT-19
