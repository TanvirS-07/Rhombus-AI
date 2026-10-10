# Schema drift: drop column (`country`)

## What I changed

- Source file: `datasets/orders_schema_drop_column.csv`. It has the same 68 rows as the baseline, but the `country` column is removed (7 columns instead of 8).
- Uploaded to S3 as `rhombus/orders.csv`, replacing the baseline, at 2026-10-10 03:15:44 UTC (14:15 local). S3 showed 4.6 KB.
- Pipeline not changed before the test.

## What I expected

Rhombus would notice the missing `country` column and either stop the run or warn me. If it carried on, I expected `country` to be empty or missing in the GCS output.

## How to repeat it

1. Start from the working baseline pipeline (see `baseline.md`).
2. Upload `datasets/orders_schema_drop_column.csv` to S3 as `rhombus/orders.csv`.
3. Let the next scheduled run fire and note whether it is skipped.
4. Scheduled runs did not reliably pick up the new file (see below), so later runs were triggered with the manual Run button.

## What happened

### 1. The new file was not picked up straight away

- The scheduled runs at 03:18 UTC and 03:20 UTC (both after the upload) were skipped: "Skipped 3 time(s) in a row due to unchanged data", then "Skipped 4 time(s)".
- The Data Input node preview in the pipeline still showed `country`.
- The dataset view (eye icon in the Data Input settings) showed the new file without `country`.
- So the pipeline was using a stored copy of the S3 file. Viewing the new file did not update it, and the scheduler said "unchanged data" and skipped.

Evidence:
- `observations/evidence/schema-drop-column/schema-drop-column-node-preview.png`
- `observations/evidence/schema-drop-column/schema-drop-column-eye-preview.png`
- `observations/evidence/schema-drop-column/schema-drop-column-skipped.png`

### 2. The first run after the change: failed

- Time: 2026-10-10 03:35 UTC (14:35 local), about 20 minutes after the upload. Just before this run I had opened the node preview and the eye view and asked the chatbot about the skips, so one of those may be what made Rhombus re-read the file.
- Status: failed in the `orders_cleaned` node. Rhombus sent a "Workflow Execution Failed" email.
- No new file was written to GCS.

### 3. After the chatbot's fix: succeeded

- Time: 2026-10-10 03:40 UTC (14:40 local), scheduled run.
- Status: succeeded. Output `RhombusAI_output_1791603618625.csv` (3.8 KB) was written to GCS.
- 54 rows and 7 columns. Apart from the missing `country` column, it is identical to the baseline output (same rows, order and values).
- Rhombus did not add an empty `country` column, so the output columns changed without any warning.

Output: `runs/schema_drop_column/run1.csv`

## What the logs said

The error email said:

`LLM execution failed (code_sha=f2e71501b508): 'country'`

It then included the full generated Python code of the node and a Python traceback ending in `KeyError: 'country'`.

- It does name the missing column, but only as `'country'` and `KeyError: 'country'`, buried after a long code dump.
- It never says in plain words "the column country is missing from the source file".
- The `code_sha` shows the pipeline reruns the same stored code rather than regenerating it.

Evidence: `observations/evidence/schema-drop-column/schema-drop-column-error-email.txt`

## What the chatbot said, and did its fix work?

### Question 1: why were the runs skipped?

The chatbot said Rhombus caches the file's content hash for about 15 minutes, and suggested a manual run or waiting for the cache to expire. It also warned that `orders_cleaned` uses `country` and offered to change that node. I declined, to see what the unchanged pipeline would do.

- Was the 15-minute explanation right: no. The first run after 03:31 UTC did pick up the new file, but when I put the baseline back later, scheduled runs were still skipped 20, 25 and 30 minutes after the upload (see "After putting the baseline back"). Waiting does not refresh the file.

### Question 2: why did the run fail?

I pasted the error. The chatbot said the source lost the `country` column but `orders_cleaned` still tried to use it, causing `KeyError: 'country'`. It removed all country logic from `orders_cleaned` (the country mapping, the cleaning step and `country` in the output columns).

- Diagnosis: correct.
- Did the fix work: yes for the drifted file. The next scheduled run succeeded with 54 correct rows.
- Catch: the fix does not make the pipeline handle a missing column. It removes `country` handling completely, so the pipeline now only fits the drifted file. See "After putting the baseline back" below.
- It suggested a manual Run, but the next scheduled run worked without one.

Evidence: `observations/evidence/schema-drop-column/schema-drop-column-chatbot.txt`

## What happened to the schedule

- It was still on after 4 skips in a row and after the failed run. It was not paused.
- The schedule never picked up a changed source file on its own in a way I could repeat. In a real pipeline, a changed (or broken) source file could go unprocessed for hours, with only "skipped" emails as a hint.

## After putting the baseline back

