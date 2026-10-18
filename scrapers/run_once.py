"""
Run a single scrape and exit - the entry point for scheduled jobs (e.g. a Railway cron service).

    python -m scrapers.run_once

Unlike `scrapers/scheduler.py` (a long-running loop for docker-compose), this process
exits as soon as the run finishes, so a cron-triggered container only exists - and is
only billed - for the few minutes the scrape takes. Exit code 0 means success or a
skipped run (another scrape held the lock); 1 means the run failed.
"""

import logging
import sys

from config.settings import Settings
from scrapers.scrape_job import run_scrape_job
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


def main() -> int:
    """
    Execute one scrape for the configured levels.

    Returns:
        int: Process exit code (0 = success/skipped, 1 = failed).
    """
    setup_logging()
    result = run_scrape_job("auto", Settings.SCRAPE_LEVELS)
    logger.info("One-shot scrape finished: %s", result)
    return 1 if result.status == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
