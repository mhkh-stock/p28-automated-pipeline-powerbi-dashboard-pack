# P28 — Automated Pipeline + Power BI Dashboard Pack

**Client (SAMPLE):** a small retailer whose daily sales CSVs land in
a folder · **Status: SAMPLE delivery on synthetic data**
**Tools:** Python · SQL (SQLite, star schema) · Power BI (model +
DAX) · Excel (live formulas) · reportlab
**Deliverable:** `outputs/pipeline_dashboard_SAMPLE.xlsx` +
`outputs/pipeline_report_SAMPLE.pdf` + the Power BI model in
`powerbi/` — a pipeline that loads the shop's daily sales files
itself and a dashboard that updates itself from them

> ⚠️ **What this is and is not.** The shop ("NoorMart"), the
> customers, the products and the 2,094 orders are synthetic SAMPLE
> data, generated in this repo with a fixed seed — not a real shop's
> sales. What is real is the method: the same daily-file scan →
> control log → SQL validation → quarantine → star schema → Power BI
> pipeline runs unchanged on the client's real daily exports, and
> every number in the report is recomputed from the loaded data,
> never typed.

## Business question it answers

> "Every morning my sales files land in a folder — can the dashboard just update itself?"

A retailer who re-keys yesterday's sales into a spreadsheet every
morning is paying for yesterday twice: once in staff time, once in
the mistakes that creep in. This delivery answers it with a
pipeline that loads each new daily file once (tracked by hash, so a
re-run adds 0 rows), validates every row in SQL, quarantines the
dirty ones with their reason, and feeds a star schema the Power BI
dashboard reads — so the owner opens the dashboard each morning and
the numbers are already there, already checked.

## The method (plainly stated)

**Ingest:** 30 daily sales CSVs (`data/raw/daily/sales_YYYY-MM-DD.csv`),
25 Oct – 23 Nov 2026, one file per day from the till export —
2,111 raw rows. `src/run_pipeline.py` scans the folder, loads only
files it has not seen before (SHA-256 in the control table
`pipeline_load_log`), and records each file's row counts.

**Validate:** every row is checked in SQL (`sql/silver_orders.sql`):
order id present and first occurrence only; a real calendar date
inside the 30-day window; quantity a whole number above 0; unit
price a number above 0; discount 0–100; known category and channel.
Line totals are recomputed (quantity × price × (1 − discount)),
never trusted from the file.

**Quarantine:** 17 rows failed and never reached the dashboard —
6 duplicate order ids, 6 invalid quantities (4 negative, 2 zero),
3 missing prices, 2 impossible dates. They sit in
`quarantine_orders` with the reason, so the shop fixes the till
export instead of arguing about the dashboard.

**Store:** gold star schema — `fact_orders` (one row per order) +
`dim_date` (30 days) / `dim_product` (24) / `dim_channel` (3) /
`dim_customer` (240) — plus five marts the Power BI model reads.

**Visualise:** a Power BI model (star schema, 12 DAX measures,
4-page layout, build guide to rebuild the `.pbix` on Windows) and a
live-formula Excel workbook, both fed by the same warehouse — so the
workbook and the dashboard cannot disagree.

