# Schema drift: combined (drop, rename, type change and add column)

## Summary

Severity: High

The first run failed on the missing `country` column. Two rounds of "Ask Chatbot" did not fix it. Both times the chatbot re-locked the existing code, reported that the pipeline was ready, and attributed the failure to the scheduler. A fix only worked after I described all 4 changes myself. That fix also kept the original file working.

### Main findings

1. "Ask Chatbot" did not address the error in either round. It never mentioned `country` and the same `'country'` error came back after each fix.
2. The chatbot blamed the scheduler for regenerating the code, but both runs were manual. It recommended raising a bug with Rhombus support instead of fixing the pipeline.
3. The error message was the same as in the drop column test: `'country'` followed by generated code. It did not mention the other 3 changes.
4. With my hint, the chatbot handled all 4 changes in one update, and the original file still produced the baseline output.

### Runs

- First run: failed, no file written
- After Ask Chatbot fix 1: failed with the same error
- After Ask Chatbot fix 2: failed with the same error
- After my hint: success, 54 rows, 8 columns, `country` empty (`runs/schema_combined/run1-fixed.csv`)
- Original file with the hint fix in place: identical to the baseline (`restored.csv`)

---

## What I changed

- Source file: `datasets/orders_schema_combined.csv`. It has the same 68 rows as the baseline with 4 changes at once:
  - `country` removed
  - `amount_usd` renamed to `total_amount`
  - `order_date` changed to a Unix timestamp in seconds
  - new `discount_code` column added
- Uploaded to S3 as `rhombus/orders.csv` at 2026-10-10 05:52 UTC (16:52 local). S3 showed 5.1 KB.
- Pipeline: the baseline pipeline, including the dual-format date fix kept from the type change test (see `schema-type-change.md`). The rename handling from the rename test had been removed during that restore.

## What I expected

The run will fail on the first missing column, probably country as in the drop column test.

## How to repeat it

1. Start from the working baseline pipeline.
2. Upload `datasets/orders_schema_combined.csv` to S3 as `rhombus/orders.csv`.
3. Press Run. Scheduled runs do not pick up a changed source file (see `schema-drop-column.md`), so all runs in this test were manual.
4. Use "Ask Chatbot" on the error for up to 2 rounds without any hint, then send a hint that names the changes.

## What happened

### 1. First run: failed

- Time: about 05:53 UTC (16:53 local).
- Status: failed at `orders_cleaned` with `'country'`. No file was written to GCS.

### 2. After Ask Chatbot fix 1: failed again

- The chatbot re-locked the node code and said it was patched. It did not change the `country` handling.
- Time: about 05:55 UTC (16:55 local).
- Status: failed at `orders_cleaned` with the same `'country'` error and a new code_sha.

### 3. After Ask Chatbot fix 2: failed again

- The chatbot again re-locked the code and said "The pipeline is ready to run".
- The next run failed with the same `'country'` error, so I stopped the unhinted rounds and sent a hint instead.

### 4. After my hint: correct

- Time: 05:56 UTC (16:56 local). Output `RhombusAI_output_1791611811414.csv` (3.9 KB).
- 54 rows and 8 columns. `country` is empty on every row, as requested. All other columns are identical to the baseline output 6: amounts were read from `total_amount`, timestamps were converted to dates, and `discount_code` was not included.

Output: `runs/schema_combined/run1-fixed.csv`

## What the logs said

```
Pipeline failed at orders_cleaned: LLM execution failed (code_sha=6ec3a222a8c9): 'country'
--- Generated code ---
import pandas as pd
...
```

- The second run gave the same error with code_sha `2644381134f1`.
- As in the drop column test, the only reference to the problem is `'country'` before the generated code.
- The error only reports the first problem the code reached. It gives no indication that 3 other columns had also changed.

Evidence: `observations/evidence/schema-combined/schema-combined-error.txt`

## What the chatbot said, and did its fix work?

### Fix 1: "Ask Chatbot" button

The chatbot said: "Re-locked. The code is patched back in with mode: code." It then said the new code_sha "confirms the LLM node is regenerating fresh code on every scheduled run, ignoring the locked code entirely", and recommended raising this with Rhombus support.

