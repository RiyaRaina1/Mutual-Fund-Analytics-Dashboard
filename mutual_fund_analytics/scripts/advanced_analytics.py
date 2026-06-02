"""Advanced analytics for NAV simulation and portfolio optimisation.

Implements:
- Trading-day aligned NAV returns with weekday reindex + ffill.
- Monte Carlo NAV projection over a configurable horizon.
- Markowitz-style random portfolio frontier for selected funds.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd


TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class MonteCarloResult:
    paths: pd.DataFrame
    bands: pd.DataFrame


@dataclass(frozen=True)
class FrontierResult:
    portfolios: pd.DataFrame
    nav_returns: pd.DataFrame


def load_nav_history(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    df["amfi_code"] = df["amfi_code"].astype(str).str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    return df.dropna(subset=["amfi_code", "date", "nav"])


def load_scheme_performance(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    df["amfi_code"] = df["amfi_code"].astype(str).str.strip()
    return df


def aligned_nav_matrix(nav_history: pd.DataFrame, scheme_codes: Sequence[str]) -> pd.DataFrame:
    selected = nav_history.loc[nav_history["amfi_code"].isin([str(c) for c in scheme_codes])].copy()
    if selected.empty:
        return pd.DataFrame()

    pivot = selected.pivot_table(index="date", columns="amfi_code", values="nav", aggfunc="last").sort_index()
    full_index = pd.date_range(pivot.index.min(), pivot.index.max(), freq="B")
    return pivot.reindex(full_index).ffill().dropna(how="all")


def daily_returns(nav_matrix: pd.DataFrame) -> pd.DataFrame:
    return nav_matrix.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan).dropna(how="all")


def monte_carlo_nav_projection(
    nav_history: pd.DataFrame,
    scheme_code: str,
    years: int = 5,
    simulations: int = 1000,
    seed: int = 42,
) -> MonteCarloResult:
    nav_matrix = aligned_nav_matrix(nav_history, [scheme_code])
    if nav_matrix.empty or str(scheme_code) not in nav_matrix.columns:
        raise ValueError(f"No NAV history found for scheme {scheme_code}")

    series = nav_matrix[str(scheme_code)].dropna()
    returns = series.pct_change(fill_method=None).dropna()
    if returns.empty:
        raise ValueError(f"Not enough NAV history to simulate scheme {scheme_code}")

    rng = np.random.default_rng(seed)
    steps = int(years * TRADING_DAYS_PER_YEAR)
    mu = float(returns.mean())
    sigma = float(returns.std(ddof=1))
    latest_nav = float(series.iloc[-1])

    shocks = rng.normal(loc=mu, scale=sigma, size=(steps, simulations))
    paths = latest_nav * np.cumprod(1.0 + shocks, axis=0)
    day_index = np.arange(1, steps + 1)
    path_df = pd.DataFrame(paths, index=day_index)
    path_df.index.name = "trading_day"

    bands = pd.DataFrame(
        {
            "trading_day": day_index,
            "p05": np.percentile(paths, 5, axis=1),
            "p25": np.percentile(paths, 25, axis=1),
            "median": np.percentile(paths, 50, axis=1),
            "p75": np.percentile(paths, 75, axis=1),
            "p95": np.percentile(paths, 95, axis=1),
        }
    )
    return MonteCarloResult(paths=path_df, bands=bands)


def efficient_frontier(
    nav_history: pd.DataFrame,
    scheme_codes: Sequence[str],
    portfolios: int = 5000,
    seed: int = 42,
    risk_free_rate: float = 0.0,
) -> FrontierResult:
    codes = [str(code) for code in scheme_codes]
    if len(codes) < 2:
        raise ValueError("Select at least two schemes for portfolio optimisation")

    nav_matrix = aligned_nav_matrix(nav_history, codes).dropna()
    returns = daily_returns(nav_matrix).dropna()
    returns = returns.loc[:, returns.notna().sum() > 1].dropna()
    if returns.shape[1] < 2:
        raise ValueError("Not enough overlapping NAV history for selected schemes")

    rng = np.random.default_rng(seed)
    n_assets = returns.shape[1]
    weights = rng.dirichlet(np.ones(n_assets), size=portfolios)
    annual_returns = returns.mean().to_numpy() * TRADING_DAYS_PER_YEAR
    covariance = returns.cov().to_numpy() * TRADING_DAYS_PER_YEAR

    port_return = weights @ annual_returns
    port_volatility = np.sqrt(np.einsum("ij,jk,ik->i", weights, covariance, weights))
    sharpe = np.divide(
        port_return - risk_free_rate,
        port_volatility,
        out=np.zeros_like(port_return),
        where=port_volatility > 0,
    )

    output = pd.DataFrame(
        {
            "return_pct": port_return * 100,
            "volatility_pct": port_volatility * 100,
            "sharpe_ratio": sharpe,
        }
    )
    for idx, code in enumerate(returns.columns):
        output[f"weight_{code}"] = weights[:, idx]

    return FrontierResult(portfolios=output, nav_returns=returns)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run advanced NAV analytics")
    parser.add_argument("--dataset-dir", type=Path, default=Path("dataset"))
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    parser.add_argument("--scheme-code", type=str, default="125497")
    parser.add_argument("--portfolio-codes", nargs="+", default=["125497", "120841", "118632", "120503", "119551"])
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    args.reports_dir.mkdir(parents=True, exist_ok=True)

    nav = load_nav_history(args.dataset_dir / "02_nav_history.csv")
    mc = monte_carlo_nav_projection(nav, args.scheme_code)
    mc.bands.to_csv(args.reports_dir / "monte_carlo_nav_projection.csv", index=False)

    frontier = efficient_frontier(nav, args.portfolio_codes)
    frontier.portfolios.to_csv(args.reports_dir / "efficient_frontier_portfolios.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
