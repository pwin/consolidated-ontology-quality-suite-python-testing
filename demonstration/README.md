# Demonstration: the VS Code extension and the quality suite, across one day's work

Two files, for two jobs:

- **[TASKS.md](TASKS.md)** — everything that has to be done before this can be
  rehearsed, as a checklist. Nothing in this folder is built yet; that list is
  what "built" means.
- **[SCRIPT.md](SCRIPT.md)** — the run of the demonstration itself: each beat,
  what to do on screen, and bullets to speak from.

## The argument

Four acts, following the order of real work: write an ontology, write the
transformations that populate it, review those transformations as a *set*, then
add the checks your project needs that no tool ships with.

It is one claim, made four times:

> **The cheap check belongs in the editor and the expensive one belongs in the
> pipeline. Neither tool can do the other's job, and both are extensible by
> you.**

That is not a slogan — both halves are asserted by tests in the two
repositories, so the demo can state them as fact:

| | Only the extension can produce | Only the CLI can produce |
|---|---|---|
| Count | 3 | 11 |
| Which | `VOC-001`, `REA-005`, `REA-006` | `REA-010`/`011`/`012`, `REA-020`/`021`/`022`, `CNF-001`/`002`/`005`, `TQL-004`/`005` |
| Why | closed-world questions SHACL's semantics cannot ask | a real DL reasoner; profile membership as findings; a data graph judged against a *separate* ontology; queries over the BIND-facts graph |
| Pinned by | `test_extension_only_checks_are_not_reported_by_the_cli` (this repo) | `CLI_ONLY` in `src/checks/registryCoverage.test.ts` (extension repo) |

Note `TQL-001`/`002`/`003` are in *both*: the extension reviews a query folder
for them in seconds. `TQL-004`/`005` are not, because they are asked of the
suite's BIND-facts graph, which the extension does not build.

The two lists partition the registry exactly. Counted from extension 0.16.3's
bundled `registry.json`: of its **61** checks the extension runs **50**
in-process, and the 11 it does not are precisely the CLI-only list above —
**50 + 11 = 61**, nothing unaccounted for. Of those 50, 44 are SPARQL queries
and 21 are *also* written as SHACL shapes across 6 shape files, which is the
dual formulation Act 4's hinge depends on.

## Shape and timing

| Act | Subject | Minutes | The hinge |
|---|---|---|---|
| 1 | Writing an ontology | 12 | `VOC-001` in the editor; `REA-021` only from the CLI |
| 2 | Creating a set of TARQL transformations | 12 | two valid queries whose IRIs never join |
| 3 | Reviewing the triplification patterns of the set | 12 | questions no single file can answer |
| 4 | Adding checks beyond the standard ones | 10 | the same house rule, in the editor and in CI |

Plus two minutes to open and two to close: **50 minutes**, and each act stands
alone if it has to be cut to fifteen.

## Audience

People who will write or review ontologies and transformations — not people
deciding whether to buy anything. Every beat therefore ends with what you *do*
about the finding, never with a dashboard.
