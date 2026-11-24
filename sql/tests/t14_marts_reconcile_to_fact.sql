-- t14: the marts add up to the fact table (by day, by channel, by category, by month).
SELECT 1 AS violation
WHERE ABS((SELECT COALESCE(SUM(revenue_pkr), 0) FROM mart_sales_by_day)
        - (SELECT COALESCE(SUM(line_total_pkr), 0) FROM fact_orders)) > 0.01
   OR ABS((SELECT COALESCE(SUM(revenue_pkr), 0) FROM mart_sales_by_channel)
        - (SELECT COALESCE(SUM(line_total_pkr), 0) FROM fact_orders)) > 0.01
   OR ABS((SELECT COALESCE(SUM(revenue_pkr), 0) FROM mart_sales_by_category)
        - (SELECT COALESCE(SUM(line_total_pkr), 0) FROM fact_orders)) > 0.01
   OR ABS((SELECT COALESCE(SUM(revenue_pkr), 0) FROM mart_sales_by_month)
        - (SELECT COALESCE(SUM(line_total_pkr), 0) FROM fact_orders)) > 0.01
   OR (SELECT COALESCE(SUM(orders), 0) FROM mart_sales_by_day)
   <> (SELECT COUNT(*) FROM fact_orders);
