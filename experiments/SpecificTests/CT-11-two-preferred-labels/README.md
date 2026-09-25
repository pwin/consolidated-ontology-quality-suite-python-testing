# CT-11 — Multiple preferred labels for the same language

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus every finding
```

| Path | What it is |
|---|---|
| `ontologies/model.ttl` | two classes, each with two preferred labels |
| `out/` | `findings.txt` and `full_results.csv`, via `--reports minimal` |

## The two sets

| | Class | `skos:prefLabel` | Expected |
|---|---|---|---|
| **error** | `:Asset` | `"Asset"@en`, `"Equipment item"@en` | **reported** |
| **control** | `:Site` | `"Site"@en`, `"Safle"@cy` | **silent** |

Both classes carry two preferred labels, so a check counting them would
report both. The rule is one per *language*, and the control exercises
exactly that distinction: a Welsh label beside an English one is correct and
common, while two English ones leave nothing able to choose between them.

## What the run should report

| Check | Focus | Why |
|---|---|---|
| `QUA-009` | `#Asset` | **the point of the fixture** |
| `STY-004` | both classes | a label in another language cannot also match an English local name, and neither can a second English label that differs from the first. It comes with any bilingual or double-labelled term, and is inseparable from what this fixture is showing |

`run.sh` fails if `QUA-009` is missing for `#Asset`, if it appears
for `#Site`, or if anything else is reported at all.

## What was left out, and why

- `dcterms:title` in the header — three findings of its own, none about
  labelling
- a term with no preferred label at all — that is CT-10
