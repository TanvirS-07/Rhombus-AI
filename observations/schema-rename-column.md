# Schema drift: rename column (`amount_usd` to `total_amount`)

## Summary

Severity: High

The first run failed. The "Ask Chatbot" fix allowed the run to succeed, but the output had no amount column and kept 2 invalid orders. The second fix worked, but only after I identified the rename myself.

### Main findings

1. The chatbot treated `amount_usd` as missing and did not notice the new `total_amount` column.
2. After its fix, the run was reported as successful with no amount column and 56 rows instead of 54 (invalid orders 1023 and 1026 were kept).
3. The fix changed the pipeline to skip any missing column, so other schema changes would also pass without an error.
4. The error message only shows `'amount_usd'` followed by the generated code. It does not mention the new column.

### Runs

- First run: failed, no file written
- After fix 1: success, 56 rows, no amount column (`runs/schema_rename_column/run1.csv`)
- After fix 2 (with my hint): identical to the baseline (`run2-fixed.csv`)
- After the restore: identical to the baseline (`restored.csv`)

---

## What I changed

- Source file: `datasets/orders_schema_rename_column.csv`. It has the same 68 rows and 8 columns as the baseline, but `amount_usd` is renamed to `total_amount`. The values are unchanged.
- Uploaded to S3 as `rhombus/orders.csv` at 2026-10-10 04:28 UTC (15:28 local).
- Pipeline: the baseline pipeline, restored after the drop-column test (see `schema-drop-column.md`).

## What I expected

It will fail like drop column, because `orders_cleaned` uses `amount_usd`.

## How to repeat it

1. Start from the working baseline pipeline.
2. Upload `datasets/orders_schema_rename_column.csv` to S3 as `rhombus/orders.csv`.
3. Press Run. Scheduled runs do not pick up a changed source file (see `schema-drop-column.md`), so all runs in this test were manual.

## What happened

### 1. First run: failed

- Time: about 04:29 UTC (15:29 local).
- Status: failed at `orders_cleaned`. No file was written to GCS.
- The run page showed the error and an "Ask Chatbot" button.

### 2. After the chatbot's first fix: succeeded, but with the wrong data

- Time: 04:33 UTC (15:33 local). Output `RhombusAI_output_1791606782152.csv` (3.8 KB) was written to GCS.
- Status: success, with no warning.
- The output had **no amount column at all**: 7 columns, with neither `amount_usd` nor `total_amount`. All the money data was lost.
- It had **56 rows instead of 54**. Orders 1023 (empty amount) and 1026 (amount -35.00) were kept, because the amount checks were now skipped.

Output: `runs/schema_rename_column/run1.csv`

### 3. After the second fix (with my hint): correct

- Time: 04:35 UTC (15:35 local). Output `RhombusAI_output_1791606934182.csv` (4 KB).
- Byte-for-byte identical to the baseline output 6: 54 rows, 8 columns, `amount_usd` correct, 1023 and 1026 removed.

Output: `runs/schema_rename_column/run2-fixed.csv`

## What the logs said

```
Pipeline failed at orders_cleaned: LLM execution failed (code_sha=cf671a772d83): 'amount_usd'
--- Generated code ---
import pandas as pd
...
```

- Like the drop-column test, the only clue is `'amount_usd'` before a long dump of generated code.
- It does not say the column is missing, and it does not notice that a new column `total_amount` appeared.
- The `code_sha` (`cf671a772d83`) differs from the drop-column test (`f2e71501b508`). The chatbot's earlier "restore" regenerated the node's code rather than putting the old code back.

Evidence: `observations/evidence/schema-rename-column/schema-rename-column-error.txt`

## What the chatbot said, and did its fix work?

### Fix 1: "Ask Chatbot" button

I used the "Ask Chatbot" button on the error. The chatbot said it made `orders_cleaned` "schema-resilient": every cleaning step and drop condition is now skipped if its column is missing, and the output only includes columns that are present "in canonical order".

- Diagnosis: wrong. It treated `amount_usd` as missing and never noticed the rename to `total_amount`.
- Did the fix work: no. The run succeeded, but the amount column was missing and 2 invalid orders were kept. A failed run became a successful run with incorrect data.
- It also changed the pipeline in a general way: any missing column would now be skipped instead of failing the run.

Evidence: `observations/evidence/schema-rename-column/schema-rename-column-chatbot.txt`

### Fix 2: after I named the rename

