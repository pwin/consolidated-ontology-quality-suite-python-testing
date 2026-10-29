# Demonstration script

Each beat has **Do** (what happens on screen), **Say** (bullets to speak from —
not sentences to read out), and **Land** (the one thing they should leave the
beat with). Times are cumulative within an act.

Palette commands are in **bold**; everything prefixed `uv run` is a terminal
line. The `>` quotes are expected output — verify each on the day before
quoting it.

---

## Open (2 min)

**Do:** nothing. One slide, or no slide.

**Say:**
- Two tools, one day's work: write an ontology, write the transformations that
  populate it, review those transformations, add the rules your project needs —
  and then decide what any of it should block.
- They are not alternatives. The registry has 61 checks; the editor runs 50 of
  them in-process as you type, and the 11 it does not are exactly the 11 the
  CLI alone can produce. 50 + 11 = 61, with nothing falling between.
- And three checks exist that **only** the editor can produce. Both lists are
  asserted by tests in the two repos, not claimed in a brochure.
- The rule all day: the cheap check belongs where you are typing, the expensive
  one belongs in the pipeline.

**Land:** this is about where a check lives, not which product wins.

---

## Act 1 — Writing an ontology (12 min)

### Beat 1 — Start a file (0:00)

**Do:** **Ontology Suite: New Ontology...** Base IRI, prefix, imports picker —
take gist and SKOS.

**Say:**
- Header, version IRI, imports — generated, not typed.
- Each import also inserts its `@prefix`, so the vocabulary is usable as CURIEs
  immediately. That is the difference between an imports list and a usable file.

**Land:** nobody should hand-write a header.

### Beat 2 — The tool has an opinion (1:30)

**Do:** **Ontology Suite: Add Class or Category...** Let it ask the question.
Choose `gist:Category` for something that should have been an `owl:Class`.

**Say:**
- It asks whether the term needs its own structure and relationships, or is a
  classification of other things.
- That is a modelling decision, and getting it wrong is the commonest thing I
  see in a new ontology — a category that grows properties until it is a class
  in everything but name.
- Note what it does *not* do: no auto-generated paired inverse property.
  Deliberate.
- I have just chosen wrong on purpose. Remember this one.

**Land:** the scaffold is making you answer the question you would otherwise
skip.

### Beat 3 — Author from the outline (3:00)

**Do:** Right-click a class in the Ontology Outline → **Add Subclass**, and give
it a real Manchester restriction, e.g. `hasReading some Reading`. Then drag one
class onto another.

**Say:**
- Protégé-shaped authoring without leaving the file.
- The restriction is parsed by the same class-expression engine `.omn` files
  use — one implementation, not a second one for the outline.
- The drag added a parent. It did not *move* the class — the old parents are
  still there, and it says so. Never destructive.

**Land:** structured authoring, plain text file.

### Beat 4 — Where the ontology sits (4:30)

**Do:** Point at the status bar, then **Ontology Suite: Show Metrics & DL
Expressivity**.

**Say:**
- OntoQA-style metrics, a DL expressivity label, EL/QL/RL profile badges.
- It never *restricts* you to a profile. It tells you where you are, so staying
  in a light profile can be a decision rather than an accident.

**Land:** expressivity is a choice you can now see.

### Beat 5 — The check nothing else can make (6:00) ★ hinge

**Do:** Type a typo into an axiom: `:Pump rdfs:subClassOf :Machnie`. Then
**Ontology Suite: Run Local Checks**. Point at `VOC-001` in the Problems panel.
Then run the CLI over the same file:

```
uv run ontology-quality-suite checks \
  --ontology competency_tests/fixtures/vsix/extension-only.ttl \
  --out-dir out/demo/vsix
```

> 2 finding(s): `DAT-002`, `QUA-004`

