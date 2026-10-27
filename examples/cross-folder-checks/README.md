# Checks in other folders

Folder A holds development work. Folders B and C hold extra checks that are
not part of the suite and are owned by someone else — a standards group,
another team, a repository pulled in as a submodule. Folder A has to
reference them and run them alongside the suite's own checks.

B and C are separate folders because the two kinds of check are referenced
differently, and that difference is most of what this example is for:

```
cross-folder-checks/
├── folder-a-fleet-project/      <- the development work under test
│   ├── ontology/fleet-v1.ttl        a small fleet register model
│   ├── data/fleet.ttl               eight records
│   ├── ontology-suite.yml           names B, C and the suite's own tree
│   ├── prepare_checks.py            assembles one registry and one shapes dir
│   └── validate.sh                  the whole run, two steps
├── folder-b-house-checks/       <- house rules written as SPARQL CONSTRUCTs
│   ├── registry-fragment.json       three checks declared
│   └── sparql/                      three .rq queries
└── folder-c-house-shapes/       <- house rules written as SHACL shapes
    ├── registry-fragment.json       one check declared
    └── shapes/fleet-house.ttl       one NodeShape
```

Everything is invented; the namespace is `example.org`. Every number below
came from running the commands shown.

---

## What was tested

Four house rules, each encoding a local convention no shipped check could
know:

| Check | In | Severity | Rule |
|---|---|---|---|
| `FLT-001` | B, SPARQL | Violation | every vehicle carries an asset tag matching `FLT-NNNNNN` |
| `FLT-002` | B, SPARQL | Warning | no retired vehicle has a work order still open |
| `FLT-003` | B, SPARQL | Info | every in-service vehicle is assigned to a depot |
| `FLT-004` | C, SHACL | Violation | every work order concerns exactly one vehicle |

`FLT-004` is a shape rather than a query because cardinality is what SHACL
says natively: one `sh:path`, `sh:minCount`, `sh:maxCount`, against a target
class.

And, just as much: **that the suite's own checks still run.** The commonest
way to get this wrong leaves you running only the house rules.

[`data/fleet.ttl`](folder-a-fleet-project/data/fleet.ttl) is written so each
rule fires on exactly one record and every other record is clean against it —
so a finding names the record it is about, and a rule that stops working
shows up as a missing finding rather than as a smaller total. One record,
`:van-3`, carries a fault **only the suite** catches: it uses `:mileage`,
which the model never declares. No house rule would find that, and no suite
check knows what an asset tag should look like.

---

## How it was set up

### Folders B and C each declare and implement their own checks

A `registry-fragment.json` holding only that folder's entries — not a copy of
the suite's registry — supplies each check's title, severity and remediation
text. The `.rq` files and the shape decide what fires.

### Folder A assembles, because only one of the two flags is additive

This is the difference between B and C, and it is the whole reason C needs
more wiring:

| | `--sparql` (Folder B) | `--shapes` (Folder C) |
|---|---|---|
| Repeatable? | yes | **no** — one directory |
| `@builtin`? | yes | **none** |
| Given at all | adds to the suite's tree | **replaces** the suite's shapes |
| Recursive? | yes (`rglob`) | **no** — top-level `*.ttl` only |

So Folder B is simply *named* alongside the suite's tree. For Folder C there
is no way to say "the suite's shapes and also these", so the directory has to
be **built**. [`prepare_checks.py`](folder-a-fleet-project/prepare_checks.py)
does both assembly jobs every run:

1. **One registry** — the installed suite's 61 entries plus B's three and C's
   one, written to `out/merged-registry.json`. `--registry` does not repeat
   either, and the file it is given replaces the suite's.
2. **One shapes directory** — the suite's six shape files plus Folder C's,
   flat, in `out/shapes/`.

Both are assembled at run time rather than committed, so the suite's half is
always the installed suite's. Commit a combined copy and it freezes at the
version it was copied from, silently.

### Folder A's config names all three

```yaml
sparql:
  - ../folder-b-house-checks/sparql
  - "@builtin"
registry: out/merged-registry.json     # assembled, not Folder B's fragment
shapes: out/shapes                     # assembled, not Folder C's shapes/
engine: both                           # `sparql` would never run a shape
```

Paths resolve against the config file, so the relative references hold from
any working directory. `@builtin` is passed through unresolved: it means the
suite's own tree wherever this install put it.

