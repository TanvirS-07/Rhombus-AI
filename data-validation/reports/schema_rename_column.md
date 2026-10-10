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

## Failure details

### `output.schema`
```json
{
  "columns": [
    "order_id",
    "customer_name",
    "email",
    "country",
    "order_date",
    "quantity",
    "status"
  ],
  "missing": [
    "amount_usd"
  ],
  "unexpected": []
}
```

### `output.rows`
```json
{
  "actual": 56,
  "expected": 54,
  "duplicates": [],
  "invented": [],
  "dropped_valid": [],
  "kept_invalid": [
    "1023",
    "1026"
  ]
}
```

### `rule.quantity_positive_int`
```json
{
  "examples": [
    "2.0",
    "3.0",
    "2.0",
    "5.0",
    "6.0"
  ]
}
```

