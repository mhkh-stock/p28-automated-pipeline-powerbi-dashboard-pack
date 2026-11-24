-- t09: fact grain is one row per order_id.
SELECT order_id, COUNT(*) AS n FROM fact_orders
GROUP BY order_id HAVING COUNT(*) > 1;
