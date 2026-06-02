-- Top funds by 3-year return.
SELECT
    scheme_name,
    fund_house,
    category,
    return_3yr_pct,
    sharpe_ratio,
    aum_crore
FROM scheme_performance
ORDER BY return_3yr_pct DESC
LIMIT 10;

-- Latest NAV for every scheme.
SELECT n.amfi_code, f.scheme_name, n.date, n.nav
FROM nav_history n
JOIN (
    SELECT amfi_code, MAX(date) AS latest_date
    FROM nav_history
    GROUP BY amfi_code
) latest
    ON n.amfi_code = latest.amfi_code
   AND n.date = latest.latest_date
LEFT JOIN fund_master f
    ON n.amfi_code = f.amfi_code;

-- Category-level AUM and average performance.
SELECT
    category,
    COUNT(*) AS scheme_count,
    SUM(aum_crore) AS total_aum_crore,
    AVG(return_3yr_pct) AS avg_return_3yr_pct,
    AVG(sharpe_ratio) AS avg_sharpe_ratio
FROM scheme_performance
GROUP BY category
ORDER BY total_aum_crore DESC;
