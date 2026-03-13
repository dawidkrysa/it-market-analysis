from abc import ABC, abstractmethod
from typing import Any, List, Dict
import logging

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """
        Abstract base class for all scrapers. Defines the interface and common workflow for fetching and parsing data.
    """
    def __init__(self, source_name: str) -> None:
        self.source_name: str = source_name

    @abstractmethod
    def fetch_raw_data(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """ Downloads raw data from the source. Should be implemented by each scraper. """
        pass

    @abstractmethod
    def parse_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """ Parses the raw data into a standardized format. Should be implemented by each scraper. """
        pass

    def run(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """
            Executes the full scraping workflow: fetches raw data and then parses it.
            Handles logging and error management.
        """
        try:
            logger.info(f"Starting {self.source_name}")
            raw: List[Dict[str, Any]] = self.fetch_raw_data(*args, **kwargs)
            parsed: List[Dict[str, Any]] = self.parse_data(raw)
            logger.info(f"Successfully processed {len(parsed)} offers from {self.source_name}")
            return parsed
        except Exception as e:
            logger.error(f"Error in scraper {self.source_name}: {e}")
            return []