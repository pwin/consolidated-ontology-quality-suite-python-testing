"""Run every fixture through the suite and print a detection matrix.

    uv run python report.py            # all fixtures
    uv run python report.py 03 06      # only fixtures whose name contains these

Writes out/findings.csv (every finding, one row each) and out/summary.md.
Exits 1 if any fixture's seeded errors went undetected.
"""
from __future__ import annotations

import csv
import sys
from collections import Counter

import detect
from detect import FIXTURES, OUT_DIR, dl_reasoner_ran, ids_of, run_fixture, severity_breach

OK, BAD, DASH = "[ok]", "[MISS]", "  -  "


def main(argv):
    selected = [f for f in FIXTURES if not argv or any(a in f.name for a in argv)]
    all_rows = []
    summary_lines = ["# OWL2 error-detection matrix", ""]
    failures = 0

    for fx in selected:
        rows = run_fixture(fx.name)
        found = ids_of(rows)
        counts = Counter(r.check_id for r in rows)
        all_rows.extend((fx.name, r) for r in rows)

        print(f"\n=== {fx.name}  (stage: {fx.stage})")
        print(f"    seeded: {fx.seeded_errors}")
        summary_lines += [f"## {fx.name}", "", f"*Stage:* `{fx.stage}` — *seeded errors:* {fx.seeded_errors}", ""]

        expected_rows = []
        for check_id in fx.expected:
            hit = check_id in found
            failures += 0 if hit else 1
            print(f"    {OK if hit else BAD} {check_id}  x{counts.get(check_id, 0)}  "
                  f"{detect.check_title(check_id) if hit else '(not reported)'}")
            expected_rows.append((check_id, hit, counts.get(check_id, 0)))

        for check_id in fx.dl_only:
            if not dl_reasoner_ran(rows):
                print(f"    {DASH} {check_id}  (external DL reasoner unavailable — skipped)")
                expected_rows.append((check_id + " (DL)", None, 0))
                continue
            hit = check_id in found
            failures += 0 if hit else 1
            print(f"    {OK if hit else BAD} {check_id}  x{counts.get(check_id, 0)}  (external DL reasoner)")
            expected_rows.append((check_id + " (DL)", hit, counts.get(check_id, 0)))

        for check_id in fx.forbidden:
            clean = check_id not in found
            failures += 0 if clean else 1
            if not clean:
                print(f"    {BAD} {check_id} FALSE POSITIVE (x{counts[check_id]})")
        if fx.forbidden:
            bad = sorted(set(fx.forbidden) & found)
            print(f"    {OK if not bad else BAD} no false positives among {len(fx.forbidden)} guarded id(s)")

        if fx.max_severity:
            breaches = severity_breach(rows, fx.max_severity)
            failures += len(breaches)
            print(f"    {OK if not breaches else BAD} nothing stricter than {fx.max_severity}"
                  + ("" if not breaches else ": " + ", ".join(f"{r.check_id}/{r.focus_node}" for r in breaches)))

        other = sorted(set(counts) - set(fx.expected) - set(fx.dl_only))
        print(f"    other findings: {', '.join(f'{c} x{counts[c]}' for c in other) or 'none'}")

        if expected_rows:
            summary_lines += ["| expected check | detected | findings | title |", "|---|---|---|---|"]
            for check_id, hit, n in expected_rows:
                mark = "yes" if hit else ("skipped" if hit is None else "**NO**")
                base = check_id.split(" ")[0]
                summary_lines.append(f"| {check_id} | {mark} | {n} | {detect.check_title(base)} |")
            summary_lines.append("")
        summary_lines += [f"*Other findings:* {', '.join(f'`{c}` x{counts[c]}' for c in other) or 'none'}", ""]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "findings.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["fixture", "check_id", "severity", "category", "sources", "focus_node", "path", "value", "message"])
        for name, r in all_rows:
            w.writerow([name, r.check_id, r.severity, r.category, "+".join(r.sources),
                        r.focus_node, r.path or "", r.value or "", r.message])
    (OUT_DIR / "summary.md").write_text("\n".join(summary_lines), encoding="utf-8")

    print(f"\nWrote {OUT_DIR / 'findings.csv'} ({len(all_rows)} findings) and {OUT_DIR / 'summary.md'}")
    print("RESULT:", "all seeded errors detected" if not failures else f"{failures} expectation(s) unmet")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
