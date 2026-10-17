# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Streamlit multi-page web app (Python 3.13) for Polish IT job-market analysis: scrapes job postings from JustJoin.it, NoFluffJobs, and TheProtocol.it, stores them in PostgreSQL via SQLAlchemy, and serves views for candidates ("blue ocean" niche radar, statistical verification with correlations/OLS, ROI calculator) and for employers (`pages/6_Dla_Firm.py`: salary benchmark, hiring difficulty, competition, job-ad hints). Pages are registered explicitly in `app.py` via `st.navigation` (not the `pages/` auto-discovery). See `README.md` for background.

## Running the app

Everything runs through Docker Compose; there is no bare `streamlit run` workflow documented.

```bash
docker-compose up --build                               # standard run (app + db + scraper-scheduler)
docker-compose -f docker-compose.dev.yml up --build      # dev profile: hot-reload, DEBUG_MODE=true
docker-compose exec streamlit-app /bin/bash               # shell into the app container
docker-compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB   # psql shell
docker-compose exec streamlit-app python -c "from scrapers.scrape_job import run_scrape_job; print(run_scrape_job('manual', 'junior,mid,senior'))"  # manual scrape
docker-compose logs -f scraper-scheduler                  # periodic scraper (scrapers/scheduler.py)
```

Scraping always goes through `scrapers/scrape_job.run_scrape_job()`: it records the run in `scrape_runs` and takes a Postgres advisory lock, so the admin button and the `scraper-scheduler` service never scrape concurrently. Interval/levels come from `SCRAPE_INTERVAL_HOURS` / `SCRAPE_LEVELS` (`0` disables). Code changes in `scrapers/` or `utils/` need a container restart (`docker restart <container>`) — Streamlit's reload doesn't re-import them, and the scheduler is a plain long-running process. Page files under `pages/` are picked up on rerun.

`requirements.txt` is unpinned, so a rebuild can pull newer libraries (e.g. SQLAlchemy 2.1 changed the default Postgres driver — `DatabaseHandler` pins `postgresql+psycopg2` for that reason).

