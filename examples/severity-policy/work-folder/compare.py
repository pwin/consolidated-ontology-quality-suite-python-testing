#!/usr/bin/env python3
"""Put the default reading and each stage's reading side by side.

The comparison is the illustration: a severity policy is only legible against
the severities the checks themselves declare, and the interesting column is
not the total but which checks moved and in which direction.

Reads the `full_results.csv` each run wrote. Run `compare.sh` first.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORDER = ("Violation", "Warning", "Info")


def load(run: str):
    """Every finding, and a by-check view of them.

    Both are needed and they are not the same number: a run reports one row
    per finding, while a severity is a property of the *check's* reading, so
    the comparison table below is per check. Reporting only the second would
    silently disagree with the "Findings: N" line the run printed.
    """
    path = HERE / "out" / run / "full_results.csv"
    if not path.is_file():
        sys.exit(f"no results for '{run}' at {path} -- run compare.sh first")
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return rows, {r["check_id"]: r for r in rows}


def counts(rows: list, by_check: dict) -> str:
    tally = {sev: sum(1 for r in rows if r["severity"] == sev) for sev in ORDER}
    return "{:>2} finding(s) ({} V, {} W, {} I) across {:>2} check(s)".format(
        len(rows), tally["Violation"], tally["Warning"], tally["Info"], len(by_check)
    )


def main() -> int:
    stages = sys.argv[1:] or ["sketch", "draft", "release"]
    loaded = {"defaults": load("defaults")}
    for stage in stages:
        loaded[stage] = load(stage)
    runs = {name: by_check for name, (_, by_check) in loaded.items()}

    print()
    print("Each run, as a whole")
    print("-" * 64)
    for name, (rows, by_check) in loaded.items():
        print(f"  {name:<10} {counts(rows, by_check)}")

    # Only the checks any run disagrees about. A check reported identically
    # everywhere is not what the reader is here for, and 12 unchanged rows
    # would bury the three that moved.
    moved = sorted(
        cid
        for cid in set().union(*(set(r) for r in runs.values()))
        if len({runs[name].get(cid, {}).get("severity", "--") for name in runs}) > 1
    )

    print()
    print("Where the readings differ")
    print("-" * 64)
    header = "  {:<10}".format("check") + "".join(f"{n:<12}" for n in runs)
    print(header)
    for cid in moved:
        cells = ""
        for name in runs:
            row = runs[name].get(cid)
            cells += "{:<12}".format(row["severity"] if row else "-- off --")
        print(f"  {cid:<10}{cells}")

    print()
    print("What each run would block on, at --fail-on Violation")
    print("-" * 64)
    for name, rows in runs.items():
        blocking = sorted(c for c, r in rows.items() if r["severity"] == "Violation")
        print(f"  {name:<10} {', '.join(blocking) if blocking else 'nothing'}")

    # The declared severity travels with the finding, so a reader of any one
    # report can see it was re-mapped without being told which stage ran.
    print()
    print("What the checks themselves declared, where a stage moved them")
    print("-" * 64)
    shown = False
    for name, rows in runs.items():
        if name == "defaults":
            continue
        for cid in moved:
            row = rows.get(cid)
            if row and row.get("declared_severity"):
                print(f"  {name:<10} {cid:<10} {row['declared_severity']} -> {row['severity']}")
                shown = True
    if not shown:
        print("  (nothing re-mapped)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
