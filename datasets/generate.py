#!/usr/bin/env python3
"""Generate the messy baseline orders CSV and every drift variant.

Deterministic: the same seed always produces byte-identical files, so anyone
can regenerate /datasets and get exactly what was uploaded to S3.

    python datasets/generate.py            # writes into datasets/
    python datasets/generate.py --check    # fails if committed files differ

Baseline contract (what the *clean* data means):
  order_id     integer, unique
  customer_name text
  email        text (lowercase, valid or empty)
  country      ISO-3166 alpha-2 (AU, US, GB, NZ, CA)
  order_date   US-style MM/DD/YYYY in the source, 2025-01-01..2025-03-31
  quantity     positive integer
  amount_usd   order total in US DOLLARS (not cents)
  status       pending | shipped | delivered | cancelled
"""
from __future__ import annotations

import argparse
import csv
import io
import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SEED = 20251006
OUT_DIR = Path(__file__).resolve().parent
COLUMNS = ["order_id", "customer_name", "email", "country", "order_date",
           "quantity", "amount_usd", "status"]

FIRST = ["olivia", "liam", "noah", "emma", "ava", "mia", "lucas", "zoe",
         "ethan", "harper", "james", "amelia", "leo", "isla", "jack", "chloe",
         "henry", "grace", "oscar", "ruby", "arjun", "mei", "sofia", "kai"]
LAST = ["smith", "nguyen", "patel", "brown", "wilson", "taylor", "singh",
        "chen", "martin", "lee", "walker", "o'brien", "garcia", "kim"]
COUNTRY_VARIANTS = {
    "AU": ["Australia", "AU", "australia ", "AUS", " Aus"],
    "US": ["United States", "USA", "us", "U.S.", "United States of America"],
    "GB": ["United Kingdom", "UK", "GB", "england", "Great Britain"],
    "NZ": ["New Zealand", "NZ", "nz"],
    "CA": ["Canada", "CA", "canada "],
}
STATUS_VARIANTS = {
    "pending": ["pending", "Pending", "PENDING "],
    "shipped": ["shipped", "Shipped", " SHIPPED"],
    "delivered": ["delivered", "Delivered"],
    "cancelled": ["cancelled", "Canceled", "CANCELLED"],
}
START = date(2025, 1, 1)
N_ORDERS = 60


def _messy_name(rng: random.Random, first: str, last: str) -> str:
    name = f"{first} {last}"
    style = rng.random()
    if style < 0.35:
        name = name.title()
    elif style < 0.5:
        name = name.upper()
    elif style < 0.6:
        name = f"  {name.title()} "
    elif style < 0.7:
        name = name.title().replace(" ", "  ")
    return name


def _messy_date(rng: random.Random, d: date) -> str:
    r = rng.random()
    if r < 0.75:
        return d.strftime("%m/%d/%Y")          # canonical US format
    if r < 0.85:
        return d.strftime("%-m/%-d/%Y")        # no zero padding
    if r < 0.95:
        return d.isoformat()                   # ISO
    return d.strftime("%b %d %Y")              # "Jan 14 2025"


def _messy_amount(rng: random.Random, amount: float) -> str:
    r = rng.random()
    if r < 0.55:
        return f"{amount:.2f}"
    if r < 0.75:
        return f"${amount:,.2f}"
    if r < 0.85:
        return f" {amount:.1f} "
    return f"{amount:,.2f}"


def build_baseline(rng: random.Random) -> tuple[list[dict], list[dict]]:
    """Returns (rows_as_written, truth) where truth holds the intended values."""
    rows: list[dict] = []
    truth: list[dict] = []
    for i in range(N_ORDERS):
        oid = 1001 + i
        first, last = rng.choice(FIRST), rng.choice(LAST)
        country = rng.choice(list(COUNTRY_VARIANTS))
        status = rng.choice(list(STATUS_VARIANTS))
        d = START + timedelta(days=rng.randrange(0, 90))
        qty = rng.randint(1, 6)
        amount = round(qty * rng.uniform(8, 180), 2)
        email = f"{first}.{last}@example.com".replace("'", "")
        truth.append(dict(order_id=oid, customer_name=f"{first} {last}".title(),
                          email=email, country=country, order_date=d,
                          quantity=qty, amount_usd=amount, status=status))
        rows.append(dict(
            order_id=str(oid),
            customer_name=_messy_name(rng, first, last),
            email=email.upper() if rng.random() < 0.2 else email,
            country=rng.choice(COUNTRY_VARIANTS[country]),
            order_date=_messy_date(rng, d),
            quantity=str(qty) if rng.random() < 0.9 else f" {qty}",
            amount_usd=_messy_amount(rng, amount),
            status=rng.choice(STATUS_VARIANTS[status]),
        ))

    # --- deliberate defects (fixed positions so they are documented) -------
    rows[3]["email"] = "lucas.chen.at.example.com"   # invalid email
    rows[7]["email"] = ""                            # missing email
    rows[11]["customer_name"] = ""                   # missing name
    rows[14]["quantity"] = "-2"                      # invalid quantity
    rows[18]["quantity"] = "two"                     # non-numeric quantity
    rows[22]["amount_usd"] = ""                      # missing amount
    rows[25]["amount_usd"] = "-35.00"                # negative amount
    rows[29]["order_date"] = "13/45/2025"            # impossible date
    rows[33]["order_date"] = ""                      # missing date
    rows[37]["country"] = ""                         # missing country
    rows[41]["status"] = "N/A"                       # invalid status
    rows[44]["email"] = "N/A"                        # placeholder email

    # duplicates: 5 exact copies + 3 near-duplicates (same order_id, messier)
    dupes = [dict(rows[i]) for i in (2, 9, 16, 30, 47)]
    near = []
    for i in (5, 20, 52):
        r = dict(rows[i])
        r["customer_name"] = f"  {r['customer_name'].strip().lower()}  "
        r["status"] = r["status"].strip().upper()
        near.append(r)
    all_rows = rows + dupes + near
    # stable shuffle so duplicates are not adjacent
    order = list(range(len(all_rows)))
    rng.shuffle(order)
    return [all_rows[i] for i in order], truth


