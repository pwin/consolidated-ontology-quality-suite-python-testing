# What has to be done

Ordered so that each group can be finished and checked off before the next one
matters. Group 1 is a blocker for everything; groups 2–5 are per act and can be
done in parallel; group 6 is the rehearsal.

---

## 1. Environment, before anything else

- [ ] Install the extension on the demo machine: `code --install-extension
      consolidated_ontology_suite_webapp/ontology-dev-suite-0.16.3.vsix`
- [ ] Point `ontologySuite.pythonCliPath` at this repo's venv, and confirm
      **Ontology Suite: Run Deep Validation (Python CLI)** actually returns
- [ ] Confirm a **Java runtime** is present. Act 1 beat 7 is HermiT; without it
      that beat has no payoff
- [ ] Confirm **`oxi-gen`** is on the machine. Act 2 beat 6 shells out to it
- [ ] Warm both: run the reasoner and a triplify once before the audience is in
      the room, so no silence waits on a cold start
- [ ] Check for a competing RDF/SPARQL extension claiming `.rq`. If Query
      Workbench says "Open a .rq CONSTRUCT query file first" with a `.rq` open,
      that is the cause — check the language-mode indicator
- [ ] Record a fallback video of Act 1 beat 7 and Act 2 beat 6, the two beats
      that can hang on a cold or incomplete machine
- [ ] Decide screen layout now: editor, Problems panel, and a terminal visible
      at once. Font size set for the room, not for the laptop

## 2. Props to build

- [ ] **`demonstration/act1-ontology/`** — a genuinely clean starting ontology
      to grow on screen. Copy the conventions of `ontologies/01-clean/`
      (labels, definitions, domains, ranges, declared annotation properties),
      not the file itself: that one is a test control and must stay one
- [ ] **`demonstration/act2-csv/`** — one raw CSV with a mix worth profiling
      (a date, an integer, a free-text field, one column that is a foreign key),
      plus the query folder that will grow from it
- [ ] **`demonstration/act4-house-rules/`** — the `.ontology-suite/` pair
      (`class-rules.json`, `standards.json`) for the editor tier of Act 4
- [ ] **`demonstration/reset.sh`** — one command back to the starting state.
      Three acts that edit files on screen will diverge on the second rehearsal
      without it. `git checkout -- demonstration/` plus removing generated
      `out/` directories

## 3. Reuse, do not rebuild

Verify each still behaves as recorded, then leave it alone:

- [x] `competency_tests/fixtures/vsix/extension-only.ttl` — Act 1 beat 5. Seeds
      `VOC-001` on a `:Machnie` typo and `REA-005` on a sameAs/differentFrom
      contradiction. **CLI contrast re-confirmed on suite 0.24.3:** 2 findings,
      `DAT-002` and `QUA-004`, and none of the three extension-only ids. Still
      to do: confirm the editor half on extension 0.16.3
- [ ] `competency_tests/fixtures/model/` — Act 3 runs entirely on this:
      ontology 1.0.0 and 2.0.0, taxonomy, units, four mappings, their CSVs, two
      comparable outputs
- [ ] `experiments/SpecificTests/CT-01-iri-template-drift/` and
      `CT-14-construct-variable-unbound/` — Act 2 beats 4 and 5 as drop-in
      props, for when live editing is too risky to rehearse
- [ ] `experiments/SpecificTests/AGGREGATE-mapping-drift/` — Act 3 beats 2–4
- [ ] `experiments/SpecificTests/CT-37-prefix-disagreement/` — Act 3 beat 3
- [ ] `examples/cross-folder-checks/` — **the whole basis of Act 4.** Folder B
      (SPARQL house rules), Folder C (a SHACL house rule), `prepare_checks.py`,
      and a README whose five failure modes are all measured
- [ ] `gate.py` + `ontology-suite.yml` — the close of Acts 3 and 4

## 4. Act-by-act preparation

### Act 1 — writing an ontology

- [ ] Stage the clean ontology one edit away from each beat, rather than typing
      from nothing
- [ ] Decide the deliberate `owl:Class` vs `gist:Category` wrong choice in beat
      2 and where it is revisited
- [ ] Pick the class-expression restriction for beat 3 and check it parses
      (e.g. `hasReading some Reading`)
- [ ] Seed the beat 7 contradiction — a class both `owl:disjointWith` and
      `rdfs:subClassOf` the same parent — and **verify Run Local Checks reports
      nothing on it** while Run Deep Validation reports `REA-021`. If the
      in-process tier has caught up, the beat needs a different contradiction

### Act 2 — creating transformations

