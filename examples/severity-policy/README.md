# The same checks, read your way

One ontology, evaluated at the severities the checks themselves declare, and
then at the severities this project wants at a given point in its life.
Nothing is copied, nothing is rewritten, and every report here is comparable
with every other by construction, because all of them ran the installed
suite's own checks.

Two policies are committed, in three file arrangements, because the arrangement
turns out to matter more than the schema: start at
[the plainest one](#the-plainest-form-one-flat-file-per-level) if you want the
shortest path to a working file.

```
severity-policy/
├── policy-repo/                     <- a separate repo, someone else's
│   ├── severities.json                  ids -> severity, one reading
│   ├── severities-by-stage.json         three stages, one file
│   ├── severities-sketch.json           the same three, one file each
│   ├── severities-draft.json
│   ├── severities-release.json
│   └── levels/                          a second policy, flat files only
│       ├── exploring.json               one id per object, no stage names
│       ├── reviewing.json
│       └── publishing.json
└── work-folder/                     <- the ontology under evaluation
    ├── myOntology.ttl
    ├── ontology-suite.yml               gate 1: the defaults
    ├── ontology-suite-release.yml       gate 2: release stringency
    ├── validate.sh                      both gates, from those two configs
    ├── compare.sh                       all four readings, side by side
    ├── compare.py                       the comparison table
    ├── split.sh                         one file per stage, and the proof
    │                                    it is the same policy
    └── levels.sh                        the flat files, against the defaults
```

Everything is invented; the namespace is `example.org`. Every number below
came from running the commands shown.

## What this needs

`--severity-policy` and `--stringency`, which are **suite 0.25.0 and later**.
`compare.sh`, `split.sh` and `levels.sh` check for the flag and say so rather
than failing obscurely.

Before 0.25.0 there was no supported mechanism. *Why the flag exists*, at the
end, is the measured argument for adding one rather than leaving it to each
project.

---

## Reading 1: the defaults

No mention of severity anywhere. This is what the checks say.

```yaml
# ontology-suite.yml
ontology: myOntology.ttl
engine: both
own_namespace: https://example.org/mine
fail_on: Violation
out_dir: out/defaults
```

```
Findings: 13 total (2 Violation, 6 Warning, 5 Info)
gate: FAIL (suite exit 1, --fail-on Violation)
```

It blocks on `STR-002` (a property used and never declared) and `STR-007`.

## Reading 2: an alternative interpretation

[`policy-repo/severities.json`](policy-repo/severities.json) is the whole
file — a list of check ids and the severity this project wants:

```json
[
  { "STR-003": "Violation" },
  { "STR-002": "Info" }
]
```

One flag applies it, and no stage name is needed when the file has only one
reading:

```
--severity-policy ../policy-repo/severities.json
```

```
Severity policy 'default' from severities.json: 2 check(s) re-mapped
  STR-002 Violation -> Info (1 finding(s))
  STR-003 Warning -> Violation (1 finding(s))
Findings: 13 total (2 Violation, 5 Warning, 6 Info)
```

**Thirteen findings and two Violations, both times — but a different pair.**
The defaults block on `STR-002` and `STR-007`; this blocks on `STR-003` and
`STR-007`. Nothing was hidden and nothing invented: the same thirteen facts,
read against a different standard. Totals alone cannot show you that.

### When one reading is not enough

[`severities-by-stage.json`](policy-repo/severities-by-stage.json) is the same
idea with named stages. The names are this project's — the suite ships none:

```json
{
  "stages": {
    "sketch":  { "STR-002": "Info", "STR-003": "Info" },
    "draft":   { "extends": "sketch", "STR-002": "Warning" },
    "release": { "extends": "draft", "STR-002": "Violation",
                 "STR-003": "Violation" }
  }
}
```

`extends` means three stages differing in two checks need not restate the
other forty. The release gate is then the default config plus **two lines**:

```yaml
# ontology-suite-release.yml
severity_policy: ../policy-repo/severities-by-stage.json
stringency: release
```

```
Severity policy 'release' from severities-by-stage.json: 1 check(s) re-mapped
  STR-003 Warning -> Violation (1 finding(s))
Findings: 13 total (3 Violation, 5 Warning, 5 Info)
gate: FAIL (suite exit 1, --fail-on Violation)
```

Note what is *not* in that config: no registry, no shapes directory, no
assembled copy of anything. The policy is applied to the findings.

> There is a third value besides the three severities — `off`, which drops a
> check's findings entirely, for a question that does not apply at a stage
> yet. It is left out of this example to keep the contrast about severity;
> `docs/SEVERITY_POLICY.md` in the suite covers it.

### Or one file per stringency

`extends` cannot reach across files, so the alternative to one nested file is
three self-contained ones, each holding a single stage:
[`severities-sketch.json`](policy-repo/severities-sketch.json),
[`severities-draft.json`](policy-repo/severities-draft.json),
[`severities-release.json`](policy-repo/severities-release.json).

```json
{
  "stages": {
    "draft": {
      "STR-002": "Warning",
      "STR-003": "Info"
    }
  }
}
```

Each is selected exactly as the nested file is, by naming the one stage it
holds, so a gate changes by one line, the filename:

```yaml
severity_policy: ../policy-repo/severities-release.json
stringency: release
```

```bash
bash examples/severity-policy/work-folder/split.sh
```

```
== draft, from severities-draft.json
Severity policy 'draft' from severities-draft.json: 2 check(s) re-mapped
  STR-002 Violation -> Warning (1 finding(s))
  STR-003 Warning -> Info (1 finding(s))
Findings: 13 total (1 Violation, 6 Warning, 6 Info)
   vs the nested file's 'draft' stage: identical

Both arrangements agree on every finding, at every stage.
```

`split.sh` runs each of the three files, runs the matching stage of the nested
file, and compares the two reports row by row — check id, focus node,
severity, declared severity. **All three stages come back identical**, which is
the only claim worth making here: this is a filing decision, not a different
policy.

**What splitting costs.** `STR-003` is `Info` at both sketch and draft, and the
draft file has to say so again. Nothing is shared, so each file restates every
entry it keeps, and the failure that follows is the ordinary one — two files
updated out of three.

**What splitting buys.** Each file names its stage, so a gate pointed at the
wrong file cannot run:

```
error: severities-sketch.json has no stage 'release'. Stages: sketch
exit 2, nothing written
```

That guard is the reason these three files are not written flat. A flat file is
read as a single stage called `default` and takes no `--stringency` at all, so
the same mistake is not an error: pointing a release gate at a flat sketch file
applies the sketch reading and carries on. Measured, with `--fail-on
Violation`:

```
Severity policy 'default' from flat-sketch.json: 2 check(s) re-mapped
  STR-002 Violation -> Info (1 finding(s))
  STR-003 Warning -> Info (1 finding(s))
Findings: 13 total (1 Violation, 5 Warning, 7 Info)
exit 1
```

Nothing is hidden — the audit line names the file it came from, and a reader
who notices `sketch` in a release log has found it. But the run did not refuse,
and that is the difference.

| | one nested file | one file per stringency | one flat file |
|---|---|---|---|
| Shape | `stages` with 2+ entries | `stages` with 1 entry | no `stages` key |
| Selected by | `--stringency <name>` | `--stringency <name>` — optional, but it is the guard | `--severity-policy` alone |
| Wrong file wired to a gate | n/a, one file holds every stage | **refused, exit 2** | applied silently |
| Entries shared between stages | `extends` | restated in each file | n/a |
| Room for a `_comment` | beside `stages` | beside `stages` | nowhere |

Choose by who owns the file. One nested file when one person or group owns the
whole progression and the stages mostly agree. One file per stringency when
different stages are reviewed, approved or released on different schedules —
then each is a small file with a name that says what it is, and the stage name
inside it is what stops it being used as the wrong one.

> A note on comments, since a policy file usually needs one: `_comment` is
> ignored only as a sibling of `stages`. Inside a stage, or anywhere in a flat
> file, it is read as a check id and the run stops with `_comment is not a
> check in this registry`. A good diagnostic, and the second reason to name
> the stage.

### The plainest form: one flat file per level

[`policy-repo/levels/`](policy-repo/levels/) holds a second, independent policy
in the plainest shape the loader accepts: no `stages` key, no stage names, just
a list with one id per object.

```json
[
  {
    "STR-001": "Violation"
  },
  {
    "STR-002": "Warning"
  },
  {
    "STR-003": "Info"
  }
]
```

Three files, three levels of stringency over the same six structural checks.
The names are deliberately not `sketch`/`draft`/`release` — they are another
project's vocabulary, and the suite ships none.

| File | The reading it encodes |
|---|---|
| [`exploring.json`](policy-repo/levels/exploring.json) | a model being sketched. An undefined class is a typo at any stage, so `STR-001` stays `Violation`; missing domains, ranges and definitions are `Info`, because they are not written yet rather than wrong |
| [`reviewing.json`](policy-repo/levels/reviewing.json) | ready to show someone. Structure has to hold; prose can lag, so `STR-004` (class has no formal definition) is the single concession |
| [`publishing.json`](policy-repo/levels/publishing.json) | anyone may depend on it. Everything structural blocks |

A flat file *is* a single unnamed stage, so each is selected by one flag with
nothing to choose inside it — no `--stringency`, and the filename is the only
name the level has:

```
--severity-policy ../policy-repo/levels/reviewing.json
```

```bash
bash examples/severity-policy/work-folder/levels.sh
```

```
Each run, as a whole
  defaults   13 finding(s) (2 V, 6 W, 5 I) across  9 check(s)
  exploring  13 finding(s) (0 V, 6 W, 7 I) across  9 check(s)
  reviewing  13 finding(s) (2 V, 5 W, 6 I) across  9 check(s)
  publishing 13 finding(s) (4 V, 4 W, 5 I) across  9 check(s)

Where the readings differ
  check     defaults    exploring   reviewing   publishing
  STR-002   Violation   Warning     Violation   Violation
  STR-003   Warning     Info        Warning     Violation
  STR-004   Warning     Info        Info        Violation
  STR-007   Violation   Warning     Violation   Violation

What each run would block on, at --fail-on Violation
  defaults   STR-002, STR-007
  exploring  nothing
  reviewing  STR-002, STR-007
  publishing STR-002, STR-003, STR-004, STR-007
```

`levels.sh` reuses `compare.py` — it takes the run names to put beside the
defaults, so a second policy needed no second comparison script.

Three things this set shows that the staged one does not.

**A level at which nothing blocks.** `exploring` reports all thirteen findings
and zero Violations, so the gate passes while the report is unchanged. That is
the answer to *we cannot switch this on, it would fail everything on day one*:
switch it on at a level that blocks nothing and raise it later. Nothing is
hidden to get there — six Warnings and seven Infos are still in the report.

**Declaring what is already true costs nothing.** `reviewing` has six entries
and re-maps exactly one check, because the other five ask for the severity the
check already declares:

```
Severity policy 'default' from reviewing.json: 1 check(s) re-mapped
  STR-004 Warning -> Info (1 finding(s))
```

So a file can be written out in full, as a statement of what this level
expects, without that making it look like five overrides. If *nothing* in it
moves, the run says so rather than passing quietly — measured on a variant
whose five entries all restate what the checks already declare:

```
WARNING: severity policy stage 'default' changed nothing: none of its 5
check(s) produced a finding whose severity differed. Check the stage name if
that is a surprise.
Severity policy 'default' from restating-the-defaults.json: 0 check(s) re-mapped
Findings: 13 total (2 Violation, 6 Warning, 5 Info)
```

**The blocking set does not identify the reading.** `reviewing` blocks on
`STR-002, STR-007` — the same pair as the defaults — and is not the same
policy: `STR-004` is `Info` there. Two runs can agree on what fails and
disagree about everything else, which is the second reason the
`declared_severity` column exists.

The cost of this shape is the one the table above names: a flat list has
nowhere to put a comment, and no stage name inside it to check, so pointing a
publishing gate at `exploring.json` runs happily. If that wiring is going to
be done by hand in more than one place, name the stage instead.

---

## Both, side by side

```bash
bash examples/severity-policy/work-folder/compare.sh
```

```
Each run, as a whole
  defaults   13 finding(s) (2 V, 6 W, 5 I) across  9 check(s)
  sketch     13 finding(s) (1 V, 5 W, 7 I) across  9 check(s)
  draft      13 finding(s) (1 V, 6 W, 6 I) across  9 check(s)
  release    13 finding(s) (3 V, 5 W, 5 I) across  9 check(s)

Where the readings differ
  check     defaults    sketch      draft       release
  STR-002   Violation   Info        Warning     Violation
  STR-003   Warning     Info        Info        Violation

What each run would block on, at --fail-on Violation
  defaults   STR-002, STR-007
  sketch     STR-007
  draft      STR-007
  release    STR-002, STR-003, STR-007
```

Three things to read off it.

**The totals do not move at all; the gate moves a lot.** Thirteen findings
across nine checks, every single time. What changes is which of them block:
one check at sketch, three at release. The report does not change — what it
means here does. A count is not a summary.

**`STR-002` travels the whole range** — `Info` at sketch, `Warning` at draft,
`Violation` at release — without the check being touched between runs. That is
the thing a single `--fail-on` threshold cannot express: it can say *how
strict*, not *about what*.

**`release` restores `STR-002` to `Violation`, which is what it declares**, so
that run re-maps one check rather than two. A stage asking for the shipped
severity is not an override, and the run says so.

### Nothing is relabelled quietly

```
What the checks themselves declared, where a stage moved them
  sketch     STR-002    Violation -> Info
  sketch     STR-003    Warning -> Info
  draft      STR-002    Violation -> Warning
  draft      STR-003    Warning -> Info
  release    STR-003    Warning -> Violation
```

Two mechanisms make that possible, and both matter if a policy is going to be
trusted:

- every re-mapping is **printed on the run that did it**, naming the stage and
  the file it came from;
- `full_results.csv` carries a **`declared_severity`** column holding what the
  check itself said, populated *only* where a policy moved it — so a reader of
  one report can tell a stage's reading from the check's own without being
  told which stage ran.

The suite's own `CLAUDE.md` says: *set severity to what is true and use
`--fail-on` to decide what blocks a build; do not relabel a finding to get a
green build.* That rule governs what the **check** declares. A project reading
the same finding differently at different points in its life is a separate
thing, and this is the auditable form of it.

---

## Running it

```bash
# both gates, from their committed configs, as CI would
bash examples/severity-policy/work-folder/validate.sh

# all four readings and the comparison
bash examples/severity-policy/work-folder/compare.sh

# the same three stages as three separate files, and the proof they agree
bash examples/severity-policy/work-folder/split.sh

# the flat one-file-per-level policy, against the defaults
bash examples/severity-policy/work-folder/levels.sh
```

`validate.sh` runs each config through `gate.py` and reports both exit codes.
`compare.sh`, `split.sh` and `levels.sh` use `--fail-on never` and compare
afterwards, because their job is to show the difference rather than to pass or
fail.

Committing the stringency is the point of the two-config arrangement: which
reading a branch is held to stops being a flag someone remembers to pass.

---

## Why the flag exists

Both of these were measured on this ontology, on suite 0.24.3, before
`--severity-policy` existed. Both are what a project reaches for first, and
neither produces a diagnostic of any kind.

| Approach | Result |
|---|---|
| Write the policy into the registry, pass `--registry` | **The shipped result exactly** — 13 findings, 2/6/5, both overrides ignored |
| Copy the suite's checks and rewrite the `.rq` files | **Looks like it worked.** Same total, same Violation count, different severities |

**The registry does not decide severity.** Its `default_severity` drives report
badges and cucumber tags; each check carries its own `sh:resultSeverity` /
`sh:severity`, and that is what `merge.py` reads and `--fail-on` gates on.

**Rewriting one arm is worse than doing nothing**, because it looks like it
worked. With `STR-002.rq` rewritten to `Info` and the shipped shape left at
`Violation`:

```
check      policy asked    reported
STR-002    Info            Violation
STR-003    Violation       Warning
```

The shape wins in both directions, and `sources` still reads `shacl+sparql`,
so nothing reports a disagreement. Twenty-one of the suite's checks are
written both ways, so this is not an edge case.

Applying the policy to *findings* rather than to checks removes the failure
entirely: by then a dual-formulated check is one row, so there is no half of
it to miss.
