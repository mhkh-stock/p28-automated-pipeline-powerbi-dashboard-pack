-- t11: no NULL keys in the fact table, and every fact key exists in its dimension.
SELECT order_id FROM fact_orders
WHERE order_id IS NULL OR order_date IS NULL OR customer_id IS NULL
   OR product_id IS NULL OR category IS NULL OR channel IS NULL
   OR order_date NOT IN (SELECT order_date FROM dim_date)
   OR product_id NOT IN (SELECT product_id FROM dim_product)
   OR channel NOT IN (SELECT channel FROM dim_channel)
   OR customer_id NOT IN (SELECT customer_id FROM dim_customer);
