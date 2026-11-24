-- t04: every silver quantity is a whole number > 0.
SELECT order_id, quantity FROM silver_orders WHERE quantity <= 0;
