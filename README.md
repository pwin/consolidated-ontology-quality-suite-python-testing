# OWL2 error-detection tests for the Ontology Quality Suite

A small set of deliberately broken OWL2 ontologies, plus a harness that runs
[`consolidated_ontology_suite_python`](../consolidated_ontology_suite_python)
over each one and asserts that the seeded errors are actually reported.

Each fixture isolates a *category* of error and pins the registry check ids it
must trigger, so a regression in the suite shows up as a named missing check
rather than as a changed finding count. All commands are in
[COMMANDS.md](COMMANDS.md).

```powershell
uv sync
uv run python report.py     # detection matrix
uv run pytest -q            # same expectations, as pass/fail tests
```

## Layout

| Path | What it is |
|---|---|
| [ontologies/](ontologies/) | 18 Turtle files in 10 folders; every seeded error is marked with an `# ERROR:` comment naming the check it should trigger |
| [detect.py](detect.py) | The fixture table (stage, expected check ids, false-positive guards) and the suite invocations |
| [tests/test_detection.py](tests/test_detection.py) | pytest assertions over that table |
| [report.py](report.py) | Prints the detection matrix; writes `out/findings.csv` and `out/summary.md` |
| [experiments/](experiments/) | Two standalone probes that isolate the suite issues found below |

## Results

All 16 fixtures pass: **43 of the registry's 61 checks** are asserted, and
every seeded error is detected. Counts below are from `uv run python report.py`
against suite 0.14.3 — 151 findings in total, identical across runs.

Taken together with [competency_tests/](competency_tests/), **58 of the 61
checks are exercised by some fixture**. The three that are not — `REA-005`,
`REA-006` and `VOC-001` — are the ones the CLI does not implement at all; they
are the VS Code extension's, and `competency_tests/fixtures/vsix/` holds a
dataset for checking them by hand. So every check the CLI can produce now has
a fixture that proves it fires.

| Fixture | Seeded error | Detected |
|---|---|---|
| `01-clean` | *(none — control)* | 0 Violations, 0 Warnings; only `CNF-005` ×2 (Info, "class never populated") |
| `02-undeclared-terms` | class IRI and property IRI misspelled in the data | `STR-001`, `STR-002`, `STR-007`, `CNF-001`, `CNF-002` |
| `03-disjoint-classes` | class disjoint with its own superclass; individual in two disjoint classes | `LOG-001` ×2, `REA-001` ×2, `REA-020` (HermiT) |
| `03b-unsatisfiable-class` | same ontology, no data — contradiction is class-level only | `LOG-001`, `REA-021` (HermiT) |
| `04-property-axioms` | functional property with 2 values; 2 inverses; self-inverse; symmetric/transitive with domain ≠ range | `LOG-002`, `LOG-004`, `LOG-005`, `LOG-006`, `LOG-007` |
| `05-reasoning-violations` | asymmetric property both ways; irreflexive self-loop | `REA-002` ×4, `REA-003` ×2, `REA-020` (HermiT) |
| `06-datatype-conformance` | ill-formed `xsd:date`/`integer`/`boolean`; domain and range violations | `DAT-001` ×3, `CNF-003`, `CNF-004` |
| `07-naming-style` | `snake_case` class, hyphenated class, `Upper_Snake` property, untagged label, deprecated term still used | `STY-001` ×2, `STY-002`, `STY-003`, `STY-005`, `QUA-001`, `QUA-003` |
| `08a-no-version-metadata` | header with no version/title metadata, no `owl:versionIRI`, `http://` IRI | `QUA-002`, `QUA-007`, `QUA-008` |
| `08b-no-ontology-header` | no `owl:Ontology` declaration at all | `QUA-005` |
| `08c-ontology-iri-reused` | ontology IRI reused verbatim as the concept namespace | `QUA-006` |
| `09-profile-violations` | `unionOf`, `complementOf`, `allValuesFrom`, `minCardinality 4`, transitive + functional properties | `REA-010` ×6, `REA-011` ×5, `REA-012` ×3 |
| `10-efficiency` | 6-hop `subClassOf` chain; blank nodes >20% of all nodes | `EFF-001` ×2, `EFF-002` |
| `11-schema-gaps` | redundant `equivalentClass`+`subClassOf`; property with no domain or range; domain and range IRIs never declared; untyped subject | `LOG-003`, `STR-003`, `STR-005`, `STR-008`, `STR-009` |
| `12-literal-volume` | 60 values on one subject-predicate pair; one lexical form under two language tags | `EFF-003`, `DAT-003` |
| `13-unsatisfiable-class` | individual typed with a class declared `rdfs:subClassOf owl:Nothing` | `REA-004`, `REA-020` (HermiT) |

