#!/usr/bin/env python3
"""Reference implementation of the cleaning rules given to the Rhombus AI builder.

This is the oracle: it turns the *baseline* source file into what a correct
pipeline should write to GCS. validate.py compares every Rhombus output
(baseline and drifted runs) with it, because in every drift case the
underlying orders are the same; only their shape or meaning changed.

Rules (identical to the prompt in README.md, keep them in sync):
  1. Trim text and collapse repeated inner spaces.
  2. Drop exact duplicate rows, then keep the first row per order_id.
  3. customer_name -> Title Case; empty -> "Unknown".
  4. email -> lowercase; invalid or placeholder -> empty.
  5. country -> ISO-3166 alpha-2 (AU, US, GB, NZ, CA); unknown/empty -> empty.
  6. order_date -> YYYY-MM-DD, source is MM/DD/YYYY (also ISO and "Jan 14 2025");
     unparseable or empty -> drop the row.
  7. quantity -> integer; non-numeric or <= 0 -> drop the row.
  8. amount_usd -> number with 2 decimals, strip "$" and ","; empty, negative or
     non-numeric -> drop the row.
  9. status -> lowercase; "canceled" -> "cancelled"; anything else outside
     pending/shipped/delivered/cancelled -> "unknown".
"""
from __future__ import annotations

import csv
import re
import sys
from datetime import date, datetime
from pathlib import Path

EMAIL_RE = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$")
COUNTRY_MAP = {
    "au": "AU", "aus": "AU", "australia": "AU",
    "us": "US", "usa": "US", "u.s.": "US", "u.s.a.": "US",
    "united states": "US", "united states of america": "US",
    "gb": "GB", "uk": "GB", "u.k.": "GB", "united kingdom": "GB",
    "great britain": "GB", "england": "GB",
    "nz": "NZ", "new zealand": "NZ",
    "ca": "CA", "canada": "CA",
}
STATUS_MAP = {"pending": "pending", "shipped": "shipped",
              "delivered": "delivered", "cancelled": "cancelled",
              "canceled": "cancelled"}
OUTPUT_COLUMNS = ["order_id", "customer_name", "email", "country",
                  "order_date", "quantity", "amount_usd", "status"]


def norm_text(v: str | None) -> str:
    return re.sub(r"\s+", " ", (v or "").strip())


def parse_source_date(v: str) -> date | None:
    v = norm_text(v)
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%b %d %Y"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            pass
    return None


def parse_money(v: str) -> float | None:
    v = norm_text(v).replace("$", "").replace(",", "")
    try:
        return float(v)
    except ValueError:
        return None


def parse_int(v: str) -> int | None:
    v = norm_text(v)
    return int(v) if re.fullmatch(r"-?\d+", v) else None


def clean_rows(rows: list[dict]) -> list[dict]:
    seen_exact: set[tuple] = set()
    seen_ids: set[str] = set()
    out: list[dict] = []
    for raw in rows:
        exact = tuple(sorted(raw.items()))
        if exact in seen_exact:
            continue
        seen_exact.add(exact)
        oid = norm_text(raw.get("order_id"))
        if oid in seen_ids:
            continue
        seen_ids.add(oid)

        d = parse_source_date(raw.get("order_date", ""))
        qty = parse_int(raw.get("quantity", ""))
        amount = parse_money(raw.get("amount_usd", ""))
        if d is None or qty is None or qty <= 0 or amount is None or amount < 0:
            continue

        email = norm_text(raw.get("email")).lower()
        status = STATUS_MAP.get(norm_text(raw.get("status")).lower(), "unknown")
        out.append({
            "order_id": oid,
            "customer_name": norm_text(raw.get("customer_name")).title() or "Unknown",
            "email": email if EMAIL_RE.match(email) else "",
            "country": COUNTRY_MAP.get(norm_text(raw.get("country")).lower(), ""),
            "order_date": d.isoformat(),
            "quantity": str(qty),
            "amount_usd": f"{amount:.2f}",
            "status": status,
        })
    return out


def read_csv(path: str | Path) -> tuple[list[str], list[dict]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: reference_clean.py <source.csv> <expected_out.csv>", file=sys.stderr)
        return 2
    _, rows = read_csv(sys.argv[1])
    cleaned = clean_rows(rows)
    with open(sys.argv[2], "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(cleaned)
    print(f"{len(rows)} source rows -> {len(cleaned)} clean rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
