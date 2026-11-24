-- t06: every discount sits in 0..100.
SELECT order_id, discount_pct FROM silver_orders
WHERE discount_pct IS NULL OR discount_pct < 0 OR discount_pct > 100;
