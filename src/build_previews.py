"""Build the 4 Power BI page preview renders for P28 from the warehouse
marts. These are matplotlib renders of the same data the .pbix shows,
made so the repo shows the dashboard without Power BI — they are
labelled as renders in the README and are NOT presented as Power BI
screenshots. Regenerate any time with: python3 src/build_previews.py

1. overview.png — daily revenue bars + 7-day moving average (page 1).
2. sales_by_channel.png — revenue share donut by channel (page 2).
3. top_products.png — top 10 products by revenue (page 3).
4. daily_trend.png — daily orders + revenue, weekend shaded (page 4).
"""
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "processed" / "pipeline.db"
OUT = ROOT / "powerbi" / "previews"

BLUE = "#2E5A88"
NAVY = "#2E5A88"
LIGHT = "#7FA8C9"
ORANGE = "#D97A2B"
GREEN = "#2E7D5B"
GREY = "#6B7280"
CHAN_COLOURS = {"In-store": "#2E5A88", "Online": "#D97A2B", "WhatsApp": "#2E7D5B"}


def moving_avg(vals, n=7):
    out = []
    for i in range(len(vals)):
        window = vals[max(0, i - n + 1):i + 1]
        out.append(sum(window) / len(window))
    return out


def chart_overview(conn):
    rows = conn.execute(
        "SELECT order_date, revenue_pkr FROM mart_sales_by_day "
        "ORDER BY order_date").fetchall()
    dates = [r[0][5:] for r in rows]
    rev = [r[1] for r in rows]
    ma = moving_avg(rev)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(dates, rev, color=LIGHT, label="Daily revenue (PKR)")
    ax.plot(dates, ma, color=BLUE, linewidth=2, label="7-day moving average")
    ax.set_ylabel("Revenue (PKR)")
    ax.set_title("Overview — daily revenue, 30 days (SAMPLE)")
    ax.legend(frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", labelsize=7)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(OUT / "overview.png", dpi=150)
    plt.close(fig)
    print("overview.png")


def chart_channel(conn):
    rows = conn.execute(
        "SELECT channel, revenue_pkr, share_pct FROM mart_sales_by_channel "
        "ORDER BY revenue_pkr DESC").fetchall()
    labels = [f"{r[0]} — {r[2]:.1f}%" for r in rows]
    vals = [r[1] for r in rows]
    colours = [CHAN_COLOURS[r[0]] for r in rows]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    wedges, _, autotexts = ax.pie(
        vals, labels=labels, colors=colours, autopct="PKR %1.0f",
        pctdistance=0.8, startangle=90, counterclock=False,
        wedgeprops=dict(width=0.45, edgecolor="white"))
    for t in autotexts:
        t.set_fontsize(8)
    ax.set_title("Sales by channel — revenue share (SAMPLE)")
    fig.tight_layout()
    fig.savefig(OUT / "sales_by_channel.png", dpi=150)
    plt.close(fig)
    print("sales_by_channel.png")


def chart_top_products(conn):
    rows = conn.execute(
        "SELECT product_name, category, revenue_pkr FROM mart_top_products "
        "ORDER BY revenue_pkr ASC").fetchall()
    names = [f"{r[0]} ({r[1]})" for r in rows]
    rev = [r[2] for r in rows]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(names, rev, color=BLUE)
    for i, v in enumerate(rev):
        ax.text(v + max(rev) * 0.01, i, f"PKR {v:,.0f}", va="center", fontsize=9)
    ax.set_xlabel("Revenue (PKR)")
    ax.set_title("Top 10 products by revenue (SAMPLE)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "top_products.png", dpi=150)
    plt.close(fig)
    print("top_products.png")


def chart_daily_trend(conn):
    rows = conn.execute(
        "SELECT m.order_date, m.orders, m.revenue_pkr, d.is_weekend "
        "FROM mart_sales_by_day m JOIN dim_date d USING (order_date) "
        "ORDER BY m.order_date").fetchall()
    dates = [r[0][5:] for r in rows]
    orders = [r[1] for r in rows]
    rev = [r[2] for r in rows]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 5.5), sharex=True)
    ax1.bar(dates, orders, color=LIGHT)
    ax1.set_ylabel("Orders")
    ax1.set_title("Daily trend — orders and revenue, weekends shaded (SAMPLE)")
    ax2.plot(dates, rev, color=ORANGE, marker="o", markersize=3, linewidth=1.5)
    ax2.set_ylabel("Revenue (PKR)")
    for ax in (ax1, ax2):
        for i, r in enumerate(rows):
            if r[3]:
                ax.axvspan(i - 0.5, i + 0.5, color="#F2F2F2", zorder=0)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="x", labelsize=7)
    plt.setp(ax2.get_xticklabels(), rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(OUT / "daily_trend.png", dpi=150)
    plt.close(fig)
    print("daily_trend.png")


def chart_star_schema():
    """Star-schema diagram: fact_orders in the middle, four dimensions
    around it. Saved as powerbi/model_star_schema.png (referenced by
    powerbi/model.md)."""
    import matplotlib.patches as mpatches
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    def box(x, y, w, h, title, lines, colour):
        rect = mpatches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.08",
            facecolor=colour, edgecolor=NAVY, linewidth=1.2)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h - 0.28, title, ha="center", va="top",
                fontsize=10, fontweight="bold",
                color="white" if colour == BLUE else NAVY)
        for i, ln in enumerate(lines):
            ax.text(x + 0.18, y + h - 0.72 - i * 0.28, ln, fontsize=8,
                    va="top", color="white" if colour == BLUE else "#222222")

    box(3.35, 1.85, 3.3, 2.3, "fact_orders",
        ["order_id  PK", "order_date  FK", "customer_id  FK",
         "product_id  FK", "channel  FK", "line_total_pkr"], BLUE)
    box(0.2, 4.3, 2.7, 1.7, "dim_date",
        ["order_date  PK", "month_name", "weekday", "is_weekend"], LIGHT)
    box(7.1, 4.3, 2.7, 1.7, "dim_product",
        ["product_id  PK", "product_name", "category"], LIGHT)
    box(0.2, 0.0, 2.7, 1.7, "dim_channel",
        ["channel  PK"], LIGHT)
    box(7.1, 0.0, 2.7, 1.7, "dim_customer",
        ["customer_id  PK", "orders", "total_spent_pkr"], LIGHT)
    for (x1, y1, x2, y2) in [
            (2.9, 4.9, 3.9, 3.9), (7.1, 4.9, 6.1, 3.9),
            (2.9, 1.1, 3.9, 2.1), (7.1, 1.1, 6.1, 2.1)]:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color=NAVY, lw=1.2))
    ax.set_title("Star schema — fact_orders with four dimensions (SAMPLE)",
                 fontsize=12, color=NAVY, fontweight="bold")
    fig.tight_layout()
    fig.savefig(ROOT / "powerbi" / "model_star_schema.png", dpi=150)
    plt.close(fig)
    print("model_star_schema.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    chart_overview(conn)
    chart_channel(conn)
    chart_top_products(conn)
    chart_daily_trend(conn)
    conn.close()
    chart_star_schema()


if __name__ == "__main__":
    main()
