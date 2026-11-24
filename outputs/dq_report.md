# P28 — Data-quality report

**14/14 tests passing.** Each test is a SQL query in `sql/tests/` that returns its violating rows; every test expects 0 rows.

| Test | Result | Violations |
|---|---|---|
| `t01_bronze_silver_quarantine_reconciles.sql` | PASS | 0 |
| `t02_silver_no_duplicate_order_id.sql` | PASS | 0 |
| `t03_silver_no_null_keys.sql` | PASS | 0 |
| `t04_silver_quantity_positive.sql` | PASS | 0 |
| `t05_silver_unit_price_positive.sql` | PASS | 0 |
| `t06_silver_discount_range.sql` | PASS | 0 |
| `t07_silver_line_total_correct.sql` | PASS | 0 |
| `t08_silver_dates_valid_and_in_range.sql` | PASS | 0 |
| `t09_fact_grain_one_row_per_order.sql` | PASS | 0 |
| `t10_fact_totals_reconcile_silver.sql` | PASS | 0 |
| `t11_fact_no_null_keys.sql` | PASS | 0 |
| `t12_dim_date_coverage_30_days.sql` | PASS | 0 |
| `t13_load_log_no_duplicate_hash.sql` | PASS | 0 |
| `t14_marts_reconcile_to_fact.sql` | PASS | 0 |

## What the tests cover

- **Reconciliation (t01, t10, t14):** bronze (2,111) = silver (2,094) + quarantine (17); fact totals reconcile to silver; all four marts reconcile to the fact table.
- **Silver guards (t02–t08):** one row per order id, no NULL keys, quantity > 0, price > 0, discount 0–100, line totals recomputed to the paisa, dates real and inside the 30-day window.
- **Gold (t09, t11–t13):** fact grain is one row per order, every fact key exists in its dimension, dim_date covers exactly the 30 days, and no file hash was ever loaded twice (the idempotency control).

## Reconciliation

- Raw rows: 2,111 → bronze: 2,111 → silver: 2,094 → fact: 2,094. 17 rows quarantined, nothing else dropped.
- Revenue: PKR 38,573,539.50 in silver, fact and all four marts — the same number four ways.
- Quarantine by reason: invalid_quantity 6, duplicate_order_id 6, missing_or_invalid_price 3, invalid_date 2.
- Load log: 30 files, one per day 2026-10-25 to 2026-11-23, each loaded exactly once.

## Checks beyond the SQL tests

src/checks.py recomputes every headline number from the raw daily CSVs independently (no database, no warehouse) and compares it with the warehouse, the workbook's formulas (recalculated in LibreOffice) and this report — including a second pipeline run that must add 0 rows. See its output for the full list.