I told it: "The output has no amount column and kept orders 1023 and 1026. The source column amount_usd was renamed to total_amount. Read total_amount as amount_usd and keep amount_usd in the output."

It added a step at the start of `orders_trimmed` that renames `total_amount` to `amount_usd`, and skips the rename if the column is already `amount_usd`.

- Did the fix work: yes. The output matched the baseline exactly.
- But it only got there because I diagnosed the problem myself.

Evidence: `observations/evidence/schema-rename-column/schema-rename-column-chatbot-2.txt`

## What happened to the schedule

Not tested separately: scheduled runs do not pick up source changes (see `schema-drop-column.md`). The schedule is still on.

## Restoring the baseline

I asked the chatbot to remove the rename step and the column-existence checks, uploaded `datasets/orders_baseline.csv`, and pressed Run at 04:41 UTC (15:41 local). The output was byte-for-byte identical to output 6.

The chatbot said both nodes were restored: `orders_trimmed` does "trim/collapse spaces + currency strip only, and no rename logic", and `orders_cleaned` has "full 8-column cleaning with hard references to all columns a missing column will fail the run". Note: before the tests, `orders_trimmed` only trimmed spaces, so "currency strip" may mean the restored node is not exactly the same as before, even though the output matched.

Evidence: `observations/evidence/schema-rename-column/schema-rename-column-chatbot-restore.txt`

Output: `runs/schema_rename_column/restored.csv`

## Data validation result

```bash
python data-validation/validate.py --case schema_rename_column --input datasets/orders_schema_rename_column.csv --output runs/schema_rename_column/run1.csv
```

````
# Validation: `schema_rename_column` — ❌ FAIL

- Input: `datasets/orders_schema_rename_column.csv`
- Outputs: `runs/schema_rename_column/run1.csv`
- 16 pass, 1 warn, 3 fail, 3 skipped

| Check | Result | Detail |
|---|---|---|
| `input.schema` | ⚠️ WARN | schema drift: missing=['amount_usd'] added=['total_amount'] likely renames={'amount_usd': 'total_amount'} |
| `input.types` | ✅ PASS | column types match the baseline |
| `input.amount_scale` | ✅ PASS | median total_amount is 1.0x the baseline |
| `input.date_order` | ✅ PASS | 1 slash dates have a first part > 12 vs 39 with a second part > 12: dates look MM/DD |
| `output.schema` | ❌ FAIL | missing=['amount_usd'] unexpected=[] |
| `output.rows` | ❌ FAIL | 56 rows, expected 54; duplicates=[] invented=[] dropped_valid=[] kept_invalid=['1023', '1026'] |
| `rule.trimmed` | ✅ PASS | text is trimmed |
| `rule.name_title_case` | ✅ PASS | customer_name is Title Case and never empty |
| `rule.email` | ✅ PASS | email is lowercase and valid, or empty |
| `rule.country_iso2` | ✅ PASS | country is one of ['AU', 'CA', 'GB', 'NZ', 'US'] or empty |
| `rule.date_iso` | ✅ PASS | order_date is YYYY-MM-DD |
| `rule.quantity_positive_int` | ❌ FAIL | 56/56 rows break: quantity is a positive integer |
| `rule.amount_2dp` | ⏭️ SKIP | column amount_usd not in output |
| `rule.status` | ✅ PASS | status is one of ['cancelled', 'delivered', 'pending', 'shipped', 'unknown'] |
| `values.customer_name` | ✅ PASS | all 54 matched rows agree with the reference |
| `values.email` | ✅ PASS | all 54 matched rows agree with the reference |
| `values.country` | ✅ PASS | all 54 matched rows agree with the reference |
| `values.order_date` | ✅ PASS | all 54 matched rows agree with the reference |
| `values.quantity` | ✅ PASS | all 54 matched rows agree with the reference |
| `values.amount_usd` | ⏭️ SKIP | amount_usd not in output |
| `values.status` | ✅ PASS | all 54 matched rows agree with the reference |
| `semantic.date_window` | ✅ PASS | all dates inside 2025-01-01..2025-03-31 |
| `determinism` | ⏭️ SKIP | pass --output more than once to compare runs |
````

- My validator spotted the rename (`likely renames={'amount_usd': 'total_amount'}`), which the chatbot missed.
- It caught the problems the run status did not show: the missing amount column (`output.schema`) and the 2 invalid orders that were kept (`output.rows`).
- `rule.quantity_positive_int` fails for the same reason as the baseline (`2.0`).
