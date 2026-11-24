-- t07: line total = quantity x unit price x (1 - discount), to the paisa.
SELECT order_id, line_total_pkr FROM silver_orders
WHERE ABS(line_total_pkr
          - ROUND(quantity * unit_price_pkr * (1 - discount_pct / 100.0), 2)) > 0.01;
