# CT-8 — Missing concept definition

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `ontologies/model.ttl` | two classes, identical but for the thing under test |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

| | Class | Label | prefLabel | Definition | Expected |
|---|---|---|---|---|---|
| **error** | `:Asset` | yes | yes | **no** | **reported** |
| **control** | `:Site` | yes | yes | yes | **silent** |

Naming a concept is not defining it. `:Asset` is labelled and looks complete
in every list and diagram; two people will read the label, reach two
different conclusions about what belongs in it, and the data will be wrong in
a way no schema check can see. The control is there because a check that
reported both would be reporting the presence of a definition as its absence.

## What the run should report

| Check | Focus | Why |
|---|---|---|
| `QUA-010` | `:Asset` | **the point of the fixture** |

`run.sh` fails if `QUA-010` is missing for `:Asset`, if it appears for
`:Site`, or if anything else is reported at all.

## What was left out, and why

- `dcterms:title` in the ontology header. It is an external property, so
  using it undeclared is three findings in its own right — `STR-002`,
  `STR-007` and `QUA-004` — all about the header rather than about whether
  a concept has been defined. `rdfs:label`, `owl:versionIRI` and
  `owl:versionInfo` say everything the header needs to say here.
- Any second undefined term. One fault, in one place.
