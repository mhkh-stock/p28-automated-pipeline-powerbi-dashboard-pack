-- P28 — silver model: promote bronze rows to silver_orders, quarantine
-- the rest. Run by src/run_pipeline.py AFTER the new daily files are
-- in bronze. Idempotent: every statement guards on bronze_rowid, so a
-- re-run promotes nothing twice.
--
-- Rules (a row is valid only if ALL hold):
--   * order_id present, and this is its FIRST occurrence in bronze
--     (later copies are duplicate_order_id)
--   * order_date a real calendar date inside the 30-day window
--     2026-10-25 .. 2026-11-23
--   * quantity a whole number > 0
--   * unit_price_pkr a number > 0
--   * discount_pct a number 0..100
--   * category one of Electronics / Groceries / Clothing / Home & Kitchen
--   * channel one of In-store / Online / WhatsApp
--   * customer_id, product_id, product_name present
-- line_total_pkr is RECOMPUTED here, never trusted from the file.

-- ---- 1. quarantine the rejects first (so silver can exclude them) ----
INSERT INTO quarantine_orders (
    order_id, order_date, customer_id, product_id, product_name,
    category, channel, quantity, unit_price_pkr, discount_pct,
    source_file, bronze_rowid, reason)
SELECT
    b.order_id, b.order_date, b.customer_id, b.product_id, b.product_name,
    b.category, b.channel, b.quantity, b.unit_price_pkr, b.discount_pct,
    b.source_file, b.rowid,
    CASE
        WHEN b.rowid <> (SELECT MIN(b2.rowid) FROM bronze_orders b2
                         WHERE b2.order_id = b.order_id)
            THEN 'duplicate_order_id'
        WHEN b.order_date IS NULL OR date(b.order_date) IS NULL
             OR b.order_date <> date(b.order_date)
             OR b.order_date NOT BETWEEN '2026-10-25' AND '2026-11-23'
            THEN 'invalid_date'
        WHEN b.quantity IS NULL OR TRIM(b.quantity) = ''
             OR b.quantity GLOB '*[^0-9]*'
             OR CAST(b.quantity AS INTEGER) <= 0
            THEN 'invalid_quantity'
        WHEN b.unit_price_pkr IS NULL OR TRIM(b.unit_price_pkr) = ''
             OR b.unit_price_pkr GLOB '*[^0-9.]*'
             OR b.unit_price_pkr LIKE '%.%.%'
             OR CAST(b.unit_price_pkr AS REAL) <= 0
            THEN 'missing_or_invalid_price'
        WHEN b.discount_pct IS NULL OR TRIM(b.discount_pct) = ''
             OR b.discount_pct GLOB '*[^0-9.]*'
             OR CAST(b.discount_pct AS REAL) < 0
             OR CAST(b.discount_pct AS REAL) > 100
            THEN 'invalid_discount'
        WHEN b.order_id IS NULL OR TRIM(b.order_id) = ''
             OR b.customer_id IS NULL OR TRIM(b.customer_id) = ''
             OR b.product_id IS NULL OR TRIM(b.product_id) = ''
             OR b.product_name IS NULL OR TRIM(b.product_name) = ''
            THEN 'missing_key'
        WHEN b.category NOT IN ('Electronics', 'Groceries', 'Clothing',
                                'Home & Kitchen')
             OR b.channel NOT IN ('In-store', 'Online', 'WhatsApp')
            THEN 'unknown_category_or_channel'
        ELSE 'invalid_row'
    END
FROM bronze_orders b
WHERE NOT EXISTS (
        SELECT 1 FROM quarantine_orders q WHERE q.bronze_rowid = b.rowid)
  AND (
        b.rowid <> (SELECT MIN(b2.rowid) FROM bronze_orders b2
                    WHERE b2.order_id = b.order_id)
        OR b.order_id IS NULL OR TRIM(b.order_id) = ''
        OR b.customer_id IS NULL OR TRIM(b.customer_id) = ''
        OR b.product_id IS NULL OR TRIM(b.product_id) = ''
        OR b.product_name IS NULL OR TRIM(b.product_name) = ''
        OR b.order_date IS NULL OR date(b.order_date) IS NULL
        OR b.order_date <> date(b.order_date)
        OR b.order_date NOT BETWEEN '2026-10-25' AND '2026-11-23'
        OR b.quantity IS NULL OR TRIM(b.quantity) = ''
        OR b.quantity GLOB '*[^0-9]*'
        OR CAST(b.quantity AS INTEGER) <= 0
        OR b.unit_price_pkr IS NULL OR TRIM(b.unit_price_pkr) = ''
        OR b.unit_price_pkr GLOB '*[^0-9.]*'
        OR b.unit_price_pkr LIKE '%.%.%'
        OR CAST(b.unit_price_pkr AS REAL) <= 0
        OR b.discount_pct IS NULL OR TRIM(b.discount_pct) = ''
        OR b.discount_pct GLOB '*[^0-9.]*'
        OR CAST(b.discount_pct AS REAL) < 0
        OR CAST(b.discount_pct AS REAL) > 100
        OR b.category NOT IN ('Electronics', 'Groceries', 'Clothing',
                              'Home & Kitchen')
        OR b.channel NOT IN ('In-store', 'Online', 'WhatsApp')
      );

-- ---- 2. silver: first occurrence of each order_id, valid only ----
INSERT INTO silver_orders (
    order_id, order_date, customer_id, product_id, product_name,
    category, channel, quantity, unit_price_pkr, discount_pct,
    line_total_pkr, source_file)
SELECT
    b.order_id, b.order_date, b.customer_id, b.product_id, b.product_name,
    b.category, b.channel,
    CAST(b.quantity AS INTEGER),
    CAST(b.unit_price_pkr AS REAL),
    CAST(b.discount_pct AS REAL),
    ROUND(CAST(b.quantity AS INTEGER) * CAST(b.unit_price_pkr AS REAL)
          * (1 - CAST(b.discount_pct AS REAL) / 100.0), 2),
    b.source_file
FROM bronze_orders b
WHERE b.rowid = (SELECT MIN(b2.rowid) FROM bronze_orders b2
                 WHERE b2.order_id = b.order_id)
  AND NOT EXISTS (
        SELECT 1 FROM silver_orders s WHERE s.order_id = b.order_id)
  AND NOT EXISTS (
        SELECT 1 FROM quarantine_orders q WHERE q.bronze_rowid = b.rowid);
