// P28 DAX measures — paste into Power BI Desktop (Modeling > New measure).
// Assumes tables fact_orders, dim_date, dim_product, dim_channel,
// dim_customer with the relationships in powerbi/model.md.
// All money is PKR. All measures are written against fact_orders;
// dimensions only filter.

// ---- KPI cards ----
Total Revenue = SUM(fact_orders[line_total_pkr])

Total Orders = DISTINCTCOUNT(fact_orders[order_id])

Total Units = SUM(fact_orders[quantity])

Average Order Value = DIVIDE([Total Revenue], [Total Orders])

Orders Per Day = DIVIDE([Total Orders], DISTINCTCOUNT(fact_orders[order_date]))

Revenue Per Day = DIVIDE([Total Revenue], DISTINCTCOUNT(fact_orders[order_date]))

// ---- Trend: vs the prior 30-day period ----
// dim_date ships a real date column (order_date, Date type on import),
// so DATEADD works with no extra setup. On this SAMPLE the window is
// a single 30 days, so Prior Period Revenue is blank until a second
// month of daily files is loaded — that is the honest behaviour, and
// the measure is written now so the dashboard never needs rebuilding.
Revenue Prior Period =
    CALCULATE([Total Revenue], DATEADD(dim_date[order_date], -30, DAY))

Revenue Growth vs Prior Period % =
    DIVIDE([Total Revenue] - [Revenue Prior Period], [Revenue Prior Period])

// ---- Mix ----
Top Category Revenue =
    MAXX(
        TOPN(1, VALUES(dim_product[category]),
            CALCULATE([Total Revenue])),
        [Total Revenue]
    )

Top Product Revenue =
    MAXX(
        TOPN(1, VALUES(dim_product[product_name]),
            CALCULATE([Total Revenue])),
        [Total Revenue]
    )

In-store Share % =
    DIVIDE(
        CALCULATE([Total Revenue], dim_channel[channel] = "In-store"),
        [Total Revenue]
    )

Online + WhatsApp Share % =
    DIVIDE(
        CALCULATE([Total Revenue],
            dim_channel[channel] IN { "Online", "WhatsApp" }),
        [Total Revenue]
    )
