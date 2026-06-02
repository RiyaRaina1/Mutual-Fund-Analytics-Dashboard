"""Fetch mutual fund NAV history from mfapi.in and store as CSV.

Day 1 Capstone - Mutual Fund Analytics Platform

Requirements implemented:
- Fetch NAV data for the following scheme codes:
    125497 (also saved to data/raw/live_nav_hdfc_top100.csv)
    119551
    120503
    118632
    119092
    120841
- For every scheme:
    - Fetch JSON
    - Parse and convert to DataFrame
    - Save as CSV under data/raw/nav_history/

Usage:
    python scripts/live_nav_fetch.py

Notes:
- MFAPI endpoints are public; be polite (timeouts, retries, logging).
- Output CSV includes meta fields for easier downstream joins.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import pandas as pd
import requests


LOGGER_NAME = "mutual_fund_analytics.live_nav_fetch"
BASE_URL = "https://api.mfapi.in/mf"


def utc_now() -> datetime:
    """Return timezone-aware UTC 'now'."""
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class FetchConfig:
    timeout_seconds: int = 20
    max_retries: int = 3
    backoff_seconds: float = 1.5


def configure_logging(log_level: str) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def fetch_scheme_json(
    session: requests.Session,
    scheme_code: str,
    config: FetchConfig,
    logger: logging.Logger,
) -> Dict[str, Any]:
    """Fetch scheme NAV JSON with basic retries."""
    url = f"{BASE_URL}/{scheme_code}"

    last_exc: Optional[Exception] = None
    for attempt in range(1, config.max_retries + 1):
        try:
            resp = session.get(url, timeout=config.timeout_seconds)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(
                "Fetch failed (scheme=%s, attempt=%s/%s): %s",
                scheme_code,
                attempt,
                config.max_retries,
                exc,
            )
            if attempt < config.max_retries:
                time.sleep(config.backoff_seconds * attempt)

    raise RuntimeError(f"Failed to fetch scheme {scheme_code} after retries") from last_exc


def parse_nav_history(payload: Dict[str, Any], scheme_code: str) -> pd.DataFrame:
    """Parse mfapi response into a normalized DataFrame."""
    meta = payload.get("meta", {}) or {}
    nav_rows = payload.get("data", []) or []

    df = pd.DataFrame(nav_rows)
    if df.empty:
        # Ensure consistent schema even on empty responses.
        df = pd.DataFrame(columns=["date", "nav"])

    # Normalize column names commonly found in mfapi
    if "nav" not in df.columns and "NAV" in df.columns:
        df = df.rename(columns={"NAV": "nav"})

    df.insert(0, "scheme_code", str(scheme_code))
    df.insert(1, "scheme_name", str(meta.get("scheme_name", "")))
    df.insert(2, "fund_house", str(meta.get("fund_house", "")))
    df.insert(3, "scheme_type", str(meta.get("scheme_type", "")))
    df.insert(4, "scheme_category", str(meta.get("scheme_category", "")))

    # Try to parse date; keep original if parsing fails.
    if "date" in df.columns:
        parsed = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)
        if parsed.notna().any():
            df["date"] = parsed.dt.date.astype(str)

    # NAV is a numeric string in the API; convert safely.
    if "nav" in df.columns:
        df["nav"] = pd.to_numeric(df["nav"], errors="coerce")

    return df


def save_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch mutual fund NAV history")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data") / "raw",
        help="Raw data directory (default: data/raw)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    logger = configure_logging(args.log_level)

    raw_dir: Path = args.raw_dir
    nav_history_dir = raw_dir / "nav_history"
    special_output = raw_dir / "live_nav_hdfc_top100.csv"

    scheme_codes = ["125497", "119551", "120503", "118632", "119092", "120841"]

    logger.info("Starting NAV fetch for %s schemes", len(scheme_codes))

    config = FetchConfig()
    with requests.Session() as session:
        session.headers.update({"User-Agent": "MutualFundAnalyticsPlatform/1.0"})

        for scheme_code in scheme_codes:
            try:
                payload = fetch_scheme_json(session, scheme_code, config, logger)
                df = parse_nav_history(payload, scheme_code)

                out_path = nav_history_dir / f"{scheme_code}.csv"
                save_csv(df, out_path)
                logger.info("Saved NAV history: %s (%s rows)", out_path.as_posix(), len(df))

                if scheme_code == "125497":
                    save_csv(df, special_output)
                    logger.info("Saved special output: %s", special_output.as_posix())

            except Exception:  # noqa: BLE001
                logger.exception("Failed scheme fetch/parse/save for %s", scheme_code)

    logger.info("Completed NAV fetch run at %s", utc_now().isoformat(timespec="seconds"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
