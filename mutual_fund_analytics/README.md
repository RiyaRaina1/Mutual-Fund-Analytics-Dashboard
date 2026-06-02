# Mutual Fund Analytics Platform

Production-grade Mutual Fund Analytics Capstone Project (Day 1).

This project sets up an analytics-ready foundation to ingest raw mutual fund datasets, fetch live NAV history from MFAPI, generate fund master summary metrics, and validate data consistency between fund master and NAV history.

## Project Overview

**Primary goals (Day 1)**

- Build a clean, scalable project structure for data engineering + analytics.
- Ingest CSV datasets from `data/raw/` and generate profiling/quality reports.
- Fetch NAV history for selected schemes from **MFAPI** and store as CSV.
- Generate fund master summary metrics (unique counts).
- Validate that scheme codes in fund master exist in NAV history.

## Folder Structure

```
mutual_fund_analytics/
│
├── data/
│   ├── raw/
│   │   ├── nav_history/
│   │   └── live_nav_hdfc_top100.csv   (generated)
│   └── processed/
│
├── notebooks/
├── sql/
├── dashboard/
├── reports/
│   ├── data_summary.csv               (generated)
│   ├── data_quality_report.txt        (generated)
│   ├── fund_master_summary.txt        (generated)
│   ├── validation_report.txt          (generated)
│   └── pipeline.log                   (generated)
│
├── scripts/
│   ├── data_ingestion.py
│   ├── live_nav_fetch.py
│   └── data_quality_check.py
│
├── requirements.txt
├── README.md
└── .gitignore
```

## Installation

From the project folder:

```bash
cd mutual_fund_analytics
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Usage

Run from the `mutual_fund_analytics/` directory.

### Run the full Day 1 pipeline (recommended)

```bash
python scripts/run_day1.py
```

### Run the analytics dashboard (Streamlit)

```bash
streamlit run dashboard/app.py
```

The dashboard includes:
- Global slicers for category, fund house, plan, and NAV date range.
- NAV trend, drawdown, and trading-day CAGR using 252 trading days.
- Monte Carlo NAV projection with 5%-95% uncertainty bands.
- Markowitz-style Efficient Frontier for exactly 5 selected funds.

### 1) Fetch NAV history (MFAPI)

```bash
python scripts/live_nav_fetch.py
```

Outputs:
- `data/raw/live_nav_hdfc_top100.csv`
- `data/raw/nav_history/{SCHEME_CODE}.csv` for each scheme

### 2) Ingest & profile raw CSVs

```bash
python scripts/data_ingestion.py
```

Outputs:
- `reports/data_summary.csv`
- `reports/data_quality_report.txt`

### 3) Fund master analysis + scheme-code validation

If you have a fund master CSV under `data/raw/` (example name: `fund_master.csv`) and NAV history under `data/raw/nav_history/`, run:

```bash
python scripts/data_quality_check.py
```

If your fund master file is named differently:

```bash
python scripts/data_quality_check.py --fund-master data/raw/your_file.csv
```

If you want to validate using the full capstone dataset files:

```bash
python scripts/data_quality_check.py --fund-master dataset/01_fund_master.csv --nav-history dataset/02_nav_history.csv
```

Outputs:
- `reports/fund_master_summary.txt`
- `reports/validation_report.txt`

### 4) Run advanced analytics exports

```bash
python scripts/advanced_analytics.py
```

Outputs:
- `reports/monte_carlo_nav_projection.csv`
- `reports/efficient_frontier_portfolios.csv`

### 5) Generate weekly HTML email report

```bash
python scripts/email_report.py
```

Output:
- `reports/weekly_performance_email.html`

To send email, set SMTP environment variables and pass `--send`:

```bash
set SMTP_HOST=smtp.example.com
set SMTP_PORT=587
set SMTP_USERNAME=your_user
set SMTP_PASSWORD=your_password
set SMTP_FROM=sender@example.com
set SMTP_TO=receiver@example.com
python scripts/email_report.py --send
```

### Schedule weekday NAV fetch

See `scheduler_setup.md` for Windows Task Scheduler and cron examples that run `scripts/live_nav_fetch.py` every weekday at 8 PM.

## Day 1 Deliverables

- Project scaffold with standard analytics layout.
- Production-ready scripts:
  - CSV ingestion + profiling + report generation.
  - Live NAV history fetch for selected MF schemes.
  - Fund master summary metrics + NAV coverage validation.
- Reports generated in `reports/`.
- `requirements.txt` containing core analytics + engineering libraries.

## Data Source

NAV data is fetched from MFAPI (public endpoint), e.g.:

- https://api.mfapi.in/mf/125497

Always validate data fields and formats from the API before production use.
