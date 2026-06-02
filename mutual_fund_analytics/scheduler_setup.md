# Weekday NAV Fetch Scheduling

The NAV fetch job is implemented in `scripts/live_nav_fetch.py`. It fetches selected scheme NAV history from `mfapi.in` and writes CSVs under `data/raw/`.

## Windows Task Scheduler

Run this from the parent folder that contains `mutual_fund_analytics`:

```powershell
$Project = "D:\Mutual Fund Analytics\mutual_fund_analytics"
$Python = "D:\Mutual Fund Analytics\.venv\Scripts\python.exe"
$Action = New-ScheduledTaskAction -Execute $Python -Argument "scripts\live_nav_fetch.py" -WorkingDirectory $Project
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 8pm
Register-ScheduledTask -TaskName "Bluestock MF Weekday NAV Fetch" -Action $Action -Trigger $Trigger -Description "Fetch mutual fund NAV from mfapi.in every weekday at 8 PM"
```

## Linux/macOS Cron

```cron
0 20 * * 1-5 cd /path/to/mutual_fund_analytics && /path/to/.venv/bin/python scripts/live_nav_fetch.py >> reports/pipeline.log 2>&1
```

Keep the actual `.db` file out of version control. Share `sql/schema.sql` instead.
