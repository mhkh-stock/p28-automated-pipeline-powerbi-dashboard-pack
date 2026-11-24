-- P28 — gold dimensions. Rebuilt from silver on every pipeline run
-- (DELETE + INSERT), so a re-run converges on the same dimensions.

DELETE FROM dim_date;
INSERT INTO dim_date (order_date, year, month, month_name, day, weekday, is_weekend)
SELECT DISTINCT
    order_date,
    CAST(strftime('%Y', order_date) AS INTEGER),
    CAST(strftime('%m', order_date) AS INTEGER),
    CASE CAST(strftime('%m', order_date) AS INTEGER)
        WHEN 10 THEN 'October' WHEN 11 THEN 'November' END,
    CAST(strftime('%d', order_date) AS INTEGER),
    CASE CAST(strftime('%w', order_date) AS INTEGER)
        WHEN 0 THEN 'Sunday' WHEN 1 THEN 'Monday' WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday' WHEN 4 THEN 'Thursday'
        WHEN 5 THEN 'Friday' WHEN 6 THEN 'Saturday' END,
    CASE WHEN CAST(strftime('%w', order_date) AS INTEGER) IN (0, 6) THEN 1 ELSE 0 END
FROM silver_orders
ORDER BY order_date;

DELETE FROM dim_product;
INSERT INTO dim_product (product_id, product_name, category, unit_price_pkr)
SELECT product_id, MAX(product_name), MAX(category), MAX(unit_price_pkr)
FROM silver_orders
GROUP BY product_id;

DELETE FROM dim_channel;
INSERT INTO dim_channel (channel)
SELECT DISTINCT channel FROM silver_orders ORDER BY channel;

DELETE FROM dim_customer;
INSERT INTO dim_customer (customer_id, orders, total_spent_pkr)
SELECT customer_id, COUNT(*), ROUND(SUM(line_total_pkr), 2)
FROM silver_orders
GROUP BY customer_id;
