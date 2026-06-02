from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


TRADING_DAYS_PER_YEAR = 252
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = PROJECT_ROOT / "dataset"


@dataclass(frozen=True)
class DatasetPaths:
    fund_master: Path
    nav_history: Path
    aum_by_fund_house: Path
    monthly_sip_inflows: Path
    category_inflows: Path
    industry_folio_count: Path
    scheme_performance: Path
    investor_transactions: Path
    portfolio_holdings: Path
    benchmark_indices: Path


def dataset_paths() -> DatasetPaths:
    return DatasetPaths(
        fund_master=DATASET_DIR / "01_fund_master.csv",
        nav_history=DATASET_DIR / "02_nav_history.csv",
        aum_by_fund_house=DATASET_DIR / "03_aum_by_fund_house.csv",
        monthly_sip_inflows=DATASET_DIR / "04_monthly_sip_inflows.csv",
        category_inflows=DATASET_DIR / "05_category_inflows.csv",
        industry_folio_count=DATASET_DIR / "06_industry_folio_count.csv",
        scheme_performance=DATASET_DIR / "07_scheme_performance.csv",
        investor_transactions=DATASET_DIR / "08_investor_transactions.csv",
        portfolio_holdings=DATASET_DIR / "09_portfolio_holdings.csv",
        benchmark_indices=DATASET_DIR / "10_benchmark_indices.csv",
    )


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing required dataset file: {path.as_posix()}")


@st.cache_data(show_spinner=False)
def load_csv(path: Path, date_cols: Tuple[str, ...] = ()) -> pd.DataFrame:
    require_file(path)
    df = pd.read_csv(path, low_memory=False)
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    if "amfi_code" in df.columns:
        df["amfi_code"] = df["amfi_code"].astype(str).str.strip()
    return df


def to_numeric(df: pd.DataFrame, cols: Sequence[str]) -> pd.DataFrame:
    df = df.copy()
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def latest_date_and_slice(df: pd.DataFrame, date_col: str) -> Tuple[Optional[pd.Timestamp], pd.DataFrame]:
    if df.empty or date_col not in df.columns:
        return None, df
    max_date = df[date_col].max()
    if pd.isna(max_date):
        return None, df
    return max_date, df.loc[df[date_col] == max_date].copy()


def compute_drawdown(nav: pd.Series) -> pd.Series:
    nav = nav.astype(float)
    return (nav / nav.cummax()) - 1.0


def aligned_nav_matrix(nav_history: pd.DataFrame, scheme_codes: Sequence[str]) -> pd.DataFrame:
    selected = nav_history.loc[nav_history["amfi_code"].isin([str(c) for c in scheme_codes])].copy()
    selected = selected.dropna(subset=["date", "nav"])
    if selected.empty:
        return pd.DataFrame()
    pivot = selected.pivot_table(index="date", columns="amfi_code", values="nav", aggfunc="last").sort_index()
    full_index = pd.date_range(pivot.index.min(), pivot.index.max(), freq="B")
    return pivot.reindex(full_index).ffill().dropna(how="all")


def daily_returns(nav_matrix: pd.DataFrame) -> pd.DataFrame:
    return nav_matrix.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan).dropna(how="all")


def cagr_from_trading_days(nav_series: pd.Series) -> float:
    clean = nav_series.dropna()
    if len(clean) < 2 or clean.iloc[0] <= 0:
        return 0.0
    trading_days = len(clean) - 1
    return (clean.iloc[-1] / clean.iloc[0]) ** (TRADING_DAYS_PER_YEAR / trading_days) - 1.0


def monte_carlo_bands(
    nav_history: pd.DataFrame,
    scheme_code: str,
    years: int,
    simulations: int,
    seed: int,
) -> pd.DataFrame:
    nav_matrix = aligned_nav_matrix(nav_history, [scheme_code])
    if nav_matrix.empty or scheme_code not in nav_matrix.columns:
        return pd.DataFrame()

    series = nav_matrix[scheme_code].dropna()
    returns = series.pct_change(fill_method=None).dropna()
    if returns.empty:
        return pd.DataFrame()

    rng = np.random.default_rng(seed)
    steps = years * TRADING_DAYS_PER_YEAR
    shocks = rng.normal(float(returns.mean()), float(returns.std(ddof=1)), size=(steps, simulations))
    paths = float(series.iloc[-1]) * np.cumprod(1.0 + shocks, axis=0)

    return pd.DataFrame(
        {
            "trading_day": np.arange(1, steps + 1),
            "p05": np.percentile(paths, 5, axis=1),
            "p25": np.percentile(paths, 25, axis=1),
            "median": np.percentile(paths, 50, axis=1),
            "p75": np.percentile(paths, 75, axis=1),
            "p95": np.percentile(paths, 95, axis=1),
        }
    )


