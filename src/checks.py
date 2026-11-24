"""P28 — verification suite. Recomputes every headline number from
the raw daily CSVs independently (no database, no warehouse code)
and compares it with the warehouse, the workbook (recalculated in
LibreOffice), the report PDF and the README. A mistake in any one
of the four shows up as a failure.

Also checks: idempotency (a second pipeline run adds 0 rows),
file inventory, preview PNGs, the Power BI pack (12 DAX measures),
test_results.json (14/14), and that the .db is gitignored.

Usage:  python3 src/checks.py   (expect all checks passing)
"""
import csv
import json
import re
import shutil
import sqlite3
import statistics
import subprocess
import sys
from datetime import date
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "processed" / "pipeline.db"
RAW_DIR = ROOT / "data" / "raw" / "daily"
OUT = ROOT / "outputs"
XLSX = OUT / "pipeline_dashboard_SAMPLE.xlsx"
PDF = OUT / "pipeline_report_SAMPLE.pdf"

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))


def close(a, b, tol=0.01):
    return abs(a - b) <= tol


VALID_CATS = {"Electronics", "Groceries", "Clothing", "Home & Kitchen"}
VALID_CHAN = {"In-store", "Online", "WhatsApp"}


def valid_row(r, seen_ids):
    """The same validity rules as sql/silver_orders.sql, re-implemented
    in Python so a SQL slip shows up as a mismatch."""
    if not r["order_id"].strip():
        return "missing_key"
    if r["order_id"] in seen_ids:
        return "duplicate_order_id"
    try:
        d = date.fromisoformat(r["order_date"])
    except ValueError:
        return "invalid_date"
    if not (date(2026, 10, 25) <= d <= date(2026, 11, 23)):
        return "invalid_date"
    try:
        qty = int(r["quantity"])
        if str(qty) != r["quantity"].strip():
            raise ValueError
    except ValueError:
        return "invalid_quantity"
    if qty <= 0:
        return "invalid_quantity"
    try:
        price = float(r["unit_price_pkr"])
    except (ValueError, TypeError):
        return "missing_or_invalid_price"
    if price <= 0:
        return "missing_or_invalid_price"
    try:
        disc = float(r["discount_pct"])
    except (ValueError, TypeError):
        return "invalid_discount"
    if not (0 <= disc <= 100):
        return "invalid_discount"
    if not r["customer_id"].strip() or not r["product_id"].strip() \
            or not r["product_name"].strip():
        return "missing_key"
    if r["category"] not in VALID_CATS or r["channel"] not in VALID_CHAN:
        return "unknown_category_or_channel"
    return None