**Say:**
- `:Machnie` is a typo for `:Machine`. The editor says so.
- Now the same file through the CLI: two findings, and neither is this one.
- That is not a bug. SHACL is open-world: nothing *contradicts* an undeclared
  class existing — it simply was never asserted to. The question "did you mean
  `:Machine`?" cannot be posed in that logic.
- So the editor does it closed-world, scoped to namespaces the graph already
  knows some terms in — which is why an unimported `foaf:` does not flood you.
- Three checks in total only exist here. This is the one that matters most,
  because a misspelled class in an axiom is invisible to every check the
  pipeline has.

**Land:** the editor is not a convenience wrapper. It asks questions the
pipeline cannot.

### Beat 6 — Fix it without typing (8:30)

**Do:** Lightbulb on a missing-label finding → **Quick Fix**. Show the preview
of exact triples. Apply.

**Say:**
- Sixteen checks offer a repair. Each is computed from a real SPARQL Update, not
  a string edit.
- Nothing is written until you have seen the triples that will change.
- Where the project has standards — a language tag, a category class — the
  repair is completed from `.ontology-suite/standards.json`. Hold that thought
  for Act 4.

**Land:** repairs are reviewable before they happen.

### Beat 7 — The honest limit (10:00) ★ hinge

**Do:** Seed a class both `owl:disjointWith` and `rdfs:subClassOf` the same
parent. **Run Local Checks** — nothing. Then **Ontology Suite: Run Deep
Validation (Python CLI)**.

> `REA-021` — class unsatisfiable

**Say:**
- The editor found nothing, and it is right not to have.
- Its in-process reasoner is an OWL2-RL-subset ruleset: sound, not complete. It
  cannot answer "is this ontology consistent" or "is this class satisfiable" in
  general.
- `REA-020`, `021` and `022` need a real DL reasoner — HermiT through
  owlready2. That is a different piece of software and it costs seconds, not
  milliseconds.
- Eleven of the sixty-one checks are like this. The extension lists them, with
  the reason for each, in its own test file. The limit is documented, not
  discovered.

**Land:** the editor tells you where it stops. Run the deep pass before you
publish.

---

## Act 2 — Creating a set of TARQL transformations (12 min)

### Beat 1 — Start from the data (0:00)

**Do:** **Ontology Suite: Infer Ontology + Query from CSV...** on the raw CSV.

**Say:**
- It profiles the CSV — types, cardinality — and drafts both an ontology
  fragment and a CONSTRUCT wired to it.
- A starting point from the data's real shape. Everything after this is
  editing, which is the easy part.

**Land:** the first draft is generated, not written.

### Beat 2 — See the triples before you commit (1:30)

**Do:** **Ontology Suite: Open Query Workbench**. Edit the query and let the
preview update.

**Say:**
- Three views of one query: the real triplified output from sample rows, a
  static sketch of the CONSTRUCT template, and a conformance panel against the
  ontology.
- The preview is Oxigraph with TARQL semantics reproduced by a standard SPARQL
  `VALUES` injection. Real triples, not a mock-up.
- Twenty rows by default. Enough to see the shape, fast enough to type through.

**Land:** the edit loop is seconds, not a pipeline run.

### Beat 3 — Break a prefix (3:30)

**Do:** Change a prefix so the query references a term the ontology lacks. Watch
the conformance panel.

**Say:**
- Undeclared classes and properties, and prefix drift, against the ontologies
  found beside the query — its own directory, then the parent, then siblings.
- All of them, because an extension ontology plus the upper ontology it builds
  on is the normal case.
- If your layout is unusual, pin them with `ontologySuite.queryOntologyPaths`.

**Land:** the query is checked against the model while you write it.

### Beat 4 — Two valid files, one broken join (5:30) ★ hinge

**Do:** Write a second query minting the same entity a different way. Then
**Ontology Suite: Review TARQL BIND Consistency** on the folder. Show `TQL-001`
in Problems and the side-by-side in the *TARQL BIND Review* output channel.

