"""P28 — the automated pipeline: daily CSVs -> bronze -> silver -> gold.

Scans data/raw/daily/ for sales_YYYY-MM-DD.csv files, loads each one
exactly once (tracked by SHA-256 in pipeline_load_log — a re-run
skips files already loaded, so the second run adds 0 rows), validates
every row in SQL (sql/silver_orders.sql), and rebuilds the gold star
schema + marts (fact_orders + dim_date/dim_product/dim_channel/
dim_customer).

  python3 src/run_pipeline.py            # incremental load (new files only)
  python3 src/run_pipeline.py --rebuild  # wipe the warehouse, load all 30 files fresh

The .db file is never committed; it rebuilds from these scripts.
"""
import argparse
import csv
import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "processed" / "pipeline.db"
RAW_DIR = ROOT / "data" / "raw" / "daily"
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "outputs"

FIELDS = ["order_id", "order_date", "customer_id", "product_id",
          "product_name", "category", "channel", "quantity",
          "unit_price_pkr", "discount_pct"]


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_sql(conn, path):
    conn.executescript(Path(path).read_text(encoding="utf-8"))


def export_csv(conn, table, path):
    cur = conn.execute(f"SELECT * FROM {table}")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true",
                    help="wipe the warehouse and load all files fresh")
    args = ap.parse_args()

    if args.rebuild and DB.exists():
        DB.unlink()
        print("rebuild: wiped pipeline.db")
    PROCESSED.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    fresh = not DB.exists()
    conn = sqlite3.connect(DB)
    if fresh:
        run_sql(conn, ROOT / "sql" / "schema.sql")
        print("created schema in pipeline.db")

    files = sorted(RAW_DIR.glob("sales_*.csv"))
    loaded_now = skipped = 0
    for path in files:
        h = file_hash(path)
        already = conn.execute(
            "SELECT COUNT(*) FROM pipeline_load_log WHERE file_hash = ?",
            (h,)).fetchone()[0]
        if already:
            skipped += 1
            continue
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        conn.executemany(
            "INSERT INTO bronze_orders (" + ", ".join(FIELDS) + ", source_file, file_hash) "
            "VALUES (" + ", ".join("?" * len(FIELDS)) + ", ?, ?)",
            [[r[c] for c in FIELDS] + [path.name, h] for r in rows])
        before_silver = conn.execute("SELECT COUNT(*) FROM silver_orders").fetchone()[0]
        before_quar = conn.execute("SELECT COUNT(*) FROM quarantine_orders").fetchone()[0]
        run_sql(conn, ROOT / "sql" / "silver_orders.sql")
        new_silver = conn.execute("SELECT COUNT(*) FROM silver_orders").fetchone()[0] - before_silver
        new_quar = conn.execute("SELECT COUNT(*) FROM quarantine_orders").fetchone()[0] - before_quar
        order_date = path.stem.replace("sales_", "")
        conn.execute(
            "INSERT INTO pipeline_load_log (file_name, file_hash, order_date, "
            "rows_in_file, rows_loaded, rows_quarantined, loaded_at, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'loaded')",
            (path.name, h, order_date, len(rows), new_silver, new_quar,
             datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")))
        conn.commit()
        loaded_now += 1
        print(f"loaded {path.name}: {len(rows)} rows "
              f"-> silver +{new_silver}, quarantine +{new_quar}")

    run_sql(conn, ROOT / "sql" / "gold_dimensions.sql")
    run_sql(conn, ROOT / "sql" / "gold_facts.sql")
    run_sql(conn, ROOT / "sql" / "gold_marts.sql")
    conn.commit()

    n = export_csv(conn, "fact_orders", PROCESSED / "fact_orders.csv")
    print(f"fact_orders: {n} rows -> data/processed/fact_orders.csv")
    for table in ["mart_sales_by_day", "mart_sales_by_channel",
                  "mart_sales_by_category", "mart_top_products",
                  "mart_sales_by_month"]:
        n = export_csv(conn, table, OUT / f"{table}.csv")
        print(f"{table}: {n} rows -> outputs/{table}.csv")

    for table in ["bronze_orders", "silver_orders", "quarantine_orders",
                  "fact_orders", "dim_date", "dim_product", "dim_channel",
                  "dim_customer", "pipeline_load_log"]:
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {n}")
    print(f"files loaded this run: {loaded_now}, skipped (already loaded): {skipped}")
    conn.close()
    print(f"wrote {DB}")


if __name__ == "__main__":
    main()
