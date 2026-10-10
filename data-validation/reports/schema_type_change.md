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