**Limits, stated upfront:** this is SAMPLE data — synthetic orders
for a sample retailer, not a real shop's sales. The 30-day window
covers 25 Oct – 23 Nov 2026 only, so there is no year-ago
comparison in the data itself; the DAX pack includes a prior-period
measure that activates once a second month of files is loaded.
Discounts in this data run 0–15%; the pipeline accepts 0–100%.
Weekend means Friday–Sunday in this market (the shop's busy days).

## What is inside

| File | What it does |
|---|---|
| `outputs/pipeline_dashboard_SAMPLE.xlsx` | The deliverable: Cover (headline numbers, live) + Orders (2,094 orders, filterable) + Sales summary (21 headline numbers, all formulas, plus the daily table) + Channel + Top products + Method |
| `outputs/pipeline_report_SAMPLE.pdf` | 2-page report: question, headline numbers, channel/category findings, top products, the quarantine, recommendations |
| `powerbi/model.md` | The Power BI model: tables, relationships, star-schema diagram (Mermaid + rendered PNG) |
| `powerbi/dax_measures.md` | 12 DAX measures (revenue, orders, AOV, prior-period growth, channel/category shares, top category/product) |
| `powerbi/build_guide.md` | Exact steps to rebuild the `.pbix` on Windows in ~20 minutes |
| `powerbi/previews/*.png` | 4 page preview renders (matplotlib, labelled as renders — not Power BI screenshots) |
| `powerbi/model_star_schema.png` | Rendered star-schema diagram |
| `outputs/dq_report.md` | Findings report: 14/14 test results, reconciliation |
| `outputs/test_results.json` | Machine-readable test results (14 tests) |
| `outputs/analysis.json` | Headline numbers, computed once from the warehouse |
| `outputs/mart_*.csv` | The five gold marts as CSVs (by day/channel/category, top products, by month) |
| `data/raw/daily/sales_*.csv` (30 files) | The daily till exports, 2,111 rows, exactly as the shop would drop them in the folder |
| `data/processed/pipeline.db` | The built warehouse (SQLite — NOT committed; rebuilds from the scripts) |
| `data/processed/fact_orders.csv` | The fact table as CSV (2,094 rows) |
| `data/README.md` | Data dictionary + the 17 dirty rows, by design |
| `sql/schema.sql` | Bronze landing table + control log + silver/quarantine + gold star-schema DDL |
| `sql/silver_orders.sql` | Silver model (validation rules + quarantine, idempotent) |
| `sql/gold_dimensions.sql`, `gold_facts.sql`, `gold_marts.sql` | Gold models (dimensions + fact + 5 marts) |
| `sql/tests/` | 14 data-quality test queries (reconciliation, silver guards, gold grain, idempotency) |
| `src/generate_data.py` | Generates the 30 SAMPLE daily files (seed 28, deterministic) |
| `src/run_pipeline.py` | The pipeline: scan → load new files once → validate → gold. `--rebuild` loads all 30 fresh |
| `src/headlines.py` | Headline numbers from the warehouse, written to `outputs/analysis.json` |
| `src/run_tests.py` | Runs all 14 tests, prints PASS/FAIL per test + summary |
| `src/build_previews.py` | Builds the 4 Power BI page previews + the star-schema diagram |
| `src/build_workbook.py` | Builds the workbook: 6 sheets, live formulas |
| `src/build_report.py` | Builds the 2-page report PDF + `dq_report.md` |
| `src/checks.py` | Verification suite — 153 automated checks, all passing (incl. LibreOffice recalc + a second pipeline run that must add 0 rows) |
| `requirements.txt` | Pinned: `openpyxl==3.1.2`, `reportlab==5.0.1`, `matplotlib==3.6.3`, `pandas==2.1.4` (Python 3.12) |

## How it fits together

```
data/raw/daily/sales_2026-10-25.csv ... sales_2026-11-23.csv (30 files, 2,111 rows)
   ──▶ src/run_pipeline.py ──▶ bronze_orders (as exported, + source file + hash)
        (control log: SHA-256 per file — re-run skips loaded files, +0 rows)
                                                        ▼
                                           silver_orders (validated, 2,094)
                                           quarantine_orders (17, with reason)
                                                        ▼
                              dim_date / dim_product / dim_channel / dim_customer
                                              ──▶ fact_orders (2,094)
                                                        ▼
              mart_sales_by_day / _channel / _category / mart_top_products / _month
                                                        ▼
                     powerbi/ model + 12 DAX measures ──▶ .pbix (built on Windows)
                     src/build_workbook.py ──▶ pipeline_dashboard_SAMPLE.xlsx
                     src/build_report.py   ──▶ pipeline_report_SAMPLE.pdf
                     src/build_previews.py ──▶ 4 page previews + star-schema diagram
                        ▲ src/checks.py verifies all of it (incl. LibreOffice recalc)
```

## Headline numbers (SAMPLE — 30 days, 25 Oct – 23 Nov 2026)

- **2,094 orders · 30 daily files · 2,111 raw rows · 17 quarantined**
  · **240 customers · 24 products · 4 categories · 3 channels**
- **Revenue PKR 38,573,539.50 · 4,848 units · AOV PKR 18,420.98**
- **69.8 orders per day · PKR 1,285,784.65 revenue per day**
- **Best day 2026-11-20: PKR 1,962,402.65 on 76 orders** · **worst
  day 2026-10-30: PKR 838,444.90 on 78 orders**
- **14/14 data-quality tests passing** · **153 automated checks passing
  (incl. a second pipeline run adding 0 rows)**

## Sales by channel (PKR)

| Channel | Orders | Revenue | Share |
|---|---|---|---|
| In-store | 1,036 | PKR 19,445,092.50 | 50.41% |
| Online | 734 | PKR 12,876,026.90 | 33.38% |
| WhatsApp | 324 | PKR 6,252,420.10 | 16.21% |
| **TOTAL** | **2,094** | **PKR 38,573,539.50** | **100.00%** |

In-store is still the shop: 1,036 orders and 50.41% of revenue. But
Online is already a third of the money (33.38%) and WhatsApp orders
(324) are real sales, not enquiries — the dashboard now counts them,
so the owner stops guessing how much the chat channel is worth.

## Sales by category (PKR)

| Category | Orders | Units | Revenue | Share |
|---|---|---|---|---|
| Electronics | 500 | 978 | PKR 25,086,924.30 | 65.04% |
| Home & Kitchen | 381 | 782 | PKR 5,815,218.40 | 15.08% |
| Groceries | 736 | 2,150 | PKR 4,411,786.75 | 11.44% |
| Clothing | 477 | 938 | PKR 3,259,610.05 | 8.45% |
| **TOTAL** | **2,094** | **4,848** | **PKR 38,573,539.50** | **100.00%** |

Electronics is 65.04% of revenue on only 500 orders — one Smartphone
X1 sale is worth about 14 grocery orders. Groceries bring the most
orders (736) at the lowest ticket: the footfall category, not the
money category. The dashboard keeps both facts in front of the owner
at once, instead of letting the busiest shelf look like the most
profitable one.

## Top products (PKR)

| Product | Category | Orders | Revenue |
|---|---|---|---|
| Smartphone X1 | Electronics | 93 | PKR 15,104,322.30 |
| LED TV 32 inch | Electronics | 89 | PKR 6,854,040.60 |
| Water Dispenser | Home & Kitchen | 71 | PKR 2,075,111.65 |
| Dinner Set 24pc | Home & Kitchen | 52 | PKR 1,268,052.45 |
| Non-stick Cookware Set | Home & Kitchen | 67 | PKR 1,248,161.30 |

The top product alone — Smartphone X1 — is PKR 15,104,322.30 on 93
orders. The top 10 products together are 82.14% of the month's
revenue, which is why the dashboard's top-products page exists:
stock the top 10 first, and a stock-out there costs more than
anywhere else in the shop.

## Sales by month (PKR)

| Month | Orders | Revenue |
|---|---|---|
| 2026-10 (7 days) | 497 | PKR 8,598,627.95 |
| 2026-11 (23 days) | 1,597 | PKR 29,974,911.55 |
| **TOTAL** | **2,094** | **PKR 38,573,539.50** |

October is only 7 days of the window, so the month split is a
calendar artefact, not a trend — the daily table in the workbook is
the honest view, and the prior-period DAX measure stays blank until
a second full month of files is loaded.

## Weekends vs weekdays

| Days | Days | Orders | Revenue | Orders/day |
|---|---|---|---|---|
| Weekend (Fri–Sun) | 9 | 693 | PKR 12,089,713.45 | 77.0 |
| Weekday | 21 | 1,401 | PKR 26,483,826.05 | 66.7 |

Weekends run hotter — 77.0 orders a day against 66.7 on weekdays —
which is why the daily-trend page shades weekends: the owner can
see at a glance whether a quiet Monday is a problem or just a Monday.

## The three recommendations (from the data, not from a template)

1. **Protect the top 10.** The top products carry most of the
   month's revenue and the top one is a phone worth
   PKR 15,104,322.30 — set a stock alert on those ten before anything
   else, and check them first every morning.
2. **Grow Online and WhatsApp on purpose.** They are already 49.59%
   of revenue combined. Give them the same morning check the till
   gets — the pipeline already loads their files, so the dashboard
   will show whether a promotion there actually moved sales.
3. **Fix the till export, not the dashboard.** 17 dirty rows in 30
   days is a small leak, and the quarantine catches it — but every
   one of them is a till-export problem (duplicates, missing prices,
   impossible dates). Fix the export and the quarantine empties
   itself.

## Same logic, four ways — and they must agree

The headline numbers exist in four forms: the raw daily CSVs, the
SQL warehouse, the workbook's formulas, and the report PDF.
`src/checks.py` recomputes all four from the raw files and compares
them — a mistake in any one shows up as a failure — and runs the
pipeline a second time to prove it adds 0 rows. The workbook's
formulas were also recalculated in LibreOffice: every total matches
the recompute exactly, with zero error values.

## Reproduce it (2 minutes)

```bash
pip install -r requirements.txt
python3 src/generate_data.py   # 30 SAMPLE daily files -> data/raw/daily/
python3 src/run_pipeline.py --rebuild  # bronze -> silver -> gold -> data/processed/pipeline.db
python3 src/run_tests.py       # 14 tests — expect 14/14 passing
python3 src/headlines.py       # headline numbers -> outputs/analysis.json
python3 src/build_previews.py  # 4 page previews + star-schema diagram
python3 src/build_workbook.py  # outputs/pipeline_dashboard_SAMPLE.xlsx
python3 src/build_report.py    # outputs/pipeline_report_SAMPLE.pdf (2 pages) + dq_report.md
python3 src/checks.py          # verification suite — expect all passing
```

Every morning after that, the client drops the new daily file into
`data/raw/daily/` and runs `python3 src/run_pipeline.py` (no
`--rebuild`) — it loads only the new file, and the workbook and
dashboard refresh from the warehouse. The `.db` file is never
committed; it rebuilds from the scripts.
