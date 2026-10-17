# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Streamlit multi-page web app (Python 3.13) for Polish IT job-market analysis: scrapes job postings from JustJoin.it, NoFluffJobs, and TheProtocol.it, stores them in PostgreSQL via SQLAlchemy, and surfaces "blue ocean" niche analysis, salary regression, and an ROI calculator. See `README.md` for full details — it's already thorough and up to date.

## Running the app

Everything runs through Docker Compose; there is no bare `streamlit run` workflow documented.

```bash
docker-compose up --build                               # standard run
docker-compose -f docker-compose.dev.yml up --build      # dev profile: hot-reload, DEBUG_MODE=true
docker-compose exec streamlit-app /bin/bash               # shell into the app container
docker-compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB   # psql shell
docker-compose exec streamlit-app python -c "from scrapers.scrape_job import run_scrape_job; print(run_scrape_job('manual', 'junior,mid,senior'))"  # manual scrape
docker-compose logs -f scraper-scheduler                  # periodic scraper (scrapers/scheduler.py)
```

Scraping always goes through `scrapers/scrape_job.run_scrape_job()`: it records the run in `scrape_runs` and takes a Postgres advisory lock, so the admin button and the `scraper-scheduler` service never scrape concurrently. Interval/levels come from `SCRAPE_INTERVAL_HOURS` / `SCRAPE_LEVELS` (`0` disables). Code changes in `scrapers/` or `utils/` need a container restart (`docker restart <container>`) — Streamlit's reload doesn't re-import them, and the scheduler is a plain long-running process.

`requirements.txt` is unpinned, so a rebuild can pull newer libraries (e.g. SQLAlchemy 2.1 changed the default Postgres driver — `DatabaseHandler` pins `postgresql+psycopg2` for that reason).

Config comes from `.env` (copy from `.env.example`), loaded via `config/settings.py`. Required vars: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`, `STREAMLIT_PORT`, `ADMIN_KEY`.

## No tests, no lint

There is no test framework, lint config, or Makefile in this repo. **Ignore `.vscode/tasks.json`** — its "Run Tests" task calls `pytest tests/ -v`, but there is no `tests/` directory and pytest isn't in `requirements.txt`; its "Database Shell" task also references a `postgres` service name and `radar_db` database that don't match the actual `docker-compose.yml` (service is `db`, db name comes from `.env`). Don't rely on that file.

## Code conventions

- **Language split is intentional**: UI strings, Streamlit page titles, and DB column/field names (e.g. `stanowisko`, `firma`, `poziom`, `wynagrodzenie_od` in `utils/db_handler.py`) are in **Polish**. Code identifiers, comments, and docstrings are in **English**. Keep this split when adding code — don't translate one into the other.
- Use type hints and Google-style docstrings (`Args:`/`Returns:`) on new functions/classes, matching the existing codebase.
- New scraper sources subclass `BaseScraper` (`scrapers/sources/base.py`) and implement `fetch_raw_data()` / `parse_data()`.
- Use `@st.cache_data`/`@st.cache_resource` where appropriate for expensive analysis/queries — this is used deliberately elsewhere for performance.

## Admin auth gotcha

Admin access is a single shared-secret pattern (`Settings.ADMIN_KEY`), not user accounts. `app.py` sets `st.session_state.is_admin` after a sidebar password check, then conditionally adds the admin page to `st.navigation`. **Admin pages do not self-guard** — e.g. `pages/5_Metodologia.py` has no internal auth check and relies entirely on not being registered in the nav when `is_admin` is `False`. If you add a new admin-only page or route, don't assume nav-gating is sufficient protection — be aware there's no page-level check today.

## Git workflow

- New functionality starts on its own branch; merge to `main` only after the user has tested it. Don't merge straight to `main`.
- Commit messages follow Conventional Commits style: `type: description` or `type(scope): description` (e.g. `feat(db): ...`, `fix: ...`, `perf: ...`). Never leave literal placeholder/boilerplate text (e.g. "Here is a summarized commit message...") as the actual commit title.
