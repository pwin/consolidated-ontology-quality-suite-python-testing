# A review of the 38 competency tests, from having built one fixture each

Written after isolating every competency test into its own folder with its
own minimal data. Building them is what produced the observations below:
several only become visible when a test is the only thing in the room.

Everything here is evidence from the fixtures, not opinion about the model.

## 1. The tests cluster by *what you must have* to answer them

The numbering runs 1–38 in the order the questions were written down. What
the fixtures reveal is a different ordering: what inputs a question needs,
which decides who can ask it and when.

| Input needed | Tests | Answerable |
|---|---|---|
| **The ontology alone** | 8, 9, 10, 11 | as soon as the model exists |
| **The mappings alone** | 37 | before any model |
| **Mappings + the model** | 1, 5, 12, 14, 22, 32, 33 | before any data |
| **Two versions of the model** | 3, 7 | at a version bump |
| **Mappings + the new model** | 6 | at a version bump |
| **Mappings + a taxonomy** | 4 | before any data |
| **Output + the model** | 2, 13, 17, 18, 19, 20, 21, 30, 31 | after a run |
| **Mappings + source + output** | 15, 16 | after a run |
| **Two outputs** | 23, 24, 25, 26, 27, 28 | after two runs |
| **Mappings as a set** | 34, 35, 36 | before any data |
| **Output + a stored expectation** | 38 | after a run, if someone kept one |
| **Mappings + a shared model** | 29 | before any data |

Two things follow.

**Half the tests can be answered before a row of data exists.** Tests
1, 4, 5, 6, 12, 14, 22, 29, 32, 33, 34, 35, 36, 37 — fourteen of them — read
query text and declarations. On the evidence of CT-32, whose fixture is a
mapping wired to no CSV, the data-side equivalent is not merely later but
sometimes never: a mapping that has not run cannot be checked by anything
that waits for output.

**The expensive tests are few.** Only 15, 16, 23–28 and 38 need a pipeline
run, and 23–28 need two. A project that wants fast feedback can have 27 of 38
answers from artefacts it already has.

## 2. Command shape follows the input, not the number

The 26 single-CT folders use six shapes:

| Shape | Folders |
|---|---|
| `checks` | CT-08, 09, 10, 11 |
| `sketch` | CT-01, 05, 06, 14, 22 |
| `sketch` then `checks` | CT-12, 29, 32, 33, 37 |
| `data` | CT-02, 13, 17, 18, 19, 20, 21, 30, 31 |
| `consistency` | CT-03 |
| `pattern-consistency` | CT-04 |
| `version-diff` ×2 | CT-07 |

The remaining twelve are comparisons and share three scripts, one per
aggregate. That is the strongest argument for clustering the numbering:
tests that share a shape share their fixtures, their invocation and their
failure modes, and a reader who has understood one has understood the rest.

## 3. Where the tests overlap

Three checks answer more than one test:

| Check | Tests | Difference |
|---|---|---|
| `TQL-001` | CT-1, CT-5 | none in the check; CT-1 is one concept minted twice, CT-5 is a concept *shared across domains* minted twice. Same fixture shape, same finding |
| `QUA-009` | CT-10, CT-11 | real: absent preferred label versus two in one language. Same check, opposite conditions |
| `undeclared-term` | CT-3, CT-6 | the same defect from two vantage points — with the old version present (a rename, repairable) and without it (an undeclared class) |

And the overlap runs the other way too. Eight tests need more than one check
to answer them (CT-3, 4, 6, 9, 10, 13, 14, 22), so the competency questions
and the registry checks are not in correspondence at all: they are two
different cuts through the same material.

Two more overlaps only the isolated fixtures exposed:

- **CT-18 is reported twice.** Flattening a value onto the wrong node is
  `CMP-018` by the project's pattern rule *and* `CNF-003` by the property's
  declared domain.
- **CT-32's fault is caught by `CNF-003`** as soon as the sketch is read as
  data. The project check earns its place not by seeing something the
  registry cannot, but by seeing it in a stage that needs no data.

**CT-1 and CT-5 are the one pair I would merge.** Everything else that looks
like duplication turns out to differ in inputs, in timing, or in what the
finding lets you do next.

## 4. What the aggregate says about reporting

`AGGREGATE-all-fixtures` merges every fixture into one project: 29 ontology
files, 15 mappings, 9 output graphs. **142 findings — 19 Violation, 87
Warning, 36 Info.**

Three checks produce 99 of them:

| Check | N | Why |
|---|---|---|
| `CMP-012` | 56 | labels minted by a transformation — but merged with a model that *has* labels, it reports nearly every labelled term |
| `CNF-005` | 33 | classes declared and never populated: 29 ontology files against 9 output graphs |
| `STR-004` | 10 | classes with no superclass, which minimal fixtures have by design |

