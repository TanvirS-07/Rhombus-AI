#!/usr/bin/env python3
"""Compare a Rhombus AI output (downloaded from GCS) with its S3 input.

    python data-validation/validate.py --case baseline \
        --input datasets/orders_baseline.csv \
        --output runs/baseline/run1.csv --output runs/baseline/run2.csv

What it checks (each check is PASS / WARN / FAIL / SKIP):

  input.*        what changed in the uploaded file vs the baseline file
                 (schema drift, type drift, amount scale, date order)
  output.schema  output columns vs the contract
  output.rows    row count and order_ids vs the reference-cleaned baseline
  rule.*         each cleaning rule actually holds in the output
  values.*       cell-by-cell agreement with the reference-cleaned baseline
  semantic.*     invariants that catch meaning changes the schema can't show
                 (date window, amount scale, implied unit price)
  determinism    every --output of the same input is identical

The truth for every case is reference_clean(baseline input): drift changes how
the orders are written, never which orders exist, so a pipeline that copes
with the drift produces the same table as the baseline.

Exit code: 0 when no check FAILs, 1 otherwise, 2 on usage errors.
Reports go to data-validation/reports/<case>.json and .md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from reference_clean import (EMAIL_RE, clean_rows, norm_text,  # noqa: E402
                             parse_money, parse_source_date, read_csv)

ROOT = HERE.parent
DEFAULT_BASELINE = ROOT / "datasets" / "orders_baseline.csv"
CONTRACT = json.loads((HERE / "contract.json").read_text(encoding="utf-8"))
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SAMPLE = 5


@dataclass
class Check:
    id: str
    status: str            # PASS | WARN | FAIL | SKIP
    message: str
    details: dict = field(default_factory=dict)


# --- tolerant parsers for output values ------------------------------------

def out_date(v: str) -> date | None:
    v = norm_text(v)
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", v)        # 2025-03-16[ 00:00:00|T..]
    if m:
        try:
            return date.fromisoformat(m.group(1))
        except ValueError:
            return None
    if re.fullmatch(r"\d{9,13}", v):                 # epoch seconds / millis
        n = int(v) / (1000 if len(v) > 10 else 1)
        return datetime.fromtimestamp(n, tz=timezone.utc).date()
    return parse_source_date(v)


def out_int(v: str) -> int | None:
    m = parse_money(v)
    return int(m) if m is not None and float(m).is_integer() else None


def canon_cell(col: str, v: str) -> str:
    """Canonical form used for value comparison (not for format rules)."""
    if col == "order_date":
        d = out_date(v)
        return d.isoformat() if d else norm_text(v)
    if col in ("amount_usd", "total_amount"):
        m = parse_money(v)
        return f"{m:.2f}" if m is not None else norm_text(v)
    if col in ("quantity", "order_id"):
        i = out_int(v)
        return str(i) if i is not None else norm_text(v)
    if col == "customer_name":
        return norm_text(v).casefold()
    return norm_text(v).lower() if col in ("email", "status") else norm_text(v)


# --- input profiling: detect drift in what was uploaded ---------------------

def classify(values: list[str]) -> str:
    vals = [norm_text(v) for v in values if norm_text(v)]
    if not vals:
        return "empty"
    def frac(pred):
        return sum(1 for v in vals if pred(v)) / len(vals)
    if frac(lambda v: re.fullmatch(r"\d{9,13}", v) is not None) > 0.8:
        return "epoch"
    if frac(lambda v: re.fullmatch(r"-?\d+", v) is not None) > 0.8:
        return "integer"
    if frac(lambda v: parse_money(v) is not None) > 0.8:
        return "number"
    if frac(lambda v: parse_source_date(v) is not None
            or re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", v) is not None) > 0.8:
        return "date"
    return "text"


def check_input(cols: list[str], rows: list[dict], base_cols: list[str],
                base_rows: list[dict]) -> list[Check]:
    checks: list[Check] = []
    missing = [c for c in base_cols if c not in cols]
    extra = [c for c in cols if c not in base_cols]
    # a renamed column carries the same values for the same order_ids
    key = CONTRACT["key"]
    base_by_id = {}
    for r in base_rows:
        base_by_id.setdefault(norm_text(r.get(key)), r)
    renames = {}
    for m in missing:
        for e in extra:
            pairs = [(norm_text(r.get(e)), norm_text(base_by_id.get(norm_text(r.get(key)), {}).get(m)))
                     for r in rows]
            same = sum(1 for a, b in pairs if a == b) / max(len(pairs), 1)
            if e not in renames.values() and same > 0.8:
                renames[m] = e
                break
    if missing or extra:
        checks.append(Check("input.schema", "WARN",
                            f"schema drift: missing={missing} added={extra}"
                            + (f" likely renames={renames}" if renames else ""),
                            {"missing": missing, "added": extra, "likely_renames": renames}))
    else:
        checks.append(Check("input.schema", "PASS", "columns match the baseline"))

    changed = {}
    for c in cols:
        if c in base_cols:
            before = classify([r.get(c, "") for r in base_rows])
            after = classify([r.get(c, "") for r in rows])
            if before != after:
                changed[c] = f"{before} -> {after}"
    checks.append(Check("input.types", "WARN" if changed else "PASS",
                        f"type drift: {changed}" if changed else "column types match the baseline",
                        {"changed": changed}))

    amount_col = "amount_usd" if "amount_usd" in cols else renames.get("amount_usd")
    if amount_col:
        now = [m for r in rows if (m := parse_money(r.get(amount_col, ""))) is not None and m > 0]
        then = [m for r in base_rows if (m := parse_money(r.get("amount_usd", ""))) is not None and m > 0]
        ratio = statistics.median(now) / statistics.median(then)
        limit = CONTRACT["scale_change_ratio"]
        bad = ratio > limit or ratio < 1 / limit
        checks.append(Check("input.amount_scale", "WARN" if bad else "PASS",
                            f"median {amount_col} is {ratio:.1f}x the baseline"
                            + (" (dollars -> cents?)" if ratio > limit else ""),
                            {"ratio": round(ratio, 3), "column": amount_col}))

    if "order_date" in cols:
        first_gt12 = second_gt12 = 0
        for r in rows:
            m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/\d{4}", norm_text(r.get("order_date")))
            if m:
                first_gt12 += int(m.group(1)) > 12
                second_gt12 += int(m.group(2)) > 12
        ddmm = first_gt12 > second_gt12
        checks.append(Check("input.date_order", "WARN" if ddmm else "PASS",
                            f"{first_gt12} slash dates have a first part > 12 vs {second_gt12} "
                            "with a second part > 12: " + ("dates look DD/MM" if ddmm else "dates look MM/DD"),
                            {"first_part_gt12": first_gt12, "second_part_gt12": second_gt12}))
    return checks


# --- output checks ----------------------------------------------------------

def check_output(cols: list[str], rows: list[dict], truth: list[dict],
                 source_ids: set[str]) -> list[Check]:
    checks: list[Check] = []
    if not rows:
        return [Check("output.rows", "FAIL", "output has no data rows")]

    expected = CONTRACT["output_columns"]
    missing = [c for c in expected if c not in cols]
    extra = [c for c in cols if c not in expected]
    status = "FAIL" if missing else "WARN" if extra else "PASS"
    checks.append(Check("output.schema", status,
                        f"missing={missing} unexpected={extra}" if status != "PASS"
                        else "output columns match the contract",
                        {"columns": cols, "missing": missing, "unexpected": extra}))

    key = CONTRACT["key"]
    if key not in cols:
        checks.append(Check("output.rows", "FAIL", f"no {key} column, cannot match rows"))
        return checks

    ids = [canon_cell(key, r[key]) for r in rows]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    truth_ids = {t[key] for t in truth}
    invented = sorted(set(ids) - source_ids)
    lost = sorted(truth_ids - set(ids))
    kept_bad = sorted(set(ids) - truth_ids - set(invented))
    ok = not (dup or invented or lost or kept_bad) and len(rows) == len(truth)
    checks.append(Check("output.rows", "PASS" if ok else "FAIL",
                        f"{len(rows)} rows, expected {len(truth)}"
                        + ("" if ok else f"; duplicates={dup[:SAMPLE]} invented={invented[:SAMPLE]} "
                           f"dropped_valid={lost[:SAMPLE]} kept_invalid={kept_bad[:SAMPLE]}"),
                        {"actual": len(rows), "expected": len(truth), "duplicates": dup,
                         "invented": invented, "dropped_valid": lost, "kept_invalid": kept_bad}))

    checks += check_rules(cols, rows)
    checks += check_values(cols, rows, truth)
    checks += check_semantics(cols, rows)
    return checks


def _rule(rule_id: str, rows: list[dict], col: str, cols: list[str], pred, desc: str) -> Check:
    if col not in cols:
        return Check(rule_id, "SKIP", f"column {col} not in output")
    bad = [r.get(col, "") for r in rows if not pred(r.get(col, "") or "")]
    return Check(rule_id, "FAIL" if bad else "PASS",
                 f"{len(bad)}/{len(rows)} rows break: {desc}" if bad else desc,
                 {"examples": bad[:SAMPLE]})


def check_rules(cols, rows) -> list[Check]:
    countries = set(CONTRACT["allowed_countries"])
    statuses = set(CONTRACT["allowed_status"])
    text_cols = [c for c in cols if c in ("customer_name", "email", "country", "status")]
    untrimmed = [f"{c}={r[c]!r}" for r in rows for c in text_cols
                 if (r.get(c) or "") != norm_text(r.get(c))]
    checks = [Check("rule.trimmed", "FAIL" if untrimmed else "PASS",
                    f"{len(untrimmed)} cells have stray whitespace" if untrimmed
                    else "text is trimmed", {"examples": untrimmed[:SAMPLE]})]
    checks.append(_rule("rule.name_title_case", rows, "customer_name", cols,
                        lambda v: bool(v) and all(w[:1].isupper() for w in v.split()) and not v.isupper(),
                        "customer_name is Title Case and never empty"))
    checks.append(_rule("rule.email", rows, "email", cols,
                        lambda v: v == "" or EMAIL_RE.match(v) is not None,
                        "email is lowercase and valid, or empty"))
    checks.append(_rule("rule.country_iso2", rows, "country", cols,
                        lambda v: v == "" or v in countries,
                        f"country is one of {sorted(countries)} or empty"))
    checks.append(_rule("rule.date_iso", rows, "order_date", cols,
                        lambda v: ISO_DATE_RE.match(v) is not None and out_date(v) is not None,
                        "order_date is YYYY-MM-DD"))
    checks.append(_rule("rule.quantity_positive_int", rows, "quantity", cols,
                        lambda v: re.fullmatch(r"\d+", v) is not None and int(v) > 0,
                        "quantity is a positive integer"))
    checks.append(_rule("rule.amount_2dp", rows, "amount_usd", cols,
                        lambda v: re.fullmatch(r"\d+(\.\d{1,2})?", v) is not None,
                        "amount_usd is a non-negative number, at most 2 decimals, no symbols"))
    checks.append(_rule("rule.status", rows, "status", cols,
                        lambda v: v in statuses, f"status is one of {sorted(statuses)}"))
    return checks


def check_values(cols, rows, truth) -> list[Check]:
    key = CONTRACT["key"]
    by_id = {canon_cell(key, r[key]): r for r in rows}
    checks = []
    for col in CONTRACT["output_columns"]:
        if col == key:
            continue
        if col not in cols:
            checks.append(Check(f"values.{col}", "SKIP", f"{col} not in output"))
            continue
        diffs = []
        matched = 0
        for t in truth:
            r = by_id.get(t[key])
            if r is None:
                continue
            matched += 1
            if canon_cell(col, r.get(col, "")) != canon_cell(col, t[col]):
                diffs.append({"order_id": t[key], "expected": t[col], "actual": r.get(col, "")})
        checks.append(Check(f"values.{col}", "FAIL" if diffs else "PASS",
                            f"{len(diffs)}/{matched} rows differ from the reference" if diffs
                            else f"all {matched} matched rows agree with the reference",
                            {"diffs": diffs[:SAMPLE], "diff_count": len(diffs)}))
    return checks


def check_semantics(cols, rows) -> list[Check]:
    checks = []
    tol = CONTRACT["max_out_of_range_fraction"]
    if "order_date" in cols:
        lo, hi = (date.fromisoformat(d) for d in CONTRACT["date_window"])
        dates = [out_date(r.get("order_date", "")) for r in rows]
        outside = [r["order_date"] for r, d in zip(rows, dates) if d is None or not lo <= d <= hi]
        months = sorted({d.month for d in dates if d})
        checks.append(Check("semantic.date_window", "FAIL" if outside else "PASS",
                            f"{len(outside)}/{len(rows)} dates outside {lo}..{hi}; months seen {months}"
                            if outside else f"all dates inside {lo}..{hi}",
                            {"examples": outside[:SAMPLE], "months_seen": months}))
    if "amount_usd" in cols:
        amounts = [m for r in rows if (m := parse_money(r.get("amount_usd", ""))) is not None]
        if amounts:
            med = statistics.median(amounts)
            lo, hi = CONTRACT["amount_median_range"]
            checks.append(Check("semantic.amount_scale", "PASS" if lo <= med <= hi else "FAIL",
                                f"median amount_usd = {med:.2f} (expected {lo}..{hi} dollars)",
                                {"median": med}))
        if "quantity" in cols:
            lo, hi = CONTRACT["unit_price_range"]
            prices = []
            for r in rows:
                a, q = parse_money(r.get("amount_usd", "")), out_int(r.get("quantity", ""))
                if a is not None and q:
                    prices.append((r.get("order_id"), a / q))
            off = [f"{i}: {p:.2f}" for i, p in prices if not lo <= p <= hi]
            frac = len(off) / len(prices) if prices else 0
            checks.append(Check("semantic.unit_price", "FAIL" if frac > tol else "WARN" if off else "PASS",
                                f"{len(off)}/{len(prices)} implied unit prices outside ${lo}..${hi}",
                                {"examples": off[:SAMPLE]}))
    return checks


# --- determinism ---------------------------------------------------------------

def canonical_table(cols: list[str], rows: list[dict]) -> list[tuple]:
    key = CONTRACT["key"]
    scols = sorted(cols)
    table = [tuple(norm_text(r.get(c)) for c in scols) for r in rows]
    if key in cols:
        k = scols.index(key)
        return sorted(table, key=lambda t: (out_int(t[k]) or 0, t))
    return sorted(table)


def check_determinism(outputs: list[tuple[str, list[str], list[dict]]]) -> tuple[Check, str]:
    if len(outputs) < 2:
        return Check("determinism", "SKIP", "pass --output more than once to compare runs"), ""
    raw = [hashlib.sha256(Path(p).read_bytes()).hexdigest()[:12] for p, _, _ in outputs]
    canon = [hashlib.sha256(repr((sorted(c), canonical_table(c, r))).encode()).hexdigest()[:12]
             for _, c, r in outputs]
    names = [Path(p).name for p, _, _ in outputs]
    if len(set(canon)) == 1:
        same_bytes = len(set(raw)) == 1
        return Check("determinism", "PASS",
                     f"{len(outputs)} runs identical" + ("" if same_bytes else
                     " after sorting rows/columns (row order or formatting of the file differs)"),
                     {"runs": names, "raw_sha": raw, "canonical_sha": canon}), ""
    # side-by-side diff against run 1
    p0, c0, r0 = outputs[0]
    key = CONTRACT["key"]
    lines = [f"# Determinism diff\n\nReference run: `{Path(p0).name}`\n"]
    base = {norm_text(r.get(key)): r for r in r0}
    total = 0
    for p, c, rows in outputs[1:]:
        lines.append(f"\n## `{Path(p0).name}` vs `{Path(p).name}`\n")
        if sorted(c) != sorted(c0):
            lines.append(f"Columns differ: {sorted(c0)} vs {sorted(c)}\n")
        lines.append("| order_id | column | run 1 | this run |\n|---|---|---|---|")
        other = {norm_text(r.get(key)): r for r in rows}
        for oid in sorted(set(base) | set(other), key=lambda s: (out_int(s) or 0, s)):
            a, b = base.get(oid), other.get(oid)
            if a is None or b is None:
                lines.append(f"| {oid} | (row) | {'present' if a else 'missing'} | {'present' if b else 'missing'} |")
                total += 1
                continue
            for col in sorted(set(c0) | set(c)):
                if norm_text(a.get(col)) != norm_text(b.get(col)):
                    lines.append(f"| {oid} | {col} | `{a.get(col)}` | `{b.get(col)}` |")
                    total += 1
    return Check("determinism", "FAIL", f"runs differ in {total} cells/rows; see diff",
                 {"runs": names, "canonical_sha": canon}), "\n".join(lines) + "\n"


# --- driver -------------------------------------------------------------------------

def validate(case: str, input_path: str, output_paths: list[str],
             baseline_path: str = str(DEFAULT_BASELINE)) -> dict:
    in_cols, in_rows = read_csv(input_path)
    base_cols, base_rows = read_csv(baseline_path)
    truth = clean_rows(base_rows)
    source_ids = {norm_text(r.get(CONTRACT["key"])) for r in base_rows}

    checks = check_input(in_cols, in_rows, base_cols, base_rows)
    outputs = [(p, *read_csv(p)) for p in output_paths]
    if outputs:
        _, out_cols, out_rows = outputs[0]
        checks += check_output(out_cols, out_rows, truth, source_ids)
    else:
        checks.append(Check("output.rows", "SKIP", "no --output given (input profiling only)"))
    det, diff_md = check_determinism(outputs)
    checks.append(det)

    counts = {s: sum(c.status == s for c in checks) for s in ("PASS", "WARN", "FAIL", "SKIP")}
    return {
        "case": case,
        "input": str(input_path),
        "outputs": [str(p) for p in output_paths],
        "validated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "summary": counts,
        "verdict": "FAIL" if counts["FAIL"] else "WARN" if counts["WARN"] else "PASS",
        "checks": [asdict(c) for c in checks],
        "_determinism_diff": diff_md,
    }


def to_markdown(report: dict) -> str:
    icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "SKIP": "⏭️"}
    s = report["summary"]
    lines = [f"# Validation: `{report['case']}` — {icon[report['verdict']]} {report['verdict']}",
             "",
             f"- Input: `{report['input']}`",
             f"- Outputs: {', '.join(f'`{o}`' for o in report['outputs']) or '(none)'}",
             f"- {s['PASS']} pass, {s['WARN']} warn, {s['FAIL']} fail, {s['SKIP']} skipped",
             "", "| Check | Result | Detail |", "|---|---|---|"]
    for c in report["checks"]:
        msg = c["message"].replace("|", "\\|")
        lines.append(f"| `{c['id']}` | {icon[c['status']]} {c['status']} | {msg} |")
    fails = [c for c in report["checks"] if c["status"] == "FAIL" and c["details"]]
    if fails:
        lines += ["", "## Failure details", ""]
        for c in fails:
            lines += [f"### `{c['id']}`", "```json", json.dumps(c["details"], indent=2, default=str)[:3000], "```", ""]
    return "\n".join(lines) + "\n"


def write_reports(report: dict, report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    diff = report.pop("_determinism_diff", "")
    (report_dir / f"{report['case']}.json").write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    (report_dir / f"{report['case']}.md").write_text(to_markdown(report), encoding="utf-8")
    if diff:
        (report_dir / f"{report['case']}.determinism-diff.md").write_text(diff, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate a Rhombus AI GCS output against its S3 input.")
    ap.add_argument("--case", required=True, help="drift case name, e.g. baseline, schema_rename_column")
    ap.add_argument("--input", required=True, help="the CSV that was uploaded to S3 for this run")
    ap.add_argument("--output", action="append", default=[],
                    help="CSV downloaded from GCS; repeat for repeated runs (determinism)")
    ap.add_argument("--baseline", default=str(DEFAULT_BASELINE), help="baseline source CSV")
    ap.add_argument("--report-dir", default=str(HERE / "reports"))
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    report = validate(a.case, a.input, a.output, a.baseline)
    md = to_markdown(report)
    write_reports(report, Path(a.report_dir))
    if not a.quiet:
        print(md)
    return 1 if report["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
