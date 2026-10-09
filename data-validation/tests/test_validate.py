"""Tests for the validator itself.

The outputs here are synthetic (built from the reference cleaner, then broken on
purpose). They prove each check fires on the failure it exists to catch; they
are not Rhombus AI results.
"""
from __future__ import annotations

import csv
import random
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
DV = HERE.parent
ROOT = DV.parent
sys.path.insert(0, str(DV))

from reference_clean import OUTPUT_COLUMNS, clean_rows, read_csv  # noqa: E402
from validate import validate  # noqa: E402

BASELINE = ROOT / "datasets" / "orders_baseline.csv"


def statuses(report: dict) -> dict[str, str]:
    return {c["id"]: c["status"] for c in report["checks"]}


def write(path: Path, rows: list[dict], columns: list[str] | None = None) -> str:
    columns = columns or list(rows[0])
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return str(path)


@pytest.fixture
def truth() -> list[dict]:
    return clean_rows(read_csv(BASELINE)[1])


def test_generated_datasets_are_committed_and_reproducible():
    r = subprocess.run([sys.executable, str(ROOT / "datasets" / "generate.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_reference_cleaner_drops_exactly_the_planted_bad_rows(truth):
    _, raw = read_csv(BASELINE)
    assert len(raw) == 68                      # 60 orders + 5 exact + 3 near duplicates
    assert len(truth) == 54                    # minus 6 rows with bad date/qty/amount
    ids = [r["order_id"] for r in truth]
    assert len(ids) == len(set(ids))
    assert {"1015", "1019", "1023", "1026", "1030", "1034"}.isdisjoint(ids)


def test_perfect_output_passes_everything(tmp_path, truth):
    out = write(tmp_path / "out.csv", truth, OUTPUT_COLUMNS)
    report = validate("t", str(BASELINE), [out])
    assert report["verdict"] == "PASS", [c for c in report["checks"] if c["status"] != "PASS"]


def test_cents_leaking_through_is_caught_by_semantic_checks(tmp_path, truth):
    leaked = [{**r, "amount_usd": f"{float(r['amount_usd']) * 100:.0f}"} for r in truth]
    out = write(tmp_path / "out.csv", leaked, OUTPUT_COLUMNS)
    s = statuses(validate("t", str(ROOT / "datasets/orders_semantic_cents.csv"), [out]))
    assert s["input.amount_scale"] == "WARN"
    assert s["semantic.amount_scale"] == "FAIL"
    assert s["semantic.unit_price"] == "FAIL"
    assert s["values.amount_usd"] == "FAIL"


def test_ddmm_dates_read_as_mmdd_are_caught(tmp_path, truth):
    swapped = []
    for r in truth:
        d = date.fromisoformat(r["order_date"])
        if d.day <= 12:                      # an ambiguous date silently flips
            d = date(d.year, d.day, d.month)
        swapped.append({**r, "order_date": d.isoformat()})
    out = write(tmp_path / "out.csv", swapped, OUTPUT_COLUMNS)
    s = statuses(validate("t", str(ROOT / "datasets/orders_semantic_date_ddmm.csv"), [out]))
    assert s["input.date_order"] == "WARN"
    assert s["values.order_date"] == "FAIL"
    assert s["semantic.date_window"] == "FAIL"


def test_renamed_column_passed_through_fails_schema(tmp_path, truth):
    renamed = [{("total_amount" if k == "amount_usd" else k): v for k, v in r.items()} for r in truth]
    out = write(tmp_path / "out.csv", renamed)
    report = validate("t", str(ROOT / "datasets/orders_schema_rename_column.csv"), [out])
    s = statuses(report)
    assert s["output.schema"] == "FAIL"
    assert s["values.amount_usd"] == "SKIP"
    drift = next(c for c in report["checks"] if c["id"] == "input.schema")
    assert drift["details"]["likely_renames"] == {"amount_usd": "total_amount"}


def test_combined_drift_does_not_mistake_new_column_for_a_rename():
    report = validate("t", str(ROOT / "datasets/orders_schema_combined.csv"), [])
    drift = next(c for c in report["checks"] if c["id"] == "input.schema")
    assert drift["details"]["likely_renames"] == {"amount_usd": "total_amount"}
    assert set(drift["details"]["missing"]) == {"country", "amount_usd"}


def test_extra_passthrough_column_is_a_warning_not_a_failure(tmp_path, truth):
    extra = [{**r, "discount_code": "SPRING10"} for r in truth]
    out = write(tmp_path / "out.csv", extra)
    s = statuses(validate("t", str(ROOT / "datasets/orders_schema_add_column.csv"), [out]))
    assert s["output.schema"] == "WARN"
    assert s["output.rows"] == "PASS"


def test_uncleaned_rows_fail_rules_and_row_count(tmp_path, truth):
    dirty = truth + [dict(truth[0])]                           # a duplicate
    dirty[1] = {**dirty[1], "customer_name": "  bob  ", "country": "Australia",
                "status": "Shipped", "amount_usd": "$12.00"}
    out = write(tmp_path / "out.csv", dirty, OUTPUT_COLUMNS)
    s = statuses(validate("t", str(BASELINE), [out]))
    for check in ("output.rows", "rule.trimmed", "rule.name_title_case", "rule.country_iso2",
                  "rule.status", "rule.amount_2dp"):
        assert s[check] == "FAIL", check


def test_determinism_ignores_row_order_but_reports_value_changes(tmp_path, truth):
    shuffled = truth[:]
    random.Random(1).shuffle(shuffled)
    a = write(tmp_path / "run1.csv", truth, OUTPUT_COLUMNS)
    b = write(tmp_path / "run2.csv", shuffled, OUTPUT_COLUMNS)
    assert statuses(validate("t", str(BASELINE), [a, b]))["determinism"] == "PASS"

    changed = [dict(r) for r in truth]
    changed[3]["country"] = "XX"
    c = write(tmp_path / "run3.csv", changed, OUTPUT_COLUMNS)
    report = validate("t", str(BASELINE), [a, b, c])
    assert statuses(report)["determinism"] == "FAIL"
    assert f"| {truth[3]['order_id']} | country |" in report["_determinism_diff"]


def test_cli_exit_code_reflects_failures(tmp_path, truth):
    good = write(tmp_path / "good.csv", truth, OUTPUT_COLUMNS)
    bad = write(tmp_path / "bad.csv", truth[:10], OUTPUT_COLUMNS)
    cmd = [sys.executable, str(DV / "validate.py"), "--case", "cli", "--input", str(BASELINE),
           "--report-dir", str(tmp_path / "reports"), "--quiet"]
    assert subprocess.run(cmd + ["--output", good]).returncode == 0
    assert subprocess.run(cmd + ["--output", bad]).returncode == 1
    assert (tmp_path / "reports" / "cli.md").exists()