- [ ] Confirm **Infer Ontology + Query from CSV** output on the chosen CSV is
      presentable; adjust the CSV until it is
- [ ] Check the Query Workbench finds the ontology automatically from the
      query's directory, parent, then siblings. If the layout needs it, pin
      `ontologySuite.queryOntologyPaths` and say so on screen
- [ ] Rehearse the BIND drift edit so `TQL-001` appears on the second query
      rather than needing explanation
- [ ] Time **Run Full Triplify** on the real data and cut the input until it is
      under about twenty seconds

### Act 3 — reviewing the set

- [ ] Confirm **Review TARQL BIND Consistency** on the Act 3 query folder comes
      back **clean**. The act opens by showing the editor satisfied, so this
      must be true
- [ ] Have each set-level finding ready to run, one command each: `CMP-034`
      (one class, two shapes), `CMP-035` (one predicate, two datatypes),
      `CMP-036` (term outside the import closure), `CMP-037` (prefix
      disagreement), `CMP-038` (golden-output drift), `CMP-015`/`016` (mapping
      integrity)
- [ ] Prepare the golden-output beat: the one mapping edit, and the `CMP-038`
      output naming what moved
- [ ] Have `consistency` and `version-diff` output ready for 1.0.0 → 2.0.0
      against mappings nobody updated

### Act 4 — adding your own checks

- [ ] Write the Act 4 narrative rule down in one sentence first, in the
      audience's own domain. The committed example uses "every vehicle carries
      an asset tag matching `FLT-NNNNNN`"
- [ ] **Tier 1, the editor, no SPARQL:** author `.ontology-suite/class-rules.json`
      live and show `PRJ-REQUIRED` in the Problems panel with a Quick Fix on a
      missing label. Confirm the bundled JSON schema gives completion as you type
- [ ] **Tier 2, a real SPARQL check:** rehearse
      `examples/cross-folder-checks/folder-a-fleet-project/validate.sh` and
      confirm the recorded output — 4 house checks merged onto 61, 11 findings,
      `FLT-001` quoting *your* remediation text
- [ ] **Tier 2 in the editor:** set `ontologySuite.checksRegistryPath` at a
      checkout holding `registry.json`/`sparql/`/`shapes/` and confirm the house
      check appears in the Problems panel. **Verify first** — this setting
      *replaces* the bundled copy, exactly as `--registry` does, so the check
      to show is that the standard findings are still there too
- [ ] **Tier 3, SHACL:** confirm Folder C's shape fires `FLT-004` from the
      `shacl` arm, and have the three flag differences on a slide: `--shapes`
      does not repeat, takes no `@builtin`, and is not recursive
- [ ] **The quiet failure:** re-measure it on the day. Point `--shapes` at
      Folder C and show that the finding **ids do not change at all** — the only
      trace anywhere is `STR-002` going from `shacl+sparql` to `sparql`
- [ ] Decide whether `disabledChecks` is worth 30 seconds — turning a standard
      check *down* is the other half of extensibility

## 5. Documentation to fix first

- [ ] `competency_tests/COMPETENCY_COVERAGE.md` still says to install
      `ontology-dev-suite-0.13.6.vsix`. The current build is **0.16.3**. Fix the
      line and re-verify the three extension-only findings on the new build
- [ ] Re-confirm the "44 SPARQL + 6 SHACL-SPARQL checks in-process" figure from
      the extension README against 0.16.3 before quoting it on screen

## 6. Rehearsal

- [ ] Dry run with `reset.sh` between acts, timing each
- [ ] Cut to the hinge of each act and check it still makes sense alone — that
      is the fifteen-minute version
- [ ] Rehearse the two sentences that have to be said out loud and are easy to
      skip: that the in-process tier is **sound but not complete**, and that
      three checks exist which no CLI run can produce
- [ ] Prepare the questions you do not want to answer mid-flow: licensing,
      performance on a million triples, whether this replaces Protégé. Park
      them to the end deliberately

---

## Deliberately out of scope

- **The graph visualiser**, early. It is the most immediately impressive thing
  here and it will pull every question away from the argument. Hold it for the
  Q&A
- **A 142-finding aggregate report** shown as a feature. This repo has measured
  what that looks like: three systemic checks produced 99 of the findings and
  the eleven real defects were single lines among them. Show it only to make
  *that* point
- **`.ontology.ts` ontology-as-code.** A genuinely good story and a whole
  demonstration of its own; it would eat Act 1
- **Any claim that either tool is complete.** The 3 and the 11 are the honest
  frame, and a practitioner audience will trust the demo more for it