**Say:**
- Both queries are valid. Both produce triples. Neither file is wrong.
- But the two IRIs for what should be one node never join, and that surfaces
  weeks later as a dangling reference or a duplicate entity.
- `TQL-001` compares the *skeleton* of the expression, not its text — the same
  template with a different column name is ordinary and is not reported. A
  different template is.
- This is invisible in either file alone. It needs the set.

**Land:** the defect lives between the files.

### Beat 5 — The silent one (8:00)

**Do:** Use a template variable nothing binds. Same command → `TQL-002`.

**Say:**
- Every triple using that variable is dropped. For every row. With no error.
- An unbound constructed IRI is never correct — fix these first, always.

**Land:** a transformation can succeed and produce nothing.

### Beat 6 — Now pay for the real run (9:30)

**Do:** **Ontology Suite: Run Full Triplify (Python CLI / oxi-gen)**.

**Say:**
- Everything so far cost seconds and needed no data at all.
- This shells out to the real `oxi-gen` binary for production-scale output.
- That order is the whole discipline: BIND consistency first because it is
  cheap, triplify last because it is not. The extension's own
  `docs/TESTING_TARQL.md` gives that review order; I am just following it.

**Land:** cheap checks before expensive ones, deliberately.

### Beat 7 — The check that needs output (11:00)

**Do:** **Run Local Checks** on the triplified output. Show `CNF-003`/`CNF-004`.

**Say:**
- A property used outside its declared domain; a value outside its range.
- Nothing before this beat could have found it, because until now there were no
  triples to judge.

**Land:** four kinds of thing go wrong in transformations, and only the last
needs the pipeline to have run.

---

## Act 3 — Reviewing the patterns across the set (12 min)

### Beat 1 — Start by showing the editor satisfied (0:00)

**Do:** **Review TARQL BIND Consistency** on the full four-mapping folder.
Clean.

**Say:**
- Clean. No drifting templates, no unbound variables.
- This is where most reviews stop, and it is a real result — it just is not the
  whole question.
- Everything from here is a property of the *set*, and no individual file has
  it.

**Land:** a clean per-file review is the floor, not the ceiling.

### Beat 2 — One class, two shapes (1:30)

**Do:** Run the mapping-drift pass. Show `CMP-034`.

**Say:**
- `sites.rq` gives this class a name. `readings.rq` builds the same class and
  gives it nothing.
- Both files pass every check in the editor. Together they produce a class that
  is sometimes labelled and sometimes not, depending which mapping got there
  first.
- This is asked of the sketch graph — what the CONSTRUCT templates *say they
  build* — which the editor does not construct.

**Land:** consistency across mappings is a different question from correctness
within one.

### Beat 3 — The one that really happened (3:30) ★ hinge

**Do:** `CMP-037` on the prefix disagreement. Show the two declarations:
`gist:` ending in `#` in one file, `/` in another.

**Say:**
- One file ends the namespace with a hash, the other with a slash. Every term
  they build is a different IRI.
- This is not invented. It was found by these fixtures, reported upstream, and
  fixed in suite 0.21.0 — and the false positive that had been *hiding* it was
  fixed in 0.20.0.
- Until that fix, the real finding was buried under a spurious one about the
  tool's own vocabulary. That is the honest history of this check.

**Land:** these are not hypothetical defects; this one cost a release to get
right.

### Beat 4 — Did anything move that shouldn't have? (6:00)

**Do:** Edit one mapping. Re-run. Show `CMP-038` against the golden output.

**Say:**
- One mapping changed; the question is what else changed with it.
- A golden file turns "the output looks fine" into "the output differs here,
  here and nowhere else".
- This is the beat reviewers recognise as their own job — and the one most
  worth automating, because doing it by eye does not scale past two files.

**Land:** diff the output, not just the code.

### Beat 5 — Did every record arrive? (8:00)