Every seeded defect is in there exactly once or twice.

That ratio is the finding, and it has three consequences.

**A first run against a real project is dominated by systemic conditions.**
The specific defects are single lines among hundreds. Reporting that groups
by competency question rather than by check id would put one `TQL-001` beside
one `CMP-030` instead of burying both under 56 of something else.

**Severity does not separate them.** 87 Warnings is not a work queue. What
separates the 99 from the rest is not severity but *kind*: three conditions
that are true of the project as a whole against eleven that are true of one
triple each.

**Some checks are sensitive to how they are invoked.** `CMP-012` is correct
in its own folder, where the ontology is declarations-only, and wrong in the
aggregate, where the model's labels are merged in. A check whose correctness
depends on what you merge will misfire the first time someone runs it
differently — which, on the evidence of the `--sparql` defect fixed in suite
0.18.0, is what happens.

## 5. What building the fixtures cost, and what that says

Four of the 26 folders carry an allowed finding that is *true* and not the
point, because several checks are in tension in a minimal model:

- a class needs a superclass or it is formally undefined (`STR-004`)
- give it `owl:Thing` and `owl:Thing` becomes a class nothing populates
  (`CNF-005`)
- a parent that exists to be specialised is never populated either
- an instance needs a label of its own or `QUA-004` reports the data
- a bilingual label cannot match an English local name (`STY-004`), and the
  same lexical form under two tags is `DAT-003`

None of these is wrong. Together they mean **a minimal, entirely clean
ontology is not writable** — "one fixture, one finding" is a target you
approach, not one you reach. That is worth knowing before anyone reads a
clean run as proof of anything.

## 6. Three suite defects the isolation exposed

All three were invisible in the shared worked example and obvious once a
fixture reported two findings instead of one.

1. **The namespace legend landed in the project's namespace** (fixed in
   0.20.0). `:isRepresentedBy` was written as a CURIE, and `:` means the
   tool's scratch namespace only when no query declares an empty prefix —
   which most do. Every project using a default namespace was told it used an
   undeclared property.
2. **An ontology's own default namespace was reported as undeclared** (fixed
   in 0.21.0). The prefix loader skipped `@prefix :` declarations, so the
   namespace IRI went missing with the prefix name. Six false findings in the
   suite's own worked example.
3. **`--sparql` silently replaced the built-in tree** (fixed upstream in
   0.18.0, found in this repo's gate config). Eight project checks ran, 42
   built-ins did not, and the gate reported a clean run.

Three defects of the same species: a tool's own vocabulary or invocation
being mistaken for the project's.

## 7. The numbering stays as it is

Decided: CT-1 to CT-38 keep their numbers. The clustering below is a lens for
reading and reporting the results, not a proposal to renumber.

That is the right call on the evidence, and the review would have been wrong
to push harder for the alternative. The `CT-n` ids are cited in
`COMPETENCY_COVERAGE.md`, in `COMPETENCY_CHECK_MATRIX.md`, in check
descriptions, in commit messages, in this folder's names and in the supplied
CSVs that define the tests in the first place. A renumbering makes every one
of those citations wrong, and nothing in the repo would catch it — the tests
would still pass, because they assert that a check fires, not that a number
means what it used to.

What the clustering is *for*, given the numbers stay:

- **Reporting.** §4 shows a first run burying eleven specific defects under
  99 findings from three systemic checks. Grouping a report by input — what
  the reader can act on now, with what they already have — separates those
  without touching an id.
- **Planning a rollout.** Groups B and C below need no data and answer 12 of
  38 questions, which is where a project with nothing set up should start.
- **Reading the set.** Tests that share a group share a fixture shape and an
  invocation, so understanding one is most of understanding the rest.

The grouping the evidence supports:

| Group | Now | What it means |
|---|---|---|
| **A — the model alone** | 8, 9, 10, 11 | documentation and structure |
| **B — the mappings alone** | 34, 35, 36, 37 | the set agreeing with itself |
| **C — mappings against the model** | 1, 5, 12, 14, 22, 29, 32, 33 | drift before data |
| **D — across versions** | 3, 6, 7 | what a change obliges |
| **E — against the vocabulary** | 4 | controlled terms |
| **F — the output against the model** | 2, 13, 17, 18, 19, 20, 21, 30, 31 | what the run produced |
| **G — the output against expectation** | 15, 16, 23–28, 38 | what changed, and what was promised |

Group F is the largest and the least urgent, because everything in it is also
the most expensive to reach. Groups B and C are the cheapest and catch the
most before anything is paid for — which is the argument for running them
first, whatever they are numbered.
