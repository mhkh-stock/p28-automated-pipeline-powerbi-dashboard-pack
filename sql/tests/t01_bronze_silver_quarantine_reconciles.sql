-- t01: every bronze row is either silver or quarantined — nothing lost, nothing added.
SELECT 1 AS violation
WHERE (SELECT COUNT(*) FROM bronze_orders)
   <> (SELECT COUNT(*) FROM silver_orders)
    + (SELECT COUNT(*) FROM quarantine_orders);