**Do:** `CMP-015` and `CMP-016` from the mapping-integrity pass.

**Say:**
- `CMP-016`: four source rows became two entities, because the IRI is built
  from the site alone and each site's readings collapse onto one node.
- `CMP-015`: the template promises a property no source column feeds.
- Both are questions about source records versus real output. Neither tool
  finds them by looking at a query.

**Land:** count what went in against what came out.

### Beat 6 — What the version bump broke (9:30)

**Do:** `consistency` and `version-diff`, ontology 1.0.0 → 2.0.0, against
mappings nobody updated.

**Say:**
- A class was removed. The suggested bump is MAJOR, computed from the axioms,
  not from somebody's judgement.
- And here are the mappings that still build the term it removed.

**Land:** the model and the transformations version together or they drift.

### Beat 7 — One exit code (11:00)

**Do:** `uv run python gate.py --config ontology-suite.yml`.

**Say:**
- The same checks, a committed config file, and the suite's own exit code.
- The run a developer does by hand, the run in CI, and the run in a git hook
  are the same run — not three command lines that drift apart.

**Land:** everything shown so far can gate a merge today.

---

## Act 4 — Checks the tools do not ship (10 min)

### Beat 1 — Name the rule (0:00)

**Do:** No tooling. Say the rule.

**Say:**
- "Every vehicle carries an asset tag of the form `FLT-NNNNNN`."
- Nothing ships with that check and nothing should. It is the key the
  maintenance system, the finance ledger and the telematics feed all join on,
  and it is true only here.
- Every project has three or four of these. They are usually in a wiki, and
  they are usually broken.
- Three ways to make it a real check, cheapest first.

**Land:** the interesting checks are the ones only you can write.

### Beat 2 — Tier one: JSON, no SPARQL (1:00)

**Do:** Author `.ontology-suite/class-rules.json` live:

```json
{ "rules": [
  { "appliesTo": "owl:ObjectProperty", "requires": ["rdfs:label", "rdfs:domain", "rdfs:range"] }
] }
```

Save. **Run Local Checks**. Show `PRJ-REQUIRED` in Problems, and the Quick Fix
on a missing label.

**Say:**
- "Every resource of this type needs these predicates." Plain JSON, with
  completion from a bundled schema — no SHACL, no Turtle.
- Findings go through the same pipeline as every other check, including Quick
  Fix. A missing label is auto-fixable from the local name.
- `rdfs:domain` is not auto-fixable, and correctly offers no repair — there is
  no safe machine-generated value for it.
- This file is meant to be committed. It travels with the ontology.

**Land:** the first tier costs a minute and needs no query language.

### Beat 3 — Tier two: a real SPARQL check (3:00)

**Do:** Open `examples/cross-folder-checks/folder-b-house-checks/` — the
fragment and `sparql/structural/FLT-001.rq`. Then:

```
bash examples/cross-folder-checks/folder-a-fleet-project/validate.sh
```

> 61 from the installed suite, 4 house, 65 in total
> Findings: 11 total (4 Violation, 3 Warning, 4 Info)
> `FLT-001  Violation  Vehicle asset tag missing or not in the house format`

**Say:**
- Two files per check: a `.rq` CONSTRUCT that decides what fires, and a
  registry entry that gives it a title, a severity and the fix-it text.
- Note what came back in the report — *our* remediation wording, not the
  suite's. That is how you know the registry merge worked rather than merely
  not crashing.
- And note where it lives: a different folder, owned by a standards group, not
  by this project. Referenced, not copied.
- Four house rules sitting alongside the suite's 61, in one run, with one
  severity scale.

**Land:** a project rule becomes a first-class check, with no fork of anything.

### Beat 4 — The same rule, in the editor (5:00)

**Do:** Set `ontologySuite.checksRegistryPath` to the checkout holding
`registry.json`/`sparql/`/`shapes/`. **Run Local Checks**. `FLT-001` appears in
Problems.

