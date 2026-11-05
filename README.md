# Radar Mikro-Nisz IT

**Interactive analysis of information asymmetry in the Polish IT job market.** A Streamlit application that mines job postings scraped from industry portals to help candidates decide **what to learn, how much to ask for and whether a bootcamp pays off**, and to show employers **what the competition offers and how to hire better** — with statistical checks on whether the "niche premium" is real.

Built as part of the **Projekt Semestralny II** university course and kept as a portfolio project open to further development.
**Team:** Dawid Krysa (lead, development), Wojciech Pomarkiewicz, Wiktor Daniel, Krzysztof Krajewski (economic analysis and review)

**Success criteria:** a working public demo, statistically defensible conclusions, and real users (measured with the in-app feedback form). Goals, key decisions and the pre-defence specs are recorded in [`docs/specs/`](docs/specs/README.md).

## 📖 Business context

The project started from one problem: **juniors can't find work.** People entering the IT industry (bootcamp graduates, self-taught developers, career switchers) typically choose which technology to learn based on popularity or anecdotal opinions rather than hard market data. This drives **structural unemployment**: an oversupply of candidates in saturated "red ocean" stacks (e.g. entry-level front-end) alongside a shortage of specialists in niches that employers struggle to fill. Employers, in turn, lack a benchmark of what other companies offer and show in their ads.

This semester the scope was widened from juniors to **mid and senior** as well. Candidate views let you pick the experience level and default to **Junior**, the original target group. Candidates and employers are treated as equally important audiences.

| Module | Audience | Business question it answers |
|---|---|---|
| 🌊 **Blue Ocean Radar** | candidates | Which technologies are open to someone at my level, pay well and are hard to fill (ads stay up long)? |
| 📈 **Statistical Verification** | candidates | At my level, do niche size and time-to-fill actually correlate with higher pay (Spearman/Kendall tests, OLS), or is that just an illusion? |
| 💰 **ROI Calculator** | candidates | Does investing time and money in a specific bootcamp pay off at the salary my level actually earns, accounting for cost of living? |
| 🏢 **For Employers** (`Dla Firm`) | employers | How much to offer for a role, how hard it will be to hire, who else is hiring the same people, and how to write the job ad? |
| ⚙️ **Data Engine** (admin panel) | team | Where does the data come from, how is it refreshed/cleared, which bootcamps feed the ROI calculator, and what do users say? |

The data isn't self-reported (surveys, industry reports) — it's pulled directly from thousands of live job postings, which limits the bias typical of self-reported salary studies.

## 🏗️ Technical architecture

