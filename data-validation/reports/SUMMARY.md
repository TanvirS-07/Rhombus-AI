# Validation summary

| Case | Runs | Verdict | Failed checks |
|---|---|---|---|
| baseline | 1 | FAIL | rule.quantity_positive_int |
| schema_add_column | 1 | FAIL | rule.quantity_positive_int |
| schema_combined | 1 | FAIL | rule.quantity_positive_int, values.country |
| schema_drop_column | 1 | FAIL | output.schema, rule.quantity_positive_int |
| schema_rename_column | 1 | FAIL | output.schema, output.rows, rule.quantity_positive_int |
| schema_type_change | 1 | FAIL | output.rows |
| semantic_cents | 1 | FAIL | rule.quantity_positive_int, values.amount_usd, semantic.amount_scale, semantic.unit_price |
| semantic_date_ddmm | 1 | FAIL | rule.quantity_positive_int, values.order_date, semantic.date_window |
