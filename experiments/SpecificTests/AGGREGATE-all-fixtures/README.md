# Every fixture at once

```bash
./run.sh            # the summary
./run.sh --detail   # plus every finding, one line each
```

Not a test, and `run-all.sh` skips it. There is no verdict to give: the
answer is the report.

| Path | What it is |
|---|---|
| `ontologies/` | every CT folder's ontology, renamed by folder |
| `queries/` | every mapping |
| `data/` | every output graph |
| `checks/` | every project check, with one merged registry |
| `out/` | three passes, and `all-findings.csv` joining them |

The files are copies, renamed (`ct01-model.ttl`, `ct13-output.ttl`) because
several folders call their files the same thing. Regenerate them with
`build_aggregate.py` after changing any fixture. The IRIs are left alone:
where two fixtures say different things about the same term, that
disagreement stays, because it is what a real project looks like.

## Three passes, not one

Each pass keeps its findings' identity. A run given only this folder's
registry reports the suite's own checks as `UNMAPPED`; a run given only the
suite's registry does the same to the `CMP-*` ones. Merging two registries at
run time is more machinery than a demonstration needs.

1. `sketch` over the mappings, against the merged model
2. `data` over the output graphs, with the suite's own checks
3. `data` over the same output, with this project's checks

## What it shows

**142 findings: 19 Violation, 87 Warning, 36 Info.**

Three checks account for 99 of them:

| Check | N | Why so many |
|---|---|---|
| `CMP-012` | 56 | labels minted by the transformation — but the merged model *has* labels, and CT-12's own folder deliberately uses a declarations-only file to keep them out. Merged, the check reports nearly every labelled term |
| `CNF-005` | 33 | classes declared and never populated — twenty-nine ontology files against nine output graphs, so most classes have no instances here |
| `STR-004` | 10 | classes with no superclass, which most minimal fixtures have by design |

Meanwhile every seeded defect is in there exactly once or twice: `TQL-001`,
`TQL-002`, `TQL-005`, `CMP-002`, `CMP-018`, `CMP-019`, `CMP-021`, `CMP-030`,
`CMP-031`, `CMP-032`, `QUA-009`.

That ratio is the finding. On a first run against a real project the output
is dominated by a few systemic conditions, and the specific defects — the
ones a competency test was written to catch — are single lines among
hundreds. The isolated folders exist because of exactly this: there, each
defect is the only thing reported, and a red row names a capability rather
than starting an investigation.

It also shows something about `CMP-012` worth taking seriously: a check whose
correctness depends on *what you merge into the graph* will misfire the
moment someone invokes it differently. Its folder documents that constraint;
the aggregate is what ignoring it looks like.