- **Frontend/UI:** Streamlit (multi-page app, native `st.navigation` routing)
- **Database:** PostgreSQL, accessed via SQLAlchemy (`utils/db_handler.py`); [Neon](https://neon.tech) in production
- **Data acquisition:** custom scrapers (`requests` + `BeautifulSoup4`/JSON API) for three portals:
  - [JustJoin.it](https://justjoin.it) (public API)
  - [NoFluffJobs](https://nofluffjobs.com)
  - [TheProtocol.it](https://theprotocol.it)
- **Statistical analysis:** SciPy (Spearman/Kendall correlations), Pandas, Statsmodels
- **Visualization:** Plotly, native Streamlit charts
- **Containerization:** Docker + docker-compose (separate `prod`/`dev` profiles), Dev Container support (VS Code / PyCharm)
- **Hosting:** Streamlit Community Cloud (app) + Neon (database) + GitHub Actions (scheduled scraping) — see [Deployment](#-deployment)

### Scraper architecture

All scrapers inherit from `BaseScraper` (`scrapers/sources/base.py`), which enforces a `fetch_raw_data()` → `parse_data()` contract and standardizes logging/error handling. `ScraperManager` (`scrapers/scraper_manager.py`) registers the available sources and lets you run all of them at once (`run_all`) or a single one (`run_single`).

Every scrape — from the admin panel, the `scraper-scheduler` service or the CI job — goes through `scrapers/scrape_job.run_scrape_job()`. It records the run in the `scrape_runs` table, holds a Postgres advisory lock so two scrapes never run at once, saves postings with a batched upsert, and after a successful run deletes postings not seen for `SCRAPE_RETENTION_DAYS` (default 30). Two entry points wrap it:

- `python -m scrapers.scheduler` — long-running loop (the `scraper-scheduler` compose service), every `SCRAPE_INTERVAL_HOURS`.
- `python -m scrapers.run_once` — a single run that exits (used by the GitHub Actions cron).

### Data conventions

- Salaries are kept separately per contract form: employment contract (UoP, gross monthly), B2B (net monthly) and hourly rates. Analyses never mix them — pick one with the **"Typ wynagrodzenia"** selector. Only PLN amounts are kept and implausible values are dropped.
- Each offer is stored once (first location only), even if a portal lists it in several cities.
- Raw ad age isn't comparable across portals (some re-date ads every ~30 days), so views use a within-portal percentile instead.
- Statistics always report `n`, flag estimates based on fewer than 10 observations and prefer medians with bootstrap confidence intervals.
- **Experience level:** the Radar, Statistical Verification and ROI pages share one level filter in the sidebar (default Junior, remembered across pages for the session). Every figure on those pages is computed only from offers at the selected levels. With only Trainee/Junior selected, the niche-size defaults are lower (e.g. Radar: 5–40 offers instead of 15–70), because far fewer postings exist per technology.

## 🔬 Methodology: what counts as a niche

Job portals don't publish how many candidates apply, so candidate competition can't be measured directly. The Radar therefore scores technologies with three proxies, all computed from offers at the **selected experience levels**:

| Component | Metric | What it approximates |
|---|---|---|
| Openness | share of the technology's offers that are at the selected levels (`Udzial_Ofert_Poziomu`) | does this technology actually hire people at my level |
| Pay | median salary-range midpoint for the chosen salary type (`Mediana_Zarobkow`) | financial attractiveness |
| Hiring difficulty | median within-portal ad-age percentile (`Wzgledny_Wiek_Ogloszen`) | candidate shortage — ads stay up longer |

**Niche score** (`Wynik_Niszy`, 0–100) = the mean percentile rank of the three components among the technologies passing the sidebar filters (offer count range, ≥ 10% of offers with a salary range, minimum `n`). Each component has equal weight. When all levels are selected, openness is 100% for every technology and is left out of the score.

**Limitations.** A long-running ad may also mean high requirements or an "always open" recruitment rather than a shortage. Offers listing several technologies feed several niches at once, so per-technology observations aren't independent. The ad-age percentile is computed per portal across all levels, so a level's hiring difficulty is relative to the whole portal. Treat the ranking as a lead to investigate, not a recommendation. The same caveats apply to the correlation tests on the Statistical Verification page.

## 💬 User feedback

A **"Twoja opinia"** form in the sidebar of every page asks whether the app helped with a decision (yes / partly / no), who the user is (candidate / company / other) and for an optional comment. Answers go to the `feedback` table, together with the page title, and are shown in the admin panel's **Opinie** tab. Spam protection: one submission per browser session, no submissions within the first 10 seconds of a session, at most 30 submissions per hour globally, and comments capped at 1000 characters.

## 📁 Project structure

```
.
├── app.py                 # Streamlit entry point, routing (st.navigation), admin login
├── pages/                 # Application pages
│   ├── 1_Home.py              # Dashboard
│   ├── 2_Konkurencja.py       # Blue Ocean Radar
│   ├── 3_Regresja.py          # Statistical verification (correlations, OLS)
│   ├── 4_Kalkulator_ROI.py    # ROI calculator
│   ├── 5_Metodologia.py       # Admin panel: scraping, data preview, cleanup, bootcamps
│   └── 6_Dla_Firm.py          # Employer view: salary benchmark, hiring difficulty, competition
├── scrapers/               # Scraping jobs, manager and source scrapers
│   ├── scrape_job.py          # Single entry point for every scrape (lock, run log, save, retention)
│   ├── scheduler.py           # Periodic loop (docker-compose scraper-scheduler service)
│   ├── run_once.py            # One-shot scrape (GitHub Actions cron)
│   ├── scraper_manager.py
│   └── sources/
│       ├── base.py
│       ├── justjoinit.py
│       ├── nofluffjobs.py
│       └── theprotocolit.py
├── utils/                  # Data layer, charts, UI helpers and logging
│   ├── db_handler.py           # SQLAlchemy models + save/analytics operations
│   ├── charts.py
│   ├── ui.py                   # Shared sidebar widgets (salary type, level filter, feedback form)
│   └── logging_config.py
├── config/                 # Application configuration (environment variables)
├── docs/specs/             # Project goal, key decisions and small feature specs
├── .github/workflows/
│   └── scrape.yml           # Scheduled scraping into the production database
├── examples/                # Sample input data (raw API responses, cost of living, bootcamps)
├── notebooks/               # Exploratory notebooks (EDA, CSV-to-Postgres import)
├── logs/                    # Application logs (not version-controlled)
├── Dockerfile
├── docker-compose.yml        # Standard profile: app + db + scraper-scheduler
├── docker-compose.dev.yml    # Development profile (hot-reload, DEBUG_MODE)
├── requirements.txt          # Runtime dependencies
├── requirements-dev.txt      # Dev tooling (ruff, notebooks)
├── ruff.toml
└── README.md
```

## 🚀 Quick start

### Prerequisites
- Docker and Docker Compose
- Git

### Setup & run

1. Clone the repository.
2. Copy the environment template and **fill in your own values** (don't leave `CHANGE_ME` in place):
   ```bash
   cp .env.example .env
   ```
3. Start the application:
   ```bash
   docker-compose up --build
   ```
4. Open the app in your browser:
   ```text
   http://localhost:8501
   ```

The database starts empty — run a scrape (see below) to fill it.

### Environment variables

| Variable | Required | Meaning |
|---|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT` | yes | Local database (docker-compose builds `DATABASE_URL` from these) |
| `STREAMLIT_PORT` | yes | Port the app is published on locally |
| `ADMIN_KEY` | yes | Password for the admin panel |
| `SCRAPE_INTERVAL_HOURS` | no | Hours between automatic scrapes in `scraper-scheduler` (default `24`, `0` disables) |
| `SCRAPE_LEVELS` | no | Seniority levels to scrape (default `junior,mid,senior`) |
| `SCRAPE_RETENTION_DAYS` | no | Delete postings not seen for this many days (default `30`, `0` keeps all) |
| `DATABASE_URL` | hosting only | Full connection string, used instead of the `POSTGRES_*` variables outside docker-compose |

### A note on `ADMIN_KEY`

The `ADMIN_KEY` variable unlocks the admin panel (the "Data Engine" module — running scrapers, clearing the database, managing bootcamps, reading feedback). Set it to your own private secret; never commit the real value. The admin page is hidden from the navigation for non-admins and also checks `st.session_state.is_admin` itself, refusing to render without an admin session.

### Development workflow

For development with hot-reload and extra debugging, use the separate compose file:

```bash
docker-compose -f docker-compose.dev.yml up --build
```

The Dev Container configuration is in [.devcontainer/devcontainer.json](.devcontainer/devcontainer.json) (supports both VS Code and PyCharm Professional).

- Lint and format with ruff (`ruff check --fix . && ruff format .`, config in `ruff.toml`, install from `requirements-dev.txt`).
- Changes in `scrapers/` or `utils/` need a container restart (`docker-compose restart`); page files under `pages/` reload on their own.
- There are no migrations: `create_tables()` only creates missing tables. After changing a model's columns, apply the matching `ALTER TABLE` to existing databases by hand.

## 🛠️ Common commands

```bash
# Start the application
docker-compose up --build

# Stop the application
docker-compose down

# View logs
docker-compose logs -f streamlit-app
docker-compose logs -f scraper-scheduler

# Open a shell inside the app container
docker-compose exec streamlit-app /bin/bash

# Run one scrape and save the results (same path as the admin panel and the scheduler)
docker-compose exec streamlit-app python -m scrapers.run_once

# Install dependencies inside the container
docker-compose exec streamlit-app pip install -r requirements.txt
```

Scraping can also be triggered from the UI: log into the admin panel (`ADMIN_KEY`) and go to **Data Engine → Fetch data**.

## 🌐 Deployment

The public instance runs entirely on free tiers:

| Part | Service | Notes |
|---|---|---|
| App | [Streamlit Community Cloud](https://share.streamlit.io) | Deploys from the `main` branch (`app.py`, Python 3.13). Sleeps after inactivity and wakes up on the next visit. |
| Database | [Neon](https://neon.tech) (PostgreSQL, Frankfurt) | Free 0.5 GB; the 30-day retention keeps the data well below that. |
| Scraping | GitHub Actions ([`scrape.yml`](.github/workflows/scrape.yml)) | Runs `python -m scrapers.run_once` at 04:00 UTC on every 3rd day of the month, or on demand via **Actions → Scrape job postings → Run workflow**. |

Every push to `main` is deployed automatically, so new work goes through a feature branch first.

Free tiers were chosen on purpose, to show the whole pipeline can run at zero cost. The trade-off is cold starts: both the Streamlit app and the Neon database suspend when idle, so the first visit after a pause takes noticeably longer. Before a demo, open the app once to wake it up. New tables (e.g. `feedback`) are created automatically on first use, so no manual SQL is needed after deploying this version.

### Secrets

| Where | Secret | Value |
|---|---|---|
| Streamlit Cloud → app **Settings → Secrets** | `DATABASE_URL` | Neon connection string **with** `-pooler` in the host (many short connections) |
| | `ADMIN_KEY` | Admin panel password |
| GitHub → **Settings → Secrets and variables → Actions** | `DATABASE_URL` | Neon connection string **without** `-pooler` (one long-lived connection holding the scrape lock) |

Both strings need `?sslmode=require`. Streamlit Cloud exposes top-level secrets as environment variables, so `config/settings.py` reads them like any other setting.

### Known limitations

- **TheProtocol.it returns `403` to GitHub Actions runners** (datacenter IPs are blocked), so the production database currently holds offers from JustJoin.it and NoFluffJobs only. Tracked in [#9](https://github.com/dawidkrysa/it-market-analysis/issues/9).
- Streamlit Community Cloud can't switch the branch of an existing app — to deploy from another branch, delete the app and create it again (copy the secrets first).

## 📊 Database management

### Open a PostgreSQL shell

```bash
docker-compose exec db psql -U ${POSTGRES_USER:-CHANGE_ME} -d ${POSTGRES_DB:-CHANGE_ME}
```

### Back up the database

```bash
docker-compose exec db pg_dump -U ${POSTGRES_USER:-CHANGE_ME} ${POSTGRES_DB:-CHANGE_ME} > backup.sql
```

### Restore the database

```bash
docker-compose exec db psql -U ${POSTGRES_USER:-CHANGE_ME} ${POSTGRES_DB:-CHANGE_ME} < backup.sql
```

## 🐛 Troubleshooting

### Port already in use

```bash
docker-compose down
```

### Changes not reflecting

1. Check logs:
   ```bash
   docker-compose logs -f streamlit-app
   ```
2. Restart containers:
   ```bash
   docker-compose down && docker-compose up --build
   ```

### Database connection issues

```bash
docker-compose ps
docker-compose restart db
```

## 📝 License

MIT licensed — see [`LICENSE`](LICENSE).

## 🔗 Technologies

- Streamlit
- PostgreSQL + SQLAlchemy
- Docker / Docker Compose
- BeautifulSoup4 + Requests
- Pandas / NumPy / SciPy / Statsmodels
- Plotly
