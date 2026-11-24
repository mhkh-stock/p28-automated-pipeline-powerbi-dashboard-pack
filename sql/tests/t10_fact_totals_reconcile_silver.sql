-- t10: fact revenue and order count reconcile exactly to silver.
SELECT 1 AS violation
WHERE (SELECT COUNT(*) FROM fact_orders) <> (SELECT COUNT(*) FROM silver_orders)
   OR ABS((SELECT COALESCE(SUM(line_total_pkr), 0) FROM fact_orders)
        - (SELECT COALESCE(SUM(line_total_pkr), 0) FROM silver_orders)) > 0.01;
