# Data — P28 Automated Pipeline + Power BI Dashboard Pack

## Source

**Synthetic SAMPLE data, generated in this repo** — 30 daily sales
CSVs, one per day, 25 Oct – 23 Nov 2026, made by
`src/generate_data.py` (seed 28, deterministic: re-running it
regenerates byte-identical files). The shop ("NoorMart"), the
customers, the products and the orders are invented to stand in for
a small retailer's real daily till exports. Nothing here is a real
shop's sales.

| File | Rows | What it is |
|---|---|---|
| `raw/daily/sales_YYYY-MM-DD.csv` (30 files) | 2,111 total | The daily till exports, exactly as the shop would drop them in the folder: one order per row |
| `processed/fact_orders.csv` | 2,094 | The gold fact table (one row per order) |
| `processed/pipeline.db` | — | The built warehouse (SQLite — **NOT committed**; rebuilds from the scripts) |

The `_SAMPLE` suffix on the deliverables marks this as demo data —
the pipeline and the method are the deliverable.

## Data dictionary — `raw/daily/sales_YYYY-MM-DD.csv`

| Column | Type | Meaning |
|---|---|---|
| `order_id` | text | Order id, unique per order (`ORD-YYYYMMDD-NNNN`); 6 rows in the month repeat an earlier id on purpose — they are duplicates the pipeline quarantines |
| `order_date` | text | Sale date (`YYYY-MM-DD`); 2 rows carry the impossible date `2026-13-40` on purpose |
| `customer_id` | text | Synthetic customer (`CUST-0001` … `CUST-0240`) |
| `product_id` | text | Product code (`E01`–`H06`, 24 products) |
| `product_name` | text | Product name as the till prints it |
| `category` | text | Electronics / Groceries / Clothing / Home & Kitchen |
| `channel` | text | In-store / Online / WhatsApp |
| `quantity` | integer | Units in the order (1–5); 6 rows carry 0 or a negative quantity on purpose |
| `unit_price_pkr` | number | Price per unit in PKR; 3 rows leave it blank on purpose |
| `discount_pct` | number | Discount applied, 0–15 in this data |

## Data dictionary — `processed/fact_orders.csv`

| Column | Type | Meaning |
|---|---|---|
| `order_id` | text | Unique order id |
| `order_date` | text | Sale date, 2026-10-25 … 2026-11-23 |
| `customer_id` | text | Synthetic customer |
| `product_id` | text | Product code |
| `category` | text | Product category |
| `channel` | text | Sales channel |
| `quantity` | integer | Units, always > 0 here |
| `unit_price_pkr` | real | Price per unit in PKR |
| `discount_pct` | real | Discount applied |
| `line_total_pkr` | real | Recomputed by the pipeline: quantity × unit price × (1 − discount) |

## The 17 dirty rows (by design)

The generator plants 17 bad rows across the month so the pipeline's
validation has real work to do: 6 duplicate order ids, 4 negative
quantities, 2 zero quantities, 3 missing prices, 2 impossible dates.
All 17 land in `quarantine_orders` with their reason and never reach
the fact table. The control log (`pipeline_load_log`) records each
file once, by SHA-256 hash — a re-run loads 0 new rows.