### Two conventions inside the shape itself

Both are in [`fleet-house.ttl`](folder-c-house-shapes/shapes/fleet-house.ttl),
and both were measured rather than assumed:

- **The shape node's local name is the check id.** That is how a result is
  tied back to its registry entry. Renaming the node to
  `oq:WorkOrderCardinalityShape` still fires the finding — as `UNMAPPED`,
  Violation, no title, no remediation.
- **`sh:severity` goes on the shape node and must agree with the registry.**
  The shape's severity wins. Moved to the nested `sh:property` node as
  `sh:Info`, the finding came back Info although the registry declares
  `FLT-004` a Violation — and a gate at `--fail-on Violation` then passes.
  With no severity anywhere it came back Violation, the SHACL default.
  Nothing checks that shape and registry agree.

---

## How it was run

```bash
bash examples/cross-folder-checks/folder-a-fleet-project/validate.sh
```

Assemble, then gate. The assembly must come first, since the config points
`--registry` and `--shapes` at what it writes; it is cheap and idempotent,
which is why it is part of the run rather than a setup step someone can
forget. The same command works unchanged as a CI gate: it exits non-zero when
anything reaches `--fail-on`.

```
  3 check(s) from folder-b-house-checks   (version 2.1.0)
  1 check(s) from folder-c-house-shapes   (version 1.3.0)
  61 from the installed suite, 4 house, 65 in total
  7 shape file(s): the suite's and Folder C's

Findings: 11 total (4 Violation, 3 Warning, 4 Info)
gate: FAIL (suite exit 1, --fail-on Violation)
```

---

## How the results were read

| From | Check | `sources` | Where | Reading |
|---|---|---|---|---|
| B | `FLT-001` | `sparql` | `:van-2` | registration number in the asset-tag field |
| B | `FLT-002` | `sparql` | `:wo-7` | open work order against a retired vehicle |
| B | `FLT-003` | `sparql` | `:truck-2` | in service, no depot |
| C | `FLT-004` | `shacl` | `:wo-9` | one work order against two vehicles |
| suite | `STR-002` | `shacl+sparql` | `:van-3` | `:mileage` used and never declared |
| suite | `STR-007`, `CNF-002`, `QUA-004` | `sparql`, `data` | `:mileage` | three more views of that one fault |
| suite | `CNF-005` ×3 | `data` | the model | classes only ever used through their subclasses — expected |

**Each house rule fired once, on the record it was written for.** That is the
assertion, not the total: a count can stay the same while a rule stops
working, but a named record cannot.

**The report quoted B's and C's own words.** The remediation text under
`FLT-001` and `FLT-004` is the text in their fragments, which is how you can
tell the registry merge worked rather than merely not crashing.

**`sources` says which arm found what** — and it is the only thing that does.
See the last row of the table below.

---

## The five ways the reference goes wrong

Each was measured by breaking the wiring one way at a time, against the
11-finding baseline. Ordered by how loud they are.

| What is wrong | What you see | Result |
|---|---|---|
| Folder B or C absent | assembly exits 1, naming the path it looked in | run never starts |
| `sparql` without `@builtin` | `WARNING: ... 3 project check(s) ran and 42 built-in check(s) did not` | **9** — `STR-007` and `QUA-004` gone |
| `--registry` given one fragment, unmerged | report looks normal; findings print as `UNMAPPED`, no title, no advice | **11**, 4 of them unusable |
| `engine: sparql` with Folder C wired | nothing at all | **10** — `FLT-004` silently never evaluated |
| `--shapes` points at Folder C itself | nothing at all | **11 — the same ids, exactly** |

That last row is the one worth sitting with. Pointing `--shapes` at Folder C
drops the suite's own 21 shapes, and the finding ids do not change at all,
because every check those shapes implement also has a `.rq` twin that still
runs. The only trace anywhere in the output is one cell:

```
check      correct wiring    Folder C alone
STR-002    shacl+sparql      sparql
```

A report with identical ids, identical counts and identical severities, where
half the cross-validation has quietly stopped. Which is why
`prepare_checks.py` reads `ontology-suite.yml` and refuses to run if the
config does not name what it just assembled: it is the only place that holds
both halves of every reference.

Two of those broken runs also show why a total is not a summary — **9 and 10
findings, neither missing the same thing.** What distinguishes them is which
named records appear, which is what the example data was built to make
legible.
