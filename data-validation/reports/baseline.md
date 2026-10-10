# Validation: `baseline` — ❌ FAIL

- Input: `datasets/orders_baseline.csv`
- Outputs: `runs/baseline/run1.csv`
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
```

