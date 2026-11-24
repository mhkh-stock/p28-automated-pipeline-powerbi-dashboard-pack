"""Build the P28 client workbook: outputs/pipeline_dashboard_SAMPLE.xlsx.

Sheets: Cover | Orders (2,094 orders, filterable) | Sales summary
(headline numbers as LIVE formulas over Orders + a daily table) |
Channel | Top products | Method. All numbers come from
src/headlines.py (the warehouse); the Summary sheet proves them a
second way with formulas, and src/checks.py recalculates the
workbook in LibreOffice and compares.

Usage:  python3 src/build_workbook.py
"""
import sqlite3
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from headlines import compute_headlines

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "processed" / "pipeline.db"
OUT = ROOT / "outputs" / "pipeline_dashboard_SAMPLE.xlsx"

NAVY = "2E5A88"
LIGHT = "DCE6F1"
TITLE_FONT = Font(name="Calibri", size=16, bold=True, color=NAVY)
H_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
HDR_FILL = PatternFill("solid", fgColor=NAVY)
MONEY = '"PKR" #,##0.00'
MONEY0 = '"PKR" #,##0'
PCT = '0.00%'
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def style_header(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = H_FONT
        cell.fill = HDR_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center",
                                   wrap_text=True)
        cell.border = BOX


def money(cell, fmt=MONEY):
    cell.number_format = fmt


