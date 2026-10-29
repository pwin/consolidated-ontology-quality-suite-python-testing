"""Assemble what Folder A's validation run needs from Folders B and C.

Two jobs, because the suite takes project-local checks two different ways and
only one of them is additive.

    uv run python examples/cross-folder-checks/folder-a-fleet-project/prepare_checks.py

JOB 1: ONE REGISTRY
-------------------
`--registry` takes one file and that file replaces the suite's, so Folder B's
and Folder C's declarations have to be merged with the suite's rather than
passed instead of them. Hand it a fragment alone and the fragment's checks
resolve while the suite's 61 do not: their findings still appear, because
queries and shapes are discovered from the filesystem rather than from the
registry, but each arrives with no title and no remediation, printed as
UNMAPPED.

Merged at run time rather than committed, so the suite's half is always the
installed suite's. A committed copy freezes at the version it was copied
from, silently.

JOB 2: ONE SHAPES DIRECTORY
---------------------------
This is where SHACL differs from SPARQL, and it is the whole reason Folder C
needs more wiring than Folder B:

    --sparql  repeats, and takes @builtin. Folder B is simply named
              alongside the suite\'s own tree and the two add up.

    --shapes  does neither. It takes ONE directory, with no @builtin, and
              that directory replaces the suite\'s shapes outright. It is
              also not recursive -- the loader globs *.ttl at the top level,
              so shapes in subdirectories are silently not loaded.

So there is no way to say "the suite\'s shapes and also Folder C\'s". The
directory has to be built, which is what assemble_shapes() does: the suite\'s
six shape files plus Folder C\'s, flat, into out/shapes/, every run.

The same three failure modes apply to both jobs, and the README measures
them: the folder absent, the folder present but empty, and the config naming
a path that no longer holds what was declared.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from ontology_suite import config

HERE = Path(__file__).resolve().parent
EXAMPLE = HERE.parent

# The references to the folders Folder A does not own. Relative to this file
# rather than to the working directory, so they hold from any cwd. They
# assume only that B and C sit beside A -- sibling checkouts, submodules, or
# directories a CI job cloned next to this one.
FOLDER_B = EXAMPLE / "folder-b-house-checks"
FOLDER_C = EXAMPLE / "folder-c-house-shapes"

FRAGMENTS = [FOLDER_B / "registry-fragment.json", FOLDER_C / "registry-fragment.json"]
QUERIES = FOLDER_B / "sparql"
SHAPES = FOLDER_C / "shapes"

# Generated, so both go under out/ and neither is committed. They do have to
# be somewhere a person can point a command at, because reproducing any
# FLT-00x finding by hand needs exactly these.
OUT = HERE / "out"
MERGED_REGISTRY = OUT / "merged-registry.json"
ASSEMBLED_SHAPES = OUT / "shapes"

CONFIG = HERE / "ontology-suite.yml"


def require(path: Path, what: str) -> None:
    if not path.exists():
        raise SystemExit(
            "{} is not where Folder A expects it.\n"
            "  looked for: {}\n"
            "If the house rules live elsewhere on this machine, change the "
            "path in {} and the matching entry in ontology-suite.yml "
            "together -- they are two halves of one reference, and a run "
            "with only one of them updated is the quiet failure the README "
            "measures.".format(what, path, Path(__file__).name))


def merge_registry() -> Path:
    """The installed suite\'s registry plus every house fragment."""
    merged = json.loads(Path(config.DEFAULT_REGISTRY_PATH).read_text(encoding="utf-8"))
    seen = {entry["id"] for entry in merged["checks"]}

    for fragment in FRAGMENTS:
        require(fragment, "A house registry fragment")
        local = json.loads(fragment.read_text(encoding="utf-8"))
        ids = {entry["id"] for entry in local["checks"]}

        # An id collision is silent and nasty: two entries with one id, and
        # whichever the lookup reaches decides the title and severity the
        # report shows. Catches B against C as well as either against the
        # suite, since `seen` grows as fragments are added.
        clash = seen & ids
        if clash:
            raise SystemExit(
                "{}: these ids are already taken: {}.\n"
                "House rules should carry a prefix of their own (FLT-, "
                "ACME-, ...) so a report can always say whose rule fired."
                .format(fragment, sorted(clash)))

        merged["checks"] = merged["checks"] + local["checks"]
        seen |= ids

    MERGED_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    MERGED_REGISTRY.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    return MERGED_REGISTRY


