#!/usr/bin/env python3
"""Validate every run that has been downloaded into runs/.

Layout (created by scripts/fetch_output.sh):

    runs/<case>/run1.csv, run2.csv, run3.csv
    datasets/orders_<case>.csv      <- what was uploaded to S3 for that case

    python data-validation/run_all.py              # writes reports/, prints a summary
    python data-validation/run_all.py --strict     # exit 1 if any case FAILs

Without --strict the exit code is 0 even when drift cases fail: for drift
cases a FAIL is usually the finding, not a broken script.
"""
from __future__ import annotations

import argparse
import json
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

    runs = Path(a.runs)
    cases = sorted(p for p in runs.iterdir() if p.is_dir()) if runs.exists() else []
    if not cases:
        print(f"no runs found under {runs}/<case>/run*.csv — see scripts/fetch_output.sh")
        return 0

    rows, summary = [], []
    for case_dir in cases:
        case = case_dir.name
        source = ROOT / "datasets" / f"orders_{case}.csv"
        outputs = sorted(str(p) for p in case_dir.glob("run*.csv"))
        if not source.exists():
            print(f"skip {case}: no {source.relative_to(ROOT)}")
            continue
        report = validate(case, str(source), outputs)
        write_reports(report, Path(a.report_dir))
        failed = [c["id"] for c in report["checks"] if c["status"] == "FAIL"]
        rows.append(f"| {case} | {len(outputs)} | {report['verdict']} | {', '.join(failed) or '-'} |")
        summary.append({"case": case, "runs": len(outputs), "verdict": report["verdict"],
                        "failed_checks": failed, "summary": report["summary"]})

    table = "\n".join(["| Case | Runs | Verdict | Failed checks |", "|---|---|---|---|", *rows])
    Path(a.report_dir, "SUMMARY.md").write_text("# Validation summary\n\n" + table + "\n", encoding="utf-8")
    Path(a.report_dir, "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(table)
    return 1 if a.strict and any(s["verdict"] == "FAIL" for s in summary) else 0


if __name__ == "__main__":
    sys.exit(main())
