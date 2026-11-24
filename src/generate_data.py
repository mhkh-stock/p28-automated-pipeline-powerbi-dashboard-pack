"""P28 — generate the SAMPLE daily sales CSVs.

A small retailer ("NoorMart", SAMPLE) exports one sales CSV per day
from the till. 30 days, 2026-10-25 .. 2026-11-23, one file per day in
data/raw/daily/sales_YYYY-MM-DD.csv. Synthetic, deterministic
(seed 28): re-running this script regenerates byte-identical files.

Each row is one order (one product line). Columns are exactly what
the shop's till exports: order_id, order_date, customer_id,
product_id, product_name, category, channel, quantity,
unit_price_pkr, discount_pct.

17 rows are deliberately dirty (spread across the month) so the
pipeline's validation has real work to do — they land in quarantine,
never in the fact table:
  * 6 duplicate order_id rows (exact copies of real orders)
  * 4 negative quantities, 2 zero quantities
  * 3 missing unit prices
  * 2 impossible dates (2026-13-40)

Usage:  python3 src/generate_data.py
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "raw" / "daily"

SEED = 28
START = date(2026, 10, 25)
DAYS = 30

PRODUCTS = [
    # (product_id, name, category, unit_price_pkr)
    ("E01", "Smartphone X1", "Electronics", 84999),
    ("E02", "Wireless Earbuds", "Electronics", 5999),
    ("E03", "LED TV 32 inch", "Electronics", 42999),
    ("E04", "Laptop Stand", "Electronics", 3499),
    ("E05", "Power Bank 10000mAh", "Electronics", 3999),
    ("E06", "Bluetooth Speaker", "Electronics", 7499),
    ("G01", "Basmati Rice 5kg", "Groceries", 2899),
    ("G02", "Cooking Oil 5L", "Groceries", 3299),
    ("G03", "Whole Wheat Flour 10kg", "Groceries", 1499),
    ("G04", "Green Tea 100ct", "Groceries", 899),
    ("G05", "Dates Ajwa 500g", "Groceries", 2499),
    ("G06", "Desi Ghee 1kg", "Groceries", 1899),
    ("C01", "Men's Kurta", "Clothing", 3499),
    ("C02", "Lawn Suit 3pc", "Clothing", 4999),
    ("C03", "Wool Shawl", "Clothing", 2799),
    ("C04", "Kids Frock", "Clothing", 1999),
    ("C05", "Men's Shalwar Kameez", "Clothing", 2999),
    ("C06", "Winter Jacket", "Clothing", 6999),
    ("H01", "Dinner Set 24pc", "Home & Kitchen", 12999),
    ("H02", "Non-stick Cookware Set", "Home & Kitchen", 8999),
    ("H03", "Bed Sheet King", "Home & Kitchen", 2499),
    ("H04", "LED Bulb Pack of 4", "Home & Kitchen", 1199),
    ("H05", "Water Dispenser", "Home & Kitchen", 14999),
    ("H06", "Steam Iron", "Home & Kitchen", 5999),
]

CATEGORIES = ["Electronics", "Groceries", "Clothing", "Home & Kitchen"]
CAT_W = [0.25, 0.35, 0.22, 0.18]
CHANNELS = ["In-store", "Online", "WhatsApp"]
CHAN_W = [0.50, 0.35, 0.15]
DISCOUNTS = [0, 0, 0, 5, 5, 10, 10, 15]

FIELDS = ["order_id", "order_date", "customer_id", "product_id",
          "product_name", "category", "channel", "quantity",
          "unit_price_pkr", "discount_pct"]


def main():
    rng = random.Random(SEED)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("sales_*.csv"):
        old.unlink()

    customers = [f"CUST-{i:04d}" for i in range(1, 241)]
    by_cat = {c: [p for p in PRODUCTS if p[2] == c] for c in CATEGORIES}

    all_clean = []  # (day_index, row) — pool to copy duplicates from
    total_clean = 0
    for d in range(DAYS):
        day = START + timedelta(days=d)
        # Weekend uplift: Fri/Sat/Sun are the busy days in this market.
        base = 66
        if day.weekday() in (4, 5, 6):
            base = 78
        n = base + rng.randint(-6, 6)
        rows = []
        for i in range(1, n + 1):
            cat = rng.choices(CATEGORIES, weights=CAT_W)[0]
            pid, name, _, price = rng.choice(by_cat[cat])
            qty = rng.randint(1, 5) if cat == "Groceries" else rng.randint(1, 3)
            row = {
                "order_id": f"ORD-{day:%Y%m%d}-{i:04d}",
                "order_date": day.isoformat(),
                "customer_id": rng.choice(customers),
                "product_id": pid,
                "product_name": name,
                "category": cat,
                "channel": rng.choices(CHANNELS, weights=CHAN_W)[0],
                "quantity": qty,
                "unit_price_pkr": price,
                "discount_pct": rng.choice(DISCOUNTS),
            }
            rows.append(row)
            all_clean.append((d, row))
        total_clean += n
        with open(OUT_DIR / f"sales_{day:%Y-%m-%d}.csv", "w",
                  newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
    print(f"clean orders: {total_clean} across {DAYS} daily files")

    # ---- inject the 17 dirty rows, spread across the month ----
    # (day_index, kind, source row) — duplicates copy real orders.
    dup_src = [rng.choice(all_clean) for _ in range(6)]
    plan = [
        (2, "duplicate", dup_src[0][1]),
        (4, "negative_qty", None),
        (6, "duplicate", dup_src[1][1]),
        (8, "missing_price", None),
        (10, "duplicate", dup_src[2][1]),
        (12, "zero_qty", None),
        (14, "negative_qty", None),
        (16, "duplicate", dup_src[3][1]),
        (18, "missing_price", None),
        (20, "bad_date", None),
        (22, "duplicate", dup_src[4][1]),
        (24, "negative_qty", None),
        (25, "missing_price", None),
        (26, "duplicate", dup_src[5][1]),
        (27, "zero_qty", None),
        (28, "negative_qty", None),
        (29, "bad_date", None),
    ]
    made = {"duplicate": 0, "negative_qty": 0, "zero_qty": 0,
            "missing_price": 0, "bad_date": 0}
    for day_idx, kind, src in plan:
        day = START + timedelta(days=day_idx)
        path = OUT_DIR / f"sales_{day:%Y-%m-%d}.csv"
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if kind == "duplicate":
            bad = dict(src)
        else:
            cat = rng.choice(CATEGORIES)
            pid, name, _, price = rng.choice(by_cat[cat])
            bad = {
                "order_id": f"ORD-{day:%Y%m%d}-BAD{day_idx:02d}",
                "order_date": day.isoformat(),
                "customer_id": rng.choice(customers),
                "product_id": pid,
                "product_name": name,
                "category": cat,
                "channel": rng.choice(CHANNELS),
                "quantity": 2,
                "unit_price_pkr": price,
                "discount_pct": 0,
            }
            if kind == "negative_qty":
                bad["quantity"] = -2
            elif kind == "zero_qty":
                bad["quantity"] = 0
            elif kind == "missing_price":
                bad["unit_price_pkr"] = ""
            elif kind == "bad_date":
                bad["order_date"] = "2026-13-40"
        rows.append(bad)
        made[kind] += 1
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
    print(f"dirty rows injected: {sum(made.values())} {made}")
    print(f"total raw rows: {total_clean + sum(made.values())}")
    print(f"wrote {DAYS} files -> {OUT_DIR}")


if __name__ == "__main__":
    main()
