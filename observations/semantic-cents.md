# Semantic drift: amounts in cents instead of dollars

## Summary

Severity: High

Rhombus did not notice the change. The run succeeded with no warning, and every amount in the output was 100x too large. When asked to check the output, the chatbot flagged only one order and attributed it to an earlier pipeline bug. After I explained the change, it added a divide-by-100 step that fixed the cents file but made every amount 100x too small when the original file came back. My data validation caught the problem in both directions.

### Main findings

1. Rhombus gave no warning. The structure was unchanged, so the run succeeded and wrote amounts 100x too large to GCS.
2. When asked whether anything looked wrong, the chatbot described the output as "largely correct" and flagged only order 1004. It blamed the earlier `orders_trimmed` bug instead of the change in the source data.
3. The hinted fix divided every amount by 100 without checking the format. With the original file, every amount became 100x too small, again with a success status and no warning.
4. The validator caught the change in the input (`input.amount_scale`: 100x the baseline) and in the output (`semantic.amount_scale`, `semantic.unit_price`, `values.amount_usd`). The format check `rule.amount_2dp` passed, so a format check alone would not have found it.

### Runs

- First run: success, 54 rows, every amount 100x too large (`runs/semantic_cents/run1.csv`)
- After the hint: identical to the baseline (`run2-fixed.csv`)
- Original file with the hint fix in place: success, every amount 100x too small (`after-restore.csv`)
- After asking the chatbot to remove the fix: identical to the baseline (`restored.csv`)

---

## What I changed

- Source file: `datasets/orders_semantic_cents.csv`. Same 68 rows, same 8 columns and same column names as the baseline. Only the meaning of `amount_usd` changed: values are in cents with no `$` and no decimal point, so `$70.84` became `7084`.
- Uploaded to S3 as `rhombus/orders.csv` at 2026-10-10 06:08 UTC (17:08 local). S3 showed 5.0 KB.
- Pipeline: the baseline pipeline, including the changes kept from the type change and combined tests (see `schema-combined.md`).

## What I expected

The amounts look like normal numbers, so Rhombus will treat them as dollars and the output will be 100x too large and nothing to catch that.

## How to repeat it

1. Start from the working baseline pipeline.
2. Upload `datasets/orders_semantic_cents.csv` to S3 as `rhombus/orders.csv`.
3. Press Run. Scheduled runs do not pick up a changed source file (see `schema-drop-column.md`), so all runs in this test were manual.
4. Ask the chatbot to check the output without mentioning cents, then send a hint that explains the change.

## What happened

### 1. First run: succeeded with wrong amounts

- Time: 06:08 UTC (17:08 local). Output `RhombusAI_output_1791612521206.csv` (4.1 KB).
- Status: success, no warning.
- 54 rows, correct apart from `amount_usd`. Every amount is 100x too large, for example order 1004 is `7084.0` instead of `70.84`.

Output: `runs/semantic_cents/run1.csv`

### 2. After the hint: correct

- Time: 06:13 UTC (17:13 local). Output `RhombusAI_output_1791612793891.csv` (4 KB).
- Byte-for-byte identical to the baseline output 6.

Output: `runs/semantic_cents/run2-fixed.csv`

## What the logs said

Nothing. The run succeeded and there was no warning about the amounts.

## What the chatbot said, and did its fix work?

### Check 1: asked to review the output, no hint

I asked: "/pipeline Please check the latest output. Does anything look wrong with the data?"

The chatbot said the output "looks largely correct" and flagged one issue: "order_id 1004: amount_usd = 7084.0 (should be 70.84)". It described this as "the recurring $70.84 → 7084 bug" from the baseline build and suggested the `orders_trimmed` code lock was not holding.

- Diagnosis: incorrect. All 54 amounts were wrong, not one, and the cause was the source data, which had no `$` or decimal point. It did not consider that the input had changed.
- It also explained the `2.0` quantity values as a pandas "read-back artefact". The output file itself contains `2.0`, so this explanation does not appear to be correct (inferred from the file).

