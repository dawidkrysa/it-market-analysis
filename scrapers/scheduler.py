"""
Background scheduler that scrapes job portals periodically.

Runs as its own container (`scraper-scheduler` in docker-compose):

    python -m scrapers.scheduler

A run is due when SCRAPE_INTERVAL_HOURS have passed since the last successful run
(manual runs from the admin panel count too), so restarts never cause duplicate runs.
"""

import logging
import time
from datetime import UTC, datetime, timedelta

from config.settings import Settings
from scrapers.scrape_job import run_scrape_job
from utils.db_handler import DatabaseHandler
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

# How often the scheduler wakes up to check whether a run is due.
CHECK_INTERVAL_SECONDS = 300
# Back-off after a failed or skipped run, so a broken source isn't hammered.
RETRY_AFTER_SECONDS = 1800


def next_run_at(db: DatabaseHandler, interval: timedelta) -> datetime:
    """
    Compute when the next scheduled run is due.

    Args:
        db (DatabaseHandler): Database access for the run history.
        interval (timedelta): Time between successful runs.

    Returns:
        datetime: UTC time of the next due run (now, if there was never a successful run).
    """
    last = db.get_last_scrape_run(only_success=True)
    if last is None or last["finished_at"] is None:
        return datetime.now(UTC)
    return last["finished_at"] + interval


def main() -> None:
    """Loop forever, triggering a scrape whenever one is due."""
    setup_logging()
    interval_hours = Settings.SCRAPE_INTERVAL_HOURS
    if interval_hours <= 0:
        logger.info("Automatic scraping disabled (SCRAPE_INTERVAL_HOURS <= 0)")
        while True:  # stay alive so `restart: unless-stopped` doesn't loop
            time.sleep(3600)

    interval = timedelta(hours=interval_hours)
    db = DatabaseHandler()
    db.create_tables()
    logger.info("Scheduler started: every %sh, levels=%s", interval_hours, Settings.SCRAPE_LEVELS)

    while True:
        due_at = next_run_at(db, interval)
        now = datetime.now(UTC)
        if now < due_at:
            time.sleep(min((due_at - now).total_seconds(), CHECK_INTERVAL_SECONDS))
            continue

        result = run_scrape_job("auto", Settings.SCRAPE_LEVELS)
        if result.status != "success":
            time.sleep(RETRY_AFTER_SECONDS)


if __name__ == "__main__":
    main()