**Say:**
- Same rule, now live in the editor, as you type.
- One sharp edge, and it is the same edge in both tools: this setting
  *replaces* the bundled registry rather than adding to it — exactly as
  `--registry` does on the command line.
- So check what I am checking: the standard findings are still there too. If
  they vanish, you are running your four checks and none of the suite's, and
  nothing looks wrong.

**Land:** write the rule once; it runs where you type and where you merge.

### Beat 5 — Tier three: SHACL, and why it is different (6:30)

**Do:** Open `folder-c-house-shapes/shapes/fleet-house.ttl` — `oq:FLT-004`,
cardinality. Show it fired from the `shacl` arm in the same run.

**Say:**
- Cardinality is what SHACL says natively: one path, `minCount`, `maxCount`,
  against a target class. Writing that as a CONSTRUCT would be worse.
- Two conventions that are not decoration. The shape node's local name *is* the
  check id — rename it and the finding still fires, as `UNMAPPED`, with no
  title and no advice.
- And `sh:severity` goes on the shape node. The shape's severity wins over the
  registry's: I measured this — move it to the nested property node as
  `sh:Info` and a rule the registry calls a Violation reports as Info, and your
  gate passes.
- The flags differ too, and this is the thing to write down: `--sparql`
  repeats, takes `@builtin`, and recurses. `--shapes` does none of those. One
  directory, no `@builtin`, top-level `*.ttl` only, and it replaces the suite's
  shapes outright.
- So there is no way to say "the suite's shapes and also mine". You have to
  build the directory. That is what the prepare step does.

**Land:** SPARQL checks add; SHACL shapes replace. Know which you are writing.

### Beat 6 — The failure worth fearing (8:30) ★ hinge

**Do:** Point `--shapes` at Folder C directly. Run. Show the finding ids: *the
same eleven*. Then show the one cell that changed:

```
check      correct wiring    Folder C alone
STR-002    shacl+sparql      sparql
```

**Say:**
- I have just dropped twenty-one of the suite's own shapes. Look at the report:
  same ids, same counts, same severities. No error. No warning.
- It looks identical because every check those shapes implement also has a
  SPARQL twin that still runs. Half the cross-validation stopped and the output
  cannot tell you.
- The only trace in the entire report is one cell in the `sources` column.
- Which is why the prepare step reads the config file and refuses to run if the
  config does not name what it just assembled — it is the only place that holds
  both halves of the reference.
- Five ways this wiring breaks. Each one measured, each one in that README. Two
  of them are completely silent.

**Land:** when you extend the checks, the dangerous mistake is the one that
still looks green.

### Beat 7 — Turning checks down (9:30)

**Do:** `ontologySuite.disabledChecks: ["QUA-010"]`.

**Say:**
- The other half of extensibility. A disabled check's query is not run at all,
  and its findings are dropped whichever engine produced them.
- Use it to make the Problems panel yours while iterating. Do not use it to
  make a gate pass.

**Land:** you own the check set in both directions.

---

## Act 5 — The standard checks, read your way (12 min)

> **This act stands alone.** It needs nothing from Acts 1–4 and can open the
> session, or be the whole session. It answers the objection that otherwise
> ends an adoption conversation: *we cannot switch this on, it would fail
> everything on day one.*
>
> Requires suite **0.25.0** or later for `--severity-policy`/`--stringency`.

### Beat 1 — The situation, in three folders (0:00)

**Do:** Three windows, nothing running.

```
consolidated_ontology_suite_python/   the suite        (installed)
policy-repo/                          severities.json  (someone else's repo)
work-folder/myOntology.ttl            what we evaluate (ours)
```

**Say:**
- This is the shape of the real question: the checks come from one place, the
  severities your organisation wants come from another, and the thing being
  evaluated is yours.
- The policy repo is deliberately not ours. It is the standards group's, or
  another team's, or a submodule. We reference it; we never copy it.
