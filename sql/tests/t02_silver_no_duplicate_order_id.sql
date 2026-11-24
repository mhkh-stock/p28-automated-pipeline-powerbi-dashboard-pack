-- t02: silver grain is one row per order_id.
SELECT order_id, COUNT(*) AS n FROM silver_orders
GROUP BY order_id HAVING COUNT(*) > 1;
