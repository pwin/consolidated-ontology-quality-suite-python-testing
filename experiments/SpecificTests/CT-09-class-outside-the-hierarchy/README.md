# CT-9 — Class has no place in the class hierarchy

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `ontologies/model.ttl` | three classes: a top, one placed under it, and one orphan |
| `checks/CMP-009.rq` | the check, scoped to this model's own namespace |
| `checks/registry.json` | its id, title and severity |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

| | Class | Superclass | Subclasses | Expected |
|---|---|---|---|---|
| **error** | `:Telemetry` | **none** | **none** | **reported** |
| **control** | `:Site` | `:PhysicalThing` | none | **silent** |

`:PhysicalThing` is the reason the control needs care. It has no
superclass either — it is the top of this model — and reporting it would be
wrong. What separates it from `:Telemetry` is that something is a subclass of
it, so it has a place in the hierarchy by being the top of one rather than by
being unattached.

The registry's `STR-004` asks a neighbouring question — whether a class has
any formal definition at all — and would report both `:PhysicalThing` and
`:Telemetry`. This folder runs only the project check, so the distinction is
the one under test.

## What the run should report

| Check | Focus | Why |
|---|---|---|
| `CMP-009` | `Telemetry` | **the point of the fixture** |

`run.sh` fails if `CMP-009` is missing for `Telemetry`, if it appears
for `#Site>`, or if anything else is reported at all.

## What was left out, and why

- an imported vocabulary, which would put someone else's top classes in
  scope and bury the one term this project can act on
- `owl:Thing` as a universal parent, which places everything and answers the
  question by making it unaskable