def efficient_frontier(
    nav_history: pd.DataFrame,
    scheme_codes: Sequence[str],
    portfolios: int,
    seed: int,
) -> pd.DataFrame:
    nav_matrix = aligned_nav_matrix(nav_history, scheme_codes).dropna()
    returns = daily_returns(nav_matrix).dropna()
    if returns.shape[1] < 2:
        return pd.DataFrame()

    rng = np.random.default_rng(seed)
    weights = rng.dirichlet(np.ones(returns.shape[1]), size=portfolios)
    annual_returns = returns.mean().to_numpy() * TRADING_DAYS_PER_YEAR
    covariance = returns.cov().to_numpy() * TRADING_DAYS_PER_YEAR
    port_return = weights @ annual_returns
    port_volatility = np.sqrt(np.einsum("ij,jk,ik->i", weights, covariance, weights))
    sharpe = np.divide(port_return, port_volatility, out=np.zeros_like(port_return), where=port_volatility > 0)

    frontier = pd.DataFrame(
        {
            "return_pct": port_return * 100,
            "volatility_pct": port_volatility * 100,
            "sharpe_ratio": sharpe,
        }
    )
    for idx, code in enumerate(returns.columns):
        frontier[f"weight_{code}"] = weights[:, idx]
    return frontier


def scheme_label_map(performance: pd.DataFrame) -> dict[str, str]:
    if {"amfi_code", "scheme_name"}.issubset(performance.columns):
        return {
            str(row.amfi_code): f"{row.scheme_name} ({row.amfi_code})"
            for row in performance[["amfi_code", "scheme_name"]].dropna().itertuples(index=False)
        }
    return {}