- And the suite being a local checkout changes nothing here. We point at the
  *installed* suite, however it got installed — editable checkout, wheel from
  PyPI, does not matter. Nothing in this act edits it.

**Land:** three owners, three folders, one run.

### Beat 2 — What the checks say (1:30)

**Do:**

```
uv run ontology-quality-suite checks --ontology myOntology.ttl \
  --engine both --own-namespace https://example.org/mine --fail-on Violation
```

> Findings: 13 total (2 Violation, 6 Warning, 5 Info)
> blocks on: STR-002, STR-007 — exit 1

**Say:**
- No policy yet. This is what the checks themselves declare, and it is the
  baseline everything else is read against.
- `STR-002` is "a property is used and never declared". The suite calls that a
  Violation, and it is right to — in general.
- Here, mid-modelling, we know about it and we are not going to stop for it.
  That is not the suite being wrong. It is the same fact meaning something
  different at this point in the work.

**Land:** the default reading is a real reading, not a placeholder.

### Beat 3 — The JSON file becomes the severity (3:00) ★ hinge

**Do:** Show `policy-repo/severities.json` — all of it:

```json
[
  { "STR-003": "Violation" },
  { "STR-002": "Info" }
]
```

Then add one flag:

```
  --severity-policy ../policy-repo/severities.json
```

> Severity policy 'default' from severities.json: 2 check(s) re-mapped
>   STR-002 Violation -> Info (1 finding(s))
>   STR-003 Warning -> Violation (1 finding(s))
> Findings: 13 total (2 Violation, 5 Warning, 6 Info)

**Say:**
- That is the whole file. A list of check ids and the severity we want. No
  SPARQL, no SHACL, no stage vocabulary to learn.
- One flag. Nothing was copied, nothing was rewritten, and the suite's own
  checks are the ones that ran.
- Now look carefully, because this is the point of the act:

```
            findings   Violations   which ones
defaults    13         2            STR-002, STR-007
policy      13         2            STR-003, STR-007
```

- **Same count. Same number of Violations. A different pair.** Nothing was
  hidden and nothing was invented — the same thirteen facts are being read
  against a different standard.
- If you only ever look at the totals, you cannot see that. It is the named
  checks that tell you what a gate is actually enforcing.

**Land:** the JSON file is now the severity, and it took one flag.

### Beat 4 — Why this is not a fudge (5:00)

**Do:** Open `full_results.csv`. Point at the `declared_severity` column.

> `STR-002, Info, Violation, ...`

**Say:**
- The obvious worry about a feature like this is that it is a way to make red
  things green and say nothing.
- So it cannot be done quietly, by construction. Three things:
- The run **prints every re-mapping**, naming the stage and the file it came
  from. It is in the log of whoever ran it.
- The CSV carries **`declared_severity`** — what the check itself said —
  populated *only* where a policy moved it. A reviewer sees both readings side
  by side without being told which policy ran.
- And a policy that changes nothing **warns**, because a wrong stage name is
  otherwise indistinguishable from a correct run.
- The suite's own contributor guide says: set severity to what is true, and use
  `--fail-on` to decide what blocks. This does not weaken that. The check still
  says what is true; the policy records, in the open, what this project does
  about it here.

**Land:** a policy can change what blocks a build. It cannot do it quietly.

### Beat 5 — The two ways this is usually got wrong (7:00) ★ hinge

**Do:** Show the table. Do not run these live — they take a minute each and
produce nothing to look at, which is the point.

```
Approach                                   Result
Write the severities into the registry     the shipped result, exactly
and pass --registry                        13 findings, both overrides ignored

Copy the suite's checks and rewrite        looks like it worked
the .rq files                              same total, same Violation count,
                                           severities still the shipped ones
```

**Say:**
- Both of these are what you reach for first. Neither produces a diagnostic of
  any kind.
