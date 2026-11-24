"""P28 — headline numbers, computed once from the warehouse.

Single source of truth for the report PDF, the workbook and the
README figures: every consumer imports compute_headlines() instead
of re-typing numbers. src/checks.py deliberately does NOT use this
module — it recomputes the same numbers from the raw CSVs so a bug
here shows up as a mismatch.
"""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "processed" / "pipeline.db"


def compute_headlines(conn):
    h = {}
    h["orders"] = conn.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0]
    h["days_loaded"] = conn.execute(
        "SELECT COUNT(*) FROM pipeline_load_log").fetchone()[0]
    h["files_loaded"] = h["days_loaded"]
    h["raw_rows"] = conn.execute("SELECT COUNT(*) FROM bronze_orders").fetchone()[0]
    h["quarantined"] = conn.execute(
        "SELECT COUNT(*) FROM quarantine_orders").fetchone()[0]
    h["revenue_pkr"] = round(conn.execute(
        "SELECT COALESCE(SUM(line_total_pkr), 0) FROM fact_orders").fetchone()[0], 2)
    h["units"] = conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM fact_orders").fetchone()[0]
    h["aov_pkr"] = round(h["revenue_pkr"] / h["orders"], 2) if h["orders"] else 0
    h["orders_per_day"] = round(h["orders"] / h["days_loaded"], 2) if h["days_loaded"] else 0
    h["revenue_per_day"] = round(h["revenue_pkr"] / h["days_loaded"], 2) if h["days_loaded"] else 0
    h["customers"] = conn.execute(
        "SELECT COUNT(*) FROM dim_customer").fetchone()[0]
    h["products"] = conn.execute(
        "SELECT COUNT(*) FROM dim_product").fetchone()[0]
    h["categories"] = conn.execute(
        "SELECT COUNT(*) FROM mart_sales_by_category").fetchone()[0]
    h["channels"] = conn.execute(
        "SELECT COUNT(*) FROM mart_sales_by_channel").fetchone()[0]
    h["date_min"] = conn.execute(
        "SELECT MIN(order_date) FROM fact_orders").fetchone()[0]
    h["date_max"] = conn.execute(
        "SELECT MAX(order_date) FROM fact_orders").fetchone()[0]
    h["best_day"] = dict(zip(["order_date", "orders", "units", "revenue", "aov"],
        conn.execute("SELECT * FROM mart_sales_by_day "
                     "ORDER BY revenue_pkr DESC LIMIT 1").fetchone()))
    h["worst_day"] = dict(zip(["order_date", "orders", "units", "revenue", "aov"],
        conn.execute("SELECT * FROM mart_sales_by_day "
                     "ORDER BY revenue_pkr ASC LIMIT 1").fetchone()))
    h["top_category"] = dict(zip(["category", "orders", "units", "revenue", "share"],
        conn.execute("SELECT * FROM mart_sales_by_category "
                     "ORDER BY revenue_pkr DESC LIMIT 1").fetchone()))
    h["top_channel"] = dict(zip(["channel", "orders", "revenue", "share"],
        conn.execute("SELECT * FROM mart_sales_by_channel "
                     "ORDER BY revenue_pkr DESC LIMIT 1").fetchone()))
    h["top_product"] = dict(zip(["product_id", "product_name", "category",
                                 "orders", "units", "revenue"],
        conn.execute("SELECT * FROM mart_top_products "
                     "ORDER BY revenue_pkr DESC LIMIT 1").fetchone()))
    h["sales_by_day"] = [
        dict(zip(["order_date", "orders", "units", "revenue", "aov"], r))
        for r in conn.execute("SELECT * FROM mart_sales_by_day ORDER BY order_date")]
    h["sales_by_channel"] = [
        dict(zip(["channel", "orders", "revenue", "share"], r))
        for r in conn.execute("SELECT * FROM mart_sales_by_channel ORDER BY revenue_pkr DESC")]
    h["sales_by_category"] = [
        dict(zip(["category", "orders", "units", "revenue", "share"], r))
        for r in conn.execute("SELECT * FROM mart_sales_by_category ORDER BY revenue_pkr DESC")]
    h["top_products"] = [
        dict(zip(["product_id", "product_name", "category", "orders", "units", "revenue"], r))
        for r in conn.execute("SELECT * FROM mart_top_products ORDER BY revenue_pkr DESC")]
    h["top10_revenue"] = round(sum(p["revenue"] for p in h["top_products"]), 2)
    h["top10_share"] = round(h["top10_revenue"] / h["revenue_pkr"] * 100, 2) \
        if h["revenue_pkr"] else 0
    h["sales_by_month"] = [
        dict(zip(["month", "orders", "revenue"], r))
        for r in conn.execute("SELECT * FROM mart_sales_by_month ORDER BY month")]
    h["quarantine_by_reason"] = [
        {"reason": r[0], "rows": r[1]}
        for r in conn.execute("SELECT reason, COUNT(*) FROM quarantine_orders "
                              "GROUP BY reason ORDER BY COUNT(*) DESC")]
    h["load_log"] = [
        dict(zip(["file_name", "file_hash", "order_date", "rows_in_file",
                  "rows_loaded", "rows_quarantined", "loaded_at", "status"], r))
        for r in conn.execute("SELECT * FROM pipeline_load_log ORDER BY order_date")]
    h["weekend_vs_weekday"] = [
        {"day_type": "Weekend" if r[0] else "Weekday", "days": r[1],
         "orders": r[2], "revenue": round(r[3], 2)}
        for r in conn.execute(
            "SELECT d.is_weekend, COUNT(*), SUM(f.orders), SUM(f.revenue_pkr) "
            "FROM mart_sales_by_day f JOIN dim_date d USING (order_date) "
            "GROUP BY d.is_weekend ORDER BY d.is_weekend DESC")]
    return h


def main():
    conn = sqlite3.connect(DB)
    h = compute_headlines(conn)
    conn.close()
    out = ROOT / "outputs" / "analysis.json"
    out.write_text(json.dumps(h, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    for k in ["orders", "days_loaded", "raw_rows", "quarantined",
              "revenue_pkr", "aov_pkr", "customers", "products"]:
        print(f"  {k}: {h[k]}")


if __name__ == "__main__":
    main()
