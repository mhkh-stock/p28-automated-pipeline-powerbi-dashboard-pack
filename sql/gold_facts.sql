-- P28 — gold fact. Grain: one row per order (order_id). Rebuilt from
-- silver on every pipeline run, so a re-run converges on the same fact.

DELETE FROM fact_orders;
INSERT INTO fact_orders (
    order_id, order_date, customer_id, product_id, category, channel,
    quantity, unit_price_pkr, discount_pct, line_total_pkr)
SELECT
    order_id, order_date, customer_id, product_id, category, channel,
    quantity, unit_price_pkr, discount_pct, line_total_pkr
FROM silver_orders;
