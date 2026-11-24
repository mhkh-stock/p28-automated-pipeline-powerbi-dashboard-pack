-- P28 — schema: bronze landing table + control log + silver +
-- quarantine + gold star-schema DDL.
-- Bronze loads each daily sales CSV exactly as the shop exported it
-- (all text, plus source file + file hash). Silver cleans it
-- (sql/silver_orders.sql); gold is built by sql/gold_dimensions.sql,
-- sql/gold_facts.sql and sql/gold_marts.sql.
-- SQLite. Run via src/run_pipeline.py (incremental, idempotent).

DROP TABLE IF EXISTS bronze_orders;
CREATE TABLE bronze_orders (
    order_id       TEXT,
    order_date     TEXT,
    customer_id    TEXT,
    product_id     TEXT,
    product_name   TEXT,
    category       TEXT,
    channel        TEXT,
    quantity       TEXT,
    unit_price_pkr TEXT,
    discount_pct   TEXT,
    source_file    TEXT NOT NULL,
    file_hash      TEXT NOT NULL
);

-- ---- control log: one row per daily file, by hash ----
DROP TABLE IF EXISTS pipeline_load_log;
CREATE TABLE pipeline_load_log (
    file_name   TEXT PRIMARY KEY,
    file_hash   TEXT NOT NULL UNIQUE,
    order_date  TEXT NOT NULL,
    rows_in_file INTEGER NOT NULL,
    rows_loaded INTEGER NOT NULL,
    rows_quarantined INTEGER NOT NULL,
    loaded_at   TEXT NOT NULL,
    status      TEXT NOT NULL
);

-- ---- silver ----
DROP TABLE IF EXISTS silver_orders;
CREATE TABLE silver_orders (
    order_id       TEXT PRIMARY KEY,
    order_date     TEXT NOT NULL,
    customer_id    TEXT NOT NULL,
    product_id     TEXT NOT NULL,
    product_name   TEXT NOT NULL,
    category       TEXT NOT NULL,
    channel        TEXT NOT NULL,
    quantity       INTEGER NOT NULL,
    unit_price_pkr REAL NOT NULL,
    discount_pct   REAL NOT NULL,
    line_total_pkr REAL NOT NULL,
    source_file    TEXT NOT NULL
);

-- ---- quarantine: rows silver rejected, with the reason ----
DROP TABLE IF EXISTS quarantine_orders;
CREATE TABLE quarantine_orders (
    order_id       TEXT,
    order_date     TEXT,
    customer_id    TEXT,
    product_id     TEXT,
    product_name   TEXT,
    category       TEXT,
    channel        TEXT,
    quantity       TEXT,
    unit_price_pkr TEXT,
    discount_pct   TEXT,
    source_file    TEXT NOT NULL,
    bronze_rowid   INTEGER NOT NULL,
    reason         TEXT NOT NULL
);

-- ---- gold star schema ----
DROP TABLE IF EXISTS dim_date;
CREATE TABLE dim_date (
    order_date  TEXT PRIMARY KEY,
    year        INTEGER NOT NULL,
    month       INTEGER NOT NULL,
    month_name  TEXT NOT NULL,
    day         INTEGER NOT NULL,
    weekday     TEXT NOT NULL,
    is_weekend  INTEGER NOT NULL
);

DROP TABLE IF EXISTS dim_product;
CREATE TABLE dim_product (
    product_id   TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category     TEXT NOT NULL,
    unit_price_pkr REAL NOT NULL
);

DROP TABLE IF EXISTS dim_channel;
CREATE TABLE dim_channel (
    channel TEXT PRIMARY KEY
);

DROP TABLE IF EXISTS dim_customer;
CREATE TABLE dim_customer (
    customer_id TEXT PRIMARY KEY,
    orders      INTEGER NOT NULL,
    total_spent_pkr REAL NOT NULL
);

DROP TABLE IF EXISTS fact_orders;
CREATE TABLE fact_orders (
    order_id       TEXT PRIMARY KEY,
    order_date     TEXT NOT NULL,
    customer_id    TEXT NOT NULL,
    product_id     TEXT NOT NULL,
    category       TEXT NOT NULL,
    channel        TEXT NOT NULL,
    quantity       INTEGER NOT NULL,
    unit_price_pkr REAL NOT NULL,
    discount_pct   REAL NOT NULL,
    line_total_pkr REAL NOT NULL
);

-- ---- gold marts ----
DROP TABLE IF EXISTS mart_sales_by_day;
CREATE TABLE mart_sales_by_day (
    order_date  TEXT PRIMARY KEY,
    orders      INTEGER NOT NULL,
    units       INTEGER NOT NULL,
    revenue_pkr REAL NOT NULL,
    avg_order_value_pkr REAL NOT NULL
);

DROP TABLE IF EXISTS mart_sales_by_channel;
CREATE TABLE mart_sales_by_channel (
    channel     TEXT PRIMARY KEY,
    orders      INTEGER NOT NULL,
    revenue_pkr REAL NOT NULL,
    share_pct   REAL NOT NULL
);

DROP TABLE IF EXISTS mart_sales_by_category;
CREATE TABLE mart_sales_by_category (
    category    TEXT PRIMARY KEY,
    orders      INTEGER NOT NULL,
    units       INTEGER NOT NULL,
    revenue_pkr REAL NOT NULL,
    share_pct   REAL NOT NULL
);

DROP TABLE IF EXISTS mart_top_products;
CREATE TABLE mart_top_products (
    product_id   TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category     TEXT NOT NULL,
    orders       INTEGER NOT NULL,
    units        INTEGER NOT NULL,
    revenue_pkr  REAL NOT NULL
);

DROP TABLE IF EXISTS mart_sales_by_month;
CREATE TABLE mart_sales_by_month (
    month       TEXT PRIMARY KEY,
    orders      INTEGER NOT NULL,
    revenue_pkr REAL NOT NULL
);
