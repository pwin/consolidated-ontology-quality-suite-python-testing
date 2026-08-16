"""Why does every pyshacl-sourced finding come back as a Violation?

FIXED UPSTREAM in ontology-quality-suite 0.6.0 (commit 2f4950c). Against
0.5.1 this probe reproduced the bug; against >= 0.6.0 it is a regression
check -- both runs below now agree with registry.json.

Originally observed while running the fixtures with the default
`--engine both`: checks whose registry `default_severity` is Warning/Info
(STY-001/002/003, QUA-001/002/003, EFF-001/002) were reported as Violation
whenever pyshacl produced them, while the portable SPARQL formulation of the
same check reported the registry severity.

Cause: the shapes declared `sh:severity` on the nested `sh:SPARQLConstraint`
blank node, but SHACL defines `sh:severity` as a property of the *shape*;
pyshacl therefore never saw it and fell back to the spec default,
sh:Violation.

This probe runs the suite's own style shapes over fixture 07 twice --
as shipped, then with `sh:severity` lifted to the shape node -- and prints
the severity each run reports. Identical output from both runs means the
shipped shapes declare severity where SHACL expects it.

    uv run python experiments/severity_probe.py

Note: the patcher below is deliberately crude (line-oriented) and does not
rewrite the two-shape STY-002 pair; that is a limitation of the probe, not a
counter-example.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from ontology_suite import config, pipeline
from ontology_suite.checks.registry import Registry

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "ontologies" / "07-naming-style" / "ontology.ttl"
WORK = ROOT / "out" / "experiment"

# Lift `sh:severity <X>` out of the sh:sparql [...] block and onto the shape:
#   oq:STY-001              ->  oq:STY-001
#     a sh:NodeShape ;            a sh:NodeShape ;
#     ...                         sh:severity sh:Warning ;
#     sh:sparql [                 ...
#       sh:severity sh:Warning ;  sh:sparql [
SHAPE_START = re.compile(r"^(oq:[A-Z]{3}-\d{3}[\w-]*)\s*$", re.MULTILINE)


def lift_severities(text: str) -> str:
    out, pending, buffer = [], None, []
    for line in text.splitlines():
        stripped = line.strip()
        if SHAPE_START.match(line):
            out.extend(buffer)
            buffer = [line]
            pending = None
            continue
        if buffer:
            if stripped.startswith("sh:severity"):
                pending = stripped.rstrip(";").strip()
                buffer.append(line)
                continue
            if stripped.startswith("a sh:NodeShape") and pending is None:
                buffer.append(line)
                continue
            buffer.append(line)
            if stripped in ("] .", ".") or stripped.endswith("] ."):
                if pending:
                    # insert the severity right after the shape's own `a sh:NodeShape ;`
                    for i, buffered in enumerate(buffer):
                        if buffered.strip().startswith("a sh:NodeShape"):
                            buffer.insert(i + 1, f"  {pending} ;")
                            break
                out.extend(buffer)
                buffer, pending = [], None
            continue
        out.append(line)
    out.extend(buffer)
    return "\n".join(out) + "\n"


def run(shapes_dir: Path, label: str) -> None:
    registry = Registry.load(config.DEFAULT_REGISTRY_PATH)
    stage = pipeline.run_checks_stage(
        registry, WORK / label, ontology_path=str(ONTOLOGY),
        shapes_dir=str(shapes_dir), engine="shacl",
    )
    print(f"\n--- {label}")
    for row in sorted(stage.rows, key=lambda r: (r.check_id or "", r.focus_node)):
        default = registry.get(row.check_id).default_severity if registry.get(row.check_id) else "?"
        flag = "" if row.severity == default else "   <-- differs from registry default"
        print(f"    {row.check_id}  reported={row.severity:<9} registry={default:<9}{flag}")


def main() -> None:
    shipped = Path(config.DEFAULT_SHAPES_DIR)
    as_shipped = WORK / "shapes-as-shipped"
    patched = WORK / "shapes-patched"
    for target in (as_shipped, patched):
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        shutil.copy(shipped / "style.ttl", target / "style.ttl")

    src = (patched / "style.ttl").read_text(encoding="utf-8")
    (patched / "style.ttl").write_text(lift_severities(src), encoding="utf-8")

    print(f"Shapes as shipped: {shipped / 'style.ttl'}")
    print(f"Patched copy:      {patched / 'style.ttl'} (sh:severity moved onto the shape node)")
    run(as_shipped, "shapes-as-shipped")
    run(patched, "shapes-patched")


if __name__ == "__main__":
    main()
