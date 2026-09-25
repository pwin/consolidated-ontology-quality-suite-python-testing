# CT-21 — Unit of measure incompatible with the quantity

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `ontologies/model.ttl` | two quantity classes and the unit pattern |
| `data/output.ttl` | the same unit used correctly once and wrongly once |
| `checks/CMP-021.rq` | the check, with the project's unit rules in its VALUES table |
| `checks/registry.json` | its id, title and severity |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

| | Node | Class | Unit | Expected |
|---|---|---|---|---|
| **error** | `pressure-R1` | `:Pressure` | `:LitrePerSecond` | **reported** |
| **control** | `flow-R1` | `:FlowRate` | `:LitrePerSecond` | **silent** |

The same unit appears on both nodes, which is what makes the control
worth having: the unit is not wrong in itself, only wrong *for this
quantity*. A check that keyed on the unit alone would report both or
neither.

Nothing structural can see this. `:LitrePerSecond` is a declared unit, the
link is the right link, the range is satisfied. It takes a project rule
pairing quantity kinds with the units that measure them.

## What the run should report

| Check | Focus | Why |
|---|---|---|
| `CMP-021` | `pressure-R1` | **the point of the fixture** |
| `CNF-005` | gist:Magnitude | a parent class that exists to be specialised is never populated directly -- every instance here is a :FlowRate or a :Pressure. True of any hierarchy, and Info severity for that reason |

`run.sh` fails if `CMP-021` is missing for `pressure-R1`, if it appears
for `flow-R1`, or if anything else is reported at all.

## What was left out, and why

- a magnitude with no unit at all, which is CT-20
- units of the same dimension but different scale, which is a conversion
  question rather than a category error
