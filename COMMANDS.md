# Commands

Every command below is run from the repo root
(`c:\repos\consolidated-ontology-suite-python-testing`) in PowerShell.

## 1. One-time setup

```powershell
uv init --name owl2-error-detection-tests --python 3.12 --no-workspace
git init
uv add --editable "C:\repos\consolidated_ontology_suite_python"   # the suite under test
uv add --dev pytest
```

`--editable` points at the local suite checkout, so edits to the suite are
picked up without reinstalling. To refresh after pulling suite changes:

```powershell
uv sync
```

## 2. Run everything

```powershell
uv run python report.py        # detection matrix, all 16 fixtures  (~3 min with HermiT)
uv run pytest -q               # the same expectations as pass/fail tests
```

`report.py` exits 1 if any seeded error went undetected, and writes
`out/findings.csv` (every finding) plus `out/summary.md`.

Skip the external DL reasoner (HermiT via owlready2 + Java) for a faster run —
REA-020/REA-021 are then reported as skipped rather than failing:

```powershell
$env:OWL2_TEST_REASONER = "owlrl-only"; uv run python report.py
Remove-Item Env:\OWL2_TEST_REASONER
```

## 3. Run one test at a time

`report.py` takes substrings of fixture names; `pytest -k` takes the same.

| # | Fixture | Harness command | Suite CLI equivalent |
|---|---|---|---|
| 01 | clean control | `uv run python report.py 01-clean` | `uv run ontology-quality-suite data ontologies/01-clean/data.ttl --ontology ontologies/01-clean/ontology.ttl --out-dir out/cli/01-clean` |
| 02 | undeclared terms | `uv run python report.py 02` | `uv run ontology-quality-suite data ontologies/02-undeclared-terms/data.ttl --ontology ontologies/02-undeclared-terms/ontology.ttl --out-dir out/cli/02-undeclared-terms` |
| 03 | disjoint classes | `uv run python report.py 03-disjoint` | `uv run ontology-quality-suite data ontologies/03-disjoint-classes/data.ttl --ontology ontologies/03-disjoint-classes/ontology.ttl --out-dir out/cli/03-disjoint-classes` |
| 03b | unsatisfiable class (no data) | `uv run python report.py 03b` | `uv run ontology-quality-suite ontology --ontology ontologies/03-disjoint-classes/ontology.ttl --out-dir out/cli/03b-unsatisfiable-class` |
| 04 | property axioms | `uv run python report.py 04` | `uv run ontology-quality-suite data ontologies/04-property-axioms/data.ttl --ontology ontologies/04-property-axioms/ontology.ttl --out-dir out/cli/04-property-axioms` |
| 05 | asymmetric / irreflexive | `uv run python report.py 05` | `uv run ontology-quality-suite data ontologies/05-reasoning-violations/data.ttl --ontology ontologies/05-reasoning-violations/ontology.ttl --out-dir out/cli/05-reasoning-violations` |
| 06 | datatypes + domain/range | `uv run python report.py 06` | `uv run ontology-quality-suite data ontologies/06-datatype-conformance/data.ttl --ontology ontologies/06-datatype-conformance/ontology.ttl --out-dir out/cli/06-datatype-conformance` |
| 07 | naming style + deprecation | `uv run python report.py 07` | `uv run ontology-quality-suite checks --ontology ontologies/07-naming-style/ontology.ttl --out-dir out/cli/07-naming-style` |
| 08a | no version metadata | `uv run python report.py 08a` | `uv run ontology-quality-suite checks --ontology ontologies/08-metadata/no-version-metadata.ttl --out-dir out/cli/08a` |
| 08b | no ontology header | `uv run python report.py 08b` | `uv run ontology-quality-suite checks --ontology ontologies/08-metadata/no-ontology-header.ttl --out-dir out/cli/08b` |
| 08c | ontology IRI reused as namespace | `uv run python report.py 08c` | `uv run ontology-quality-suite checks --ontology ontologies/08-metadata/ontology-iri-reused.ttl --out-dir out/cli/08c` |
| 09 | OWL2 profile violations | `uv run python report.py 09` | `uv run ontology-quality-suite ontology --ontology ontologies/09-profile-violations/ontology.ttl --profile EL --profile QL --profile RL --out-dir out/cli/09-profile-violations` |
| 10 | efficiency | `uv run python report.py 10` | `uv run ontology-quality-suite checks --ontology ontologies/10-efficiency/ontology.ttl --out-dir out/cli/10-efficiency` |
| 11 | schema gaps | `uv run python report.py 11` | `uv run ontology-quality-suite data ontologies/11-schema-gaps/data.ttl --ontology ontologies/11-schema-gaps/ontology.ttl --out-dir out/cli/11-schema-gaps` |
| 12 | literal volume | `uv run python report.py 12` | `uv run ontology-quality-suite checks --ontology ontologies/12-literal-volume/ontology.ttl --data ontologies/12-literal-volume/data.ttl --out-dir out/cli/12-literal-volume` |
| 13 | unsatisfiable class | `uv run python report.py 13` | `uv run ontology-quality-suite data ontologies/13-unsatisfiable-class/data.ttl --ontology ontologies/13-unsatisfiable-class/ontology.ttl --out-dir out/cli/13-unsatisfiable-class` |

