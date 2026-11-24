# Power BI build guide — Automated Pipeline + Power BI Dashboard Pack (~20 minutes)

Builds the finished `.pbix` from this repo's model in Power BI
Desktop (Windows, free). No step needs anything outside this repo.
The `.pbix` itself is not in the repo — it needs a Windows machine
to build, so this guide, the model, the DAX and the page previews
are the shippable form, exactly as the client would rebuild it.

## 1. Import (5 min)

Power BI Desktop → Get Data → Text/CSV → import
`data/processed/fact_orders.csv`. In Power Query:

- Set `quantity` to Whole Number; `unit_price_pkr`,
  `discount_pct`, `line_total_pkr` to Decimal Number.
- Set `order_date` to Date.
- **dim_date:** Reference `fact_orders`, keep `order_date` only,
  Remove Duplicates, then Add Column → Year, Month, Month Name, Day,
  Day Name from the date; add a custom column `is_weekend` =
  `if Date.DayOfWeek([order_date], Day.Sunday) = 0 or
  Date.DayOfWeek([order_date], Day.Sunday) = 6 then 1 else 0`.
  (Or export it from SQLite with the query in `powerbi/model.md`.)
- **dim_product:** Reference `fact_orders`, keep `product_id`,
  `product_name`, `category`, `unit_price_pkr`, Remove Duplicates on
  `product_id`.
- **dim_channel:** Reference `fact_orders`, keep `channel`, Remove
  Duplicates.
- **dim_customer:** Reference `fact_orders`, Group By `customer_id`
  → `orders` = Count Rows, `total_spent_pkr` = Sum of
  `line_total_pkr`.
- Import the four mart CSVs from `outputs/` as standalone tables
  (`mart_sales_by_day`, `mart_sales_by_channel`,
  `mart_sales_by_category`, `mart_top_products`) for the
  pre-aggregated visuals. Load.

## 2. Relationships (2 min, Model view)

Single-direction, one-to-many, from each dimension to the fact:

- `dim_date[order_date]` → `fact_orders[order_date]`
- `dim_product[product_id]` → `fact_orders[product_id]`
- `dim_channel[channel]` → `fact_orders[channel]`
- `dim_customer[customer_id]` → `fact_orders[customer_id]`

One fact table, four dimensions — that star shape is why every
visual agrees on the same totals. Do not join the mart tables to
the fact; they are reference tables whose totals already equal the
fact's (proven by `sql/tests/t14`).

## 3. Measures (3 min)

Modeling → New measure, paste each measure from
`powerbi/dax_measures.md` (12 measures): Total Revenue, Total
Orders, Total Units, Average Order Value, Orders Per Day, Revenue
Per Day, Revenue Prior Period, Revenue Growth vs Prior Period %,
Top Category Revenue, Top Product Revenue, In-store Share %,
Online + WhatsApp Share %. Format revenue measures as whole PKR,
shares as %.

Note: Revenue Prior Period is blank on this SAMPLE — the window is
a single 30 days, so there is no prior 30-day period yet. It fills
itself in once a second month of daily files is loaded; nothing
needs rebuilding.

## 4. Page layout (10 min, four pages, top to bottom)

**Page 1 — Overview** (see `powerbi/previews/overview.png`):
1. KPI cards (top row): Total Revenue · Total Orders · Average
   Order Value · Orders Per Day — the four numbers the owner reads
   first.
2. Clustered column chart: Total Revenue by `dim_date[order_date]`
   with a 7-day moving-average line (Analytics → Trend line, or a
   second line visual on the daily mart).
3. Slicers (left or top): `dim_channel[channel]`,
   `dim_product[category]`, `dim_date[month_name]` — every visual
   must respond to all three.

**Page 2 — Sales by channel** (see `powerbi/previews/sales_by_channel.png`):
1. Donut chart: Total Revenue by `dim_channel[channel]` — In-store
   first.
2. Bar chart: Total Orders by channel.
3. Table: channel, Total Orders, Total Revenue, In-store Share %.

**Page 3 — Top products** (see `powerbi/previews/top_products.png`):
1. Bar chart: Total Revenue by `dim_product[product_name]`, top 10.
2. Donut chart: Total Revenue by `dim_product[category]`.
3. Table: product, category, Total Orders, Total Revenue — sorted
   by Total Revenue descending; Smartphone X1 on top.

**Page 4 — Daily trend** (see `powerbi/previews/daily_trend.png`):
1. Line chart: Total Revenue by `dim_date[order_date]`.
2. Column chart: Total Orders by `dim_date[order_date]`.
3. Card: best day (max daily revenue) and worst day, from the
   daily mart.

## 5. Check before you call it done

- KPI cards match the README: revenue PKR 38,573,539.50 · orders
  2,094 · AOV PKR 18,420.98 · orders per day 69.8 (on this SAMPLE
  data).
- Filter to one channel: every visual moves, and the KPI cards move
  too. If a visual does not move, its relationship is wrong — fix
  step 2.
- Filter to Groceries: the category shows 736 orders and
  PKR 4,411,786.75 — the busiest shelf, not the richest.
- Save as `.pbix` and publish/share from Power BI Service on a real
  order. To refresh on live data: drop the new daily CSVs into
  `data/raw/daily/`, run `python3 src/run_pipeline.py`, re-import
  `fact_orders.csv` (or point Power BI at the SQLite warehouse) and
  Refresh — the model and measures do not change.

## What the preview renders are

`powerbi/previews/*.png` are matplotlib renders of the same data,
made so this repo shows the dashboard without Power BI — regenerate
them any time with `python3 src/build_previews.py` (reads
`data/processed/pipeline.db`). They are labelled as renders in the
README and are **not** presented as Power BI screenshots. The real
screenshots come from the `.pbix` built above.