- Diagnosis: incorrect. The run was manual, not scheduled, and the error was caused by the missing `country` column, which it did not mention. The code_sha had already changed for a known reason, the date fix added in the type change test (inferred, not confirmed).
- Did the fix work: no. The next run failed with the same error.

Evidence: `observations/evidence/schema-combined/schema-combined-chatbot.txt`

### Fix 2: "Ask Chatbot" button again

The chatbot said: "Re-locked. The pipeline is ready to run." It added that this was "the third time the scheduled runner has regenerated a different code_sha" and again recommended contacting Rhombus support.

- Diagnosis: the same as fix 1. It repeated the scheduler explanation and again did not mention `country`.
- Did the fix work: no. The next run failed with the same error.

Evidence: `observations/evidence/schema-combined/schema-combined-chatbot-2.txt`

### Fix 3: after I described the changes

I told it: "/pipeline The source file changed in 4 ways: the country column was removed, amount_usd was renamed to total_amount, order_date is now a Unix timestamp in seconds, and a new discount_code column was added. Read total_amount as amount_usd. If country is missing, output an empty country column. Ignore discount_code. Keep all other cleaning rules, keep the output columns the same as before, and make sure the original file format still works."

It updated `orders_trimmed` to rename `total_amount` to `amount_usd` and drop columns outside the 8-column schema, and updated `orders_cleaned` to add an empty `country` column when it is missing and to parse Unix timestamps before the existing date formats.

- Did the fix work: yes. The output was correct, and the original file still gave the baseline output (see "Restoring the baseline").
- As in the other tests, it only worked after I identified the changes myself.

Evidence: `observations/evidence/schema-combined/schema-combined-chatbot-hint.txt`

## What happened to the schedule

Not tested separately: scheduled runs do not pick up source changes (see `schema-drop-column.md`). The schedule is still on.

## Restoring the baseline

- Uploaded `datasets/orders_baseline.csv` as `rhombus/orders.csv` and pressed Run without changing the pipeline.
- Output `RhombusAI_output_1791612038392.csv` (4 KB) at 06:00 UTC (17:00 local) was byte-for-byte identical to output 6.
- I kept the hint fix for the remaining tests, as it handles both the original and the drifted file.

Output: `runs/schema_combined/restored.csv`

## Data validation result

```bash
python data-validation/validate.py --case schema_combined --input datasets/orders_schema_combined.csv --output runs/schema_combined/run1-fixed.csv
```

````
# Validation: `schema_combined` — ❌ FAIL

- Input: `datasets/orders_schema_combined.csv`
- Outputs: `runs/schema_combined/run1-fixed.csv`
- 20 pass, 2 warn, 2 fail, 1 skipped

| Check | Result | Detail |
|---|---|---|
| `input.schema` | ⚠️ WARN | schema drift: missing=['country', 'amount_usd'] added=['discount_code', 'total_amount'] likely renames={'amount_usd': 'total_amount'} |
| `input.types` | ⚠️ WARN | type drift: {'order_date': 'date -> epoch'} |
| `input.amount_scale` | ✅ PASS | median total_amount is 1.0x the baseline |
| `input.date_order` | ✅ PASS | 1 slash dates have a first part > 12 vs 1 with a second part > 12: dates look MM/DD |
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
| `values.country` | ❌ FAIL | 53/54 rows differ from the reference |
| `values.order_date` | ✅ PASS | all 54 matched rows agree with the reference |
| `values.quantity` | ✅ PASS | all 54 matched rows agree with the reference |
| `values.amount_usd` | ✅ PASS | all 54 matched rows agree with the reference |
| `values.status` | ✅ PASS | all 54 matched rows agree with the reference |
| `semantic.date_window` | ✅ PASS | all dates inside 2025-01-01..2025-03-31 |
| `semantic.amount_scale` | ✅ PASS | median amount_usd = 191.16 (expected 10..1000 dollars) |
| `semantic.unit_price` | ✅ PASS | 0/54 implied unit prices outside $5..$250 |
| `determinism` | ⏭️ SKIP | pass --output more than once to compare runs |
````

- The validator detected all 4 changes in the input, including the rename and the timestamp format. Neither the error message nor the chatbot identified any of them.
- `values.country` fails because the source no longer has country data, so the output column is empty. The one matching row is order 1038, which has no country in the baseline either.
- `rule.quantity_positive_int` fails for the same reason as the baseline (`2.0`).
