-- P28 — gold marts (the tables the Power BI model reads). Rebuilt
-- from the fact table on every pipeline run.

DELETE FROM mart_sales_by_day;
INSERT INTO mart_sales_by_day
    (order_date, orders, units, revenue_pkr, avg_order_value_pkr)
SELECT order_date, COUNT(*), SUM(quantity),
       ROUND(SUM(line_total_pkr), 2),
       ROUND(SUM(line_total_pkr) * 1.0 / COUNT(*), 2)
FROM fact_orders
GROUP BY order_date
ORDER BY order_date;

DELETE FROM mart_sales_by_channel;
INSERT INTO mart_sales_by_channel
    (channel, orders, revenue_pkr, share_pct)
SELECT channel, COUNT(*) AS orders, ROUND(SUM(line_total_pkr), 2) AS revenue_pkr,
       ROUND(SUM(line_total_pkr) * 100.0
             / (SELECT SUM(line_total_pkr) FROM fact_orders), 2)
FROM fact_orders
GROUP BY channel
ORDER BY revenue_pkr DESC;

DELETE FROM mart_sales_by_category;
INSERT INTO mart_sales_by_category
    (category, orders, units, revenue_pkr, share_pct)
SELECT category, COUNT(*) AS orders, SUM(quantity) AS units, ROUND(SUM(line_total_pkr), 2) AS revenue_pkr,
       ROUND(SUM(line_total_pkr) * 100.0
             / (SELECT SUM(line_total_pkr) FROM fact_orders), 2)
FROM fact_orders
GROUP BY category
ORDER BY revenue_pkr DESC;

DELETE FROM mart_top_products;
INSERT INTO mart_top_products
    (product_id, product_name, category, orders, units, revenue_pkr)
SELECT f.product_id, d.product_name, MAX(f.category), COUNT(*) AS orders,
       SUM(f.quantity), ROUND(SUM(f.line_total_pkr), 2) AS revenue_pkr
FROM fact_orders f JOIN dim_product d USING (product_id)
GROUP BY f.product_id, d.product_name
ORDER BY revenue_pkr DESC
LIMIT 10;

DELETE FROM mart_sales_by_month;
INSERT INTO mart_sales_by_month (month, orders, revenue_pkr)
SELECT strftime('%Y-%m', order_date), COUNT(*),
       ROUND(SUM(line_total_pkr), 2)
FROM fact_orders
GROUP BY strftime('%Y-%m', order_date)
ORDER BY 1;
