"""
Single entry point for a full scraping run, shared by the admin panel and the scheduler.

Every run is recorded in the `scrape_runs` table. A PostgreSQL advisory lock makes
sure a manual run and a scheduled run never scrape (and write) at the same time.
"""

import logging
from dataclasses import dataclass

from sqlalchemy import text

from scrapers.scraper_manager import ScraperManager
from utils.db_handler import DatabaseHandler

logger = logging.getLogger(__name__)

# Arbitrary key shared by every process that scrapes; must stay constant.
SCRAPE_LOCK_KEY = 727_274_101


@dataclass
class ScrapeResult:
    """Outcome of a scraping run."""

    status: str  # "success", "failed" or "skipped" (another run holds the lock)
    saved_count: int = 0
    error: str | None = None


def run_scrape_job(trigger: str, experience_levels: str) -> ScrapeResult:
    """
    Scrape all sources for the given levels and save the results.

    Args:
        trigger (str): "auto" (scheduler) or "manual" (admin panel).
        experience_levels (str): Comma-separated levels, e.g. "junior,mid,senior".

    Returns:
        ScrapeResult: Status of the run; "skipped" if another run is in progress.
    """
    db = DatabaseHandler()
    db.create_tables()

    # The lock lives as long as this connection, so keep it open for the whole run.
    with db.engine.connect() as lock_conn:
        acquired = lock_conn.execute(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": SCRAPE_LOCK_KEY}
        ).scalar()
        if not acquired:
            logger.info("Scrape (%s) skipped: another run is in progress", trigger)
            return ScrapeResult(status="skipped")

        run_id = db.start_scrape_run(trigger, experience_levels)
        logger.info("Scrape run %s started (%s, levels=%s)", run_id, trigger, experience_levels)
        try:
            jobs = ScraperManager().run_all(experience_levels=experience_levels)
            saved = db.save_jobs(jobs) if jobs else 0
            db.finish_scrape_run(run_id, "success", saved_count=saved)
            logger.info("Scrape run %s finished: %s postings saved", run_id, saved)
            return ScrapeResult(status="success", saved_count=saved)
        except Exception as e:
            db.finish_scrape_run(run_id, "failed", error=str(e))
            logger.exception("Scrape run %s failed", run_id)
            return ScrapeResult(status="failed", error=str(e))
        finally:
            lock_conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": SCRAPE_LOCK_KEY})