Evidence: `observations/evidence/semantic-cents/semantic-cents-chatbot.txt`

### Fix 1: after I explained the change

I told it: "/pipeline It is not just order 1004. Every amount_usd in the source is now in cents with no decimal point (7084 means $70.84), so every amount in the output is 100x too large. Convert these to dollars. Keep the other cleaning rules."

It changed `parse_amount_usd` in `orders_cleaned` to divide every parsed value by 100.

- Did the fix work: yes for the cents file. The output matched the baseline exactly.
- But the division applies to every value, whatever its format. It did not check for a `$` or a decimal point, so the original file was no longer handled correctly (see below).

Evidence: `observations/evidence/semantic-cents/semantic-cents-chatbot-2.txt`

## What happened to the schedule

Not tested separately: scheduled runs do not pick up source changes (see `schema-drop-column.md`). The schedule is still on.

## Restoring the baseline

- Uploaded `datasets/orders_baseline.csv` at 06:20 UTC (17:20 local) and pressed Run without changing the pipeline.
- Output `RhombusAI_output_1791613290692.csv` (3.9 KB): success, no warning, but every amount was 100x too small. `$70.84` became `0.71`.
- I asked the chatbot: "/pipeline The source is back in dollars ($70.84) and the output now shows 0.71. Remove the divide-by-100 step so amount_usd is read as dollars again. Keep all other cleaning rules." It removed the step.
- Run at 06:23 UTC (17:23 local): output `RhombusAI_output_1791613393208.csv` was byte-for-byte identical to output 6.

Outputs: `runs/semantic_cents/after-restore.csv` (amounts 100x too small), `runs/semantic_cents/restored.csv` (back to baseline)

Evidence: `observations/evidence/semantic-cents/semantic-cents-chatbot-restore.txt`

## Data validation result

```bash
python data-validation/validate.py --case semantic_cents --input datasets/orders_semantic_cents.csv --output runs/semantic_cents/run1.csv
```

````
# Validation: `semantic_cents` — ❌ FAIL

- Input: `datasets/orders_semantic_cents.csv`
- Outputs: `runs/semantic_cents/run1.csv`
- 18 pass, 2 warn, 4 fail, 1 skipped

| Check | Result | Detail |
|---|---|---|
| `input.schema` | ✅ PASS | columns match the baseline |
| `input.types` | ⚠️ WARN | type drift: {'amount_usd': 'number -> integer'} |
| `input.amount_scale` | ⚠️ WARN | median amount_usd is 100.0x the baseline (dollars -> cents?) |
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
| `values.amount_usd` | ❌ FAIL | 54/54 rows differ from the reference |
| `values.status` | ✅ PASS | all 54 matched rows agree with the reference |
| `semantic.date_window` | ✅ PASS | all dates inside 2025-01-01..2025-03-31 |
| `semantic.amount_scale` | ❌ FAIL | median amount_usd = 19115.50 (expected 10..1000 dollars) |
| `semantic.unit_price` | ❌ FAIL | 54/54 implied unit prices outside $5..$250 |
| `determinism` | ⏭️ SKIP | pass --output more than once to compare runs |
````

- The validator flagged the change in the input before looking at the output (`input.amount_scale`: 100x the baseline, with the suggestion "dollars -> cents?").
- In the output, three checks caught it: `values.amount_usd`, `semantic.amount_scale` and `semantic.unit_price`.
- `rule.amount_2dp` passed, because `7084.0` is a valid number with no symbols. Checking the format alone would not have found the problem. The scale and unit price checks are what caught it.
- The same checks also catch the opposite error. Run against `after-restore.csv` with the baseline input, `semantic.amount_scale` fails with a median of $1.92 and `semantic.unit_price` fails on all 54 rows.
- `rule.quantity_positive_int` fails for the same reason as the baseline (`2.0`).
