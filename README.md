<div align="center">

# 📊 Mutual Fund Analytics Dashboard

### Advanced Fintech Analytics Platform for NAV Analysis, Risk Modeling, Portfolio Optimization & Investment Insights

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![Pandas](https://img.shields.io/badge/Pandas-Data_Analysis-green?style=for-the-badge&logo=pandas)
![Plotly](https://img.shields.io/badge/Plotly-Interactive_Dashboard-purple?style=for-the-badge&logo=plotly)
![SQL](https://img.shields.io/badge/SQL-Analytics-orange?style=for-the-badge&logo=postgresql)
![Fintech](https://img.shields.io/badge/Domain-Fintech-red?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

</div>

---

## 🚀 Project Overview

The **Mutual Fund Analytics Dashboard** is a comprehensive fintech analytics platform designed to analyze mutual fund performance, evaluate investment risk, compare schemes, and generate actionable insights using advanced data analytics techniques.

This project combines:

- Financial Data Analytics
- Mutual Fund Performance Tracking
- NAV Analysis
- Risk & Return Modeling
- Portfolio Optimization
- Monte Carlo Simulation
- Efficient Frontier Analysis
- Interactive Dashboarding

The platform enables investors, analysts, and researchers to make data-driven investment decisions using historical mutual fund data and advanced quantitative techniques.

---

# 🎯 Business Objectives

The project aims to answer key investment questions:

✅ Which mutual funds deliver the highest returns?

✅ Which funds offer the best risk-adjusted performance?

✅ How does SIP compare with Lump Sum investing?

✅ What are the top-performing fund houses?

✅ What is the future probability range of portfolio growth?

✅ How diversified is a portfolio?

✅ Which mutual funds fit different investor risk profiles?

---

# 🏗️ System Architecture

```text
Data Sources
      │
      ▼
Data Ingestion Layer
      │
      ▼
Data Cleaning & Validation
      │
      ▼
Feature Engineering
      │
      ▼
Analytics Engine
      │
 ┌────┼────────────┐
 ▼    ▼            ▼
NAV  Risk     Portfolio
Analysis Analysis Analytics
 │      │          │
 └──────┼──────────┘
        ▼
Interactive Dashboard
```

---

# 📂 Project Structure

```text
Mutual-Fund-Analytics-Dashboard/

├── dataset/
├── scripts/
│   ├── data_ingestion.py
│   ├── live_nav_fetch.py
│   ├── data_quality_check.py
│   ├── advanced_analytics.py
│   └── email_report.py
│
├── sql/
│   ├── schema.sql
│   └── queries.sql
│
├── reports/
│
├── dashboard/
│
├── requirements.txt
├── README.md
└── LICENSE
```

---

# ✨ Core Features

## 📈 NAV Analytics

- Daily NAV Tracking
- Historical NAV Analysis
- NAV Growth Trends
- Fund Comparison
- Return Distribution

---

## 📊 Performance Analytics

- CAGR Calculation
- Rolling Returns
- Annualized Returns
- Benchmark Comparison
- Top Performing Schemes

---

## ⚠️ Risk Analytics

- Volatility Analysis
- Sharpe Ratio
- Sortino Ratio
- Beta
- Alpha
- Maximum Drawdown

---

## 💰 SIP Analytics

- SIP Growth Projection
- Wealth Accumulation
- SIP vs Lump Sum Comparison
- Investment Scenario Analysis

---

## 🧠 Advanced Analytics

- Monte Carlo Simulation
- Efficient Frontier
- Portfolio Optimization
- Correlation Analysis
- Risk-Return Scatter Modeling

---

## 🏢 Fund House Analytics

- Fund House Ranking
- Category Performance
- Scheme Comparison
- Risk Grade Analysis

---

# 📷 Dashboard Preview

## Main Dashboard

> Add dashboard screenshot here

```md
![Dashboard](assets/dashboard_home.png)
```

---

## NAV Analysis

```md
![NAV Analysis](assets/nav_analysis.png)
```

---

## Risk vs Return

```md
![Risk Return](assets/risk_return.png)
```

---

# 📊 Key Metrics Used

| Metric | Description |
|----------|-------------|
| CAGR | Compound Annual Growth Rate |
| NAV | Net Asset Value |
| Sharpe Ratio | Risk-adjusted return measure |
| Sortino Ratio | Downside risk-adjusted return |
| Alpha | Excess return over benchmark |
| Beta | Market sensitivity |
| Drawdown | Peak-to-trough decline |
| Volatility | Return fluctuation measure |

---

# 🛠️ Technology Stack

### Programming

- Python

### Data Analysis

- Pandas
- NumPy

### Visualization

- Plotly
- Matplotlib
- Seaborn

### Database

- SQL
- PostgreSQL

### Statistical Analysis

- SciPy

### Dashboarding

- Streamlit / Dash

### Version Control

- Git
- GitHub

---

# 📋 Installation

Clone repository:

```bash
git clone https://github.com/RiyaRaina1/Mutual-Fund-Analytics-Dashboard.git
```

Move into project:

```bash
cd Mutual-Fund-Analytics-Dashboard
```

Create virtual environment:

```bash
python -m venv .venv
```

Activate:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# ▶️ Running The Project

Run data ingestion:

```bash
python scripts/data_ingestion.py
```

Run NAV fetching:

```bash
python scripts/live_nav_fetch.py
```

Run analytics:

```bash
python scripts/advanced_analytics.py
```

Launch dashboard:

```bash
streamlit run dashboard/app.py
```

---

# 📈 Sample Insights

- UTI Flexi Cap Fund delivered the highest 3-year return among analyzed schemes.
- High-risk funds demonstrated greater return dispersion.
- SIP investments showed lower volatility than lump-sum investments.
- Diversified portfolios exhibited superior risk-adjusted performance.

---

# 🔮 Future Enhancements

- Live AMFI Integration
- Real-Time NAV Updates
- AI-Powered Fund Recommendations
- Investor Risk Profiling
- Portfolio Rebalancing Engine
- Mobile Responsive Dashboard
- Cloud Deployment

---

# 👩‍💻 Author

### Riya Raina

🎓 MCA (AI & ML)

📊 Data Analytics & Fintech Enthusiast

🔗 GitHub: https://github.com/RiyaRaina1

🔗 LinkedIn: https://www.linkedin.com/in/riya-raina-1rr3/

---

# ⭐ Support

If you found this project useful:

⭐ Star the repository

🍴 Fork the repository

📢 Share feedback

---

<div align="center">

### Built with ❤️ using Python, Data Analytics & Fintech Intelligence

</div>
