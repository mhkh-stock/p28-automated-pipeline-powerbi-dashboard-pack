-- t05: every silver unit price is > 0.
SELECT order_id, unit_price_pkr FROM silver_orders
WHERE unit_price_pkr IS NULL OR unit_price_pkr <= 0;