The clean control is the important negative case: it declares labels,
definitions, domains, ranges and metadata properly, and produces **no Violation
or Warning at all** — so the findings in the other fixtures are attributable to
the seeded errors, not to background noise. It needed one edit to stay that way
across the 0.6.0 → 0.14.2 upgrade: `skos:definition` on each term, for the
`QUA-010` check added in between.

## Issues found

Building these fixtures surfaced six defects in the suite, **all now fixed** —
the first four in ontology-quality-suite 0.6.0 (commit `2f4950c`, which also
credits three more found while fixing them), the last two in 0.14.3. Each
section keeps the original evidence and records how the fixed suite behaves
now. The fixtures themselves needed almost no changing across either round —
they pin check ids, not finding counts, which is what let them survive.

### 1. pyshacl reported every finding as a Violation, ignoring the declared severity — fixed

With the default `--engine both`, any finding produced by the pyshacl path
came back as `Violation` regardless of the registry's `default_severity`:

| Check | Registry default | Reported via pyshacl |
|---|---|---|
| `STY-001`, `STY-002`, `QUA-001`, `QUA-003`, `EFF-001`, `EFF-002` | Warning | **Violation** |
| `QUA-002`, `STY-003` | Info | **Violation** |

Cause: the shapes declared `sh:severity` on the nested `sh:SPARQLConstraint`
blank node, but SHACL defines `sh:severity` as a property of the *shape*.
pyshacl never saw it and fell back to the spec default, `sh:Violation`.
[experiments/severity_probe.py](experiments/severity_probe.py) proved it by
lifting `sh:severity` onto the shape node in a copy of
`resources/shapes/style.ttl` and re-running:

```
--- shapes-as-shipped
    STY-001  reported=Violation registry=Warning     <-- differs
    STY-003  reported=Violation registry=Info        <-- differs
--- shapes-patched
    STY-001  reported=Warning   registry=Warning
    STY-003  reported=Info      registry=Info
```

Impact: with the default `--fail-on Violation`, a class named `person_record`
failed a CI gate exactly as hard as a logical contradiction. The portable SPARQL
formulation was unaffected (`--engine sparql` reported the registry severities),
which is also why the same finding could appear twice at two severities —
`STY-003` on `:legacyId` was reported both `Info via sparql` and
`Violation via shacl`, because the two rows differed in the dedup key
`(check_id, focus_node, path, value)` and so never merged.

**Now:** `sh:severity` sits on the shape, both engines agree with
`registry.json`, and `STY-003` is reported once instead of twice.
`tests/test_detection.py::test_reported_severity_matches_registry` asserts
this across every fixture.

### 2. `STR-002` flagged `skos:prefLabel`, but its sibling `STR-007` did not — fixed

Using `skos:prefLabel` without declaring it locally produced a Violation-severity
`STR-002` ("undefined property used") — 5 of them in the first draft of the clean
control. `STR-002` exempted only the `rdf:`, `rdfs:` and `owl:` namespaces, while
`STR-007`, `STR-004`, `STR-006`, `STR-009`, `QUA-004` and `STY-004` all exempt
`http://www.w3.org/` wholesale, and the data-quality layer's
`ANNOTATION_PREDICATES` set recognises SKOS explicitly. `STR-004`'s own comment
asserted that "the same exemption STR-001/STR-002/… already apply", which was not
what the query did.

