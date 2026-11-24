-- t08: every silver date is a real calendar date inside the 30-day window.
SELECT order_id, order_date FROM silver_orders
WHERE date(order_date) IS NULL OR order_date <> date(order_date)
   OR order_date NOT BETWEEN '2026-10-25' AND '2026-11-23';
