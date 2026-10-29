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
      contradiction. **Both halves of the contrast re-confirmed.** CLI,
      re-checked on suite **0.25.0**: 2 findings, `DAT-002` and `QUA-004`,
      none of the three
      extension-only ids. Editor, extension 0.16.3: `VOC-001` (Warning) on
      `:Pump` → `:Machnie` and `REA-005` (Violation) on `:pump-17`, by driving
      `runVocabularyChecks` and `runReasoningChecks` over the fixture directly.
      That exercises the check engines, **not** the Problems-panel path — so
      still run the palette command once on the day before showing it
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
- [x] `examples/severity-policy/` — **the whole basis of Act 5, and it needs
      no props built.** `policy-repo/severities.json` is the flat
      id→severity list the act shows on screen;
      `policy-repo/severities-by-stage.json` is the staged version for beat 6;
      `work-folder/` holds `myOntology.ttl` and the two gate configs;
      `compare.sh` produces beat 6's table. **Re-measured on suite 0.25.0:**
      13 findings in every reading, blocking set moving from `STR-002`,
      `STR-007` at defaults to `STR-007` alone at sketch to three at release
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
      check *down* is the other half of extensibility, and Act 5 beat 7 refers
      back to it as the editor's blunt instrument

### Act 5 — the standard checks, read your way

Least preparation of any act: it runs from `examples/severity-policy/` as
committed, and needs no props.

- [ ] Confirm the installed suite is **0.25.0 or later**
      (`ontology-quality-suite checks --help | grep severity-policy`).
      `compare.sh` checks this too and says so rather than failing obscurely
- [ ] Rehearse beat 3 as **one flag added to the beat 2 command**, not a new
      command typed from scratch. The whole point is that nothing else changed
- [ ] Have the beat 3 contrast ready to point at, because it is the beat:
      13 findings and 2 Violations both times, `STR-002`/`STR-007` becoming
      `STR-003`/`STR-007`. If you only show totals the act has no content
- [ ] Open `full_results.csv` at the `declared_severity` column before beat 4
      rather than hunting for it live
- [ ] Beat 5's two failure modes are **told, not run** — each takes about a
      minute and produces nothing to look at. Have the table on a slide
- [ ] Decide whether to say the honest limit out loud in beat 7: there is no
      stringency in the editor, only `disabledChecks`. Recommended — a room
      that finds it afterwards trusts the rest less
- [ ] If the room is a standards group rather than a project team, swap the
      framing of beat 1: they are the owners of the policy repo, not the
      consumers of it
- [ ] Consider opening beat 3 with `policy-repo/levels/exploring.json` instead
      of `severities.json`. It is the same flat shape, and it reports **13
      findings and 0 Violations** — the gate passes with the report unchanged,
      which is the literal answer to *we cannot switch this on, it would fail
      everything on day one*. `severities.json` makes the subtler point (a
      different pair blocking), so it is a choice about which objection the
      room actually has
- [ ] Have one answer ready for the question beat 6 invites: *can each stage be
      its own file?* Yes — `split.sh` runs
      `severities-{sketch,draft,release}.json` and compares each against the
      matching stage of the nested file, identical every time. Know it, do not
      show it: it is a filing decision, and on screen it looks like the same
      output twice

## 5. Documentation to fix first

- [x] `competency_tests/COMPETENCY_COVERAGE.md` said to install
      `ontology-dev-suite-0.13.6.vsix`; the current build is **0.16.3**. Fixed
      at the source — that file is generated, so the edit is in
      `run_competency_checks.py`, and the line now says the version is not
      load-bearing so the next bump does not silently invalidate it
- [x] The extension README's "44 SPARQL + 6 SHACL-SPARQL checks" — measured
      against 0.16.3's bundled registry rather than taken from the prose.
      **The 44 holds**: 46 `.rq` files ship, minus `TQL-004`/`005`, which
      `CLI_ONLY` excludes because they query the suite's BIND-facts graph.
      **The 6 counts shape *files*, not checks** — those 6 files hold 22 shape
      nodes resolving to 21 check ids, every one of which also has an `.rq`
      twin. Do not say "6 checks" on screen. The figure worth quoting is the
      one in `SCRIPT.md`: **50 of the registry's 61 run in-process**, and the
      11 that do not are exactly `CLI_ONLY`

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
