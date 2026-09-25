# CT-4 — taxonomy/ontology concepts referenced by TARQL do not exist

```bash
./run.sh          # verdict only
./run.sh --show   # verdict plus the whole report
```

| Path | What it is |
|---|---|
| `ontologies/model.ttl` | the model: an asset class and the categorisation property |
| `ontologies/asset-types.ttl` | the taxonomy — every asset type the data may use |
| `queries/assets.rq` | the mapping, hard-coding two taxonomy terms |
| `out/` | `pattern-consistency.txt` |

## The two sets

| | Term in the template | In the taxonomy | Expected |
|---|---|---|---|
| **error** | `vocab:Resevoir` | **no** — one letter out | **reported** |
| **control** | `vocab:Borehole` | yes | **silent** |

A hard-coded controlled-vocabulary term is where this typo lives: it is
written by hand into the CONSTRUCT template, so it never passes through a
CSV, never varies by row, and produces valid RDF pointing at a term that does
not exist. Every asset classified that way is categorised by nothing.

The control is spelled as the taxonomy spells it, so a check that reported
both would be saying only "this query mentions the vocabulary".

## What the run should report

- `undeclared_taxonomy_reference` for `vocab:Resevoir`
- nothing about `vocab:Borehole`
- no prefix misalignment

## Why the taxonomy is passed twice

`--taxonomy` makes it the authority for controlled-vocabulary terms.
`--ontology` puts its namespace into the set the prefix layer compares query
prefixes against. Pass it only as a taxonomy and the query's own `vocab:`
prefix is reported as a namespace nothing declares — true of the ontology set
as given, and not what anyone means by it. `run.sh` asserts that no
misalignment is reported, so this stays deliberate rather than becoming
folklore.

## What was left out, and why

- real triplified output, which would answer the per-row half of CT-4 — a
  term chosen from a CSV value rather than hard-coded. That is a different
  fixture and needs a mapping run
- any second taxonomy term, correct or otherwise
