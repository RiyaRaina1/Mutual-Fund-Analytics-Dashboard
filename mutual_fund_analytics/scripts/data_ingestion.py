"""Data ingestion and profiling for raw CSV datasets.

Day 1 Capstone - Mutual Fund Analytics Platform

Features:
- Read all CSV files under data/raw (recursive).
- For each file, print filename, shape, columns, datatypes, missing values.
- Save dataset summary to reports/data_summary.csv
- Save data quality report to reports/data_quality_report.txt
- Production-grade logging and exception handling.

Usage:
    python scripts/data_ingestion.py
    python scripts/data_ingestion.py --raw-dir data/raw --reports-dir reports

Notes:
- This script is safe to run multiple times; reports are overwritten.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

import pandas as pd


LOGGER_NAME = "mutual_fund_analytics.data_ingestion"


def utc_now() -> datetime:
    """Return timezone-aware UTC 'now'."""
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class FileProfile:
    filename: str
    relative_path: str
    rows: int
    cols: int
    columns: str
    dtypes: str
    missing_total: int
    missing_by_column: str
    duplicate_rows: int


def configure_logging(log_level: str, log_file: Optional[Path]) -> logging.Logger:
    """Configure logging to console (and optionally to a file)."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def find_csv_files(raw_dir: Path) -> List[Path]:
    """Return all CSV files under raw_dir (recursive), excluding hidden files."""
    if not raw_dir.exists():
        return []

    csv_files: List[Path] = []
    for path in raw_dir.rglob("*.csv"):
        if any(part.startswith(".") for part in path.parts):
            continue
        if path.is_file():
            csv_files.append(path)

    return sorted(csv_files)


def safe_read_csv(path: Path) -> pd.DataFrame:
    """Read a CSV with sensible defaults and fallbacks."""
    # Try utf-8 first, fall back to latin-1 for messy exports.
    try:
        return pd.read_csv(path, low_memory=False, encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(path, low_memory=False, encoding="latin-1")


def _json_dumps_compact(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def profile_dataframe(df: pd.DataFrame, file_path: Path, raw_dir: Path) -> FileProfile:
    """Compute a profile row for summary output."""
    missing_by_column = df.isna().sum().to_dict()
    dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}

    duplicate_rows = int(df.duplicated().sum()) if not df.empty else 0

    rel_path = file_path.relative_to(raw_dir).as_posix()

    return FileProfile(
        filename=file_path.name,
        relative_path=rel_path,
        rows=int(df.shape[0]),
        cols=int(df.shape[1]),
        columns=_json_dumps_compact(list(df.columns)),
        dtypes=_json_dumps_compact(dtypes),
        missing_total=int(df.isna().sum().sum()),
        missing_by_column=_json_dumps_compact(missing_by_column),
        duplicate_rows=duplicate_rows,
    )


def print_profile(logger: logging.Logger, file_path: Path, df: pd.DataFrame) -> None:
    """Print required details to stdout."""
    print("\n" + "=" * 80)
    print(f"File: {file_path.name}")
    print(f"Shape: {df.shape}")
    print("Columns:")
    print(list(df.columns))
    print("Data types:")
    print(df.dtypes)
    print("Missing values (per column):")
    print(df.isna().sum())

    logger.info(
        "Profiled %s (rows=%s, cols=%s)",
        file_path.name,
        df.shape[0],
        df.shape[1],
    )


def write_summary_csv(profiles: Sequence[FileProfile], output_path: Path) -> None:
    """Write a flat CSV summary of all ingested files."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(asdict(profiles[0]).keys()) if profiles else [
        "filename",
        "relative_path",
        "rows",
        "cols",
        "columns",
        "dtypes",
        "missing_total",
        "missing_by_column",
        "duplicate_rows",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for profile in profiles:
            writer.writerow(asdict(profile))


def write_quality_report(
    profiles: Sequence[FileProfile],
    output_path: Path,
    started_at: datetime,
    ended_at: datetime,
    errors: Sequence[Tuple[str, str]],
) -> None:
    """Write a human-readable quality report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_files = len(profiles) + len(errors)
    ok_files = len(profiles)
    failed_files = len(errors)

    with output_path.open("w", encoding="utf-8") as f:
        f.write("Mutual Fund Analytics Platform - Data Quality Report\n")
        f.write(f"Generated at: {ended_at.isoformat(timespec='seconds')}\n")
        f.write(f"Duration: {(ended_at - started_at).total_seconds():.2f}s\n")
        f.write("\n")
        f.write(f"Total CSV files discovered: {total_files}\n")
        f.write(f"Successfully profiled: {ok_files}\n")
        f.write(f"Failed to read/profile: {failed_files}\n")
        f.write("\n")

        if profiles:
            f.write("Top issues (by missing values)\n")
            f.write("-----------------------------\n")
            top = sorted(profiles, key=lambda p: p.missing_total, reverse=True)[:10]
            for p in top:
                f.write(
                    f"- {p.relative_path}: missing_total={p.missing_total}, "
                    f"duplicate_rows={p.duplicate_rows}, rows={p.rows}, cols={p.cols}\n"
                )
            f.write("\n")

        if errors:
            f.write("Errors\n")
            f.write("------\n")
            for rel_path, message in errors:
                f.write(f"- {rel_path}: {message}\n")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest and profile CSV files")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data") / "raw",
        help="Directory containing raw CSVs (default: data/raw)",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("reports"),
        help="Directory where reports are written (default: reports)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=Path("reports") / "pipeline.log",
        help="Optional log file path (default: reports/pipeline.log)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    raw_dir: Path = args.raw_dir
    reports_dir: Path = args.reports_dir

    logger = configure_logging(args.log_level, args.log_file)

    started_at = utc_now()
    logger.info("Starting data ingestion from %s", raw_dir.as_posix())

    csv_files = find_csv_files(raw_dir)
    if not csv_files:
        logger.warning("No CSV files found in %s", raw_dir.as_posix())

    profiles: List[FileProfile] = []
    errors: List[Tuple[str, str]] = []

    for file_path in csv_files:
        rel_path = file_path.relative_to(raw_dir).as_posix()
        try:
            df = safe_read_csv(file_path)
            print_profile(logger, file_path, df)
            profiles.append(profile_dataframe(df, file_path, raw_dir))
        except Exception as exc:  # noqa: BLE001 - we want to continue profiling other files
            logger.exception("Failed processing %s", rel_path)
            errors.append((rel_path, f"{type(exc).__name__}: {exc}"))

    summary_csv = reports_dir / "data_summary.csv"
    quality_txt = reports_dir / "data_quality_report.txt"

    try:
        write_summary_csv(profiles, summary_csv)
        logger.info("Wrote summary CSV: %s", summary_csv.as_posix())
    except Exception:
        logger.exception("Failed writing summary CSV")
        return 2

    ended_at = utc_now()
    try:
        write_quality_report(profiles, quality_txt, started_at, ended_at, errors)
        logger.info("Wrote quality report: %s", quality_txt.as_posix())
    except Exception:
        logger.exception("Failed writing quality report")
        return 3

    logger.info("Completed ingestion run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