def main():
    conn = sqlite3.connect(DB)
    h = compute_headlines(conn)
    rows = conn.execute(
        "SELECT order_id, order_date, customer_id, product_name, category, "
        "channel, quantity, unit_price_pkr, discount_pct, line_total_pkr "
        "FROM silver_orders ORDER BY order_date, order_id").fetchall()
    n = len(rows)
    last = n + 1  # last data row on Orders (header is row 1)
    conn.close()

    wb = Workbook()

    # ---------- Cover ----------
    ws = wb.active
    ws.title = "Cover"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToPage = True
    ws["A1"] = "Automated Pipeline + Power BI Dashboard Pack"
    ws["A1"].font = TITLE_FONT
    ws["A2"] = "Your daily sales files, loaded themselves — and the dashboard updates itself."
    ws["A2"].font = Font(name="Calibri", size=12, italic=True)
    ws["A3"] = ("SAMPLE delivery — 30 daily sales files (25 Oct – 23 Nov 2026), "
                "2,094 orders, 4 categories, 3 channels, PKR. Every morning the "
                "pipeline loads the new file into a star schema that feeds the "
                "Power BI dashboard, so the dashboard updates itself from the "
                "shop's own files. 17 dirty rows were quarantined, never loaded.")
    ws["A3"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells("A3:F3")
    ws.row_dimensions[3].height = 45
    ws["A5"] = "Headline numbers (live — change the Orders sheet and these move)"
    ws["A5"].font = Font(name="Calibri", size=11, bold=True)
    cover_rows = [
        ("Orders loaded", "='Sales summary'!B3"),
        ("Revenue (PKR)", "='Sales summary'!B4"),
        ("Average order value (PKR)", "='Sales summary'!B5"),
        ("Units sold", "='Sales summary'!B6"),
        ("Days loaded", "='Sales summary'!B7"),
        ("Orders per day", "='Sales summary'!B8"),
        ("Customers", "='Sales summary'!B10"),
        ("Best day revenue (PKR)", "='Sales summary'!B12"),
    ]
    for i, (label, formula) in enumerate(cover_rows):
        r = 6 + i
        ws.cell(row=r, column=1, value=label)
        c = ws.cell(row=r, column=2, value=formula)
        if "Revenue" in label or "value" in label:
            money(c)
        if label == "Orders per day":
            c.number_format = '0.00'
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 20
    ws["A15"] = ("How to use this file: Orders holds every loaded order "
                 "(filter it). Sales summary proves the headline numbers with "
                 "formulas and carries the daily table. Channel / Top products "
                 "hold the analysis. Method explains the pipeline, the "
                 "quarantine and what the pack cannot say.")
    ws["A15"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells("A15:F15")
    ws.row_dimensions[15].height = 45

    # ---------- Orders ----------
    od = wb.create_sheet("Orders")
    headers = ["Order ID", "Order date", "Customer ID", "Product", "Category",
               "Channel", "Quantity", "Unit price (PKR)", "Discount (%)",
               "Line total (PKR)"]
    od.append(headers)
    style_header(od, 1, len(headers))
    for r in rows:
        od.append(list(r))
    for row in od.iter_rows(min_row=2, max_row=last, min_col=8, max_col=8):
        for c in row:
            money(c)
    for row in od.iter_rows(min_row=2, max_row=last, min_col=10, max_col=10):
        for c in row:
            money(c)
    widths = [18, 12, 12, 26, 15, 11, 9, 16, 11, 16]
    for i, w in enumerate(widths, start=1):
        od.column_dimensions[get_column_letter(i)].width = w
    od.freeze_panes = "A2"
    od.auto_filter.ref = f"A1:J{last}"
    od.sheet_properties.pageSetUpPr.fitToPage = True
    od.page_setup.orientation = "landscape"
    od.page_setup.fitToWidth = 1

    # ---------- Sales summary (all formulas over Orders) ----------
    sm = wb.create_sheet("Sales summary")
    sm["A1"] = "Headline numbers — every value below is a formula over the Orders sheet"
    sm["A1"].font = Font(name="Calibri", size=11, bold=True)
    sm.merge_cells("A1:B1")
    OID = f"Orders!A2:A{last}"
    DATE = f"Orders!B2:B{last}"
    CUST = f"Orders!C2:C{last}"
    PROD = f"Orders!D2:D{last}"
    CAT = f"Orders!E2:E{last}"
    CHAN = f"Orders!F2:F{last}"
    QTY = f"Orders!G2:G{last}"
    TOTAL = f"Orders!J2:J{last}"
    distinct = (lambda rng:
                f'=SUMPRODUCT(({rng}<>"")/COUNTIF({rng},{rng}&""))')
    metrics = [
        ("Orders loaded", f"=ROWS({OID})", '0'),
        ("Revenue (PKR)", f"=SUM({TOTAL})", MONEY),
        ("Average order value (PKR)", "=B4/B3", MONEY),
        ("Units sold", f"=SUM({QTY})", '0'),
        ("Days loaded", distinct(DATE), '0'),
        ("Orders per day", "=B3/B7", '0.00'),
        ("Revenue per day (PKR)", "=B4/B7", MONEY),
        ("Customers", distinct(CUST), '0'),
        ("Products", distinct(PROD), '0'),
        ("Best day revenue (PKR)", "=MAX(D22:D51)", MONEY),
        ("Worst day revenue (PKR)", "=MIN(D22:D51)", MONEY),
        ("In-store revenue share", f'=SUMIF({CHAN},"In-store",{TOTAL})/B4', PCT),
        ("Online revenue share", f'=SUMIF({CHAN},"Online",{TOTAL})/B4', PCT),
        ("WhatsApp revenue share", f'=SUMIF({CHAN},"WhatsApp",{TOTAL})/B4', PCT),
        ("Electronics revenue share", f'=SUMIF({CAT},"Electronics",{TOTAL})/B4', PCT),
        ("Groceries orders", f'=COUNTIF({CAT},"Groceries")', '0'),
    ]
    sm.append(["Metric", "Value"])
    style_header(sm, 2, 2)
    for label, formula, fmt in metrics:
        sm.append([label, formula])
        if fmt:
            sm.cell(row=sm.max_row, column=2).number_format = fmt
    # Daily table (rows 20-22 header, 22-51 data, 52 total)
    sm["A20"] = "Daily sales (formulas over Orders — one row per loaded day)"
    sm["A20"].font = Font(name="Calibri", size=11, bold=True)
    sm.merge_cells("A20:E20")
    sm.append(["Date", "Orders", "Units", "Revenue (PKR)", "Avg order value (PKR)"])
    style_header(sm, 21, 5)
    for d in h["sales_by_day"]:
        r = sm.max_row + 1
        sm.cell(row=r, column=1, value=d["order_date"])
        sm.cell(row=r, column=2, value=f'=COUNTIF({DATE},A{r})')
        sm.cell(row=r, column=3, value=f'=SUMIF({DATE},A{r},{QTY})')
        sm.cell(row=r, column=4, value=f'=SUMIF({DATE},A{r},{TOTAL})')
        sm.cell(row=r, column=5, value=f'=IF(B{r}=0,0,D{r}/B{r})')
        sm.cell(row=r, column=4).number_format = MONEY
        sm.cell(row=r, column=5).number_format = MONEY
    total_row = sm.max_row + 1
    sm.cell(row=total_row, column=1, value="TOTAL")
    sm.cell(row=total_row, column=2, value=f"=SUM(B22:B{total_row - 1})")
    sm.cell(row=total_row, column=3, value=f"=SUM(C22:C{total_row - 1})")
    sm.cell(row=total_row, column=4, value=f"=SUM(D22:D{total_row - 1})")
    sm.cell(row=total_row, column=4).number_format = MONEY
    sm.cell(row=total_row, column=5, value=f"=D{total_row}/B{total_row}")
    sm.cell(row=total_row, column=5).number_format = MONEY
    for col in range(1, 6):
        sm.cell(row=total_row, column=col).font = Font(bold=True)
    sm.cell(row=total_row + 2, column=1,
            value="Best day").font = Font(bold=True)
    sm.cell(row=total_row + 2, column=2,
            value="=INDEX(A22:A51,MATCH(MAX(D22:D51),D22:D51,0))")
    sm.cell(row=total_row + 3, column=1,
            value="Worst day").font = Font(bold=True)
    sm.cell(row=total_row + 3, column=2,
            value="=INDEX(A22:A51,MATCH(MIN(D22:D51),D22:D51,0))")
    sm.column_dimensions["A"].width = 34
    sm.column_dimensions["B"].width = 20
    sm.column_dimensions["C"].width = 14
    sm.column_dimensions["D"].width = 20
    sm.column_dimensions["E"].width = 22

    # ---------- Channel ----------
    ch = wb.create_sheet("Channel")
    ch.append(["Channel", "Orders", "Revenue (PKR)", "Share"])
    style_header(ch, 1, 4)
    for c in h["sales_by_channel"]:
        ch.append([c["channel"], c["orders"], c["revenue"], c["share"] / 100])
        ch.cell(row=ch.max_row, column=3).number_format = MONEY
        ch.cell(row=ch.max_row, column=4).number_format = PCT
    total_row = ch.max_row + 1
    ch.cell(row=total_row, column=1, value="TOTAL")
    ch.cell(row=total_row, column=2, value=f"=SUM(B2:B{total_row - 1})")
    ch.cell(row=total_row, column=3, value=f"=SUM(C2:C{total_row - 1})")
    ch.cell(row=total_row, column=3).number_format = MONEY
    ch.cell(row=total_row, column=4, value=f"=SUM(D2:D{total_row - 1})")
    ch.cell(row=total_row, column=4).number_format = PCT
    for col in range(1, 5):
        ch.cell(row=total_row, column=col).font = Font(bold=True)
    ch.column_dimensions["A"].width = 14
    for col in "BCD":
        ch.column_dimensions[col].width = 18

    # ---------- Top products ----------
    tp = wb.create_sheet("Top products")
    tp.append(["Product", "Category", "Orders", "Units", "Revenue (PKR)"])
    style_header(tp, 1, 5)
    for p in h["top_products"]:
        tp.append([p["product_name"], p["category"], p["orders"],
                   p["units"], p["revenue"]])
        tp.cell(row=tp.max_row, column=5).number_format = MONEY
    total_row = tp.max_row + 1
    tp.cell(row=total_row, column=1, value="TOTAL (top 10)")
    tp.cell(row=total_row, column=3, value=f"=SUM(C2:C{total_row - 1})")
    tp.cell(row=total_row, column=4, value=f"=SUM(D2:D{total_row - 1})")
    tp.cell(row=total_row, column=5, value=f"=SUM(E2:E{total_row - 1})")
    tp.cell(row=total_row, column=5).number_format = MONEY
    for col in range(1, 6):
        tp.cell(row=total_row, column=col).font = Font(bold=True)
    tp.column_dimensions["A"].width = 26
    tp.column_dimensions["B"].width = 16
    for col in "CDE":
        tp.column_dimensions[col].width = 16

    # ---------- Method ----------
    md = wb.create_sheet("Method")
    md["A1"] = "Method, definitions and limits"
    md["A1"].font = Font(name="Calibri", size=11, bold=True)
    lines = [
        "Source: 30 daily sales CSVs (sales_YYYY-MM-DD.csv), 25 Oct – "
        "23 Nov 2026, one file per day from the shop's till export. "
        "2,111 raw rows; 2,094 loaded, 17 quarantined.",
        "Pipeline: each morning src/run_pipeline.py scans data/raw/daily/, "
        "loads only files it has not seen before (SHA-256 in the control "
        "table pipeline_load_log — a re-run adds 0 rows), validates every "
        "row in SQL, and rebuilds the gold star schema + marts.",
        "Validation: order_id present and first occurrence only (later "
        "copies are duplicates); real calendar date inside the 30-day "
        "window; quantity a whole number > 0; unit price a number > 0; "
        "discount 0–100; known category and channel. Line totals are "
        "recomputed (quantity x price x (1 - discount)), never trusted "
        "from the file.",
        "Quarantine: 17 rows rejected — 6 duplicate order ids, 6 invalid "
        "quantities (4 negative, 2 zero), 3 missing prices, 2 impossible "
        "dates. They sit in quarantine_orders with the reason, and never "
        "reach the fact table or the dashboard.",
        "Star schema: fact_orders (one row per order) + dim_date (30 days) "
        " / dim_product (24) / dim_channel (3) / dim_customer (240). The "
        "Power BI model reads the five marts in outputs/ — see powerbi/.",
        "Revenue is in PKR. Average order value = revenue / orders. "
        "Weekend = Friday–Sunday in this market (the shop's busy days).",
        "Limits: this is SAMPLE data — synthetic orders for a sample "
        "retailer, not a real shop's sales. The 30-day window covers "
        "25 Oct – 23 Nov 2026 only, so there is no year-ago comparison in "
        "the data itself; the DAX pack includes a prior-period measure "
        "that activates once a second month of files is loaded.",
        "Reproduce: python3 src/generate_data.py, then "
        "src/run_pipeline.py --rebuild, src/run_tests.py, "
        "src/build_previews.py, src/build_workbook.py, src/build_report.py, "
        "src/checks.py. The .db rebuilds from the scripts and is never "
        "committed.",
    ]
    for i, line in enumerate(lines):
        r = 3 + i
        md.cell(row=r, column=1, value=f"•  {line}")
        md.cell(row=r, column=1).alignment = Alignment(wrap_text=True, vertical="top")
        md.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
        md.row_dimensions[r].height = 30
    md.column_dimensions["A"].width = 110

    wb.save(OUT)
    print(f"wrote {OUT} ({n} orders, 6 sheets)")


if __name__ == "__main__":
    main()