def main():
    # ---- 1. Independent recompute from the raw daily CSVs ----
    files = sorted(RAW_DIR.glob("sales_*.csv"))
    check("raw: 30 daily files", len(files) == 30, f"got {len(files)}")
    raw_rows = []
    for path in files:
        with open(path, newline="", encoding="utf-8") as f:
            raw_rows.extend(csv.DictReader(f))
    seen = set()
    clean, quar = [], {}
    for r in raw_rows:
        reason = valid_row(r, seen)
        if reason:
            quar[reason] = quar.get(reason, 0) + 1
        else:
            seen.add(r["order_id"])
            qty = int(r["quantity"])
            price = float(r["unit_price_pkr"])
            disc = float(r["discount_pct"])
            clean.append({
                "order_id": r["order_id"], "date": r["order_date"],
                "customer": r["customer_id"], "product": r["product_name"],
                "category": r["category"], "channel": r["channel"],
                "qty": qty,
                "total": round(qty * price * (1 - disc / 100), 2),
            })
    exp = {
        "raw_rows": len(raw_rows),
        "orders": len(clean),
        "quarantined": sum(quar.values()),
        "revenue": round(sum(c["total"] for c in clean), 2),
        "units": sum(c["qty"] for c in clean),
        "customers": len({c["customer"] for c in clean}),
        "products": len({c["product"] for c in clean}),
    }
    exp["aov"] = round(exp["revenue"] / exp["orders"], 2)
    exp["orders_per_day"] = round(exp["orders"] / 30, 2)
    exp["revenue_per_day"] = round(exp["revenue"] / 30, 2)
    check("raw: 2,111 rows", exp["raw_rows"] == 2111, str(exp["raw_rows"]))
    check("raw: 2,094 clean orders", exp["orders"] == 2094, str(exp["orders"]))
    check("raw: 17 quarantined rows", exp["quarantined"] == 17, str(exp["quarantined"]))
    check("raw: quarantine reasons 6/6/3/2",
          quar == {"duplicate_order_id": 6, "invalid_quantity": 6,
                   "missing_or_invalid_price": 3, "invalid_date": 2}, str(quar))
    check("raw: revenue PKR 38,573,539.50",
          close(exp["revenue"], 38573539.50), str(exp["revenue"]))
    check("raw: AOV PKR 18,420.98", close(exp["aov"], 18420.98), str(exp["aov"]))
    check("raw: 4,848 units", exp["units"] == 4848, str(exp["units"]))
    check("raw: 240 customers", exp["customers"] == 240, str(exp["customers"]))
    check("raw: 24 products", exp["products"] == 24, str(exp["products"]))
    by_day = {}
    for c in clean:
        by_day.setdefault(c["date"], []).append(c["total"])
    best = max(by_day, key=lambda d: sum(by_day[d]))
    worst = min(by_day, key=lambda d: sum(by_day[d]))
    check("raw: best day 2026-11-20 / PKR 1,962,402.65",
          best == "2026-11-20" and close(sum(by_day[best]), 1962402.65),
          f"{best} {sum(by_day[best]):,.2f}")
    check("raw: worst day 2026-10-30 / PKR 838,444.90",
          worst == "2026-10-30" and close(sum(by_day[worst]), 838444.90),
          f"{worst} {sum(by_day[worst]):,.2f}")
    chan = {}
    for c in clean:
        chan.setdefault(c["channel"], [0, 0.0])
        chan[c["channel"]][0] += 1
        chan[c["channel"]][1] += c["total"]
    check("raw: channel orders 1036/734/324",
          chan["In-store"][0] == 1036 and chan["Online"][0] == 734
          and chan["WhatsApp"][0] == 324, str({k: v[0] for k, v in chan.items()}))
    check("raw: channel revenue In-store 19,445,092.50",
          close(chan["In-store"][1], 19445092.50), f"{chan['In-store'][1]:,.2f}")
    cat = {}
    for c in clean:
        cat.setdefault(c["category"], [0, 0.0])
        cat[c["category"]][0] += 1
        cat[c["category"]][1] += c["total"]
    check("raw: Electronics 65.04% of revenue",
          close(cat["Electronics"][1] / exp["revenue"] * 100, 65.04),
          f"{cat['Electronics'][1] / exp['revenue'] * 100:.2f}%")
    check("raw: Groceries most orders (736)",
          cat["Groceries"][0] == 736, str(cat["Groceries"][0]))
    top_prod = max({c["product"]: sum(x["total"] for x in clean if x["product"] == c["product"])
                    for c in clean}.items(), key=lambda kv: kv[1])
    check("raw: top product Smartphone X1 / PKR 15,104,322.30",
          top_prod[0] == "Smartphone X1" and close(top_prod[1], 15104322.30),
          str(top_prod))

    # ---- 2. Warehouse agrees with the independent recompute ----
    conn = sqlite3.connect(DB)
    db = {
        "orders": conn.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0],
        "raw": conn.execute("SELECT COUNT(*) FROM bronze_orders").fetchone()[0],
        "quar": conn.execute("SELECT COUNT(*) FROM quarantine_orders").fetchone()[0],
        "revenue": round(conn.execute("SELECT SUM(line_total_pkr) FROM fact_orders").fetchone()[0], 2),
        "units": conn.execute("SELECT SUM(quantity) FROM fact_orders").fetchone()[0],
        "customers": conn.execute("SELECT COUNT(*) FROM dim_customer").fetchone()[0],
        "products": conn.execute("SELECT COUNT(*) FROM dim_product").fetchone()[0],
        "days": conn.execute("SELECT COUNT(*) FROM dim_date").fetchone()[0],
        "files": conn.execute("SELECT COUNT(*) FROM pipeline_load_log").fetchone()[0],
    }
    for key, exp_key in [("orders", "orders"), ("raw", "raw_rows"),
                         ("quar", "quarantined"), ("revenue", "revenue"),
                         ("units", "units"), ("customers", "customers"),
                         ("products", "products")]:
        check(f"db matches raw: {key}",
              close(db[key], exp[exp_key]) if isinstance(exp[exp_key], float)
              else db[key] == exp[exp_key],
              f"db={db[key]} raw={exp[exp_key]}")
    check("db: 30 days + 30 files in load log",
          db["days"] == 30 and db["files"] == 30, f"{db['days']}/{db['files']}")
    check("db: silver = fact row counts",
          conn.execute("SELECT COUNT(*) FROM silver_orders").fetchone()[0]
          == conn.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0])
    check("db: mart by day sums to fact revenue",
          close(conn.execute("SELECT SUM(revenue_pkr) FROM mart_sales_by_day").fetchone()[0],
                exp["revenue"]))
    check("db: top product is Smartphone X1",
          conn.execute("SELECT product_name FROM mart_top_products "
                       "ORDER BY revenue_pkr DESC LIMIT 1").fetchone()[0] == "Smartphone X1")
    check("db: months Oct 497 / Nov 1597",
          dict(conn.execute("SELECT month, orders FROM mart_sales_by_month").fetchall())
          == {"2026-10": 497, "2026-11": 1597})
    conn.close()

    # ---- 3. Idempotency: a second pipeline run adds 0 rows ----
    before = {}
    conn = sqlite3.connect(DB)
    for t in ["bronze_orders", "silver_orders", "quarantine_orders",
              "fact_orders", "pipeline_load_log"]:
        before[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    conn.close()
    r = subprocess.run([sys.executable, "src/run_pipeline.py"],
                       cwd=ROOT, capture_output=True, text=True, timeout=120)
    check("idempotency: second run exits 0", r.returncode == 0,
          r.stderr.strip()[-200:])
    check("idempotency: second run skipped all 30 files",
          "skipped (already loaded): 30" in r.stdout, r.stdout.strip().splitlines()[-1] if r.stdout else "")
    conn = sqlite3.connect(DB)
    for t, n in before.items():
        now = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        check(f"idempotency: {t} unchanged ({n})", now == n, f"now {now}")
    conn.close()

    # ---- 4. analysis.json agrees ----
    analysis = json.loads((OUT / "analysis.json").read_text())
    for key, exp_key in [("orders", "orders"), ("raw_rows", "raw_rows"),
                         ("quarantined", "quarantined"),
                         ("revenue_pkr", "revenue"), ("units", "units"),
                         ("aov_pkr", "aov"), ("customers", "customers"),
                         ("products", "products")]:
        check(f"analysis.json matches raw: {key}",
              close(analysis[key], exp[exp_key]) if isinstance(exp[exp_key], float)
              else analysis[key] == exp[exp_key],
              f"{analysis[key]} vs {exp[exp_key]}")

    # ---- 5. test_results.json ----
    tests = json.loads((OUT / "test_results.json").read_text())
    check("test_results.json: 14/14 passing",
          tests["total"] == 14 and tests["passed"] == 14,
          f"{tests['passed']}/{tests['total']}")
    check("test_results.json: no FAIL entries",
          all(t["status"] == "PASS" for t in tests["tests"]))

    # ---- 6. Workbook: LibreOffice recalc ----
    recalc_dir = OUT / ".recalc"
    if recalc_dir.exists():
        shutil.rmtree(recalc_dir)
    recalc_dir.mkdir()
    r = subprocess.run(["soffice", "--headless", "--calc", "--convert-to", "xlsx",
                        "--outdir", str(recalc_dir), str(XLSX)],
                       capture_output=True, text=True, timeout=180)
    check("libreoffice recalc ran", r.returncode == 0, r.stderr.strip()[:200])
    recalc = recalc_dir / XLSX.name
    wb = load_workbook(recalc, data_only=True)
    check("workbook: 6 sheets",
          wb.sheetnames == ["Cover", "Orders", "Sales summary", "Channel",
                            "Top products", "Method"],
          str(wb.sheetnames))
    od = wb["Orders"]
    check("workbook: Orders has 2,094 orders + header",
          od.max_row == 2095, str(od.max_row))
    check("workbook: Orders line-total sum matches revenue",
          close(sum(c.value for c in od["J"][1:]), exp["revenue"]),
          f"{sum(c.value for c in od['J'][1:]):,.2f}")
    sm = wb["Sales summary"]
    expected_summary = {
        "B3": 2094, "B4": 38573539.50, "B5": 18420.98, "B6": 4848,
        "B7": 30, "B8": 69.80, "B9": 1285784.65, "B10": 240, "B11": 24,
        "B12": 1962402.65, "B13": 838444.90, "B14": 0.5041, "B15": 0.3338,
        "B16": 0.1621, "B17": 0.6504, "B18": 736,
    }
    for cell, val in expected_summary.items():
        got = sm[cell].value
        ok = close(got, val) if isinstance(val, float) else got == val
        check(f"workbook Summary {cell} = {val}", ok, f"got {got}")
    check("workbook: daily table totals B52/D52 match",
          sm["B52"].value == 2094 and close(sm["D52"].value, 38573539.50),
          f"B52={sm['B52'].value} D52={sm['D52'].value}")
    check("workbook: best day label is 2026-11-20",
          sm["B54"].value == "2026-11-20", str(sm["B54"].value))
    check("workbook: worst day label is 2026-10-30",
          sm["B55"].value == "2026-10-30", str(sm["B55"].value))
    errors = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("#"):
                    errors.append(f"{ws.title}!{c.coordinate}={c.value}")
    check("workbook: zero error values after recalc", not errors, "; ".join(errors[:5]))
    cv = wb["Cover"]
    check("workbook Cover B6 (orders) = 2,094", cv["B6"].value == 2094, str(cv["B6"].value))
    check("workbook Cover B7 (revenue) matches",
          close(cv["B7"].value, 38573539.50), str(cv["B7"].value))
    wb_src = load_workbook(XLSX, data_only=False)
    check("workbook source: Summary values are formulas",
          isinstance(wb_src["Sales summary"]["B3"].value, str)
          and wb_src["Sales summary"]["B3"].value.startswith("="))
    check("workbook source: Cover values are formulas",
          isinstance(wb_src["Cover"]["B6"].value, str)
          and wb_src["Cover"]["B6"].value.startswith("="))
    check("workbook source: daily table values are formulas",
          isinstance(wb_src["Sales summary"]["B22"].value, str)
          and wb_src["Sales summary"]["B22"].value.startswith("=COUNTIF"))
    shutil.rmtree(recalc_dir)

    # ---- 7. Preview PNGs + star-schema diagram ----
    for rel in ["powerbi/previews/overview.png",
                "powerbi/previews/sales_by_channel.png",
                "powerbi/previews/top_products.png",
                "powerbi/previews/daily_trend.png",
                "powerbi/model_star_schema.png"]:
        p = ROOT / rel
        ok = p.exists() and p.stat().st_size > 10000 \
            and p.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
        check(f"preview PNG exists and is a PNG: {rel}", ok,
              f"{p.stat().st_size if p.exists() else 0} bytes")

    # ---- 8. PDF report ----
    check("report PDF exists", PDF.exists() and PDF.stat().st_size > 1000)
    info = subprocess.run(["pdfinfo", str(PDF)], capture_output=True, text=True)
    pages = re.search(r"Pages:\s+(\d+)", info.stdout)
    check("report PDF is 2 pages", pages and pages.group(1) == "2",
          pages.group(0) if pages else info.stderr[:100])
    text = subprocess.run(["pdftotext", str(PDF), "-"],
                          capture_output=True, text=True).stdout
    for needle in ["2,094", "PKR 38,573,539.50", "18,420.98", "Smartphone X1",
                   "50.41%", "65.04%", "17", "2026-11-20"]:
        check(f"report PDF contains {needle!r}", needle in text)

    # ---- 9. Power BI pack ----
    dax = (ROOT / "powerbi" / "dax_measures.md").read_text()
    measures = [ln for ln in dax.splitlines()
                if ln and not ln.startswith("//")
                and re.match(r"^[A-Za-z][A-Za-z +\%&-]+ =", ln)]
    check("powerbi: 12 DAX measures", len(measures) == 12, f"got {len(measures)}")
    for name in ["Total Revenue", "Total Orders", "Average Order Value",
                 "Revenue Prior Period", "Revenue Growth vs Prior Period %",
                 "Top Category Revenue", "In-store Share %"]:
        check(f"powerbi: DAX measure present — {name}", name in dax)
    model = (ROOT / "powerbi" / "model.md").read_text()
    check("powerbi: model.md has the star-schema diagram",
          "```mermaid" in model and "fact_orders" in model)
    guide = (ROOT / "powerbi" / "build_guide.md").read_text()
    check("powerbi: build guide covers import + relationships + measures",
          "Import" in guide and "Relationships" in guide and "Measures" in guide)

    # ---- 10. File inventory + repo hygiene ----
    for rel in ["README.md", "PACKAGE-NOTE.md", "requirements.txt",
                ".gitignore", "data/README.md",
                "data/processed/fact_orders.csv",
                "sql/schema.sql", "sql/silver_orders.sql",
                "sql/gold_dimensions.sql", "sql/gold_facts.sql",
                "sql/gold_marts.sql", "src/generate_data.py",
                "src/run_pipeline.py", "src/run_tests.py",
                "src/build_previews.py", "src/build_workbook.py",
                "src/build_report.py", "src/headlines.py", "src/checks.py",
                "outputs/analysis.json", "outputs/test_results.json",
                "outputs/dq_report.md", "powerbi/model.md",
                "powerbi/dax_measures.md", "powerbi/build_guide.md"]:
        check(f"file exists: {rel}", (ROOT / rel).exists())
    for name in ["mart_sales_by_day.csv", "mart_sales_by_channel.csv",
                 "mart_sales_by_category.csv", "mart_top_products.csv",
                 "mart_sales_by_month.csv"]:
        check(f"mart CSV exists: {name}", (OUT / name).exists())
    check("tests dir has 14 SQL files",
          len(list((ROOT / "sql" / "tests").glob("*.sql"))) == 14)
    check("raw dir has 30 daily CSVs",
          len(list(RAW_DIR.glob("sales_*.csv"))) == 30)
    gitignore = (ROOT / ".gitignore").read_text()
    check(".gitignore excludes *.db", "*.db" in gitignore)
    check(".db exists locally (never uploaded)", DB.exists())
    req = (ROOT / "requirements.txt").read_text()
    for pkg in ["openpyxl==", "reportlab==", "matplotlib==", "pandas=="]:
        check(f"requirements pins {pkg}", pkg in req)

    # ---- 11. README numbers match the verified outputs ----
    readme = (ROOT / "README.md").read_text()
    for needle in ["2,094", "30 daily", "PKR 38,573,539.50", "18,420.98",
                   "4,848", "69.8", "240", "24 products", "14/14",
                   "17 quarantined", "Smartphone X1", "50.41%", "65.04%",
                   "2026-11-20", "1,962,402.65"]:
        check(f"README contains {needle!r}", needle in readme)

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n{passed}/{total} checks passing")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
