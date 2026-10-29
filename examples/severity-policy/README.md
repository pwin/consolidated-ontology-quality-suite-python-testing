# The same checks, read two ways

One ontology, evaluated twice: once at the severities the checks themselves
declare, and once at the severities this project wants at a given stage of its
life. Nothing is copied, nothing is rewritten, and the two reports are
comparable by construction because both ran the installed suite's own checks.

```
severity-policy/
├── policy-repo/                     <- a separate repo, someone else's
│   └── severities.json                  three stages, ids -> severity
└── work-folder/                     <- the ontology under evaluation
    ├── myOntology.ttl
    ├── ontology-suite.yml               gate 1: the defaults
    ├── ontology-suite-release.yml       gate 2: release stringency
    ├── validate.sh                      both gates, from those two configs
    ├── compare.sh                       all four readings, side by side
    └── compare.py                       the comparison table
```

Everything is invented; the namespace is `example.org`. Every number below
came from running the commands shown.

## What this needs

`--severity-policy` and `--stringency`, which are **suite 0.25.0 and later**.
`compare.sh` checks for the flag and says so rather than failing obscurely.

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

Three stages, named by this project. The suite ships none and has no opinion
about them:

```json
{
  "stages": {
    "sketch":  { "STR-002": "Info", "STR-003": "Info", "QUA-004": "off" },
    "draft":   { "extends": "sketch", "STR-002": "Warning" },
    "release": { "extends": "draft", "STR-002": "Violation",
                 "STR-003": "Violation" }
  }
}
```

`extends` means three stages that differ in two checks need not restate the
other forty. `off` is not a severity — the suite has exactly three — it says
*do not ask this question at this stage*, which is different from `Info`,
meaning *we looked and here it is*.

The release gate is the default config plus **two lines**:

```yaml
# ontology-suite-release.yml
severity_policy: ../policy-repo/severities.json
stringency: release
```

```
Severity policy 'release' from severities.json: 2 check(s) re-mapped
  QUA-004 Warning -> off (1 finding(s) dropped)
  STR-003 Warning -> Violation (1 finding(s))
Findings: 12 total (3 Violation, 4 Warning, 5 Info)
gate: FAIL (suite exit 1, --fail-on Violation)
```

Note what is *not* in that config: no registry, no shapes directory, no
assembled copy of anything. The policy is applied to the findings.

---

## Both, side by side

```bash
bash examples/severity-policy/work-folder/compare.sh
```

```
Each run, as a whole
  defaults   13 finding(s) (2 V, 6 W, 5 I) across  9 check(s)
  sketch     12 finding(s) (1 V, 4 W, 7 I) across  8 check(s)
  draft      12 finding(s) (1 V, 5 W, 6 I) across  8 check(s)
  release    12 finding(s) (3 V, 4 W, 5 I) across  8 check(s)

Where the readings differ
  check     defaults    sketch      draft       release
  QUA-004   Warning     -- off --   -- off --   -- off --
  STR-002   Violation   Info        Warning     Violation
  STR-003   Warning     Info        Info        Violation

What each run would block on, at --fail-on Violation
  defaults   STR-002, STR-007
  sketch     STR-007
  draft      STR-007
  release    STR-002, STR-003, STR-007
```

Three things to read off it.

**The totals barely move; the gate moves a lot.** Every stage reports twelve
findings. What changes is which of them block: one check at sketch, three at
release. A count is not a summary.

**`STR-002` travels the whole range** — `Info` at sketch, `Warning` at draft,
`Violation` at release — without the check being touched between runs. That is
the thing a single `--fail-on` threshold cannot express: it can say *how
strict*, not *about what*.

**`release` restores `STR-002` to `Violation`, which is what it declares**, so
that run re-maps only two checks rather than three. A stage asking for the
shipped severity is not an override, and the run says so.

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
```

`validate.sh` runs each config through `gate.py` and reports both exit codes.
`compare.sh` uses `--fail-on never` and compares afterwards, because its job
is to show the difference rather than to pass or fail.

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
