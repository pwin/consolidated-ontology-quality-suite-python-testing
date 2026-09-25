# One folder per competency test

Each folder poses one competency question with the smallest data that can
answer it, and answers red or green.

```bash
./run-all.sh                  # the board
./run-all.sh --csv            # the same, for CI to keep
./run-all.sh CT-01 CT-07      # a subset, by folder name
./CT-01-*/run.sh --show       # one test, with every finding printed

SUITE=ontology-quality-suite ./run-all.sh   # against an installed suite
```

`run-all.sh` exits 0 only when every test is green, so it works as a CI step
as it stands.

## What a folder holds

```
CT-01-iri-template-drift/
  ontologies/     the declarations, and nothing that is not needed
  queries/        the mappings, carrying both the fault and its control
  out/            what the run writes -- two text files, via --reports minimal
  run.sh          the exact command, plus the assertions
  README.md       the defect, the two sets, and what should be reported
```

## Both sets, in the same files

Every folder carries the fault **and** a control that is identical in kind
and correct. CT-1's two queries build two IRIs: `?site_IRI` from two
different templates (the fault) and `?asset_IRI` from the same template
twice (the control).

`run.sh` asserts both directions — the fault is reported, the control is
not — because a check that fired on everything would pass a fire-only test
while being useless, and one that fired on nothing would look exactly like a
clean project.

## One finding, and it is the one under test

The data is trimmed until the run reports the seeded defect and nothing
else, so red is attributable without reading a diff. Anything else that
appears has to be named in the folder's `ALLOWED` list with a reason, and an
empty list is the goal.

When something turns up that no data of ours produced, the disposal is a fix
upstream rather than an entry in that list. CT-1 carried `CNF-002` on
`:isRepresentedBy` until suite 0.20.0: the sketch wrote its namespace legend
with the CURIE `:isRepresentedBy`, and `:` means the tool's scratch namespace
only when no query declares an empty prefix — so the tool's own predicate
landed in the project's namespace and was reported as a property nobody had
declared. No project could have made that go away.

## How this differs from `competency_tests/`

Both run the real suite over real artefacts. The difference is isolation.

| | `competency_tests/` | here |
|---|---|---|
| Data | one worked example where all 38 defects coexist | one folder per test, minimal |
| A failure says | something moved; now diagnose it | this capability stopped working |
| Catches | one check masking or interfering with another | nothing about interaction |
| Runs against | this repo's harness | any suite install, via `SUITE=` |

Neither replaces the other. The worked example is the only place you would
notice a check swallowing another's finding; the board is the only place a
red row names the capability directly, and the only one you can point at a
published release.
