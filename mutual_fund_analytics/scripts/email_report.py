"""Generate and optionally send a weekly mutual fund performance HTML report.

SMTP settings are read from environment variables:
SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM, SMTP_TO.

If SMTP_HOST or SMTP_TO is missing, the script only writes the HTML file.
"""

from __future__ import annotations

import argparse
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import Optional, Sequence

import pandas as pd


def load_performance(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    numeric_cols = ["return_1yr_pct", "return_3yr_pct", "return_5yr_pct", "sharpe_ratio", "aum_crore"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def render_html_report(performance: pd.DataFrame) -> str:
    top_return = performance.sort_values("return_3yr_pct", ascending=False).head(10)
    top_sharpe = performance.sort_values("sharpe_ratio", ascending=False).head(10)
    total_aum = performance["aum_crore"].sum() if "aum_crore" in performance.columns else 0.0

    cols = ["scheme_name", "fund_house", "category", "return_3yr_pct", "sharpe_ratio", "aum_crore"]
    cols = [c for c in cols if c in performance.columns]

    css = """
    <style>
      body { font-family: Arial, sans-serif; color: #1f2933; }
      h1, h2 { color: #14324a; }
      .metric { display: inline-block; margin: 0 20px 20px 0; padding: 12px 16px; border: 1px solid #d8dee4; }
      table { border-collapse: collapse; width: 100%; margin-bottom: 24px; }
      th, td { border: 1px solid #d8dee4; padding: 8px; text-align: left; }
      th { background: #eef3f8; }
    </style>
    """
    return f"""<!doctype html>
<html>
<head><meta charset="utf-8">{css}</head>
<body>
  <h1>Weekly Mutual Fund Performance Summary</h1>
  <div class="metric"><strong>Schemes tracked</strong><br>{performance["amfi_code"].nunique() if "amfi_code" in performance.columns else len(performance):,}</div>
  <div class="metric"><strong>Total scheme AUM</strong><br>{total_aum:,.0f} crore</div>

  <h2>Top 10 by 3Y Return</h2>
  {top_return[cols].to_html(index=False, border=0)}

  <h2>Top 10 by Sharpe Ratio</h2>
  {top_sharpe[cols].to_html(index=False, border=0)}
</body>
</html>"""


def send_email(subject: str, html: str) -> bool:
    host = os.getenv("SMTP_HOST")
    to_addr = os.getenv("SMTP_TO")
    if not host or not to_addr:
        return False

    port = int(os.getenv("SMTP_PORT", "587"))
    from_addr = os.getenv("SMTP_FROM") or os.getenv("SMTP_USERNAME") or to_addr
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content("Your email client does not support HTML reports.")
    msg.add_alternative(html, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls(context=context)
        if username and password:
            server.login(username, password)
        server.send_message(msg)
    return True


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate/send weekly HTML performance email")
    parser.add_argument("--performance-csv", type=Path, default=Path("dataset") / "07_scheme_performance.csv")
    parser.add_argument("--output", type=Path, default=Path("reports") / "weekly_performance_email.html")
    parser.add_argument("--send", action="store_true", help="Send email using SMTP environment variables")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    performance = load_performance(args.performance_csv)
    html = render_html_report(performance)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(f"Wrote HTML report: {args.output}")

    if args.send:
        sent = send_email("Weekly Mutual Fund Performance Summary", html)
        print("Email sent" if sent else "SMTP_HOST/SMTP_TO not set; skipped sending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
