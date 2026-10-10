# Schema drift: add column (`discount_code`)

## What I changed

- Source file: `datasets/orders_schema_add_column.csv`. It has the same 68 rows as the baseline plus a new column, `discount_code`, between `quantity` and `amount_usd` (9 columns instead of 8).
- The new column is messy on purpose: `WELCOME5` (with a leading space), `FREESHIP`, `SPRING10` and `spring10`, `N/A`, or empty (47 of 68 rows have a value).
- Uploaded to S3 as `rhombus/orders.csv` at 2026-10-10 05:39 UTC (16:39 local). S3 showed 5.5 KB.
- Pipeline: the baseline pipeline, plus the dual-format date fix kept from the type change test (see `schema-type-change.md`).

## What I expected

The pipeline only picks the 8 known columns, so it ignores `discount_code` and the output matches the baseline.

## How to repeat it

1. Start from the working baseline pipeline.
2. Upload `datasets/orders_schema_add_column.csv` to S3 as `rhombus/orders.csv`.
3. Press Run. Scheduled runs do not pick up a changed source file (see `schema-drop-column.md`), so the run was manual.

## What happened

- Time: 05:39 UTC (16:39 local).
- Status: succeeded with no warning. Output `RhombusAI_output_1791610758314.csv` (4 KB) was written to GCS.
- The output is byte-for-byte identical to the baseline output 6: 54 rows, the same 8 columns, the same values.
- `discount_code` is not in the output. The column order shift in the source did not break anything, because the pipeline reads columns by name.
- Rhombus did not say anywhere that a new column appeared. It was dropped silently.

Output: `runs/schema_add_column/run1.csv`

## What the logs said

Nothing. The run succeeded and no message mentioned `discount_code`.

## What the chatbot said, and did its fix work?

Not used. The run succeeded and the output was correct, so there was nothing to fix.

## What happened to the schedule

Not tested separately: scheduled runs do not pick up source changes (see `schema-drop-column.md`). The schedule is still on.

## Restoring the baseline

Not needed. The pipeline was not changed in this test.

## Data validation result

```bash
python data-validation/validate.py --case schema_add_column --input datasets/orders_schema_add_column.csv --output runs/schema_add_column/run1.csv
```

````
# Validation: `schema_add_column`: ❌ FAIL

- Input: `datasets/orders_schema_add_column.csv`
- Outputs: `runs/schema_add_column/run1.csv`
- 22 pass, 1 warn, 1 fail, 1 skipped

| Check | Result | Detail |
|---|---|---|
| `input.schema` | ⚠️ WARN | schema drift: missing=[] added=['discount_code'] |
| `input.types` | ✅ PASS | column types match the baseline |
| `input.amount_scale` | ✅ PASS | median amount_usd is 1.0x the baseline |
| `input.date_order` | ✅ PASS | 1 slash dates have a first part > 12 vs 39 with a second part > 12: dates look MM/DD |
| `output.schema` | ✅ PASS | output columns match the contract |
| `output.rows` | ✅ PASS | 54 rows, expected 54 |
| `rule.trimmed` | ✅ PASS | text is trimmed |
| `rule.name_title_case` | ✅ PASS | customer_name is Title Case and never empty |
| `rule.email` | ✅ PASS | email is lowercase and valid, or empty |
| `rule.country_iso2` | ✅ PASS | country is one of ['AU', 'CA', 'GB', 'NZ', 'US'] or empty |
| `rule.date_iso` | ✅ PASS | order_date is YYYY-MM-DD |
| `rule.quantity_positive_int` | ❌ FAIL | 54/54 rows break: quantity is a positive integer |
| `rule.amount_2dp` | ✅ PASS | amount_usd is a non-negative number, at most 2 decimals, no symbols |
| `rule.status` | ✅ PASS | status is one of ['cancelled', 'delivered', 'pending', 'shipped', 'unknown'] |
| `values.customer_name` | ✅ PASS | all 54 matched rows agree with the reference |
| `values.email` | ✅ PASS | all 54 matched rows agree with the reference |
| `values.country` | ✅ PASS | all 54 matched rows agree with the reference |
| `values.order_date` | ✅ PASS | all 54 matched rows agree with the reference |
| `values.quantity` | ✅ PASS | all 54 matched rows agree with the reference |
| `values.amount_usd` | ✅ PASS | all 54 matched rows agree with the reference |
| `values.status` | ✅ PASS | all 54 matched rows agree with the reference |
| `semantic.date_window` | ✅ PASS | all dates inside 2025-01-01..2025-03-31 |
| `semantic.amount_scale` | ✅ PASS | median amount_usd = 191.16 (expected 10..1000 dollars) |
| `semantic.unit_price` | ✅ PASS | 0/54 implied unit prices outside $5..$250 |
| `determinism` | ⏭️ SKIP | pass --output more than once to compare runs |
````

- The validator flagged the new column in the input (`input.schema` warning). Rhombus did not.
- Everything in the output is correct. `rule.quantity_positive_int` fails for the same reason as the baseline (`2.0`), not because of this drift.

## Verdict

- Pipeline stopped: no, and it did not need to.
- Chatbot fix needed: no.
- Severity: Low
- Summary: This is the one schema change Rhombus handled cleanly. The output was identical to the baseline, because the pipeline picks its 8 columns by name and ignores anything else. The only gap is visibility: a new column in the source is dropped without any notice, so a user would never learn that new data (here, discount codes on 47 of 68 orders) is arriving and being thrown away.
