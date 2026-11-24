-- t03: no NULL join keys in silver.
SELECT order_id FROM silver_orders
WHERE order_id IS NULL OR order_date IS NULL OR customer_id IS NULL
   OR product_id IS NULL OR category IS NULL OR channel IS NULL;