- Uploaded `datasets/orders_baseline.csv` as `rhombus/orders.csv` at 03:45 UTC (14:45 local).
- Scheduled runs at 04:05, 04:10 and 04:15 UTC were all skipped ("Skipped 1/2/3 time(s) in a row due to unchanged data"), 20 to 30 minutes after the upload. Opening the eye view in between did not help. The node preview still showed the drop-column file without `country`.
- I pressed Run manually at 04:17 UTC. Afterwards the node preview showed the baseline with `country`, so the manual run read the new file.
- But the output had no `country`: 54 rows, 7 columns, identical to the drop-column output. The chatbot's fix silently dropped a valid column from good data, and the run status was success with no warning.
- I asked the chatbot to restore the country cleaning and why it removed the column. It said: "Making the logic conditional on whether country exists at runtime would have been a better long-term approach, I should have offered that instead of silently removing it."
- Manual run at 04:21 UTC: output identical to the baseline output 6 (54 rows, 8 columns). The pipeline was back to baseline.

Outputs: `runs/schema_drop_column/after-restore.csv` (no country), `runs/schema_drop_column/restored.csv` (back to baseline)

Evidence: `observations/evidence/schema-drop-column/schema-drop-column-chatbot-restore.txt`

## Data validation result

```bash
python data-validation/validate.py --case schema_drop_column --input datasets/orders_schema_drop_column.csv --output runs/schema_drop_column/run1.csv
```

````
# Validation: `schema_drop_column` — ❌ FAIL

- Input: `datasets/orders_schema_drop_column.csv`
- Outputs: `runs/schema_drop_column/run1.csv`
- 19 pass, 1 warn, 2 fail, 3 skipped

| Check | Result | Detail |
|---|---|---|
| `input.schema` | ⚠️ WARN | schema drift: missing=['country'] added=[] |
| `input.types` | ✅ PASS | column types match the baseline |
| `input.amount_scale` | ✅ PASS | median amount_usd is 1.0x the baseline |
| `input.date_order` | ✅ PASS | 1 slash dates have a first part > 12 vs 39 with a second part > 12: dates look MM/DD |
| `output.schema` | ❌ FAIL | missing=['country'] unexpected=[] |
| `output.rows` | ✅ PASS | 54 rows, expected 54 |
| `rule.trimmed` | ✅ PASS | text is trimmed |
| `rule.name_title_case` | ✅ PASS | customer_name is Title Case and never empty |
| `rule.email` | ✅ PASS | email is lowercase and valid, or empty |
| `rule.country_iso2` | ⏭️ SKIP | column country not in output |
| `rule.date_iso` | ✅ PASS | order_date is YYYY-MM-DD |
| `rule.quantity_positive_int` | ❌ FAIL | 54/54 rows break: quantity is a positive integer |
| `rule.amount_2dp` | ✅ PASS | amount_usd is a non-negative number, at most 2 decimals, no symbols |
| `rule.status` | ✅ PASS | status is one of ['cancelled', 'delivered', 'pending', 'shipped', 'unknown'] |
| `values.customer_name` | ✅ PASS | all 54 matched rows agree with the reference |
| `values.email` | ✅ PASS | all 54 matched rows agree with the reference |
| `values.country` | ⏭️ SKIP | country not in output |
| `values.order_date` | ✅ PASS | all 54 matched rows agree with the reference |
| `values.quantity` | ✅ PASS | all 54 matched rows agree with the reference |
| `values.amount_usd` | ✅ PASS | all 54 matched rows agree with the reference |
| `values.status` | ✅ PASS | all 54 matched rows agree with the reference |
| `semantic.date_window` | ✅ PASS | all dates inside 2025-01-01..2025-03-31 |
| `semantic.amount_scale` | ✅ PASS | median amount_usd = 191.16 (expected 10..1000 dollars) |
| `semantic.unit_price` | ✅ PASS | 0/54 implied unit prices outside $5..$250 |
| `determinism` | ⏭️ SKIP | pass --output more than once to compare runs |
````

- The validator flagged the drift in the input (`input.schema` warning) and in the output (`output.schema` fail).
- `rule.quantity_positive_int` fails for the same reason as the baseline (`2.0`), not because of this drift.

## Verdict

- Pipeline stopped: yes, the first run after the change failed.
- Chatbot fix worked: yes for the drifted file, but it broke the pipeline for the original file (silently dropped `country`) until I asked for it to be restored.
- Severity: High
- Summary: Rhombus failed loudly when `country` disappeared, which is the right behaviour. But the scheduler did not notice the changed S3 file and kept skipping runs as "unchanged data"; the chatbot's "15-minute cache" explanation was wrong. The error message is a raw code dump. The chatbot's fix removed `country` handling instead of making the column optional, so when the original file came back, a valid column was silently dropped with a success status.
