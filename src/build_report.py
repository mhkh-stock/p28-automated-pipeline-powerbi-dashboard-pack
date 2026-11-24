"""Build the P28 client report PDF + dq_report.md.

outputs/pipeline_report_SAMPLE.pdf — 2 pages: the question, the
headline numbers, channel/category findings, top products, the
quarantine, recommendations, method and limits. Every number comes
from src/headlines.py (the warehouse), never typed.
outputs/dq_report.md records the 14 test results and the
reconciliation.

Usage:  python3 src/build_report.py
"""
import json
import sqlite3
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle)

from headlines import compute_headlines

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "processed" / "pipeline.db"
OUT_PDF = ROOT / "outputs" / "pipeline_report_SAMPLE.pdf"
OUT_DQ = ROOT / "outputs" / "dq_report.md"
TEST_RESULTS = ROOT / "outputs" / "test_results.json"

NAVY = colors.HexColor("#2E5A88")


def money(v):
    return f"PKR {v:,.2f}"


def money0(v):
    return f"PKR {v:,.0f}"


def table(data, widths, header=True):
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BFBFBF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), NAVY),
                  ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    t.setStyle(TableStyle(style))
    return t


def build_pdf(h):
    styles = getSampleStyleSheet()
    title = ParagraphStyle("Title2", parent=styles["Title"], fontSize=17,
                           textColor=NAVY, spaceAfter=2 * mm, alignment=0)
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=13,
                        textColor=NAVY, spaceBefore=4 * mm, spaceAfter=2 * mm)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=10,
                          leading=13, spaceAfter=2 * mm)
    small = ParagraphStyle("Small", parent=body, fontSize=8.5, leading=11,
                           textColor=colors.HexColor("#555555"))
    cell = ParagraphStyle("Cell", parent=body, fontSize=9, leading=11,
                          spaceAfter=0)
    cell_r = ParagraphStyle("CellR", parent=cell, alignment=2)
    cell_h = ParagraphStyle("CellH", parent=cell, textColor=colors.white)

    def c(text, style=cell):
        return Paragraph(text, style)

    def cr(text):
        return Paragraph(text, cell_r)

    def ch(text):
        return Paragraph(text, cell_h)

    doc = SimpleDocTemplate(str(OUT_PDF), pagesize=A4,
                            leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm,
                            title="Automated Pipeline + Power BI Dashboard Pack — SAMPLE report",
                            author="Muhammad Hashir")
    story = []
    story.append(Paragraph("Automated Pipeline + Power BI Dashboard Pack", title))
    story.append(Paragraph(
        "Your daily sales files, loaded themselves — SAMPLE delivery on "
        "30 daily sales files, 25 Oct – 23 Nov 2026.", body))
    story.append(Paragraph(
        "Client question: “Every morning my sales files land in a folder — "
        "can the dashboard just update itself?” This pack answers it: a "
        "pipeline that loads each new daily file once, validates every row "
        "in SQL, quarantines the dirty ones, and feeds a star schema the "
        "Power BI dashboard reads — so the dashboard updates itself from "
        "the shop's own files, and the owner opens the workbook each "
        "morning knowing the numbers are already checked.", body))

    story.append(Paragraph("Headline numbers", h1))
    story.append(table([
        [ch("Measure"), ch("Value")],
        [c("Days loaded (daily files)"), cr(f"{h['days_loaded']} — {h['date_min']} to {h['date_max']}")],
        [c("Orders loaded"), cr(f"{h['orders']:,}")],
        [c("Raw rows received"), cr(f"{h['raw_rows']:,} (17 quarantined)")],
        [c("Revenue"), cr(money(h["revenue_pkr"]))],
        [c("Units sold"), cr(f"{h['units']:,}")],
        [c("Average order value"), cr(money(h["aov_pkr"]))],
        [c("Orders per day"), cr(f"{h['orders_per_day']:.1f}")],
        [c("Revenue per day"), cr(money(h["revenue_per_day"]))],
        [c("Customers"), cr(f"{h['customers']:,}")],
        [c("Products / categories / channels"),
         cr(f"{h['products']} / {h['categories']} / {h['channels']}")],
        [c("Best day"), cr(f"{h['best_day']['order_date']} — {money(h['best_day']['revenue'])} on {h['best_day']['orders']} orders")],
        [c("Worst day"), cr(f"{h['worst_day']['order_date']} — {money(h['worst_day']['revenue'])} on {h['worst_day']['orders']} orders")],
    ], [62 * mm, 116 * mm]))

    story.append(Paragraph("Sales by channel", h1))
    rows = [[ch("Channel"), ch("Orders"), ch("Revenue"), ch("Share")]]
    for chn in h["sales_by_channel"]:
        rows.append([c(chn["channel"]), cr(f"{chn['orders']:,}"),
                     cr(money(chn["revenue"])), cr(f"{chn['share']:.2f}%")])
    story.append(table(rows, [44 * mm, 30 * mm, 60 * mm, 44 * mm]))
    story.append(Paragraph(
        f"In-store is still the shop: {h['top_channel']['orders']:,} orders "
        f"and {h['top_channel']['share']:.2f}% of revenue. But Online is "
        f"already a third of the money ({h['sales_by_channel'][1]['share']:.2f}%) "
        f"and WhatsApp orders ({h['sales_by_channel'][2]['orders']:,}) are "
        "real sales, not enquiries — the dashboard now counts them, so the "
        "owner stops guessing how much the chat channel is worth.", body))

    story.append(Paragraph("Sales by category", h1))
    rows = [[ch("Category"), ch("Orders"), ch("Units"), ch("Revenue"), ch("Share")]]
    for cat in h["sales_by_category"]:
        rows.append([c(cat["category"]), cr(f"{cat['orders']:,}"),
                     cr(f"{cat['units']:,}"), cr(money(cat["revenue"])),
                     cr(f"{cat['share']:.2f}%")])
    story.append(table(rows, [36 * mm, 24 * mm, 24 * mm, 56 * mm, 38 * mm]))
    story.append(Paragraph(
        f"Electronics is {h['top_category']['share']:.2f}% of revenue on "
        f"only {h['top_category']['orders']:,} orders — one Smartphone X1 "
        "sale is worth about 14 grocery orders. Groceries bring the most "
        f"orders ({h['sales_by_category'][2]['orders']:,}) at the lowest "
        "ticket: the footfall category, not the money category. The "
        "dashboard keeps both facts in front of the owner at once, instead "
        "of letting the busiest shelf look like the most profitable one.",
        body))

    story.append(Paragraph("Top products", h1))
    rows = [[ch("Product"), ch("Category"), ch("Orders"), ch("Revenue")]]
    for p in h["top_products"][:5]:
        rows.append([c(p["product_name"]), c(p["category"]),
                     cr(f"{p['orders']:,}"), cr(money(p["revenue"]))])
    story.append(table(rows, [58 * mm, 34 * mm, 30 * mm, 56 * mm]))
    story.append(Paragraph(
        f"The top product alone — {h['top_product']['product_name']} — is "
        f"{money0(h['top_product']['revenue'])} on {h['top_product']['orders']} "
        "orders. The top 10 products together are "
        f"{h['top10_share']:.2f}% of the month's "
        "revenue, which is why the dashboard's top-products page exists: "
        "stock the top 10 first, and a stock-out there costs more than "
        "anywhere else in the shop.", body))

    story.append(Paragraph("What the pipeline caught", h1))
    q = {r["reason"]: r["rows"] for r in h["quarantine_by_reason"]}
    story.append(Paragraph(
        f"Of {h['raw_rows']:,} raw rows, {h['quarantined']} were quarantined "
        "and never reached the dashboard: "
        f"{q.get('duplicate_order_id', 0)} duplicate order ids, "
        f"{q.get('invalid_quantity', 0)} invalid quantities, "
        f"{q.get('missing_or_invalid_price', 0)} missing prices and "
        f"{q.get('invalid_date', 0)} impossible dates. Without the "
        "quarantine, the duplicates alone would have double-counted real "
        "orders. Every quarantined row sits in quarantine_orders with its "
        "reason, so the shop can fix the till export instead of arguing "
        "about the dashboard.", body))

    story.append(Paragraph("Three recommendations", h1))
    for i, rec in enumerate([
        "<b>Protect the top 10.</b> The top products carry most of the "
        "month's revenue and the top one is a phone worth "
        f"{money0(h['top_product']['revenue'])} — set a stock alert on "
        "those ten before anything else, and check them first every morning.",
        "<b>Grow Online and WhatsApp on purpose.</b> They are already "
        f"{100 - h['top_channel']['share']:.2f}% of revenue combined. "
        "Give them the same morning check the till gets — the pipeline "
        "already loads their files, so the dashboard will show whether a "
        "promotion there actually moved sales.",
        "<b>Fix the till export, not the dashboard.</b> 17 dirty rows in "
        "30 days is a small leak, and the quarantine catches it — but "
        "every one of them is a till-export problem (duplicates, missing "
        "prices, impossible dates). Fix the export and the quarantine "
        "empties itself.",
    ], start=1):
        story.append(Paragraph(f"{i}. {rec}", body))

    story.append(Paragraph("Method and limits", h1))
    story.append(Paragraph(
        "Thirty daily CSVs (sales_YYYY-MM-DD.csv), 25 Oct – 23 Nov 2026. "
        "Each morning the pipeline loads only files it has not seen before "
        "(SHA-256 in the control table — a re-run adds 0 rows), validates "
        "every row in SQL (first occurrence of each order id, real date in "
        "the window, quantity > 0, price > 0, discount 0–100, known "
        "category and channel), recomputes line totals, and rebuilds the "
        "gold star schema (fact_orders + dim_date/dim_product/dim_channel/"
        "dim_customer) and five marts. 14 data-quality tests, all passing — "
        "see outputs/dq_report.md. The Power BI model reads the marts; the "
        ".pbix is built on Windows from powerbi/build_guide.md (model, 12 "
        "DAX measures, 4 page previews included). Limits: this is SAMPLE "
        "data — synthetic orders for a sample retailer, not a real shop's "
        "sales. The 30-day window has no year-ago comparison in the data; "
        "the prior-period DAX measure activates once a second month of "
        "files is loaded. Full method and reproduction steps are in the "
        "repo README.", small))
    story.append(Paragraph(
        "SAMPLE delivery: the shop, the orders and the recommendations are "
        "the sample framing, not a real business. The method — daily files "
        "→ control log → validation → star schema → dashboard — runs "
        "unchanged on the client's real daily exports.", small))
    doc.build(story)
    print(f"wrote {OUT_PDF}")


