# P28 — Package Note (Fiverr-ready)

**Gig title:** I will build an automated sales pipeline and Power BI dashboard that updates itself from your daily files

**What the client gets:** a pipeline that loads their daily sales
CSVs by itself — every morning it scans the folder, loads only the
new file (tracked by hash, so a re-run never double-counts), validates
every row in SQL, quarantines the dirty ones with the reason, and
feeds a star-schema warehouse (fact + date/product/channel/customer
dimensions) that a Power BI dashboard reads — so the dashboard
updates itself from their own files. Plus a live-formula Excel
workbook (every headline number a formula over the full order list),
a 2-page report they can hand to the owner, the Power BI model with
12 DAX measures and a step-by-step build guide for the `.pbix`, 4
page preview renders, 14 data-quality tests with a pass/fail report,
a reconciliation proof (raw files → warehouse → workbook to the
paisa), and a 1-page owner guide (drop the new file in, run one
command, refresh). Delivered as a GitHub repo they can re-run
themselves.

**Honest note (in the repo, stated plainly):** this is a sample
delivery on synthetic data — a sample retailer, 30 daily files,
2,094 orders — the skill and the method are real, the shop is not.
The `.pbix` is built on the client's Windows machine from the
included model, DAX and build guide (a `.pbix` cannot be built on
Linux); the 4 preview renders show exactly what each page looks
like. The prior-period DAX measure stays blank until a second month
of daily files exists — that is the honest behaviour, and it fills
itself in once the files are there.

## Tiers (Hashir's band)

| Tier | Price | Delivery | Includes |
|---|---|---|---|
| Basic | $20 | 2 days | The pipeline on their daily files (up to 30 days): the validated warehouse (SQLite star schema), the control log proving each file loaded once, the quarantine report with every rejected row and its reason, the 14 data-quality tests with a pass/fail report |
| Standard | $65 | 4 days | Everything in Basic + the Power BI model (star schema, 12 DAX measures, 4-page layout, build guide for the `.pbix`), the live Excel workbook (full order list, headline numbers as formulas, daily table, channel + top-products sheets), the 2-page report PDF, the reconciliation proof (raw files → warehouse → workbook to the paisa) |
| Premium | $140 | 6 days | Everything in Standard + up to 90 days of daily files (or 3 shops' folders), the 4 page preview renders, a second month's load run a month later to show the prior-period comparison working, the owner guide (drop the file in, run one command, refresh), 1 revision round |

**What's NOT included:** building the `.pbix` on Linux (this service
ships the model + DAX + build guide and the client builds the
`.pbix` on Windows in ~20 minutes — building it for them on a
Windows machine is quoted separately); fixing their till/POS export
(this service quarantines the bad rows and names the cause — fixing
the export itself is quoted separately); a live cloud dashboard that
updates without anyone running a command (this service is a local
pipeline + a workbook + a Power BI model they refresh — a scheduled
cloud refresh is a different gig); changing their prices or stock
(this service shows them what their own files say — the
recommendations use their own numbers); real-time sales (this
service loads daily files each morning — intraday refresh is quoted
separately).

**Delivery time note:** counts from the day the client shares the
daily files (or a sample of them) and names the columns, not from
order placement.

**Proof this service works:** this repo's SAMPLE — 30 daily sales
files (25 Oct – 23 Nov 2026), 2,111 raw rows, 2,094 orders loaded,
17 rows quarantined (6 duplicate order ids, 6 invalid quantities,
3 missing prices, 2 impossible dates), revenue PKR 38,573,539.50 on
4,848 units, average order value PKR 18,420.98, 69.8 orders a day,
240 customers, 24 products, 4 categories, 3 channels, In-store
50.41% of revenue against Online 33.38% and WhatsApp 16.21%,
Electronics 65.04% of revenue on only 500 orders while Groceries
bring the most orders (736), the top product (Smartphone X1) alone
worth PKR 15,104,322.30 and the top 10 together 82.14% of the
month's revenue, best day 2026-11-20 at PKR 1,962,402.65 and worst
day 2026-10-30 at PKR 838,444.90, weekends running 77.0 orders a
day against 66.7 on weekdays, 14/14 data-quality tests passing, the
full verification suite passing including a LibreOffice
recalculation of the workbook with zero error values, a verified
2-page report PDF, and a second pipeline run that added 0 rows —
plus 3 recommendations the owner can act on: protect the top 10,
grow Online and WhatsApp on purpose, fix the till export not the
dashboard.
