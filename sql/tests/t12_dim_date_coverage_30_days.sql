-- t12: dim_date covers exactly the 30 days of the load window, no gaps.
SELECT 1 AS violation
WHERE (SELECT COUNT(*) FROM dim_date) <> 30
   OR (SELECT MIN(order_date) FROM dim_date) <> '2026-10-25'
   OR (SELECT MAX(order_date) FROM dim_date) <> '2026-11-23';
