#!/usr/bin/env python3
"""Validate every run that has been downloaded into runs/.

Layout (outputs downloaded by hand from the GCS bucket):

    runs/<case>/run1.csv            <- first output of the drift file
    datasets/orders_<case>.csv      <- what was uploaded to S3 for that case

Only the first run*.csv of each case is validated. Later files in a case
folder (run2-fixed.csv, restored.csv, ...) come from changed pipelines or a
different input, so they are not repeats and are not compared for
determinism. To check repeats, pass several --output files to validate.py.
Paths in the reports are written relative to the repository root.

    python data-validation/run_all.py              # writes reports/, prints a summary
    python data-validation/run_all.py --strict     # exit 1 if any case FAILs

Without --strict the exit code is 0 even when drift cases fail: for drift
cases a FAIL is usually the finding, not a broken script.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate import validate, write_reports  # noqa: E402

ROOT = HERE.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=str(ROOT / "runs"))
    ap.add_argument("--report-dir", default=str(HERE / "reports"))
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()

    runs = Path(a.runs).resolve()
    report_dir = Path(a.report_dir).resolve()
    os.chdir(ROOT)  # so the paths written into the reports are relative
    cases = sorted(p for p in runs.iterdir() if p.is_dir()) if runs.exists() else []
    if not cases:
        print(f"no runs found under {runs}/<case>/run*.csv")
        return 0

    rows, summary = [], []
    for case_dir in cases:
        case = case_dir.name
        source = Path("datasets") / f"orders_{case}.csv"
        found = sorted(case_dir.glob("run*.csv"))
        if not source.exists():
            print(f"skip {case}: no {source.as_posix()}")
            continue
        if not found:
            print(f"skip {case}: no run*.csv")
            continue
        outputs = [Path(os.path.relpath(found[0], ROOT)).as_posix()]
        report = validate(case, source.as_posix(), outputs)
        write_reports(report, report_dir)
        failed = [c["id"] for c in report["checks"] if c["status"] == "FAIL"]
        rows.append(f"| {case} | {len(outputs)} | {report['verdict']} | {', '.join(failed) or '-'} |")
        summary.append({"case": case, "runs": len(outputs), "verdict": report["verdict"],
                        "failed_checks": failed, "summary": report["summary"]})

    table = "\n".join(["| Case | Runs | Verdict | Failed checks |", "|---|---|---|---|", *rows])
    Path(report_dir, "SUMMARY.md").write_text("# Validation summary\n\n" + table + "\n", encoding="utf-8")
    Path(report_dir, "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(table)
    return 1 if a.strict and any(s["verdict"] == "FAIL" for s in summary) else 0


if __name__ == "__main__":
    sys.exit(main())