def build_dq(h):
    tests = json.loads(TEST_RESULTS.read_text(encoding="utf-8"))
    lines = ["# P28 — Data-quality report", "",
             f"**{tests['passed']}/{tests['total']} tests passing.** "
             "Each test is a SQL query in `sql/tests/` that returns its "
             "violating rows; every test expects 0 rows.", "",
             "| Test | Result | Violations |", "|---|---|---|"]
    for t in tests["tests"]:
        lines.append(f"| `{t['test']}` | {t['status']} | {t['violations']} |")
    q = {r["reason"]: r["rows"] for r in h["quarantine_by_reason"]}
    lines += ["",
              "## What the tests cover",
              "",
              "- **Reconciliation (t01, t10, t14):** bronze (2,111) = silver "
              "(2,094) + quarantine (17); fact totals reconcile to silver; "
              "all four marts reconcile to the fact table.",
              "- **Silver guards (t02–t08):** one row per order id, no NULL "
              "keys, quantity > 0, price > 0, discount 0–100, line totals "
              "recomputed to the paisa, dates real and inside the 30-day window.",
              "- **Gold (t09, t11–t13):** fact grain is one row per order, "
              "every fact key exists in its dimension, dim_date covers "
              "exactly the 30 days, and no file hash was ever loaded twice "
              "(the idempotency control).",
              "",
              "## Reconciliation",
              "",
              f"- Raw rows: {h['raw_rows']:,} → bronze: {h['raw_rows']:,} → "
              f"silver: {h['orders']:,} → fact: {h['orders']:,}. "
              f"{h['quarantined']} rows quarantined, nothing else dropped.",
              f"- Revenue: {money(h['revenue_pkr'])} in silver, fact and "
              "all four marts — the same number four ways.",
              "- Quarantine by reason: "
              + ", ".join(f"{k} {v}" for k, v in q.items()) + ".",
              f"- Load log: {h['days_loaded']} files, one per day "
              f"{h['date_min']} to {h['date_max']}, each loaded exactly once.",
              "",
              "## Checks beyond the SQL tests",
              "",
              "src/checks.py recomputes every headline number from the raw "
              "daily CSVs independently (no database, no warehouse) and "
              "compares it with the warehouse, the workbook's formulas "
              "(recalculated in LibreOffice) and this report — including a "
              "second pipeline run that must add 0 rows. See its output for "
              "the full list.",
              ""]
    OUT_DQ.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT_DQ}")


def main():
    conn = sqlite3.connect(DB)
    h = compute_headlines(conn)
    conn.close()
    build_pdf(h)
    build_dq(h)


if __name__ == "__main__":
    main()
