"""Run Day 1 pipeline end-to-end.

Day 1 Capstone - Mutual Fund Analytics Platform

This orchestrates:
1) live_nav_fetch.py
2) data_ingestion.py
3) data_quality_check.py

Usage:
    python scripts/run_day1.py

Optional:
    python scripts/run_day1.py --raw-dir data/raw --reports-dir reports --log-level INFO

Notes:
- This script uses subprocess to run the individual scripts so their output
  (including prints) is preserved.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence


LOGGER_NAME = "mutual_fund_analytics.run_day1"


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


def run_step(logger: logging.Logger, args: List[str], cwd: Path) -> int:
    """Run a pipeline step and stream output to the console."""
    logger.info("Running: %s", " ".join(args))
    proc = subprocess.run(args, cwd=str(cwd), check=False)
    if proc.returncode != 0:
        logger.error("Step failed (exit_code=%s): %s", proc.returncode, " ".join(args))
    return proc.returncode


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Day 1 pipeline end-to-end")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data") / "raw",
        help="Raw data directory (default: data/raw)",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("reports"),
        help="Reports directory (default: reports)",
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

    project_root = Path(__file__).resolve().parents[1]
    scripts_dir = project_root / "scripts"

    raw_dir = args.raw_dir
    reports_dir = args.reports_dir

    steps: List[List[str]] = [
        [sys.executable, str(scripts_dir / "live_nav_fetch.py"), "--raw-dir", str(raw_dir), "--log-level", args.log_level],
        [
            sys.executable,
            str(scripts_dir / "data_ingestion.py"),
            "--raw-dir",
            str(raw_dir),
            "--reports-dir",
            str(reports_dir),
            "--log-level",
            args.log_level,
        ],
        [
            sys.executable,
            str(scripts_dir / "data_quality_check.py"),
            "--raw-dir",
            str(raw_dir),
            "--reports-dir",
            str(reports_dir),
            "--log-level",
            args.log_level,
        ],
    ]

    for step in steps:
        code = run_step(logger, step, cwd=project_root)
        if code != 0:
            return code

    logger.info("Day 1 pipeline completed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