def assemble_shapes() -> Path:
    """The suite\'s shapes and Folder C\'s, flat, in one directory.

    Rebuilt rather than updated, so a shape deleted from Folder C disappears
    from the run instead of lingering in out/ as a check nobody owns.
    """
    require(SHAPES, "Folder C")
    house = sorted(SHAPES.glob("*.ttl"))
    if not house:
        raise SystemExit(
            "{} holds no .ttl shapes at its top level.\n"
            "The loader globs *.ttl and does not recurse, so shapes in "
            "subdirectories here would be declared and never loaded."
            .format(SHAPES))

    if ASSEMBLED_SHAPES.exists():
        shutil.rmtree(ASSEMBLED_SHAPES)
    ASSEMBLED_SHAPES.mkdir(parents=True)

    shipped = sorted(Path(config.DEFAULT_SHAPES_DIR).glob("*.ttl"))
    for path in shipped + house:
        destination = ASSEMBLED_SHAPES / path.name
        if destination.exists():
            raise SystemExit(
                "{} has the same filename as one of the suite\'s shape "
                "files. Flattened into one directory they would collide, and "
                "the copy that landed second would be the one that ran."
                .format(path))
        shutil.copy(path, destination)
    return ASSEMBLED_SHAPES


def check_config_agrees() -> None:
    """The config must run what this script just assembled.

    A stale path is the quiet one. The suite does not fail on a query root
    holding nothing, nor on a shapes directory that is not the one you built
    -- the checks simply stop firing. No error, no warning, a smaller number
    nobody has a baseline for.

    Checked here because this is the only place that holds both halves of
    every reference.
    """
    doc = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}

    roots = [str(root) for root in (doc.get("sparql") or [])]
    resolved = {(CONFIG.parent / root).resolve() for root in roots if root != "@builtin"}
    if QUERIES.resolve() not in resolved:
        raise SystemExit(
            "{} does not run the queries this script declares.\n"
            "  declared from: {}\n"
            "  config runs:   {}\n"
            "The registry would name house rules that never run."
            .format(CONFIG, QUERIES, sorted(str(p) for p in resolved) or "(nothing)"))
    if "@builtin" not in roots:
        raise SystemExit(
            "{} lists `sparql` without `@builtin`, so naming Folder B "
            "replaces the suite\'s own tree instead of adding to it."
            .format(CONFIG))

    shapes = doc.get("shapes")
    if not shapes or (CONFIG.parent / str(shapes)).resolve() != ASSEMBLED_SHAPES.resolve():
        raise SystemExit(
            "{} must point `shapes` at the assembled directory, not at "
            "Folder C itself.\n"
            "  assembled: {}\n"
            "  config:    {}\n"
            "--shapes replaces the suite\'s shapes rather than adding to "
            "them, so naming Folder C directly would run one shape where 22 "
            "should.".format(CONFIG, ASSEMBLED_SHAPES, shapes or "(unset)"))

    engine = str(doc.get("engine", ""))
    if engine not in ("both", "shacl", "native", "native+sparql"):
        raise SystemExit(
            "{} sets `engine: {}`, which never runs a SHACL shape, so Folder "
            "C\'s rules are declared and never evaluated. Use `both` to run "
            "shapes and queries together.".format(CONFIG, engine or "(unset)"))


if __name__ == "__main__":
    registry = merge_registry()
    shapes = assemble_shapes()
    check_config_agrees()

    total = len(json.loads(registry.read_text(encoding="utf-8"))["checks"])
    house = 0
    for fragment in FRAGMENTS:
        local = json.loads(fragment.read_text(encoding="utf-8"))
        count = len(local["checks"])
        house += count
        print("  {} check(s) from {}".format(count, fragment.parent.name))
        print("     owner:   {}".format(local.get("_owner", "unstated")))
        print("     version: {}".format(local.get("_version", "unstated")))
    print("wrote {}".format(registry))
    print("  {} from the installed suite, {} house, {} in total"
          .format(total - house, house, total))
    print("wrote {}".format(shapes))
    print("  {} shape file(s): the suite\'s and Folder C\'s"
          .format(len(list(shapes.glob("*.ttl")))))