Config comes from `.env` (copy from `.env.example`), loaded via `config/settings.py`. Required vars: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`, `STREAMLIT_PORT`, `ADMIN_KEY`; optional `SCRAPE_INTERVAL_HOURS`, `SCRAPE_LEVELS`.

## Schema changes: no migrations

There is no Alembic. `DatabaseHandler.create_tables()` (`Base.metadata.create_all`) only creates missing tables — it never alters existing ones. After changing a model's columns, apply an `ALTER TABLE` to the existing DB by hand (via the psql shell above), or the ORM will fail on insert.

## Lint and verification

- Lint/format with ruff (`ruff.toml`, line length 100; dev dependency in `requirements-dev.txt`). A PostToolUse hook (`.claude/hooks/ruff_format.py`) runs `ruff check --fix` + `ruff format` on every edited `.py` file — so an import added before its first usage gets removed as unused (F401). Add the usage first, or import and use it in the same edit. Many pre-existing long lines (E501) remain; don't mass-fix them unasked.
- There are no unit tests. Verify pages headlessly with Streamlit's `AppTest` inside the app container, e.g. `docker exec radarmikro-nisz-streamlit-app-1 python -c "from streamlit.testing.v1 import AppTest; at=AppTest.from_file('pages/2_Konkurencja.py', default_timeout=180); at.run(); print(at.exception)"`. Sidebar widgets are reachable as `at.sidebar.selectbox[i]` / `at.sidebar.slider[i]`; selectboxes with `format_func` need `select_index`, not `set_value`.
- **Ignore `.vscode/tasks.json`** — its "Run Tests" task calls a non-existent `tests/` dir, and its "Database Shell" task uses a wrong service/db name.

## Data model and analysis conventions

These encode fixes for real data problems — keep them when touching scrapers or analysis code.

- **Salaries are split by contract form**: `wynagrodzenie_uop_*` (gross monthly), `wynagrodzenie_b2b_*` (net monthly), `wynagrodzenie_godzinowe_*` (hourly, any contract form). Never mix them: analyses pick one via `SALARY_TYPE_COLUMNS` / the "Typ wynagrodzenia" selector, and `_prepare_salary_data` resolves the generic `Wynagrodzenie Od/Do` + `Srednia_Kwota` (range midpoint) for the chosen type. Only PLN amounts are kept. Implausible values (posting errors, e.g. hourly rates entered as monthly) are dropped via `PLAUSIBLE_SALARY_RANGE`.
- **Portal quirks the scrapers handle**: JustJoinIT needs cursor pagination (`from`) and repeated `experienceLevels` params; its `publishedAt` is the latest "bump" while the original date is the earlier `lastPublishedAt`; day/year rates use the API's monthly-equivalent `from`/`to`. NoFluffJobs needs a browser User-Agent (403 otherwise) and exposes no hourly rates. Every source stores **one row per offer** (first location only), not one per city.
- **Ad age is not comparable across portals in raw days** (NoFluffJobs/TheProtocol re-date ads ~every 30 days, JustJoinIT keeps the original date). Use the within-portal percentile `Wzgledny_Wiek_Pct` (per offer) / `Wzgledny_Wiek_Ogloszen` (median per technology); compare raw days only within a portal. `scraped_at` is refreshed on every save, so age = age at last observation.
- **Statistics**: always report n; flag estimates with fewer than 10 observations; prefer medians with bootstrap CIs; per-technology observations share offers (not independent), so treat borderline p-values with caution. `Liczba_Ofert_Z_Widelkami` is the n behind a niche median.
- **ROI calculator**: payback uses the monthly surplus over the user's living cost (entered manually, kept in session state); bootcamp data lives in the `bootcamp_data` table, managed from the admin panel's "Bootcampy" tab (the notebook is only an optional initial import).

## Code conventions

- **Language split is intentional**: UI strings, Streamlit page titles, and DB column/field names (e.g. `stanowisko`, `firma`, `poziom`, `wynagrodzenie_uop_od` in `utils/db_handler.py`) are in **Polish**. Code identifiers, comments, and docstrings are in **English**. Keep this split when adding code — don't translate one into the other.
- Use type hints and Google-style docstrings (`Args:`/`Returns:`) on new functions/classes, matching the existing codebase.
- New scraper sources subclass `BaseScraper` (`scrapers/sources/base.py`) and implement `fetch_raw_data()` / `parse_data()`, emitting the six salary-bucket keys.
- Use `@st.cache_data(show_spinner=False)` / `@st.cache_resource` for expensive analysis/queries (the default cache spinner is deliberately hidden).
- **UI style**: no colourful emoji in titles, tabs, buttons or messages; use plain words for status (e.g. "wysoka / średnia / niska") and monochrome Material icons (`:material/...:`) where an icon is needed.

## Admin auth gotcha

Admin access is a single shared-secret pattern (`Settings.ADMIN_KEY`), not user accounts. `app.py` sets `st.session_state.is_admin` after a sidebar password check, then conditionally adds the admin page to `st.navigation`. **Admin pages do not self-guard** — e.g. `pages/5_Metodologia.py` has no internal auth check and relies entirely on not being registered in the nav when `is_admin` is `False`. If you add a new admin-only page or route, don't assume nav-gating is sufficient protection — be aware there's no page-level check today.

## Git workflow

- New functionality starts on its own branch; merge to `main` only after the user has tested it. Don't merge straight to `main`.
- Commit messages follow Conventional Commits style: `type: description` or `type(scope): description` (e.g. `feat(db): ...`, `fix: ...`, `perf: ...`). Never leave literal placeholder/boilerplate text (e.g. "Here is a summarized commit message...") as the actual commit title.
