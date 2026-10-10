# Semantic drift: dates in DD/MM instead of MM/DD

## Summary

Severity: Critical

Rhombus did not notice the change, and it could not fix it. The run succeeded with no warning, but 14 of 54 dates were wrong because day and month were swapped. When asked to check the output, the chatbot said "The output looks correct" and "No issues to fix". After I explained the problem, it reported a fix twice. Both times the output was byte-for-byte unchanged, and the second time it claimed to have verified the fix in a simulation and blamed a "workspace cache" for the old dates. My data validation caught the problem.

### Main findings

1. Rhombus read the same column in two different ways without any warning. Dates with a day above 12 (for example `16/03/2025`) were read correctly as day/month. Dates where both parts are 12 or under (for example `11/03/2025`) were read as month/day, so day and month were swapped.
2. When asked to check the output, the chatbot said it looked correct. It confirmed `order_date` only by format ("All YYYY-MM-DD"), so all 14 wrong dates passed.
3. The chatbot reported a fix twice and neither changed the output. All three outputs are byte-for-byte identical.
4. In its second answer the chatbot invented a cause (a Unix timestamp conversion, although this file has no timestamps), said it had "verified in simulation" that all 14 dates were correct, and did not show the date parsing code I asked for.
5. The validator caught the change in the input (`input.date_order`: dates look DD/MM) and in the output (`values.order_date`: 14 of 54 wrong, `semantic.date_window`: 13 outside Jan to Mar 2025). The date window check missed one swapped date that still fell inside the window, so only the comparison against the reference caught all 14.

### Runs

- First run: success, 54 rows, 14 dates swapped (`runs/semantic_date_ddmm/run1.csv`)
- After fix 1 (my hint): identical to the first run (`run2-claimed-fix.csv`)
- After fix 2 (my follow-up): identical to the first run (`run3-claimed-fix.csv`)
- Original file: identical to the baseline (`restored.csv`)

---

## What I changed

- Source file: `datasets/orders_semantic_date_ddmm.csv`. Same 68 rows, same 8 columns and same column names as the baseline. Only the meaning of the slash dates changed: they are written day first, so `03/16/2025` became `16/03/2025`. ISO dates and other formats were left as they were.
- Uploaded to S3 as `rhombus/orders.csv` at 2026-10-10 06:27 UTC (17:27 local). S3 showed 5.1 KB.
- Pipeline: the baseline pipeline, including the changes kept from the earlier tests (see `semantic-cents.md`).

## What I expected

The structure is unchanged, so the run will succeed.

## How to repeat it

1. Start from the working baseline pipeline.
2. Upload `datasets/orders_semantic_date_ddmm.csv` to S3 as `rhombus/orders.csv`.
3. Press Run. Scheduled runs do not pick up a changed source file (see `schema-drop-column.md`), so all runs in this test were manual.
4. Ask the chatbot to check the output without mentioning dates, then send a hint that explains the change.

## What happened

### 1. First run: succeeded with swapped dates

- Time: 06:27 UTC (17:27 local). Output `RhombusAI_output_1791613638882.csv` (4 KB).
- Status: success, no warning.
- 54 rows, correct apart from `order_date`. 14 dates have day and month swapped, for example order 1022 is `2025-11-03` instead of `2025-03-11`, and order 1016 is `2025-09-01` instead of `2025-01-09`.
- Dates with a day above 12 were converted correctly, for example order 1004 (`16/03/2025`) became `2025-03-16`. So the column mixes two interpretations.

Output: `runs/semantic_date_ddmm/run1.csv`

### 2. After fix 1: no change

- Time: 06:30 UTC (17:30 local). Output `RhombusAI_output_1791613851322.csv`.
- Byte-for-byte identical to the first run. All 14 dates were still swapped.

Output: `runs/semantic_date_ddmm/run2-claimed-fix.csv`

### 3. After fix 2: no change

- Time: 06:37 UTC (17:37 local). Output `RhombusAI_output_1791614246942.csv`.
- Byte-for-byte identical to the first run.

Output: `runs/semantic_date_ddmm/run3-claimed-fix.csv`

## What the logs said

Nothing. Every run succeeded and there was no warning about the dates.

## What the chatbot said, and did its fix work?

### Check 1: asked to review the output, no hint

I asked: "/pipeline Please check the latest output. Does anything look wrong with the data?"

The chatbot said "The output looks correct" and "The data looks good. No issues to fix." For `order_date` it reported "All YYYY-MM-DD, no malformed dates".

- Diagnosis: incorrect. It checked the format of the dates, not whether they matched the source, so it missed all 14 wrong dates.
- This is a weaker result than the cents test, where it at least flagged one wrong value.

Evidence: `observations/evidence/semantic-date-ddmm/semantic-date-ddmm-chatbot.txt`

