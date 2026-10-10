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


# Run-level results for the bonus dashboard sections, written by hand from
# observations/ and the output files kept in runs/. Only recorded runs count:
# "runs" is how many times a setup was run, as recorded in the write-ups.
# The baseline file gave a byte-identical output 5 times across pipeline
# versions (observations/baseline.md). Only the first scheduled baseline run
# was timed (17 s); no other run time was recorded.
SECONDS = {"measured": {"baseline": 17}}

# heat columns: completed, correct, surfaced, chatbot (no hint), chatbot (hint)
# values: ok, partial, stop (failed loudly), fail (wrong data or missed), na. Each pair is (state, label).
EXTRA = {
    "baseline": {
        "group": "Baseline", "runs": 5, "completed": True, "correct": True, "verdict": None, "heat": None,
        "configs": [("Original pipeline", "Baseline file", "Correct", "runs/baseline/run1.csv", 5)],
    },
    "schema_drop_column": {
        "group": "Schema drift", "completed": False, "correct": False, "verdict": "Breaks",
        "heat": [("stop", "Failed"), ("stop", "None written"), ("ok", "Yes, run failed"), ("partial", "Broke original file"), ("na", "Not needed")],
        "configs": [
            ("Original pipeline", "Drift file", "Run failed", None, 1),
            ("Chatbot fix", "Drift file", "54 rows, no country", "runs/schema_drop_column/run1.csv", 1),
            ("Chatbot fix", "Baseline file", "Valid country column lost", "runs/schema_drop_column/after-restore.csv", 1),
            ("Restored", "Baseline file", "Correct", "runs/schema_drop_column/restored.csv", 1),
        ],
    },
    "schema_rename_column": {
        "group": "Schema drift", "completed": False, "correct": False, "verdict": "Breaks",
        "heat": [("stop", "Failed"), ("stop", "None written"), ("ok", "Yes, run failed"), ("fail", "Wrong data"), ("ok", "Fixed")],
        "configs": [
            ("Original pipeline", "Drift file", "Run failed", None, 1),
            ("Chatbot fix 1", "Drift file", "56 rows, no amount", "runs/schema_rename_column/run1.csv", 1),
            ("Chatbot fix 2", "Drift file", "Correct", "runs/schema_rename_column/run2-fixed.csv", 1),
            ("Restored", "Baseline file", "Correct", "runs/schema_rename_column/restored.csv", 1),
        ],
    },
    "schema_type_change": {
        "group": "Schema drift", "completed": False, "correct": False, "verdict": "Breaks",
        "heat": [("stop", "Failed"), ("stop", "None written"), ("partial", "Misleading error"), ("fail", "Empty file"), ("ok", "Fixed")],
        "configs": [
            ("Original pipeline", "Drift file", "Run failed", None, 1),
            ("Chatbot fix 1", "Drift file", "Empty file", "runs/schema_type_change/run1.csv", 1),
            ("Chatbot fix 2", "Drift file", "Correct", "runs/schema_type_change/run2-fixed.csv", 1),
            ("Chatbot fix 2", "Baseline file", "Correct", "runs/schema_type_change/restored.csv", 1),
        ],
    },
    "schema_add_column": {
        "group": "Schema drift", "completed": True, "correct": True, "verdict": "Handled",
        "heat": [("ok", "Yes"), ("ok", "Correct"), ("partial", "New column dropped silently"), ("na", "Not needed"), ("na", "Not needed")],
        "configs": [("Original pipeline", "Drift file", "Correct", "runs/schema_add_column/run1.csv", 1)],
    },
    "schema_combined": {
        "group": "Combined drift", "completed": False, "correct": False, "verdict": "Breaks",
        "heat": [("stop", "Failed"), ("stop", "None written"), ("ok", "Yes, run failed"), ("stop", "Failed twice"), ("ok", "Fixed")],
        "configs": [
            ("Original pipeline", "Drift file", "Run failed", None, 1),
            ("Chatbot fix 1", "Drift file", "Run failed", None, 1),
            ("Chatbot fix 2", "Drift file", "Run failed", None, 1),
            ("Hint fix", "Drift file", "Correct, country empty", "runs/schema_combined/run1-fixed.csv", 1),
            ("Hint fix", "Baseline file", "Correct", "runs/schema_combined/restored.csv", 1),
        ],
    },
    "semantic_cents": {
        "group": "Semantic drift", "completed": True, "correct": False, "verdict": "Missed",
        "heat": [("ok", "Yes"), ("fail", "Wrong, 100x"), ("fail", "No warning"), ("fail", "Missed it"), ("partial", "Broke original file")],
        "configs": [
            ("Original pipeline", "Drift file", "Amounts 100x too large", "runs/semantic_cents/run1.csv", 1),
            ("Hint fix", "Drift file", "Correct", "runs/semantic_cents/run2-fixed.csv", 1),
            ("Hint fix", "Baseline file", "Amounts 100x too small", "runs/semantic_cents/after-restore.csv", 1),
            ("Restored", "Baseline file", "Correct", "runs/semantic_cents/restored.csv", 1),
        ],
    },
    "semantic_date_ddmm": {
        "group": "Semantic drift", "completed": True, "correct": False, "verdict": "Missed",
        "heat": [("ok", "Yes"), ("fail", "14 dates wrong"), ("fail", "No warning"), ("fail", "Said it was correct"), ("fail", "No change")],
        "configs": [
            ("Original pipeline", "Drift file", "14 dates swapped", "runs/semantic_date_ddmm/run1.csv", 1),
            ("Chatbot fix 1", "Drift file", "Identical to the first run", "runs/semantic_date_ddmm/run2-claimed-fix.csv", 1),
            ("Chatbot fix 2", "Drift file", "Identical to the first run", "runs/semantic_date_ddmm/run3-claimed-fix.csv", 1),
            ("Restored", "Baseline file", "Correct", "runs/semantic_date_ddmm/restored.csv", 1),
        ],
    },
}


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
        x = EXTRA[t["case"]]
        tests.append({
            **t,
            "group": x["group"],
            "health": {"runs": x.get("runs", 1), "completed": x["completed"], "correct": x["correct"]},
            "verdict": x["verdict"],
            "heat": [{"state": s, "label": l} for s, l in x["heat"]] if x["heat"] else None,
            "configs": [{"pipeline": p, "input": i, "result": r, "file": f, "runs": n} for p, i, r, f, n in x["configs"]],
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
        "seconds": SECONDS,
        "heat_columns": ["Run completed", "Output", "Rhombus warned", "AI fix, unprompted", "AI fix, with hint"],
    }
    out = Path(__file__).resolve().parent / "data.json"
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} with {len(tests)} tests")


if __name__ == "__main__":
    main()
