# LC Tactical MA Dashboard & Optimizer

Self-contained HTML dashboard with:
- **Dashboard**: Full performance overview for all 8 tactical MA strategies (QQQ/SPY families, 1x/2x/3x/Blend)
- **Blend Optimizer**: Interactive weight sliders + Deep Bear filter (MA100/150/200)

Auto-updates daily at US market close via GitHub Actions → Netlify.

## Setup (one-time, ~5 minutes)

### 1. Fork / create repo
Push this folder to a new GitHub repository (public or private).

### 2. Connect to Netlify
1. Log in to [netlify.com](https://netlify.com)
2. **Add new site → Import from Git**
3. Select your GitHub repo
4. Build settings:
   - **Build command**: *(leave blank — pre-built HTML)*
   - **Publish directory**: `.`
5. Click **Deploy**

Your site is live at `https://your-site.netlify.app`

### 3. Enable daily auto-updates
The `.github/workflows/update.yml` workflow runs automatically **Mon–Fri at 5:30 PM ET** (after US market close).

To trigger it manually: GitHub repo → **Actions** tab → **Daily Data Update** → **Run workflow**

The workflow:
1. Downloads fresh price data from Yahoo Finance
2. Re-runs the full backtest
3. Regenerates `index.html` with updated data
4. Commits and pushes → Netlify auto-deploys in ~30 seconds

### 4. Initial data build (optional)
To rebuild locally before pushing:
```bash
pip install -r requirements.txt
python build.py
```

## File structure
```
├── index.html          # Generated dashboard (do not edit manually)
├── template.html       # HTML template with __DASH_DATA__ / __OPT_DATA__ placeholders
├── build.py            # Python build script
├── requirements.txt
├── netlify.toml
└── .github/
    └── workflows/
        └── update.yml  # Daily GitHub Actions workflow
```

## Strategy overview
| Strategy | Signal | Bull Allocation |
|---|---|---|
| QQQ 3x | QQQ MA(25/50) | 100% TQQQ |
| QQQ 2x | QQQ MA(25/50) | 100% QLD |
| QQQ Blend | QQQ MA(25/50) | 50% QQQ + 30% QLD + 20% TQQQ |
| QQQ 1x | QQQ MA(25/50) | 100% QQQ |
| SPY 3x | SPY MA(25/50) | 100% SPXL |
| SPY 2x | SPY MA(25/50) | 100% SSO |
| SPY Blend | SPY MA(25/50) | 50% SPY + 30% SSO + 20% SPXL |
| SPY 1x | SPY MA(25/50) | 100% SPY |

Defensive regime (price > MA50, ≤ MA25): 75% base + 25% BIL  
Bear regime (price ≤ MA50): 50% base + 50% BIL  
Deep Bear (optional filter): price ≤ MA50 AND ≤ MA100/150/200 → configurable equity %

## Disclaimer
Internal use only — Lighthouse Canton Pte. Ltd. Compliance review required before external distribution.