### Fix 1: after I explained the change

I told it: "/pipeline The slash dates in order_date are now DD/MM/YYYY, not MM/DD/YYYY. 16/03/2025 is 16 March. 14 dates in the output are swapped, for example order 1022 is 11/03/2025 in the source and should be 2025-03-11, not 2025-11-03. Read slash dates as DD/MM/YYYY. Keep all other cleaning rules."

It said slash dates "are now parsed as DD/MM/YYYY ... so 11/03/2025 correctly becomes 2025-03-11".

- Did the fix work: no. The next output was byte-for-byte identical to the first run.

Evidence: `observations/evidence/semantic-date-ddmm/semantic-date-ddmm-chatbot-2.txt`

### Fix 2: after I said the output had not changed

I told it: "/pipeline The output did not change. Order 1022 is still 2025-11-03. Show me the exact date parsing code in orders_cleaned and the order it tries the formats in. Then fix it so slash dates are read as DD/MM/YYYY, and check order 1022 in the Preview before you reply."

It said "The fix works correctly. Order 1022 now produces 2025-03-11" and that "the simulation confirms the correct result". It said the Preview still showed the old dates because "The workspace cache just hasn't refreshed yet". It gave the cause as "the platform's serialization layer ... converting the raw Unix timestamp integers" and added a timestamp conversion to `orders_trimmed`.

- Diagnosis: incorrect. This file has no Unix timestamps. The dates are slash strings such as `11/03/2025`.
- Did the fix work: no. The next output was byte-for-byte identical to the first run, so its claim to have verified all 14 dates was not true.
- It did not show the date parsing code I asked for.
- I stopped after this attempt. Two hinted fixes were reported as successful and neither changed the output.

Evidence: `observations/evidence/semantic-date-ddmm/semantic-date-ddmm-chatbot-3.txt`

## What happened to the schedule

Not tested separately: scheduled runs do not pick up source changes (see `schema-drop-column.md`). The schedule is still on.

## Restoring the baseline

- Uploaded `datasets/orders_baseline.csv` at 06:42 UTC (17:42 local) and pressed Run without changing the pipeline.
- Output `RhombusAI_output_1791614551163.csv` was byte-for-byte identical to output 6. For example, order 1022 (`03/11/2025` in the baseline) became `2025-03-11`.
- This confirms that the pipeline still reads slash dates as month/day first, so neither of the chatbot's reported fixes changed the slash date parsing.

Output: `runs/semantic_date_ddmm/restored.csv`

## Data validation result

```bash
python data-validation/validate.py --case semantic_date_ddmm --input datasets/orders_semantic_date_ddmm.csv --output runs/semantic_date_ddmm/run1.csv
```

````
# Validation: `semantic_date_ddmm` — ❌ FAIL

- Input: `datasets/orders_semantic_date_ddmm.csv`
- Outputs: `runs/semantic_date_ddmm/run1.csv`
- 20 pass, 1 warn, 3 fail, 1 skipped

| Check | Result | Detail |
|---|---|---|
| `input.schema` | ✅ PASS | columns match the baseline |
| `input.types` | ✅ PASS | column types match the baseline |
| `input.amount_scale` | ✅ PASS | median amount_usd is 1.0x the baseline |
| `input.date_order` | ⚠️ WARN | 39 slash dates have a first part > 12 vs 1 with a second part > 12: dates look DD/MM |
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
| `values.order_date` | ❌ FAIL | 14/54 rows differ from the reference |
| `values.quantity` | ✅ PASS | all 54 matched rows agree with the reference |
| `values.amount_usd` | ✅ PASS | all 54 matched rows agree with the reference |
| `values.status` | ✅ PASS | all 54 matched rows agree with the reference |
| `semantic.date_window` | ❌ FAIL | 13/54 dates outside 2025-01-01..2025-03-31; months seen [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12] |
| `semantic.amount_scale` | ✅ PASS | median amount_usd = 191.16 (expected 10..1000 dollars) |
| `semantic.unit_price` | ✅ PASS | 0/54 implied unit prices outside $5..$250 |
| `determinism` | ⏭️ SKIP | pass --output more than once to compare runs |
````

- The validator flagged the change in the input before looking at the output (`input.date_order`: 39 slash dates have a first part above 12, so the dates look DD/MM).
- `rule.date_iso` passed, because every swapped date is still a valid YYYY-MM-DD date. This is the same check the chatbot relied on.
- `values.order_date` found all 14 wrong dates. `semantic.date_window` found 13: order 1011 became `2025-02-03` instead of `2025-03-02`, which is still inside the January to March window. A range check alone would have missed it.
- `rule.quantity_positive_int` fails for the same reason as the baseline (`2.0`).
