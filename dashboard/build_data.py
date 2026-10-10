#!/usr/bin/env python3
"""Build dashboard/data.json from the validation reports and the test results.

    python dashboard/build_data.py

The validator reports come from data-validation/reports/*.json. The columns a
validator cannot know (did the run stop, did the chatbot fix work, severity)
are written by hand below from the write-ups in observations/.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "data-validation" / "reports"

# quantity is written as 2.0 in every output, including the correct baseline,
# so it is shown separately rather than counted as a drift finding.
KNOWN_ISSUE = "rule.quantity_positive_int"

TESTS = [
    {
        "case": "baseline", "name": "Baseline", "kind": "Baseline",
        "doc": "observations/baseline.md",
        "stopped": "No", "chatbot": "Correct after 6 outputs and 7 follow-ups",
        "severity": "None",
        "summary": "The correct pipeline output. Every earlier wrong output was reported as a success.",
    },
    {
        "case": "schema_drop_column", "name": "Drop column", "kind": "Schema drift",
        "doc": "observations/schema-drop-column.md",
        "stopped": "Yes, failed", "chatbot": "Only for the drifted file; it broke the original file",
        "severity": "High",
        "summary": "The run failed with a code dump. The fix only worked for the new file.",
    },
    {
        "case": "schema_rename_column", "name": "Rename column", "kind": "Schema drift",
        "doc": "observations/schema-rename-column.md",
        "stopped": "Yes, failed", "chatbot": "No, then yes after I named the rename",
        "severity": "High",
        "summary": "The chatbot did not find the renamed column until I described it.",
    },
    {
        "case": "schema_type_change", "name": "Type change", "kind": "Schema drift",
        "doc": "observations/schema-type-change.md",
        "stopped": "Yes, with a misleading error", "chatbot": "No (an empty file reached GCS), then yes after a hint",
        "severity": "High",
        "summary": "The first fix removed the crash, and an empty file was written to GCS.",
    },
    {
        "case": "schema_add_column", "name": "Add column", "kind": "Schema drift",
        "doc": "observations/schema-add-column.md",
        "stopped": "No, output correct", "chatbot": "Not needed",
        "severity": "Low",
        "summary": "Handled cleanly. The new column was dropped without any notice.",
    },
    {
        "case": "schema_combined", "name": "Combined schema changes", "kind": "Schema drift",
        "doc": "observations/schema-combined.md",
        "stopped": "Yes, failed", "chatbot": "No in two rounds, then yes after a hint",
        "severity": "High",
        "summary": "Ask Chatbot looped twice and blamed the scheduler before a hint fixed it.",
    },
    {
        "case": "semantic_cents", "name": "Amounts in cents", "kind": "Semantic drift",
        "doc": "observations/semantic-cents.md",
        "stopped": "No, wrong amounts written silently", "chatbot": "Yes after a hint, but it broke the original file",
        "severity": "High",
        "summary": "Amounts reached GCS 100x too large with a success status.",
    },
    {
        "case": "semantic_date_ddmm", "name": "Dates as DD/MM", "kind": "Semantic drift",
        "doc": "observations/semantic-date-ddmm.md",
        "stopped": "No, 14 wrong dates written silently", "chatbot": "No, two claimed fixes changed nothing",
        "severity": "Critical",
        "summary": "Day and month were swapped on 14 orders. The chatbot said the dates were correct.",
    },
]


FINDINGS = [
    {
        "title": "Dates were swapped silently and the fixes did nothing",
        "body": "DD/MM dates were read as MM/DD and 14 wrong dates reached GCS with a success status. "
                "The chatbot said the dates were correct, then claimed two fixes that produced a byte-identical output.",
        "doc": "observations/semantic-date-ddmm.md",
    },
    {
        "title": "Chatbot fixes fit only the file in front of them",
        "body": "One fix turned a crash into an empty file in GCS. Others worked for the drifted file but broke the original, "
                "and most only found the cause after I described it.",
        "doc": "observations/schema-type-change.md",
    },
    {
        "title": "A successful run says nothing about the data",
        "body": "Every wrong output was reported as a success. The scheduler skipped changed files as unchanged data, "
                "and successful scheduled runs do not appear in the logs.",
        "doc": "observations/baseline.md",
    },
]

PIPELINE = ["S3 source", "orders_raw", "orders_trimmed", "orders_no_exact_dups",
            "orders_deduped", "orders_cleaned", "orders_output", "GCS destination"]


def main() -> None:
    tests = []
    for t in TESTS:
        report = json.loads((REPORTS / f"{t['case']}.json").read_text(encoding="utf-8"))
        checks = report["checks"]
        failed = [c for c in checks if c["status"] == "FAIL" and c["id"] != KNOWN_ISSUE]
        warned = [c for c in checks if c["status"] == "WARN"]
        tests.append({
            **t,
            "validator": {
                "counts": report["summary"],
                "verdict": report["verdict"],
                "failed": [{"id": c["id"], "message": c["message"]} for c in failed],
                "warned": [{"id": c["id"], "message": c["message"]} for c in warned],
                "known_issue": any(c["id"] == KNOWN_ISSUE and c["status"] == "FAIL" for c in checks),
                "outputs": report.get("outputs", []),
                "validated_at": report.get("validated_at"),
            },
        })
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "known_issue": "quantity is written as 2.0 instead of 2",
        "tests": tests,
        "findings": FINDINGS,
        "pipeline": PIPELINE,
    }
    out = Path(__file__).resolve().parent / "data.json"
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} with {len(tests)} tests")


if __name__ == "__main__":
    main()
