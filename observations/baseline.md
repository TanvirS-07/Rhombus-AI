# Baseline Observations Document

## Summary

- Source file: `datasets/orders_baseline.csv` (68 rows)
- Expected output: 54 rows. The file holds 60 distinct orders plus 5 exact duplicates and 3 near-duplicates. Six orders are invalid and must be removed (1015, 1019, 1023, 1026, 1030, 1034).
- Pipeline built with: the Rhombus AI builder only (`/pipeline` and chat follow-ups). No nodes were added or edited by hand.
- Result: it took 6 outputs to get a correct file.
- Date: 2026-10-09 (UTC)

## What I did

1. Connected S3 (`rhombus/orders.csv`) as the source.
2. Sent one structured prompt (`pipeline/cleaning-prompt.md`, 9 rules) to the AI builder with `/pipeline`.
3. Downloaded each output and compared it with the expected answer (`data-validation/reference_clean.py`).
4. Sent follow-up messages to the chatbot until the output matched.

## Attempt 1: first output (looked fine, was wrong)

Evidence: `observations/evidence/baseline-output-1.csv`

The output had 56 rows. The Rhombus run status said successful and nothing warned that the data was wrong.

Correct:
- dates
- status values
- whitespace trimming
- duplicates

Wrong:
- Decimal points were removed from amounts, so every amount was 100x too big. `$70.84` became `7084.0` (order 1004).
- Minus signs were removed. Quantity `-2` became `2` (order 1015) and amount `-35.00` became `3500` (order 1026). Two invalid rows therefore looked valid and were kept.
- Every email was blank, even valid ones. `arjun.lee@example.com` became empty.
- Apostrophes were removed from names. `O'Brien` became `Obrien`.
- Some countries were blanked: 1036 and 1006 (source `AU`) and 1058 (`United States of America`).
- Quantity was written as a float, `2.0` instead of `2`.
- The row count was 56 instead of 54.

## Follow-up messages to the AI builder

### Follow-up 1: list of fixes

I asked it to keep the decimal point in amount, keep valid emails, fix quantity, keep two-letter country codes and keep apostrophes.

Prompt used:

/pipeline fix these problems in the current pipeline:

amount_usd: only remove the "$" sign and commas. Keep the decimal point. 70.84 must stay 70.84, never 7084. Round to 2 decimal places.
email: keep valid emails (lowercase). Only make an email empty if it is not a valid address or is "N/A".
quantity: keep the minus sign. Remove rows where quantity is not a whole number or is zero or negative (so -2 and "two" are removed). Output as a whole number like 2, not 2.0.
country: two-letter codes (AU, US, GB, NZ, CA) stay as they are. "United States of America" becomes US.
customer_name: keep apostrophes (O'Brien).

The chatbot said "compile succeeded" and described the fixes. The output file (output 2) was identical to output 1: amounts were still `7084.0` and emails still blank. The chatbot claimed a fix that had no effect.

Evidence: `observations/evidence/baseline-output-2.csv`

### Follow-up 2: ask for the exact rule

I told it : "The output still shows amount_usd 7084 for order 1004. It must be 70.84. Show me the exact rule you used for amount_usd."

The chatbot found the real cause. A built-in `orders_trimmed` text-cleanup node stripped every non-alphanumeric character (including `.`, `-`, `@` and `'`) before the cleaning step ran. It changed that node to skip amount_usd and quantity. Emails were still blank and `Obrien` was still wrong in the next output.

Evidence: `observations/evidence/baseline-output-3.csv`

### Follow-up 3: make orders_trimmed only trim spaces

I told it "/pipeline The orders_trimmed node still strips @, . and apostrophes. Make it only trim leading and trailing spaces and collapse repeated spaces. It must not remove any other characters." The chatbot replaced the node with an LLM node, but the new node had an empty prompt and the pipeline failed:

`Pipeline failed at orders_trimmed: LLM transform requires a non-empty prompt when code is not provided.`

Evidence: a screenshot of the error, `observations/evidence/baseline-error-empty-prompt.PNG`

### Follow-up 4: fix the node prompt

I asked it to fix the node using prompt:

"Pipeline failed at orders_trimmed: LLM transform requires a non-empty prompt when code is not provided. Fix the node so it has a valid prompt. It must only trim leading and trailing spaces and collapse repeated spaces in the text columns, and must not remove any other characters. Then check that the whole pipeline compiles and runs."

The pipeline then ran end to end.

## Attempt 4: output after follow-ups

Evidence: `observations/evidence/baseline-output-4.csv`

Fixed:
- Amounts (`70.84` stays `70.84`).
- Emails.
- Apostrophes.
- Dates, status and names.
- Bad rows 1015 and 1026 are removed.

Still wrong:
- It had 41 rows instead of 54. Thirteen valid orders were silently missing: 1003, 1004, 1005, 1013, 1018, 1022, 1040, 1045, 1046, 1050, 1057, 1058 and 1060. None of them has an invalid date, quantity or amount.
- Orders 1036 and 1006 still had a blank country (source `AU`).
- Quantity was still written as `2.0` in the CSV.

## Attempt 5: asked for 54 rows, chatbot claimed it, still 41

I told the chatbot the output had 41 rows but should have 54.

Prompt used: 

"/pipeline The output has 41 rows but should have 54. These valid orders are missing: 1003, 1004, 1005, 1013, 1018, 1022, 1040, 1045, 1046, 1050, 1057, 1058, 1060. For each node, list which order_ids it removed and why. Then fix the pipeline so rows are only removed if they are exact duplicates, repeated order_ids, or have an invalid date, a non-positive whole number quantity, or a negative or empty amount. Also, orders 1036 and 1006 have country "AU" in the source but come out blank. Keep two-letter codes as they are."

It sent a drop trace that claimed 54 rows. The downloaded file (`observations/evidence/baseline-output-5.csv`) still had 41 rows.

I told it the new file had 41 rows again. Then I counted the rows in the Preview of each node myself:
- Data input: 68
- orders_trimmed: 68
- orders_no_exact_dups: 64
- orders_deduped: 60
- orders_cleaned: 41

That showed the problem was in `orders_cleaned`. It removed 13 valid rows when only 6 should be removed there.

Side note: `orders_no_exact_dups` gave 64 rows, not the 63 I expected (68 minus 5 exact duplicates). I could not explain this. It is harmless, because the next step dedupes by order_id.

## Attempt 6: final prompt and result

I sent this message to the chatbot:

"/pipeline Your report said orders_cleaned outputs 54 rows, but Preview shows 41. orders_deduped outputs 60 rows and orders_cleaned outputs 41, so orders_cleaned wrongly removes 13 valid rows. Only 6 rows should be removed there: orders 1015, 1019, 1023, 1026, 1030, 1034. These valid orders are missing from the output: 1003, 1004, 1005, 1013, 1018, 1022, 1040, 1045, 1046, 1050, 1057, 1058, 1060. Show me the exact code of orders_cleaned, then fix it so only those kinds of invalid rows are removed. After running, tell me the row count from the Preview, not from your own estimate."

The chatbot fixed `orders_cleaned`. This time its row count matched the Preview (54).

## Final result (output 6)

Evidence: `observations/evidence/baseline-output-6.csv`

- Row count: 54 (expected 54).
- No missing order ids and no extra order ids.
- customer_name, email, country, order_date, status and amount_usd all match the expected answer.
- Blank emails on 1004, 1008 and 1045 are correct. Their source emails were invalid (`lucas.chen.at.example.com`), empty or `N/A`.
- Quantity is written as `2.0` instead of `2`. The values are right but the CSV format is a float. I count this as minor.

Nodes the AI builder created:
- orders_raw (source)
- orders_trimmed (first a built-in text_cleanup node, then replaced by an LLM node)
- orders_no_exact_dups
- orders_deduped
- orders_cleaned (LLM node)

Pipeline canvas screenshot: `observations/evidence/Baseline-canvas.PNG`

Validation command:

```bash
python data-validation/validate.py --case baseline --input datasets/orders_baseline.csv --output observations/evidence/baseline-output-6.csv
```

Validation result: all content checks pass. The only failure is `rule.quantity_positive_int` (quantity written as `2.0`).

Here is the validation table:
````
# Validation: `baseline` — ❌ FAIL

- Input: `datasets/orders_baseline.csv`
- Outputs: `observations/evidence/baseline-output-6.csv`
- 23 pass, 0 warn, 1 fail, 1 skipped

| Check | Result | Detail |
|---|---|---|
| `input.schema` | ✅ PASS | columns match the baseline |
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

## Failure details

### `rule.quantity_positive_int`
```json
{
  "examples": [
    "2.0",
    "3.0",
    "2.0",
    "6.0",
    "6.0"
  ]
}
````

## Findings

1. **The run status said success while the data was wrong.** Amounts were 100x too big, emails were blank and invalid rows were kept. Nothing in the platform flagged it.
2. **The chatbot claimed fixes that did not change the output.** It only found the real cause when I told it the output was still wrong and asked for the exact rule.
3. **The AI builder created a node it could not run.** The LLM node had an empty prompt.
4. **A default text-cleanup step silently destroyed numeric formatting.** Decimal points, minus signs and email characters were stripped.
5. **Valid rows were dropped without any warning or explanation.** Thirteen valid orders went missing in `orders_cleaned`.
6. **The chatbot's own numbers did not match the data.** It reported "87 rows affected" on a 68-row file, and it claimed 54 rows when the Preview showed 41.
7. **Quantity is exported as a float (`2.0`)** even though it is a whole number.

## Time spent

- Follow-up messages to reach a correct output: 7 Follow up messages
- Total time: Logs (12:28pm - 12:57pm), 29 minutes to get the desired result