Whether that was a bug depended on intent — "declare the external terms you use"
is a defensible rule — but the two checks should not disagree with each other.

**Now:** `STR-002` exempts `http://www.w3.org/` like its siblings. Every fixture
here still declares `skos:prefLabel a owl:AnnotationProperty`, which is good
practice regardless and keeps the fixtures valid against either version.

### 3. `DAT-001` could not detect an invalid `xsd:boolean` — fixed

Fixture 06 seeds three ill-formed literals; only two were reported. `DAT-001`
tests the lexical form with a regex, but rdflib *rewrites* the stored lexical
form of an ill-typed boolean — `"yes"^^xsd:boolean` is stored as `'false'` —
so the invalid form no longer exists by the time the check runs. Date and
integer keep their original lexical form, which is why those two were caught:

```
  predicate    authored   stored lexical   .value   ill_typed
  headcount    twelve     'twelve'         None     True     -> DAT-001 fires
  birthDate    31-12-1990 '31-12-1990'     None     True     -> DAT-001 fires
  isActive     yes        'false'          False    True     -> not detected
```

rdflib already flags all three as `ill_typed`, so a Python-side pass over the
loaded graph would catch every case the regex branch was meant to. Reproduce
with `uv run python experiments/illtyped_boolean_probe.py`.

**Now:** the suite added `checks/literal_typing.py`, which does exactly that.
Fixture 06 reports `DAT-001` three times, the third attributed to source
`literal-typing`. The probe still shows the SPARQL branch matching nothing —
that part is inherent to rdflib, which is why the fix had to live outside the
query.

### 4. Finding counts were not reproducible for multi-value checks — fixed

