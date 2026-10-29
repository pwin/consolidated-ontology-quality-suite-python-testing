# A severity policy held in another repo

Three locations, which is the situation this example is for:

- the **installed suite**, wherever this install put it — not edited, not copied
  into the project
- a **policy repo**, someone else's, holding only a JSON list of check ids and
  the severity your organisation wants them reported at
- a **work folder** holding `myOntology.ttl`, the thing being evaluated

```
severity-policy/
├── policy-repo/                 <- the separate repo of JSON
│   └── severities.json              ids -> severity, nothing else
└── work-folder/                 <- the ontology under evaluation
    ├── myOntology.ttl
    ├── ontology-suite.yml           names the assembled copies, not the suite's
    ├── apply_severities.py          applies the policy to a copy of the checks
    └── validate.sh                  the whole run, two steps
```

Everything is invented; the namespace is `example.org`. Every number below came
from running the commands shown, on suite 0.24.3.

---

## Read this first, because it is the whole point

**The registry's `default_severity` does not decide what severity a finding
comes back at.** It is reporting metadata — it fills a column in the summary
tables, a badge in the HTML, a tag in the Cucumber output.

Each check carries its severity *literally*, in its own implementation:

- the portable query says `sh:resultSeverity sh:Violation` in its CONSTRUCT
- the shape says `sh:severity sh:Violation` on its node

`merge.py` reads the severity off the results graph the check produced, and
`cli._exit_code` gates on those row severities. So `--fail-on` follows the
check, never the registry. The suite's own source says as much, in
`run_literal_typing_check`: severity is hard-coded "to **match** `DAT-001`'s
`default_severity` in `resources/registry.json`". Matching, by convention, in
three places at once.

Which means the obvious approach does nothing at all:

```
# Policy severities written into the registry, checks left as shipped
Findings: 13 total (2 Violation, 6 Warning, 5 Info)     <- identical to shipped
  STR-002 -> Violation     (policy asked for Info)
  STR-003 -> Warning       (policy asked for Violation)
exit 1
```

Byte-for-byte the shipped result. No warning, no note, nothing in the report to
suggest a policy was supplied and ignored.

So `apply_severities.py` rewrites **the checks**, into a copy, and keeps the
registry in step so the reports do not contradict the findings.

---

## What was tested

Three overrides, one of each kind that matters:

| Check | Shipped | Policy | Why this one |
|---|---|---|---|
| `STR-002` | Violation | `Info` | lowering. Dual-formulated, so the shape must be rewritten too |
| `STR-003` | Warning | `Violation` | raising — and it changes whether the gate fails |
| `QUA-004` | Warning | `off` | suppression. SPARQL-only, so there is no shape to rewrite |

`off` is not a severity the suite has; `Violation`, `Warning` and `Info` are the
only three. It is this script's word for "stop running this check", implemented
by leaving the check's files out of the assembled copy, because the honest way
to say "not a worry" is not to ask the question.

[`myOntology.ttl`](work-folder/myOntology.ttl) is written so each of the three
fires exactly once, so a policy that stops working shows up as a finding at the
wrong severity rather than as a different total.

---

## How it was set up

### The policy repo declares ids and severities, nothing else

```json
[
  { "STR-002": "Info" },
  { "STR-003": "Violation" },
  { "QUA-004": "off" }
]
```

The list-of-single-key-objects shape is accepted, and so is a plain object —
both are natural to write and the difference is not worth an argument. What is
*not* accepted is an id the registry does not have or a severity the suite does
not have, because both fail silently otherwise. See the table at the end.

### The work folder assembles, because nothing composes

There is no "severity override" flag. `--registry` takes one file and replaces
the suite's; `--shapes` takes one directory and replaces the suite's; `--sparql`
is additive but there is nothing additive to say about a severity. So
[`apply_severities.py`](work-folder/apply_severities.py) builds all three
inputs, every run:

1. copy the installed suite's `sparql/` and `shapes/` trees into `out/`
2. rewrite `sh:resultSeverity` in each overridden check's `.rq`
3. rewrite `sh:severity` on each overridden check's shape node(s)
4. rewrite `default_severity` in a copied registry, so reports agree
5. **read it all back** and fail if any override is not on disk

It copies from the installed suite every run rather than from a committed
snapshot, so the assembled checks are always this install's. Commit a rewritten
copy and it freezes at the version it was copied from, silently.

Two details in step 3 that are easy to get wrong:

- **A shape binds to its check by its node's local name, or by an explicit
  `oq:checkId "ID"`.** Both are needed: `STY-002` ships as two nodes,
  `oq:STY-002-data` and `oq:STY-002-obj`, and neither local name is the check
  id — so matching on the name alone silently misses both.
