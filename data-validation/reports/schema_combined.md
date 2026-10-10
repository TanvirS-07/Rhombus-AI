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

### `values.country`
```json
{
  "diffs": [
    {
      "order_id": "1004",
      "expected": "US",
      "actual": ""
    },
    {
      "order_id": "1040",
      "expected": "AU",
      "actual": ""
    },
    {
      "order_id": "1042",
      "expected": "CA",
      "actual": ""
    },
    {
      "order_id": "1043",
      "expected": "CA",
      "actual": ""
    },
    {
      "order_id": "1022",
      "expected": "GB",
      "actual": ""
    }
  ],
  "diff_count": 53
}
```

