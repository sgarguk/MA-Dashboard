# MA Dashboard — Setup & Operations

Tactical MA(25/50) dashboard & optimizer for QQQ/SPY strategies.
Live: https://ma-dashboard-9wx.pages.dev/

## Architecture
- `build.py` — downloads daily prices (yfinance), computes MA(25/50) signals,
  8 strategies + optimizer data, then inlines the results into `index.html`.
- `template.html` — page skeleton with `__DASH_DATA__` / `__OPT_DATA__` placeholders.
- `index.html` — generated artifact (committed). Also mirrored to `public/index.html`
  for Cloudflare Pages.
- `.github/workflows/update.yml` — scheduled Action that runs `build.py` and
  commits/pushes any changed `index.html`.

## Schedule
- Cron: `30 22 * * 1-5` = 22:30 UTC Mon–Fri = 06:30 SGT, ~2.5h after the 16:00 ET
  US close (captures the prior session's close the same evening).
- Manual: GitHub → Actions → "Daily Data Update" → Run workflow, or
  `gh workflow run update.yml`.

## Staleness guard (build.py)
- `expected_latest_trade_date()` → latest trading day whose close should be available.
- If downloaded data is behind that date, retries up to 3× (5 min apart), then warns.

## Local dev (Windows)
- `winget install Git.Git GitHub.cli`
- `gh auth login` (browser flow)
- Python 3.11+, `pip install -r requirements.txt`
- `python build.py` regenerates `index.html` + `public/index.html`

## Recent fix (23 Oct 2026)
- One-day data lag fixed: cron `25 1 * * 2-6` → `30 22 * * 1-5`, plus a
  staleness-retry guard added to `build.py`.
