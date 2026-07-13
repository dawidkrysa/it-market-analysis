# 🧭 Radar Mikro-Nisz IT

**Interactive analysis of information asymmetry in the Polish IT job market.** A Streamlit application that mines job postings scraped from industry portals to identify technology "blue oceans" — niches with high demand but low candidate supply — and statistically verifies whether the market actually pays a premium for them.

Built as part of the **Projekt Semestralny II** university course.
**Team:** Dawid Krysa, Wojciech Pomarkiewicz, Wiktor Daniel, Krzysztof Krajewski

## 📖 Business context

People entering the IT industry (bootcamp graduates, self-taught developers, career switchers) typically choose which technology to learn based on popularity or anecdotal opinions rather than hard market data. This drives **structural unemployment**: an oversupply of candidates in saturated "red ocean" stacks (e.g. entry-level front-end) alongside a shortage of specialists in niches that employers struggle to fill.

Radar Mikro-Nisz addresses this with four decision-support modules:

| Module | Business question it answers |
|---|---|
| 🌊 **Blue Ocean Radar** | Which technologies have many job openings but little candidate competition (deficit niches)? |
| 📈 **Statistical Verification** | Do niche size and time-to-fill actually correlate with higher pay (Spearman/Kendall tests), or is that just an illusion? |
| 💰 **ROI Calculator** | Does investing time and money in a specific bootcamp pay off, accounting for cost of living and forgone income? |
| ⚙️ **Data Engine** (admin panel) | Where does the data come from, and how is it refreshed/cleared? |

The data isn't self-reported (surveys, industry reports) — it's pulled directly from thousands of live job postings, which limits the bias typical of self-reported salary studies.

## 🏗️ Technical architecture

- **Frontend/UI:** Streamlit (multi-page app, native `st.navigation` routing)
- **Database:** PostgreSQL, accessed via the SQLAlchemy ORM (`utils/db_handler.py`)
- **Data acquisition:** custom scrapers (`requests` + `BeautifulSoup4`/JSON API) for three portals:
  - [JustJoin.it](https://justjoin.it) (public API)
  - [NoFluffJobs](https://nofluffjobs.com)
  - [TheProtocol.it](https://theprotocol.it)
- **Statistical analysis:** SciPy (Spearman/Kendall correlations), Pandas, Statsmodels
- **Visualization:** Plotly, native Streamlit charts
- **Containerization:** Docker + docker-compose (separate `prod`/`dev` profiles), Dev Container support (VS Code / PyCharm)

### Scraper architecture

All scrapers inherit from `BaseScraper` (`scrapers/sources/base.py`), which enforces a `fetch_raw_data()` → `parse_data()` contract and standardizes logging/error handling. `ScraperManager` (`scrapers/scraper_manager.py`) registers the available sources and lets you run all of them at once (`run_all`) or a single one (`run_single`).

## 📁 Project structure

```
.
├── app.py                 # Streamlit entry point, routing, admin panel
├── pages/                 # Application pages
│   ├── 1_Home.py
│   ├── 2_Konkurencja.py       # Blue Ocean Radar
│   ├── 3_Regresja.py          # Statistical verification (correlations)
│   ├── 4_Kalkulator_ROI.py    # ROI calculator
│   └── 5_Metodologia.py       # Admin panel: scraping, data preview, cleanup
├── scrapers/               # Scraper manager and source scrapers
│   ├── scraper_manager.py
│   └── sources/
│       ├── base.py
│       ├── justjoinit.py
│       ├── nofluffjobs.py
│       └── theprotocolit.py
├── utils/                  # Data layer and logging
│   ├── db_handler.py           # SQLAlchemy model + CRUD/analytics operations
│   └── logging_config.py
├── config/                 # Application configuration (environment variables)
├── examples/                # Sample input data (raw API responses, cost of living, bootcamps)
├── notebooks/               # Exploratory notebooks (EDA, CSV-to-Postgres import)
├── logs/                    # Application logs (not version-controlled)
├── Dockerfile
├── docker-compose.yml        # Production/standard profile
├── docker-compose.dev.yml    # Development profile (hot-reload, DEBUG_MODE)
├── requirements.txt
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

### A note on `ADMIN_KEY`

The `ADMIN_KEY` variable in `.env` unlocks the admin panel (the "Data Engine" module — running scrapers and clearing the database). Set it to your own private secret; never commit the real value.

### Development workflow

For development with hot-reload and extra debugging, use the separate compose file:

```bash
docker-compose -f docker-compose.dev.yml up --build
```

Matching VS Code tasks live in [.vscode/tasks.json](.vscode/tasks.json), and the Dev Container configuration is in [.devcontainer/devcontainer.json](.devcontainer/devcontainer.json) (supports both VS Code and PyCharm Professional).

## 🛠️ Common commands

```bash
# Start the application
docker-compose up --build

# Stop the application
docker-compose down

# View logs
docker-compose logs -f streamlit-app

# Open a shell inside the app container
docker-compose exec streamlit-app /bin/bash

# Manually run all scrapers from inside the container
docker-compose exec streamlit-app python -c "from scrapers.scraper_manager import ScraperManager; ScraperManager().run_all()"

# Install dependencies inside the container
docker-compose exec streamlit-app pip install -r requirements.txt
```

Scraping can also be triggered from the UI: log into the admin panel (`ADMIN_KEY`) and go to **Data Engine → Fetch data**.

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
