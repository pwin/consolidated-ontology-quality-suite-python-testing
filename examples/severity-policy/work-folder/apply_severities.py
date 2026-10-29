#!/usr/bin/env python3
"""Apply a severity policy held in another repo to the suite's own checks.

The thing worth knowing before reading any of this: **the registry's
``default_severity`` does not decide what severity a finding comes back at.**
It is reporting metadata. Every check carries its own severity literally --
``sh:resultSeverity sh:Violation`` in the ``.rq``, ``sh:severity sh:Violation``
on the shape -- and ``merge.py`` reads the severity off the results graph the
check produced. ``cli._exit_code`` then gates on those row severities, so
``--fail-on`` follows the check, not the registry.

Measured, on suite 0.24.3: patching ``default_severity`` to ``Info`` for
STR-002 and passing that file as ``--registry`` changed nothing at all. Same
15 findings, same ``2 Violation``, STR-002 still ``Violation``, still exit 1.
A policy applied only to the registry is a policy that does nothing, and
nothing warns you.

So this script rewrites the checks themselves, into a copy, and keeps the
registry in step so the reports do not contradict the findings:

1. copy the suite's ``sparql/`` and ``shapes/`` trees into ``out/``
2. rewrite ``sh:resultSeverity`` in each overridden check's ``.rq``
3. rewrite ``sh:severity`` on each overridden check's shape node(s)
4. rewrite ``default_severity`` in a copied registry
5. refuse to run if any of that did not take, or if the config would undo it

Run from this directory, or with --work pointing at it.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

VALID = ("Violation", "Warning", "Info")
OFF = "off"


def fail(message: str) -> None:
    print("ERROR: " + message, file=sys.stderr)
    sys.exit(1)


def suite_resources() -> Path:
    """The installed suite's resources directory, wherever this install put it.

    Located through the package rather than a path in the config, so the
    assembled copy is always *this* install's checks. A committed combined
    copy would freeze at the version it was copied from, silently.
    """
    try:
        import importlib.resources as ir

        root = Path(str(ir.files("ontology_suite"))) / "resources"
    except Exception as exc:  # pragma: no cover - environment problem
        fail("cannot import ontology_suite to find its checks: {}".format(exc))
    if not (root / "registry.json").is_file():
        fail("no registry.json under {} -- is the suite installed?".format(root))
    return root


def load_policy(path: Path) -> dict:
    """Read the policy repo's JSON into {check_id: severity}.

    Accepts the list-of-single-key-objects shape -- ``[{"STR-002": "Info"},
    ...]`` -- and a plain object, because both are natural to write and the
    difference is not worth an argument.
    """
    if not path.is_file():
        fail("no policy file at {}".format(path))
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail("{} is not valid JSON: {}".format(path, exc))

    policy: dict = {}
    if isinstance(raw, dict):
        items = list(raw.items())
    elif isinstance(raw, list):
        items = []
        for entry in raw:
            if not isinstance(entry, dict):
                fail("policy entries must be objects, found {!r}".format(entry))
            items.extend(entry.items())
    else:
        fail("policy must be a list or an object, found {}".format(type(raw).__name__))

    for check_id, severity in items:
        if check_id in policy and policy[check_id] != severity:
            fail(
                "{} is listed twice, as {} and as {} -- which one wins is not "
                "something this script will guess".format(
                    check_id, policy[check_id], severity
                )
            )
        policy[check_id] = severity
    if not policy:
        fail("{} declares no overrides".format(path))
    return policy


def validate_policy(policy: dict, registry_ids: set) -> None:
    """Reject a policy before it is applied, naming every problem at once.

    Both failure modes here are silent otherwise. A severity the suite does
    not have cannot be written into a check. An id the registry does not have
    matches no check, so the override is simply never applied -- and a typo
    like ``STR-0003`` for ``STR-003`` looks entirely plausible in a diff.
    """
    problems = []
    for check_id, severity in sorted(policy.items()):
        if check_id not in registry_ids:
            near = sorted(
                other
                for other in registry_ids
                if other.replace("-", "").replace("0", "")
                == check_id.replace("-", "").replace("0", "")
            )
            hint = " -- did you mean {}?".format(", ".join(near)) if near else ""
            problems.append(
                "{} is not a check in this registry{}".format(check_id, hint)
            )
        if severity not in VALID and severity != OFF:
            problems.append(
                "{}: {!r} is not a severity. Use one of {}, or {!r} to stop the "
                "check running at all".format(
                    check_id, severity, ", ".join(VALID), OFF
                )
            )
    if problems:
        for problem in problems:
            print("ERROR: " + problem, file=sys.stderr)
        sys.exit(1)


def shape_blocks(text: str) -> list:
    """Split a shapes file into (node_name, start, end) for each top-level node.

    Text ranges rather than an rdflib round-trip: these files carry SPARQL in
    triple-quoted literals and hand-laid comments, and re-serialising would
    rewrite the whole file to change one object.
    """
    starts = [
        (m.start(), m.group(1))
        for m in re.finditer(r"(?m)^oq:([A-Za-z0-9_-]+)", text)
    ]
    blocks = []
    for index, (offset, name) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(text)
        blocks.append((name, offset, end))
    return blocks


def blocks_for_check(text: str, check_id: str) -> list:
    """Every shape block belonging to a check.

    A block binds to a check by its node's local name, or by an explicit
    ``oq:checkId "ID"``. Both are needed: STY-002 is written as two nodes,
    ``oq:STY-002-data`` and ``oq:STY-002-obj``, and neither local name is the
    check id -- so matching on the name alone would miss both.
    """
    found = []
    for name, start, end in shape_blocks(text):
        body = text[start:end]
        if name == check_id or re.search(
            r'oq:checkId\s+"' + re.escape(check_id) + r'"', body
        ):
            found.append((start, end))
    return found


def apply_to_sparql(tree: Path, check_id: str, severity: str) -> int:
    """Rewrite (or delete) the .rq files implementing one check."""
    files = sorted(tree.rglob(check_id + ".rq"))
    for path in files:
        if severity == OFF:
            path.unlink()
            continue
        text = path.read_text(encoding="utf-8")
        patched = re.sub(
            r"sh:resultSeverity\s+sh:(Violation|Warning|Info)",
            "sh:resultSeverity sh:" + severity,
            text,
        )
        if patched == text and "sh:resultSeverity" not in text:
            fail(
                "{} emits no sh:resultSeverity, so its severity cannot be set "
                "here".format(path)
            )
        path.write_text(patched, encoding="utf-8")
    return len(files)


def apply_to_shapes(tree: Path, check_id: str, severity: str) -> int:
    """Rewrite (or remove) the shape nodes implementing one check.

    This is the half that is easy to leave out, and leaving it out silently
    discards the whole policy for any dual-formulated check. Measured on
    0.24.3, with the `.rq` rewritten and the shapes left shipped: STR-002 came
    back Violation (policy said Info) and STR-003 came back Warning (policy
    said Violation). **The shape wins, both directions.** And `sources` still
    reads `shacl+sparql`, so nothing reports a disagreement -- the run looks
    exactly as authoritative as a correct one.
    """
    touched = 0
    for path in sorted(tree.glob("*.ttl")):
        text = path.read_text(encoding="utf-8")
        blocks = blocks_for_check(text, check_id)
        if not blocks:
            continue
        # Back to front, so each edit leaves earlier offsets valid.
        for start, end in reversed(blocks):
            body = text[start:end]
            if severity == OFF:
                new_body = ""
            else:
                new_body, count = re.subn(
                    r"sh:severity\s+sh:(Violation|Warning|Info)",
                    "sh:severity sh:" + severity,
                    body,
                )
                if count == 0:
                    fail(
                        "the {} shape in {} declares no sh:severity; with none "
                        "declared SHACL reports Violation, so the policy could "
                        "not be applied".format(check_id, path.name)
                    )
            text = text[:start] + new_body + text[end:]
            touched += 1
        path.write_text(text, encoding="utf-8")
    return touched


def verify(out_sparql: Path, out_shapes: Path, policy: dict) -> None:
    """Read back what was written and confirm the policy is what is on disk.

    The whole point of the exercise is a severity you can trust, so the last
    step is to check rather than assume -- a regex that matched nothing would
    otherwise leave the shipped severity in place and report success.
    """
    for check_id, severity in sorted(policy.items()):
        rq = sorted(out_sparql.rglob(check_id + ".rq"))
        shapes = [
            (path, blocks_for_check(path.read_text(encoding="utf-8"), check_id))
            for path in sorted(out_shapes.glob("*.ttl"))
        ]
        shapes = [(path, blocks) for path, blocks in shapes if blocks]

        if severity == OFF:
            if rq:
                fail("{} was switched off but {} is still there".format(check_id, rq[0]))
            if shapes:
                fail(
                    "{} was switched off but a shape for it remains in {}".format(
                        check_id, shapes[0][0].name
                    )
                )
            continue

        for path in rq:
            text = path.read_text(encoding="utf-8")
            wrong = set(re.findall(r"sh:resultSeverity\s+sh:(\w+)", text)) - {severity}
            if wrong:
                fail(
                    "{} still emits {} after the rewrite".format(
                        path.name, ", ".join(sorted(wrong))
                    )
                )
        for path, blocks in shapes:
            text = path.read_text(encoding="utf-8")
            for start, end in blocks:
                wrong = set(
                    re.findall(r"sh:severity\s+sh:(\w+)", text[start:end])
                ) - {severity}
                if wrong:
                    fail(
                        "the {} shape in {} still declares {}".format(
                            check_id, path.name, ", ".join(sorted(wrong))
                        )
                    )


def check_config_agrees(config_path: Path, policy: dict) -> None:
    """Refuse to leave a config that would quietly undo the rewrite.

    Three ways to wire this wrongly, all silent:

    * ``@builtin`` left in ``sparql`` -- the suite's unmodified tree runs
      *alongside* the rewritten copy, so each overridden check is evaluated
      twice at two different severities and the row you keep is whichever the
      stage join kept.
    * ``shapes`` left unset or pointing at the suite's own directory -- the
      SHACL arm then reports shipped severities, and measured, those are the
      ones that reach the report: the policy is discarded for all 21
      dual-formulated checks with nothing said.
    * an engine that runs only one formulation, so only half the policy is
      ever consulted.
    """
    if not config_path.is_file():
        fail("no ontology-suite.yml at {}".format(config_path))
    try:
        import yaml
    except ImportError:  # pragma: no cover - environment problem
        fail("pyyaml is needed to read ontology-suite.yml")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    # Parsed, not grepped: the first version of this tripped over the word
    # "@builtin" in the config's own explanatory comment.
    sparql = config.get("sparql") or []
    if isinstance(sparql, str):
        sparql = [sparql]
    if "@builtin" in sparql:
        fail(
            "ontology-suite.yml still lists @builtin under sparql. The "
            "rewritten copy in out/sparql is already a full copy of the "
            "suite's tree, so @builtin would run the unmodified checks "
            "as well and your severities would be decided by whichever arm "
            "the stage join kept. Remove it."
        )
    if "out/sparql" not in sparql:
        fail(
            "ontology-suite.yml does not point sparql at out/sparql "
            "(found {!r})".format(sparql)
        )
    if config.get("shapes") != "out/shapes":
        fail(
            "ontology-suite.yml does not point shapes at out/shapes (found "
            "{!r}). Without it the SHACL arm reports the severities the suite "
            "shipped, which overrides the policy for every dual-formulated "
            "check.".format(config.get("shapes"))
        )
    if config.get("registry") != "out/registry.json":
        fail(
            "ontology-suite.yml does not point registry at out/registry.json "
            "(found {!r})".format(config.get("registry"))
        )
    if config.get("engine") not in ("both", "native+sparql"):
        fail(
            "engine is {!r}; this example uses 'both' so that the two "
            "formulations are cross-checked and a half-applied policy shows "
            "up as drift rather than as a severity you cannot "
            "account for".format(config.get("engine"))
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--work",
        default=str(Path(__file__).resolve().parent),
        help="the work folder (default: the directory holding this script, so "
        "it does not matter where it is run from)",
    )
    parser.add_argument(
        "--policy",
        default="../policy-repo/severities.json",
        help="the policy repo's JSON, relative to the work folder",
    )
    args = parser.parse_args()

    work = Path(args.work).resolve()
    policy_path = (work / args.policy).resolve()
    out = work / "out"
    resources = suite_resources()

    registry = json.loads((resources / "registry.json").read_text(encoding="utf-8"))
    entries = registry["checks"] if isinstance(registry, dict) else registry
    registry_ids = {entry["id"] for entry in entries}

    policy = load_policy(policy_path)
    validate_policy(policy, registry_ids)

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copytree(resources / "sparql", out / "sparql")
    shutil.copytree(resources / "shapes", out / "shapes")

    print("policy: {} ({} override(s))".format(policy_path, len(policy)))
    print("checks: {}".format(resources))
    for check_id, severity in sorted(policy.items()):
        shipped = next(
            entry["default_severity"] for entry in entries if entry["id"] == check_id
        )
        rq_count = apply_to_sparql(out / "sparql", check_id, severity)
        shape_count = apply_to_shapes(out / "shapes", check_id, severity)
        for entry in entries:
            if entry["id"] == check_id and severity != OFF:
                entry["default_severity"] = severity
        print(
            "  {:<9} {:<9} -> {:<9} ({} query, {} shape node(s))".format(
                check_id, shipped, severity, rq_count, shape_count
            )
        )
        if rq_count == 0 and shape_count == 0:
            fail(
                "{} is in the registry but nothing implements it here, so the "
                "override would do nothing. It is probably one of the 11 "
                "CLI-only checks, or extension-only.".format(check_id)
            )

    (out / "registry.json").write_text(
        json.dumps(registry, indent=2) + "\n", encoding="utf-8"
    )

    verify(out / "sparql", out / "shapes", policy)
    check_config_agrees(work / "ontology-suite.yml", policy)

    rq_total = len(list((out / "sparql").rglob("*.rq")))
    shape_total = len(list((out / "shapes").glob("*.ttl")))
    print(
        "assembled: {} query file(s), {} shape file(s), {} registry entries".format(
            rq_total, shape_total, len(entries)
        )
    )
    print("verified: every override is on disk, and the config agrees")
    return 0


if __name__ == "__main__":
    sys.exit(main())
