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

### `values.amount_usd`
```json
{
  "diffs": [
    {
      "order_id": "1004",
      "expected": "70.84",
      "actual": "7084.0"
    },
    {
      "order_id": "1040",
      "expected": "295.29",
      "actual": "29529.0"
    },
    {
      "order_id": "1042",
      "expected": "39.15",
      "actual": "3915.0"
    },
    {
      "order_id": "1043",
      "expected": "940.49",
      "actual": "94049.0"
    },
    {
      "order_id": "1022",
      "expected": "106.67",
      "actual": "10667.0"
    }
  ],
  "diff_count": 54
}
```

### `semantic.amount_scale`
```json
{
  "median": 19115.5
}
```

### `semantic.unit_price`
```json
{
  "examples": [
    "1004: 3542.00",
    "1040: 9843.00",
    "1042: 1957.50",
    "1043: 15674.83",
    "1022: 1777.83"
  ]
}
```