def _to_csv(rows: list[dict], columns: list[str]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n",
                       extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in columns})
    return buf.getvalue()


def _parse_us(s: str) -> date | None:
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%b %d %Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


# --- drift variants --------------------------------------------------------

def drop_column(rows):
    cols = [c for c in COLUMNS if c != "country"]
    return rows, cols


def rename_column(rows):
    out = [{("total_amount" if k == "amount_usd" else k): v for k, v in r.items()}
           for r in rows]
    cols = ["total_amount" if c == "amount_usd" else c for c in COLUMNS]
    return out, cols


def change_type(rows):
    """order_date: text date -> integer Unix epoch seconds (UTC midnight)."""
    out = []
    for r in rows:
        r = dict(r)
        d = _parse_us(r["order_date"])
        r["order_date"] = (str(int(datetime(d.year, d.month, d.day,
                                            tzinfo=timezone.utc).timestamp()))
                           if d else r["order_date"])
        out.append(r)
    return out, COLUMNS


def add_column(rows, rng: random.Random):
    codes = ["", "", "", "SPRING10", "spring10", " WELCOME5", "N/A", "FREESHIP"]
    out = []
    for r in rows:
        r = dict(r)
        r["discount_code"] = rng.choice(codes)
        out.append(r)
    cols = COLUMNS[:6] + ["discount_code"] + COLUMNS[6:]   # added mid-file
    return out, cols


def combined(rows, rng: random.Random):
    rows, _ = change_type(rows)
    rows, _ = add_column(rows, rng)
    rows, _ = rename_column(rows)
    cols = [c for c in COLUMNS if c != "country"]
    cols = ["total_amount" if c == "amount_usd" else c for c in cols]
    cols = cols[:5] + ["discount_code"] + cols[5:]
    return rows, cols


def semantic_cents(rows):
    """amount_usd now holds CENTS, same header, same text type."""
    out = []
    for r in rows:
        r = dict(r)
        raw = r["amount_usd"].replace("$", "").replace(",", "").strip()
        try:
            r["amount_usd"] = str(int(round(float(raw) * 100)))
        except ValueError:
            pass  # keep the original defect as-is
        out.append(r)
    return out, COLUMNS


def semantic_ddmm(rows):
    """Every slash date flips to DD/MM/YYYY (e.g. upstream locale change)."""
    out = []
    for r in rows:
        r = dict(r)
        s = r["order_date"].strip()
        if "/" in s:
            try:
                d = datetime.strptime(s, "%m/%d/%Y").date()
                r["order_date"] = d.strftime("%d/%m/%Y")
            except ValueError:
                pass
        out.append(r)
    return out, COLUMNS


def build_all() -> dict[str, str]:
    rng = random.Random(SEED)
    base, _ = build_baseline(rng)
    files = {"orders_baseline.csv": _to_csv(base, COLUMNS)}
    variants = {
        "orders_schema_drop_column.csv": drop_column(base),
        "orders_schema_rename_column.csv": rename_column(base),
        "orders_schema_type_change.csv": change_type(base),
        "orders_schema_add_column.csv": add_column(base, random.Random(SEED + 1)),
        "orders_schema_combined.csv": combined(base, random.Random(SEED + 1)),
        "orders_semantic_cents.csv": semantic_cents(base),
        "orders_semantic_date_ddmm.csv": semantic_ddmm(base),
    }
    for name, (rows, cols) in variants.items():
        files[name] = _to_csv(rows, cols)
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="verify committed files match the generator")
    args = ap.parse_args()
    files = build_all()
    stale = []
    for name, content in files.items():
        path = OUT_DIR / name
        if args.check:
            if not path.exists() or path.read_text() != content:
                stale.append(name)
        else:
            path.write_text(content)
            print(f"wrote {path.relative_to(OUT_DIR.parent)} "
                  f"({content.count(chr(10)) - 1} rows)")
    if stale:
        print("out of date: " + ", ".join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