def main() -> None:
    st.set_page_config(page_title="Mutual Fund Analytics", layout="wide")

    paths = dataset_paths()
    with st.spinner("Loading datasets..."):
        fund_master = load_csv(paths.fund_master, ("launch_date",))
        nav_history = to_numeric(load_csv(paths.nav_history, ("date",)), ["nav"])
        performance = to_numeric(
            load_csv(paths.scheme_performance),
            [
                "return_1yr_pct",
                "return_3yr_pct",
                "return_5yr_pct",
                "sharpe_ratio",
                "sortino_ratio",
                "std_dev_ann_pct",
                "max_drawdown_pct",
                "aum_crore",
                "expense_ratio_pct",
            ],
        )
        aum = to_numeric(load_csv(paths.aum_by_fund_house, ("date",)), ["aum_crore"])
        sip = to_numeric(load_csv(paths.monthly_sip_inflows, ("month",)), ["sip_inflow_crore"])
        inflows = to_numeric(load_csv(paths.category_inflows, ("month",)), ["net_inflow_crore"])
        folios = load_csv(paths.industry_folio_count, ("month",))
        txns = to_numeric(load_csv(paths.investor_transactions, ("transaction_date",)), ["amount_inr"])
        holdings = to_numeric(load_csv(paths.portfolio_holdings, ("portfolio_date",)), ["weight_pct", "market_value_cr"])
        benchmarks = to_numeric(load_csv(paths.benchmark_indices, ("date",)), ["close_value"])

    st.title("Mutual Fund Analytics Dashboard")
    st.caption("Interactive Streamlit alternative to Power BI with advanced NAV analytics")

    label_map = scheme_label_map(performance)
    categories = sorted(performance["category"].dropna().astype(str).unique().tolist())
    fund_houses = sorted(performance["fund_house"].dropna().astype(str).unique().tolist())
    plans = sorted(performance["plan"].dropna().astype(str).unique().tolist())

    with st.sidebar:
        st.header("Slicers")
        selected_categories = st.multiselect("Category", categories, default=categories[: min(4, len(categories))])
        selected_houses = st.multiselect("Fund house", fund_houses, default=fund_houses[: min(5, len(fund_houses))])
        selected_plans = st.multiselect("Plan", plans, default=plans)
        nav_dates = nav_history["date"].dropna()
        start_date = nav_dates.min().date()
        end_date = nav_dates.max().date()
        selected_dates = st.date_input("NAV date range", value=(start_date, end_date), min_value=start_date, max_value=end_date)

    perf_view = performance.copy()
    if selected_categories:
        perf_view = perf_view.loc[perf_view["category"].astype(str).isin(selected_categories)]
    if selected_houses:
        perf_view = perf_view.loc[perf_view["fund_house"].astype(str).isin(selected_houses)]
    if selected_plans:
        perf_view = perf_view.loc[perf_view["plan"].astype(str).isin(selected_plans)]

    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        date_start = pd.to_datetime(selected_dates[0])
        date_end = pd.to_datetime(selected_dates[1])
    else:
        date_start = pd.to_datetime(start_date)
        date_end = pd.to_datetime(end_date)
    nav_filtered = nav_history.loc[nav_history["date"].between(date_start, date_end)].copy()

    latest_aum_date, aum_latest = latest_date_and_slice(aum, "date")
    nav_min = nav_filtered["date"].min()
    nav_max = nav_filtered["date"].max()
    latest_sip_month = sip["month"].max() if "month" in sip.columns else None
    latest_sip_value = (
        float(sip.loc[sip["month"] == latest_sip_month, "sip_inflow_crore"].iloc[0])
        if latest_sip_month is not None and "sip_inflow_crore" in sip.columns and not sip.empty
        else 0.0
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Filtered schemes", f"{perf_view['amfi_code'].nunique():,}")
    c2.metric("Fund houses", f"{perf_view['fund_house'].nunique():,}")
    c3.metric("NAV range", f"{nav_min.date()} to {nav_max.date()}" if pd.notna(nav_min) and pd.notna(nav_max) else "-")
    c4.metric("Latest SIP inflow (Rs cr)", f"{latest_sip_value:,.0f}" if latest_sip_value else "-")

    st.divider()

    tab_overview, tab_nav, tab_monte, tab_frontier, tab_flows, tab_holdings = st.tabs(
        ["Overview", "NAV & Drawdown", "Monte Carlo", "Efficient Frontier", "Flows", "Holdings"]
    )

    with tab_overview:
        st.header("Scheme Performance")
        left, right = st.columns(2)
        if "return_3yr_pct" in perf_view.columns and not perf_view.empty:
            top3 = perf_view.sort_values("return_3yr_pct", ascending=False).head(15)
            fig = px.bar(
                top3,
                x="return_3yr_pct",
                y="scheme_name",
                color="fund_house",
                orientation="h",
                title="Top schemes by 3Y return (%)",
            )
            fig.update_layout(height=520, yaxis_title="")
            left.plotly_chart(fig, use_container_width=True)

        if {"return_3yr_pct", "std_dev_ann_pct"}.issubset(perf_view.columns) and not perf_view.empty:
            fig = px.scatter(
                perf_view,
                x="std_dev_ann_pct",
                y="return_3yr_pct",
                color="risk_grade",
                size="aum_crore",
                hover_name="scheme_name",
                title="Risk vs Return",
            )
            fig.update_layout(height=520, xaxis_title="Annualized standard deviation (%)", yaxis_title="3Y return (%)")
            right.plotly_chart(fig, use_container_width=True)

        columns = [
            "amfi_code",
            "scheme_name",
            "fund_house",
            "category",
            "plan",
            "return_1yr_pct",
            "return_3yr_pct",
            "return_5yr_pct",
            "sharpe_ratio",
            "max_drawdown_pct",
            "aum_crore",
            "expense_ratio_pct",
        ]
        st.dataframe(perf_view[[c for c in columns if c in perf_view.columns]], use_container_width=True, hide_index=True)

    with tab_nav:
        st.header("NAV Trend & Drawdown")
        scheme_options = perf_view["amfi_code"].astype(str).tolist() or performance["amfi_code"].astype(str).tolist()
        scheme_code = st.selectbox("Scheme", options=scheme_options, format_func=lambda code: label_map.get(code, code))
        nav_scheme = nav_filtered.loc[nav_filtered["amfi_code"] == scheme_code].dropna(subset=["date", "nav"]).sort_values("date")

        if nav_scheme.empty:
            st.info("No NAV rows found for this scheme and date range.")
        else:
            nav_matrix = aligned_nav_matrix(nav_scheme, [scheme_code])
            cagr = cagr_from_trading_days(nav_matrix[scheme_code]) if scheme_code in nav_matrix else 0.0
            st.metric("Trading-day CAGR", f"{cagr * 100:.2f}%")

            fig = px.line(nav_scheme, x="date", y="nav", title="NAV over time")
            fig.update_layout(height=420, yaxis_title="NAV")
            st.plotly_chart(fig, use_container_width=True)

            nav_scheme["drawdown"] = compute_drawdown(nav_scheme["nav"])
            fig = px.area(nav_scheme, x="date", y="drawdown", title="Drawdown over time")
            fig.update_layout(height=320, yaxis_title="Drawdown")
            st.plotly_chart(fig, use_container_width=True)

    with tab_monte:
        st.header("Monte Carlo NAV Projection")
        mc_left, mc_mid, mc_right = st.columns(3)
        mc_scheme = mc_left.selectbox(
            "Projection scheme",
            options=performance["amfi_code"].astype(str).tolist(),
            format_func=lambda code: label_map.get(code, code),
        )
        mc_years = mc_mid.slider("Years", min_value=1, max_value=5, value=5)
        mc_sims = mc_right.slider("Simulations", min_value=250, max_value=5000, value=1000, step=250)
        bands = monte_carlo_bands(nav_filtered, mc_scheme, mc_years, mc_sims, seed=42)

        if bands.empty:
            st.info("Not enough NAV data for this projection.")
        else:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=bands["trading_day"], y=bands["p95"], line=dict(width=0), showlegend=False))
            fig.add_trace(
                go.Scatter(
                    x=bands["trading_day"],
                    y=bands["p05"],
                    fill="tonexty",
                    name="5%-95% band",
                    line=dict(width=0),
                    fillcolor="rgba(33, 113, 181, 0.18)",
                )
            )
            fig.add_trace(go.Scatter(x=bands["trading_day"], y=bands["p75"], line=dict(width=0), showlegend=False))
            fig.add_trace(
                go.Scatter(
                    x=bands["trading_day"],
                    y=bands["p25"],
                    fill="tonexty",
                    name="25%-75% band",
                    line=dict(width=0),
                    fillcolor="rgba(33, 113, 181, 0.28)",
                )
            )
            fig.add_trace(go.Scatter(x=bands["trading_day"], y=bands["median"], name="Median NAV", line=dict(color="#14324a")))
            fig.update_layout(height=520, xaxis_title="Trading day", yaxis_title="Projected NAV")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(bands.tail(10), use_container_width=True, hide_index=True)

    with tab_frontier:
        st.header("Markowitz Efficient Frontier")
        default_codes = performance.sort_values("return_3yr_pct", ascending=False)["amfi_code"].astype(str).head(5).tolist()
        frontier_codes = st.multiselect(
            "Select exactly 5 funds",
            options=performance["amfi_code"].astype(str).tolist(),
            default=default_codes,
            format_func=lambda code: label_map.get(code, code),
        )
        portfolio_count = st.slider("Random portfolios", min_value=1000, max_value=20000, value=5000, step=1000)

        if len(frontier_codes) != 5:
            st.info("Select exactly 5 funds for the bonus challenge.")
        else:
            frontier = efficient_frontier(nav_filtered, frontier_codes, portfolio_count, seed=42)
            if frontier.empty:
                st.info("Not enough overlapping NAV history for these funds.")
            else:
                best_sharpe = frontier.loc[frontier["sharpe_ratio"].idxmax()]
                min_vol = frontier.loc[frontier["volatility_pct"].idxmin()]

                fig = px.scatter(
                    frontier,
                    x="volatility_pct",
                    y="return_pct",
                    color="sharpe_ratio",
                    color_continuous_scale="Viridis",
                    title="Efficient frontier candidate portfolios",
                )
                fig.add_trace(
                    go.Scatter(
                        x=[best_sharpe["volatility_pct"]],
                        y=[best_sharpe["return_pct"]],
                        mode="markers",
                        marker=dict(size=14, color="red", symbol="star"),
                        name="Max Sharpe",
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=[min_vol["volatility_pct"]],
                        y=[min_vol["return_pct"]],
                        mode="markers",
                        marker=dict(size=12, color="white", line=dict(color="black", width=1.5)),
                        name="Min volatility",
                    )
                )
                fig.update_layout(height=540, xaxis_title="Annualized volatility (%)", yaxis_title="Annualized return (%)")
                st.plotly_chart(fig, use_container_width=True)

                weight_cols = [c for c in frontier.columns if c.startswith("weight_")]
                summary = pd.DataFrame(
                    [
                        {"portfolio": "Max Sharpe", **best_sharpe[["return_pct", "volatility_pct", "sharpe_ratio", *weight_cols]].to_dict()},
                        {"portfolio": "Min Volatility", **min_vol[["return_pct", "volatility_pct", "sharpe_ratio", *weight_cols]].to_dict()},
                    ]
                )
                st.dataframe(summary, use_container_width=True, hide_index=True)

    with tab_flows:
        st.header("AUM, SIP & Category Inflows")
        left, right = st.columns(2)
        if not aum.empty and {"date", "fund_house", "aum_crore"}.issubset(aum.columns):
            house_options = sorted(aum["fund_house"].dropna().astype(str).unique().tolist())
            house = left.selectbox("AUM fund house", options=house_options)
            aum_house = aum.loc[aum["fund_house"].astype(str) == house].dropna(subset=["date", "aum_crore"]).sort_values("date")
            fig = px.line(aum_house, x="date", y="aum_crore", title="AUM over time (Rs crore)")
            fig.update_layout(height=360, yaxis_title="AUM (Rs crore)")
            left.plotly_chart(fig, use_container_width=True)

        if latest_aum_date is not None and not aum_latest.empty:
            latest = aum_latest.sort_values("aum_crore", ascending=False)
            fig = px.bar(latest, x="aum_crore", y="fund_house", orientation="h", title=f"AUM by fund house on {latest_aum_date.date()}")
            fig.update_layout(height=360, yaxis_title="", xaxis_title="Rs crore")
            right.plotly_chart(fig, use_container_width=True)

        if not sip.empty and {"month", "sip_inflow_crore"}.issubset(sip.columns):
            fig = px.line(sip.dropna(subset=["month", "sip_inflow_crore"]).sort_values("month"), x="month", y="sip_inflow_crore", title="Monthly SIP inflows")
            fig.update_layout(height=360, yaxis_title="Rs crore")
            st.plotly_chart(fig, use_container_width=True)

        if not inflows.empty and {"month", "category", "net_inflow_crore"}.issubset(inflows.columns):
            months = sorted(inflows["month"].dropna().unique().tolist())
            month = st.selectbox("Inflow month", options=months, format_func=lambda d: pd.to_datetime(d).strftime("%Y-%m"))
            inflow_month = inflows.loc[inflows["month"] == month].sort_values("net_inflow_crore", ascending=False)
            fig = px.bar(inflow_month, x="net_inflow_crore", y="category", orientation="h", title="Net inflow by category")
            fig.update_layout(height=420, yaxis_title="", xaxis_title="Rs crore")
            st.plotly_chart(fig, use_container_width=True)

        if not folios.empty and "month" in folios.columns:
            value_cols = [c for c in folios.columns if c != "month"]
            melted = folios.melt(id_vars=["month"], value_vars=value_cols, var_name="metric", value_name="value")
            fig = px.line(melted.dropna(subset=["month", "value"]).sort_values("month"), x="month", y="value", color="metric", title="Folio counts")
            fig.update_layout(height=380, yaxis_title="Crore")
            st.plotly_chart(fig, use_container_width=True)

    with tab_holdings:
        st.header("Portfolio Holdings, Transactions & Benchmarks")
        if not holdings.empty and "amfi_code" in holdings.columns:
            holding_schemes = sorted(holdings["amfi_code"].dropna().astype(str).unique().tolist())
            holding_code = st.selectbox("Scheme for holdings", options=holding_schemes, format_func=lambda code: label_map.get(code, code))
            h = holdings.loc[holdings["amfi_code"].astype(str) == holding_code].copy()
            if "portfolio_date" in h.columns:
                latest_hold_date = h["portfolio_date"].max()
                if pd.notna(latest_hold_date):
                    h = h.loc[h["portfolio_date"] == latest_hold_date]
            if "weight_pct" in h.columns and not h.empty:
                top = h.sort_values("weight_pct", ascending=False).head(15)
                fig = px.bar(top, x="weight_pct", y="stock_symbol", orientation="h", title="Top holdings by weight (%)")
                fig.update_layout(height=420, yaxis_title="")
                st.plotly_chart(fig, use_container_width=True)
            st.dataframe(h.sort_values("weight_pct", ascending=False) if "weight_pct" in h.columns else h, use_container_width=True, hide_index=True)

        if not txns.empty and {"transaction_type", "amount_inr"}.issubset(txns.columns):
            by_type = txns.groupby("transaction_type", dropna=False)["amount_inr"].sum().reset_index().sort_values("amount_inr", ascending=False)
            fig = px.bar(by_type, x="transaction_type", y="amount_inr", title="Total amount by transaction type")
            fig.update_layout(height=320, yaxis_title="Amount (INR)")
            st.plotly_chart(fig, use_container_width=True)

        if not benchmarks.empty and {"index_name", "date", "close_value"}.issubset(benchmarks.columns):
            idx_names = sorted(benchmarks["index_name"].dropna().astype(str).unique().tolist())
            idx = st.selectbox("Benchmark index", options=idx_names)
            b = benchmarks.loc[benchmarks["index_name"].astype(str) == idx].dropna(subset=["date", "close_value"]).sort_values("date")
            fig = px.line(b, x="date", y="close_value", title="Benchmark close value")
            fig.update_layout(height=380, yaxis_title="Close")
            st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
