# Schema drift: type change (`order_date` to Unix timestamp)

## What I changed

- Source file: `datasets/orders_schema_type_change.csv`. It has the same 68 rows and 8 columns as the baseline, but `order_date` is now a Unix timestamp in seconds (for example `1742083200`) instead of a date string. The two invalid dates from the baseline (order 1034 empty, order 1030 `13/45/2025`) are left as they were.
- Uploaded to S3 as `rhombus/orders.csv` at 2026-10-10 05:16 UTC (16:16 local).
- Pipeline: the baseline pipeline, restored after the rename test (see `schema-rename-column.md`).

## What I expected

The date parser only knows date strings, so every date fails and the rows get dropped

## How to repeat it

1. Start from the working baseline pipeline.
2. Upload `datasets/orders_schema_type_change.csv` to S3 as `rhombus/orders.csv`.
3. Press Run. Scheduled runs do not pick up a changed source file (see `schema-drop-column.md`), so all runs in this test were manual.

## What happened

### 1. First run: failed

- Time: 05:16 UTC (16:16 local).
- Status: failed at `orders_cleaned`. No file was written to GCS.
- The run page showed the error and an "Ask Chatbot" button.

### 2. After the chatbot's first fix: an empty file reached GCS

- Time: 05:19 UTC (16:19 local). Output `RhombusAI_output_1791609540614.csv` (75 B) was written to GCS.
- The file has the header row and **no orders at all**. All 54 valid orders were lost.
- The only warning was a small note on the `orders_cleaned` node: "No results found after applying this LLM transformation." The pipeline still wrote the empty file to GCS.
- Run status was shown as success but small warning let me know something was wrong.

Output: `runs/schema_type_change/run1.csv`

### 3. After the second fix (with my hint): correct

- Time: 05:23 UTC (16:23 local). Output `RhombusAI_output_1791609804680.csv` (4 KB).
- Byte-for-byte identical to the baseline output 6: 54 rows, 8 columns, and every timestamp converted to the right date (for example order 1004 is `2025-03-16`).

Output: `runs/schema_type_change/run2-fixed.csv`

## What the logs said

```
Pipeline failed at orders_cleaned: LLM execution failed (code_sha=cf671a772d83): name 'TypeError' is not defined
--- Generated code ---
import pandas as pd
import numpy as np
def _safe_to_timedelta_wrapper(arg, *args, **kwargs):
...
```

- This is the least helpful error so far. It does not mention `order_date`, dates or timestamps at all.
- `name 'TypeError' is not defined` is about Python itself: the generated code has `except (ValueError, TypeError)`, and Rhombus's sandbox does not seem to allow the name `TypeError`. The new data made the code reach that line and crash (inferred from the chatbot's answer, not confirmed).
- So the real cause (a changed date format) was hidden behind an unrelated crash.
- The `code_sha` (`cf671a772d83`) is the same as in the rename test, so the restore after the rename test brought back the same node code.

Evidence: `observations/evidence/schema-type-change/schema-type-change-error.txt`

## What the chatbot said, and did its fix work?

### Fix 1: "Ask Chatbot" button

The chatbot said it replaced the `except (ValueError, TypeError)` clauses with `except Exception` "to avoid the TypeError is not defined error that occurs in the sandboxed execution environment where some built-in names aren't directly accessible", and said "The pipeline is ready to run."

- Diagnosis: only half right. It fixed the crash but never looked at why the data reached that code. It did not notice that `order_date` changed to timestamps.
- Did the fix work: no. With the crash gone, every timestamp failed to parse as a date, every row was dropped as invalid, and an empty file was written to GCS. A loud failure became silent total data loss.

Evidence: `observations/evidence/schema-type-change/schema-type-change-chatbot.txt`

### Fix 2: after I named the type change

I told it: "/pipeline The output is empty. order_date in the source is now a Unix timestamp in seconds (e.g. 1742083200), not a date string. Convert it to YYYY-MM-DD and keep the other cleaning rules."

It changed the date parser in `orders_cleaned` to try a Unix timestamp first, then fall back to the existing string formats (M/D/YYYY, YYYY-MM-DD, Mon DD YYYY and so on).

- Did the fix work: yes. The output matched the baseline exactly.
- Unlike the drop-column fix, this one handles both the old and the new format, so it does not break the original file (see "Restoring the baseline").
- But again, it only got there because I diagnosed the problem myself.

Evidence: `observations/evidence/schema-type-change/schema-type-change-chatbot-2.txt`

## What happened to the schedule

Not tested separately: scheduled runs do not pick up source changes (see `schema-drop-column.md`). Schedule is still on.

## Restoring the baseline

- Uploaded `datasets/orders_baseline.csv` as `rhombus/orders.csv` at 05:26 UTC (16:26 local) and pressed Run without changing the pipeline.
- Output `RhombusAI_output_1791609984077.csv` (4 KB) was byte-for-byte identical to output 6.
- So I kept the chatbot's second fix. A date parser that accepts both formats does no harm for the later tests.

Output: `runs/schema_type_change/restored.csv`

## Data validation result

```bash
python data-validation/validate.py --case schema_type_change --input datasets/orders_schema_type_change.csv --output runs/schema_type_change/run1.csv
```

````
# Validation: `schema_type_change` — ❌ FAIL

- Input: `datasets/orders_schema_type_change.csv`
- Outputs: `runs/schema_type_change/run1.csv`
- 3 pass, 1 warn, 1 fail, 1 skipped

| Check | Result | Detail |
|---|---|---|
| `input.schema` | ✅ PASS | columns match the baseline |
| `input.types` | ⚠️ WARN | type drift: {'order_date': 'date -> epoch'} |
| `input.amount_scale` | ✅ PASS | median amount_usd is 1.0x the baseline |
| `input.date_order` | ✅ PASS | 1 slash dates have a first part > 12 vs 1 with a second part > 12: dates look MM/DD |
| `output.rows` | ❌ FAIL | output has no data rows |
| `determinism` | ⏭️ SKIP | pass --output more than once to compare runs |
````

- My validator named the real cause straight away (`order_date: date -> epoch`), which neither the error message nor the chatbot did.
- It caught the empty output (`output.rows`), which Rhombus only hinted at in a small node note.
- The other checks did not run because there were no rows to check.

## Verdict

- Pipeline stopped: yes, the first run failed, but with a misleading error.
- Chatbot fix worked: no on the first attempt (an empty file was written to GCS); yes on the second, but only after I diagnosed the type change myself.
- Severity: High
- Summary: The error message pointed at a Python internals problem (`TypeError` not defined) instead of the changed date format. The "Ask Chatbot" fix removed the crash without finding the cause, so the next run dropped every row and delivered an empty file to GCS with a success status and only a small node note as warning. A downstream system reading that file would see zero orders.
