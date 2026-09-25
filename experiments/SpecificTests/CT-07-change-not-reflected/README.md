# CT-7 — Changes not consistently reflected across dependent artefacts

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus both reports
```

| Path | What it is |
|---|---|
| `ontologies/model-v1.ttl` | the baseline both comparisons start from |
| `ontologies/model-v2-breaking.ttl` | a class removed |
| `ontologies/model-v1-1-compatible.ttl` | a class added, nothing removed |
| `out/` | `breaking/diff.txt` and `compatible/diff.txt` |

## The two sets

| | Comparison | The change | Expected |
|---|---|---|---|
| **error** | 1.0.0 → 2.0.0 | `:PumpStation` **removed** | **MAJOR** |
| **control** | 1.0.0 → 1.1.0 | `:Reservoir` added | **MINOR** |

The question is not "did anything change" — something always has. It is how
much the change obliges everyone else to change, and the answer is the
difference between a version number people can ignore and one they cannot.

Removing a class breaks every mapping, query, document and downstream graph
that names it: MAJOR. Adding one breaks nothing that already existed: MINOR.
A tool that called both MAJOR would be useless in the same way a tool that
called both MINOR would be dangerous — hence two runs rather than one.

## What this folder does not do

The competency question has a second half: comparing the implied bump against
whether the dependent artefacts *actually moved*. That needs the mappings and
the version history, and `version-diff` reads neither — it compares two
ontologies and tells you what the change implies. Noticing that the ontology
went to 2.0.0 while every mapping stayed put is orchestration on top, and
lives in the harness rather than in one command.

So this folder establishes the half a single command can answer: that the
severity of a change is judged correctly. Take it as necessary, not
sufficient.