- **The registry does not decide severity.** Its `default_severity` drives
  report badges and Cucumber tags. Each check carries its own
  `sh:resultSeverity` or `sh:severity`, and that is what is read and what
  `--fail-on` gates on.
- The second is worse, because it looks like it worked. Rewrite the query and
  leave the shape, and **the shape wins** — in both directions. `STR-002` came
  back Violation where we asked for Info; `STR-003` came back Warning where we
  asked for Violation.
- And `sources` still read `shacl+sparql`, so nothing reported a disagreement.
  Twenty-one of the suite's checks are written both ways. This is not an edge
  case.
- Applying the policy to *findings* removes the failure entirely: by then a
  check written both ways is one row, so there is no half of it to miss.

**Land:** the reason this is a flag and not a recipe is that every recipe
fails silently.

### Beat 6 — One reading is rarely enough (9:00)

**Do:** Show `severities-by-stage.json`, then:

```
bash examples/severity-policy/work-folder/compare.sh
```

> ```
> check     defaults    sketch      draft       release
> STR-002   Violation   Info        Warning     Violation
> STR-003   Warning     Info        Info        Violation
>
> blocks on defaults  STR-002, STR-007
>           sketch    STR-007
>           draft     STR-007
>           release   STR-002, STR-003, STR-007
> ```

**Say:**
- The same file grows stages when one reading stops being enough. `extends`
  means three stages that differ in two checks do not restate the other forty.
- The stage names are **ours**. The suite ships none and has no opinion — call
  them what your process calls them.
- `STR-002` runs Info → Warning → Violation across the three, and the check is
  untouched between runs. That is exactly what one `--fail-on` threshold cannot
  say: it sets *how strict*, not *about what*.
- And look at the totals: **thirteen findings, every single time.** The report
  does not change. What it means here does.

**Land:** stringency becomes a property of the stage, not of the check.

### Beat 7 — Commit it, so nobody has to remember (11:00)

**Do:** Show the two configs side by side. The second is the first plus two
lines.

```yaml
severity_policy: ../policy-repo/severities-by-stage.json
stringency: release
```

```
uv run python gate.py --config ontology-suite-release.yml
```

**Say:**
- Two committed configs: one for the defaults, one for release. The difference
  is two lines, and `gate.py` resolves the policy path against the config, so
  it works from any directory and from CI.
- That is the real win. Which reading a branch is held to stops being a flag
  someone remembers to pass.
- One honest limit, and say it rather than let them find it: **this is the CLI.**
  The editor has no stringency. Its blunt instrument is
  `ontologySuite.disabledChecks`, which drops a check entirely — fine for
  keeping the Problems panel usable while you iterate, not a substitute for a
  policy.
- So the shape is: the editor shows you everything as you type; the gate decides
  what blocks, per stage, from a file you can read in a pull request.

**Land:** the question is never "is this a Violation". It is "is it a Violation
*here, now*" — and that answer belongs in a committed file.

---

## Close (2 min)

**Say:**
- Five acts, one rule: the cheap check where you type, the expensive one in the
  pipeline, and you decide what any of it blocks.
- The editor does 50 of the registry's 61 in-process, plus three that no
  pipeline can do. The CLI does the 11 remaining, and asks the questions that
  need more than one file — the set-level ones from Act 3.
- Both are extensible by you, in three tiers: JSON rules, SPARQL checks, SHACL
  shapes. Committed, versioned, running in the editor and in CI from the same
  source.
- And the check set is yours in a second sense: a JSON file of check ids and
  severities decides what any of it *means here*, per stage, without editing a
  single check. Printed on every run and recorded next to what the check
  declared, so it is a decision in the open rather than a fudge.
- The one thing to take away: when you add your own checks, or change what they
  mean, the mistake to fear is not the one that errors. It is the one that
  still reports green.

**Then, and only then:** **Ontology Suite: Visualize Subject Graph**, for the
questions.
