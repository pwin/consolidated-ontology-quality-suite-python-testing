"""Generate COMPETENCY_CHECK_MATRIX.md -- which checks to run for each
competency test, joined to the registry entry each check comes from.

    uv run python competency_tests/build_check_matrix.py

Merges three sources:

  * the five competency CSVs in this folder (the issue text),
  * competency.py's COVERAGE table (which check answers which test) and
    runspecs.py (the command that produces it),
  * results/merged-registry.json -- the shipped registry plus this repo's own
    CMP-* checks -- for each check's title, severity and category.

Reads results/findings.csv, if a run has left one, to fill in how many times
each check actually fired. Runs nothing itself, so it is cheap to regenerate;
run run_competency_checks.py first if the counts are stale.

Commands are footnotes rather than a column: several competency tests share
one command, and repeating a forty-word invocation on every row buries the
matrix it is meant to serve.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import competency
import runspecs

# The supplied CSVs space many words with U+00A0 NO-BREAK SPACE rather than
# U+0020. An editor or tool that strips those instead of converting them
# silently welds words together -- "ontology.Identify" for "ontology. Identify"
# -- and the text still looks plausible enough to publish. This exact thing
# happened once here, to four of the five files, and was caught only because
# the generated table read wrongly.
#
# The punctuation form is the detectable signature: run-together lowercase
# ("eachmagnitude") is indistinguishable from prose by any rule worth having,
# but a comma or full stop welded to a following letter is not. Reported
# rather than repaired -- the CSVs are the authoritative definition of these
# tests, and the fix is to restore them, not to paper over them downstream.
LOST_SPACE = re.compile(r"(?<=[a-z])[.,](?=[A-Za-z])")

HERE = Path(__file__).resolve().parent
DOCUMENT = HERE / "COMPETENCY_CHECK_MATRIX.md"
REGISTRY_PATH = HERE / "results" / "merged-registry.json"
FINDINGS_PATH = HERE / "results" / "findings.csv"

# Repeating the full paths in every footnote makes them hard to scan, so the
# short forms use shell variables the document defines up front. The commands
# stay runnable: they are the same strings with the long prefixes substituted.
ABBREVIATIONS = (
    (runspecs.OUTPUT, "$O"),
    (runspecs.REGISTRY, "$R"),
    ("competency_tests/checks/sparql", "$C"),
    (runspecs.MODEL, "$M"),
)


def load_registry() -> Dict[str, dict]:
    if not REGISTRY_PATH.exists():
        raise SystemExit(
            "{} is missing. run_competency_checks.py writes it -- run that first."
            .format(REGISTRY_PATH))
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {check["id"]: check for check in data["checks"]}


def load_observed() -> Dict[tuple, int]:
    """{(run, check_id): count} from the last recorded run, if there is one."""
    if not FINDINGS_PATH.exists():
        return {}
    counts: Counter = Counter()
    with FINDINGS_PATH.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            counts[(row["run"], row["check_id"])] += 1
    return dict(counts)


def _cell(text: str) -> str:
    """Markdown table cells hold no raw newline and no unescaped pipe."""
    return " ".join(str(text).split()).replace("|", "\\|")


def shorten(command: str) -> str:
    one_line = " ".join(command.replace("\\\n", " ").split())
    for full, short in ABBREVIATIONS:
        one_line = one_line.replace(full, short)
    return one_line


def check_facts(check_id: str, registry: Dict[str, dict]) -> Tuple[str, str, str]:
    """(title, severity, source) for a check id, registry-backed or not."""
    entry = registry.get(check_id)
    if entry:
        return (entry["title"], entry["default_severity"],
                "project-local" if check_id.startswith("CMP-") else "registry")
    if check_id in runspecs.NON_REGISTRY_EVIDENCE:
        _run, severity, description = runspecs.NON_REGISTRY_EVIDENCE[check_id]
        source = "harness" if check_id.startswith(("MAP-", "RVW-")) else "suite module"
        # These have no registry title, only prose. The first sentence is the
        # title; the rest would make the row unreadable and is in the module.
        return description.split(". ")[0].rstrip("."), severity, source
    return "(unknown)", "", ""


class Footnotes:
    """Numbers each distinct command once, in order of first appearance."""

    def __init__(self) -> None:
        self.order: List[Tuple[str, str, str]] = []  # (run_key, label, command)
        self._index: Dict[Tuple[str, str], int] = {}

    def ref(self, run_key: str, check_id: str) -> str:
        command, _note = runspecs.command_for(run_key, check_id)
        variant = "project" if (check_id.startswith("CMP-")
                                and runspecs.RUNS[run_key].project_command) else "plain"
        key = (run_key, variant)
        if key not in self._index:
            label = run_key if variant == "plain" else "{} (CMP-*)".format(run_key)
            self.order.append((run_key, label, command))
            self._index[key] = len(self.order)
        return "[^{}]".format(self._index[key])


def render(registry: Dict[str, dict], observed: Dict[tuple, int]) -> str:
    definitions = competency.load_definitions()
    footnotes = Footnotes()
    lines: List[str] = []
    add = lines.append

    pairs = [(cover, entry) for cover in competency.COVERAGE for entry in cover.evidence]

    add("# Competency test -> check matrix")
    add("")
    add("Generated by `build_check_matrix.py`. One row per (competency test, check) pair: which "
        "check answers each of the 28 competency tests, what that check is according to the "
        "registry, and -- as a footnote on each row -- the command that produces it.")
    add("")
    add("- **{} competency tests**, answered by **{} distinct checks** across **{} rows**"
        .format(len(competency.COVERAGE), len({e[1] for _c, e in pairs}), len(pairs)))
    add("- Titles, severities and categories come from `results/merged-registry.json` -- the "
        "suite's shipped registry plus this repo's own `CMP-*` entries")
    add("- *Fired* is from the last recorded run (`results/findings.csv`)")
    add("")
    damaged = sorted(n for n, d in definitions.items()
                     if LOST_SPACE.search(d.issue) or LOST_SPACE.search(d.summary))
    if damaged:
        add("> **The source CSVs look damaged.** {} of them {} punctuation welded to the next word "
            "-- {} -- which is what stripping their U+00A0 spaces rather than converting them "
            "does. The text below is reproduced verbatim, so it will read wrongly until the files "
            "are restored: `git checkout -- competency_tests/*.csv`. This note disappears once "
            "they are."
            .format(len(damaged), "has" if len(damaged) == 1 else "have",
                    ", ".join("CT-{}".format(n) for n in damaged)))
        add("")
    add("Commands run from the repo root. Set these once and every footnote is copy-pasteable as "
        "written:")
    add("")
    add("```bash")
    add("M={}".format(runspecs.MODEL))
    add("O={}".format(runspecs.OUTPUT))
    add("R={}".format(runspecs.REGISTRY))
    add("C=competency_tests/checks/sparql")
    add("```")
    add("")
    add("| Source | Meaning |")
    add("|---|---|")
    add("| `registry` | a check shipped in the suite's own registry |")
    add("| `project-local` | a `CMP-*` check in `checks/sparql/`, added here through the suite's "
        "documented registry + `--sparql` extension mechanism, without forking it |")
    add("| `suite module` | structured output of a suite module that has no registry id -- "
        "`pattern-consistency`, `consistency`, `version-diff` |")
    add("| `harness` | `review_aids.py` / `mapping_integrity.py` in this folder, for the questions "
        "that compare two artefacts and so cannot be a check over one graph |")
    add("")

    add("## The matrix")
    add("")
    add("| CT | Competency issue | Check | Title | Severity | Source | Fired | Run |")
    add("|---|---|---|---|---|---|---|---|")
    for cover, entry in pairs:
        run_key, check_id = entry[0], entry[1]
        title, severity, source = check_facts(check_id, registry)
        count = observed.get((run_key, check_id))
        add("| CT-{} | {} | `{}` | {} | {} | {} | {} | `{}`{} |".format(
            cover.number,
            _cell(definitions[cover.number].issue),
            check_id,
            _cell(title),
            severity or "--",
            source or "--",
            "x{}".format(count) if count else "--",
            run_key,
            footnotes.ref(run_key, check_id)))
    add("")

    add("## By competency test")
    add("")
    add("The same thing read the other way: everything one test needs, in one place.")
    add("")
    by_test: Dict[int, List[tuple]] = defaultdict(list)
    for cover, entry in pairs:
        by_test[cover.number].append(entry)
    for cover in competency.COVERAGE:
        definition = definitions[cover.number]
        checks = ", ".join("`{}`".format(entry[1]) for entry in by_test[cover.number])
        runs = sorted({entry[0] for entry in by_test[cover.number]})
        add("**CT-{} -- {}**  ".format(cover.number, definition.issue))
        add("{}  ".format(definition.summary))
        add("*Checks:* {} &middot; *Run:* {}".format(
            checks, ", ".join("`{}`".format(r) for r in runs)))
        add("")
        for run_key in runs:
            spec = runspecs.RUNS[run_key]
            check_ids = [e[1] for e in by_test[cover.number] if e[0] == run_key]
            command, note = runspecs.command_for(run_key, check_ids[0])
            if command:
                add("```bash")
                add(command)
                add("```")
            else:
                add("> {}".format(note or "No single-command form."))
                add(">")
                add("> ```bash")
                add("> {}".format(runspecs.HARNESS))
                add("> ```")
            add("")

    add("## Registry checks no competency test pins")
    add("")
    used = {e[1] for _c, e in pairs}
    unused = sorted(set(registry) - used)
    add("The 28 tests pin {} of the registry's {} checks as evidence. The other {} still run in the "
        "stages above -- being outside the evidence list is not the same as being irrelevant. "
        "`DAT-001` is the clearest case: an invalid lexical form for a declared datatype is "
        "squarely CT-22's subject, and this fixture set happens to seed the datatype-loss form of "
        "that defect rather than the ill-formed-literal one. Listed so the gap between \"the "
        "competency set passes\" and \"the suite found nothing\" stays visible."
        .format(len(used & set(registry)), len(registry), len(unused)))
    add("")
    add("| Check | Title | Severity | Category |")
    add("|---|---|---|---|")
    for check_id in unused:
        entry = registry[check_id]
        add("| `{}` | {} | {} | {} |".format(
            check_id, _cell(entry["title"]), entry["default_severity"], entry["category"]))
    add("")
    extension_only = sorted(set(competency.EXTENSION_ONLY_CHECKS) & set(unused))
    if extension_only:
        add("{} of those -- {} -- {} declared in the registry but implemented only in the VS Code "
            "extension, so no CLI command can produce {}. `fixtures/vsix/` holds a dataset for "
            "checking {} by hand; see COMPETENCY_COVERAGE.md."
            .format(len(extension_only), ", ".join("`{}`".format(c) for c in extension_only),
                    "is" if len(extension_only) == 1 else "are",
                    "it" if len(extension_only) == 1 else "them",
                    "it" if len(extension_only) == 1 else "them"))
        add("")

    add("## Commands")
    add("")
    for number, (run_key, label, command) in enumerate(footnotes.order, start=1):
        spec = runspecs.RUNS[run_key]
        if command:
            add("[^{}]: **{}** -- {}. `{}`".format(number, label, spec.title, shorten(command)))
        else:
            add("[^{}]: **{}** -- {}. {} `{}`".format(
                number, label, spec.title, spec.note, runspecs.HARNESS))
        add("")
    return "\n".join(lines) + "\n"


def main() -> int:
    registry = load_registry()
    observed = load_observed()
    DOCUMENT.write_text(render(registry, observed), encoding="utf-8")
    pairs = sum(len(cover.evidence) for cover in competency.COVERAGE)
    print("Wrote {}".format(DOCUMENT))
    print("{} competency tests, {} rows, registry of {} checks{}".format(
        len(competency.COVERAGE), pairs, len(registry),
        "" if observed else " (no results/findings.csv -- Fired column left empty)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