- **A shape with no `sh:severity` at all reports Violation**, the SHACL
  default. The script refuses rather than leave that implicit.

### The config names the copies, and never the suite's own

```yaml
registry: out/registry.json
sparql:
  - out/sparql          # no "@builtin" -- this IS the builtin tree, rewritten
shapes: out/shapes      # required: a shape's severity beats the registry
engine: both
fail_on: Violation
```

`apply_severities.py` parses this file and refuses to finish if it disagrees
with what was just assembled — it is the only place that holds both halves of
the arrangement.

---

## How it was run

```bash
bash examples/severity-policy/work-folder/validate.sh
```

Apply, then gate. The apply must come first, since the config points at what it
writes; it is cheap and idempotent, which is why it is part of the run rather
than a setup step someone can forget. The same command works unchanged as a CI
gate: it exits non-zero when anything reaches `--fail-on`.

```
policy: .../policy-repo/severities.json (3 override(s))
  QUA-004   Warning   -> off       (1 query, 0 shape node(s))
  STR-002   Violation -> Info      (1 query, 1 shape node(s))
  STR-003   Warning   -> Violation (1 query, 1 shape node(s))
assembled: 43 query file(s), 6 shape file(s), 61 registry entries
verified: every override is on disk, and the config agrees

Findings: 12 total (2 Violation, 4 Warning, 6 Info)
gate: FAIL (suite exit 1, --fail-on Violation)
```

43 query files, not 44: `QUA-004`'s is the one left out.

### One warning to expect and ignore

```
WARNING: --sparql replaced the suite's own query tree: 41 project check(s)
ran and 42 built-in check(s) did not. Pass --sparql @builtin as well to run
both.
```

That warning is right in general and wrong here, and **its advice would undo
the policy** — see the last row but two of the table below. The suite cannot
tell that this "project" tree is its own tree with three edits. Expect it; do
not act on it.

---

## How the results were read

| Check | Shipped | With the policy | `sources` |
|---|---|---|---|
| `STR-002` | Violation | **Info** | `shacl+sparql` |
| `STR-003` | Warning | **Violation** | `shacl+sparql` |
| `QUA-004` | Warning | **absent** | — |
| `STR-007` | Violation | Violation | `sparql` |

Three things to read off it.

**`sources` still says `shacl+sparql`.** That is the evidence the policy reached
*both* formulations. If only the query had been rewritten, that cell would look
exactly the same while the severity came from the shape — which is the next
section.

**The Violation count did not move, and the Violations did.**

```
shipped:      2 Violation   STR-002, STR-007
with policy:  2 Violation   STR-003, STR-007
```

The gate fails both times, for a different reason. A count is not a summary;
only the named checks tell you whether the policy did what you asked.

**13 findings became 12**, and the one that left is the one switched off.

---

## The five ways this goes wrong

Each was measured by breaking the wiring one way at a time, against the
12-finding policy run. Ordered by how loud they are.

| What is wrong | What you see | Result |
|---|---|---|
| id the registry does not have (`STR-0003`) | `ERROR: STR-0003 is not a check in this registry -- did you mean STR-003?` | never runs |
| severity the suite does not have (`"Not a worry"`) | `ERROR: 'Not a worry' is not a severity. Use one of Violation, Warning, Info, or 'off'` | never runs |
| check in the registry that nothing here implements | assembler exits 1, naming it — probably one of the 11 CLI-only checks | never runs |
| `@builtin` left in `sparql` | nothing | **13** — severities hold, but `QUA-004` is **back at Warning**: `off` is undone, because the unmodified tree still has its query |
| policy applied to the registry only | nothing | **13 — the shipped result exactly**, 2/6/5, both overrides ignored |
| policy applied to the `.rq` files only | nothing | **12 — same total, same 2 Violations, different ones** |

The last two are the ones worth sitting with, because neither produces a
diagnostic of any kind.

**Registry only** is the approach the flag names invite, and it changes nothing
whatsoever.

**Queries only** is subtler and worse, because it looks like it worked. With
`STR-002.rq` rewritten to `Info` and the shipped shape left at `Violation`:

```
check      policy asked    reported
STR-002    Info            Violation
STR-003    Violation       Warning
```

**The shape wins, in both directions**, and `sources` still reads
`shacl+sparql`, so nothing anywhere reports a disagreement. Total findings,
Violation count and exit code are all identical to the correct run — 12, 2 and
1. Only the named severities differ, and only if you knew to look.

That is why `apply_severities.py` reads back what it wrote and refuses to
finish on a mismatch, and why `ontology-suite.yml` is checked against what was
assembled: a severity you cannot verify is worse than the shipped one, because
you will act on it.