Several fixtures at once: `uv run python report.py 03 05 09`.

As pytest, one fixture:

```powershell
uv run pytest -q -k "04-property-axioms"
uv run pytest -q -k "clean"                     # the false-positive / severity control
uv run pytest -q tests/test_detection.py::test_expected_checks_fire
```

### Reading the CLI output

The CLI exits **1** whenever a Violation is found, so every fixture except
`01-clean`, `08a/b/c` and `09` exits 1 — that is the fixture working, not a
failure. Add `--fail-on never` to force exit 0, e.g. in CI smoke tests.
Each run writes `report.html`, `full_results.csv` and `cucumber.json` into its
`--out-dir`.

Which subcommand does what here:

* `data <data.ttl> --ontology <ont.ttl>` — the full pass: registry checks over
  ontology+data, the ontology-vs-data conformance layer (CNF-*), and reasoning
  (owlrl closure, plus HermiT when available).
* `checks --ontology <ont.ttl>` — registry SHACL+SPARQL suite over the ontology
  alone; no conformance layer, no reasoning.
* `ontology --ontology <ont.ttl>` — as-authored evaluation; the only stage that
  checks OWL2 profile membership, and only when `--profile` is passed.

## 4. Competency tests

The 28 numbered competency tests in [competency_tests/](competency_tests/) are a
separate exercise with their own fixtures, project-local checks and generated
report.

```powershell
uv run python competency_tests/run_competency_checks.py   # runs all 28, regenerates COMPETENCY_COVERAGE.md
uv run pytest competency_tests -q                          # the same expectations as pass/fail tests
uv run pytest "competency_tests/test_competency.py::test_competency_test_is_evidenced[16]" -q   # one competency test
```

Individual stages of that worked example, if you want to see one on its own:

```powershell
uv run ontology-quality-suite sketch --queries competency_tests/fixtures/model/queries --file-pattern "**/*.rq" --ontology competency_tests/fixtures/model/ontology/water-v1.ttl --out-dir out/ct/sketch
uv run ontology-quality-suite consistency --old competency_tests/fixtures/model/ontology/water-v1.ttl --new competency_tests/fixtures/model/ontology/water-v2.ttl --queries competency_tests/fixtures/model/queries --file-pattern "**/*.rq" --out-dir out/ct/consistency
uv run ontology-quality-suite pattern-consistency --queries competency_tests/fixtures/model/queries --ontology competency_tests/fixtures/model/ontology/water-v1.ttl --taxonomy competency_tests/fixtures/model/ontology/asset-types.ttl --taxonomy competency_tests/fixtures/model/ontology/units.ttl --file-pattern "**/*.rq" --out-dir out/ct/pattern
uv run ontology-quality-suite triplify --csv-dir competency_tests/fixtures/model/csv --queries competency_tests/fixtures/model/queries/readings --out-dir out/ct/triplify
```

The three checks only the VS Code extension implements have their own dataset:

```powershell
uv run ontology-quality-suite checks --ontology competency_tests/fixtures/vsix/extension-only.ttl --out-dir out/ct/vsix
# then open the same file in VS Code and run "Ontology Suite: Run Local Checks"
```

## 5. Experiments behind the observations in README.md

```powershell
uv run python experiments/severity_probe.py         # pyshacl reports every finding as Violation
uv run python experiments/illtyped_boolean_probe.py # DAT-001 can't see an invalid xsd:boolean
uv run python experiments/langstring_crash_probe.py # `data` crashes on a language-tagged literal (open)
```

## 6. Useful variations

```powershell
# faster: portable SPARQL engine only (skips pyshacl)
uv run ontology-quality-suite checks --ontology ontologies/07-naming-style/ontology.ttl --engine sparql --out-dir out/cli/07-sparql-only

# show what each input resolved to (imports, files matched, engine used)
uv run ontology-quality-suite checks --ontology ontologies/10-efficiency/ontology.ttl --verbose --out-dir out/cli/10-verbose

# human-readable documentation page for a fixture
uv run ontology-quality-suite docgen --ontology ontologies/09-profile-violations/ontology.ttl --out-dir out/cli/09-docs

# compare two ontology versions (any two fixtures work as a demo)
uv run ontology-quality-suite version-diff ontologies/01-clean/ontology.ttl ontologies/02-undeclared-terms/ontology.ttl --out-dir out/cli/version-diff
```

Clean regenerated output:

```powershell
Remove-Item -Recurse -Force out
```