Running fixture 04 three times, unchanged, reports `LOG-004` ("property has
more than one inverse") **3, then 2, then 4 times**:

```powershell
1..3 | ForEach-Object { uv run python report.py 04 | Select-String "LOG-004" }
```

Cause: `LOG-004`'s CONSTRUCT emits two values per result
(`sh:value ?p1, ?p2`), while `checks/merge.py` reads a single one with
`results_graph.value(result, SH.value)` — an arbitrary pick among them — and
then dedups on `(check_id, focus_node, path, value)`. Which value rdflib
returns varies per run, so rows collapse differently each time. `LOG-006`
(`sh:resultPath rdfs:domain, rdfs:range ; sh:value ?domain, ?range`) and
`REA-001` (`sh:value ?c1, ?c2`) share the pattern.

Impact: finding totals and `full_results.csv` diffs fluctuated with no input
change, which made count-based CI gates and report diffs unreliable. The
*set* of check ids reported stayed stable, which is why the tests here assert
on ids rather than counts — and why they passed unchanged across the fix.

**Now:** `merge.py` sorts and joins all values into one order-independent key,
and renders `sh:resultPath` property paths instead of blank-node ids. `LOG-004`
reports `x2` on three consecutive runs.

## Notes on the fixtures

* Namespaces are `https://example.org/test/<name>#`, with the ontology IRI at
  `https://example.org/test/<name>` — deliberately distinct, since reusing one
  as the other is itself a finding (`QUA-006`, fixture 08c).
* `REA-020`/`REA-021` need the optional external DL reasoner (owlready2 +
  a Java runtime). The harness asserts them only when it actually ran, and
  reports them as skipped otherwise — the suite signals its absence with
  `REA-022`.
* The fixtures pin check *ids*, never finding counts — which is what let them
  pass unchanged across the 0.6.0 fixes above.
* The suite falls back to owlrl-only for fixture 06 (`REA-022` is reported):
  owlready2's RDF/XML parser rejects the ill-typed literals. The degradation is
  visible in the report rather than silent, which is the designed behaviour.

### 5. `data` crashed on a language-tagged literal — fixed

Found while adding the `DAT-003` fixture, which needs two literals sharing a
lexical form — most naturally the same text under two language tags.
`dataquality/data_quality.py:356` computes a literal's effective datatype as:

```python
actual = o.datatype or (RDFS.langString if o.language else XSD.string)
```

`langString` is an RDF term, not an RDFS one, and rdflib's `RDFS` is a closed
`DefinedNamespace`, so the attribute access raises instead of quietly yielding
a wrong IRI:

```
AttributeError: term 'langString' not in namespace 'http://www.w3.org/2000/01/rdf-schema#'
```

This was a crash, not a misreported finding: the `data` stage stopped, taking
every other check in that run with it. Three ordinary conditions have to coincide — a
property whose `rdfs:range` names an XSD datatype, a language-tagged value for
it, and any stage that calls `check_conformance` (`data`, `sketch --ontology`,
`run`). `rdfs:range xsd:string` with a `"..."@en` value is the everyday case.

```
$ uv run python experiments/langstring_crash_probe.py
  "Checked" (untagged)         ok     0 range violation(s)
  "Checked"@en (tagged)        CRASH  AttributeError: term 'langString' not in namespace '...rdf-schema#'
```

**Now:** fixed in ontology-quality-suite 0.14.3 — one word, `RDF.langString`,
which that module already imports. The fix also changes the answer rather than
just unblocking it: a `rdf:langString` is not an `xsd:string`, so the tagged
literal is now reported as the `CNF-004` range violation it always was. The
suite's own test for a tagged literal could never have caught this — it uses
`foaf:name`, whose `rdfs:Literal` range short-circuits two lines above the
defect. `12-literal-volume` is back on the `data` stage and asserts `CNF-004`
alongside its two seeded defects.

### 6. `pattern-consistency` misreported per-row entities as taxonomy references — fixed

`check_taxonomy_references` skips the per-row entities a mapping builds
(`?vehicle_IRI` and the like) by recognising the sketch's scratch namespace,
`https://tarqlviz.org/`. But `sketch.ttl` renders those entities using the
*query's* own empty prefix whenever the query declares one — and most do. Every
unbound variable then landed in the model's namespace and was reported as a
reference to a nonexistent taxonomy term.

Measured on the competency-test mappings, where all four files declare
`PREFIX : <...>`: **11 of 12 findings named a CONSTRUCT variable**, burying the
one real one (`vocab:Resevoir`, a typo for `vocab:Reservoir`). The suite's own
worked example does not declare `:`, which is why its output looked clean.

**Now:** fixed in 0.14.3. `tarql_visualiser.per_row_entity_iris` computes both
candidate namespaces — the scratch one and each query's own empty prefix —
crossed with the variable names that query's CONSTRUCT blocks use, so the answer
holds whichever binding won.

## Competency tests

[competency_tests/](competency_tests/) is a second, larger exercise over the
same suite: 28 numbered competency tests supplied as CSVs, each one seeded into
a worked example spanning an ontology, a taxonomy, four TARQL mappings, the CSVs
they read and two comparable outputs. All 28 are evidenced. Two generated documents record it:
[COMPETENCY_COVERAGE.md](competency_tests/COMPETENCY_COVERAGE.md), how each test
is checked and what the run found, and
[COMPETENCY_CHECK_MATRIX.md](competency_tests/COMPETENCY_CHECK_MATRIX.md), every
(test, check) pair joined to its registry entry with the command to run it.

```bash
uv run python competency_tests/run_competency_checks.py
```

## Licence

Copyright 2026 Peter Winstanley. Dual-licensed under either
[MIT](LICENSE-MIT) or [Apache-2.0](LICENSE-APACHE), at your option — the same
terms as the suite under test.
